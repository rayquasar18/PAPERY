"""Authentication service — business logic for auth flows.

Orchestrates registration, login, logout, token rotation, email verification,
and superuser bootstrap. Delegates security primitives (password hashing,
JWT lifecycle, token blacklist) to ``app.core.security``.

Data access is handled by ``app.repositories.UserRepository`` — this service
contains only business logic, validation, and orchestration.
"""

from __future__ import annotations

import logging
import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.configs import settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.security import (
    blacklist_token,
    create_email_verification_token,
    create_token_pair,
    decode_token,
    hash_password,
    invalidate_token_family,
    is_token_blacklisted,
    register_token_in_family,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPayload
from app.utils.email import send_email

logger = logging.getLogger(__name__)


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    """Create a new local user.

    Raises ``ConflictError`` if the email is already registered.
    If the existing account is OAuth-only (no password), hints the user
    to log in via their OAuth provider instead.
    """
    user_repo = UserRepository(db)
    existing = await user_repo.get(email=email.lower())
    if existing is not None:
        if existing.hashed_password is None:
            raise ConflictError(
                detail="This email is linked to a social login. "
                "Please sign in with your OAuth provider.",
            )
        raise ConflictError(detail="Email already registered")

    return await user_repo.create_user(
        email=email,
        hashed_password=hash_password(password),
        is_active=True,
        is_verified=False,
        is_superuser=False,
    )


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Validate credentials, returning the user on success.

    Raises ``UnauthorizedError`` for invalid credentials or inactive accounts.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get(email=email.lower())
    if user is None:
        raise UnauthorizedError(detail="Invalid email or password")

    if user.hashed_password is None:
        raise UnauthorizedError(
            detail="This account uses social login. "
            "Please sign in with your OAuth provider.",
        )

    if not verify_password(password, user.hashed_password):
        raise UnauthorizedError(detail="Invalid email or password")

    if not user.is_active:
        raise UnauthorizedError(detail="Account is deactivated")

    return user


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
async def logout_user(
    access_payload: TokenPayload,
    refresh_jti: str | None = None,
) -> None:
    """Blacklist the current access token and optionally the refresh token.

    If the access token carries a ``family`` claim, the whole family is
    invalidated (revoking all related refresh tokens).
    """
    # Blacklist the access token for its remaining lifetime
    remaining = access_payload.exp - int(datetime.now(UTC).timestamp())
    if remaining > 0:
        await blacklist_token(access_payload.jti, remaining)

    # Blacklist explicit refresh jti if provided
    if refresh_jti:
        await blacklist_token(
            refresh_jti,
            settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )

    # Invalidate the entire token family (if present)
    if access_payload.family:
        await invalidate_token_family(access_payload.family)


# ---------------------------------------------------------------------------
# Token rotation (refresh)
# ---------------------------------------------------------------------------
async def rotate_refresh_token(
    db: AsyncSession,
    old_payload: TokenPayload,
) -> tuple[str, str]:
    """Issue a new token pair from a valid refresh token.

    Implements replay detection: if the old jti is already blacklisted,
    the entire token family is invalidated (all sessions revoked).

    Returns ``(new_access_token, new_refresh_token)``.
    """
    if old_payload.type != "refresh":
        raise UnauthorizedError(detail="Token is not a refresh token")

    family_id = old_payload.family
    if not family_id:
        raise UnauthorizedError(detail="Refresh token missing family claim")

    # Replay detection — if this jti was already used, someone stole a token
    if await is_token_blacklisted(old_payload.jti):
        logger.warning(
            "Refresh token replay detected — invalidating family=%s user=%s",
            family_id,
            old_payload.sub,
        )
        await invalidate_token_family(family_id)
        raise UnauthorizedError(
            detail="Token reuse detected. All sessions revoked for security.",
            error_code="TOKEN_REPLAY",
        )

    # Verify user still exists and is active
    user_repo = UserRepository(db)
    user = await user_repo.get(uuid=uuid_pkg.UUID(old_payload.sub))
    if user is None or not user.is_active:
        await invalidate_token_family(family_id)
        raise UnauthorizedError(detail="User not found or deactivated")

    # Blacklist the old refresh token
    remaining = old_payload.exp - int(datetime.now(UTC).timestamp())
    if remaining > 0:
        await blacklist_token(old_payload.jti, remaining)

    # Issue new pair in the same family
    access, refresh = create_token_pair(user.uuid, family_id=family_id)

    # Register the new refresh jti in the family
    new_refresh_payload = decode_token(refresh)
    await register_token_in_family(family_id, new_refresh_payload.jti)

    return access, refresh


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------
async def verify_email(db: AsyncSession, token: str) -> User:
    """Decode a verification token and mark the user as verified.

    Raises appropriate errors for invalid/expired tokens or missing users.
    """
    from jose import JWTError
    from jose import jwt as jose_jwt

    try:
        raw = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        payload = TokenPayload(**raw)
    except JWTError as exc:
        raise BadRequestError(detail=f"Invalid or expired verification token: {exc}") from exc

    if payload.purpose != "email_verify":
        raise BadRequestError(detail="Token is not an email verification token")

    user_repo = UserRepository(db)
    user = await user_repo.get(uuid=uuid_pkg.UUID(payload.sub))
    if user is None:
        raise NotFoundError(detail="User not found")

    if user.is_verified:
        raise BadRequestError(detail="Email is already verified")

    user.is_verified = True
    return await user_repo.update(user)


async def send_verification_email(email: str, user_uuid: uuid_pkg.UUID) -> None:
    """Generate a verification token and send the verification email."""
    token = create_email_verification_token(user_uuid)
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    html_body = f"""
    <html>
    <body style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Welcome to {settings.APP_NAME}!</h2>
        <p>Please verify your email address by clicking the button below:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}"
               style="background-color: #4F46E5; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                Verify Email
            </a>
        </p>
        <p style="color: #6B7280; font-size: 14px;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{verification_url}">{verification_url}</a>
        </p>
        <p style="color: #9CA3AF; font-size: 12px;">
            This link expires in 24 hours.
        </p>
    </body>
    </html>
    """

    await send_email(
        to=email,
        subject=f"Verify your email — {settings.APP_NAME}",
        html_body=html_body,
    )


# ---------------------------------------------------------------------------
# Superuser bootstrap
# ---------------------------------------------------------------------------
async def create_first_superuser(db: AsyncSession) -> None:
    """Create the initial admin account from env config (idempotent).

    Reads ``ADMIN_EMAIL`` and ``ADMIN_PASSWORD`` from settings.
    Does nothing if the admin already exists.
    """
    admin_email: str | None = getattr(settings, "ADMIN_EMAIL", None)
    admin_password: str | None = getattr(settings, "ADMIN_PASSWORD", None)

    if not admin_email or not admin_password:
        logger.info("ADMIN_EMAIL / ADMIN_PASSWORD not set — skipping superuser bootstrap.")
        return

    user_repo = UserRepository(db)
    existing = await user_repo.get(email=admin_email.lower())
    if existing is not None:
        logger.info("Superuser %s already exists — skipping.", admin_email)
        return

    await user_repo.create_user(
        email=admin_email,
        hashed_password=hash_password(admin_password),
        is_active=True,
        is_verified=True,
        is_superuser=True,
    )
    logger.info("Created superuser: %s", admin_email)
