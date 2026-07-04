"""Redis cache service with multi-level caching strategies."""

import json
from typing import Any, Optional

from app.core.config import get_settings
from app.core.redis_client import get_redis

settings = get_settings()

# ── Cache key patterns ────────────────────────────────────────────
CACHE_PREFIX = "meetscript:cache"


class CacheService:
    """Centralized caching service with Cache-Aside pattern."""

    # ── Generic Cache Operations ───────────────────────────────────

    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """Retrieve a cached value, deserialize from JSON."""
        redis = await get_redis()
        full_key = f"{CACHE_PREFIX}:{key}"
        value = await redis.get(full_key)
        if value is None:
            return None
        return json.loads(value)

    @staticmethod
    async def set(key: str, value: Any, ttl: int = 300) -> None:
        """Set a cached value with TTL in seconds."""
        redis = await get_redis()
        full_key = f"{CACHE_PREFIX}:{key}"
        await redis.setex(full_key, ttl, json.dumps(value, default=str))

    @staticmethod
    async def delete(key: str) -> None:
        """Invalidate a cached entry."""
        redis = await get_redis()
        full_key = f"{CACHE_PREFIX}:{key}"
        await redis.delete(full_key)

    @staticmethod
    async def delete_pattern(pattern: str) -> int:
        """Delete all keys matching a pattern. Returns count deleted."""
        redis = await get_redis()
        full_pattern = f"{CACHE_PREFIX}:{pattern}"
        keys = []
        async for key in redis.scan_iter(match=full_pattern):
            keys.append(key)
        if keys:
            return await redis.delete(*keys)
        return 0

    # ── Domain-Specific Caching ────────────────────────────────────

    # Subtitles cache: 1h TTL
    @staticmethod
    async def get_meeting_subtitles(meeting_id: str, language: str) -> Optional[list[dict]]:
        return await CacheService.get(f"subtitles:meeting:{meeting_id}:lang:{language}")

    @staticmethod
    async def set_meeting_subtitles(meeting_id: str, language: str, data: list[dict]) -> None:
        await CacheService.set(f"subtitles:meeting:{meeting_id}:lang:{language}", data, ttl=3600)

    # Translation cache: 30d TTL (cost-saving)
    @staticmethod
    async def get_translation(text_hash: str, target_lang: str) -> Optional[str]:
        return await CacheService.get(f"translation:{text_hash}:{target_lang}")

    @staticmethod
    async def set_translation(text_hash: str, target_lang: str, translated_text: str) -> None:
        await CacheService.set(
            f"translation:{text_hash}:{target_lang}",
            translated_text,
            ttl=86400 * 30,
        )

    # Model config cache: 5min TTL
    @staticmethod
    async def get_model_config(model_type: str) -> Optional[dict]:
        return await CacheService.get(f"model_config:{model_type}")

    @staticmethod
    async def set_model_config(model_type: str, data: dict) -> None:
        await CacheService.set(f"model_config:{model_type}", data, ttl=300)

    # User session cache: 30min
    @staticmethod
    async def get_user_session(user_id: str) -> Optional[dict]:
        return await CacheService.get(f"session:{user_id}")

    @staticmethod
    async def set_user_session(user_id: str, data: dict) -> None:
        await CacheService.set(f"session:{user_id}", data, ttl=1800)

    # Task lock: 1h (deduplication)
    @staticmethod
    async def acquire_task_lock(meeting_id: str, task_type: str) -> bool:
        """Acquire distributed lock for task dedup. Returns True if acquired."""
        redis = await get_redis()
        key = f"task_lock:{meeting_id}:{task_type}"
        acquired = await redis.setnx(key, "1")
        if acquired:
            await redis.expire(key, 3600)
        return bool(acquired)

    @staticmethod
    async def release_task_lock(meeting_id: str, task_type: str) -> None:
        redis = await get_redis()
        key = f"task_lock:{meeting_id}:{task_type}"
        await redis.delete(key)

    # Rate limit counter: 1min window
    @staticmethod
    async def check_rate_limit(user_id: str, endpoint: str, limit: int = 100) -> bool:
        """Check rate limit. Returns True if under limit."""
        redis = await get_redis()
        key = f"rate_limit:{user_id}:{endpoint}"
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, 60)
        return current <= limit


# Singleton
cache_service = CacheService()
