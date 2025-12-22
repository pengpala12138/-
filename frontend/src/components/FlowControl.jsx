import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Space,
  Alert,
  Modal,
  Form,
  InputNumber,
  message,
  Select,
  Switch,
  Divider,
  Timeline
} from 'antd';
import {
  BarChartOutlined,
  TeamOutlined,
  WarningOutlined,
  SettingOutlined,
  ReloadOutlined,
  LineChartOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import { getDataView, executeProcedure, apiRequest } from '../services/api'; // 确保导入apiRequest
import moment from 'moment';

const { Option } = Select;

const FlowControl = () => {
  const [areas, setAreas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedArea, setSelectedArea] = useState(null);
  const [form] = Form.useForm();
  const [historyData, setHistoryData] = useState([]);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchFlowData();
    if (autoRefresh) {
      const interval = setInterval(fetchFlowData, 10000); // 10秒刷新
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const fetchFlowData = async () => {
    setLoading(true);
    try {
      // 修改这里：直接调用流量控制API，而不是视图
      const response = await apiRequest('GET', '/api/flow-control');
      if (response && Array.isArray(response)) {
        setAreas(response);
      } else {
        // 如果视图数据格式不同，回退到原逻辑
        const result = await getDataView('flow-monitoring');
        setAreas(result || []);
      }
    } catch (error) {
      console.error('获取流量数据失败:', error);
      message.error('获取流量数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    fetchFlowData();
    message.info('数据已刷新');
  };

  const handleUpdateFlow = (area) => {
    setSelectedArea(area);
    form.setFieldsValue({
      current_visitors: area.current_visitors,
      daily_capacity: area.daily_capacity,
      warning_threshold: area.warning_threshold
    });
    setModalVisible(true);
  };

  const handleSubmit = async (values) => {
    setSubmitting(true);
    try {
      if (!selectedArea) {
        message.error('未选择区域');
        return;
      }

      // 调用更新API
      const response = await apiRequest(
        'PUT',
        `/api/flow-control/${selectedArea.area_id}`,
        {
          daily_capacity: values.daily_capacity,
          warning_threshold: values.warning_threshold,
          current_visitors: values.current_visitors
        }
      );

      if (response && response.message) {
        message.success(response.message);

        // 更新本地数据
        const updatedAreas = areas.map(area => {
          if (area.area_id === selectedArea.area_id) {
            return {
              ...area,
              ...values,
              last_updated: new Date().toISOString(),
              // 计算状态（前端预览用，实际由后端计算）
              status: calculateStatus(
                values.current_visitors,
                values.daily_capacity,
                values.warning_threshold
              ),
              capacity_percentage: Math.round((values.current_visitors / values.daily_capacity) * 100)
            };
          }
          return area;
        });

        setAreas(updatedAreas);
      } else {
        message.error('更新失败');
      }

      setModalVisible(false);
    } catch (error) {
      console.error('更新失败:', error);
      message.error(error.message || '更新失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 计算区域状态（前端预览用）
  const calculateStatus = (current, capacity, threshold) => {
    const percentage = current / capacity;
    if (percentage >= 1) return 'restricted';
    if (percentage >= threshold) return 'warning';
    return 'normal';
  };

  const handleUpdateFlowStatus = async () => {
    try {
      const result = await executeProcedure('update-flow-status');
      message.success('流量状态更新成功');
      fetchFlowData(); // 重新获取数据
    } catch (error) {
      message.error('更新失败');
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      normal: '#52c41a',
      warning: '#faad14',
      restricted: '#ff4d4f'
    };
    return colors[status] || '#666';
  };

  const getStatusText = (status) => {
    const texts = {
      normal: '正常',
      warning: '预警',
      restricted: '限流'
    };
    return texts[status] || status;
  };

  const columns = [
    {
      title: '区域',
      dataIndex: 'area_id',
      key: 'area',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.area_name || text}</div>
          <div style={{ fontSize: 12, color: '#666' }}>
            ID: {text}
          </div>
        </div>
      ),
    },
    {
      title: '承载量',
      key: 'capacity',
      render: (_, record) => {
        const percentage = Math.round((record.current_visitors / record.daily_capacity) * 100);
        const isOverCapacity = record.current_visitors >= record.daily_capacity;
        const isWarning = !isOverCapacity &&
          record.current_visitors >= record.daily_capacity * record.warning_threshold;

        return (
          <div>
            <div style={{ marginBottom: 4 }}>
              <TeamOutlined style={{ marginRight: 8 }} />
              {record.current_visitors} / {record.daily_capacity}
            </div>
            <Progress
              percent={percentage}
              size="small"
              status={isOverCapacity ? 'exception' : isWarning ? 'normal' : 'success'}
            />
          </div>
        );
      },
    },
    {
      title: '使用率',
      key: 'usage',
      render: (_, record) => {
        const percentage = Math.round((record.current_visitors / record.daily_capacity) * 100);
        return (
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: 20,
              fontWeight: 'bold',
              color: percentage >= 100 ? '#ff4d4f' :
                     percentage >= (record.warning_threshold * 100) ? '#faad14' : '#52c41a'
            }}>
              {percentage}%
            </div>
            <div style={{ fontSize: 12, color: '#666' }}>
              承载率
            </div>
          </div>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status, record) => {
        const color = getStatusColor(status);
        const text = getStatusText(status);

        let additionalInfo = '';
        if (record.current_visitors >= record.daily_capacity) {
          additionalInfo = '（已达上限）';
        } else if (record.current_visitors >= record.daily_capacity * record.warning_threshold) {
          additionalInfo = '（接近上限）';
        }

        return (
          <div>
            <Tag color={color} style={{ marginBottom: 4 }}>
              {text}
            </Tag>
            <div style={{ fontSize: 12, color: '#666' }}>
              {additionalInfo}
            </div>
          </div>
        );
      },
    },
    {
      title: '预警阈值',
      dataIndex: 'warning_threshold',
      key: 'threshold',
      render: (threshold) => `${(threshold * 100).toFixed(0)}%`,
    },
    {
      title: '最近更新',
      key: 'last_updated',
      render: (_, record) => (
        <div>
          <div style={{ marginBottom: 4 }}>
            {record.last_updated ?
              moment(record.last_updated).fromNow() :
              '从未更新'}
          </div>
          <div style={{ fontSize: 12, color: '#666' }}>
            {record.last_updated ?
              moment(record.last_updated).format('HH:mm:ss') :
              '--'}
          </div>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            size="small"
            onClick={() => handleUpdateFlow(record)}
          >
            调整
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => viewAreaHistory(record)}
          >
            历史
          </Button>
        </Space>
      ),
    },
  ];

  const viewAreaHistory = (area) => {
    setSelectedArea(area);
    // 这里可以调用API获取历史数据
    const history = [
      { time: '09:00', visitors: 200, status: 'normal' },
      { time: '10:00', visitors: 450, status: 'normal' },
      { time: '11:00', visitors: 650, status: 'warning' },
      { time: '12:00', visitors: 820, status: 'warning' },
      { time: '13:00', visitors: 780, status: 'warning' },
      { time: '14:00', visitors: 920, status: 'restricted' },
      { time: '15:00', visitors: 880, status: 'warning' },
    ];
    setHistoryData(history);
    // 显示历史模态框
    // 可以创建另一个模态框显示历史数据
    Modal.info({
      title: `区域 ${area.area_id} 历史流量`,
      width: 600,
      content: (
        <Timeline>
          {history.map((item, index) => (
            <Timeline.Item
              key={index}
              color={item.status === 'normal' ? 'green' :
                     item.status === 'warning' ? 'orange' : 'red'}
            >
              <p>{item.time} - {item.visitors} 人</p>
              <p>状态: {getStatusText(item.status)}</p>
            </Timeline.Item>
          ))}
        </Timeline>
      ),
    });
  };

  // 统计信息
  const stats = {
    totalAreas: areas.length,
    warningAreas: areas.filter(a => a.status === 'warning').length,
    restrictedAreas: areas.filter(a => a.status === 'restricted').length,
    totalVisitors: areas.reduce((sum, a) => sum + (a.current_visitors || 0), 0),
    totalCapacity: areas.reduce((sum, a) => sum + (a.daily_capacity || 0), 0),
    averageUsage: areas.length > 0 ?
      Math.round(areas.reduce((sum, a) => {
        const percentage = (a.current_visitors / a.daily_capacity) * 100;
        return sum + percentage;
      }, 0) / areas.length) : 0
  };

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>流量控制</h2>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card>
            <Statistic
              title="监控区域"
              value={stats.totalAreas}
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card>
            <Statistic
              title="当前游客"
              value={stats.totalVisitors}
              prefix={<TeamOutlined />}
              suffix={`/${stats.totalCapacity}`}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card>
            <Statistic
              title="预警区域"
              value={stats.warningAreas}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card>
            <Statistic
              title="平均使用率"
              value={stats.averageUsage}
              suffix="%"
              prefix={<LineChartOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="区域流量监控"
        extra={
          <Space>
            <Switch
              checked={autoRefresh}
              onChange={setAutoRefresh}
              checkedChildren="自动刷新"
              unCheckedChildren="手动刷新"
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchFlowData}
              loading={loading}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<SettingOutlined />}
              onClick={handleUpdateFlowStatus}
            >
              更新状态
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        {areas.some(a => a.status === 'restricted') && (
          <Alert
            message="限流预警"
            description="有区域已达到最大承载量，已启动限流措施"
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {areas.some(a => a.status === 'warning') && (
          <Alert
            message="流量预警"
            description="部分区域游客数量接近上限，请注意疏导"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Table
          columns={columns}
          dataSource={areas}
          rowKey="area_id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 调整流量模态框 */}
      <Modal
        title={`调整流量 - ${selectedArea?.area_id || ''}`}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={submitting}
        width={500}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            warning_threshold: 0.8
          }}
        >
          <Form.Item
            name="daily_capacity"
            label="日最大承载量"
            rules={[
              { required: true, message: '请输入承载量' },
              { type: 'number', min: 1, message: '承载量必须大于0' }
            ]}
          >
            <InputNumber
              min={1}
              style={{ width: '100%' }}
              placeholder="请输入最大承载量"
            />
          </Form.Item>

          <Form.Item
            name="current_visitors"
            label="当前游客数量"
            rules={[
              { required: true, message: '请输入游客数量' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  const dailyCapacity = getFieldValue('daily_capacity');
                  if (value > dailyCapacity) {
                    return Promise.reject(new Error(`不能超过最大承载量 ${dailyCapacity}`));
                  }
                  return Promise.resolve();
                },
              }),
            ]}
          >
            <InputNumber
              min={0}
              style={{ width: '100%' }}
              placeholder="请输入当前游客数量"
            />
          </Form.Item>

          <Form.Item
            name="warning_threshold"
            label="预警阈值"
            rules={[{ required: true, message: '请选择预警阈值' }]}
          >
            <Select placeholder="请选择预警阈值">
              <Option value={0.7}>70%（宽松）</Option>
              <Option value={0.8}>80%（标准）</Option>
              <Option value={0.9}>90%（严格）</Option>
            </Select>
          </Form.Item>

          <Alert
            message="调整提示"
            description={
              <div>
                <p>• 调整后系统会自动重新计算区域状态</p>
                <p>• 状态计算规则：</p>
                <p>&nbsp;&nbsp;- 正常：当前游客 &lt; 承载量 × 预警阈值</p>
                <p>&nbsp;&nbsp;- 预警：当前游客 ≥ 承载量 × 预警阈值</p>
                <p>&nbsp;&nbsp;- 限流：当前游客 ≥ 承载量</p>
              </div>
            }
            type="info"
            showIcon
          />
        </Form>
      </Modal>
    </div>
  );
};

export default FlowControl;