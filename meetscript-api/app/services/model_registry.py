"""Model registry: CRUD for model configurations with Redis caching."""

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_config import ModelConfig
from app.services.cache_service import cache_service


class ModelRegistry:
    """Manages AI model configurations with caching and provider abstraction."""

    @staticmethod
    async def get_active_config(
        db: AsyncSession,
        model_type: str,
    ) -> Optional[ModelConfig]:
        """Get the active model config for a given type (asr/translation/summary).

        Checks Redis cache first, falls back to DB.
        """
        # Try cache
        cached = await cache_service.get_model_config(model_type)
        if cached:
            return cached

        # Query DB
        result = await db.execute(
            select(ModelConfig)
            .where(ModelConfig.model_type == model_type)
            .where(ModelConfig.is_active == True)
            .order_by(ModelConfig.updated_at.desc())
            .limit(1)
        )
        config = result.scalar_one_or_none()

        if config:
            # Cache it
            config_dict = {
                "id": str(config.id),
                "model_type": config.model_type,
                "provider": config.provider,
                "model_name": config.model_name,
                "endpoint_url": config.endpoint_url,
                "parameters": config.parameters,
                "is_active": config.is_active,
            }
            await cache_service.set_model_config(model_type, config_dict)

        return config

    @staticmethod
    async def list_configs(
        db: AsyncSession,
        model_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> list[ModelConfig]:
        """List model configs with optional filters."""
        query = select(ModelConfig)

        if model_type:
            query = query.where(ModelConfig.model_type == model_type)
        if is_active is not None:
            query = query.where(ModelConfig.is_active == is_active)

        query = query.order_by(ModelConfig.model_type, ModelConfig.updated_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def _deactivate_others(
        db: AsyncSession,
        model_type: str,
        exclude_id: Optional[uuid.UUID],
    ) -> None:
        """Set is_active=False for all other configs of the same type."""
        stmt = (
            update(ModelConfig)
            .where(ModelConfig.model_type == model_type)
            .where(ModelConfig.is_active == True)
        )
        if exclude_id is not None:
            stmt = stmt.where(ModelConfig.id != exclude_id)
        stmt = stmt.values(is_active=False)
        await db.execute(stmt)

    @staticmethod
    async def create_config(
        db: AsyncSession,
        model_type: str,
        provider: str,
        model_name: str,
        api_key_encrypted: str,
        endpoint_url: Optional[str] = None,
        parameters: Optional[dict] = None,
        is_active: bool = True,
    ) -> ModelConfig:
        """Create a new model configuration."""
        # Enforce mutual exclusion: only one active config per type
        if is_active:
            await ModelRegistry._deactivate_others(db, model_type, exclude_id=None)

        config = ModelConfig(
            model_type=model_type,
            provider=provider,
            model_name=model_name,
            api_key_encrypted=api_key_encrypted,
            endpoint_url=endpoint_url,
            parameters=parameters,
            is_active=is_active,
        )
        db.add(config)
        await db.flush()

        # Refresh to load DB-computed values (created_at, updated_at)
        await db.refresh(config)

        # Invalidate cache for this model type
        await cache_service.delete(f"model_config:{model_type}")

        return config

    @staticmethod
    async def update_config(
        db: AsyncSession,
        config_id: uuid.UUID,
        **kwargs,
    ) -> Optional[ModelConfig]:
        """Update a model configuration."""
        result = await db.execute(
            select(ModelConfig).where(ModelConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            return None

        # Enforce mutual exclusion: only one active config per type
        new_is_active = kwargs.get("is_active")
        if new_is_active is True:
            await ModelRegistry._deactivate_others(db, config.model_type, exclude_id=config_id)

        for key, value in kwargs.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

        await db.flush()

        # Refresh to load DB-computed values (e.g. onupdate=func.now())
        await db.refresh(config)

        # Invalidate cache
        await cache_service.delete(f"model_config:{config.model_type}")

        return config

    @staticmethod
    async def delete_config(
        db: AsyncSession,
        config_id: uuid.UUID,
    ) -> bool:
        """Delete a model configuration."""
        result = await db.execute(
            select(ModelConfig).where(ModelConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            return False

        model_type = config.model_type
        await db.delete(config)
        await db.flush()

        # Invalidate cache
        await cache_service.delete(f"model_config:{model_type}")

        return True

    @staticmethod
    def get_provider_config(config: ModelConfig) -> dict:
        """Extract provider configuration for API calls."""
        return {
            "provider": config.provider,
            "model_name": config.model_name,
            "api_key": config.api_key_encrypted,  # Note: stored encrypted
            "endpoint_url": config.endpoint_url,
            "parameters": config.parameters or {},
        }


# Singleton
model_registry = ModelRegistry()
