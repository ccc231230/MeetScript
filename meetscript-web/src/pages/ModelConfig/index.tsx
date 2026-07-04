import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
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
  Statistic,
  Row,
  Col,
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
    form.setFieldsValue({
      model_name: record.model_name,
      is_active: record.is_active,
      ...record.parameters,
    });
  };

  const handleSave = () => {
    const values = form.getFieldsValue();
    const { model_name, is_active, ...params } = values;
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
      width: 150,
      render: (t: ModelType) => (
        <Space>
          {MODEL_TYPE_ICONS[t]}
          <Text>{MODEL_TYPE_LABELS[t] ?? t}</Text>
        </Space>
      ),
    },
    { title: 'Provider', dataIndex: 'provider', key: 'provider', width: 120 },
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
      width: 120,
      render: (_: unknown, r: ModelConfig) => (
        <Button size="small" icon={<SettingOutlined />} onClick={() => handleEdit(r)}>
          配置
        </Button>
      ),
    },
  ];

  if (isLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  return (
    <div>
      <Title level={4}>模型配置</Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {(['asr', 'translation', 'summary'] as ModelType[]).map((type) => {
          const cfg = configs?.find((c: ModelConfig) => c.model_type === type && c.is_active);
          return (
            <Col xs={24} sm={8} key={type}>
              <Card>
                <Statistic
                  title={MODEL_TYPE_LABELS[type]}
                  value={cfg?.model_name ?? '未配置'}
                  prefix={MODEL_TYPE_ICONS[type]}
                  valueStyle={{ fontSize: 16 }}
                />
              </Card>
            </Col>
          );
        })}
      </Row>

      <Card>
        <Table
          dataSource={configs}
          columns={columns}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </Card>

      <Modal
        title={`配置 - ${editModal?.model_name ?? ''}`}
        open={!!editModal}
        onCancel={() => setEditModal(null)}
        onOk={handleSave}
        confirmLoading={updateMutation.isPending}
        width={500}
      >
        {editModal && (
          <Form form={form} layout="vertical">
            <Form.Item label="模型名称" name="model_name">
              <Input />
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
              <>
                <Form.Item label="源语言" name="source_lang" initialValue="auto">
                  <Select options={[
                    { value: 'auto', label: '自动检测' },
                    { value: 'zh', label: '中文' },
                    { value: 'en', label: 'English' },
                    { value: 'ja', label: '日本語' },
                  ]} />
                </Form.Item>
              </>
            )}
          </Form>
        )}
      </Modal>
    </div>
  );
}
