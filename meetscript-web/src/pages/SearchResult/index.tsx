import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Input,
  Typography,
  List,
  Tag,
  Space,
  Button,
  Select,
  Spin,
  Empty,
} from 'antd';
import { SearchOutlined, PlayCircleOutlined, FilterOutlined } from '@ant-design/icons';
import { searchAPI } from '../../api/search';
import { useSearchStore } from '../../stores/searchStore';
import { useSearch } from '../../hooks/useSearch';
import type { Subtitle } from '../../types';

const { Title, Text, Paragraph } = Typography;

export default function SearchResultPage() {
  const navigate = useNavigate();
  const { query, setQuery, setQueryImmediate } = useSearch(400);
  const {
    result,
    loading,
    filters,
    setResult,
    setLoading,
    setFilters,
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
      } finally {
        setLoading(false);
      }
      return null;
    },
    enabled: !!query.trim(),
  });

  const handleJumpToMeeting = (meetingId: string, startTimeMs: number) => {
    navigate(`/meetings/${meetingId}?t=${startTimeMs}`);
  };

  return (
    <div>
      <Title level={4}>全局搜索</Title>

      <Card>
        <Input.Search
          placeholder="搜索会议字幕内容（支持关键词、说话人筛选）"
          onChange={(e) => setQuery(e.target.value)}
          onSearch={(value) => setQueryImmediate(value)}
          size="large"
          enterButton={<SearchOutlined />}
        />

        <Space wrap style={{ marginTop: 12 }}>
          <Button icon={<FilterOutlined />}>高级筛选</Button>
          <Input
            placeholder="按说话人筛选"
            allowClear
            style={{ width: 150 }}
            onChange={(e) => setFilters({ speaker: e.target.value || undefined })}
          />
          <Select
            placeholder="时间范围"
            allowClear
            style={{ width: 120 }}
            onChange={(v) => setFilters({})}
            options={[
              { value: '5min', label: '最近5分钟' },
              { value: '15min', label: '最近15分钟' },
              { value: '30min', label: '最近30分钟' },
            ]}
          />
        </Space>
      </Card>

      <div style={{ marginTop: 16 }}>
        {loading && <Spin size="large" style={{ display: 'block', margin: '40px auto' }} />}

        {!loading && !result && query.trim() && (
          <Empty description="未找到匹配的结果" style={{ marginTop: 60 }} />
        )}

        {!loading && result && (!result.items || result.items.length === 0) && (
          <Empty description={`未找到关于 "${query}" 的结果`} style={{ marginTop: 60 }} />
        )}

        {result && result.items && result.items.length > 0 && (
          <>
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary">
                找到 <Text strong>{result.total}</Text> 条匹配结果
              </Text>
            </div>
            <List
              dataSource={result.items}
              renderItem={(item: Subtitle) => (
                <Card
                  size="small"
                  style={{ marginBottom: 8, cursor: 'pointer' }}
                  onClick={() => handleJumpToMeeting(item.meeting_id, item.start_time_ms)}
                >
                  <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                    <Button
                      icon={<PlayCircleOutlined />}
                      type="text"
                      size="small"
                      style={{ flexShrink: 0, marginTop: 4 }}
                    />
                    <div style={{ flex: 1 }}>
                      <Space style={{ marginBottom: 4 }}>
                        <Tag color="blue">{formatMs(item.start_time_ms)}</Tag>
                        <Tag>{item.speaker_label}</Tag>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {item.language}
                        </Text>
                      </Space>
                      <Paragraph style={{ margin: 0 }}>
                        <span
                          dangerouslySetInnerHTML={{
                            __html: item.headline || escapeHtml(item.text),
                          }}
                        />
                      </Paragraph>
                    </div>
                  </div>
                </Card>
              )}
            />
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
