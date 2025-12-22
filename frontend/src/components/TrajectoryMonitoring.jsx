import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Input,
  Select,
  Space,
  Tag,
  Row,
  Col,
  Statistic,
  Modal,
  Descriptions,
  message,
  Badge,
  Empty,
  List,
  Avatar,
  Timeline,
  Progress,
  Divider,
  Tooltip
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  RadarChartOutlined,
  EnvironmentOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  UserOutlined,
  RightCircleOutlined,
  LeftCircleOutlined,
  HistoryOutlined,
  AreaChartOutlined,
  GlobalOutlined
} from '@ant-design/icons';
import { getDataView, executeProcedure } from '../services/api';
import moment from 'moment';

const { Search } = Input;
const { Option } = Select;

const TrajectoryMonitoring = () => {
  const [trajectories, setTrajectories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filteredTrajectories, setFilteredTrajectories] = useState([]);
  const [selectedTrajectory, setSelectedTrajectory] = useState(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [filters, setFilters] = useState({
    area: 'all',
    status: 'all',
    search: ''
  });
  const [stats, setStats] = useState({
    total: 0,
    warning: 0,
    normal: 0,
    offline: 0
  });

  // 轨迹时间线视图状态
  const [timeView, setTimeView] = useState('latest'); // latest, day, week
  const [activeTrajectories, setActiveTrajectories] = useState([]);

  useEffect(() => {
    fetchTrajectories();
    const interval = setInterval(fetchTrajectories, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    filterTrajectories();
  }, [trajectories, filters]);

  useEffect(() => {
    // 根据时间视图过滤活跃轨迹
    let active = [...filteredTrajectories];

    if (timeView === 'latest') {
      // 显示最近30分钟的轨迹
      const thirtyMinutesAgo = moment().subtract(30, 'minutes');
      active = active.filter(t =>
        t.location_time && moment(t.location_time).isAfter(thirtyMinutesAgo)
      );
    } else if (timeView === 'day') {
      // 显示今天的数据
      const startOfDay = moment().startOf('day');
      active = active.filter(t =>
        t.location_time && moment(t.location_time).isAfter(startOfDay)
      );
    }

    setActiveTrajectories(active);
  }, [filteredTrajectories, timeView]);

  const fetchTrajectories = async () => {
    setLoading(true);
    try {
      console.log('开始获取轨迹数据...');
      const response = await fetch('http://172.20.10.7:5000/api/trajectories');
      const result = await response.json();
      console.log('轨迹API返回:', result);

      let trajectoryData = [];

      if (result && Array.isArray(result)) {
        trajectoryData = result;
      } else if (result && result.trajectories && Array.isArray(result.trajectories)) {
        trajectoryData = result.trajectories;
      } else {
        console.error('返回的数据格式不正确:', result);
        setTrajectories([]);
        setStats({
          total: 0,
          warning: 0,
          normal: 0,
          offline: 0
        });
        return;
      }

      const processedResult = trajectoryData.map(item => ({
        ...item,
        latitude: item.latitude ? Number(item.latitude) : null,
        longitude: item.longitude ? Number(item.longitude) : null,
        off_route: Boolean(item.off_route),
        // 生成简化的位置标签
        location_label: item.area_id || (item.latitude && item.longitude ?
          `(${Number(item.latitude).toFixed(2)}, ${Number(item.longitude).toFixed(2)})` : '未知位置')
      }));

      // 按时间排序，最新的在前
      processedResult.sort((a, b) => {
        if (!a.location_time || !b.location_time) return 0;
        return moment(b.location_time).valueOf() - moment(a.location_time).valueOf();
      });

      setTrajectories(processedResult);

      const stats = {
        total: processedResult.length,
        warning: processedResult.filter(t => t.off_route === true || t.area_status !== 'normal').length,
        normal: processedResult.filter(t => t.off_route === false && t.area_status === 'normal').length,
        offline: processedResult.filter(t => t.device_status === 'offline').length || 0
      };
      setStats(stats);

    } catch (error) {
      console.error('获取轨迹数据失败:', error);
      message.error('获取轨迹数据失败');
      setTrajectories([]);
    } finally {
      setLoading(false);
    }
  };

  const filterTrajectories = () => {
    let filtered = [...trajectories];

    if (filters.area !== 'all') {
      filtered = filtered.filter(t => t.area_id === filters.area);
    }

    if (filters.status !== 'all') {
      if (filters.status === 'warning') {
        filtered = filtered.filter(t => t.off_route === true || t.area_status !== 'normal');
      } else if (filters.status === 'normal') {
        filtered = filtered.filter(t => t.off_route === false && t.area_status === 'normal');
      }
    }

    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      filtered = filtered.filter(t =>
        (t.tourist_id && t.tourist_id.toLowerCase().includes(searchTerm)) ||
        (t.name && t.name.toLowerCase().includes(searchTerm)) ||
        (t.area_id && t.area_id.toLowerCase().includes(searchTerm))
      );
    }

    setFilteredTrajectories(filtered);
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleViewDetail = (record) => {
    setSelectedTrajectory(record);
    setDetailVisible(true);
  };

  const handleSimulateTrajectory = async () => {
    try {
      message.loading({ content: '正在生成模拟轨迹数据...', key: 'simulate' });
      await executeProcedure('simulate-trajectory-data', { minutes: 60 });
      message.success({ content: '轨迹数据模拟完成', key: 'simulate' });
      fetchTrajectories();
    } catch (error) {
      console.error('模拟轨迹失败:', error);
      message.error({ content: '模拟失败: ' + (error.message || '未知错误'), key: 'simulate' });
    }
  };

  const handleRefresh = () => {
    fetchTrajectories();
  };

  // 获取状态颜色
  const getStatusColor = (record) => {
    if (record.off_route === true) return '#ff4d4f';
    if (record.area_status === 'warning') return '#faad14';
    if (record.area_status === 'restricted') return '#ff4d4f';
    return '#52c41a';
  };

  // 获取状态文本
  const getStatusText = (record) => {
    if (record.off_route === true) return '异常';
    if (record.area_status === 'warning') return '预警';
    if (record.area_status === 'restricted') return '限流';
    return '正常';
  };

  // 获取状态图标
  const getStatusIcon = (record) => {
    if (record.off_route === true) return <ExclamationCircleOutlined />;
    if (record.area_status === 'warning') return <WarningOutlined />;
    return <EnvironmentOutlined />;
  };

  // 格式化时间
  const formatTime = (time) => {
    if (!time) return '未知时间';
    const m = moment(time);
    const now = moment();
    const diffMinutes = now.diff(m, 'minutes');

    if (diffMinutes < 1) return '刚刚';
    if (diffMinutes < 60) return `${diffMinutes}分钟前`;
    if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)}小时前`;
    if (now.isSame(m, 'day')) return '今天';
    if (now.subtract(1, 'day').isSame(m, 'day')) return '昨天';
    return m.format('MM-DD HH:mm');
  };

  const columns = [
    {
      title: '轨迹ID',
      dataIndex: 'trajectory_id',
      key: 'trajectory_id',
      width: 100,
      render: (text) => text || '-'
    },
    {
      title: '游客信息',
      key: 'tourist_info',
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.name || '未知'}</div>
          <div style={{ color: '#666', fontSize: 12 }}>
            ID: {record.tourist_id || '-'}
          </div>
        </div>
      ),
    },
    {
      title: '位置',
      key: 'location',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <div>
            <EnvironmentOutlined style={{ marginRight: 8, color: '#666' }} />
            {record.area_id || '未知区域'}
          </div>
          {record.latitude && record.longitude && (
            <div style={{ color: '#999', fontSize: 12 }}>
              {Number(record.latitude).toFixed(4)}, {Number(record.longitude).toFixed(4)}
            </div>
          )}
        </Space>
      ),
    },
    {
      title: '时间',
      dataIndex: 'location_time',
      key: 'time',
      render: (text) => (
        <Space>
          <ClockCircleOutlined />
          {formatTime(text)}
          {text && (
            <div style={{ color: '#999', fontSize: 12 }}>
              {moment(text).format('HH:mm')}
            </div>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_, record) => {
        const color = getStatusColor(record);
        const text = getStatusText(record);
        const icon = getStatusIcon(record);

        return (
          <Tag color={color} icon={icon}>
            {text}
          </Tag>
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => handleViewDetail(record)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>轨迹监控</h2>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总轨迹数"
              value={stats.total}
              prefix={<RadarChartOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="异常轨迹"
              value={stats.warning}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="正常轨迹"
              value={stats.normal}
              prefix={<EnvironmentOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="离线设备"
              value={stats.offline}
              prefix={<EnvironmentOutlined />}
              valueStyle={{ color: '#666' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 主内容区域 */}
      <Row gutter={[16, 16]}>
        {/* 左侧：轨迹列表 */}
        <Col xs={24} lg={16}>
          <Card
            title="轨迹监控面板"
            extra={
              <Space>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={handleRefresh}
                  loading={loading}
                >
                  刷新
                </Button>
                <Button
                  type="primary"
                  icon={<RadarChartOutlined />}
                  onClick={handleSimulateTrajectory}
                  disabled={loading}
                >
                  模拟轨迹
                </Button>
              </Space>
            }
            style={{ marginBottom: 16, height: '100%' }}
          >
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Search
                  placeholder="搜索游客ID、姓名或区域"
                  allowClear
                  onSearch={(value) => handleFilterChange('search', value)}
                  style={{ width: 300 }}
                  enterButton={<SearchOutlined />}
                />
                <Select
                  placeholder="区域筛选"
                  style={{ width: 120 }}
                  value={filters.area}
                  onChange={(value) => handleFilterChange('area', value)}
                >
                  <Option value="all">全部区域</Option>
                  <Option value="R001">A区</Option>
                  <Option value="R002">B区</Option>
                  <Option value="R003">C区</Option>
                  <Option value="R004">D区</Option>
                </Select>
                <Select
                  placeholder="状态筛选"
                  style={{ width: 120 }}
                  value={filters.status}
                  onChange={(value) => handleFilterChange('status', value)}
                >
                  <Option value="all">全部状态</Option>
                  <Option value="normal">正常</Option>
                  <Option value="warning">异常</Option>
                </Select>
              </Space>
            </div>

            {filteredTrajectories.length === 0 ? (
              <Empty
                description={loading ? "加载中..." : "暂无轨迹数据"}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                style={{ padding: '40px 0' }}
              />
            ) : (
              <Table
                columns={columns}
                dataSource={filteredTrajectories}
                rowKey="trajectory_id"
                loading={loading}
                pagination={{
                  pageSize: 10,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total) => `共 ${total} 条轨迹`
                }}
                scroll={{ x: 1200 }}
              />
            )}
          </Card>
        </Col>

        {/* 右侧：轨迹概览和时间线 */}
        <Col xs={24} lg={8}>
          {/* 活跃轨迹卡片 */}
          <Card
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>活跃轨迹</span>
                <Select
                  size="small"
                  style={{ width: 100 }}
                  value={timeView}
                  onChange={setTimeView}
                >
                  <Option value="latest">最近30分钟</Option>
                  <Option value="day">今天</Option>
                  <Option value="week">本周</Option>
                </Select>
              </div>
            }
            style={{ marginBottom: 16 }}
          >
            {activeTrajectories.length === 0 ? (
              <Empty
                description="暂无活跃轨迹"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                style={{ padding: '20px 0' }}
              />
            ) : (
              <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                <Timeline mode="left">
                  {activeTrajectories.slice(0, 10).map((trajectory, index) => (
                    <Timeline.Item
                      key={trajectory.trajectory_id || index}
                      color={getStatusColor(trajectory)}
                      label={
                        <div style={{ fontSize: 12, color: '#999' }}>
                          {formatTime(trajectory.location_time)}
                        </div>
                      }
                    >
                      <div
                        style={{
                          cursor: 'pointer',
                          padding: '4px 8px',
                          borderRadius: 4,
                          transition: 'background 0.3s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = '#f5f5f5'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        onClick={() => handleViewDetail(trajectory)}
                      >
                        <div style={{ fontWeight: 500, fontSize: 14 }}>
                          <Avatar
                            size="small"
                            icon={<UserOutlined />}
                            style={{ marginRight: 8, background: getStatusColor(trajectory) }}
                          />
                          {trajectory.name || '未知游客'}
                        </div>
                        <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
                          <Space size={8}>
                            <span>{trajectory.area_id || '未知区域'}</span>
                            <Tag size="small" color={getStatusColor(trajectory)}>
                              {getStatusText(trajectory)}
                            </Tag>
                          </Space>
                        </div>
                      </div>
                    </Timeline.Item>
                  ))}
                </Timeline>
              </div>
            )}
          </Card>

          {/* 轨迹统计卡片 */}
          <Card title="轨迹统计" style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <div style={{ fontSize: 14, color: '#666', marginBottom: 4 }}>轨迹分布</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Progress
                    percent={stats.total > 0 ? Math.round((stats.normal / stats.total) * 100) : 0}
                    strokeColor="#52c41a"
                    size="small"
                    showInfo={false}
                    style={{ flex: 1 }}
                  />
                  <div style={{ fontSize: 12, color: '#52c41a' }}>
                    正常 {stats.normal}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                  <Progress
                    percent={stats.total > 0 ? Math.round((stats.warning / stats.total) * 100) : 0}
                    strokeColor="#faad14"
                    size="small"
                    showInfo={false}
                    style={{ flex: 1 }}
                  />
                  <div style={{ fontSize: 12, color: '#faad14' }}>
                    异常 {stats.warning}
                  </div>
                </div>
              </div>

              <Divider style={{ margin: '12px 0' }} />

              <div>
                <div style={{ fontSize: 14, color: '#666', marginBottom: 8 }}>区域统计</div>
                <Row gutter={[8, 8]}>
                  {['A001', 'A002', 'A003', 'A004'].map(area => {
                    const areaTrajectories = filteredTrajectories.filter(t => t.area_id === area);
                    const warningCount = areaTrajectories.filter(t =>
                      t.off_route === true || t.area_status !== 'normal'
                    ).length;

                    return (
                      <Col span={12} key={area}>
                        <div style={{
                          background: '#fafafa',
                          padding: '8px 12px',
                          borderRadius: 6,
                          border: '1px solid #f0f0f0'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span style={{ fontSize: 12, color: '#666' }}>{area}</span>
                            <Badge
                              count={areaTrajectories.length}
                              style={{ backgroundColor: warningCount > 0 ? '#faad14' : '#52c41a' }}
                            />
                          </div>
                          {warningCount > 0 && (
                            <div style={{ fontSize: 10, color: '#faad14', marginTop: 4 }}>
                              异常: {warningCount}
                            </div>
                          )}
                        </div>
                      </Col>
                    );
                  })}
                </Row>
              </div>
            </Space>
          </Card>

          {/* 快速操作卡片 */}
          <Card title="快速操作">
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <Button
                  type="primary"
                  block
                  icon={<ReloadOutlined />}
                  onClick={handleRefresh}
                  loading={loading}
                  style={{ height: 40 }}
                >
                  刷新数据
                </Button>
              </Col>
              <Col span={12}>
                <Button
                  type="default"
                  block
                  icon={<RadarChartOutlined />}
                  onClick={handleSimulateTrajectory}
                  disabled={loading}
                  style={{ height: 40 }}
                >
                  模拟轨迹
                </Button>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* 轨迹详情模态框 */}
      <Modal
        title="轨迹详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={600}
      >
        {selectedTrajectory && (
          <div>
            <div style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
                <Avatar
                  size={48}
                  icon={<UserOutlined />}
                  style={{
                    marginRight: 16,
                    background: getStatusColor(selectedTrajectory),
                    fontSize: 24
                  }}
                />
                <div>
                  <div style={{ fontSize: 18, fontWeight: 500, marginBottom: 4 }}>
                    {selectedTrajectory.name || '未知游客'}
                  </div>
                  <div style={{ fontSize: 14, color: '#666' }}>
                    ID: {selectedTrajectory.tourist_id || '-'}
                  </div>
                </div>
              </div>
            </div>

            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="游客信息">
                <div style={{ lineHeight: 1.6 }}>
                  <div>姓名：{selectedTrajectory.name || '未知'}</div>
                  <div>电话：{selectedTrajectory.phone || '-'}</div>
                  <div>ID：{selectedTrajectory.tourist_id || '-'}</div>
                </div>
              </Descriptions.Item>

              <Descriptions.Item label="位置信息">
                <div style={{ lineHeight: 1.6 }}>
                  <div>区域：{selectedTrajectory.area_id || '未知'}</div>
                  <div>经纬度：{selectedTrajectory.latitude && selectedTrajectory.longitude
                    ? `${Number(selectedTrajectory.latitude).toFixed(6)}, ${Number(selectedTrajectory.longitude).toFixed(6)}`
                    : '未知'}
                  </div>
                </div>
              </Descriptions.Item>

              <Descriptions.Item label="时间信息">
                <div style={{ lineHeight: 1.6 }}>
                  <div>记录时间：{selectedTrajectory.location_time
                    ? moment(selectedTrajectory.location_time).format('YYYY-MM-DD HH:mm:ss')
                    : '-'}
                  </div>
                  <div>更新状态：{formatTime(selectedTrajectory.location_time)}</div>
                </div>
              </Descriptions.Item>

              <Descriptions.Item label="轨迹状态">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Tag
                    color={getStatusColor(selectedTrajectory)}
                    style={{ fontSize: 14, padding: '4px 8px' }}
                  >
                    {getStatusIcon(selectedTrajectory)} {getStatusText(selectedTrajectory)}
                  </Tag>
                  {selectedTrajectory.off_route === true && (
                    <Badge status="error" text="超出规定路线" />
                  )}
                  {selectedTrajectory.area_status === 'warning' && (
                    <Badge status="warning" text="处于预警区域" />
                  )}
                </div>
              </Descriptions.Item>
            </Descriptions>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TrajectoryMonitoring;