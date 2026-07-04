"""Model configuration model."""

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ModelConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "model_configs"

    model_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # asr / translation / summary
    provider: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # aliyun_bailian / openai / ...
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
