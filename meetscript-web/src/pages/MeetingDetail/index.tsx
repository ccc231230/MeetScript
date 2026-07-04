import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Typography,
  Spin,
  Tag,
  Select,
  Input,
  List,
  Button,
  Space,
  App,
  Segmented,
  Tooltip,
} from 'antd';
import {
  PlayCircleOutlined,
  SearchOutlined,
  TranslationOutlined,
  ExportOutlined,
  UserOutlined,
  SoundOutlined,
} from '@ant-design/icons';
import { meetingsAPI } from '../../api/meetings';
import { subtitlesAPI } from '../../api/subtitles';
import { translationAPI } from '../../api/translation';
import { exportsAPI } from '../../api/exports';
import { useSearch } from '../../hooks/useSearch';
import type { Meeting, Subtitle, Translation } from '../../types';

const { Title, Text, Paragraph } = Typography;

const SPEAKER_COLORS = [
  '#1890ff', '#52c41a', '#faad14', '#f5222d',
  '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16',
];

const TARGET_LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'ja', label: '日本語' },
  { value: 'ko', label: '한국어' },
  { value: 'fr', label: 'Français' },
  { value: 'de', label: 'Deutsch' },
  { value: 'es', label: 'Español' },
];

function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export default function MeetingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const { message } = App.useApp();

  const [targetLang, setTargetLang] = useState('en');
  const [viewMode, setViewMode] = useState<'original' | 'bilingual'>('original');
  const [currentTime, setCurrentTime] = useState(0);
  const { query, setQuery } = useSearch(300);
  const videoRef = useRef<HTMLVideoElement>(null);

  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current) {
      setCurrentTime(Math.floor(videoRef.current.currentTime * 1000));
    }
  }, []);

  const { data: meeting, isLoading: meetingLoading } = useQuery({
    queryKey: ['meeting', id],
    queryFn: async () => {
      const res = await meetingsAPI.get(id!);
      return res.data;
    },
    enabled: !!id,
  });

  const { data: subtitles, isLoading: subsLoading } = useQuery({
    queryKey: ['subtitles', id],
    queryFn: async () => {
      return await subtitlesAPI.list(id!);
    },
    enabled: !!id,
  });

  const { data: translations } = useQuery({
    queryKey: ['translations', id, targetLang],
    queryFn: async () => {
      return await translationAPI.list(id!, targetLang);
    },
    enabled: !!id && viewMode === 'bilingual',
  });

  const handleExport = async (format: string) => {
    try {
      const res = await exportsAPI.export({
        meeting_id: id!,
        format: format as 'srt' | 'vtt' | 'json' | 'txt',
        lang: targetLang,
      });
      const blob = res.data as unknown as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `subtitles-${id}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      message.success(`已导出 ${format.toUpperCase()} 格式`);
    } catch {
      message.error('导出失败');
    }
  };

  const handleRequestTranslation = async () => {
    try {
      await translationAPI.request({ meeting_id: id!, target_language: targetLang });
      message.success('翻译任务已提交，请稍候刷新查看');
    } catch {
      message.error('翻译请求失败');
    }
  };

  // Build speaker map for colors
  const speakerMap = useMemo(() => {
    const speakers = new Map<string, string>();
    if (subtitles) {
      const uniqueSpeakers = [...new Set(subtitles.map((s: Subtitle) => s.speaker_label))];
      uniqueSpeakers.forEach((sp, i) => {
        speakers.set(sp, SPEAKER_COLORS[i % SPEAKER_COLORS.length]);
      });
    }
    return speakers;
  }, [subtitles]);

  // Build translation lookup
  const translationMap = useMemo(() => {
    const map = new Map<string, Translation>();
    if (translations) {
      translations.forEach((t: Translation) => {
        map.set(t.subtitle_id, t);
      });
    }
    return map;
  }, [translations]);

  // Filter subtitles by search query
  const filteredSubtitles = useMemo(() => {
    if (!subtitles) return [];
    if (!query.trim()) {
      // Filter by current playback time (show nearby subtitles)
      return subtitles.filter(
        (s: Subtitle) =>
          s.end_time_ms >= currentTime - 30000 &&
          s.start_time_ms <= currentTime + 60000,
      );
    }
    const q = query.toLowerCase();
    return subtitles.filter((s: Subtitle) => s.text.toLowerCase().includes(q));
  }, [subtitles, query, currentTime]);

  const statusColor: Record<string, string> = {
    uploaded: 'blue',
    preprocessing: 'cyan',
    processing: 'processing' as const,
    completed: 'green',
    failed: 'red',
  };

  if (meetingLoading || subsLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  if (!meeting) {
    return <div>会议不存在</div>;
  }

  const m = meeting as Meeting;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>{m.title}</Title>
          <Space style={{ marginTop: 8 }}>
            <Tag color={statusColor[m.status]}>{m.status}</Tag>
            <Text type="secondary">{m.source_language}</Text>
            {m.duration_seconds && (
              <Text type="secondary">
                {Math.floor(m.duration_seconds / 60)} 分钟
              </Text>
            )}
          </Space>
        </div>
        <Space wrap>
          <Select
            value={targetLang}
            onChange={setTargetLang}
            options={TARGET_LANGUAGES}
            style={{ width: 120 }}
            size="small"
          />
          <Segmented
            options={[
              { label: '原文', value: 'original' },
              { label: '双语', value: 'bilingual' },
            ]}
            value={viewMode}
            onChange={(v) => setViewMode(v as 'original' | 'bilingual')}
            size="small"
          />
          <Tooltip title="请求翻译">
            <Button
              icon={<TranslationOutlined />}
              size="small"
              onClick={handleRequestTranslation}
            />
          </Tooltip>
          <Tooltip title="导出字幕">
            <Button
              icon={<ExportOutlined />}
              size="small"
              onClick={() => handleExport('srt')}
            />
          </Tooltip>
        </Space>
      </div>

      {m.file_path && (
        <Card style={{ marginTop: 16 }} size="small" title="视频播放">
          <video
            ref={videoRef}
            controls
            style={{ width: '100%', maxHeight: 400, borderRadius: 4, background: '#000' }}
            onTimeUpdate={handleTimeUpdate}
            preload="metadata"
          >
            <source
              src={`/api/v1/meetings/${m.id}/media?token=${localStorage.getItem('access_token')}`}
              type={m.file_type === 'video' ? 'video/mp4' : 'audio/mpeg'}
            />
            您的浏览器不支持视频播放
          </video>
        </Card>
      )}

      <Card style={{ marginTop: 16 }}>
        <Input
          prefix={<SearchOutlined />}
          placeholder="搜索字幕内容..."
          onChange={(e) => setQuery(e.target.value)}
          allowClear
          style={{ marginBottom: 16 }}
        />

        <div style={{ maxHeight: 'calc(100vh - 300px)', overflow: 'auto' }}>
          {filteredSubtitles.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
              {query.trim()
                ? '没有找到匹配的字幕'
                : '暂无字幕数据'}
            </div>
          ) : (
            <List
              dataSource={filteredSubtitles}
              renderItem={(sub: Subtitle) => {
                const translation = translationMap.get(sub.id);
                const speakerColor = speakerMap.get(sub.speaker_label) ?? '#666';
                const isCandidate = sub.is_candidate;

                return (
                  <div
                    key={sub.id}
                    style={{
                      display: 'flex',
                      gap: 12,
                      padding: '8px 0',
                      borderBottom: '1px solid #f0f0f0',
                      background: isCandidate ? '#fff7e6' : 'transparent',
                      borderRadius: 4,
                      paddingLeft: 8,
                    }}
                    onClick={() => setCurrentTime(sub.start_time_ms)}
                  >
                    <Text
                      style={{
                        color: speakerColor,
                        minWidth: 100,
                        fontWeight: 500,
                        fontSize: 12,
                        cursor: 'pointer',
                      }}
                    >
                      <PlayCircleOutlined style={{ marginRight: 4 }} />
                      {formatTime(sub.start_time_ms)}
                    </Text>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Tag
                          color={speakerColor}
                          style={{ margin: 0, fontSize: 11, lineHeight: '18px' }}
                        >
                          <UserOutlined /> {sub.speaker_label}
                        </Tag>
                        {isCandidate && (
                          <Tag color="orange" style={{ margin: 0, fontSize: 11 }}>
                            候选人
                          </Tag>
                        )}
                        {sub.confidence > 0 && (
                          <Text type="secondary" style={{ fontSize: 10 }}>
                            {Math.round(sub.confidence * 100)}%
                          </Text>
                        )}
                      </div>
                      <Paragraph
                        style={{ margin: '4px 0 0', whiteSpace: 'pre-wrap' }}
                      >
                        <span
                          dangerouslySetInnerHTML={{
                            __html: query.trim()
                              ? sub.text.replace(
                                  new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
                                  '<mark style="background:#ffd666;padding:0 2px">$1</mark>',
                                )
                              : sub.text,
                          }}
                        />
                      </Paragraph>
                      {viewMode === 'bilingual' && translation && (
                        <Paragraph
                          style={{
                            margin: '2px 0 0',
                            color: '#1890ff',
                            fontSize: 13,
                          }}
                        >
                          <SoundOutlined style={{ marginRight: 4 }} />
                          {translation.translated_text}
                        </Paragraph>
                      )}
                    </div>
                  </div>
                );
              }}
            />
          )}
        </div>
      </Card>
    </div>
  );
}
