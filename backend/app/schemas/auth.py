"""Authentication request/response schemas."""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    """User registration payload."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def password_must_not_match_email(self) -> RegisterRequest:
        """Reject passwords that are identical to the email address."""
        if self.password and self.password.lower() == self.email.lower():
            raise ValueError("Password must not match the email address")
        return self


class LoginRequest(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    """Email verification payload."""

    token: str


class ResendVerificationRequest(BaseModel):
    """Resend verification email payload."""

    email: EmailStr


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class UserPublicRead(BaseModel):
    """Public-safe user representation returned by auth endpoints."""

    model_config = ConfigDict(from_attributes=True)

    uuid: uuid_pkg.UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    is_verified: bool
    is_superuser: bool
    created_at: datetime


class AuthResponse(BaseModel):
    """Response returned after successful login or registration."""

    user: UserPublicRead
    message: str


class MessageResponse(BaseModel):
    """Generic message-only response."""

    message: str


# ---------------------------------------------------------------------------
# Internal schemas (token payload)
# ---------------------------------------------------------------------------
class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    sub: str
    jti: str
    type: str  # "access" | "refresh"
    exp: int
    iat: int
    family: str | None = None
    purpose: str | None = None
