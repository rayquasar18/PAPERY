"""UsageTracking model — per-user monthly quota tracking."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UsageTracking(Base, TimestampMixin):
    """Tracks usage counts per user per metric per billing period.

    Metrics: "projects", "documents", "fixes".
    Period: monthly — period_start is first day of month, period_end is last day.
    Convention: upsert via INSERT ... ON CONFLICT DO UPDATE SET count = count + 1.
    """

    __tablename__ = "usage_tracking"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "metric", "period_start", name="uq_usage_user_metric_period"),
        Index("ix_usage_user_metric_active", "user_id", "metric", "period_end"),
    )

    def __repr__(self) -> str:
        return f"<UsageTracking user_id={self.user_id} metric={self.metric} count={self.count}>"
