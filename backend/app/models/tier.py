"""Tier model — subscription tiers with configurable limits and feature flags."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class Tier(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Subscription tier with numeric limits + JSONB feature flags.

    Convention: -1 means unlimited for any numeric limit column.
    """

    __tablename__ = "tier"

    # Human-readable name + unique slug
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Dedicated columns for typed, queryable limits ---
    max_projects: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_docs_per_project: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_fixes_monthly: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    max_file_size_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    # --- JSONB for flexible data ---
    allowed_models: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    feature_flags: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")

    # Stripe price ID (nullable — free tier has no Stripe price)
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<Tier slug={self.slug} name={self.name}>"
