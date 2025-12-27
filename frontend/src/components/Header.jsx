import React from 'react';
import { Layout, Breadcrumb, Button, Space, Tooltip } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BellOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  QuestionCircleOutlined,
  GlobalOutlined
} from '@ant-design/icons';

const { Header } = Layout;

const CustomHeader = ({ collapsed, toggleSidebar }) => {
  const [fullscreen, setFullscreen] = React.useState(false);

  // 处理全屏切换
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => {
        setFullscreen(true);
      });
    } else {
      document.exitFullscreen().then(() => {
        setFullscreen(false);
      });
    }
  };

  // 处理通知
  const handleNotification = () => {
    console.log('显示通知');
  };

  // 处理帮助
  const handleHelp = () => {
    console.log('显示帮助');
  };

  return (
    <Header style={{
      padding: '0 24px',
      background: '#fff',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      boxShadow: '0 1px 4px rgba(0,21,41,0.08)',
      position: 'sticky',
      top: 0,
      zIndex: 999,
      height: '64px',
      lineHeight: '64px',
    }}>
      <Space>
        <Button
          type="text"
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={toggleSidebar}
          style={{
            fontSize: '16px',
            width: '64px',
            height: '64px',
            color: '#00a65a'
          }}
        />
        <Breadcrumb style={{ lineHeight: '64px' }}>
          <Breadcrumb.Item>首页</Breadcrumb.Item>
          <Breadcrumb.Item>仪表板</Breadcrumb.Item>
        </Breadcrumb>
      </Space>

      <Space size="middle">
        <div style={{ fontSize: '14px', color: '#666' }}>
          系统时间：{new Date().toLocaleString()}
        </div>

        <Tooltip title="通知">
          <Button
            type="text"
            icon={<BellOutlined />}
            onClick={handleNotification}
            style={{ fontSize: '16px' }}
          />
        </Tooltip>

        <Tooltip title={fullscreen ? '退出全屏' : '全屏'}>
          <Button
            type="text"
            icon={fullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            onClick={toggleFullscreen}
            style={{ fontSize: '16px' }}
          />
        </Tooltip>

        <Tooltip title="语言">
          <Button
            type="text"
            icon={<GlobalOutlined />}
            style={{ fontSize: '16px' }}
          />
        </Tooltip>

        <Tooltip title="帮助">
          <Button
            type="text"
            icon={<QuestionCircleOutlined />}
            onClick={handleHelp}
            style={{ fontSize: '16px' }}
          />
        </Tooltip>
      </Space>
    </Header>
  );
};

export default CustomHeader;