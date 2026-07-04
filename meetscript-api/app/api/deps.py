"""Dependency injection for FastAPI routes."""

from typing import Optional

from fastapi import Depends, HTTPException, Query, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token

security_scheme = HTTPBearer(auto_error=False)
api_key_scheme = HTTPBearer(auto_error=False, scheme_name="ApiKeyAuth")


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    token: Optional[str] = Query(None, description="JWT access token (fallback for media/video requests)"),
) -> str:
    """Validate JWT and return the user ID (sub claim).

    Accepts token via Authorization: Bearer header OR ?token= query parameter.
    The query parameter fallback is needed for <video>/<audio> HTML elements
    which cannot send custom HTTP headers.
    """
    token_value = credentials.credentials if credentials else token
    if not token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
        )
    payload = decode_token(token_value)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload["sub"]


async def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[str]:
    """Optionally validate JWT; returns None if not provided."""
    if credentials is None:
        return None
    payload = decode_token(credentials.credentials)
    if payload is None:
        return None
    return payload.get("sub")


async def get_user_id_from_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(api_key_scheme),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Validate API Key and return the associated user ID.

    This is used for third-party integrations that authenticate via API keys
    instead of JWT tokens. The API key is passed as a Bearer token.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide it as: Authorization: Bearer <api_key>",
        )

    from app.services.api_key_service import api_key_service

    key_info = await api_key_service.validate_key(db, credentials.credentials)
    if key_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or inactive API key",
        )

    return key_info["user_id"]
