import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Typography, Spin, Tag, Button } from 'antd';
import {
  VideoCameraOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  ExclamationCircleOutlined,
  PlusOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { meetingsAPI } from '../../api/meetings';
import { tokenUsageAPI } from '../../api/token-usage';
import type { Meeting, TokenUsageStats } from '../../types';

const { Title, Text } = Typography;

const GRADIENT_TEAL = 'linear-gradient(135deg, #0D9488, #14B8A6)';
const GRADIENT_GREEN = 'linear-gradient(135deg, #10B981, #34D399)';
const GRADIENT_AMBER = 'linear-gradient(135deg, #F59E0B, #FBBF24)';
const GRADIENT_ORANGE = 'linear-gradient(135deg, #EA580C, #F97316)';

function StatCard({ icon, label, value, suffix, gradient, trend }: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  suffix?: string;
  gradient: string;
  trend?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-elevated transition-shadow duration-200">
      <div className="flex items-start justify-between mb-3">
        <div
          className="flex items-center justify-center rounded-lg"
          style={{
            width: 42, height: 42,
            background: gradient,
            boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
          }}
        >
          <span className="text-white text-lg">{icon}</span>
        </div>
        {trend && (
          <Text className="text-xs text-slate-400">{trend}</Text>
        )}
      </div>
      <div className="text-2xl font-bold text-slate-800 mb-1">
        {typeof value === 'number' ? value.toLocaleString() : value}
        {suffix && <span className="text-sm font-normal text-slate-400 ml-1">{suffix}</span>}
      </div>
      <Text className="text-sm text-slate-500">{label}</Text>
    </div>
  );
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const { data: meetings, isLoading: meetingsLoading } = useQuery({
    queryKey: ['meetings', 'dashboard'],
    queryFn: async () => {
      const res = await meetingsAPI.list({ page_size: 100 });
      return res.data.items;
    },
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['token-stats', 'dashboard'],
    queryFn: async () => {
      const res = await tokenUsageAPI.stats();
      return res.data;
    },
  });

  const isLoading = meetingsLoading || statsLoading;

  const completedCount = meetings?.filter((m: Meeting) => m.status === 'completed').length ?? 0;
  const processingCount = meetings?.filter((m: Meeting) =>
    ['uploaded', 'preprocessing', 'processing'].includes(m.status),
  ).length ?? 0;
  const failedCount = meetings?.filter((m: Meeting) => m.status === 'failed').length ?? 0;
  const totalTokens = (stats as TokenUsageStats)?.total_tokens ?? 0;
  const totalCost = (stats as TokenUsageStats)?.total_cost ?? 0;

  const recentColumns = [
    {
      title: '会议名称',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (t: string) => <Text strong>{t}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => {
        const color: Record<string, string> = {
          uploaded: 'blue', preprocessing: 'cyan',
          processing: 'processing' as const, completed: 'green', failed: 'red',
        };
        const label: Record<string, string> = {
          uploaded: '已上传', preprocessing: '预处理中',
          processing: '处理中', completed: '已完成', failed: '失败',
        };
        return <Tag color={color[s] ?? 'default'}>{label[s] ?? s}</Tag>;
      },
    },
    {
      title: '源语言',
      dataIndex: 'source_language',
      key: 'source_language',
      width: 80,
      render: (l: string) => <Tag>{l?.toUpperCase()}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (d: string) => (
        <Text type="secondary" className="text-xs">{new Date(d).toLocaleString()}</Text>
      ),
    },
  ];

  if (isLoading) {
    return <Spin size="large" className="block mx-auto mt-24" />;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <Title level={4} className="!mb-1 !text-slate-800">{t('nav.dashboard')}</Title>
          <Text type="secondary">会议处理概览与 Token 消耗统计</Text>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/meetings/upload')}
          size="large"
          className="rounded-lg font-medium"
        >
          上传会议
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<VideoCameraOutlined />}
          label="会议总数"
          value={meetings?.length ?? 0}
          gradient={GRADIENT_TEAL}
        />
        <StatCard
          icon={<CheckCircleOutlined />}
          label="已完成"
          value={completedCount}
          gradient={GRADIENT_GREEN}
          trend={meetings?.length ? `${Math.round(completedCount / meetings.length * 100)}%` : undefined}
        />
        <StatCard
          icon={<ClockCircleOutlined />}
          label="处理中"
          value={processingCount}
          gradient={GRADIENT_AMBER}
          trend={failedCount > 0 ? `${failedCount} 失败` : undefined}
        />
        <StatCard
          icon={<DollarOutlined />}
          label="Token 消耗"
          value={totalTokens}
          suffix="tokens"
          gradient={GRADIENT_ORANGE}
          trend={`¥${totalCost.toFixed(2)}`}
        />
      </div>

      {/* Failed meeting alerts */}
      {failedCount > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <ExclamationCircleOutlined className="text-red-500 text-lg" />
          <Text className="text-red-700 text-sm">
            有 <strong>{failedCount}</strong> 个会议处理失败，请前往任务管理查看详情。
          </Text>
          <Button size="small" type="link" danger onClick={() => navigate('/tasks')}>
            查看任务 <RightOutlined />
          </Button>
        </div>
      )}

      {/* Recent Meetings */}
      <Card
        title={<span className="font-semibold text-slate-700">最近会议</span>}
        className="border-slate-200 shadow-sm"
        styles={{ body: { padding: 0 } }}
      >
        <Table
          dataSource={meetings?.slice(0, 10)}
          columns={recentColumns}
          rowKey="id"
          pagination={false}
          size="middle"
          onRow={(record) => ({
            onClick: () => navigate(`/meetings/${record.id}`),
            className: 'cursor-pointer hover:bg-slate-50 transition-colors',
          })}
        />
        {(meetings?.length ?? 0) > 10 && (
          <div className="p-3 text-center border-t border-slate-100">
            <Button type="link" onClick={() => navigate('/meetings/upload')}>
              查看全部会议 <RightOutlined />
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
