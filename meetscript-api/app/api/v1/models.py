"""Model configuration routes."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id, get_db
from app.schemas.model_config import ModelConfigCreate, ModelConfigOut, ModelConfigUpdate
from app.services.model_registry import model_registry

router = APIRouter()


@router.get("", response_model=list[ModelConfigOut])
async def list_model_configs(
    model_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    configs = await model_registry.list_configs(db, model_type=model_type, is_active=is_active)
    return [ModelConfigOut.model_validate(c) for c in configs]


@router.post("", response_model=ModelConfigOut)
async def create_model_config(
    body: ModelConfigCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    config = await model_registry.create_config(
        db,
        model_type=body.model_type,
        provider=body.provider,
        model_name=body.model_name,
        api_key_encrypted=body.api_key_encrypted,
        endpoint_url=body.endpoint_url,
        parameters=body.parameters,
        is_active=body.is_active,
    )
    result = ModelConfigOut.model_validate(config)
    await db.commit()
    return result


@router.put("/{config_id}", response_model=ModelConfigOut)
async def update_model_config(
    config_id: str,
    body: ModelConfigUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    config = await model_registry.update_config(
        db,
        uuid.UUID(config_id),
        **body.model_dump(exclude_none=True),
    )
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")
    # Serialize BEFORE commit to avoid detached-instance MissingGreenlet errors
    result = ModelConfigOut.model_validate(config)
    await db.commit()
    return result


@router.delete("/{config_id}", status_code=204)
async def delete_model_config(
    config_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    deleted = await model_registry.delete_config(db, uuid.UUID(config_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Model config not found")
    await db.commit()
