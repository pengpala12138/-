import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Input,
  Space,
  Modal,
  Form,
  InputNumber,
  Select,
  DatePicker,
  Tag,
  message,
  Popconfirm,
  Row,   // 添加这一行
  Col
} from 'antd';
import {
  SearchOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import { getTourists, createTourist, updateTourist, deleteTourist } from '../services/api';
import moment from 'moment';

const { Search } = Input;
const { Option } = Select;

const TouristManagement = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchData();
  }, [pagination.current, pagination.pageSize, searchText]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = {
        page: pagination.current,
        page_size: pagination.pageSize,
        search: searchText
      };
      const result = await getTourists(params);
      setData(result || []);
      // 如果有分页信息可以更新pagination.total
    } catch (error) {
      message.error('获取游客数据失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleTableChange = (pagination) => {
    setPagination(pagination);
  };

  const handleSearch = (value) => {
    setSearchText(value);
    setPagination({ ...pagination, current: 1 });
  };

  const showAddModal = () => {
    setEditingRecord(null);
    form.resetFields();
    setModalVisible(true);
  };

  const showEditModal = (record) => {
    setEditingRecord(record);
    form.setFieldsValue({
      ...record,
      entry_time: record.entry_time ? moment(record.entry_time) : null,
      exit_time: record.exit_time ? moment(record.exit_time) : null
    });
    setModalVisible(true);
  };

  const handleDelete = async (touristId) => {
    try {
      await deleteTourist(touristId);
      message.success('删除成功');
      fetchData();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const submitData = {
        ...values,
        entry_time: values.entry_time ? values.entry_time.format('YYYY-MM-DD HH:mm:ss') : null,
      exit_time: values.exit_time ? values.exit_time.format('YYYY-MM-DD HH:mm:ss') : null
      };
      if (editingRecord) {
        delete submitData.tourist_id;
        await updateTourist(editingRecord.tourist_id, submitData);
        message.success('更新成功');
      } else {
        await createTourist(values);
        message.success('创建成功');
      }

      setModalVisible(false);
      fetchData();
    } catch (error) {
      console.error('提交失败:', error);
    }
  };

  const columns = [
    {
      title: '游客ID',
      dataIndex: 'tourist_id',
      key: 'tourist_id',
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '身份证号',
      dataIndex: 'id_card',
      key: 'id_card',
      render: (text) => text && `${text.substring(0, 6)}****${text.substring(14)}`
    },
    {
      title: '联系方式',
      dataIndex: 'phone',
      key: 'phone',
    },
    {
      title: '入园方式',
      dataIndex: 'entry_method',
      key: 'entry_method',
      render: (text) => (
        <Tag color={text === 'online' ? 'blue' : 'green'}>
          {text === 'online' ? '线上预约' : '现场购票'}
        </Tag>
      )
    },
    {
      title: '入园时间',
      dataIndex: 'entry_time',
      key: 'entry_time',
      render: (text) => text ? moment(text).format('YYYY-MM-DD HH:mm') : '-'
    },
    {
      title: '状态',
      key: 'status',
      render: (_, record) => {
        if (!record.entry_time) return <Tag color="default">未入园</Tag>;
        if (!record.exit_time) return <Tag color="success">在园中</Tag>;
        return <Tag color="processing">已离园</Tag>;
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
           onClick={async () => {
            try {
              // 快速更新离园时间为当前时间
              await updateTourist(record.tourist_id, { exit_time: moment().format('YYYY-MM-DD HH:mm:ss') });
              message.success('已办理离园');
              fetchData();
            } catch (e) { message.error('离园办理失败'); }
          }}
        >
          离园办理
        </Button>

      <Button type="link" icon={<EditOutlined />} onClick={() => showEditModal(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确定要删除此游客吗？"
            onConfirm={() => handleDelete(record.tourist_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <Search
            placeholder="搜索游客姓名、ID或身份证号"
            allowClear
            enterButton={<SearchOutlined />}
            onSearch={handleSearch}
            style={{ width: 300 }}
          />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={showAddModal}>
          添加游客
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="tourist_id"
        loading={loading}
        pagination={{
          ...pagination,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`
        }}
        onChange={handleTableChange}
      />

      <Modal
        title={editingRecord ? '编辑游客' : '添加游客'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ entry_method: 'online' }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="tourist_id"
                label="游客ID"
                rules={[{ required: true, message: '请输入游客ID' }]}
              >
                <Input placeholder="请输入游客ID" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="name"
                label="姓名"
                rules={[{ required: true, message: '请输入姓名' }]}
              >
                <Input placeholder="请输入姓名" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="id_card"
                label="身份证号"
                rules={[
                  { required: true, message: '请输入身份证号' },
                  { pattern: /^\d{17}[\dXx]$/, message: '身份证号格式不正确' }
                ]}
              >
                <Input placeholder="请输入身份证号" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="phone"
                label="联系方式"
                rules={[{ pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确' }]}
              >
                <Input placeholder="请输入联系方式" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="entry_method"
                label="入园方式"
              >
                <Select>
                  <Option value="online">线上预约</Option>
                  <Option value="onsite">现场购票</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          {editingRecord && (
            <>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="entry_time"
                    label="入园时间"
                  >
                    <DatePicker showTime style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="exit_time"
                    label="离园时间"
                  >
                    <DatePicker showTime style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
            </>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default TouristManagement;