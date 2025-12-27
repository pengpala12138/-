import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Layout, ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import './App.css';
import Header from './components/Header';
import Navigation from './components/Navigation';
import Footer from './components/Footer';
import Dashboard from './components/Dashboard';
import TouristManagement from './components/TouristManagement';
import ReservationManagement from './components/ReservationManagement';
import TrajectoryMonitoring from './components/TrajectoryMonitoring';
import FlowControl from './components/FlowControl';
import CheckIn from './components/CheckIn';
import RealtimeMonitor from './components/RealtimeMonitor';
import Statistics from './components/Statistics';
import SystemLogs from './components/SystemLogs';
import TouristService from "./components/TouristService";

const { Content } = Layout;

function App() {
  const [collapsed, setCollapsed] = useState(false);

  // 处理侧边栏折叠
  const handleCollapse = (collapsed) => {
    setCollapsed(collapsed);
  };

  // 处理侧边栏切换
  const toggleSidebar = () => {
    setCollapsed(!collapsed);
  };

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#0A5E38',
          borderRadius: 6,
        },
      }}
    >
      <Router>
        <Layout style={{ minHeight: '100vh' }}>
          <Navigation
            collapsed={collapsed}
            onCollapse={handleCollapse}
          />
          <Layout
            style={{
              marginLeft: collapsed ? 80 : 250,
              transition: 'margin-left 0.2s',
              minHeight: '100vh',
              background: '#f0f2f5',
            }}
          >
            <Header
              collapsed={collapsed}
              toggleSidebar={toggleSidebar}
            />
            <Content style={{
              margin: '24px 16px',
              padding: 0,
              overflow: 'initial',
            }}>
              <div style={{
                padding: 24,
                background: '#fff',
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
                minHeight: 'calc(100vh - 140px)',
              }}>
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/tourists" element={<TouristManagement />} />
                  <Route path="/reservations" element={<ReservationManagement />} />
                  <Route path="/trajectory" element={<TrajectoryMonitoring />} />
                  <Route path="/flow-control" element={<FlowControl />} />
                  <Route path="/check-in" element={<CheckIn />} />
                  <Route path="/realtime" element={<RealtimeMonitor />} />
                  <Route path="/statistics" element={<Statistics />} />
                  <Route path="/logs" element={<SystemLogs />} />
                  <Route path="/eco-service" element={<TouristService />} />
                </Routes>
              </div>
            </Content>
            <Footer />
          </Layout>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App;