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
  InputNumber,
  Tag,
  Space,
  App,
  Popconfirm,
  Spin,
  Tooltip,
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
    { title: '名称', dataIndex: 'key_name', key: 'key_name' },
    {
      title: 'Key',
      dataIndex: 'prefix',
      key: 'prefix',
      render: (p: string) => <Text code>{p}****</Text>,
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
      render: (d: string | null) => (d ? new Date(d).toLocaleString() : '从未使用'),
    },
    {
      title: '过期时间',
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 170,
      render: (d: string | null) => (d ? new Date(d).toLocaleString() : '永不过期'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, r: ApiKey) => (
        <Popconfirm
          title="确定删除此 API Key？"
          onConfirm={() => deleteMutation.mutate(r.id)}
        >
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  if (isLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>API Key 管理</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setNewKey(null);
            setCreateModal(true);
          }}
        >
          创建 API Key
        </Button>
      </div>

      <Card style={{ marginTop: 16 }}>
        <Table
          dataSource={keys}
          columns={columns}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </Card>

      <Modal
        title="创建 API Key"
        open={createModal}
        onCancel={() => {
          setCreateModal(false);
          setNewKey(null);
        }}
        footer={newKey ? [
          <Button key="close" onClick={() => { setCreateModal(false); setNewKey(null); }}>
            关闭
          </Button>
        ] : [
          <Button key="cancel" onClick={() => setCreateModal(false)}>取消</Button>,
          <Button
            key="create"
            type="primary"
            loading={createMutation.isPending}
            onClick={() => form.submit()}
          >
            创建
          </Button>,
        ]}
      >
        {newKey ? (
          <div>
            <Paragraph>
              <Text strong>API Key 已创建。请立即复制，关闭后将不可见！</Text>
            </Paragraph>
            <Input.Password
              value={newKey.api_key}
              readOnly
              addonAfter={
                <Tooltip title="复制">
                  <CopyOutlined
                    style={{ cursor: 'pointer' }}
                    onClick={() => copyToClipboard(newKey.api_key)}
                  />
                </Tooltip>
              }
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">前缀: {newKey.prefix}</Text>
            </div>
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
              <Input placeholder="例如：生产环境 API Key" />
            </Form.Item>
            <Form.Item name="rate_limit" label="速率限制 (次/分钟)" initialValue={60}>
              <InputNumber style={{ width: '100%' }} min={1} max={1000} />
            </Form.Item>
            <Form.Item name="expires_in_days" label="有效期 (天)">
              <InputNumber style={{ width: '100%' }} min={1} max={3650} placeholder="留空则永不过期" />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </div>
  );
}
