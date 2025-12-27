import React, { useState, useEffect, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Timeline,
  Tag,
  Alert,
  Button,
  Space,
  Badge,
  Table,
  Switch,
  Modal,
  Descriptions,
  Tooltip,
  Avatar
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  WarningOutlined,
  UserOutlined,
  DashboardOutlined,
  EyeOutlined,
  SoundOutlined,
  SyncOutlined,
  VideoCameraOutlined,
  ClockCircleOutlined,
  EnvironmentOutlined
} from '@ant-design/icons';
import { getRealtimeMonitor } from '../services/api';
import moment from 'moment';

const RealtimeMonitor = () => {
  const [monitorData, setMonitorData] = useState({
    trajectories: [],
    flow_control: [],
    alerts: [],
    stats: {}
  });
  const [loading, setLoading] = useState(false);
  const [monitorRunning, setMonitorRunning] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [alertDetailVisible, setAlertDetailVisible] = useState(false);
  const [dataStream, setDataStream] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    fetchRealtimeData();

    if (monitorRunning) {
      const interval = setInterval(fetchRealtimeData, 5000); // 5秒刷新
      return () => clearInterval(interval);
    }
  }, [monitorRunning]);

  useEffect(() => {
  if (monitorRunning) {
    const newStream = [...dataStream];

    // 1. 如果有真实的报警数据，插入报警
    if (monitorData.alerts?.length > 0) {
      monitorData.alerts.forEach(alert => {
        if (!dataStream.some(item => item.id === alert.log_id)) {
          newStream.unshift({
            id: alert.log_id,
            type: alert.log_type,
            message: alert.message,
            time: alert.created_at,
            module: alert.module
          });
        }
      });
    } else {
      // 2. 如果没有报警，每隔5秒插入一条“系统心跳”日志，增强视觉反馈
      newStream.unshift({
        id: Date.now(),
        type: 'info',
        message: '系统监控收集中...',
        time: new Date().toISOString(),
        module: 'SYSTEM'
      });
    }

    if (newStream.length > 20) newStream.length = 20;
    setDataStream(newStream);
  }
}, [monitorData]); // 修改依赖项为 monitorData 整体

  const fetchRealtimeData = async () => {
    try {
      const result = await getRealtimeMonitor();
      console.log("Monitor Data from API:", result); // 关键：在控制台看 trajectories 和 alerts 的具体内容
      setMonitorData(result);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('获取实时数据失败:', error);
    }
  };

  const handleToggleMonitor = () => {
    setMonitorRunning(!monitorRunning);
  };

  const handleViewAlertDetail = (alert) => {
    setSelectedAlert(alert);
    setAlertDetailVisible(true);
  };

  const getAlertTypeIcon = (type) => {
    const icons = {
      warning: <WarningOutlined style={{ color: '#faad14' }} />,
      error: <WarningOutlined style={{ color: '#ff4d4f' }} />,
      security: <WarningOutlined style={{ color: '#ff4d4f' }} />,
      info: <SoundOutlined style={{ color: '#1890ff' }} />
    };
    return icons[type] || <SoundOutlined />;
  };

  const getAlertTypeColor = (type) => {
    const colors = {
      warning: 'warning',
      error: 'error',
      security: 'error',
      info: 'processing'
    };
    return colors[type] || 'default';
  };

  const alertColumns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'time',
      width: 100,
      render: (text) => moment(text).format('HH:mm:ss')
    },
    {
      title: '类型',
      dataIndex: 'log_type',
      key: 'type',
      width: 80,
      render: (type) => (
        <Tag color={getAlertTypeColor(type)}>
          {type === 'warning' ? '预警' :
           type === 'error' ? '错误' :
           type === 'security' ? '安全' : '信息'}
        </Tag>
      )
    },
    {
      title: '模块',
      dataIndex: 'module',
      key: 'module',
      width: 100
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => handleViewAlertDetail(record)}
        >
          详情
        </Button>
      )
    }
  ];

  const trajectoryColumns = [
    {
      title: '游客',
      key: 'tourist',
      width: 120,
      render: (_, record) => (
        <Space>
          <Avatar size="small" icon={<UserOutlined />} />
          <div>
            <div style={{ fontWeight: 500 }}>{record.name}</div>
            <div style={{ fontSize: 12, color: '#666' }}>{record.tourist_id}</div>
          </div>
        </Space>
      )
    },
    {
      title: '位置',
      key: 'location',
      render: (_, record) => (
        <Space>
          <EnvironmentOutlined />
          {record.area_id}
        </Space>
      )
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_, record) => {
        if (record.off_route) {
          return <Tag color="red">超出路线</Tag>;
        }
        if (record.area_status === 'warning') {
          return <Tag color="orange">预警区域</Tag>;
        }
        return <Tag color="green">正常</Tag>;
      }
    },
    {
      title: '更新时间',
      key: 'updated',
      width: 100,
      render: (_, record) => {
        const time = moment(record.location_time);
        const diff = moment().diff(time, 'seconds');
        if (diff < 60) return '刚刚';
        if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
        return time.format('HH:mm');
      }
    }
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>
        <VideoCameraOutlined style={{ marginRight: 8 }} />
        实时监控
      </h2>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <DashboardOutlined />
                实时数据流
                <Badge
                  status={monitorRunning ? 'success' : 'default'}
                  text={monitorRunning ? '运行中' : '已暂停'}
                />
              </Space>
            }
            extra={
              <Space>
                <span style={{ fontSize: 12, color: '#666' }}>
                  最后更新: {lastUpdate ? lastUpdate.toLocaleTimeString() : '--'}
                </span>
                <Button
                  icon={monitorRunning ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                  onClick={handleToggleMonitor}
                  type={monitorRunning ? 'default' : 'primary'}
                >
                  {monitorRunning ? '暂停' : '开始'}
                </Button>
                <Button
                  icon={<SyncOutlined />}
                  onClick={fetchRealtimeData}
                  loading={loading}
                >
                  刷新
                </Button>
              </Space>
            }
          >
            <div style={{
              height: 400,
              overflowY: 'auto',
              padding: '0 16px',
              border: '1px solid #f0f0f0',
              borderRadius: 4
            }}>
              <Timeline>
                {dataStream.map((item, index) => (
                  <Timeline.Item
                    key={index}
                    color={getAlertTypeColor(item.type)}
                    dot={getAlertTypeIcon(item.type)}
                  >
                    <div style={{ marginBottom: 4 }}>
                      <strong style={{ marginRight: 8 }}>[{item.module}]</strong>
                      {item.message}
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>
                      {moment(item.time).format('YYYY-MM-DD HH:mm:ss')}
                    </div>
                  </Timeline.Item>
                ))}
                {dataStream.length === 0 && (
                  <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                    <SoundOutlined style={{ fontSize: 32, marginBottom: 16 }} />
                    <div>暂无实时数据</div>
                    <div style={{ fontSize: 12, marginTop: 8 }}>等待系统产生新的数据...</div>
                  </div>
                )}
              </Timeline>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="系统状态">
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="系统状态"
                    value="运行正常"
                    valueStyle={{ color: '#52c41a' }}
                    prefix={<DashboardOutlined />}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="数据采集"
                    value="分钟级"
                    valueStyle={{ color: '#1890ff' }}
                    prefix={<ClockCircleOutlined />}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="在线设备"
                    value={monitorData.stats?.in_park_count || 0}
                    valueStyle={{ color: '#722ed1' }}
                    prefix={<UserOutlined />}
                  />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Statistic
                    title="API响应"
                    value="正常"
                    valueStyle={{ color: '#13c2c2' }}
                    prefix={<SyncOutlined />}
                  />
                </Card>
              </Col>
            </Row>

            <div style={{ marginTop: 16 }}>
              <h4>监控指标</h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                <Tooltip title="在园游客数量">
                  <Tag icon={<UserOutlined />} color="blue">
                    在园: {monitorData.stats?.in_park_count || 0}
                  </Tag>
                </Tooltip>
                <Tooltip title="异常轨迹数量">
                  <Tag icon={<WarningOutlined />} color="orange">
                    异常: {monitorData.stats?.off_route_count || 0}
                  </Tag>
                </Tooltip>
                <Tooltip title="预警区域数量">
                  <Tag icon={<EyeOutlined />} color="red">
                    预警: {monitorData.stats?.warning_areas || 0}
                  </Tag>
                </Tooltip>
                <Tooltip title="今日预约数量">
                  <Tag icon={<ClockCircleOutlined />} color="green">
                    预约: {monitorData.stats?.today_reservations || 0}
                  </Tag>
                </Tooltip>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title="实时预警"
            extra={<a href="/logs">查看全部</a>}
          >
            <Table
              columns={alertColumns}
              dataSource={monitorData.alerts || []}
              size="small"
              pagination={false}
              rowKey={(record) => record.log_id || record.id || Math.random()} // 自动适配字段名
              scroll={{ y: 200 }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title="实时轨迹"
            extra={<a href="/trajectory">查看全部</a>}
          >
            <Table
              columns={trajectoryColumns}
              dataSource={monitorData.trajectories?.slice(0, 5) || []}
              size="small"
              pagination={false}
              rowKey="trajectory_id"
              scroll={{ y: 200 }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24}>
          <Card title="监控视图">
            <div style={{
              height: 300,
              background: '#f5f5f5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 8
            }}>
             {/* 模拟视频扫描线效果 */}
  <div className="video-overlay" style={{
    position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
    background: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))',
    backgroundSize: '100% 2px, 3px 100%', pointerEvents: 'none'
  }} />

  <div style={{ textAlign: 'center', color: '#52c41a', marginTop: 100 }}>
    <VideoCameraOutlined style={{ fontSize: 48, marginBottom: 16 }} />
    <div style={{ fontFamily: 'monospace' }}>REC ● LIVE_CAM_MAIN_{moment().format('HH:mm:ss')}</div>
    <div style={{ fontSize: 12, marginTop: 8, color: '#0f0' }}>信号强度: 极佳 (Latency: 24ms)</div>
  </div>

  {/* 右上角时间戳 */}
  <div style={{ position: 'absolute', top: 10, right: 10, color: '#fff', fontFamily: 'monospace' }}>
    {moment().format('YYYY-MM-DD HH:mm:ss')}
  </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 预警详情模态框 */}
      <Modal
        title="预警详情"
        open={alertDetailVisible}
        onCancel={() => setAlertDetailVisible(false)}
        footer={null}
        width={600}
      >
        {selectedAlert && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="时间">
              {moment(selectedAlert.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="类型">
              <Tag color={getAlertTypeColor(selectedAlert.log_type)}>
                {selectedAlert.log_type}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="模块">
              {selectedAlert.module}
            </Descriptions.Item>
            <Descriptions.Item label="消息">
              {selectedAlert.message}
            </Descriptions.Item>
            {selectedAlert.user_id && (
              <Descriptions.Item label="相关游客">
                ID: {selectedAlert.user_id}
                {selectedAlert.tourist_name && ` (${selectedAlert.tourist_name})`}
              </Descriptions.Item>
            )}
            <Descriptions.Item label="IP地址">
              {selectedAlert.ip_address || '未知'}
            </Descriptions.Item>
            <Descriptions.Item label="处理建议">
              {selectedAlert.log_type === 'warning' ? '请检查相关区域并进行疏导' :
               selectedAlert.log_type === 'security' ? '请立即检查安全状况' :
               selectedAlert.log_type === 'error' ? '请检查系统日志排查问题' :
               '无需特别处理'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default RealtimeMonitor;