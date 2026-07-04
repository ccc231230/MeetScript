import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Card, Col, Row, Statistic, Typography, Table, Spin, Tag } from 'antd';
import {
  VideoCameraOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { meetingsAPI } from '../../api/meetings';
import { tokenUsageAPI } from '../../api/token-usage';
import type { Meeting, TokenUsageStats } from '../../types';

const { Title } = Typography;

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

  const completedCount = meetings?.filter((m: Meeting) => m.status === 'completed').length ?? 0;
  const processingCount = meetings?.filter((m: Meeting) =>
    ['uploaded', 'preprocessing', 'processing'].includes(m.status),
  ).length ?? 0;
  const failedCount = meetings?.filter((m: Meeting) => m.status === 'failed').length ?? 0;
  const totalTokens = (stats as TokenUsageStats)?.total_tokens ?? 0;
  const totalCost = (stats as TokenUsageStats)?.total_cost ?? 0;

  const recentColumns = [
    { title: '会议名称', dataIndex: 'title', key: 'title', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => {
        const color: Record<string, string> = {
          uploaded: 'blue',
          preprocessing: 'cyan',
          processing: 'processing' as const,
          completed: 'green',
          failed: 'red',
        };
        const label: Record<string, string> = {
          uploaded: '已上传',
          preprocessing: '预处理',
          processing: '处理中',
          completed: '已完成',
          failed: '失败',
        };
        return <Tag color={color[s] ?? 'default'}>{label[s] ?? s}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (d: string) => new Date(d).toLocaleString(),
    },
  ];

  if (meetingsLoading || statsLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  return (
    <div>
      <Title level={4}>{t('nav.dashboard')}</Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="会议总数"
              value={meetings?.length ?? 0}
              prefix={<VideoCameraOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="处理完成"
              value={completedCount}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="处理中"
              value={processingCount}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
            {failedCount > 0 && (
              <div style={{ marginTop: 4, color: '#ff4d4f', fontSize: 12 }}>
                <ExclamationCircleOutlined /> {failedCount} 个失败
              </div>
            )}
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Token 消耗"
              value={totalTokens}
              prefix={<DollarOutlined />}
              suffix="tokens"
            />
            <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
              预估成本: ¥{totalCost.toFixed(4)}
            </div>
          </Card>
        </Col>
      </Row>

      <Card title="最近会议" style={{ marginTop: 24 }}>
        <Table
          dataSource={meetings?.slice(0, 10)}
          columns={recentColumns}
          rowKey="id"
          pagination={false}
          size="small"
          onRow={(record) => ({
            onClick: () => navigate(`/meetings/${record.id}`),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
    </div>
  );
}
