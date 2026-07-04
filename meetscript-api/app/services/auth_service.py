"""User authentication service."""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User


class AuthService:
    """User registration, authentication, and profile management."""

    @staticmethod
    async def get_user_by_username(
        db: AsyncSession,
        username: str,
    ) -> Optional[User]:
        """Find a user by username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> Optional[User]:
        """Find a user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def authenticate(
        db: AsyncSession,
        username: str,
        password: str,
    ) -> Optional[User]:
        """Authenticate a user with username and password."""
        user = await AuthService.get_user_by_username(db, username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user

    @staticmethod
    async def create_user(
        db: AsyncSession,
        username: str,
        email: str,
        password: str,
        role: str = "viewer",
        preferred_language: str = "zh-CN",
    ) -> User:
        """Register a new user."""
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=role,
            preferred_language=preferred_language,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def check_user_exists(
        db: AsyncSession,
        username: Optional[str] = None,
        email: Optional[str] = None,
    ) -> bool:
        """Check if a user with the given username or email exists."""
        conditions = []
        if username:
            conditions.append(User.username == username)
        if email:
            conditions.append(User.email == email)

        if not conditions:
            return False

        result = await db.execute(
            select(User).where(
                conditions[0] if len(conditions) == 1 else (conditions[0] | conditions[1])
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        user_id: uuid.UUID,
        **kwargs,
    ) -> Optional[User]:
        """Update user profile fields."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)

        await db.flush()
        return user


# Singleton
auth_service = AuthService()
