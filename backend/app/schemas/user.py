"""User profile request/response schemas."""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserProfileRead(BaseModel):
    """Full user profile response — includes computed fields not in UserPublicRead."""

    model_config = ConfigDict(from_attributes=True)

    uuid: uuid_pkg.UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    tier_name: str = "free"
    has_password: bool = False
    oauth_providers: list[str] = Field(default_factory=list)


class UserProfileUpdate(BaseModel):
    """Partial update for user profile — display_name only."""

    display_name: str | None = Field(
        None,
        min_length=2,
        max_length=50,
        pattern=r"^[\w\s\-]+$",
    )


class DeleteAccountRequest(BaseModel):
    """Account deletion confirmation — password for local users, email for OAuth-only."""

    password: str | None = None
    email: str | None = None

    @model_validator(mode="after")
    def exactly_one_must_be_provided(self) -> DeleteAccountRequest:
        """Enforce: exactly one of password or email must be provided."""
        if self.password is None and self.email is None:
            raise ValueError("Either password or email must be provided for account deletion")
        if self.password is not None and self.email is not None:
            raise ValueError("Provide either password or email, not both")
        return self


class AvatarUploadResponse(BaseModel):
    """Response after successful avatar upload."""

    avatar_url: str
    thumbnail_url: str
    message: str = "Avatar uploaded successfully"
