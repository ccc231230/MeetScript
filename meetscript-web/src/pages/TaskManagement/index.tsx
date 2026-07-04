import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Table,
  Tag,
  Button,
  Typography,
  Space,
  Select,
  App,
  Tabs,
  Progress,
  Empty,
  Collapse,
  Spin,
} from 'antd';
import { ReloadOutlined, FileTextOutlined } from '@ant-design/icons';
import { useSSE } from '../../hooks/useSSE';
import { useTaskProgress } from '../../hooks/useTaskProgress';
import { tasksAPI } from '../../api/tasks'; // v2
import type { MeetingTask, TaskLog } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;

const TASK_TYPE_LABELS: Record<string, string> = {
  audio_preprocess: '音频预处理',
  asr: '语音识别',
  diarization: '说话人分离',
  translation: '翻译',
  summary: '会议总结',
};

const STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'green',
  failed: 'red',
  retrying: 'orange',
  dlq: 'magenta',
};

const STATUS_LABELS: Record<string, string> = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  retrying: '重试中',
  dlq: '死信队列',
};

export default function TaskManagementPage() {
  const { message } = App.useApp();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'active' | 'dlq'>('active');

  const { events, appendEvent } = useTaskProgress(selectedTaskId);

  // Fetch real task list
  const { data: taskListData, isLoading } = useQuery({
    queryKey: ['tasks', statusFilter, activeTab],
    queryFn: async () => {
      const res = await tasksAPI.list({
        status: activeTab === 'dlq' ? 'dlq' : statusFilter,
        page_size: 100,
      });
      return res.data;
    },
    refetchInterval: 5000,
  });

  const tasks: MeetingTask[] = taskListData?.items ?? [];

  // Subscribe to SSE for selected task
  useSSE(selectedTaskId, (event) => {
    appendEvent(event);
  });

  const { data: taskLogs } = useQuery({
    queryKey: ['task-logs', selectedTaskId],
    queryFn: async () => {
      if (!selectedTaskId) return [];
      const res = await tasksAPI.getLogs(selectedTaskId);
      return res.data;
    },
    enabled: !!selectedTaskId,
  });

  const handleRetry = async (taskId: string) => {
    try {
      await tasksAPI.retry(taskId);
      message.success('任务已重新提交');
    } catch {
      message.error('重试失败');
    }
  };

  const columns: ColumnsType<MeetingTask> = [
    { title: '会议', dataIndex: 'meeting_id', key: 'meeting_id', width: 120, ellipsis: true },
    {
      title: '任务类型',
      dataIndex: 'task_type',
      key: 'task_type',
      width: 120,
      render: (t: string) => TASK_TYPE_LABELS[t] ?? t,
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 70,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => (
        <Tag color={STATUS_COLORS[s] ?? 'default'}>
          {STATUS_LABELS[s] ?? s}
        </Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 150,
      render: (p: number) => <Progress percent={p} size="small" />,
    },
    {
      title: '重试',
      key: 'retry_info',
      width: 80,
      render: (_: unknown, r: MeetingTask) =>
        `${r.retry_count}/${r.max_retries}`,
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: unknown, r: MeetingTask) => (
        <Space>
          <Button
            size="small"
            onClick={() => setSelectedTaskId(r.id)}
          >
            查看
          </Button>
          {(r.status === 'failed' || r.status === 'dlq') && (
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleRetry(r.id)}
            >
              重试
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Title level={4}>任务管理</Title>

      <Tabs
        activeKey={activeTab}
        onChange={(k) => setActiveTab(k as 'active' | 'dlq')}
        items={[
          {
            key: 'active',
            label: '进行中的任务',
            children: isLoading ? (
              <Spin size="large" style={{ display: 'block', margin: '60px auto' }} />
            ) : (
              <Card>
                <Space style={{ marginBottom: 16 }}>
                  <Select
                    placeholder="筛选状态"
                    allowClear
                    value={statusFilter}
                    onChange={setStatusFilter}
                    style={{ width: 140 }}
                    options={Object.entries(STATUS_LABELS).map(([k, v]) => ({ value: k, label: v }))}
                  />
                  <Button icon={<ReloadOutlined />}>刷新</Button>
                </Space>
                <Table
                  dataSource={tasks.filter((t: MeetingTask) =>
                    !statusFilter || t.status === statusFilter,
                  )}
                  columns={columns}
                  rowKey="id"
                  pagination={{ pageSize: 20 }}
                  size="small"
                  locale={{ emptyText: <Empty description="暂无任务" /> }}
                />
              </Card>
            ),
          },
          {
            key: 'dlq',
            label: '死信队列 (DLQ)',
            children: (
              <Card>
                <Table
                  dataSource={tasks.filter((t: MeetingTask) => t.status === 'dlq')}
                  columns={columns}
                  rowKey="id"
                  pagination={{ pageSize: 20 }}
                  size="small"
                  locale={{ emptyText: <Empty description="死信队列为空" /> }}
                />
              </Card>
            ),
          },
        ]}
      />

      {selectedTaskId && (
        <Card title="任务详情与日志" style={{ marginTop: 16 }}>
          {events.current.length > 0 && (
            <Collapse
              items={[
                {
                  key: 'progress',
                  label: `实时进度事件 (${events.current.length})`,
                  children: (
                    <div style={{ maxHeight: 200, overflow: 'auto' }}>
                      {events.current.map((e, i) => (
                        <div key={i} style={{ fontSize: 12, marginBottom: 4 }}>
                          <Text type="secondary">{e.timestamp}</Text>
                          {' '}
                          <Tag color={STATUS_COLORS[e.status]}>{e.status}</Tag>
                          {' '}
                          {e.current_step} ({e.progress}%)
                          {e.message && ` - ${e.message}`}
                          {e.error_detail && (
                            <Text type="danger"> - {e.error_detail}</Text>
                          )}
                        </div>
                      ))}
                    </div>
                  ),
                },
              ]}
            />
          )}
          {taskLogs && taskLogs.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <Text strong><FileTextOutlined /> 日志 ({taskLogs.length})</Text>
              <div style={{ maxHeight: 200, overflow: 'auto', marginTop: 8, fontSize: 12 }}>
                {taskLogs.map((log: TaskLog) => (
                  <div key={log.id}>
                    [{log.timestamp}] [{log.level}] {log.message}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
