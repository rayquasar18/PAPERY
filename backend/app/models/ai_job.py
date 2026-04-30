"""AI job ORM model for async orchestration and status polling."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.schemas.ai_job import AIJobStatus


class AIJob(Base, UUIDMixin, TimestampMixin):
    """Persisted AI job envelope with lifecycle status and execution metadata."""

    __tablename__ = "ai_job"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    document_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    status: Mapped[AIJobStatus] = mapped_column(
        SAEnum(AIJobStatus, name="ai_job_status", native_enum=False),
        nullable=False,
        default=AIJobStatus.PENDING,
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    error_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    provider_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True, default=None)

    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    owner: Mapped["User"] = relationship("User", lazy="selectin")
