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
import { ReloadOutlined, FileTextOutlined, SyncOutlined } from '@ant-design/icons';
import { useSSE } from '../../hooks/useSSE';
import { useTaskProgress } from '../../hooks/useTaskProgress';
import { tasksAPI } from '../../api/tasks';
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

const STATUS_ICONS: Record<string, React.ReactNode> = {
  running: <SyncOutlined spin />,
  retrying: <SyncOutlined spin />,
};

export default function TaskManagementPage() {
  const { message } = App.useApp();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'active' | 'dlq'>('active');

  const { events, appendEvent } = useTaskProgress(selectedTaskId);

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
    } catch { message.error('重试失败'); }
  };

  const columns: ColumnsType<MeetingTask> = [
    {
      title: '会议',
      dataIndex: 'meeting_id',
      key: 'meeting_id',
      width: 140,
      ellipsis: true,
      render: (id: string) => (
        <Text code className="text-xs">{id?.slice(0, 8)}...</Text>
      ),
    },
    {
      title: '任务类型',
      dataIndex: 'task_type',
      key: 'task_type',
      width: 120,
      render: (t: string) => (
        <Tag color="blue">{TASK_TYPE_LABELS[t] ?? t}</Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 70,
      align: 'center',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s: string) => (
        <Tag
          color={STATUS_COLORS[s] ?? 'default'}
          icon={STATUS_ICONS[s]}
        >
          {STATUS_LABELS[s] ?? s}
        </Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 150,
      render: (p: number) => (
        <Progress
          percent={p}
          size="small"
          strokeColor={p === 100 ? '#10B981' : '#0D9488'}
        />
      ),
    },
    {
      title: '重试',
      key: 'retry_info',
      width: 70,
      align: 'center',
      render: (_: unknown, r: MeetingTask) => (
        <Text type={r.retry_count > 0 ? 'warning' : 'secondary'} className="text-xs">
          {r.retry_count}/{r.max_retries}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: unknown, r: MeetingTask) => (
        <Space>
          <Button size="small" type={selectedTaskId === r.id ? 'primary' : 'default'}
            onClick={() => setSelectedTaskId(r.id)}
          >
            查看
          </Button>
          {(r.status === 'failed' || r.status === 'dlq') && (
            <Button size="small" icon={<ReloadOutlined />}
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Title level={4} className="!mb-1 !text-slate-800">任务管理</Title>
          <Text type="secondary">查看与管理所有异步处理任务</Text>
        </div>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={(k) => setActiveTab(k as 'active' | 'dlq')}
        className="[&_.ant-tabs-nav]:!mb-3"
        items={[
          {
            key: 'active',
            label: (
              <span className="flex items-center gap-1.5">
                <SyncOutlined className="text-primary-500" />
                进行中的任务
              </span>
            ),
            children: isLoading ? (
              <Spin size="large" className="block mx-auto mt-16" />
            ) : (
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100 bg-slate-50/50">
                  <Space>
                    <Select
                      placeholder="筛选状态"
                      allowClear
                      value={statusFilter}
                      onChange={setStatusFilter}
                      size="small"
                      style={{ width: 140 }}
                      options={Object.entries(STATUS_LABELS).map(([k, v]) => ({ value: k, label: v }))}
                    />
                  </Space>
                  <Text type="secondary" className="text-xs">
                    共 {tasks.filter((t) => !statusFilter || t.status === statusFilter).length} 个任务
                  </Text>
                </div>
                <Table
                  dataSource={tasks.filter((t: MeetingTask) =>
                    !statusFilter || t.status === statusFilter,
                  )}
                  columns={columns}
                  rowKey="id"
                  pagination={{ pageSize: 20, size: 'small' }}
                  size="middle"
                  locale={{ emptyText: <Empty description="暂无任务" /> }}
                />
              </div>
            ),
          },
          {
            key: 'dlq',
            label: (
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                死信队列 (DLQ)
              </span>
            ),
            children: (
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <Table
                  dataSource={tasks.filter((t: MeetingTask) => t.status === 'dlq')}
                  columns={columns}
                  rowKey="id"
                  pagination={{ pageSize: 20, size: 'small' }}
                  size="middle"
                  locale={{ emptyText: <Empty description="死信队列为空" /> }}
                />
              </div>
            ),
          },
        ]}
      />

      {/* Task Detail Panel */}
      {selectedTaskId && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden animate-slide-in-right">
          <div className="px-5 py-3 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <Text strong className="text-slate-700">
              <FileTextOutlined className="mr-2" />
              任务详情
            </Text>
            <Button size="small" type="text" onClick={() => setSelectedTaskId(null)}>
              关闭
            </Button>
          </div>

          <div className="p-5 space-y-4">
            {/* SSE Progress Events */}
            {events.current.length > 0 && (
              <Collapse
                size="small"
                defaultActiveKey={['progress']}
                items={[{
                  key: 'progress',
                  label: (
                    <span className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                      实时进度事件 ({events.current.length})
                    </span>
                  ),
                  children: (
                    <div className="max-h-[200px] overflow-auto space-y-1.5">
                      {events.current.map((e, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <Text type="secondary" className="shrink-0">{e.timestamp}</Text>
                          <Tag color={STATUS_COLORS[e.status]} className="!text-[10px] !leading-4">
                            {e.status}
                          </Tag>
                          <span className="text-slate-600">
                            {e.current_step} ({e.progress}%)
                          </span>
                          {e.message && (
                            <Text type="secondary">- {e.message}</Text>
                          )}
                          {e.error_detail && (
                            <Text type="danger">- {e.error_detail}</Text>
                          )}
                        </div>
                      ))}
                    </div>
                  ),
                }]}
              />
            )}

            {/* Logs */}
            {taskLogs && taskLogs.length > 0 && (
              <div>
                <Text strong className="text-sm text-slate-600">
                  <FileTextOutlined className="mr-1" /> 日志 ({taskLogs.length})
                </Text>
                <div className="mt-2 max-h-[200px] overflow-auto bg-slate-50 rounded-lg p-3 text-xs font-mono">
                  {taskLogs.map((log: TaskLog) => (
                    <div key={log.id} className="py-0.5 text-slate-600">
                      <span className="text-slate-400">[{log.timestamp}]</span>
                      {' '}
                      <span className="text-primary-600">[{log.level}]</span>
                      {' '}
                      {log.message}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {events.current.length === 0 && (!taskLogs || taskLogs.length === 0) && (
              <Empty description="暂无详情数据" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
