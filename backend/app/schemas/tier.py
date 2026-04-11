"""Tier request/response schemas."""

from __future__ import annotations

import uuid as uuid_pkg

from pydantic import BaseModel, ConfigDict, Field


class TierPublicRead(BaseModel):
    """Public tier listing — visible to all users on pricing page."""

    model_config = ConfigDict(from_attributes=True)

    uuid: uuid_pkg.UUID
    name: str
    slug: str
    description: str | None = None
    max_projects: int
    max_docs_per_project: int
    max_fixes_monthly: int
    max_file_size_mb: int
    allowed_models: list[str] = Field(default_factory=list)
    feature_flags: dict[str, bool] = Field(default_factory=dict)


class TierRead(TierPublicRead):
    """Full tier response — includes admin-only fields."""

    stripe_price_id: str | None = None


class TierCreate(BaseModel):
    """Create a new tier (admin only)."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9\-]+$")
    description: str | None = None
    max_projects: int = Field(default=3, ge=-1)
    max_docs_per_project: int = Field(default=10, ge=-1)
    max_fixes_monthly: int = Field(default=20, ge=-1)
    max_file_size_mb: int = Field(default=10, ge=-1)
    allowed_models: list[str] = Field(default_factory=list)
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    stripe_price_id: str | None = None


class TierUpdate(BaseModel):
    """Partial update for an existing tier (admin only). All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=100)
    slug: str | None = Field(None, min_length=1, max_length=50, pattern=r"^[a-z0-9\-]+$")
    description: str | None = None
    max_projects: int | None = Field(None, ge=-1)
    max_docs_per_project: int | None = Field(None, ge=-1)
    max_fixes_monthly: int | None = Field(None, ge=-1)
    max_file_size_mb: int | None = Field(None, ge=-1)
    allowed_models: list[str] | None = None
    feature_flags: dict[str, bool] | None = None
    stripe_price_id: str | None = None
