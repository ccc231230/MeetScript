import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Dropdown, Typography, Avatar, Badge, Tooltip } from 'antd';
import {
  DashboardOutlined,
  VideoCameraOutlined,
  UnorderedListOutlined,
  SettingOutlined,
  DollarOutlined,
  KeyOutlined,
  SearchOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  GlobalOutlined,
  UserOutlined,
  TranslationOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/authStore';
import { useUIStore } from '../../stores/uiStore';
import type { MenuProps } from 'antd';

const { Sider, Content } = Layout;
const { Text } = Typography;

const BRAND_GRADIENT = 'linear-gradient(135deg, #0D9488 0%, #14B8A6 50%, #2DD4BF 100%)';

export default function AppLayout() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const username = useAuthStore((s) => s.username);
  const { collapsed, toggleCollapsed } = useUIStore();

  const menuItems: MenuProps['items'] = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: t('nav.dashboard') },
    { key: '/meetings/upload', icon: <VideoCameraOutlined />, label: t('nav.meetings') },
    { key: '/tasks', icon: <UnorderedListOutlined />, label: t('nav.tasks') },
    { key: '/search', icon: <SearchOutlined />, label: t('nav.search') },
    { type: 'divider' },
    { key: '/models', icon: <SettingOutlined />, label: t('nav.models') },
    { key: '/token-usage', icon: <DollarOutlined />, label: t('nav.tokenUsage') },
    { key: '/api-keys', icon: <KeyOutlined />, label: t('nav.apiKeys') },
  ];

  const langItems: MenuProps['items'] = [
    { key: 'zh-CN', label: '🇨🇳 中文' },
    { key: 'en-US', label: '🇺🇸 English' },
    { key: 'ja-JP', label: '🇯🇵 日本語' },
  ];

  const handleLangChange: MenuProps['onClick'] = ({ key }) => {
    i18n.changeLanguage(key);
  };

  const userMenuItems: MenuProps['items'] = [
    { key: 'profile', icon: <UserOutlined />, label: username || '用户' },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: t('common.logout', '退出登录'), danger: true },
  ];

  const handleUserMenu: MenuProps['onClick'] = ({ key }) => {
    if (key === 'logout') logout();
  };

  const selectedKey = '/' + location.pathname.split('/').filter(Boolean)[0] || '/dashboard';

  return (
    <div className="flex h-screen bg-slate-50">
      {/* ─── Sidebar ─── */}
      <aside
        className="flex flex-col h-full transition-all duration-300 ease-in-out bg-white border-r border-slate-200 shadow-sm"
        style={{ width: collapsed ? 72 : 240 }}
      >
        {/* Logo */}
        <div
          className="flex items-center h-16 px-4 gap-3 shrink-0 border-b border-slate-100"
          style={{ justifyContent: collapsed ? 'center' : 'flex-start' }}
        >
          <div
            className="flex items-center justify-center rounded-lg shrink-0"
            style={{
              width: 36, height: 36,
              background: BRAND_GRADIENT,
              boxShadow: '0 2px 8px rgba(13,148,136,0.3)',
            }}
          >
            <ThunderboltOutlined style={{ color: '#fff', fontSize: 18 }} />
          </div>
          {!collapsed && (
            <span className="text-lg font-bold text-slate-800 tracking-tight whitespace-nowrap">
              MeetScript
            </span>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-3">
          <Sider
            trigger={null}
            collapsible
            collapsed={collapsed}
            width={216}
            collapsedWidth={48}
            theme="light"
            style={{ background: 'transparent', border: 'none' }}
          >
            <Menu
              mode="inline"
              selectedKeys={[selectedKey]}
              items={menuItems}
              onClick={({ key }) => navigate(key)}
              style={{
                background: 'transparent',
                border: 'none',
                fontWeight: 500,
              }}
            />
          </Sider>
        </nav>

        {/* Collapse toggle */}
        <div className="p-3 border-t border-slate-100">
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={toggleCollapsed}
            className="w-full flex items-center justify-center text-slate-400 hover:text-slate-600"
            style={{ height: 40 }}
          />
        </div>
      </aside>

      {/* ─── Main Content ─── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between h-16 px-6 bg-white border-b border-slate-200 shrink-0">
          <div className="flex items-center gap-4">
            <Text className="text-slate-400 text-sm">
              {(() => {
                const parts = location.pathname.split('/').filter(Boolean);
                const labels: Record<string, string> = {
                  dashboard: '仪表盘',
                  meetings: '会议管理',
                  tasks: '任务管理',
                  search: '全局搜索',
                  models: '模型配置',
                  'token-usage': 'Token 用量',
                  'api-keys': 'API 密钥',
                  translations: '翻译查看',
                };
                if (parts.length >= 1 && labels[parts[0]]) {
                  return labels[parts[0]] + (parts.length > 1 ? ` / ${parts[1]}` : '');
                }
                return '';
              })()}
            </Text>
          </div>

          <div className="flex items-center gap-3">
            {/* Search shortcut */}
            <Tooltip title="全局搜索 Ctrl+K">
              <Button
                icon={<SearchOutlined />}
                onClick={() => navigate('/search')}
                className="flex items-center gap-2 text-slate-400 bg-slate-50 border-slate-200 hover:border-primary-300"
                style={{ borderRadius: 8 }}
              >
                <span className="text-xs text-slate-400">⌘K</span>
              </Button>
            </Tooltip>

            {/* Language switcher */}
            <Dropdown menu={{ items: langItems, onClick: handleLangChange }}>
              <Button
                icon={<GlobalOutlined />}
                type="text"
                className="text-slate-500 hover:text-primary-600"
              />
            </Dropdown>

            {/* User menu */}
            <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenu }}>
              <div className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 rounded-lg px-2 py-1 transition-colors">
                <Avatar
                  size={32}
                  icon={<UserOutlined />}
                  style={{ background: BRAND_GRADIENT }}
                />
                <span className="text-sm font-medium text-slate-700 hidden sm:inline">
                  {username || '用户'}
                </span>
              </div>
            </Dropdown>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6">
          <div className="animate-fade-in-up mx-auto" style={{ maxWidth: 1400 }}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

