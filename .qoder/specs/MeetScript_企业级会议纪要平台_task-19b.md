# MeetScript 企业级视频会议纪要平台 - 架构设计方案 (v2 修订版)

## 修订说明
本版根据技术评审反馈全面修订，新增：音频预处理层、任务队列可靠性设计、SSE 实时推送、数据库索引、全文搜索、前端国际化、多级缓存策略、文件存储容灾、可观测性监控体系。

## 技术选型总览

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | React 18 + TypeScript + Vite | SPA 应用 |
| UI 组件库 | Ant Design 5.x | 企业级后台管理 |
| 状态管理 | Zustand | 轻量、高性能 |
| HTTP 客户端 | TanStack Query (React Query) + Axios | 请求缓存与服务端状态 |
| 国际化 | react-i18next | 中/英/日 多语言前端 |
| 路由 | React Router v6 | SPA 路由 |
| 视频播放 | video.js + WebVTT | 字幕时间轴同步 |
| 后端框架 | FastAPI (Python 3.12+) | 异步高性能、自动 OpenAPI 文档 |
| ORM | SQLAlchemy 2.0 (async) + Alembic | 异步数据库操作与迁移 |
| 数据库 | PostgreSQL 16 | 主存储 + 全文搜索 |
| 缓存/队列 | Redis 7 | Celery broker + Result Backend + 应用缓存 |
| 任务队列 | Celery 5.x + Redis + 死信队列 | 异步任务 + 优先级 + 去重 + 可靠重试 |
| 音频预处理 | ffmpeg (管道模式) + pydub | 格式转换/降噪/切分/音质检测 |
| 文件存储 | MinIO 分布式 / 阿里云 OSS | 会议音视频 + 分片断点续传 |
| ASR 引擎 | 阿里云百炼 Paraformer | 非实时语音识别 + 说话人分离 |
| 翻译引擎 | 阿里云百炼 AnyTrans / TextTranslate | 多语言翻译 |
| LLM 总结 | 阿里云百炼 通义千问 (Qwen) | 会议纪要智能总结 |
| Token 计费 | DashScope API usage (金标准) + tiktoken (预估算) | Token 消耗统计与成本计算 |
| 搜索 | PostgreSQL Full-Text Search (GIN) | 字幕/会议全文搜索 |
| 任务进度 | SSE (Server-Sent Events) | 单向实时推送，兼容 HTTP 基础设施 |
| 监控 | Prometheus + Grafana | API QPS/延迟/错误率/队列深度 |
| 追踪 | Sentry + structlog | 错误追踪 + 结构化日志 |
| 容器化 | Docker + Docker Compose | 本地开发与部署 |
| 反向代理 | Nginx | 生产环境静态资源 + API 代理 + SSE 透传 |

---

## Task 1: 项目初始化与目录结构搭建

### 前端项目结构 (meetscript-web/)
```
meetscript-web/
├── public/
│   └── locales/                 # <新增> 静态语言包 (fallback)
│       ├── zh-CN/
│       ├── en-US/
│       └── ja-JP/
├── src/
│   ├── api/                    # API 调用层
│   │   ├── client.ts           # Axios 实例 + 拦截器
│   │   ├── auth.ts             # 认证相关 API
│   │   ├── meetings.ts         # 会议相关 API
│   │   ├── tasks.ts            # 任务相关 API
│   │   ├── subtitles.ts        # 字幕相关 API
│   │   ├── translation.ts      # 翻译相关 API
│   │   ├── models.ts           # 模型配置 API
│   │   ├── search.ts           # <新增> 搜索 API
│   │   └── api-keys.ts         # API Key 管理
│   ├── assets/
│   ├── components/             # 通用组件
│   │   ├── layout/             # 布局组件 (Header, Sidebar, Content)
│   │   ├── video/              # 视频播放器 + 字幕组件
│   │   ├── subtitle/           # 字幕时间轴/列表组件
│   │   ├── search/             # <新增> 全局搜索组件
│   │   ├── task/               # 任务状态展示组件 (含 SSE 进度)
│   │   ├── model/              # 模型选择器组件
│   │   └── common/             # 通用组件 (Loading, ErrorBoundary, LocaleSwitch)
│   ├── hooks/                  # 自定义 Hooks
│   │   ├── useSSE.ts           # <新增> SSE 订阅 Hook
│   │   ├── useSearch.ts        # <新增> 防抖搜索 Hook
│   │   └── useTaskProgress.ts  # <新增> 任务进度 Hook
│   ├── i18n/                   # <新增> 国际化配置
│   │   ├── index.ts            # i18next 初始化
│   │   ├── resources/          # 语言资源文件 (按模块拆分)
│   │   │   ├── zh-CN/
│   │   │   │   ├── common.json
│   │   │   │   ├── meeting.json
│   │   │   │   ├── task.json
│   │   │   │   └── model.json
│   │   │   ├── en-US/
│   │   │   └── ja-JP/
│   │   └── detector.ts         # 语言检测 (浏览器/用户偏好)
│   ├── pages/                  # 页面组件
│   │   ├── Dashboard/          # 仪表盘首页
│   │   ├── MeetingUpload/      # 会议上传页 (含分片上传)
│   │   ├── MeetingDetail/      # 会议详情/字幕查看页 (核心)
│   │   ├── TaskManagement/     # 任务管理页
│   │   ├── ModelConfig/        # 模型配置页
│   │   ├── TokenUsage/         # Token 消耗统计页
│   │   ├── ApiManagement/      # API 管理页
│   │   ├── TranslationView/    # 翻译查看页 (表单式编辑)
│   │   ├── SearchResult/       # <新增> 搜索结果页
│   │   └── Login/              # 登录页
│   ├── stores/                 # Zustand 状态管理
│   │   ├── authStore.ts
│   │   ├── meetingStore.ts
│   │   ├── uiStore.ts          # 含语言/主题偏好
│   │   └── searchStore.ts      # <新增> 搜索状态
│   ├── types/                  # TypeScript 类型定义
│   │   ├── meeting.ts
│   │   ├── subtitle.ts
│   │   ├── task.ts
│   │   └── sse.ts              # <新增> SSE 事件类型
│   ├── utils/                  # 工具函数
│   │   ├── format.ts           # 时间/Token 格式化
│   │   └── download.ts         # 文件下载/导出
│   ├── App.tsx
│   └── main.tsx
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### 后端项目结构 (meetscript-api/)
```
meetscript-api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── core/                   # 核心配置
│   │   ├── config.py           # 配置管理 (pydantic-settings)
│   │   ├── security.py         # JWT + OAuth2 认证
│   │   ├── database.py         # 数据库连接池
│   │   ├── celery_app.py       # Celery 配置 (含优先级队列+DLQ)
│   │   └── redis_client.py     # Redis 连接管理 (broker + result backend + cache)
│   ├── models/                 # SQLAlchemy 数据模型 (按模块拆分)
│   │   ├── base.py             # Base Model
│   │   ├── user.py             # 用户模型
│   │   ├── meeting.py          # 会议模型
│   │   ├── task.py             # 任务模型
│   │   ├── subtitle.py         # 字幕模型
│   │   ├── translation.py      # 翻译记录模型
│   │   ├── model_config.py     # 模型配置模型
│   │   ├── token_usage.py      # Token 消耗模型
│   │   ├── api_key.py          # API Key 模型
│   │   └── audit_log.py        # 审计日志模型
│   ├── schemas/                # Pydantic 请求/响应 Schema
│   │   ├── auth.py
│   │   ├── meeting.py
│   │   ├── task.py
│   │   ├── subtitle.py
│   │   ├── translation.py
│   │   ├── model_config.py
│   │   ├── token_usage.py
│   │   ├── api_key.py
│   │   └── sse.py              # SSE 事件协议 Schema
│   ├── api/                    # API 路由 (按模块拆分)
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py       # 路由聚合
│   │   │   ├── auth.py         # POST /auth/login, /auth/refresh
│   │   │   ├── users.py        # GET/POST/PUT /users
│   │   │   ├── meetings.py     # POST/GET /meetings
│   │   │   ├── tasks.py        # GET /tasks/{id}, /tasks/{id}/logs
│   │   │   ├── subtitles.py    # GET /meetings/{id}/subtitles
│   │   │   ├── translations.py # GET/POST /translations
│   │   │   ├── models.py       # GET/PUT /model-configs
│   │   │   ├── token_usage.py  # GET /token-usage
│   │   │   ├── api_keys.py     # POST/GET/DELETE /api-keys
│   │   │   ├── exports.py      # POST /export (SRT/VTT/JSON)
│   │   │   ├── search.py       # GET /search (全文搜索)
│   │   │   └── sse.py          # GET /tasks/{id}/stream (SSE 进度推送)
│   │   └── deps.py             # 依赖注入 (get_db, get_current_user)
│   ├── services/               # 业务逻辑层 (按模块拆分)
│   │   ├── auth_service.py     # 用户认证与权限
│   │   ├── meeting_service.py  # 会议管理业务
│   │   ├── file_service.py     # 文件上传/存储 (MinIO/OSS，断点续传)
│   │   ├── audio_processor.py  # <新增> 音频预处理 (ffmpeg管道: 提取/转码/降噪/切分/音质检测)
│   │   ├── task_service.py     # 任务调度与状态管理 (含去重+优先级+DLQ)
│   │   ├── asr_service.py      # 阿里云百炼 Paraformer ASR
│   │   ├── diarization_service.py # 说话人分离
│   │   ├── subtitle_service.py # 字幕生成与对齐
│   │   ├── translation_service.py # 阿里云百炼 AnyTrans 翻译 (含缓存)
│   │   ├── summary_service.py  # 通义千问 LLM 会议总结
│   │   ├── model_registry.py   # 模型注册与配置中心 (含缓存)
│   │   ├── token_service.py    # Token 计数与计费 (DashScope usage优先)
│   │   ├── search_service.py   # <新增> PostgreSQL 全文搜索
│   │   ├── cache_service.py    # <新增> Redis 缓存服务 (多级缓存管理)
│   │   ├── api_key_service.py  # API Key 管理
│   │   └── audit_service.py    # 审计日志
│   ├── tasks/                  # Celery 异步任务
│   │   ├── process_meeting.py  # 会议处理主流程 (Celery Chain)
│   │   ├── audio_task.py       # <新增> 音频预处理任务
│   │   ├── asr_task.py         # ASR 转写任务
│   │   ├── translation_task.py # 翻译任务
│   │   ├── summary_task.py     # 总结生成任务
│   │   └── export_task.py      # 导出任务
│   ├── middleware/             # <新增> 中间件
│   │   ├── request_id.py       # X-Request-ID 注入
│   │   ├── access_log.py       # 访问日志记录
│   │   └── metrics.py          # Prometheus 指标收集
│   └── utils/                  # 工具函数
│       ├── srt_parser.py       # SRT/VTT 格式解析
│       ├── time_utils.py       # 时间戳处理
│       └── token_counter.py    # Token 计数器 (tiktoken预估+DashScope实际)
├── migrations/                 # Alembic 迁移 (含索引定义)
├── tests/                      # 测试用例
├── alembic.ini
├── Dockerfile
├── docker-compose.yml          # 含 Prometheus + Grafana + MinIO多节点
├── prometheus.yml              # <新增> Prometheus 配置
├── requirements.txt
└── pyproject.toml
```

---

## Task 2: 数据库设计与 Alembic 迁移

### 核心数据表设计

**users** - 用户表
- id (UUID PK), username, email, password_hash, role (admin/editor/viewer), is_active, preferred_language, created_at, updated_at
- 索引: unique(email), unique(username)

**meetings** - 会议表
- id (UUID PK), user_id (FK), title, description, source_language, file_path, file_type (video/audio), file_size_bytes, duration_seconds, status (uploaded/preprocessing/processing/completed/failed), created_at, updated_at
- 索引: (user_id, created_at), (status, created_at)
- GIN 索引: search_vector tsvector (标题全文搜索)

**meeting_tasks** - 任务表
- id (UUID PK), meeting_id (FK), task_type (audio_preprocess/asr/diarization/translation/summary), celery_task_id, priority (1-10), status (pending/running/completed/failed/retrying/dlq), progress (0-100), error_message, retry_count, max_retries, started_at, completed_at
- **必须索引**: (meeting_id, task_type, status) -- 查询某会议某类型任务状态
- 索引: (status, created_at), (celery_task_id)

**subtitles** - 字幕表
- id (UUID PK), meeting_id (FK), speaker_label (SPEAKER_00/姓名), language, start_time_ms, end_time_ms, text, is_candidate (bool), confidence (float), created_at
- **必须索引**: (meeting_id, start_time_ms) -- 按时间范围查询字幕
- **必须索引**: (meeting_id, speaker_label) -- 按说话人过滤
- GIN 索引: text_search_vector tsvector (字幕文本全文搜索)

**translations** - 翻译记录表
- id (UUID PK), subtitle_id (FK), meeting_id (FK), target_language, translated_text, model_used, token_count_input, token_count_output, cost, translation_hash, created_at
- 索引: (subtitle_id, target_language) -- 查找某字幕的翻译
- 索引: (meeting_id, target_language) -- 按语言获取会议翻译
- 索引: (translation_hash, target_language) -- 翻译缓存命中查询

**model_configs** - 模型配置表
- id (UUID PK), model_type (asr/translation/summary), provider (aliyun_bailian/openai/...), model_name, api_key_encrypted, endpoint_url, parameters (JSONB), is_active, created_at, updated_at
- 索引: (model_type, is_active)

**token_usages** - Token 消耗记录表
- id (UUID PK), user_id (FK), meeting_id (FK), model_config_id (FK), operation_type, tokens_input, tokens_output, tokens_total, cost, request_id, created_at
- **必须索引**: (user_id, created_at) -- 用户 Token 消耗查询
- 索引: (meeting_id), (created_at)

**api_keys** - 外部 API Key 管理表
- id (UUID PK), user_id (FK), key_name, api_key_hash, prefix, scopes (JSONB), rate_limit, expires_at, is_active, last_used_at, created_at
- 索引: (user_id), (api_key_hash)

**audit_logs** - 审计日志表
- id (UUID PK), user_id (FK), action, resource_type, resource_id, ip_address, user_agent, details (JSONB), created_at
- **必须索引**: (user_id, action, created_at) -- 审计日志查询
- 索引: (resource_type, resource_id), (created_at)

### <新增> 全文搜索索引设计
```sql
-- 字幕全文搜索 GIN 索引
ALTER TABLE subtitles ADD COLUMN text_search_vector tsvector 
    GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED;
CREATE INDEX idx_subtitles_text_search ON subtitles USING GIN (text_search_vector);

-- 会议标题全文搜索
ALTER TABLE meetings ADD COLUMN search_vector tsvector 
    GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(description, ''))) STORED;
CREATE INDEX idx_meetings_search ON meetings USING GIN (search_vector);

-- 组合查询示例：按说话人+关键词+时间范围搜索
-- SELECT * FROM subtitles 
-- WHERE meeting_id = $1 AND speaker_label = $2 
--   AND text_search_vector @@ to_tsquery('simple', $3)
--   AND start_time_ms BETWEEN $4 AND $5
-- ORDER BY start_time_ms;
```

---

## Task 3: 后端核心模块实现

### 3.0 <新增> 音频预处理模块 (audio_processor.py) — 必需层
会议纪要平台的核心输入质量依赖此模块，不可跳过。

**处理流水线 (ffmpeg 管道模式)**：
```
原始文件 (mp4/mov/wav/mp3/...)
    │
    ▼
[步骤1] 音频轨道提取 (视频文件专属)
    ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 output.wav
    │
    ▼
[步骤2] 统一转码 (所有文件)
    目标: 16kHz 采样率 + 单声道 + PCM 16bit WAV (阿里云 Paraformer 推荐格式)
    ffmpeg -i input.xxx -ar 16000 -ac 1 -sample_fmt s16 output.wav
    │
    ▼
[步骤3] 长音频切分 (>30min 自动分段)
    按 30 分钟/段切分，段落间保留 2 秒重叠避免边界截断
    ffmpeg -i input.wav -f segment -segment_time 1800 -c copy segment_%03d.wav
    │
    ▼
[步骤4] 音质检测
    - 静音检测 (低于阈值占比 >80% → 警告)
    - 响度检测 (RMS < -40dB → 警告)
    - 采样率校验 (确认输出为 16000Hz)
    │
    ▼
输出: 处理后的音频文件对象列表 → 进入 ASR 任务队列
```

**关键实现要点**：
- 使用 `ffmpeg-python` 库调用 ffmpeg，避免 subprocess 裸调带来的注入风险
- 文件处理幂等性：通过文件 MD5 哈希 + 处理参数生成缓存 key，避免重复转码
- 异常处理：ffmpeg 调用超时 300 秒，超时自动 kill 进程并重试
- 临时文件清理：任务完成后立即清理中间文件

### 3.1 <修订> Celery 任务队列可靠性设计 (celery_app.py)
原方案缺少结果后端和死信队列，修订如下：

```python
# Celery 配置要点
app = Celery('meetscript')

# Broker + Result Backend
app.conf.broker_url = 'redis://redis:6379/0'          # 消息代理
app.conf.result_backend = 'redis://redis:6379/1'       # 结果后端 (必需!)
app.conf.result_expires = 86400 * 7                    # 结果保留 7 天

# 任务优先级队列 (Redis 需要多个队列)
app.conf.task_queues = [
    Queue('priority_high', routing_key='priority.high'),    # ASR (阻塞步骤)
    Queue('priority_normal', routing_key='priority.normal'), # 翻译 (可并行)
    Queue('priority_low', routing_key='priority.low'),       # 总结 (可延后)
]
app.conf.task_default_queue = 'priority_normal'
app.conf.task_default_routing_key = 'priority.normal'

# 死信队列 (DLQ)
app.conf.task_queues += [
    Queue('dlq', routing_key='dlq'),  # 失败3次后的任务
]

# 任务重试 + DLQ
@app.task(bind=True, max_retries=3, default_retry_delay=60, 
          autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=600)
def process_asr(self, meeting_id):
    try:
        # ... ASR 处理逻辑
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            # 进入死信队列
            mark_task_dlq(meeting_id, str(exc))
            return
        raise self.retry(exc=exc)

# 任务去重 (基于 meeting_id + task_type)
def submit_meeting_task(meeting_id, task_type):
    redis_key = f"task_lock:{meeting_id}:{task_type}"
    if redis_client.setnx(redis_key, 1):  # 原子锁
        redis_client.expire(redis_key, 3600)
        return celery.send_task(...)
    else:
        raise DuplicateTaskError("该会议已有相同类型任务在进行中")
```

### 3.2 <修订> SSE 实时任务进度推送 (替代 WebSocket)

选用 SSE 而非 WebSocket 的原因：
- 会议处理进度是单向推送（服务端→前端），SSE 天然契合
- SSE 兼容 HTTP 基础设施（Nginx 反向代理、负载均衡器无需特殊配置）
- 浏览器原生支持 `EventSource` API，无需额外库
- 断线自动重连机制内置

**SSE 事件协议**：
```python
# schemas/sse.py
class TaskProgressEvent(BaseModel):
    task_id: str
    meeting_id: str
    task_type: str               # audio_preprocess / asr / translation / summary
    status: str                   # pending / running / completed / failed / dlq
    progress: int                 # 0-100
    current_step: str             # 当前步骤描述，如 "正在进行语音识别 (45%)"
    message: str                  # 详细信息
    timestamp: datetime           # ISO 8601 格式
    error_detail: Optional[str]   # 失败时填充错误信息
```

**后端 SSE 端点**：
```python
# api/v1/sse.py
@router.get("/tasks/{task_id}/stream")
async def task_stream(task_id: str, request: Request):
    async def event_generator():
        redis = get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"task_progress:{task_id}")
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    yield f"data: {json.dumps(data)}\n\n"
                    if data['status'] in ('completed', 'failed', 'dlq'):
                        break
        finally:
            await pubsub.unsubscribe(f"task_progress:{task_id}")
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Nginx SSE 透传配置** (必须!)：
```nginx
location /api/v1/tasks/ {
    proxy_pass http://api:8000;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_buffering off;           # 关闭缓冲，确保实时推送
    proxy_cache off;
    chunked_transfer_encoding on;
}
```

**前端 SSE 订阅**：
```typescript
// hooks/useSSE.ts
function useTaskProgress(taskId: string) {
  const queryClient = useQueryClient();
  
  useEffect(() => {
    const eventSource = new EventSource(`/api/v1/tasks/${taskId}/stream`);
    
    eventSource.onmessage = (event) => {
      const data: TaskProgressEvent = JSON.parse(event.data);
      queryClient.setQueryData(['task', taskId], data);
    };
    
    return () => eventSource.close();
  }, [taskId]);
}
```

### 3.3 <修订> Token 计费策略修正

**计费精度原则**：
- **金标准（实际扣费）**：DashScope API 返回的 `usage.input_tokens` / `usage.output_tokens`
- **预估算（仅供参考）**：本地 tiktoken 计算，仅用于提交前预算预估
- **偏差说明**：tiktoken 是 OpenAI tokenizer，对 Qwen 计数偏差 5-15%

```python
# services/token_service.py
class TokenService:
    def record_usage_from_api_response(self, response: dict, context: dict):
        """从 DashScope API 响应中提取实际 Token 消耗并入库"""
        usage = response.get("usage", {})
        token_usage = TokenUsage(
            user_id=context["user_id"],
            meeting_id=context.get("meeting_id"),
            model_config_id=context["model_config_id"],
            operation_type=context["operation_type"],
            tokens_input=usage.get("input_tokens", 0),
            tokens_output=usage.get("output_tokens", 0),
            tokens_total=usage.get("total_tokens", 0),
            cost=self._calculate_cost(context["model_name"], usage),
            request_id=response.get("request_id"),
        )
        db.add(token_usage)
    
    def estimate_tokens_locally(self, text: str, model: str) -> int:
        """本地预估算 (仅用于 UI 展示预算，不计入实际账单)"""
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    
    def _calculate_cost(self, model_name: str, usage: dict) -> Decimal:
        """按阿里云百炼官方定价计算成本
        Paraformer: 2.8 元/小时
        Qwen-Max: 输入 0.04元/千token, 输出 0.12元/千token
        AnyTrans: 按字符计费
        """
        pricing = self._get_pricing(model_name)
        return pricing.calculate(usage)
```

### 3.4 文件管理模块 (file_service.py)
- 使用 MinIO Python SDK 实现文件上传/下载
- **分片上传 + 断点续传**：文件 >10MB 自动分片（5MB/片），前端直传 OSS/MinIO
- 服务端签名 URL 模式：API 签发临时上传凭证，前端直传存储，避免流量经过 API 服务器
- 文件类型校验 (mp4, avi, mov, wav, mp3, m4a, flac)
- 上传完成回调 → 自动触发音频预处理 → ASR 任务链

### 3.5 任务调度模块 (task_service.py)
- Celery Chain 编排：音频预处理 → ASR → 字幕生成 → 翻译(并行) → 总结
- 任务状态机：pending → running → completed/failed/dlq
- 失败重试：指数退避 (60s→120s→240s)，max 3 次 → 进入 DLQ
- 任务去重：Redis 分布式锁 (meeting_id + task_type)
- 优先级路由：ASR(high) > 翻译(normal) > 总结(low)
- 通过 Redis Pub/Sub 广播进度 → SSE 推送前端

### 3.6 ASR 语音识别模块 (asr_service.py)
- 调用阿里云百炼 Paraformer 非实时语音识别 API
- 启用说话人分离功能 (diarization_enabled=true)
- 支持多语言：中文、英语、日语等（通过 source_language 参数）
- 长音频自动分段提交（>30min 已在预处理层切分）
- 回调处理异步转写结果
- 异常重试与降级策略

### 3.7 说话人识别模块 (diarization_service.py)
- 利用 Paraformer 的说话人分离结果
- 将说话人标签映射为可识别名称
- 支持手动标注/修正说话人身份
- 候选人识别：通过预设候选人姓名关键词匹配（在字幕文本中搜索）

### 3.8 字幕生成模块 (subtitle_service.py)
- 将 ASR 结果转换为 WebVTT/SRT 格式
- 时间轴对齐与分段
- 按说话人分组展示
- 字幕搜索与高亮
- 支持导出 SRT/VTT/JSON/TXT 格式

### 3.9 <修订> 翻译服务模块 (translation_service.py) — 含多级缓存
- 调用阿里云百炼 AnyTrans API
- 支持语言列表：中文、英语、日语、韩语、法语、德语、西班牙语等
- 保留原文与翻译的对应关系（通过 subtitle_id 关联）
- 批量翻译优化（合并相邻同说话人片段，减少 API 调用次数）
- **翻译缓存**：相同文本 Hash → 缓存翻译结果 (Redis TTL 30d)，避免重复 API 调用节省成本
- 翻译结果编辑：前端提供表单式编辑界面（非 JSON 编辑器），符合用户交互偏好

### 3.10 LLM 总结模块 (summary_service.py)
- 调用阿里云百炼通义千问 (Qwen-Max/Qwen-Plus)
- 生成会议纪要摘要
- 提取关键决策与行动项
- 支持自定义 Prompt 模板

### 3.11 模型管理模块 (model_registry.py)
- 模型配置的增删改查
- 支持多 Provider 注册（阿里云百炼/OpenAI 兼容接口）
- **模型配置 Redis 缓存**（TTL 5min），减少 DB 查询
- 模型切换热生效
- 模型调用统计

### 3.12 <新增> 全文搜索模块 (search_service.py)
```python
class SearchService:
    async def search_subtitles(
        self, 
        keyword: str, 
        meeting_id: Optional[str] = None,
        speaker_label: Optional[str] = None,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
        page: int = 1, 
        page_size: int = 20
    ) -> SearchResult:
        """PostgreSQL Full-Text Search 组合查询"""
        # 使用 websearch_to_tsquery 支持用户自然查询语法
        query = select(Subtitle).where(
            Subtitle.text_search_vector.op('@@')(
                func.websearch_to_tsquery('simple', keyword)
            )
        )
        if meeting_id:
            query = query.where(Subtitle.meeting_id == meeting_id)
        if speaker_label:
            query = query.where(Subtitle.speaker_label == speaker_label)
        if start_time_ms is not None:
            query = query.where(Subtitle.start_time_ms >= start_time_ms)
        if end_time_ms is not None:
            query = query.where(Subtitle.end_time_ms <= end_time_ms)
        
        query = query.order_by(Subtitle.start_time_ms)
        return await paginate(query, page, page_size)
    
    async def search_meetings(self, keyword: str) -> list[Meeting]:
        """搜索会议标题和描述"""
        ...
```

**搜索结果高亮**：
```sql
SELECT ts_headline('simple', text, websearch_to_tsquery('simple', :keyword), 
                   'StartSel=<mark>, StopSel=</mark>, MaxWords=30, MinWords=10') 
FROM subtitles WHERE ...;
```

### 3.13 <新增> 缓存策略模块 (cache_service.py)

| 缓存类型 | Key 模式 | TTL | 说明 |
|---------|---------|-----|------|
| 热门会议字幕 | `subtitles:meeting:{id}:lang:{lang}` | 1h | 减少字幕表查询 |
| 翻译结果 | `translation:{text_hash}:{target_lang}` | 30d | 相同文本不重复翻译，节约 API 成本 |
| 模型配置 | `model_config:{model_type}` | 5min | 高频读取数据 |
| 用户会话 | `session:{user_id}` | 30min | JWT 黑名单/白名单 |
| 任务锁 | `task_lock:{meeting_id}:{task_type}` | 1h | 任务去重分布式锁 |
| 限流计数器 | `rate_limit:{user_id}:{endpoint}` | 1min | API 频率限制 |

**缓存更新策略**：Cache-Aside Pattern（旁路缓存），更新 DB 后主动失效缓存。

### 3.14 API 网关模块
- 对外标准化 RESTful API
- API Key 生成与管理 (SHA256 Hash 存储)
- 请求频率限制 (slowapi + Redis)
- 接口文档自动生成 (Swagger UI + ReDoc)

### 3.15 审计日志模块
- 记录所有关键操作
- 结构化 JSON 日志 (structlog)
- 请求追踪 (X-Request-ID)
- 日志保留策略（90 天热数据 + 归档）

---

## Task 4: 前端页面开发

### 4.1 项目基础架构
- Vite + React 18 + TypeScript 项目初始化
- Ant Design 5.x 安装与主题配置 + ConfigProvider 国际化
- **react-i18next 集成**：语言检测（浏览器偏好 > 用户设置 > 默认中文）
- **语言切换组件 (LocaleSwitch)**：全局 Header 下拉切换，即时生效
- Zustand 状态管理 Store 设计
- TanStack Query 配置与 API Client 封装
- React Router v6 路由配置 + 路由守卫
- **前端直传 OSS/MinIO**：通过 API 获取签名 URL，分片上传大文件，显示进度

### 4.2 登录/认证页面
- 登录表单 (Ant Design Form)
- JWT Token 管理与自动刷新
- OAuth2 流程对接
- 支持中/英/日三语切换

### 4.3 会议上传页面 (MeetingUpload)
- 拖拽上传 + 点击上传 (Ant Design Upload)
- **分片上传进度条**（大文件 >10MB 自动分片）
- 会议信息表单（标题、描述、源语言选择）
- 支持 API 提交模式切换
- 上传完成自动创建处理任务，SSE 流式显示处理进度

### 4.4 会议详情 / 字幕查看页面 (MeetingDetail) — 核心页面
- 视频播放器 (video.js) + WebVTT 字幕轨道
- 字幕时间轴面板（YouTube 风格：左侧说话人色标 + 右侧时间轴文本）
- 说话人颜色标识（自动分配 8 色板）
- 候选人发言高亮标注（橙色背景）
- 字幕点击跳转视频对应时间点
- **全局搜索栏**：实时搜索当前会议字幕，高亮匹配词
- 翻译语言切换下拉框
- 原文/译文对照显示（左右分栏）

### 4.5 任务管理页面 (TaskManagement)
- 任务列表 (Ant Design Table) + 状态筛选
- **SSE 实时进度更新**：进度条 + 当前步骤文字 + 时间戳
- 处理日志查看
- 失败任务手动重试
- DLQ 死信队列任务列表（人工审核/重新入队）

### 4.6 模型配置页面 (ModelConfig)
- ASR 模型选择（Paraformer/Qwen-ASR）
- 翻译模型选择（AnyTrans/Qwen-MT）
- 总结模型选择（Qwen-Max/Qwen-Plus/Turbo）
- API Key 配置（加密存储，仅显示前后各 4 位）
- 模型参数调优（温度、Top-P 等滑动条）
- 模型调用统计卡片

### 4.7 Token 消耗统计页面 (TokenUsage)
- 按时间范围统计图表 (Recharts)
- 按模型/操作类型分组饼图
- 概算 vs 实际消耗对比曲线（体现 tiktoken 偏差）
- 成本汇总卡片（本月/总计）
- 消耗明细列表 (Ant Design Table)
- 数据导出 CSV

### 4.8 API 管理页面 (ApiManagement)
- API Key 创建与管理
- 接口调用文档展示 (Swagger UI iframe 嵌入)
- 调用次数统计图表
- 速率限制配置

### 4.9 翻译查看页面 (TranslationView)
- 原文与多语言翻译对照表
- 按说话人/语言筛选
- **表单式编辑界面**：分区清晰，支持增删改，而非 JSON 编辑器
- 导出翻译结果 (JSON/CSV)

### 4.10 <新增> 全局搜索页面 (SearchResult)
- 输入框搜索（300ms 防抖）
- 高级筛选：会议范围、说话人、时间范围
- 搜索结果列表：显示匹配字幕片段 + 上下文 + 高亮
- 点击跳转到对应会议的视频时间点
- 搜索结果高亮显示关键词（使用 ts_headline）

---

## Task 5: Celery 异步任务流程设计 (修订)

### 会议处理主流程 (process_meeting.py) — Celery Chain
```
文件上传完成 (前端直传 OSS/MinIO)
    │
    ▼
[Task 0] 音频预处理 (audio_task.py) — <新增，必需>
    │  优先级: HIGH
    │  输入: 原始文件路径 (mp4/mov/wav/mp3/...)
    │  处理:
    │    1. 视频文件 → 提取音频轨道 (ffmpeg -vn)
    │    2. 转为 16kHz 单声道 WAV
    │    3. 长音频 (>30min) 按段切分
    │    4. 音质检测 (静音/响度/采样率)
    │  输出: 预处理后的音频文件列表 [file_segment_001.wav, ...]
    │  失败: 音质不达标 → 标记警告，仍继续处理
    │
    ▼
[Task 1] ASR 语音识别 (asr_task.py)
    │  优先级: HIGH (阻塞后续步骤)
    │  输入: 预处理音频文件列表, source_language
    │  引擎: 阿里云百炼 Paraformer (diarization_enabled=true)
    │  输出: raw_transcript (文本 + 时间戳 + 说话人标签)
    │  失败: 重试 3 次 → DLQ → 整个流程失败
    │
    ▼
[Task 2] 字幕生成与入库 (subtitle_task.py)
    │  合并 ASR + 说话人结果 → subtitles 表
    │  生成 WebVTT/SRT 文件存入 MinIO
    │  建立全文搜索索引 (text_search_vector)
    │  通过 Redis Pub/Sub 推送进度 → SSE 通知前端
    │
    ▼
[Task 3] 候选人识别 (可选)
    │  关键词匹配预定义候选人名单
    │  标记 subtitles.is_candidate 字段
    │
    ▼
[Task 4] 翻译 (并行执行，如启用)
    │  优先级: NORMAL
    │  并行翻译为多个目标语言 (AnyTrans API)
    │  翻译缓存命中直接返回 (Redis)
    │  写入 translations 表
    │
    ▼
[Task 5] LLM 总结 (如启用)
    │  优先级: LOW (可延后)
    │  输入: 完整字幕文本
    │  引擎: 通义千问 Qwen-Max
    │  生成会议纪要摘要 + 关键决策 + 行动项
    │
    ▼
任务完成 → Redis Pub/Sub → SSE 通知前端刷新
```

### 错误处理与重试策略 (修订)
- 每个 Task 独立重试（max_retries=3, exponential_backoff: 60s→120s→240s）
- 3 次失败后自动进入死信队列 (DLQ)，标记 status=dlq
- DLQ 任务可在前端手动重新入队或废弃
- 音频预处理失败 → 标记警告，仍尝试继续（可能影响 ASR 质量）
- ASR 失败 = 整个流程失败（必须步骤）
- 翻译/总结失败 = 标记部分失败，不影响已完成步骤

### 优先级路由映射
| 任务 | 优先级 | 队列 | 原因 |
|------|--------|------|------|
| 音频预处理 | HIGH (7) | priority_high | 所有后续步骤的前置依赖 |
| ASR 语音识别 | HIGH (8) | priority_high | 阻塞步骤，影响用户体验 |
| 字幕生成 | HIGH (6) | priority_high | 用户可见结果的第一步 |
| 翻译 | NORMAL (5) | priority_normal | 可并行，不阻塞主流程 |
| LLM 总结 | LOW (3) | priority_low | 锦上添花，可延后处理 |
| 文件导出 | LOW (2) | priority_low | 用户主动触发的离线任务 |

---

## Task 6: 对外 API 设计

### RESTful API 端点
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/login | 用户登录 |
| POST | /api/v1/auth/refresh | 刷新 Token |
| POST | /api/v1/meetings/upload/sign-url | 获取文件上传签名 URL |
| POST | /api/v1/meetings | 创建会议记录 (上传完成后) |
| GET | /api/v1/meetings | 会议列表 |
| GET | /api/v1/meetings/{id} | 会议详情 |
| POST | /api/v1/meetings/{id}/process | 触发处理任务链 |
| GET | /api/v1/tasks/{id} | 任务状态查询 |
| GET | /api/v1/tasks/{id}/stream | SSE 实时任务进度推送 |
| GET | /api/v1/tasks/{id}/logs | 任务日志查询 |
| POST | /api/v1/tasks/{id}/retry | 手动重试 DLQ 任务 |
| GET | /api/v1/meetings/{id}/subtitles | 获取字幕 (?format=vtt/srt/json&lang=zh) |
| GET | /api/v1/meetings/{id}/translations | 获取翻译结果 (?lang=en) |
| GET | /api/v1/search/subtitles | 全文搜索字幕 (?q=关键词&meeting_id=&speaker=&time_from=&time_to=) |
| GET | /api/v1/search/meetings | 搜索会议 |
| POST | /api/v1/export | 导出字幕/翻译 (?format=srt/vtt/json/csv) |
| GET | /api/v1/model-configs | 模型配置列表 |
| PUT | /api/v1/model-configs/{id} | 更新模型配置 |
| GET | /api/v1/token-usage | Token 消耗查询 |
| GET | /api/v1/token-usage/stats | Token 消耗统计汇总 |
| POST | /api/v1/api-keys | 创建 API Key |
| GET | /api/v1/api-keys | API Key 列表 |
| DELETE | /api/v1/api-keys/{id} | 删除 API Key |
| GET | /api/v1/health | 健康检查 |
| GET | /metrics | Prometheus 指标暴露 |
| GET | /docs | Swagger UI 接口文档 |
| GET | /redoc | ReDoc 接口文档 |

---

## Task 7: 文件存储容灾设计 (新增)

### 本地开发环境 → 生产环境切换策略
| 环境 | 存储方案 | 配置 |
|------|---------|------|
| 本地开发 | MinIO 单节点 (Docker) | `MINIO_ENDPOINT=localhost:9000` |
| 测试环境 | MinIO 4 节点分布式 | `MINIO_ENDPOINT=minio1:9000,minio2:9000,...` |
| 生产环境 | 阿里云 OSS | `STORAGE_BACKEND=aliyun_oss` |

### 统一存储抽象接口
```python
# services/file_service.py
class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, file_path: str, object_key: str) -> str: ...
    @abstractmethod
    async def get_presigned_url(self, object_key: str, expires: int = 3600) -> str: ...
    @abstractmethod
    async def download(self, object_key: str) -> bytes: ...
    @abstractmethod
    async def delete(self, object_key: str) -> None: ...

class MinIOBackend(StorageBackend): ...
class OSSBackend(StorageBackend): ...
class S3Backend(StorageBackend): ...

# 工厂函数
def get_storage() -> StorageBackend:
    backend = settings.STORAGE_BACKEND  # "minio" | "oss" | "s3"
    return {"minio": MinIOBackend(), "oss": OSSBackend(), "s3": S3Backend()}[backend]
```

### 分片上传 + 断点续传
- 前端通过 `/api/v1/meetings/upload/sign-url` 获取签名 URL
- 文件 >10MB：自动分片（5MB/片），使用 multipart upload
- 每片上传独立签名 URL，上传进度精确到分片
- 中断后可从断点继续，已上传的分片无需重传
- 所有分片完成后，调用 API 通知服务端合并 + 校验 MD5

### MinIO 分布式部署 (生产环境)
```yaml
# docker-compose.prod.yml
minio1:
  image: minio/minio:latest
  command: server http://minio{1...4}/data
  environment:
    MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
    MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
  volumes:
    - minio_data_1:/data

minio2:
  # ... 同上，共 4 节点
  # 4 节点可容忍 1 节点故障，满足生产基本要求
```

---

## Task 8: Docker 容器化与部署配置 (修订)

### docker-compose.yml 服务编排 (新增监控组件)
| 服务 | 镜像 | 说明 |
|------|------|------|
| postgres | postgres:16-alpine | 主数据库 (含 GIN 索引支持) |
| redis | redis:7-alpine | Celery broker + result backend + 缓存 |
| minio (x4) | minio/minio:latest | 分布式文件存储 |
| api | Python 3.12 (uvicorn) | FastAPI 应用 |
| celery_worker_high | Python 3.12 | HIGH 优先级队列 Worker (2 并发) |
| celery_worker_normal | Python 3.12 | NORMAL 优先级队列 Worker (4 并发) |
| celery_worker_low | Python 3.12 | LOW 优先级队列 Worker (2 并发) |
| celery_beat | Python 3.12 | 定时任务调度 |
| nginx | nginx:alpine | 反向代理 + SSE 透传 |
| prometheus | prom/prometheus | 指标收集 |
| grafana | grafana/grafana | 监控仪表盘 |
| web | node:20-alpine (dev) | React 前端 Vite dev server |

### Celery Worker 分组策略
```bash
# 高优先级 Worker (处理 ASR 和音频预处理)
celery -A app.core.celery_app worker -Q priority_high -c 2 --hostname=high@%h

# 普通优先级 Worker (处理翻译)
celery -A app.core.celery_app worker -Q priority_normal -c 4 --hostname=normal@%h

# 低优先级 Worker (处理总结和导出)
celery -A app.core.celery_app worker -Q priority_low -c 2 --hostname=low@%h
```

---

## Task 9: 监控与可观测性体系 (新增)

### 9.1 Prometheus 指标收集
```python
# middleware/metrics.py - 使用 prometheus-fastapi-instrumentator
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_instrument_requests_inprogress=True,
)
instrumentator.add(metrics.request_size())
instrumentator.add(metrics.response_size())
instrumentator.add(metrics.latency(buckets=(0.1, 0.5, 1, 2, 5, 10, 30)))

# 自定义业务指标
celery_queue_depth = Gauge('meetscript_celery_queue_depth', '队列深度', ['queue_name'])
asr_duration_seconds = Histogram('meetscript_asr_duration_seconds', 'ASR 处理耗时')
api_call_counter = Counter('meetscript_api_calls_total', 'API 调用次数', ['model', 'operation'])
```

### 9.2 Grafana 仪表盘
预置 4 个 Dashboard：
1. **API 概览**：QPS、P50/P95/P99 延迟、错误率、状态码分布
2. **Celery 队列**：各队列深度、任务处理速率、失败/重试/DLQ 计数
3. **AI 模型调用**：各模型调用次数、Token 消耗、成本、平均延迟
4. **业务总览**：会议上传量、处理成功率、用户活跃度

### 9.3 结构化日志 (structlog)
```python
import structlog

logger = structlog.get_logger()
logger.info("asr_task_started", 
    meeting_id=meeting_id, 
    audio_duration=duration,
    request_id=get_request_id(),
    user_id=current_user.id,
    model="paraformer-v2",
)
# 输出 JSON: {"event": "asr_task_started", "meeting_id": "...", "audio_duration": 1800, ...}
```

### 9.4 Sentry 错误追踪
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration(), CeleryIntegration()],
    traces_sample_rate=0.1,
    environment=settings.ENVIRONMENT,  # "development" | "staging" | "production"
)
```

### 9.5 告警规则 (Prometheus AlertManager)
| 告警 | 条件 | 严重级别 |
|------|------|---------|
| 队列堆积 | `celery_queue_depth > 100` 持续 5 分钟 | Warning |
| 队列严重堆积 | `celery_queue_depth > 500` 持续 2 分钟 | Critical |
| API 错误率过高 | `error_rate > 5%` 持续 5 分钟 | Critical |
| ASR 调用失败率 | `asr_failure_rate > 10%` 持续 10 分钟 | Warning |
| 磁盘使用率 | `disk_usage > 80%` | Warning |
| 磁盘使用率危险 | `disk_usage > 90%` | Critical |
| 服务不可用 | `up == 0` | Critical |

---

## Task 10: 关键实现注意点 (修订)

### 阿里云百炼 SDK 集成要点
- 使用 DashScope Python SDK (`dashscope`)
- 非实时 ASR: `dashscope.audio.asr.Transcription.async_call()`
- 说话人分离参数: `diarization_enabled=True`, 仅支持单声道音频 (这也是 Step 0 转单声道的原因)
- 翻译: `dashscope.TextTranslate.call()` / AnyTrans API
- 大模型总结: 使用 OpenAI 兼容接口调用 Qwen
- API Key 通过环境变量 `DASHSCOPE_API_KEY` 配置
- **Token 计费金标准**：提取 response.usage 字段，不依赖本地 tiktoken 估算

### 安全性设计
- 所有 API Key 加密存储 (Fernet/AES-256，密钥通过 KMS 或环境变量注入)
- JWT Token 过期机制 (access: 30min, refresh: 7d)
- CORS 白名单配置
- SQL 注入防护 (SQLAlchemy ORM)
- XSS 防护 (React 默认转义)
- 文件上传大小/类型限制
- 请求频率限制 (slowapi + Redis)
- API Key 哈希存储 (SHA256)，不存明文

### 可扩展性设计
- 模型注册中心支持热插拔（通过 model_configs 表 + 策略模式）
- 翻译引擎可替换（统一 TranslateEngine 接口抽象）
- ASR 引擎可替换（Provider 模式：ASRProvider 基类）
- 存储后端可切换（StorageBackend 抽象 + MinIO/OSS/S3 实现）
- LLM Provider 可替换（OpenAI 兼容接口统一）