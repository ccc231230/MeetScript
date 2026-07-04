"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "MeetScript"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field("development", alias="ENV")
    DEBUG: bool = False
    SECRET_KEY: SecretStr = Field(alias="SECRET_KEY")
    API_V1_PREFIX: str = "/api/v1"

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: SecretStr = Field(alias="DATABASE_URL")
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379"
    REDIS_BROKER_DB: int = 0
    REDIS_RESULT_DB: int = 1
    REDIS_CACHE_DB: int = 2

    # ── JWT ──────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Storage ──────────────────────────────────────────────────
    STORAGE_BACKEND: str = "minio"  # "minio" | "oss" | "s3"
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_PUBLIC_ENDPOINT: str = "localhost:9000"  # Browser-accessible endpoint for presigned URLs
    MINIO_ACCESS_KEY: SecretStr = Field(alias="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: SecretStr = Field(alias="MINIO_SECRET_KEY")
    MINIO_BUCKET: str = "meetscript"
    MINIO_SECURE: bool = False
    # Public base URL for storage access from external services (e.g., DashScope ASR).
    # For local dev, set this to your ngrok/cpolar tunnel: "https://xxx.ngrok.io/meetscript"
    PUBLIC_STORAGE_BASE_URL: Optional[str] = None

    OSS_ENDPOINT: Optional[str] = None
    OSS_ACCESS_KEY_ID: Optional[SecretStr] = None
    OSS_ACCESS_KEY_SECRET: Optional[SecretStr] = None
    OSS_BUCKET: Optional[str] = None

    # ── AI / DashScope ───────────────────────────────────────────
    DASHSCOPE_API_KEY: SecretStr = Field(alias="DASHSCOPE_API_KEY")
    DASHSCOPE_REGION: str = "cn-beijing"

    DEFAULT_ASR_MODEL: str = "paraformer-v2"
    DEFAULT_TRANSLATION_MODEL: str = "anytrans"
    DEFAULT_SUMMARY_MODEL: str = "qwen-max"

    # ── Celery ───────────────────────────────────────────────────
    CELERY_TASK_MAX_RETRIES: int = 3
    CELERY_TASK_RETRY_DELAY: int = 60
    CELERY_TASK_RETRY_BACKOFF_MAX: int = 600

    # ── CORS ─────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # ── Rate Limiting ────────────────────────────────────────────
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "10/minute"

    # ── Upload ───────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 2048  # 2 GB
    ALLOWED_AUDIO_EXTENSIONS: list[str] = [
        "mp4", "avi", "mov", "wav", "mp3", "m4a", "flac",
        "aac", "ogg", "wma", "webm", "mkv",
    ]

    # ── Monitoring ───────────────────────────────────────────────
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_ENABLED: bool = True

    # ── File Processing ──────────────────────────────────────────
    AUDIO_WORK_DIR: str = "/tmp/meetscript/audio"  # Persistent work dir for audio preprocessing
    AUDIO_SEGMENT_DURATION: int = 1800  # 30 minutes per segment
    AUDIO_TARGET_SAMPLE_RATE: int = 16000
    AUDIO_TARGET_CHANNELS: int = 1
    AUDIO_TARGET_FORMAT: str = "wav"
    FFMPEG_TIMEOUT: int = 300  # 5 minutes


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()  # type: ignore[call-arg]
