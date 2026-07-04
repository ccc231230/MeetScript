import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Input,
  Typography,
  List,
  Tag,
  Space,
  Button,
  Spin,
  Empty,
} from 'antd';
import { SearchOutlined, PlayCircleOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { searchAPI } from '../../api/search';
import { useSearchStore } from '../../stores/searchStore';
import { useSearch } from '../../hooks/useSearch';
import type { Subtitle } from '../../types';

const { Title, Text } = Typography;

export default function SearchResultPage() {
  const navigate = useNavigate();
  const { query, setQuery, setQueryImmediate } = useSearch(400);
  const {
    result,
    loading,
    filters,
    setResult,
    setLoading,
  } = useSearchStore();

  const { refetch } = useQuery({
    queryKey: ['search', query, filters],
    queryFn: async () => {
      if (!query.trim()) {
        setResult(null);
        setLoading(false);
        return null;
      }
      setLoading(true);
      try {
        const res = await searchAPI.searchSubtitles({
          q: query,
          meeting_id: filters.meeting_id,
          speaker: filters.speaker,
          time_from: filters.time_from,
          time_to: filters.time_to,
          page: 1,
          page_size: 50,
        });
        setResult(res.data);
      } finally { setLoading(false); }
      return null;
    },
    enabled: !!query.trim(),
  });

  const handleJumpToMeeting = (meetingId: string, startTimeMs: number) => {
    navigate(`/meetings/${meetingId}?t=${startTimeMs}`);
  };

  return (
    <div className="space-y-6">
      <div>
        <Title level={4} className="!mb-1 !text-slate-800">全局搜索</Title>
        <Text type="secondary">跨会议搜索字幕内容，快速定位关键信息</Text>
      </div>

      {/* Search Bar */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <Input.Search
          placeholder="搜索会议字幕内容（支持关键词、说话人筛选）"
          onChange={(e) => setQuery(e.target.value)}
          onSearch={(value) => setQueryImmediate(value)}
          size="large"
          enterButton={
            <Button type="primary" icon={<SearchOutlined />} className="rounded-r-lg">
              搜索
            </Button>
          }
          className="[&_.ant-input]:rounded-l-lg [&_.ant-btn]:h-10"
        />

        <div className="mt-3 flex gap-3">
          <Input
            placeholder="按说话人筛选"
            allowClear
            className="max-w-[180px] rounded-lg"
            size="small"
            onChange={(e) => useSearchStore.getState().setFilters({ speaker: e.target.value || undefined })}
          />
        </div>
      </div>

      {/* Results */}
      <div>
        {loading && <Spin size="large" className="block mx-auto mt-12" />}

        {!loading && !result && query.trim() && (
          <Empty description="未找到匹配的结果" className="mt-16" />
        )}

        {!loading && result && (!result.items || result.items.length === 0) && (
          <Empty description={`未找到关于 "${query}" 的结果`} className="mt-16" />
        )}

        {result && result.items && result.items.length > 0 && (
          <>
            <div className="mb-4 flex items-center justify-between">
              <Text type="secondary">
                找到 <Text strong className="text-primary-600">{result.total}</Text> 条匹配结果
              </Text>
            </div>

            <div className="space-y-2">
              {result.items.map((item: Subtitle, idx: number) => (
                <div
                  key={`${item.id}-${idx}`}
                  onClick={() => handleJumpToMeeting(item.meeting_id, item.start_time_ms)}
                  className="bg-white rounded-lg border border-slate-200 p-4 cursor-pointer
                    hover:border-primary-200 hover:shadow-sm transition-all duration-200 group"
                >
                  <div className="flex items-start gap-4">
                    <Button
                      icon={<PlayCircleOutlined />}
                      type="text"
                      size="small"
                      className="mt-1 shrink-0 text-primary-500 opacity-70 group-hover:opacity-100 transition-opacity"
                    />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <Tag color="blue" className="!text-xs">{formatMs(item.start_time_ms)}</Tag>
                        <Tag className="!text-xs">{item.speaker_label}</Tag>
                        <Text type="secondary" className="text-[11px]">
                          {item.language?.toUpperCase()}
                        </Text>
                        <span className="ml-auto text-xs text-slate-400 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          跳转 <ArrowRightOutlined />
                        </span>
                      </div>

                      <p className="m-0 text-sm text-slate-700 leading-relaxed"
                        dangerouslySetInnerHTML={{
                          __html: item.headline || escapeHtml(item.text),
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function formatMs(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
