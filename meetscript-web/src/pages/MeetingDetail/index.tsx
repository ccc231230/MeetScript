import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Typography,
  Spin,
  Tag,
  Select,
  Input,
  Button,
  Space,
  App,
  Segmented,
  Tooltip,
  Empty,
} from 'antd';
import {
  PlayCircleOutlined,
  SearchOutlined,
  TranslationOutlined,
  ExportOutlined,
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
  '#4A90D9', '#6ABF69', '#E8A838', '#E05555',
  '#8E6ACF', '#3CB8B8', '#E05B9E', '#E88A3C',
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
  const { message } = App.useApp();

  const [targetLang, setTargetLang] = useState('en');
  const [viewMode, setViewMode] = useState<'original' | 'bilingual'>('original');
  const [currentTime, setCurrentTime] = useState(0);
  const { query, setQuery } = useSearch(300);
  const videoRef = useRef<HTMLVideoElement>(null);
  const subtitleListRef = useRef<HTMLDivElement>(null);
  const activeSubRef = useRef<HTMLDivElement>(null);

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
    // Auto-poll while meeting is still processing (every 5 seconds)
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 5000; // initial load
      if (data.status === 'completed' || data.status === 'failed') return false;
      return 5000;
    },
  });

  const { data: subtitles, isLoading: subsLoading } = useQuery({
    queryKey: ['subtitles', id],
    queryFn: async () => {
      return await subtitlesAPI.list(id!);
    },
    enabled: !!id,
    // Auto-poll while meeting is still processing
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data || (Array.isArray(data) && data.length === 0)) return 5000;
      return false; // subtitles loaded, stop polling
    },
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

  // Filter subtitles by search query (show all when not searching)
  const filteredSubtitles = useMemo(() => {
    if (!subtitles) return [];
    if (!query.trim()) return subtitles;
    const q = query.toLowerCase();
    return subtitles.filter((s: Subtitle) => s.text.toLowerCase().includes(q));
  }, [subtitles, query]);

  // Find the index of the currently active subtitle
  const activeIndex = useMemo(() => {
    if (!filteredSubtitles.length) return -1;
    // Binary search for the subtitle covering currentTime
    let lo = 0, hi = filteredSubtitles.length - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      const s = filteredSubtitles[mid];
      if (currentTime >= s.start_time_ms && currentTime <= s.end_time_ms) {
        return mid;
      }
      if (currentTime < s.start_time_ms) {
        hi = mid - 1;
      } else {
        lo = mid + 1;
      }
    }
    // Find the last subtitle whose end_time <= currentTime
    for (let i = filteredSubtitles.length - 1; i >= 0; i--) {
      if (filteredSubtitles[i].end_time_ms <= currentTime) return i;
    }
    return -1;
  }, [filteredSubtitles, currentTime]);

  // Auto-scroll to active subtitle
  useEffect(() => {
    if (activeIndex >= 0 && activeSubRef.current) {
      activeSubRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [activeIndex]);

  // Reset scroll when search results change
  const prevSubCount = useRef(0);
  useEffect(() => {
    if (filteredSubtitles.length !== prevSubCount.current && subtitleListRef.current) {
      prevSubCount.current = filteredSubtitles.length;
      subtitleListRef.current.scrollTop = 0;
    }
  }, [filteredSubtitles.length]);

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

  const handleSubClick = (startTimeMs: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = startTimeMs / 1000;
      videoRef.current.play();
    }
  };

  // ─── Toolbar ────────────────────────────────────────────────
  const toolbar = (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      flexWrap: 'wrap', gap: 8, marginBottom: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Title level={5} style={{ margin: 0, fontWeight: 600 }}>{m.title}</Title>
        <Tag color={statusColor[m.status]} style={{ margin: 0 }}>{m.status}</Tag>
        <Text type="secondary" style={{ fontSize: 13 }}>{m.source_language}</Text>
        {m.duration_seconds && (
          <Text type="secondary" style={{ fontSize: 13 }}>
            {Math.floor(m.duration_seconds / 60)} 分钟
          </Text>
        )}
      </div>
      <Space wrap size="small">
        <Select
          value={targetLang}
          onChange={setTargetLang}
          options={TARGET_LANGUAGES}
          style={{ width: 110 }}
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
          <Button icon={<TranslationOutlined />} size="small" onClick={handleRequestTranslation} />
        </Tooltip>
        <Tooltip title="导出字幕">
          <Button icon={<ExportOutlined />} size="small" onClick={() => handleExport('srt')} />
        </Tooltip>
      </Space>
    </div>
  );

  return (
    <div>
      {toolbar}

      {/* ─── Main split layout: Video (left) + Subtitles (right) ─── */}
      <div style={{
        display: 'flex', gap: 16,
        height: 'calc(100vh - 180px)',
        minHeight: 500,
      }}>
        {/* ─── LEFT: Video Panel ─── */}
        <div style={{
          flex: '0 0 52%',
          display: 'flex', flexDirection: 'column',
          minWidth: 0,
        }}>
          {m.file_path ? (
            <Card
              size="small"
              style={{
                flex: 1, display: 'flex', flexDirection: 'column',
                background: '#000', borderRadius: 8, overflow: 'hidden',
                border: 'none',
              }}
              styles={{ body: { flex: 1, padding: 0, display: 'flex' } }}
            >
              <video
                ref={videoRef}
                controls
                style={{ width: '100%', height: '100%', objectFit: 'contain', background: '#000' }}
                onTimeUpdate={handleTimeUpdate}
                preload="metadata"
              >
                <source
                  src={`/api/v1/meetings/${m.id}/media?token=${localStorage.getItem('access_token')}`}
                  type={m.file_type === 'video' ? 'video/mp4' : 'audio/mpeg'}
                />
              </video>
            </Card>
          ) : (
            <Card size="small" style={{ flex: 1 }}>
              <Empty description="无媒体文件" />
            </Card>
          )}
        </div>

        {/* ─── RIGHT: Subtitle Panel ─── */}
        <div style={{
          flex: 1,
          display: 'flex', flexDirection: 'column',
          minWidth: 380,
          background: '#fff',
          borderRadius: 8,
          border: '1px solid #e8e8e8',
          overflow: 'hidden',
        }}>
          {/* Search bar */}
          <div style={{
            padding: '12px 16px',
            borderBottom: '1px solid #f0f0f0',
            background: '#fafafa',
          }}>
            <Input
              prefix={<SearchOutlined style={{ color: '#bbb' }} />}
              placeholder="搜索字幕内容..."
              onChange={(e) => setQuery(e.target.value)}
              allowClear
              size="small"
              variant="borderless"
              style={{ background: '#fff', borderRadius: 6 }}
            />
          </div>

          {/* Subtitle list */}
          <div
            ref={subtitleListRef}
            style={{
              flex: 1,
              overflow: 'auto',
              padding: '4px 0',
            }}
          >
            {filteredSubtitles.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
                {query.trim() ? '没有找到匹配的字幕' : '暂无字幕数据'}
              </div>
            ) : (
              filteredSubtitles.map((sub: Subtitle, idx: number) => {
                const translation = translationMap.get(sub.id);
                const speakerColor = speakerMap.get(sub.speaker_label) ?? '#666';
                const isActive = idx === activeIndex;
                const isCandidate = sub.is_candidate;

                return (
                  <div
                    key={sub.id}
                    ref={isActive ? activeSubRef : null}
                    onClick={() => handleSubClick(sub.start_time_ms)}
                    style={{
                      display: 'flex',
                      gap: 0,
                      padding: '10px 16px',
                      cursor: 'pointer',
                      transition: 'background 0.15s',
                      background: isActive
                        ? '#E8F4FD'
                        : isCandidate
                          ? '#fffbe6'
                          : 'transparent',
                      borderLeft: isActive ? `3px solid ${speakerColor}` : '3px solid transparent',
                      borderBottom: '1px solid #f5f5f5',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) e.currentTarget.style.background = '#fafafa';
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) e.currentTarget.style.background = isCandidate ? '#fffbe6' : 'transparent';
                    }}
                  >
                    {/* Timestamp column */}
                    <div style={{
                      flexShrink: 0, width: 52,
                      textAlign: 'center', paddingTop: 2,
                    }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSubClick(sub.start_time_ms);
                        }}
                        style={{
                          border: 'none', background: 'none', cursor: 'pointer',
                          color: isActive ? speakerColor : '#888',
                          fontSize: 12, fontWeight: isActive ? 600 : 400,
                          padding: '2px 4px', borderRadius: 4,
                          transition: 'color 0.15s',
                          lineHeight: 1.3,
                        }}
                      >
                        <PlayCircleOutlined style={{ fontSize: 10, marginRight: 2, display: 'block', margin: '0 auto 1px' }} />
                        {formatTime(sub.start_time_ms)}
                      </button>
                    </div>

                    {/* Content column */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      {/* Speaker + confidence */}
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: 6,
                        marginBottom: 3,
                      }}>
                        <span style={{
                          display: 'inline-block',
                          width: 6, height: 6, borderRadius: '50%',
                          background: speakerColor,
                          flexShrink: 0,
                        }} />
                        <Text style={{
                          fontSize: 12, color: speakerColor,
                          fontWeight: 500, lineHeight: 1,
                        }}>
                          {sub.speaker_label}
                        </Text>
                        {isCandidate && (
                          <Tag color="orange" style={{ margin: 0, fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>
                            候选
                          </Tag>
                        )}
                        {sub.confidence > 0 && (
                          <Text type="secondary" style={{ fontSize: 10, marginLeft: 'auto' }}>
                            {Math.round(sub.confidence * 100)}%
                          </Text>
                        )}
                      </div>

                      {/* Main text */}
                      <Paragraph
                        style={{
                          margin: 0,
                          fontSize: 14,
                          lineHeight: 1.7,
                          color: isActive ? '#111' : '#333',
                          fontWeight: isActive ? 500 : 400,
                          wordBreak: 'break-word',
                        }}
                      >
                        <span
                          dangerouslySetInnerHTML={{
                            __html: query.trim()
                              ? sub.text.replace(
                                  new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
                                  '<mark style="background:#ffd666;padding:0 2px;border-radius:2px">$1</mark>',
                                )
                              : sub.text,
                          }}
                        />
                      </Paragraph>

                      {/* Translation text */}
                      {viewMode === 'bilingual' && translation && (
                        <Paragraph
                          style={{
                            margin: '4px 0 0',
                            color: '#4A90D9',
                            fontSize: 13,
                            lineHeight: 1.6,
                          }}
                        >
                          <SoundOutlined style={{ marginRight: 4, fontSize: 11 }} />
                          {translation.translated_text}
                        </Paragraph>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
