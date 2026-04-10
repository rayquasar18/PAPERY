"""Authentication service — business logic for auth flows.

Orchestrates registration, login, logout, token rotation, email verification,
and superuser bootstrap. Delegates security primitives (password hashing,
JWT lifecycle, token blacklist) to ``app.core.security``.

Data access is handled by ``app.repositories.UserRepository`` — this service
contains only business logic, validation, and orchestration.

Usage:
    service = AuthService(db)
    user = await service.register_user(email, password)
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
    create_password_reset_token,
    create_token_pair,
    decode_token,
    hash_password,
    invalidate_all_user_sessions,
    invalidate_token_family,
    is_token_blacklisted,
    register_token_in_family,
    verify_password,
)
from app.models.user import User
from app.repositories.oauth_account_repository import OAuthAccountRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPayload
from app.schemas.oauth import OAuthUserInfo
from app.utils.email import render_email_template, send_email

logger = logging.getLogger(__name__)


class AuthService:
    """Class-based auth service — one instance per request lifecycle.

    Constructor accepts an ``AsyncSession``; all methods use the same
    ``UserRepository`` instance created at construction time.

    Example::

        service = AuthService(db)
        user = await service.register_user(email, password)
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db: AsyncSession = db
        self._user_repo: UserRepository = UserRepository(db)

    # ------------------------------------------------------------------
    # Helper methods — for router-level lookups without direct repo access
    # ------------------------------------------------------------------

    async def get_user_by_uuid(self, user_uuid: uuid_pkg.UUID) -> User | None:
        """Return a user by UUID, or None if not found."""
        return await self._user_repo.get(uuid=user_uuid)

    async def get_user_by_email(self, email: str) -> User | None:
        """Return a user by email (lowercased), or None if not found."""
        return await self._user_repo.get(email=email.lower())

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def register_user(self, email: str, password: str) -> User:
        """Create a new local user.

        Raises ``ConflictError`` if the email is already registered.
        If the existing account is OAuth-only (no password), hints the user
        to log in via their OAuth provider instead.
        """
        existing = await self._user_repo.get(email=email.lower())
        if existing is not None:
            if existing.hashed_password is None:
                raise ConflictError(
                    detail="This email is linked to a social login. "
                    "Please sign in with your OAuth provider.",
                )
            raise ConflictError(detail="Email already registered")

        return await self._user_repo.create_user(
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            is_verified=False,
            is_superuser=False,
        )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def authenticate_user(self, email: str, password: str) -> User:
        """Validate credentials, returning the user on success.

        Raises ``UnauthorizedError`` for invalid credentials or inactive accounts.
        """
        user = await self._user_repo.get(email=email.lower())
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

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    async def logout_user(
        self,
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

    # ------------------------------------------------------------------
    # Token rotation (refresh)
    # ------------------------------------------------------------------

    async def rotate_refresh_token(
        self,
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
        user = await self._user_repo.get(uuid=uuid_pkg.UUID(old_payload.sub))
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

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    async def verify_email(self, token: str) -> User:
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

        user = await self._user_repo.get(uuid=uuid_pkg.UUID(payload.sub))
        if user is None:
            raise NotFoundError(detail="User not found")

        if user.is_verified:
            raise BadRequestError(detail="Email is already verified")

        user.is_verified = True
        return await self._user_repo.update(user)

    async def send_verification_email(self, email: str, user_uuid: uuid_pkg.UUID) -> None:
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

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    async def request_password_reset(self, email: str) -> None:
        """Generate a reset token and send a password reset email.

        Anti-enumeration: does nothing (silently) if the email does not exist
        or the account is inactive. The caller always returns a success message.
        """
        user = await self._user_repo.get(email=email.lower())

        if user is None or not user.is_active:
            return  # Silent — anti-enumeration (D-04)

        if user.hashed_password is None:
            # OAuth-only user — cannot reset a password that doesn't exist
            return

        token = await create_password_reset_token(user.uuid)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        html_body = render_email_template(
            "password_reset",
            locale="en",  # TODO: use user locale preference when available
            context={"reset_url": reset_url, "app_name": settings.APP_NAME},
        )

        await send_email(
            to=user.email,
            subject=f"Reset your password — {settings.APP_NAME}",
            html_body=html_body,
        )

    async def reset_password(self, token: str, new_password: str) -> None:
        """Validate a reset token and update the user's password.

        Enforces single-use: the token's JTI is blacklisted after success.
        """
        from jose import JWTError
        from jose import jwt as jose_jwt

        try:
            raw = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            payload = TokenPayload(**raw)
        except JWTError as exc:
            raise BadRequestError(detail=f"Invalid or expired reset token: {exc}") from exc

        if payload.purpose != "password_reset":
            raise BadRequestError(detail="Token is not a password reset token")

        # Single-use check
        if await is_token_blacklisted(payload.jti):
            raise BadRequestError(detail="This reset link has already been used")

        user = await self._user_repo.get(uuid=uuid_pkg.UUID(payload.sub))
        if user is None:
            raise NotFoundError(detail="User not found")

        if not user.is_active:
            raise BadRequestError(detail="Account is deactivated")

        # Update password
        user.hashed_password = hash_password(new_password)
        await self._user_repo.update(user)

        # Blacklist the reset token JTI (single-use enforcement)
        remaining = payload.exp - int(datetime.now(UTC).timestamp())
        if remaining > 0:
            await blacklist_token(payload.jti, remaining)

        logger.info("Password reset completed for user=%s", payload.sub)

    # ------------------------------------------------------------------
    # Superuser bootstrap
    # ------------------------------------------------------------------

    async def create_first_superuser(self) -> None:
        """Create the initial admin account from env config (idempotent).

        Reads ``ADMIN_EMAIL`` and ``ADMIN_PASSWORD`` from settings.
        Does nothing if the admin already exists.
        """
        admin_email: str | None = getattr(settings, "ADMIN_EMAIL", None)
        admin_password: str | None = getattr(settings, "ADMIN_PASSWORD", None)

        if not admin_email or not admin_password:
            logger.info("ADMIN_EMAIL / ADMIN_PASSWORD not set — skipping superuser bootstrap.")
            return

        existing = await self._user_repo.get(email=admin_email.lower())
        if existing is not None:
            logger.info("Superuser %s already exists — skipping.", admin_email)
            return

        await self._user_repo.create_user(
            email=admin_email,
            hashed_password=hash_password(admin_password),
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )
        logger.info("Created superuser: %s", admin_email)


# ---------------------------------------------------------------------------
# OAuth login / registration (module-level — not class-bound)
# ---------------------------------------------------------------------------

async def oauth_login_or_register(
    db: AsyncSession,
    user_info: OAuthUserInfo,
) -> User:
    """Find or create a user from OAuth provider info.

    Logic (D-14, D-15):
    1. If OAuthAccount exists for this provider+provider_user_id → return existing user (login)
    2. If a User with the same email exists → auto-link OAuth account (D-14)
       - But reject if user already has a DIFFERENT OAuth provider linked (D-15)
    3. Otherwise → create new User + OAuthAccount (registration)

    OAuth users are auto-verified (is_verified=True) because the provider
    guarantees email ownership.
    """
    oauth_repo = OAuthAccountRepository(db)
    user_repo = UserRepository(db)

    # 1. Check for existing OAuth account (returning user)
    existing_oauth = await oauth_repo.get(
        provider=user_info.provider,
        provider_user_id=user_info.provider_user_id,
    )
    if existing_oauth is not None:
        user = await user_repo.get(id=existing_oauth.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError(detail="Account not found or deactivated")
        return user

    # 2. Check for existing user by email (auto-link per D-14)
    existing_user = await user_repo.get(email=user_info.email.lower())
    if existing_user is not None:
        if not existing_user.is_active:
            raise UnauthorizedError(detail="Account is deactivated")

        # D-15: Single OAuth provider per user
        existing_oauth_for_user = await oauth_repo.get(user_id=existing_user.id)
        if existing_oauth_for_user is not None:
            raise ConflictError(
                detail="This account is already linked to another OAuth provider. "
                "Please sign in with your existing provider or use email/password.",
            )

        # Link new OAuth provider to existing user
        await oauth_repo.create_oauth_account(
            user_id=existing_user.id,
            provider=user_info.provider,
            provider_user_id=user_info.provider_user_id,
            provider_email=user_info.email,
        )

        # Auto-verify if not already (email confirmed by OAuth provider)
        if not existing_user.is_verified:
            existing_user.is_verified = True
            await user_repo.update(existing_user)

        logger.info(
            "Linked %s OAuth to existing user=%s",
            user_info.provider,
            existing_user.uuid,
        )
        return existing_user

    # 3. Create new user + OAuth account
    new_user = await user_repo.create_user(
        email=user_info.email.lower(),
        hashed_password=None,  # OAuth-only — no password
        is_active=True,
        is_verified=True,  # Provider guarantees email ownership
        is_superuser=False,
    )

    # Set display name from provider if available
    if user_info.name and not new_user.display_name:
        new_user.display_name = user_info.name
        await user_repo.update(new_user)

    await oauth_repo.create_oauth_account(
        user_id=new_user.id,
        provider=user_info.provider,
        provider_user_id=user_info.provider_user_id,
        provider_email=user_info.email,
    )

    logger.info(
        "Created new user via %s OAuth: user=%s email=%s",
        user_info.provider,
        new_user.uuid,
        new_user.email,
    )
    return new_user


# ---------------------------------------------------------------------------
# Change password (authenticated user with existing password)
# ---------------------------------------------------------------------------
async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """Change password for a user who has an existing password.

    Validates the current password, updates to the new one, and
    invalidates ALL active sessions (D-17: forces re-login everywhere).

    Raises:
        BadRequestError: If the user has no password (OAuth-only).
        UnauthorizedError: If the current password is incorrect.
    """
    if user.hashed_password is None:
        raise BadRequestError(
            detail="This account uses social login and has no password set. "
            "Use the set-password endpoint instead.",
        )

    if not verify_password(current_password, user.hashed_password):
        raise UnauthorizedError(detail="Current password is incorrect")

    user_repo = UserRepository(db)
    user.hashed_password = hash_password(new_password)
    await user_repo.update(user)

    # Invalidate ALL sessions for this user (D-17)
    await invalidate_all_user_sessions(user.uuid)

    logger.info("Password changed for user=%s — all sessions invalidated", user.uuid)


# ---------------------------------------------------------------------------
# Set password (OAuth-only users — no current password)
# ---------------------------------------------------------------------------
async def set_password(
    db: AsyncSession,
    user: User,
    new_password: str,
) -> None:
    """Set a password for an OAuth-only user (no existing password).

    Only allowed when user.hashed_password is NULL. Does NOT invalidate
    existing sessions (user has no password-based sessions to protect).

    Raises:
        BadRequestError: If the user already has a password set.
    """
    if user.hashed_password is not None:
        raise BadRequestError(
            detail="Account already has a password. "
            "Use the change-password endpoint instead.",
        )

    user_repo = UserRepository(db)
    user.hashed_password = hash_password(new_password)
    await user_repo.update(user)

    logger.info("Password set for OAuth-only user=%s", user.uuid)


# ---------------------------------------------------------------------------
# Backward-compatible module-level wrapper (for scripts/create_first_superuser.py)
# ---------------------------------------------------------------------------

async def create_first_superuser(db: AsyncSession) -> None:
    """Module-level wrapper for backward compatibility with bootstrap scripts.

    Delegates to ``AuthService(db).create_first_superuser()``.
    """
    await AuthService(db).create_first_superuser()
