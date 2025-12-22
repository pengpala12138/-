import React from 'react';
import { Layout, Typography } from 'antd';

const { Footer: AntFooter } = Layout;
const { Text } = Typography;

const Footer = () => {
  return (
    <AntFooter style={{
      textAlign: 'center',
      padding: '16px 50px',
      background: '#f0f2f5'
    }}>
      <Text type="secondary">
        游客智能管理系统 © {new Date().getFullYear()} 版权所有
      </Text>
      <div style={{ marginTop: 8 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          技术支持：智能旅游管理团队 | 联系方式：support@tourist.com
        </Text>
      </div>
    </AntFooter>
  );
};

export default Footer;