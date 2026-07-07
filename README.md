让我先了解一下项目的详细信息，以便生成准确的 README 内容。
Let me gather a bit more context about the project's frontend pages and features.
以下是根据项目实际情况生成的完整 README 内容，你可以直接复制使用：

---

```markdown
# MeetScript — 企业级智能会议纪要平台

> 上传音视频 → 自动语音识别 → 翻译 / 总结 / 搜索，全流程 AI 驱动

## 技术栈

| 层 | 技术 |
|---|------|
| **后端** | Python 3.12 / FastAPI / Celery / SQLAlchemy (async) |
| **前端** | React 19 / TypeScript / Vite / Ant Design 6 / Tailwind CSS 4 |
| **数据库** | PostgreSQL 16 + Redis 7 |
| **存储** | MinIO (开发) / 阿里云 OSS (生产) |
| **AI 引擎** | 阿里云百炼 DashScope（千问系列模型） |
| **基础设施** | Docker Compose / Nginx / Prometheus + Grafana |

## 核心功能

- **音视频上传与处理** — 支持 MP4 / AVI / MOV / WAV / MP3 等 12 种格式，最大 2 GB
- **自动语音识别 (ASR)** — 基于千问 Paraformer，支持说话人分离 + 置信度评分
- **多语言翻译** — 92 种语言互译，选中字幕即翻
- **AI 会议总结** — LLM 自动生成结构化纪要（议题 / 决议 / 待办）
- **全文搜索** — PostgreSQL 中文全文检索，跨会议搜索字幕内容
- **字幕导出** — 支持 SRT / VTT / JSON / TXT 四种格式
- **多语言界面** — 前端支持中文 / 英文 / 日文
- **模型热切换** — 在管理后台一键切换 ASR / 翻译 / 总结模型
- **Token 统计** — 按模型类型实时统计 API 消耗量
- **API Key 管理** — 支持创建和管理第三方 API 访问密钥
- **实时任务进度** — SSE 推送任务状态，前端自动刷新
- **可视化仪表盘** — 会议数量 / Token 消耗 / 任务状态趋势图
- **企业级基础设施** — 请求 ID 追踪 / 访问日志 / 限流 / Prometheus 监控 / Sentry 错误追踪

## 快速开始

### 前置条件

- Docker Desktop（20.10+）
- 阿里云 DashScope API Key（[获取地址](https://dashscope.aliyun.com/)）

### 1. 配置环境变量

```bash
cd meetscript-api
cp .env.example .env
```

编辑 `.env`，填入你的 `DASHSCOPE_API_KEY`：

```ini
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

> 其余配置项（数据库密码、MinIO 密钥等）使用默认值即可在本地运行。

### 2. 启动全部服务

```bash
cd meetscript-api
docker compose up -d --build
```

首次构建约需 3-5 分钟（含镜像拉取、Python 依赖安装、npm 依赖安装）。

### 3. 初始化数据库 & 预置模型配置

```bash
# 运行数据库迁移
docker compose exec api alembic upgrade head

# 预置 AI 模型配置（ASR / 翻译 / 总结）
docker compose exec celery_worker_high python -m app.seed_models
```

### 4. 访问

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost:5173 | React 开发服务器 |
| API 文档 (Swagger) | http://localhost:8000/docs | 交互式 API 调试 |
| API 文档 (ReDoc) | http://localhost:8000/redoc | 只读 API 文档 |
| MinIO 控制台 | http://localhost:9001 | 对象存储管理 |
| Prometheus | http://localhost:9090 | 指标采集 |
| Grafana | http://localhost:3001 | 监控面板 |
| Nginx | http://localhost:80 | 反向代理入口 |

### 默认账号

| 项目 | 值 |
|------|-----|
| 平台登录 | `admin` / `meetscript` |
| MinIO | `minioadmin` / `minioadmin` |
| Grafana | `admin` / `admin` |
| PostgreSQL | `meetscript` / `meetscript` |

## 项目结构

```
MeetScript/
├── meetscript-api/               # 后端 FastAPI 应用
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/               # API 路由层
│   │   │   │   ├── auth.py       #   认证（登录/刷新 Token）
│   │   │   │   ├── users.py      #   用户管理
│   │   │   │   ├── meetings.py   #   会议 CRUD + 上传 + 流媒体
│   │   │   │   ├── subtitles.py  #   字幕查询
│   │   │   │   ├── translations.py # 翻译请求与查询
│   │   │   │   ├── tasks.py      #   任务状态
│   │   │   │   ├── models.py     #   AI 模型配置
│   │   │   │   ├── token_usage.py #  Token 消耗统计
│   │   │   │   ├── api_keys.py   #   API Key 管理
│   │   │   │   ├── exports.py    #   字幕导出
│   │   │   │   ├── search.py     #   全文搜索
│   │   │   │   └── sse.py        #   服务端推送事件
│   │   │   └── deps.py           #   依赖注入（当前用户/数据库会话）
│   │   ├── core/                 # 核心配置
│   │   │   ├── config.py         #   pydantic-settings 全局配置
│   │   │   ├── database.py       #   SQLAlchemy async 引擎 & 会话
│   │   │   ├── redis_client.py   #   Redis 连接池
│   │   │   ├── security.py       #   JWT + bcrypt 密码哈希
│   │   │   └── celery_app.py     #   Celery 应用工厂
│   │   ├── middleware/           # 中间件层
│   │   │   ├── request_id.py     #   请求 ID 注入
│   │   │   ├── access_log.py     #   结构化访问日志 (structlog)
│   │   │   └── rate_limit.py     #   基于 slowapi 的限流
│   │   ├── models/               # SQLAlchemy ORM 模型
│   │   │   ├── base.py           #   UUID 主键 + 时间戳 + 软删除 基类
│   │   │   ├── user.py           #   用户
│   │   │   ├── meeting.py        #   会议
│   │   │   ├── subtitle.py       #   字幕
│   │   │   ├── translation.py    #   翻译记录
│   │   │   ├── task.py           #   异步任务
│   │   │   ├── model_config.py   #   AI 模型配置
│   │   │   ├── token_usage.py    #   Token 消耗记录
│   │   │   ├── api_key.py        #   API 密钥
│   │   │   └── audit_log.py      #   审计日志
│   │   ├── schemas/              # Pydantic 请求/响应 Schema
│   │   ├── services/             # 业务逻辑层
│   │   │   ├── asr_service.py        #   语音识别服务
│   │   │   ├── translation_service.py #  翻译服务
│   │   │   ├── summary_service.py    #   会议总结服务
│   │   │   ├── diarization_service.py # 说话人分离
│   │   │   ├── audio_processor.py    #   音频预处理 (ffmpeg)
│   │   │   ├── subtitle_service.py   #   字幕管理
│   │   │   ├── meeting_service.py    #   会议业务
│   │   │   ├── auth_service.py       #   认证业务
│   │   │   ├── api_key_service.py    #   API Key 业务
│   │   │   ├── search_service.py     #   全文搜索业务
│   │   │   ├── cache_service.py      #   Redis 缓存
│   │   │   ├── model_registry.py     #   模型注册中心
│   │   │   ├── token_service.py      #   Token 计费
│   │   │   ├── task_service.py       #   任务管理
│   │   │   └── file_service.py       #   对象存储抽象层
│   │   ├── tasks/                # Celery 异步任务
│   │   │   ├── process_meeting.py #   会议处理编排 (chain)
│   │   │   ├── asr_task.py        #   ASR 识别任务
│   │   │   ├── audio_task.py      #   音频提取任务
│   │   │   ├── translation_task.py #  翻译任务
│   │   │   ├── summary_task.py    #   总结任务
│   │   │   └── export_task.py     #   导出任务
│   │   └── utils/                # 工具模块
│   │       ├── srt_parser.py     #   SRT 字幕解析
│   │       ├── token_counter.py  #   tiktoken Token 计数
│   │       └── time_utils.py     #   时间格式化
│   ├── migrations/               # Alembic 数据库迁移
│   ├── nginx/                    # Nginx 反向代理配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── prometheus.yml
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── .env.example
│
├── meetscript-web/               # 前端 React + Vite 应用
│   └── src/
│       ├── api/                  # API 调用封装 (axios)
│       ├── pages/                # 页面组件
│       │   ├── Dashboard/        #   仪表盘
│       │   ├── MeetingUpload/    #   上传会议
│       │   ├── MeetingDetail/    #   会议详情（视频 + 字幕联动）
│       │   ├── TaskManagement/   #   任务管理
│       │   ├── ModelConfig/      #   模型配置
│       │   ├── TokenUsage/       #   Token 消耗统计
│       │   ├── ApiManagement/    #   API Key 管理
│       │   ├── TranslationView/  #   翻译视图
│       │   ├── SearchResult/     #   全文搜索
│       │   └── Login/            #   登录
│       ├── components/           # 通用组件
│       ├── hooks/                # 自定义 Hooks
│       │   ├── useSSE.ts         #   SSE 服务端推送
│       │   ├── useSearch.ts      #   搜索逻辑
│       │   └── useTaskProgress.ts #  任务进度轮询
│       ├── stores/               # Zustand 状态管理
│       │   ├── authStore.ts      #   认证状态
│       │   ├── meetingStore.ts   #   会议状态
│       │   ├── searchStore.ts    #   搜索状态
│       │   └── uiStore.ts       #   UI 状态
│       ├── i18n/                 # 国际化（中 / 英 / 日）
│       ├── types/                # TypeScript 类型定义
│       └── utils/                # 工具函数
```

## 处理流程

```
上传视频/音频
    │
    ▼
音频预处理 (ffmpeg)
├── 提取音轨、转码为 16kHz 单声道 WAV
├── 大文件自动分段 (30 分钟/段)
└── 上传音频片段至 MinIO/OSS
    │
    ▼
ASR 语音识别 (DashScope Paraformer)
├── 说话人分离 (diarization)
├── 时间轴对齐
└── 置信度评分
    │
    ├──► 字幕展示（视频 + 字幕联动，飞书风格）
    │
    ├──► 翻译 (qwen-mt)
    │    └── 92 语言互译，选中字幕即翻
    │
    └──► 会议总结 (qwen-max)
         └── 结构化纪要（议题 / 决议 / 待办事项）
```

## AI 模型

| 类型 | 默认模型 | 可选模型 |
|------|---------|---------|
| 语音识别 (ASR) | `fun-asr` | `fun-asr-mtl` / `qwen3-asr-flash-filetrans` / `paraformer-v2` |
| 翻译 | `qwen-mt-plus` | `qwen-mt-turbo` / `qwen-mt-flash` |
| 会议总结 (LLM) | `qwen-max` | `qwen-plus` / `qwen-turbo` |

> 模型通过注册中心动态管理，支持运行时互斥启停。在「模型配置」页面可一键切换。

## API 概览

| 路由前缀 | 说明 | 主要端点 |
|---------|------|---------|
| `/api/v1/auth` | 认证 | `POST /login`, `POST /refresh` |
| `/api/v1/users` | 用户管理 | `GET /me`, `PATCH /me` |
| `/api/v1/meetings` | 会议管理 | `POST /upload`, `GET /{id}`, `GET /{id}/stream` |
| `/api/v1/subtitles` | 字幕查询 | `GET /meetings/{id}/subtitles` |
| `/api/v1/translations` | 翻译 | `POST /meetings/{id}/translate`, `GET /{meeting_id}` |
| `/api/v1/tasks` | 任务状态 | `GET /`, `GET /{id}` |
| `/api/v1/model-configs` | 模型配置 | `GET /`, `PUT /{id}` |
| `/api/v1/token-usage` | Token 统计 | `GET /stats`, `GET /records` |
| `/api/v1/api-keys` | API Key | `POST /`, `DELETE /{id}` |
| `/api/v1/exports` | 字幕导出 | `POST /meetings/{id}/export` (SRT/VTT/JSON/TXT) |
| `/api/v1/search` | 全文搜索 | `GET /` |
| `/api/v1/sse` | 实时推送 | `GET /tasks/subscribe` (Server-Sent Events) |
| `/api/v1/health` | 健康检查 | `GET /` |

## 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ENV` | 运行环境 | `development` |
| `SECRET_KEY` | JWT 签名密钥 | 生产环境务必修改 |
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql://meetscript:meetscript@postgres:5432/meetscript` |
| `REDIS_URL` | Redis 连接串 | `redis://redis:6379` |
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key | **必填** |
| `STORAGE_BACKEND` | 存储后端 | `minio` (可选 `oss` / `s3`) |
| `MAX_UPLOAD_SIZE_MB` | 上传文件大小限制 | `2048` |
| `RATE_LIMIT_DEFAULT` | 默认限流策略 | `100/minute` |
| `CORS_ORIGINS` | 允许的跨域来源 | `http://localhost:5173,...` |
| `PROMETHEUS_ENABLED` | 是否启用 Prometheus | `true` |
| `SENTRY_DSN` | Sentry 错误追踪 DSN | 可选 |

完整配置项见 [.env.example](meetscript-api/.env.example)。

## 常用命令

```bash
# ── 服务管理 ──────────────────────────────────────

# 启动所有服务
docker compose up -d --build

# 停止所有服务
docker compose down

# 只重启 API
docker compose restart api

# ── 日志查看 ──────────────────────────────────────

# API 日志
docker compose logs -f api

# Celery Worker 日志 (高优先级队列)
docker compose logs -f celery_worker_high

# ── 数据库操作 ────────────────────────────────────

# 运行迁移
docker compose exec api alembic upgrade head

# 生成新迁移文件
docker compose exec api alembic revision --autogenerate -m "description"

# 回滚迁移
docker compose exec api alembic downgrade -1

# 进入 PostgreSQL
docker compose exec postgres psql -U meetscript -d meetscript

# ── 预置数据 ──────────────────────────────────────

# 初始化 AI 模型配置
docker compose exec celery_worker_high python -m app.seed_models

# ── 进入容器 ──────────────────────────────────────

docker compose exec api bash
docker compose exec celery_worker_high bash

# ── 清理 ──────────────────────────────────────────

# 完全清理（含数据卷）
docker compose down -v
```

## 基础设施架构

```
                    ┌──────────────┐
                    │   Browser    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    Nginx     │  :80 (反向代理)
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼───┐  ┌────▼─────┐
        │    API    │ │  Web  │  │  MinIO   │
        │  :8000    │ │ :5173 │  │ :9000/01 │
        └──┬───┬────┘ └───────┘  └──────────┘
           │   │
    ┌──────▼┐ ┌▼──────┐
    │Postgre│ │ Redis │
    │ :5432 │ │ :6379 │
    └───────┘ └───┬───┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼────┐  ┌─────▼────┐  ┌────▼────┐
│Worker  │  │ Worker   │  │ Worker  │
│ High   │  │ Normal   │  │ Low     │
└───┬────┘  └─────┬────┘  └────┬────┘
    │             │             │
    └─────────────┼─────────────┘
                  │
           ┌──────▼──────┐
           │ Celery Beat │  (定时任务调度)
           └─────────────┘
```

- **Celery 三队列架构**：`priority_high`（音频处理）、`priority_normal`（ASR/翻译/总结）、`priority_low`（导出）各自独立 Worker，互不阻塞
- **Connection Pooling**：SQLAlchemy async 连接池 + Redis 连接池，支持高并发
- **数据隔离**：所有业务数据按 `user_id` 严格隔离，用户之间数据不可见

## 监控

| 组件 | 地址 | 说明 |
|------|------|------|
| Prometheus | http://localhost:9090 | 指标采集存储 |
| Grafana | http://localhost:3001 | 可视化面板 (admin/admin) |
| API Metrics | http://localhost:8000/metrics | Prometheus 指标端点 |

集成指标包括：请求数 / 响应延迟 / 状态码分布 / 并发连接数 / Celery 任务量。

## 开发指南

### 本地开发（不使用 Docker）

**后端：**

```bash
cd meetscript-api

# 创建虚拟环境
python -m venv .venv
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # macOS / Linux

# 安装依赖
pip install -e ".[dev]"

# 启动 API（需要先启动 PostgreSQL、Redis、MinIO）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动 Celery Worker
celery -A app.core.celery_app worker -Q priority_high,priority_normal,priority_low -l info
```

**前端：**

```bash
cd meetscript-web

npm install
npm run dev
```

### 代码规范

- 后端：Ruff 格式化 + MyPy 类型检查
- 前端：Oxlint + TypeScript strict 模式
- 遵循最小影响范围修复原则

### 测试

```bash
cd meetscript-api
pytest -v
```

## License

MIT
```

---

以上就是完整的 README 内容，涵盖了项目概述、技术栈、功能特性、快速开始、项目结构、处理流程、API 概览、环境变量、架构图、常用命令等所有关键信息。你可以直接全选复制使用。
