import React, { useState, useEffect } from 'react';
import {
  Card, Form, Input, Select, Button, message,
  Row, Col, Table, Tag, Typography, Radio, Space
} from 'antd';
import {SendOutlined, BarChartOutlined, EnvironmentOutlined} from '@ant-design/icons';
import axios from 'axios';
import moment from 'moment';

const { TextArea } = Input;
const { Option } = Select;
const { Title, Text } = Typography;

// 配置区域映射（保持与你系统其他部分一致）
const AREA_CONFIG = {
  'A001': 'A区 - 主入口广场',
  'A002': 'B区 - 园林区',
  'A003': 'C区 - 休闲区',
  'A004': 'D区 - 观景区',
};

const TouristService = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [ecoData, setEcoData] = useState([]);
  const [role, setRole] = useState('officer'); // 角色状态：officer(监管员) 或 manager(管理层)

  // 获取视图数据
  const fetchEcoData = async (currentRole) => {
    setTableLoading(true);
    try {
      // 这里的 URL 对应后端新写的 /api/eco-stats/<role> 接口
      const res = await axios.get(`http://192.168.69.44:5000/api/eco-stats/${currentRole}`);
      setEcoData(res.data || []);
    } catch (error) {
      message.error('获取生态数据失败');
    } finally {
      setTableLoading(false);
    }
  };

  useEffect(() => {
    fetchEcoData(role);
  }, [role]);

  // 提交反馈
  const onFinish = async (values) => {
    setLoading(true);
    try {
      const res = await axios.post('http://192.168.69.44:5000/api/ecological-feedback', values);
      if (res.data.success) {
        message.success('反馈提交成功，感谢您的参与！');
        form.resetFields();
        fetchEcoData(role); // 刷新数据
      }
    } catch (error) {
      message.error('提交失败，请检查网络或后端接口');
    } finally {
      setLoading(false);
    }
  };

  // 定义表格列 - 满足不同角色
  const columns = role === 'manager' ? [
    { title: '区域编号', dataIndex: 'area_id', key: 'area_id' },
    { title: '区域名称', key: 'area_name', render: (_, r) => AREA_CONFIG[r.area_id] || r.area_id },
    { title: '累计反馈数', dataIndex: 'total_feedbacks', key: 'total_feedbacks', sorter: (a, b) => a.total_feedbacks - b.total_feedbacks },
    { title: '待处理', dataIndex: 'pending_count', key: 'pending_count', render: (c) => <Tag color={c > 0 ? 'volcano' : 'green'}>{c}</Tag> },
    { title: '最后反馈时间', dataIndex: 'last_feedback_time', key: 'last_feedback_time', render: (t) => t ? moment(t).format('YYYY-MM-DD HH:mm') : '-' }
  ] : [
    { title: '游客姓名', dataIndex: 'tourist_name', key: 'tourist_name' },
    { title: '联系电话', dataIndex: 'tourist_phone', key: 'tourist_phone' },
    { title: '类型', dataIndex: 'feedback_type', key: 'feedback_type', render: (t) => <Tag color="blue">{t}</Tag> },
    { title: '反馈内容', dataIndex: 'content', key: 'content', ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'status', render: (s) => (
      <Tag color={s === '待处理' ? 'orange' : 'cyan'}>{s}</Tag>
    )},
    { title: '提交时间', dataIndex: 'created_at', key: 'created_at', render: (t) => moment(t).format('MM-DD HH:mm') }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>游客服务与生态监督</Title>

      <Row gutter={[24, 24]}>
        {/* 左侧：提交表单 */}
        <Col xs={24} lg={8}>
          <Card
            title={<span><EnvironmentOutlined style={{ color: '#52c41a', marginRight: 8 }} />提交生态保护反馈</span>}
            variant="outlined"
          >
            <Form form={form} layout="vertical" onFinish={onFinish}>
              <Form.Item name="tourist_id" label="游客ID" rules={[{ required: true, message: '请输入您的游客ID' }]}>
                <Input placeholder="例如: TOUR1001" />
              </Form.Item>

              <Form.Item name="area_id" label="发现区域" rules={[{ required: true }]}>
                <Select placeholder="选择所在区域">
                  {Object.entries(AREA_CONFIG).map(([id, name]) => (
                    <Option key={id} value={id}>{name}</Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item name="feedback_type" label="问题类型" rules={[{ required: true }]}>
                <Select placeholder="请选择问题类型">
                  <Option value="垃圾处理">垃圾处理</Option>
                  <Option value="植被破坏">植被破坏</Option>
                  <Option value="动物干扰">动物干扰</Option>
                  <Option value="水体污染">水体污染</Option>
                  <Option value="其他">其他</Option>
                </Select>
              </Form.Item>

              <Form.Item name="content" label="详情描述" rules={[{ required: true }]}>
                <TextArea rows={4} placeholder="请描述您看到的具体情况..." />
              </Form.Item>

              <Button type="primary" htmlType="submit" loading={loading} icon={<SendOutlined />} block>
                提交反馈
              </Button>
            </Form>
          </Card>
        </Col>

        {/* 右侧：数据看板（展示视图数据） */}
        <Col xs={24} lg={16}>
          <Card
            title={<span><BarChartOutlined style={{ marginRight: 8 }} />生态监督数据概览</span>}
            extra={
              <Radio.Group value={role} onChange={(e) => setRole(e.target.value)} size="small">
                <Radio.Button value="officer">监管员视图 (明细)</Radio.Button>
                <Radio.Button value="manager">管理层视图 (汇总)</Radio.Button>
              </Radio.Group>
            }
          >
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary">
                {role === 'manager'
                  ? "当前显示：各区域生态问题热点分析（基于 view_area_eco_summary 视图）"
                  : "当前显示：待处理反馈明细清单（基于 view_eco_feedback_details 视图）"}
              </Text>
            </div>

            <Table
              dataSource={ecoData}
              columns={columns}
              rowKey={(r) => r.feedback_id || r.area_id}
              loading={tableLoading}
              pagination={{ pageSize: 6 }}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default TouristService;