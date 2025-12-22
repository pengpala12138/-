import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Input,
  Select,
  DatePicker,
  Button,
  Space,
  Tag,
  Tooltip,
  Row,
  Col,
  Statistic,
  Descriptions,
  Modal,
  Alert,
  Badge,
  Typography
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  ClearOutlined,
  EyeOutlined,
  ExportOutlined,
  DeleteOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  BugOutlined,
  SecurityScanOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { getSystemLogs } from '../services/api';
import moment from 'moment';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { Text } = Typography;

const SystemLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 50,
    total: 0
  });
  const [filters, setFilters] = useState({
    log_type: '',
    module: '',
    search: '',
    dateRange: [moment().startOf('day'), moment().endOf('day')]
  });
  const [selectedLog, setSelectedLog] = useState(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [logStats, setLogStats] = useState({
    total: 0,
    info: 0,
    warning: 0,
    error: 0,
    security: 0
  });

  useEffect(() => {
    fetchLogs();
  }, [pagination.current, pagination.pageSize, filters]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = {
        page: pagination.current,
        page_size: pagination.pageSize,
        type: filters.log_type,
        module: filters.module,
        start_date: filters.dateRange[0]?.format('YYYY-MM-DD'),
        end_date: filters.dateRange[1]?.format('YYYY-MM-DD'),
        search: filters.search
      };

      const result = await getSystemLogs(params);
      setLogs(result.logs || []);
      setPagination(prev => ({
        ...prev,
        total: result.pagination?.total || 0
      }));

      // 计算统计
      const stats = {
        total: result.pagination?.total || 0,
        info: result.logs?.filter(l => l.log_type === 'info').length || 0,
        warning: result.logs?.filter(l => l.log_type === 'warning').length || 0,
        error: result.logs?.filter(l => l.log_type === 'error').length || 0,
        security: result.logs?.filter(l => l.log_type === 'security').length || 0
      };
      setLogStats(stats);
    } catch (error) {
      console.error('获取系统日志失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTableChange = (pagination) => {
    setPagination(pagination);
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, current: 1 }));
  };

  const handleClearFilters = () => {
    setFilters({
      log_type: '',
      module: '',
      search: '',
      dateRange: [moment().startOf('day'), moment().endOf('day')]
    });
  };

  const handleViewDetail = (log) => {
    setSelectedLog(log);
    setDetailVisible(true);
  };

  const handleExportLogs = () => {
    // 导出日志功能
    alert('导出功能开发中...');
  };

  const handleClearLogs = () => {
    Modal.confirm({
      title: '确认清空日志',
      content: '确定要清空所有日志记录吗？此操作不可恢复。',
      okText: '确定',
      okType: 'danger',
      cancelText: '取消',
      onOk() {
        alert('清空日志功能开发中...');
      }
    });
  };

  const getLogTypeConfig = (type) => {
    const configs = {
      info: {
        color: 'blue',
        icon: <InfoCircleOutlined />,
        text: '信息'
      },
      warning: {
        color: 'orange',
        icon: <WarningOutlined />,
        text: '警告'
      },
      error: {
        color: 'red',
        icon: <BugOutlined />,
        text: '错误'
      },
      security: {
        color: 'red',
        icon: <SecurityScanOutlined />,
        text: '安全'
      }
    };
    return configs[type] || { color: 'default', icon: null, text: type };
  };

  const getLogLevelText = (type) => {
    const texts = {
      info: '信息',
      warning: '警告',
      error: '错误',
      security: '安全'
    };
    return texts[type] || type;
  };

  const getModuleText = (module) => {
    const texts = {
      tourist: '游客管理',
      reservation: '预约管理',
      entry: '入园管理',
      trajectory: '轨迹监控',
      flow_control: '流量控制',
      security: '安全管理',
      system: '系统管理',
      backup: '数据备份'
    };
    return texts[module] || module;
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'time',
      width: 120,
      render: (text) => moment(text).format('HH:mm:ss'),
      sorter: (a, b) => moment(a.created_at).unix() - moment(b.created_at).unix()
    },
    {
      title: '级别',
      dataIndex: 'log_type',
      key: 'type',
      width: 80,
      render: (type) => {
        const config = getLogTypeConfig(type);
        return (
          <Tooltip title={getLogLevelText(type)}>
            <Tag color={config.color} icon={config.icon}>
              {config.text}
            </Tag>
          </Tooltip>
        );
      },
      filters: [
        { text: '信息', value: 'info' },
        { text: '警告', value: 'warning' },
        { text: '错误', value: 'error' },
        { text: '安全', value: 'security' }
      ],
      filteredValue: filters.log_type ? [filters.log_type] : null,
      onFilter: (value, record) => record.log_type === value
    },
    {
      title: '模块',
      dataIndex: 'module',
      key: 'module',
      width: 100,
      render: (module) => (
        <Tooltip title={module}>
          <Tag color="blue">{getModuleText(module)}</Tag>
        </Tooltip>
      ),
      filters: [
        { text: '游客管理', value: 'tourist' },
        { text: '预约管理', value: 'reservation' },
        { text: '入园管理', value: 'entry' },
        { text: '轨迹监控', value: 'trajectory' },
        { text: '流量控制', value: 'flow_control' },
        { text: '安全管理', value: 'security' },
        { text: '系统管理', value: 'system' }
      ],
      filteredValue: filters.module ? [filters.module] : null,
      onFilter: (value, record) => record.module === value
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <Text style={{ maxWidth: 400 }} ellipsis>
            {text}
          </Text>
        </Tooltip>
      )
    },
    {
      title: '用户',
      dataIndex: 'user_id',
      key: 'user',
      width: 100,
      render: (userId) => userId || '-'
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip',
      width: 120,
      render: (ip) => ip || '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
          size="small"
        />
      )
    }
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>
          系统日志
        </h2>
        <Space>
          <Badge count={logStats.warning + logStats.error + logStats.security}>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchLogs}
              loading={loading}
            >
              刷新
            </Button>
          </Badge>
        </Space>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="总日志数"
              value={logStats.total}
              prefix={<InfoCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="信息日志"
              value={logStats.info}
              prefix={<InfoCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="警告日志"
              value={logStats.warning}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="错误日志"
              value={logStats.error + logStats.security}
              prefix={<BugOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="日志查询"
        extra={
          <Space>
            <Button
              icon={<ExportOutlined />}
              onClick={handleExportLogs}
            >
              导出
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleClearLogs}
            >
              清空
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <div style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]} align="middle">
            <Col xs={24} md={8}>
              <Input
                placeholder="搜索日志内容..."
                prefix={<SearchOutlined />}
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
                allowClear
              />
            </Col>
            <Col xs={24} md={6}>
              <Select
                placeholder="日志级别"
                style={{ width: '100%' }}
                value={filters.log_type || undefined}
                onChange={(value) => handleFilterChange('log_type', value)}
                allowClear
              >
                <Option value="info">信息</Option>
                <Option value="warning">警告</Option>
                <Option value="error">错误</Option>
                <Option value="security">安全</Option>
              </Select>
            </Col>
            <Col xs={24} md={6}>
              <Select
                placeholder="模块"
                style={{ width: '100%' }}
                value={filters.module || undefined}
                onChange={(value) => handleFilterChange('module', value)}
                allowClear
              >
                <Option value="tourist">游客管理</Option>
                <Option value="reservation">预约管理</Option>
                <Option value="entry">入园管理</Option>
                <Option value="trajectory">轨迹监控</Option>
                <Option value="flow_control">流量控制</Option>
                <Option value="security">安全管理</Option>
                <Option value="system">系统管理</Option>
              </Select>
            </Col>
            <Col xs={24} md={8}>
              <RangePicker
                style={{ width: '100%' }}
                value={filters.dateRange}
                onChange={(dates) => handleFilterChange('dateRange', dates)}
                format="YYYY-MM-DD"
              />
            </Col>
            <Col xs={24} md={4}>
              <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                <Button
                  icon={<FilterOutlined />}
                  onClick={fetchLogs}
                  loading={loading}
                  type="primary"
                >
                  筛选
                </Button>
                <Button
                  icon={<ClearOutlined />}
                  onClick={handleClearFilters}
                >
                  清空
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        {(logStats.warning > 0 || logStats.error > 0) && (
          <Alert
            message="存在异常日志"
            description={`发现 ${logStats.warning} 条警告和 ${logStats.error + logStats.security} 条错误/安全日志，请及时处理。`}
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Table
          columns={columns}
          dataSource={logs}
          rowKey="log_id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条日志`,
            pageSizeOptions: ['20', '50', '100', '200']
          }}
          onChange={handleTableChange}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 日志详情模态框 */}
      <Modal
        title="日志详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={800}
      >
        {selectedLog && (
          <div>
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="日志ID">
                {selectedLog.log_id}
              </Descriptions.Item>
              <Descriptions.Item label="时间">
                {moment(selectedLog.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="级别">
                <Tag color={getLogTypeConfig(selectedLog.log_type).color}>
                  {getLogTypeConfig(selectedLog.log_type).text}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="模块">
                <Tag color="blue">{getModuleText(selectedLog.module)}</Tag>
                <span style={{ marginLeft: 8, color: '#666' }}>
                  ({selectedLog.module})
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="消息">
                <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {selectedLog.message}
                </div>
              </Descriptions.Item>
              <Descriptions.Item label="用户ID">
                {selectedLog.user_id || '系统'}
              </Descriptions.Item>
              <Descriptions.Item label="IP地址">
                {selectedLog.ip_address || '未知'}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 24 }}>
              <h4>处理建议</h4>
              {selectedLog.log_type === 'warning' && (
                <Alert
                  message="警告日志处理建议"
                  description="请检查相关系统模块，确保系统正常运行。可能需要人工干预。"
                  type="warning"
                  showIcon
                />
              )}
              {selectedLog.log_type === 'error' && (
                <Alert
                  message="错误日志处理建议"
                  description="需要立即关注，检查系统错误原因并进行修复。"
                  type="error"
                  showIcon
                />
              )}
              {selectedLog.log_type === 'security' && (
                <Alert
                  message="安全日志处理建议"
                  description="涉及系统安全，需要立即检查并采取安全措施。"
                  type="error"
                  showIcon
                />
              )}
              {selectedLog.log_type === 'info' && (
                <Alert
                  message="信息日志说明"
                  description="正常系统操作记录，无需特别处理。"
                  type="info"
                  showIcon
                />
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default SystemLogs;