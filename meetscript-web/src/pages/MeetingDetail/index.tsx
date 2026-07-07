import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
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
  Avatar,
} from 'antd';
import {
  PlayCircleOutlined,
  SearchOutlined,
  TranslationOutlined,
  ExportOutlined,
  SoundOutlined,
  PauseCircleOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { meetingsAPI } from '../../api/meetings';
import { subtitlesAPI } from '../../api/subtitles';
import { translationAPI } from '../../api/translation';
import { exportsAPI } from '../../api/exports';
import { useSearch } from '../../hooks/useSearch';
import type { Meeting, Subtitle, Translation } from '../../types';

const { Text } = Typography;

const SPEAKER_COLORS: readonly string[] = [
  '#0D9488', '#6366F1', '#F59E0B', '#EF4444',
  '#8B5CF6', '#06B6D4', '#EC4899', '#F97316',
] as const;

const TARGET_LANGUAGES = [
  { value: 'zh', label: '中文' },
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

function SpeakerAvatar({ label, color, size = 28 }: { label: string; color: string; size?: number }) {
  const initial = (label || '?')[0].toUpperCase();
  return (
    <Avatar
      size={size}
      style={{
        backgroundColor: color,
        verticalAlign: 'middle',
        fontSize: size * 0.45,
        fontWeight: 700,
        flexShrink: 0,
      }}
    >
      {initial}
    </Avatar>
  );
}

export default function MeetingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { message } = App.useApp();
  const [targetLang, setTargetLang] = useState('zh');
  const [viewMode, setViewMode] = useState<'original' | 'bilingual' | 'translation'>('original');
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [translating, setTranslating] = useState(false);
  const { query, setQuery } = useSearch(300);
  const videoRef = useRef<HTMLVideoElement>(null);
  const subtitleListRef = useRef<HTMLDivElement>(null);
  const activeSubRef = useRef<HTMLDivElement>(null);
  const autoTranslatedRef = useRef<Set<string>>(new Set());

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
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 5000;
      if (data.status === 'completed' || data.status === 'failed') return false;
      return 5000;
    },
  });

  const { data: subtitles, isLoading: subsLoading } = useQuery({
    queryKey: ['subtitles', id],
    queryFn: async () => await subtitlesAPI.list(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data || (Array.isArray(data) && data.length === 0)) return 5000;
      return false;
    },
  });

  const { data: translations, isFetched: transFetched } = useQuery({
    queryKey: ['translations', id, targetLang],
    queryFn: async () => await translationAPI.list(id!, targetLang),
    enabled: !!id,
    refetchInterval: translating ? 3000 : false,
  });

  // Auto-switch to bilingual when translations arrive
  const prevHasTranslations = useRef(false);
  useEffect(() => {
    const hasTranslations = translations && translations.length > 0;
    if (hasTranslations && !prevHasTranslations.current && viewMode === 'original') {
      setViewMode('bilingual');
    }
    prevHasTranslations.current = hasTranslations || false;
  }, [translations]);

  useEffect(() => {
    if (translations && translations.length > 0 && viewMode === 'original') {
      setViewMode('bilingual');
    }
  }, [targetLang]);

  // Auto-trigger translation
  useEffect(() => {
    if (!transFetched || targetLang === meeting?.source_language) return;
    if (translations && translations.length === 0 && !autoTranslatedRef.current.has(targetLang)) {
      autoTranslatedRef.current.add(targetLang);
      setTranslating(true);
      handleRequestTranslation();
    }
    if (translations && translations.length > 0) {
      setTranslating(false);
    }
  }, [targetLang, transFetched, meeting?.source_language]);

  const handleExport = async (format: string) => {
    try {
      const res = await exportsAPI.export({
        meeting_id: id!, format: format as 'srt' | 'vtt' | 'json' | 'txt', lang: targetLang,
      });
      const blob = res.data as unknown as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `subtitles-${id}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      message.success(`已导出 ${format.toUpperCase()} 格式`);
    } catch { message.error('导出失败'); }
  };

  const handleRequestTranslation = async () => {
    try {
      setTranslating(true);
      await translationAPI.request({ meeting_id: id!, target_languages: [targetLang] });
      message.success(`翻译任务已提交（${targetLang}），处理中...`);
    } catch {
      setTranslating(false);
      message.error('翻译请求失败');
    }
  };

  const speakerMap = useMemo(() => {
    const speakers = new Map<string, string>();
    if (subtitles) {
      [...new Set(subtitles.map((s: Subtitle) => s.speaker_label))].forEach((sp, i) => {
        speakers.set(sp, SPEAKER_COLORS[i % SPEAKER_COLORS.length]);
      });
    }
    return speakers;
  }, [subtitles]);

  const translationMap = useMemo(() => {
    const map = new Map<string, Translation>();
    if (translations) translations.forEach((t: Translation) => map.set(t.subtitle_id, t));
    return map;
  }, [translations]);

  const filteredSubtitles = useMemo(() => {
    if (!subtitles) return [];
    if (!query.trim()) return subtitles;
    const q = query.toLowerCase();
    return subtitles.filter((s: Subtitle) => s.text.toLowerCase().includes(q));
  }, [subtitles, query]);

  const activeIndex = useMemo(() => {
    if (!filteredSubtitles.length) return -1;
    let lo = 0, hi = filteredSubtitles.length - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      const s = filteredSubtitles[mid];
      if (currentTime >= s.start_time_ms && currentTime <= s.end_time_ms) return mid;
      if (currentTime < s.start_time_ms) hi = mid - 1;
      else lo = mid + 1;
    }
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

  const prevSubCount = useRef(0);
  useEffect(() => {
    if (filteredSubtitles.length !== prevSubCount.current && subtitleListRef.current) {
      prevSubCount.current = filteredSubtitles.length;
      subtitleListRef.current.scrollTop = 0;
    }
  }, [filteredSubtitles.length]);

  const statusColor: Record<string, string> = {
    uploaded: 'blue', preprocessing: 'cyan',
    processing: 'processing' as const, completed: 'green', failed: 'red',
  };
  const statusLabel: Record<string, string> = {
    uploaded: '已上传', preprocessing: '预处理中',
    processing: '处理中', completed: '已完成', failed: '失败',
  };

  if (meetingLoading || subsLoading) {
    return <Spin size="large" className="block mx-auto mt-24" />;
  }
  if (!meeting) return <div className="text-center py-20 text-slate-400">会议不存在</div>;

  const m = meeting as Meeting;

  const handleSubClick = (startTimeMs: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = startTimeMs / 1000;
      videoRef.current.play();
    }
  };

  const togglePlay = () => {
    if (videoRef.current) {
      if (videoRef.current.paused) videoRef.current.play();
      else videoRef.current.pause();
    }
  };

  // ─── Feishu-style Subtitle Row ───
  const renderSubtitleRow = (sub: Subtitle, idx: number) => {
    const translation = translationMap.get(sub.id);
    const speakerColor = speakerMap.get(sub.speaker_label) ?? '#64748B';
    const isActive = idx === activeIndex;

    return (
      <div
        key={sub.id}
        ref={isActive ? activeSubRef : null}
        onClick={() => handleSubClick(sub.start_time_ms)}
        className="subtitle-active group"
        style={{
          display: 'flex',
          gap: 12,
          padding: '14px 20px',
          cursor: 'pointer',
          background: isActive
            ? 'linear-gradient(90deg, rgba(13,148,136,0.06) 0%, rgba(13,148,136,0.02) 100%)'
            : 'transparent',
          borderLeft: isActive ? `3px solid ${speakerColor}` : '3px solid transparent',
          borderBottom: '1px solid #F1F5F9',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => {
          if (!isActive) e.currentTarget.style.background = '#F8FAFC';
        }}
        onMouseLeave={(e) => {
          if (!isActive) e.currentTarget.style.background = 'transparent';
        }}
      >
        {/* Timestamp */}
        <div className="flex flex-col items-center shrink-0" style={{ width: 48 }}>
          <button
            onClick={(e) => { e.stopPropagation(); handleSubClick(sub.start_time_ms); }}
            className="flex flex-col items-center gap-0.5 border-none bg-transparent cursor-pointer transition-colors"
            style={{ color: isActive ? speakerColor : '#94A3B8', padding: '2px 4px', borderRadius: 6 }}
          >
            <PlayCircleOutlined style={{ fontSize: 12 }} />
            <span style={{
              fontSize: 11,
              fontWeight: isActive ? 600 : 400,
              fontVariantNumeric: 'tabular-nums',
            }}>
              {formatTime(sub.start_time_ms)}
            </span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Speaker row */}
          <div className="flex items-center gap-2 mb-2">
            <SpeakerAvatar label={sub.speaker_label} color={speakerColor} size={22} />
            <span style={{
              fontSize: 12, fontWeight: 600, color: speakerColor,
              lineHeight: 1,
            }}>
              {sub.speaker_label}
            </span>
            {sub.is_candidate && (
              <Tag color="orange" className="!m-0 !text-[10px] !leading-4 !px-1">候选</Tag>
            )}
            {sub.confidence > 0 && (
              <span className="text-[10px] text-slate-400 ml-auto">
                {Math.round(sub.confidence * 100)}%
              </span>
            )}
          </div>

          {/* Original text */}
          {viewMode !== 'translation' && (
            <p style={{
              margin: 0,
              fontSize: 15,
              lineHeight: 1.75,
              color: isActive ? '#0F172A' : '#334155',
              fontWeight: isActive ? 500 : 400,
              wordBreak: 'break-word',
            }}>
              {query.trim() ? (
                <span dangerouslySetInnerHTML={{
                  __html: sub.text.replace(
                    new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
                    '<mark style="background:#FDE68A;padding:0 2px;border-radius:2px;color:#1E293B">$1</mark>',
                  ),
                }} />
              ) : sub.text}
            </p>
          )}

          {/* Translation */}
          {(viewMode === 'bilingual' || viewMode === 'translation') && translation && (
            <p style={{
              margin: viewMode === 'bilingual' ? '6px 0 0' : 0,
              color: '#0D9488',
              fontSize: viewMode === 'translation' ? 15 : 14,
              fontWeight: viewMode === 'translation' && isActive ? 500 : 400,
              lineHeight: 1.7,
            }}>
              {viewMode === 'bilingual' && (
                <SoundOutlined style={{ marginRight: 5, fontSize: 11, opacity: 0.6 }} />
              )}
              {translation.translated_text}
            </p>
          )}
          {viewMode === 'translation' && !translation && (
            <p style={{
              margin: 0, fontSize: 15, lineHeight: 1.7,
              color: '#94A3B8', fontStyle: 'italic',
            }}>
              {sub.text}
            </p>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 160px)', minHeight: 560 }}>
      {/* ─── Toolbar ─── */}
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4 shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <h1 className="text-lg font-bold text-slate-800 truncate m-0">{m.title}</h1>
          <Tag color={statusColor[m.status]}>{statusLabel[m.status]}</Tag>
          <Text type="secondary" className="text-xs">{m.source_language?.toUpperCase()}</Text>
          {m.duration_seconds && (
            <Text type="secondary" className="text-xs">
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
              { label: '译文', value: 'translation' },
            ]}
            value={viewMode}
            onChange={(v) => setViewMode(v as 'original' | 'bilingual' | 'translation')}
            size="small"
          />
          <Tooltip title={translating ? '翻译处理中...' : '请求翻译'}>
            <Button icon={<TranslationOutlined />} size="small" onClick={handleRequestTranslation} loading={translating} />
          </Tooltip>
          <Tooltip title="导出字幕">
            <Button icon={<ExportOutlined />} size="small" onClick={() => handleExport('srt')} />
          </Tooltip>
        </Space>
      </div>

      {/* ─── Main Split: Video (Left) + Subtitles (Right) - Feishu Style ─── */}
      <div className="flex gap-0 flex-1 min-h-0 rounded-xl overflow-hidden border border-slate-200 shadow-sm">
        {/* LEFT: Video Panel - Dark background like Feishu */}
        <div className="flex-[0_0_50%] flex flex-col min-w-0 bg-[#1a1a2e] relative">
          {m.file_path ? (
            <>
              <video
                ref={videoRef}
                controls
                className="w-full flex-1 object-contain"
                style={{ background: '#0f0f1a' }}
                onTimeUpdate={handleTimeUpdate}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                preload="metadata"
              >
                <source
                  src={`/api/v1/meetings/${m.id}/media?token=${localStorage.getItem('access_token')}`}
                  type={m.file_type === 'video' ? 'video/mp4' : 'audio/mpeg'}
                />
              </video>

              {/* Feishu-style floating play/pause overlay */}
              {!isPlaying && subtitles && subtitles.length > 0 && (
                <div
                  className="absolute inset-0 flex items-center justify-center cursor-pointer"
                  style={{ background: 'rgba(0,0,0,0.3)' }}
                  onClick={togglePlay}
                >
                  <div
                    className="flex items-center justify-center rounded-full transition-transform hover:scale-110"
                    style={{
                      width: 64, height: 64,
                      background: 'rgba(255,255,255,0.15)',
                      backdropFilter: 'blur(8px)',
                    }}
                  >
                    <PlayCircleOutlined style={{ fontSize: 32, color: '#fff' }} />
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <Empty description="无媒体文件" />
            </div>
          )}
        </div>

        {/* RIGHT: Subtitle Panel - Feishu-style clean list */}
        <div className="flex-1 flex flex-col min-w-[380px] bg-white">
          {/* Search bar */}
          <div className="shrink-0 px-5 py-3 border-b border-slate-100 bg-white">
            <Input
              prefix={<SearchOutlined className="text-slate-400" />}
              placeholder="搜索字幕内容..."
              onChange={(e) => setQuery(e.target.value)}
              allowClear
              size="middle"
              variant="borderless"
              className="bg-slate-50 rounded-lg"
            />
          </div>

          {/* Translation pending notice */}
          {translating && translations && translations.length === 0 && (
            <div className="shrink-0 flex items-center gap-3 px-5 py-3 bg-primary-50 border-b border-primary-100">
              <Spin size="small" />
              <Text className="text-primary-700 text-sm">
                正在翻译为 {TARGET_LANGUAGES.find(l => l.value === targetLang)?.label || targetLang}...
              </Text>
            </div>
          )}

          {/* Subtitle list */}
          <div ref={subtitleListRef} className="flex-1 overflow-y-auto">
            {filteredSubtitles.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-400">
                <SearchOutlined style={{ fontSize: 40, marginBottom: 12 }} />
                <Text type="secondary">
                  {query.trim() ? '没有找到匹配的字幕' : '暂无字幕数据'}
                </Text>
              </div>
            ) : (
              <div className="pb-4">
                {filteredSubtitles.map((sub: Subtitle, idx: number) => renderSubtitleRow(sub, idx))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
