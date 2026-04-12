"""SystemSetting model — persistent key-value configuration with JSONB values."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class SystemSetting(Base, UUIDMixin, TimestampMixin):
    """Key-value system setting stored in DB with JSONB value.

    Settings are registered via an allowlist in code. Admin can only
    edit values of pre-defined keys — cannot create arbitrary keys via API.
    Value is wrapped in {"v": <actual_value>} for consistent JSONB typing.
    """

    __tablename__ = "system_setting"

    key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    value: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SystemSetting key={self.key} category={self.category}>"
