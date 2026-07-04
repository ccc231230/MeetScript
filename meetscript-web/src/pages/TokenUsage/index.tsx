import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Table,
  Typography,
  Row,
  Col,
  Select,
  Button,
  Spin,
  Tag,
  Space,
  App,
  Empty,
} from 'antd';
import { DollarOutlined, ThunderboltOutlined, DownloadOutlined } from '@ant-design/icons';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';
import { tokenUsageAPI } from '../../api/token-usage';
import type { TokenUsage, TokenUsageStats } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;

const PIE_COLORS = ['#0D9488', '#6366F1', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#EC4899', '#F97316'];

function StatCard({ icon, label, value, suffix, colorClass = 'text-primary-600' }: {
  icon: React.ReactNode; label: string; value: number | string; suffix?: string; colorClass?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-center gap-3 mb-3">
        <span className={colorClass}>{icon}</span>
        <Text type="secondary" className="text-sm">{label}</Text>
      </div>
      <div className={`text-2xl font-bold ${colorClass}`}>
        {typeof value === 'number' ? value.toLocaleString() : value}
        {suffix && <span className="text-sm font-normal text-slate-400 ml-1">{suffix}</span>}
      </div>
    </div>
  );
}

export default function TokenUsagePage() {
  const { message } = App.useApp();
  const [days, setDays] = useState(30);

  const { data: listData, isLoading } = useQuery({
    queryKey: ['token-usage', days],
    queryFn: async () => {
      const res = await tokenUsageAPI.list({ days, page_size: 50 });
      return res.data;
    },
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['token-stats', days],
    queryFn: async () => {
      const res = await tokenUsageAPI.stats(days);
      return res.data;
    },
  });

  const handleExportCSV = () => {
    if (!listData?.items) return;
    const headers = '日期,操作类型,模型,输入Token,输出Token,总计Token,成本\n';
    const rows = listData.items.map((r: TokenUsage) =>
      `${r.created_at},${r.operation_type},${r.model_config_id},${r.tokens_input},${r.tokens_output},${r.tokens_total},${r.cost}`
    ).join('\n');
    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `token-usage-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    message.success('导出成功');
  };

  const columns: ColumnsType<TokenUsage> = [
    {
      title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (d: string) => <Text className="text-xs">{new Date(d).toLocaleString()}</Text>,
    },
    {
      title: '操作类型', dataIndex: 'operation_type', key: 'operation_type', width: 120,
      render: (t: string) => <Tag color="blue">{t}</Tag>,
    },
    {
      title: '输入 Token', dataIndex: 'tokens_input', key: 'tokens_input', width: 110,
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: '输出 Token', dataIndex: 'tokens_output', key: 'tokens_output', width: 110,
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: '总计 Token', dataIndex: 'tokens_total', key: 'tokens_total', width: 120,
      render: (v: number) => <Text strong>{v.toLocaleString()}</Text>,
    },
    {
      title: '成本', dataIndex: 'cost', key: 'cost', width: 120,
      render: (v: number) => (
        <Text className="text-accent-600 font-medium">¥{Number(v).toFixed(6)}</Text>
      ),
    },
  ];

  if (isLoading || statsLoading) {
    return <Spin size="large" className="block mx-auto mt-24" />;
  }

  const s = stats as TokenUsageStats | undefined;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <Title level={4} className="!mb-1 !text-slate-800">Token 消耗统计</Title>
          <Text type="secondary">AI 模型调用成本与用量分析</Text>
        </div>
        <Space>
          <Select
            value={days}
            onChange={setDays}
            options={[
              { value: 7, label: '最近7天' },
              { value: 30, label: '最近30天' },
              { value: 90, label: '最近90天' },
            ]}
            style={{ width: 130 }}
          />
          <Button icon={<DownloadOutlined />} onClick={handleExportCSV}>
            导出 CSV
          </Button>
        </Space>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          icon={<ThunderboltOutlined className="text-xl" />}
          label="总 Token 消耗"
          value={s?.total_tokens ?? 0}
          colorClass="text-primary-600"
        />
        <StatCard
          icon={<DollarOutlined className="text-xl" />}
          label="总成本"
          value={s?.total_cost?.toFixed(4) ?? '0'}
          suffix="¥"
          colorClass="text-accent-600"
        />
        <StatCard
          icon={<ThunderboltOutlined className="text-xl" />}
          label="API 调用次数"
          value={listData?.total ?? 0}
          colorClass="text-indigo-500"
        />
      </div>

      {/* Charts */}
      {s?.by_model && Object.keys(s.by_model).length > 0 ? (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <Text strong className="text-slate-700">按模型 Token 分布</Text>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={Object.entries(s.by_model).map(([name, d]) => ({ name, value: d.tokens }))}
                    dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {Object.keys(s.by_model).map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => v.toLocaleString()} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <Text strong className="text-slate-700">按模型成本分布</Text>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={Object.entries(s.by_model).map(([name, d]) => ({ name, cost: d.cost }))}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip formatter={(v: number) => `¥${v.toFixed(6)}`} />
                  <Bar dataKey="cost" fill="#0D9488" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      ) : (
        <Empty description="暂无统计数据" />
      )}

      {/* Usage Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100">
          <Text strong className="text-slate-700">使用记录</Text>
        </div>
        <Table
          dataSource={listData?.items ?? []}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条记录` }}
          size="middle"
        />
      </div>
    </div>
  );
}
