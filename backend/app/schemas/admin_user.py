"""Admin user management schemas — superuser-only views and operations."""

from __future__ import annotations

import math
import uuid as uuid_pkg
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminUserRead(BaseModel):
    """Full user data visible to admin — includes admin-only fields."""

    model_config = ConfigDict(from_attributes=True)

    uuid: uuid_pkg.UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    status: str
    is_verified: bool
    is_superuser: bool
    tier_slug: str | None = None
    tier_name: str | None = None
    stripe_customer_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class AdminUserUpdate(BaseModel):
    """Partial update schema for admin user management.

    All fields optional — only provided fields are applied.
    """

    status: str | None = Field(None, pattern=r"^(active|deactivated|banned)$")
    tier_uuid: uuid_pkg.UUID | None = None
    is_superuser: bool | None = None
    is_verified: bool | None = None
    display_name: str | None = Field(None, min_length=2, max_length=100)


class AdminUserListResponse(BaseModel):
    """Paginated user list response for admin."""

    items: list[AdminUserRead]
    total: int
    page: int
    per_page: int
    pages: int

    @classmethod
    def build(
        cls,
        items: list[AdminUserRead],
        total: int,
        page: int,
        per_page: int,
    ) -> AdminUserListResponse:
        """Construct a paginated response with computed pages count."""
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=max(1, math.ceil(total / per_page)),
        )
