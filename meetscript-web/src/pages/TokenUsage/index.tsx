import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Table,
  Typography,
  Row,
  Col,
  Statistic,
  Select,
  Button,
  Spin,
  Tag,
  Space,
  App,
  Empty,
} from 'antd';
import { DollarOutlined, ThunderboltOutlined } from '@ant-design/icons';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import { tokenUsageAPI } from '../../api/token-usage';
import type { TokenUsage, TokenUsageStats } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;

const PIE_COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16'];

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
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (d: string) => new Date(d).toLocaleString(),
    },
    {
      title: '操作类型',
      dataIndex: 'operation_type',
      key: 'operation_type',
      width: 120,
      render: (t: string) => <Tag>{t}</Tag>,
    },
    {
      title: '输入 Token',
      dataIndex: 'tokens_input',
      key: 'tokens_input',
      width: 110,
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: '输出 Token',
      dataIndex: 'tokens_output',
      key: 'tokens_output',
      width: 110,
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: '总计 Token',
      dataIndex: 'tokens_total',
      key: 'tokens_total',
      width: 110,
      render: (v: number) => (
        <Text strong>{v.toLocaleString()}</Text>
      ),
    },
    {
      title: '成本 (¥)',
      dataIndex: 'cost',
      key: 'cost',
      width: 100,
      render: (v: number) => (
        <Text style={{ color: '#cf1322' }}>¥{Number(v).toFixed(6)}</Text>
      ),
    },
  ];

  if (isLoading || statsLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  const s = stats as TokenUsageStats | undefined;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>Token 消耗统计</Title>
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
          <Button onClick={handleExportCSV}>导出 CSV</Button>
        </Space>
      </div>

      <Row gutter={[16, 16]} style={{ marginTop: 16, marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="总 Token 消耗"
              value={s?.total_tokens ?? 0}
              prefix={<ThunderboltOutlined />}
              formatter={(v) => Number(v).toLocaleString()}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="总成本"
              value={s?.total_cost ?? 0}
              prefix={<DollarOutlined />}
              precision={6}
              suffix="¥"
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="API 调用次数"
              value={listData?.total ?? 0}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {s?.by_model && Object.keys(s.by_model).length > 0 ? (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={12}>
              <Card title="按模型 Token 分布" size="small">
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={Object.entries(s.by_model).map(([name, d]) => ({ name, value: d.tokens }))}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
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
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="按模型成本分布" size="small">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={Object.entries(s.by_model).map(([name, d]) => ({ name, cost: d.cost }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip formatter={(v: number) => `¥${v.toFixed(6)}`} />
                    <Bar dataKey="cost" fill="#1890ff" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </Col>
          </Row>

          {s?.by_operation && Object.keys(s.by_operation).length > 0 && (
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col xs={24} lg={12}>
                <Card title="按操作类型 Token 分布" size="small">
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie
                        data={Object.entries(s.by_operation).map(([name, d]) => ({ name, value: d.tokens }))}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={90}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {Object.keys(s.by_operation).map((_, i) => (
                          <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number) => v.toLocaleString()} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </Card>
              </Col>
              <Col xs={24} lg={12}>
                <Card title="按操作类型成本分布" size="small">
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart
                      data={Object.entries(s.by_operation).map(([name, d]) => ({ name, cost: d.cost }))}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip formatter={(v: number) => `¥${v.toFixed(6)}`} />
                      <Bar dataKey="cost" fill="#52c41a" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </Col>
            </Row>
          )}
        </>
      ) : (
        <Empty description="暂无统计数据" style={{ marginBottom: 24 }} />
      )}

      <Card>
        <Table
          dataSource={listData?.items ?? []}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条记录` }}
          size="small"
        />
      </Card>
    </div>
  );
}
