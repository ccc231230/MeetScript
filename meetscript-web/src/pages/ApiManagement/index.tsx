import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Table,
  Button,
  Typography,
  Modal,
  Form,
  Input,
  InputNumber,
  Tag,
  App,
  Popconfirm,
  Spin,
  Tooltip,
  Empty,
} from 'antd';
import { KeyOutlined, PlusOutlined, CopyOutlined, DeleteOutlined } from '@ant-design/icons';
import { apiKeysAPI } from '../../api/api-keys';
import type { ApiKey, ApiKeyCreateResponse } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text, Paragraph } = Typography;

export default function ApiManagementPage() {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [createModal, setCreateModal] = useState(false);
  const [newKey, setNewKey] = useState<ApiKeyCreateResponse | null>(null);
  const [form] = Form.useForm();

  const { data: keys, isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: async () => {
      const res = await apiKeysAPI.list();
      return res.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: apiKeysAPI.create,
    onSuccess: (res) => {
      setNewKey(res.data);
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      form.resetFields();
    },
    onError: () => message.error('创建失败'),
  });

  const deleteMutation = useMutation({
    mutationFn: apiKeysAPI.delete,
    onSuccess: () => {
      message.success('已删除');
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
    onError: () => message.error('删除失败'),
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => message.success('已复制到剪贴板'));
  };

  const columns: ColumnsType<ApiKey> = [
    {
      title: '名称',
      dataIndex: 'key_name',
      key: 'key_name',
      render: (n: string) => <Text strong>{n}</Text>,
    },
    {
      title: 'Key',
      dataIndex: 'prefix',
      key: 'prefix',
      render: (p: string) => (
        <Text code className="text-xs">{p}****</Text>
      ),
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
      title: '最后使用',
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      width: 170,
      render: (d: string | null) => (
        <Text type="secondary" className="text-xs">
          {d ? new Date(d).toLocaleString() : '从未使用'}
        </Text>
      ),
    },
    {
      title: '过期时间',
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 170,
      render: (d: string | null) => (
        <Text type="secondary" className="text-xs">
          {d ? new Date(d).toLocaleString() : '永不过期'}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, r: ApiKey) => (
        <Popconfirm
          title="确定删除此 API Key？"
          description="删除后不可恢复"
          onConfirm={() => deleteMutation.mutate(r.id)}
          okButtonProps={{ danger: true }}
        >
          <Button size="small" danger icon={<DeleteOutlined />} type="text" />
        </Popconfirm>
      ),
    },
  ];

  if (isLoading) {
    return <Spin size="large" className="block mx-auto mt-24" />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <Title level={4} className="!mb-1 !text-slate-800">
            <KeyOutlined className="mr-2" />
            API Key 管理
          </Title>
          <Text type="secondary">管理用于外部 API 调用的密钥</Text>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => { setNewKey(null); setCreateModal(true); }}
          size="large"
          className="rounded-lg"
        >
          创建 API Key
        </Button>
      </div>

      {/* Keys Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {(!keys || keys.length === 0) ? (
          <div className="py-16">
            <Empty description="暂无 API Key">
              <Button type="primary" icon={<PlusOutlined />}
                onClick={() => { setNewKey(null); setCreateModal(true); }}
              >
                创建第一个 API Key
              </Button>
            </Empty>
          </div>
        ) : (
          <Table
            dataSource={keys}
            columns={columns}
            rowKey="id"
            pagination={false}
            size="middle"
          />
        )}
      </div>

      {/* Create Modal */}
      <Modal
        title={<span className="font-semibold">创建 API Key</span>}
        open={createModal}
        onCancel={() => { setCreateModal(false); setNewKey(null); }}
        footer={newKey ? [
          <Button key="close" onClick={() => { setCreateModal(false); setNewKey(null); }}>
            关闭
          </Button>
        ] : [
          <Button key="cancel" onClick={() => setCreateModal(false)}>取消</Button>,
          <Button key="create" type="primary" loading={createMutation.isPending}
            onClick={() => form.submit()}
          >
            创建
          </Button>,
        ]}
      >
        {newKey ? (
          <div className="space-y-4">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <Text className="text-amber-800 text-sm">
                ⚠️ API Key 已创建。请立即复制保存，关闭后将不可见！
              </Text>
            </div>
            <Input.Password
              value={newKey.api_key}
              readOnly
              className="rounded-lg"
              addonAfter={
                <Tooltip title="复制">
                  <CopyOutlined
                    className="cursor-pointer hover:text-primary-500"
                    onClick={() => copyToClipboard(newKey.api_key)}
                  />
                </Tooltip>
              }
            />
            <Text type="secondary" className="text-xs">
              前缀: <Text code>{newKey.prefix}</Text>
            </Text>
          </div>
        ) : (
          <Form
            form={form}
            layout="vertical"
            onFinish={(values) => createMutation.mutate(values)}
          >
            <Form.Item
              name="key_name"
              label="Key 名称"
              rules={[{ required: true, message: '请输入名称' }]}
            >
              <Input placeholder="例如：生产环境 API Key" className="rounded-lg" />
            </Form.Item>
            <Form.Item name="rate_limit" label="速率限制 (次/分钟)" initialValue={60}>
              <InputNumber style={{ width: '100%' }} min={1} max={1000} />
            </Form.Item>
            <Form.Item name="expires_in_days" label="有效期 (天)">
              <InputNumber
                style={{ width: '100%' }} min={1} max={3650}
                placeholder="留空则永不过期"
              />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  );
}
