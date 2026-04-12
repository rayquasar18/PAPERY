"""Rate limit rule schemas for admin CRUD."""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RateLimitRuleRead(BaseModel):
    """Rate limit rule response."""

    model_config = ConfigDict(from_attributes=True)

    uuid: uuid_pkg.UUID
    tier_id: int | None = None
    tier_slug: str | None = None
    tier_name: str | None = None
    endpoint_pattern: str
    max_requests: int
    window_seconds: int
    description: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class RateLimitRuleCreate(BaseModel):
    """Create a new rate limit rule."""

    tier_uuid: uuid_pkg.UUID | None = Field(
        None,
        description="UUID of the tier this rule applies to. NULL for default rule.",
    )
    endpoint_pattern: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Endpoint pattern, e.g. 'auth:login', 'documents:upload'.",
    )
    max_requests: int = Field(..., ge=1, description="Maximum requests allowed in the window.")
    window_seconds: int = Field(..., ge=1, description="Window duration in seconds.")
    description: str | None = None


class RateLimitRuleUpdate(BaseModel):
    """Partial update for a rate limit rule. All fields optional."""

    tier_uuid: uuid_pkg.UUID | None = None
    endpoint_pattern: str | None = Field(None, min_length=1, max_length=200)
    max_requests: int | None = Field(None, ge=1)
    window_seconds: int | None = Field(None, ge=1)
    description: str | None = None
