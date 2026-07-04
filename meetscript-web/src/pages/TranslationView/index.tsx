import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Card,
  Table,
  Typography,
  Tag,
  Select,
  Input,
  Button,
  Space,
  App,
  Spin,
} from 'antd';
import { EditOutlined, SaveOutlined, ExportOutlined } from '@ant-design/icons';
import { subtitlesAPI } from '../../api/subtitles';
import { translationAPI } from '../../api/translation';
import { exportsAPI } from '../../api/exports';
import type { Subtitle, Translation } from '../../types';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;

const TARGET_LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'ja', label: '日本語' },
  { value: 'ko', label: '한국어' },
  { value: 'fr', label: 'Français' },
  { value: 'de', label: 'Deutsch' },
  { value: 'es', label: 'Español' },
];

export default function TranslationViewPage() {
  const { meetingId } = useParams<{ meetingId: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [targetLang, setTargetLang] = useState('en');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  const { data: subtitles, isLoading: subsLoading } = useQuery({
    queryKey: ['subtitles', meetingId],
    queryFn: async () => {
      return await subtitlesAPI.list(meetingId!);
    },
    enabled: !!meetingId,
  });

  const { data: translations, refetch } = useQuery({
    queryKey: ['translations', meetingId, targetLang],
    queryFn: async () => {
      return await translationAPI.list(meetingId!, targetLang);
    },
    enabled: !!meetingId,
  });

  const handleRequestTranslation = async () => {
    try {
      await translationAPI.request({ meeting_id: meetingId!, target_language: targetLang });
      message.success('翻译任务已提交');
      setTimeout(() => refetch(), 3000);
    } catch {
      message.error('翻译请求失败');
    }
  };

  const handleStartEdit = (sub: Subtitle, tr?: Translation) => {
    setEditingId(sub.id);
    setEditText(tr?.translated_text ?? '');
  };

  const handleSaveEdit = async (sub: Subtitle) => {
    const tr = translationMap.get(sub.id);
    const translationId = tr?.id;
    if (!translationId) {
      message.error('翻译记录不存在');
      return;
    }
    try {
      await translationAPI.update(translationId, editText);
      message.success('翻译已保存');
      setEditingId(null);
      refetch();
    } catch {
      message.error('保存失败');
    }
  };

  const handleExport = async (format: string) => {
    try {
      const res = await exportsAPI.export({
        meeting_id: meetingId!,
        format: format as 'csv' | 'json',
        lang: targetLang,
      });
      const blob = res.data as unknown as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `translations-${meetingId}-${targetLang}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('导出成功');
    } catch {
      message.error('导出失败');
    }
  };

  // Build translation lookup
  const translationMap = new Map<string, Translation>();
  if (translations) {
    translations.forEach((t: Translation) => translationMap.set(t.subtitle_id, t));
  }

  if (subsLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  const columns: ColumnsType<Subtitle> = [
    {
      title: '时间',
      dataIndex: 'start_time_ms',
      key: 'time',
      width: 100,
      render: (ms: number, r: Subtitle) => {
        const start = formatMs(ms);
        const end = formatMs(r.end_time_ms);
        return <Text style={{ fontSize: 11 }}>{start} - {end}</Text>;
      },
    },
    {
      title: '说话人',
      dataIndex: 'speaker_label',
      key: 'speaker',
      width: 100,
      render: (s: string) => <Tag>{s}</Tag>,
    },
    {
      title: '原文',
      dataIndex: 'text',
      key: 'original',
      render: (t: string) => <Text>{t}</Text>,
    },
    {
      title: '译文',
      key: 'translation',
      render: (_: unknown, r: Subtitle) => {
        const tr = translationMap.get(r.id);
        if (editingId === r.id) {
          return (
            <Space direction="vertical" style={{ width: '100%' }}>
              <Input.TextArea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                rows={2}
              />
              <Space>
                <Button
                  size="small"
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={() => handleSaveEdit(r)}
                >
                  保存
                </Button>
                <Button size="small" onClick={() => setEditingId(null)}>
                  取消
                </Button>
              </Space>
            </Space>
          );
        }
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Text style={{ color: tr ? '#1890ff' : '#ccc' }}>
              {tr?.translated_text ?? '未翻译'}
            </Text>
            <Button
              size="small"
              icon={<EditOutlined />}
              type="link"
              onClick={() => handleStartEdit(r, tr)}
            />
          </div>
        );
      },
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <Title level={4} style={{ margin: 0 }}>翻译查看</Title>
        <Space wrap>
          <Select
            value={targetLang}
            onChange={setTargetLang}
            options={TARGET_LANGUAGES}
            style={{ width: 120 }}
          />
          <Button onClick={handleRequestTranslation}>请求翻译</Button>
          <Button icon={<ExportOutlined />} onClick={() => handleExport('csv')}>
            导出 CSV
          </Button>
        </Space>
      </div>

      <Card style={{ marginTop: 16 }}>
        <Table
          dataSource={subtitles}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 30, showSizeChanger: true }}
          size="small"
        />
      </Card>
    </div>
  );
}

function formatMs(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}
