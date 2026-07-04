import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Dropdown, theme, Typography } from 'antd';
import {
  DashboardOutlined,
  VideoCameraOutlined,
  UnorderedListOutlined,
  SettingOutlined,
  DollarOutlined,
  KeyOutlined,
  TranslationOutlined,
  SearchOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  GlobalOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/authStore';
import { useUIStore } from '../../stores/uiStore';
import type { MenuProps } from 'antd';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

export default function AppLayout() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const { collapsed, toggleCollapsed } = useUIStore();
  const { token } = theme.useToken();

  const menuItems: MenuProps['items'] = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: t('nav.dashboard') },
    { key: '/meetings/upload', icon: <VideoCameraOutlined />, label: t('nav.meetings') },
    { key: '/tasks', icon: <UnorderedListOutlined />, label: t('nav.tasks') },
    { key: '/models', icon: <SettingOutlined />, label: t('nav.models') },
    { key: '/token-usage', icon: <DollarOutlined />, label: t('nav.tokenUsage') },
    { key: '/api-keys', icon: <KeyOutlined />, label: t('nav.apiKeys') },
    { key: '/search', icon: <SearchOutlined />, label: t('nav.search') },
  ];

  const langItems: MenuProps['items'] = [
    { key: 'zh-CN', label: '中文' },
    { key: 'en-US', label: 'English' },
    { key: 'ja-JP', label: '日本語' },
  ];

  const handleLangChange: MenuProps['onClick'] = ({ key }) => {
    i18n.changeLanguage(key);
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="dark"
        style={{ borderRight: `1px solid ${token.colorBorderSecondary}` }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 700,
            fontSize: collapsed ? 16 : 20,
            letterSpacing: 1,
          }}
        >
          {collapsed ? 'MS' : t('app.title')}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: token.colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={toggleCollapsed}
          />
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <Dropdown menu={{ items: langItems, onClick: handleLangChange }}>
              <Button icon={<GlobalOutlined />}>
                {i18n.language === 'zh-CN' ? '中文' : i18n.language === 'ja-JP' ? '日本語' : 'EN'}
              </Button>
            </Dropdown>
            <Button icon={<UserOutlined />} />
            <Button icon={<LogoutOutlined />} onClick={logout} danger>
              {t('common.logout', '退出')}
            </Button>
          </div>
        </Header>
        <Content
          style={{
            margin: 24,
            padding: 24,
            background: token.colorBgContainer,
            borderRadius: 8,
            minHeight: 280,
            overflow: 'auto',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
