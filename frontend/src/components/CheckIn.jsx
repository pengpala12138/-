import React, {useEffect, useState} from 'react';
import {Card, Form, Input, Select, Button, Alert, message, Row, Col, Statistic, List, Tag, Typography} from 'antd';import { CheckCircleOutlined, UserOutlined, IdcardOutlined } from '@ant-design/icons';
import {checkInTourist, getStatistics} from '../services/api';
import moment from 'moment';

const { Option } = Select;
const AREA_CONFIG = {
  'A001': { name: 'A区 - 主入口广场', shortName: 'A区' },
  'A002': { name: 'B区 - 园林区', shortName: 'B区' },
  'A003': { name: 'C区 - 休闲区', shortName: 'C区' },
  'A004': { name: 'D区 - 观景区', shortName: 'D区' },
};
const CheckIn = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [checkInResult, setCheckInResult] = useState(null);
  const [todayStats, setTodayStats] = useState({
    checkedIn: 0,
    pending: 0,
    successRate: '100%'
  });
  const { Text } = Typography; // 2. 确保定义了 Text
  const [recentRecords, setRecentRecords] = useState([]);
 const getAreaName = (areaId) => {
    return AREA_CONFIG[areaId]?.shortName || areaId || '未知区域';
  };

  // 区域ID转换为完整区域名称的辅助函数
  const getAreaFullName = (areaId) => {
    return AREA_CONFIG[areaId]?.name || areaId || '未知区域';
  };

  const refreshData = async () => {
    try {
      const response = await getStatistics();
      console.log('获取到的最新统计数据:', response);

      // 注意：后端返回的对象里嵌套了一个 stats 属性
      if (response && response.stats) {
        const s = response.stats;
        setTodayStats({
          // 匹配后端字段名：visitors_today
          checkedIn: s.visitors_today || 0,
          // 匹配后端字段名：reservations_today (作为待入园参考)
          pending: (s.reservations_today - s.visitors_today) > 0 ? (s.reservations_today - s.visitors_today) : 0,
          successRate: '100%'
        });

        // 如果后端有最近记录，这里处理
        if (response.recent_records) {
           const formattedRecords = response.recent_records.map(record => ({
            ...record,
            // 假设后端返回的area字段是区域ID（如 'A001'），转换为区域名称
           displayArea: getAreaName(record.area)
          }));
          setRecentRecords(formattedRecords);
        }
      }
    } catch (error) {
      console.error("加载统计数据失败", error);
    }
  };
useEffect(() => {
  // 只保留这一行，删除下面那个重复的 loadStats
  refreshData().then(() => console.log('数据初始化刷新完成'));
}, []);
  const handleCheckIn = async (values) => {
    setLoading(true);
    try {
      const result = await checkInTourist(values);
      if (result && (result.success !== false) ){
         const areaName = getAreaFullName(values.area_id);
        message.success('入园核验成功！');
        setCheckInResult({
          success: true,
          message: '入园核验成功',
          tourist: {
            ...result.tourist,
            area: areaName // 添加区域名称
          },
          time: moment().format('YYYY-MM-DD HH:mm:ss')
        });
        form.resetFields();
  await refreshData();
        // 更新统计数据
        setTodayStats(prev => ({
          ...prev,
          checkedIn: prev.checkedIn + 1,
          successRate: '100%'
        }));
      } else {
        message.error(result?.message || '核验返回异常');
        setCheckInResult({
          success: false,
          message: result.message,
          time: moment().format('YYYY-MM-DD HH:mm:ss')
        });
      }
    } catch (error) {
      message.error('入园核验失败，请重试');
      console.error('Check-in error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>入园核验</h2>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={14}>
          <Card
            title="核验游客信息"
            style={{ marginBottom: 24 }}
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleCheckIn}
              initialValues={{ area_id: 'A001' }}
            >
              <Form.Item
                name="tourist_id"
                label="游客ID"
                rules={[{ required: true, message: '请输入游客ID' }]}
              >
                <Input
                  placeholder="请输入游客ID"
                  prefix={<UserOutlined />}
                  size="large"
                />
              </Form.Item>

              <Form.Item
                name="id_card"
                label="身份证号"
                rules={[
                  { required: true, message: '请输入身份证号' },
                  { pattern: /^\d{17}[\dXx]$/, message: '身份证号格式不正确' }
                ]}
              >
                <Input
                  placeholder="请输入身份证号"
                  prefix={<IdcardOutlined />}
                  size="large"
                />
              </Form.Item>

              <Form.Item
                name="area_id"
                label="入园区域"
                rules={[{ required: true, message: '请选择入园区域' }]}
              >
                <Select size="large">
                  <Option value="A001">A区 - 主入口广场</Option>
                  <Option value="A002">B区 - 园林区</Option>
                  <Option value="A003">C区 - 休闲区</Option>
                  <Option value="A004">D区 - 观景区</Option>
                </Select>
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  icon={<CheckCircleOutlined />}
                  size="large"
                  block
                >
                  确认入园
                </Button>
              </Form.Item>
            </Form>

            {checkInResult && (
              <Alert
                message={checkInResult.message}
                type={checkInResult.success ? 'success' : 'error'}
                showIcon
                description={
                  checkInResult.success && (
                    <div>
                      <p>游客：{checkInResult.tourist.name}</p>
                      <p>游客ID：{checkInResult.tourist.tourist_id}</p>
                      <p>入园时间：{checkInResult.time}</p>
                    </div>
                  )
                }
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card title="今日入园统计" style={{ marginBottom: 24 }}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="已入园"
                  value={todayStats.checkedIn}
                  prefix={<UserOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="待入园"
                  value={todayStats.pending}
                  prefix={<UserOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="核验成功率"
                  value={todayStats.successRate}
                  prefix={<CheckCircleOutlined />}
                />
              </Col>
            </Row>
          </Card>

          <Card title="最近入园记录">
          <List
              dataSource={recentRecords}
              renderItem={item => (
                <List.Item>
                  <List.Item.Meta
                    title={<Text strong>{item.name} ({item.tourist_id})</Text>}
                    description={<span>入园区域: <Tag color="blue">{item.displayArea}</Tag></span>}
                  />
                  <div>{item.time}</div>
                </List.Item>
              )}
              locale={{ emptyText: '暂无最近入园记录' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default CheckIn;