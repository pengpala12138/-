import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Input,
  Select,
  DatePicker,
  Modal,
  Form,
  InputNumber,
  Tag,
  Space,
  message
} from 'antd';
import { PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { getReservations, createReservation } from '../services/api';
import moment from 'moment';
import { updateReservation } from '../services/api';
const { RangePicker } = DatePicker;
const { Option } = Select;

const ReservationManagement = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchReservations();
  }, []);

  const fetchReservations = async (params = {}) => {
    setLoading(true);
    try {
      const result = await getReservations(params);
      setData(result || []);
    } catch (error) {
      message.error('获取预约数据失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddReservation = () => {
    form.resetFields();
    setModalVisible(true);
  };
const handleUpdatePayment = async (id, status) => {
  try {
    // 调用 api 更新支付状态
    await updateReservation(id, { payment_status: status });
    message.success('支付状态已更新');
    fetchReservations(); // 刷新列表
  } catch (error) {
    message.error('更新失败');
  }
};
  const handleSubmit = async (values) => {
    try {
      const formattedValues = {
        ...values,
        reservation_date: values.reservation_date.format('YYYY-MM-DD'),
        group_size: values.group_size || 1,
        ticket_amount: values.ticket_amount || 0,
        status: 'confirmed',
        payment_status: 'pending'
      };

      await createReservation(formattedValues);
      message.success('预约创建成功');
      setModalVisible(false);
      fetchReservations();
    } catch (error) {
      message.error('创建预约失败');
      console.error(error);
    }
  };

  const columns = [
    {
      title: '预约编号',
      dataIndex: 'reservation_id',
      key: 'reservation_id',
    },
    {
      title: '游客ID',
      dataIndex: 'tourist_id',
      key: 'tourist_id',
    },
    {
      title: '预约日期',
      dataIndex: 'reservation_date',
      key: 'reservation_date',
      render: (text) => moment(text).format('YYYY-MM-DD')
    },
    {
      title: '入园时段',
      dataIndex: 'entry_time_slot',
      key: 'entry_time_slot',
    },
    {
      title: '同行人数',
      dataIndex: 'group_size',
      key: 'group_size',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusMap = {
          confirmed: { color: 'blue', text: '已确认' },
          cancelled: { color: 'red', text: '已取消' },
          completed: { color: 'green', text: '已完成' }
        };
        const statusInfo = statusMap[status] || { color: 'default', text: status };
        return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>;
      }
    },
    {
      title: '票价',
      dataIndex: 'ticket_amount',
      key: 'ticket_amount',
      render: (amount) => `¥${amount}`
    },
    {
      title: '支付状态',
      dataIndex: 'payment_status',
      key: 'payment_status',
      render: (status) => {
        const statusMap = {
          pending: { color: 'orange', text: '待支付' },
          paid: { color: 'green', text: '已支付' },
          refunded: { color: 'red', text: '已退款' }
        };
        const statusInfo = statusMap[status] || { color: 'default', text: status };
        return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>;
      }
    },
      {
  title: '操作',
  key: 'action',
  render: (_, record) => (
    <Space size="small">
      {record.payment_status === 'pending' && (
        <Button
          type="link"
          onClick={() => handleUpdatePayment(record.reservation_id, 'paid')}
        >
          确认支付
        </Button>
      )}
      {/* 也可以添加取消预约按钮 */}
    </Space>
  ),
},
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <Input
            placeholder="搜索预约编号"
            prefix={<SearchOutlined />}
            style={{ width: 200 }}
          />
          <Select
            placeholder="状态筛选"
            style={{ width: 120 }}
            allowClear
          >
            <Option value="confirmed">已确认</Option>
            <Option value="cancelled">已取消</Option>
            <Option value="completed">已完成</Option>
          </Select>
          <RangePicker />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAddReservation}>
          新增预约
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="reservation_id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title="新增预约"
        open={modalVisible}
        onOk={() => form.submit()}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            group_size: 1,
            ticket_amount: 100,
            entry_time_slot: '08:00-10:00'
          }}
        >
          <Form.Item
            name="reservation_id"
            label="预约编号"
            rules={[{ required: true, message: '请输入预约编号' }]}
          >
            <Input placeholder="请输入预约编号" />
          </Form.Item>

          <Form.Item
            name="tourist_id"
            label="游客ID"
            rules={[{ required: true, message: '请输入游客ID' }]}
          >
            <Input placeholder="请输入游客ID" />
          </Form.Item>

          <Form.Item
            name="reservation_date"
            label="预约日期"
            rules={[{ required: true, message: '请选择预约日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="entry_time_slot"
            label="入园时段"
            rules={[{ required: true, message: '请选择入园时段' }]}
          >
            <Select>
              <Option value="08:00-10:00">08:00-10:00</Option>
              <Option value="10:00-12:00">10:00-12:00</Option>
              <Option value="12:00-14:00">12:00-14:00</Option>
              <Option value="14:00-16:00">14:00-16:00</Option>
              <Option value="16:00-18:00">16:00-18:00</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="group_size"
            label="同行人数"
          >
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="ticket_amount"
            label="票价"
          >
            <InputNumber
              min={0}
              step={0.01}
              style={{ width: '100%' }}
              prefix="¥"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ReservationManagement;