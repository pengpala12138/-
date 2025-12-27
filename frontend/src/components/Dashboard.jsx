import React, { useState, useEffect, useMemo } from 'react';
import {
  Row, Col, Card, Statistic, Table, Tag, Progress, Alert,
  Typography, Space, Button, Timeline, Badge, List, Avatar,
  Tooltip, Empty, Divider
} from 'antd';
import {
  UserOutlined,
  CalendarOutlined,
  SafetyOutlined,
  DollarOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  RiseOutlined,
  FallOutlined,
  LineChartOutlined,
  BellOutlined,
  AreaChartOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  EnvironmentOutlined
} from '@ant-design/icons';
import { getStatistics, getRealtimeMonitor } from '../services/api';

const { Title, Text } = Typography;

const Dashboard = () => {
  const [stats, setStats] = useState({});
  const [realtimeData, setRealtimeData] = useState({
    alerts: [],
    flow_control: [],
    recent_alerts: []
  });
  const [loading, setLoading] = useState(true);
  const [activeAlert, setActiveAlert] = useState(null);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [statsData, realtimeData] = await Promise.all([
        getStatistics(),
        getRealtimeMonitor()
      ]);
      setStats(statsData.stats || {});
      setRealtimeData(realtimeData || {});
    } catch (error) {
      console.error('获取数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 1. 从现有数据计算今日趋势信息
  const todayTrends = useMemo(() => {
    if (!realtimeData.flow_control || realtimeData.flow_control.length === 0) {
      return {
        totalVisitors: 0,
        peakArea: null,
        peakVisitors: 0,
        averageUsage: 0,
        trends: []
      };
    }

    // 计算总游客数
    const totalVisitors = realtimeData.flow_control.reduce((sum, area) =>
      sum + (area.current_visitors || 0), 0
    );

    // 找到人数最多的区域
    const peakArea = realtimeData.flow_control.reduce((max, area) =>
      (area.current_visitors || 0) > (max.current_visitors || 0) ? area : max
    );

    // 计算平均使用率
    const averageUsage = realtimeData.flow_control.reduce((sum, area) => {
      const usage = (area.current_visitors || 0) / (area.daily_capacity || 1) * 100;
      return sum + usage;
    }, 0) / realtimeData.flow_control.length;

    // 生成趋势数据
    const trends = realtimeData.flow_control
      .sort((a, b) => (b.current_visitors || 0) - (a.current_visitors || 0))
      .slice(0, 5)
      .map(area => ({
        area: area.area_id,
        visitors: area.current_visitors || 0,
        capacity: area.daily_capacity || 0,
        usage: Math.round(((area.current_visitors || 0) / (area.daily_capacity || 1)) * 100),
        status: area.status || 'normal'
      }));

    return {
      totalVisitors,
      peakArea,
      peakVisitors: peakArea.current_visitors || 0,
      averageUsage: Math.round(averageUsage),
      trends
    };
  }, [realtimeData.flow_control]);

  // 2. 从预警数据计算统计信息
  const alertStats = useMemo(() => {
    if (!realtimeData.alerts || realtimeData.alerts.length === 0) {
      return {
        totalAlerts: 0,
        byLevel: {},
        byModule: {},
        recentCount: 0
      };
    }

    const alerts = realtimeData.alerts;

    // 按级别统计
    const byLevel = alerts.reduce((acc, alert) => {
      const level = alert.log_type || 'unknown';
      acc[level] = (acc[level] || 0) + 1;
      return acc;
    }, {});

    // 按模块统计
    const byModule = alerts.reduce((acc, alert) => {
      const module = alert.module || 'unknown';
      acc[module] = (acc[module] || 0) + 1;
      return acc;
    }, {});

    // 最近30分钟内的预警
    const thirtyMinutesAgo = new Date(Date.now() - 30 * 60 * 1000);
    const recentCount = alerts.filter(alert =>
      new Date(alert.created_at) > thirtyMinutesAgo
    ).length;

    return {
      totalAlerts: alerts.length,
      byLevel,
      byModule,
      recentCount
    };
  }, [realtimeData.alerts]);

  const statCards = [
    {
      title: '在园游客',
      value: stats.visitors_in_park || 0,
      icon: <UserOutlined />,
      color: '#1890ff',
      suffix: '人'
    },
    {
      title: '今日预约',
      value: stats.reservations_today || 0,
      icon: <CalendarOutlined />,
      color: '#52c41a',
      suffix: '单'
    },
    {
      title: '预警区域',
      value: stats.warning_areas || 0,
      icon: <WarningOutlined />,
      color: '#faad14',
      suffix: '个'
    },
    {
      title: '今日收入',
      value: `¥${(stats.revenue_today || 0).toLocaleString()}`,
      icon: <DollarOutlined />,
      color: '#722ed1'
    },
    {
      title: '总游客数',
      value: stats.total_visitors || 0,
      icon: <UserOutlined />,
      color: '#13c2c2',
      suffix: '人'
    },
    {
      title: '异常轨迹',
      value: stats.off_route_today || 0,
      icon: <SafetyOutlined />,
      color: '#f5222d',
      suffix: '条'
    }
  ];

  // 完善预警表格列
  const alertColumns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'time',
      width: 100,
      render: (text) => {
        const date = new Date(text);
        return (
          <Tooltip title={date.toLocaleString('zh-CN')}>
            <div style={{ fontSize: '12px' }}>
              <div>{date.toLocaleDateString('zh-CN')}</div>
              <div style={{ color: '#999' }}>
                {date.toLocaleTimeString('zh-CN', {
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </div>
            </div>
          </Tooltip>
        );
      }
    },
    {
      title: '模块/区域',
      dataIndex: 'module',
      key: 'module',
      width: 120,
      render: (module, record) => (
        <Space direction="vertical" size={2}>
          <Tag color="blue">{module || '系统'}</Tag>
          {record.area_id && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              <EnvironmentOutlined /> {record.area_id}
            </Text>
          )}
        </Space>
      )
    },
    {
      title: '预警信息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
      width: 200,
      render: (text, record) => {
        const isRecent = new Date(record.created_at) > new Date(Date.now() - 5 * 60 * 1000);
        return (
          <Space direction="vertical" size={2}>
            <Text
              strong={record.log_type === 'warning' || record.log_type === 'error'}
              style={{
                color: record.log_type === 'error' ? '#ff4d4f' :
                       record.log_type === 'warning' ? '#fa8c16' : '#1890ff',
                cursor: 'pointer'
              }}
              onClick={() => setActiveAlert(record)}
            >
              {isRecent && <Badge status="processing" />}
              {text}
            </Text>
            {record.description && (
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {record.description}
              </Text>
            )}
          </Space>
        );
      }
    },
    {
      title: '级别',
      dataIndex: 'log_type',
      key: 'type',
      width: 80,
      align: 'center',
      render: (type) => {
        const typeConfig = {
          error: {
            color: '#ff4d4f',
            text: '紧急',
            icon: <ExclamationCircleOutlined />
          },
          warning: {
            color: '#fa8c16',
            text: '预警',
            icon: <WarningOutlined />
          },
          security: {
            color: '#722ed1',
            text: '安全',
            icon: <SafetyOutlined />
          },
          info: {
            color: '#1890ff',
            text: '信息',
            icon: <InfoCircleOutlined />
          }
        };
        const config = typeConfig[type] || { color: '#d9d9d9', text: type };
        return (
          <Tag
            color={config.color}
            icon={config.icon}
            style={{ margin: 0, padding: '2px 8px' }}
          >
            {config.text}
          </Tag>
        );
      }
    },
    {
      title: '状态',
      key: 'status',
      width: 80,
      align: 'center',
      render: (_, record) => {
        // 根据创建时间判断状态
        const createTime = new Date(record.created_at);
        const now = new Date();
        const diffMinutes = (now - createTime) / (1000 * 60);

        let status = '已处理';
        let color = 'success';

        if (diffMinutes < 5) {
          status = '新预警';
          color = 'error';
        } else if (diffMinutes < 30) {
          status = '处理中';
          color = 'processing';
        }

        return <Badge status={color} text={status} />;
      }
    }
  ];

  // 完善区域表格列
  const areaColumns = [
    {
      title: '区域',
      dataIndex: 'area_id',
      key: 'area',
      width: 100,
      render: (areaId) => (
        <Space>
          <EnvironmentOutlined />
          <Text strong>{areaId}</Text>
        </Space>
      )
    },
    {
      title: '当前人数',
      dataIndex: 'current_visitors',
      key: 'visitors',
      width: 100,
      render: (visitors) => (
        <Text strong style={{ fontSize: '16px' }}>{visitors || 0}</Text>
      ),
      sorter: (a, b) => (a.current_visitors || 0) - (b.current_visitors || 0),
      defaultSortOrder: 'descend'
    },
    {
      title: '承载量',
      dataIndex: 'daily_capacity',
      key: 'capacity',
      width: 100,
      render: (capacity) => (
        <Text type="secondary">{capacity || 0}</Text>
      )
    },
    {
      title: '使用率',
      key: 'usage',
      width: 150,
      render: (_, record) => {
        const usage = ((record.current_visitors || 0) / (record.daily_capacity || 1)) * 100;
        const percent = Math.round(usage);

        let status = 'normal';
        if (percent >= 90) status = 'exception';
        else if (percent >= 70) status = 'active';

        return (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Progress
              percent={percent}
              size="small"
              status={status}
              strokeColor={percent >= 90 ? '#ff4d4f' : percent >= 70 ? '#faad14' : '#52c41a'}
            />
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {percent}%
            </Text>
          </Space>
        );
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const statusMap = {
          normal: { color: 'green', text: '正常', icon: <CheckCircleOutlined /> },
          warning: { color: 'orange', text: '预警', icon: <WarningOutlined /> },
          restricted: { color: 'red', text: '限流', icon: <ExclamationCircleOutlined /> }
        };
        const statusInfo = statusMap[status] || { color: 'default', text: status, icon: <InfoCircleOutlined /> };
        return (
          <Tag color={statusInfo.color} icon={statusInfo.icon}>
            {statusInfo.text}
          </Tag>
        );
      }
    }
  ];

  // 今日趋势统计卡片
  const trendCards = [
    {
      title: '当前在园总人数',
      value: todayTrends.totalVisitors,
      icon: <UserOutlined />,
      color: '#1890ff',
      suffix: '人',
      description: `分布于${realtimeData.flow_control?.length || 0}个区域`
    },
    {
      title: '最繁忙区域',
      value: todayTrends.peakArea?.area_id || '暂无',
      icon: <EnvironmentOutlined />,
      color: '#ff4d4f',
      suffix: todayTrends.peakVisitors > 0 ? ` (${todayTrends.peakVisitors}人)` : '',
      description: todayTrends.peakArea?.status === 'restricted' ? '已限流' :
                   todayTrends.peakArea?.status === 'warning' ? '预警中' : '运行正常'
    },
    {
      title: '平均使用率',
      value: todayTrends.averageUsage,
      icon: <AreaChartOutlined />,
      color: '#52c41a',
      suffix: '%',
      description: todayTrends.averageUsage >= 90 ? '负荷较高' :
                   todayTrends.averageUsage >= 70 ? '中等负荷' : '运行良好'
    },
    {
      title: '当前预警数',
      value: alertStats.totalAlerts,
      icon: <BellOutlined />,
      color: '#faad14',
      suffix: '个',
      description: `近30分钟: ${alertStats.recentCount}个`
    }
  ];

  return (
    <div>
      <Title level={2} style={{ marginBottom: 24 }}>智慧景区监控系统</Title>

      {/* 主要统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {statCards.map((card, index) => (
          <Col xs={24} sm={12} md={8} lg={6} xl={4} key={index}>
            <Card loading={loading} hoverable>
              <Statistic
                title={card.title}
                value={card.value}
                prefix={card.icon}
                suffix={card.suffix}
                valueStyle={{
                  color: card.color,
                  fontSize: '24px'
                }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* 今日趋势概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24}>
          <Card
            title={
              <Space>
                <LineChartOutlined />
                <span>今日趋势概览</span>
              </Space>
            }
            extra={
              <Text type="secondary">
                更新时间: {new Date().toLocaleTimeString('zh-CN')}
              </Text>
            }
            loading={loading}
          >
            {/* 趋势统计卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              {trendCards.map((card, index) => (
                <Col xs={24} sm={12} md={6} key={index}>
                  <Card size="small" hoverable>
                    <Statistic
                      title={card.title}
                      value={card.value}
                      prefix={card.icon}
                      suffix={card.suffix}
                      valueStyle={{
                        color: card.color,
                        fontSize: '20px'
                      }}
                    />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {card.description}
                    </Text>
                  </Card>
                </Col>
              ))}
            </Row>

            {/* 区域热门排行 */}
            {todayTrends.trends.length > 0 ? (
              <>
                <Divider orientation="left">区域热度排行</Divider>
                <Row gutter={[16, 16]}>
                  {todayTrends.trends.map((trend, index) => (
                    <Col xs={24} sm={12} md={8} lg={4.8} key={index}>
                      <Card
                        size="small"
                        style={{
                          borderLeft: `4px solid ${
                            trend.status === 'restricted' ? '#ff4d4f' : 
                            trend.status === 'warning' ? '#faad14' : '#52c41a'
                          }`
                        }}
                      >
                        <div style={{ textAlign: 'center' }}>
                          <Text strong style={{ fontSize: '16px', display: 'block' }}>
                            {trend.area}
                          </Text>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {index + 1}. {trend.visitors}人 / {trend.capacity}人
                          </Text>
                          <Progress
                            percent={trend.usage}
                            size="small"
                            style={{ marginTop: 8 }}
                            strokeColor={trend.usage >= 90 ? '#ff4d4f' : trend.usage >= 70 ? '#faad14' : '#52c41a'}
                          />
                        </div>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </>
            ) : (
              <Alert
                message="暂无趋势数据"
                description="请确保区域流量数据已正确加载"
                type="info"
                showIcon
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* 实时监控数据 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <BellOutlined />
                <span>实时预警监控</span>
                {alertStats.totalAlerts > 0 && (
                  <Badge count={alertStats.totalAlerts} style={{ backgroundColor: '#ff4d4f' }} />
                )}
              </Space>
            }
            extra={
              <Button type="link" size="small" href="/logs">
                查看更多
              </Button>
            }
            loading={loading}
          >
            {realtimeData.alerts?.length > 0 ? (
              <>
                {/* 预警统计信息 */}
                <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
                  {Object.entries(alertStats.byLevel).map(([level, count]) => (
                    <Col key={level}>
                      <Tag
                        color={
                          level === 'error' ? 'red' :
                          level === 'warning' ? 'orange' :
                          level === 'security' ? 'purple' : 'blue'
                        }
                      >
                        {level}: {count}
                      </Tag>
                    </Col>
                  ))}
                </Row>

                <Table
                  columns={alertColumns}
                  dataSource={realtimeData.alerts.slice(0, 5)}
                  size="small"
                  pagination={false}
                  rowKey="log_id"
                  scroll={{ x: 600 }}
                  onRow={(record) => ({
                    onClick: () => setActiveAlert(record),
                    style: {
                      cursor: 'pointer',
                      backgroundColor: new Date(record.created_at) > new Date(Date.now() - 5 * 60 * 1000)
                        ? '#fff2e8'
                        : 'inherit'
                    }
                  })}
                />

                {/* 最近预警时间线 */}
                {alertStats.recentCount > 0 && (
                  <Card size="small" title="最近预警时间线" style={{ marginTop: 16 }}>
                    <Timeline mode="left">
                      {realtimeData.alerts
                        .filter(alert => new Date(alert.created_at) > new Date(Date.now() - 30 * 60 * 1000))
                        .slice(0, 3)
                        .map((alert, index) => (
                          <Timeline.Item
                            key={index}
                            color={
                              alert.log_type === 'error' ? 'red' :
                              alert.log_type === 'warning' ? 'orange' : 'blue'
                            }
                          >
                            <Space direction="vertical" size={2}>
                              <Text>{new Date(alert.created_at).toLocaleTimeString('zh-CN')}</Text>
                              <Text type="secondary">{alert.message}</Text>
                            </Space>
                          </Timeline.Item>
                        ))}
                    </Timeline>
                  </Card>
                )}
              </>
            ) : (
              <Alert
                message="当前无预警信息"
                description="系统运行正常，暂无预警需要处理。"
                type="success"
                showIcon
                icon={<CheckCircleOutlined />}
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <EnvironmentOutlined />
                <span>区域流量监控</span>
              </Space>
            }
            extra={
              <Button type="link" size="small" href="/flow-control">
                查看更多
              </Button>
            }
            loading={loading}
          >
            {realtimeData.flow_control?.length > 0 ? (
              <>
                <Table
                  columns={areaColumns}
                  dataSource={realtimeData.flow_control}
                  size="small"
                  pagination={false}
                  rowKey="area_id"
                  scroll={{ x: 600 }}
                />

                {/* 区域状态统计 */}
                <Row gutter={[8, 8]} style={{ marginTop: 16 }}>
                  <Col span={8}>
                    <Statistic
                      title="正常区域"
                      value={realtimeData.flow_control.filter(a => a.status === 'normal').length}
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="预警区域"
                      value={realtimeData.flow_control.filter(a => a.status === 'warning').length}
                      valueStyle={{ color: '#faad14' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="限流区域"
                      value={realtimeData.flow_control.filter(a => a.status === 'restricted').length}
                      valueStyle={{ color: '#ff4d4f' }}
                    />
                  </Col>
                </Row>
              </>
            ) : (
              <Alert message="暂无流量数据" type="info" showIcon />
            )}
          </Card>
        </Col>
      </Row>

      {/* 预警详情面板 */}
      {activeAlert && (
        <Card
          title="预警详情"
          style={{ marginTop: 16 }}
          extra={
            <Button type="link" onClick={() => setActiveAlert(null)}>
              关闭
            </Button>
          }
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Row gutter={[16, 8]}>
              <Col span={12}>
                <Text strong>发生时间: </Text>
                <Text>{new Date(activeAlert.created_at).toLocaleString('zh-CN')}</Text>
              </Col>
              <Col span={12}>
                <Text strong>预警级别: </Text>
                <Tag
                  color={activeAlert.log_type === 'error' ? 'red' :
                         activeAlert.log_type === 'warning' ? 'orange' : 'blue'}
                >
                  {activeAlert.log_type}
                </Tag>
              </Col>
              <Col span={12}>
                <Text strong>所属模块: </Text>
                <Text>{activeAlert.module || '系统'}</Text>
              </Col>
              <Col span={12}>
                <Text strong>相关区域: </Text>
                <Text>{activeAlert.area_id || '未指定'}</Text>
              </Col>
              <Col span={24}>
                <Text strong>预警内容: </Text>
                <Text>{activeAlert.message}</Text>
              </Col>
              {activeAlert.description && (
                <Col span={24}>
                  <Text strong>详细描述: </Text>
                  <Text>{activeAlert.description}</Text>
                </Col>
              )}
            </Row>
            <Divider />
            <Text type="secondary" style={{ fontSize: '12px' }}>
              <ClockCircleOutlined />
              此预警产生于 {Math.round((new Date() - new Date(activeAlert.created_at)) / 60000)} 分钟前
            </Text>
          </Space>
        </Card>
      )}
    </div>
  );
};

export default Dashboard;