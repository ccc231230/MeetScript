"""API Key management service with SHA256 hashing."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey


class ApiKeyService:
    """API Key generation, validation, and management."""

    KEY_PREFIX_LENGTH = 8  # First 8 chars stored as prefix for identification

    @staticmethod
    def generate_api_key() -> tuple[str, str, str]:
        """Generate a new API key.

        Returns:
            Tuple of (full_key, key_hash, prefix)
        """
        raw = f"ms_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        prefix = raw[: ApiKeyService.KEY_PREFIX_LENGTH]
        return raw, key_hash, prefix

    @staticmethod
    def hash_key(api_key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    async def create_key(
        db: AsyncSession,
        user_id: uuid.UUID,
        key_name: str,
        scopes: Optional[list[str]] = None,
        rate_limit: int = 100,
        expires_in_days: Optional[int] = None,
    ) -> dict:
        """Create a new API key.

        Returns dict with full_key (only time it's shown) and key metadata.
        """
        full_key, key_hash, prefix = ApiKeyService.generate_api_key()

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        api_key = ApiKey(
            user_id=user_id,
            key_name=key_name,
            api_key_hash=key_hash,
            prefix=prefix,
            scopes={"scopes": scopes} if scopes else None,
            rate_limit=rate_limit,
            expires_at=expires_at,
            is_active=True,
        )
        db.add(api_key)
        await db.flush()

        return {
            "api_key": full_key,
            "id": api_key.id,
            "key_name": api_key.key_name,
            "prefix": api_key.prefix,
            "scopes": api_key.scopes,
            "rate_limit": api_key.rate_limit,
            "expires_at": api_key.expires_at,
            "is_active": api_key.is_active,
            "created_at": api_key.created_at,
        }

    @staticmethod
    async def validate_key(
        db: AsyncSession,
        api_key: str,
    ) -> Optional[dict]:
        """Validate an API key and return its metadata.

        Returns None if invalid/expired/inactive.
        """
        key_hash = ApiKeyService.hash_key(api_key)

        result = await db.execute(
            select(ApiKey).where(ApiKey.api_key_hash == key_hash)
        )
        key_record = result.scalar_one_or_none()

        if not key_record:
            return None
        if not key_record.is_active:
            return None
        if key_record.expires_at and key_record.expires_at < datetime.now(timezone.utc):
            return None

        # Update last_used_at
        key_record.last_used_at = datetime.now(timezone.utc)
        await db.flush()

        return {
            "user_id": str(key_record.user_id),
            "scopes": key_record.scopes,
            "rate_limit": key_record.rate_limit,
        }

    @staticmethod
    async def list_keys(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[ApiKey]:
        """List all API keys for a user."""
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def deactivate_key(
        db: AsyncSession,
        key_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Deactivate an API key."""
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.id == key_id,
                ApiKey.user_id == user_id,
            )
        )
        key = result.scalar_one_or_none()
        if not key:
            return False

        key.is_active = False
        await db.flush()
        return True

    @staticmethod
    async def delete_key(
        db: AsyncSession,
        key_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete an API key permanently."""
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.id == key_id,
                ApiKey.user_id == user_id,
            )
        )
        key = result.scalar_one_or_none()
        if not key:
            return False

        await db.delete(key)
        await db.flush()
        return True


# Singleton
api_key_service = ApiKeyService()
