import React, { useState } from 'react';
import { Layout, Menu, Avatar, Dropdown } from 'antd';
import {
  DashboardOutlined,
  UserOutlined,
  CalendarOutlined,
  RadarChartOutlined,
  ControlOutlined,
  CheckCircleOutlined,
  AreaChartOutlined,
  BarChartOutlined,
  FileTextOutlined,
  SettingOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined, EnvironmentOutlined
} from '@ant-design/icons';
import { Link, useLocation } from 'react-router-dom';

const { Sider } = Layout;

const Navigation = ({ collapsed, onCollapse }) => {
  const location = useLocation();

  // 用户菜单
  const userMenu = {
    items: [
      {
        key: 'profile',
        label: '个人中心',
      },
      {
        key: 'settings',
        label: '账号设置',
      },
      {
        type: 'divider',
      },
      {
        key: 'logout',
        label: '退出登录',
      },
    ],
  };

  // 获取当前选中的菜单项
  const getSelectedKey = () => {
    const path = location.pathname;
    if (path.includes('dashboard')) return 'dashboard';
    if (path.includes('tourists')) return 'tourists';
    if (path.includes('reservations')) return 'reservations';
    if (path.includes('trajectory')) return 'trajectory';
    if (path.includes('flow-control')) return 'flow-control';
    if (path.includes('check-in')) return 'check-in';
    if (path.includes('realtime')) return 'realtime';
    if (path.includes('statistics')) return 'statistics';
    if (path.includes('logs')) return 'logs';
    if (path.includes('eco-service')) return 'eco-service';
    return 'dashboard';
  };

  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: <Link to="/dashboard">仪表板</Link>,
    },
    {
      key: 'tourists',
      icon: <UserOutlined />,
      label: <Link to="/tourists">游客管理</Link>,
    },
    {
      key: 'reservations',
      icon: <CalendarOutlined />,
      label: <Link to="/reservations">预约管理</Link>,
    },
    {
      key: 'trajectory',
      icon: <RadarChartOutlined />,
      label: <Link to="/trajectory">轨迹监控</Link>,
    },
    {
      key: 'flow-control',
      icon: <ControlOutlined />,
      label: <Link to="/flow-control">流量管控</Link>,
    },
    {
      key: 'check-in',
      icon: <CheckCircleOutlined />,
      label: <Link to="/check-in">入园核验</Link>,
    },
    {
      key: 'realtime',
      icon: <AreaChartOutlined />,
      label: <Link to="/realtime">实时监控</Link>,
    },
    {
      key: 'statistics',
      icon: <BarChartOutlined />,
      label: <Link to="/statistics">数据统计</Link>,
    },
    {
      key: 'logs',
      icon: <FileTextOutlined />,
      label: <Link to="/logs">系统日志</Link>,
    },
{
    key: 'eco-service',
    icon: <EnvironmentOutlined />, // 使用叶子图标代表生态
    label: <Link to="/eco-service">生态监督</Link>,
  },
  ];

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={onCollapse}
      width={250}
      style={{
        overflow: 'auto',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
        zIndex: 1000,
        boxShadow: '2px 0 8px 0 rgba(29, 35, 41, 0.05)',
         backgroundColor: '#0A5E38',
      }}
    >
      <div style={{
        height: '64px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        padding: '0 16px'
      }}>
        <div style={{
          color: '#F5F5DC',
          fontSize: collapsed ? '14px' : '18px',
          fontWeight: 'bold',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          textAlign: 'center',
          flex: 1
        }}>
          {collapsed ? '智慧公园' : '智慧公园系统'}
        </div>
      </div>

      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[getSelectedKey()]}
        items={menuItems.map(item => ({
          ...item,
          label: React.cloneElement(item.label, {
            style: {
              color: '#F5F5DC', // 浅米色文字
            }
          })
        }))}
        style={{
          borderRight: 0,
          marginTop: '16px',
           backgroundColor: '#0A5E38', // 绿色背景
        }}
        onClick={({ item, key, keyPath, domEvent }) => {
          // 可选：点击菜单项时的自定义样式处理
        }}
      />

      {/* 用户信息 */}
      {!collapsed && (
        <div style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          padding: '16px',
          borderTop: '1px solid rgba(255, 255, 255, 0.1)'
        }}>
          <Dropdown menu={userMenu} trigger={['click']}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              transition: 'background 0.3s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            >
              <Avatar
                style={{
                  backgroundColor: '#1890ff',
                  marginRight: '12px',
                }}
                icon={<UserOutlined />}
              />
              <div style={{ flex: 1 }}>
                <div style={{ color: 'white', fontSize: '14px', fontWeight: 500 }}>管理员</div>
                <div style={{ color: '#F5F5DC', fontSize: '12px' }}>系统管理员</div>
              </div>
            </div>
          </Dropdown>
        </div>
      )}
    </Sider>
  );
};

export default Navigation;