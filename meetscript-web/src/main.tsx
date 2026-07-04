import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import 'antd/dist/reset.css';
import './i18n';
import App from './App';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30000, refetchOnWindowFocus: false },
  },
});

// MeetScript Design System - Ant Design Theme Token
const themeToken = {
  colorPrimary: '#0D9488',
  colorSuccess: '#10B981',
  colorWarning: '#F59E0B',
  colorError: '#DC2626',
  colorInfo: '#0D9488',
  borderRadius: 8,
  fontFamily: "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif",
  colorBgContainer: '#FFFFFF',
  colorBgLayout: '#F8FAFC',
  colorBorder: '#E2E8F0',
  colorText: '#1E293B',
  colorTextSecondary: '#64748B',
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN} theme={{ token: themeToken }}>
        <AntApp>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
