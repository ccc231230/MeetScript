import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Typography, App } from 'antd';
import { UserOutlined, LockOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { authAPI } from '../../api/auth';
import { useAuthStore } from '../../stores/authStore';

const { Title, Text } = Typography;

const BRAND_GRADIENT = 'linear-gradient(135deg, #0D9488 0%, #14B8A6 40%, #2DD4BF 100%)';

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      const { data } = await authAPI.login(values);
      setAuth(data.access_token, data.refresh_token, data.user_id || values.username, data.role);
      message.success('登录成功');
      navigate('/dashboard');
    } catch {
      message.error('用户名或密码错误');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left: Brand Panel */}
      <div
        className="hidden lg:flex flex-col justify-between w-1/2 relative overflow-hidden"
        style={{ background: BRAND_GRADIENT }}
      >
        {/* Animated background pattern */}
        <div className="absolute inset-0 opacity-10">
          <div
            className="absolute rounded-full"
            style={{
              width: 600, height: 600,
              background: 'white',
              top: '-200px', right: '-200px',
            }}
          />
          <div
            className="absolute rounded-full"
            style={{
              width: 400, height: 400,
              background: 'white',
              bottom: '-100px', left: '-100px',
            }}
          />
        </div>

        <div className="relative z-10 p-16 flex-1 flex flex-col justify-center">
          <div className="flex items-center gap-4 mb-8">
            <div
              className="flex items-center justify-center rounded-2xl"
              style={{
                width: 56, height: 56,
                background: 'rgba(255,255,255,0.2)',
                backdropFilter: 'blur(10px)',
              }}
            >
              <ThunderboltOutlined style={{ color: '#fff', fontSize: 28 }} />
            </div>
            <Title level={1} style={{ color: '#fff', margin: 0, fontSize: 40, fontWeight: 800 }}>
              MeetScript
            </Title>
          </div>
          <Text className="text-white/80 text-lg leading-relaxed max-w-md">
            {t('app.title', '智能会议纪要平台')} — 基于 AI 的会议录制转写、翻译与纪要生成，让每一次会议都有迹可循。
          </Text>

          {/* Feature highlights */}
          <div className="mt-12 space-y-4">
            {[
              { icon: '🎙️', label: 'AI 语音识别 + 说话人分离' },
              { icon: '🌐', label: '多语言实时翻译' },
              { icon: '📝', label: '智能会议纪要生成' },
              { icon: '🔍', label: '全文搜索定位回放' },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-3 text-white/90">
                <span className="text-xl">{item.icon}</span>
                <span className="text-sm font-medium">{item.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10 p-16">
          <Text className="text-white/50 text-xs">
            © 2024 MeetScript. All rights reserved.
          </Text>
        </div>
      </div>

      {/* Right: Login Form */}
      <div className="flex-1 flex items-center justify-center bg-white p-8">
        <div className="w-full max-w-sm animate-fade-in-up">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-10">
            <div
              className="inline-flex items-center justify-center rounded-2xl mb-4"
              style={{
                width: 56, height: 56,
                background: BRAND_GRADIENT,
                boxShadow: '0 4px 16px rgba(13,148,136,0.3)',
              }}
            >
              <ThunderboltOutlined style={{ color: '#fff', fontSize: 28 }} />
            </div>
            <Title level={2} className="!mb-1 !text-slate-800">MeetScript</Title>
            <Text type="secondary">智能会议纪要平台</Text>
          </div>

          <div className="mb-8">
            <Title level={3} className="!mb-1 !text-slate-800">欢迎回来</Title>
            <Text type="secondary">请登录您的账户以继续</Text>
          </div>

          <Form name="login" onFinish={onFinish} size="large" layout="vertical">
            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input
                prefix={<UserOutlined className="text-slate-400" />}
                placeholder="用户名"
                className="h-12 rounded-lg"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password
                prefix={<LockOutlined className="text-slate-400" />}
                placeholder="密码"
                className="h-12 rounded-lg"
              />
            </Form.Item>

            <Form.Item className="mb-3">
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                className="h-12 rounded-lg font-semibold text-base"
                style={{
                  background: BRAND_GRADIENT,
                  border: 'none',
                  boxShadow: '0 4px 14px rgba(13,148,136,0.35)',
                }}
              >
                登录
              </Button>
            </Form.Item>
          </Form>
        </div>
      </div>
    </div>
  );
}
