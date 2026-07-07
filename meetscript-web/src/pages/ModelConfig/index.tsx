import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Table,
  Button,
  Typography,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Slider,
  Tag,
  Space,
  App,
  Spin,
} from 'antd';
import { SettingOutlined, PlayCircleOutlined, GlobalOutlined, RobotOutlined } from '@ant-design/icons';
import { modelsAPI } from '../../api/models';
import type { ModelConfig, ModelConfigUpdate, ModelType } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;

const MODEL_TYPE_LABELS: Record<ModelType, string> = {
  asr: '语音识别 (ASR)',
  translation: '翻译引擎',
  summary: '会议总结 (LLM)',
};

const MODEL_TYPE_ICONS: Record<ModelType, React.ReactNode> = {
  asr: <PlayCircleOutlined />,
  translation: <GlobalOutlined />,
  summary: <RobotOutlined />,
};

const MODEL_TYPE_GRADIENTS: Record<ModelType, string> = {
  asr: 'linear-gradient(135deg, #0D9488, #14B8A6)',
  translation: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
  summary: 'linear-gradient(135deg, #F59E0B, #F97316)',
};

export default function ModelConfigPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [editModal, setEditModal] = useState<ModelConfig | null>(null);
  const [form] = Form.useForm();

  const { data: configs, isLoading } = useQuery({
    queryKey: ['model-configs'],
    queryFn: async () => {
      const res = await modelsAPI.list();
      return res.data;
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ModelConfigUpdate }) =>
      modelsAPI.update(id, data),
    onSuccess: () => {
      message.success('模型配置已更新');
      queryClient.invalidateQueries({ queryKey: ['model-configs'] });
      setEditModal(null);
    },
    onError: () => message.error('更新失败'),
  });

  const handleEdit = (record: ModelConfig) => {
    setEditModal(record);
    form.resetFields();  // clear stale fields from previously opened modal
    form.setFieldsValue({
      model_name: record.model_name,
      is_active: record.is_active,
      ...record.parameters,
    });
  };

  const handleSave = () => {
    const values = form.getFieldsValue();
    const { model_name, is_active, ...others } = values;
    // Only keep keys that are in the current record's parameters
    const known_keys = new Set([...Object.keys(editModal?.parameters ?? {}), 'diarization_enabled', 'speaker_count', 'temperature', 'top_p', 'max_tokens', 'source_lang']);
    const params: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(others)) {
      if (known_keys.has(k) && v !== undefined) {
        params[k] = v;
      }
    }
    updateMutation.mutate({
      id: editModal!.id,
      data: { model_name, is_active, parameters: params },
    });
  };

  const columns: ColumnsType<ModelConfig> = [
    {
      title: '类型',
      dataIndex: 'model_type',
      key: 'model_type',
      width: 180,
      render: (t: ModelType) => (
        <Space>
          <div
            className="flex items-center justify-center rounded-md"
            style={{
              width: 28, height: 28,
              background: MODEL_TYPE_GRADIENTS[t] || MODEL_TYPE_GRADIENTS.asr,
            }}
          >
            <span className="text-white text-xs">{MODEL_TYPE_ICONS[t]}</span>
          </div>
          <Text>{MODEL_TYPE_LABELS[t] ?? t}</Text>
        </Space>
      ),
    },
    {
      title: 'Provider',
      dataIndex: 'provider',
      key: 'provider',
      width: 120,
      render: (p: string) => <Tag>{p}</Tag>,
    },
    {
      title: '模型名称',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 200,
      render: (n: string) => <Tag color="blue">{n}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (v: boolean) => (
        <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, r: ModelConfig) => (
        <Button size="small" icon={<SettingOutlined />} onClick={() => handleEdit(r)}>
          配置
        </Button>
      ),
    },
  ];

  if (isLoading) {
    return <Spin size="large" className="block mx-auto mt-24" />;
  }

  return (
    <div className="space-y-6">
      <div>
        <Title level={4} className="!mb-1 !text-slate-800">模型配置</Title>
        <Text type="secondary">管理 AI 模型参数与开关</Text>
      </div>

      {/* Model Type Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {(['asr', 'translation', 'summary'] as ModelType[]).map((type) => {
          const cfg = configs?.find((c: ModelConfig) => c.model_type === type && c.is_active);
          return (
            <div
              key={type}
              className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-center gap-3 mb-3">
                <div
                  className="flex items-center justify-center rounded-lg"
                  style={{
                    width: 40, height: 40,
                    background: MODEL_TYPE_GRADIENTS[type],
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  }}
                >
                  <span className="text-white text-lg">{MODEL_TYPE_ICONS[type]}</span>
                </div>
                <div>
                  <Text strong className="text-slate-700">{MODEL_TYPE_LABELS[type]}</Text>
                </div>
              </div>
              <div className="text-lg font-bold text-slate-800">
                {cfg?.model_name ?? '未配置'}
              </div>
              <Text type="secondary" className="text-xs">
                {cfg ? `${cfg.provider}` : '点击下方表格进行配置'}
              </Text>
            </div>
          );
        })}
      </div>

      {/* Config Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <Table
          dataSource={configs}
          columns={columns}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      </div>

      {/* Edit Modal */}
      <Modal
        title={
          <span className="font-semibold">
            配置 - {editModal?.model_name ?? ''}
          </span>
        }
        open={!!editModal}
        onCancel={() => setEditModal(null)}
        onOk={handleSave}
        confirmLoading={updateMutation.isPending}
        width={500}
      >
        {editModal && (
          <Form form={form} layout="vertical">
            <Form.Item label="模型名称" name="model_name">
              <Input className="rounded-lg" />
            </Form.Item>
            <Form.Item label="启用" name="is_active" valuePropName="checked">
              <Switch />
            </Form.Item>

            {editModal.model_type === 'summary' && (
              <>
                <Form.Item label="Temperature" name="temperature" initialValue={0.7}>
                  <Slider min={0} max={2} step={0.1} />
                </Form.Item>
                <Form.Item label="Top-P" name="top_p" initialValue={0.9}>
                  <Slider min={0} max={1} step={0.05} />
                </Form.Item>
                <Form.Item label="Max Tokens" name="max_tokens" initialValue={4096}>
                  <InputNumber style={{ width: '100%' }} min={1} max={32768} />
                </Form.Item>
              </>
            )}

            {editModal.model_type === 'asr' && (
              <>
                <Form.Item label="说话人分离" name="diarization_enabled" valuePropName="checked" initialValue={true}>
                  <Switch />
                </Form.Item>
                <Form.Item label="说话人数量" name="speaker_count" initialValue={0}>
                  <InputNumber style={{ width: '100%' }} min={0} max={20} placeholder="0 = 自动检测" />
                </Form.Item>
              </>
            )}

            {editModal.model_type === 'translation' && (
              <Form.Item label="源语言" name="source_lang" initialValue="auto">
                <Select options={[
                  { value: 'auto', label: '自动检测' },
                  { value: 'zh', label: '中文' },
                  { value: 'en', label: 'English' },
                  { value: 'ja', label: '日本語' },
                ]} />
              </Form.Item>
            )}
          </Form>
        )}
      </Modal>
    </div>
  );
}
