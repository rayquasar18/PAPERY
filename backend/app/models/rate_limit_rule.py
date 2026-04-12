"""RateLimitRule model — configurable per-tier per-endpoint rate limiting."""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class RateLimitRule(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Rate limit rule for a specific tier and endpoint pattern.

    tier_id=NULL means this is a default rule applying to all tiers.
    tier_id set means this is a tier-specific override.
    Priority: tier-specific > default (tier_id=NULL) > hardcoded fallback.
    """

    __tablename__ = "rate_limit_rule"
    __table_args__ = (
        UniqueConstraint("tier_id", "endpoint_pattern", name="uq_rate_limit_tier_endpoint"),
    )

    tier_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("tier.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    endpoint_pattern: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )
    max_requests: Mapped[int] = mapped_column(Integer, nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship to Tier (optional — nullable FK)
    tier: Mapped["Tier"] = relationship("Tier", lazy="selectin")

    def __repr__(self) -> str:
        return f"<RateLimitRule endpoint={self.endpoint_pattern} tier_id={self.tier_id}>"
