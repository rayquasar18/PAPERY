"""Authentication service — all auth business logic in one place.

Covers password hashing, JWT lifecycle, Redis token blacklist,
refresh-token rotation with replay detection, user CRUD helpers,
email verification, and superuser bootstrap.
"""

from __future__ import annotations

import logging
import uuid as uuid_pkg
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs import settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from app.infra.redis.client import cache_client
from app.models.user import User
from app.schemas.auth import TokenPayload
from app.utils.email import send_email

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify *plain* against a bcrypt *hashed* value."""
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT creation / decoding
# ---------------------------------------------------------------------------
def create_access_token(user_uuid: uuid_pkg.UUID) -> str:
    """Create a short-lived access JWT."""
    now = datetime.now(UTC)
    jti = str(uuid_pkg.uuid4())
    payload = {
        "sub": str(user_uuid),
        "jti": jti,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    user_uuid: uuid_pkg.UUID,
    family_id: str | None = None,
) -> str:
    """Create a long-lived refresh JWT bound to a token family."""
    now = datetime.now(UTC)
    jti = str(uuid_pkg.uuid4())
    family = family_id or str(uuid_pkg.uuid4())
    payload = {
        "sub": str(user_uuid),
        "jti": jti,
        "type": "refresh",
        "family": family,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_token_pair(
    user_uuid: uuid_pkg.UUID,
    family_id: str | None = None,
) -> tuple[str, str]:
    """Return ``(access_token, refresh_token)``."""
    family = family_id or str(uuid_pkg.uuid4())
    access = create_access_token(user_uuid)
    refresh = create_refresh_token(user_uuid, family_id=family)
    return access, refresh


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT, returning a typed payload.

    Raises ``UnauthorizedError`` on any failure (expired, tampered, etc.).
    """
    try:
        raw = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return TokenPayload(**raw)
    except JWTError as exc:
        raise UnauthorizedError(detail=f"Invalid token: {exc}") from exc


# ---------------------------------------------------------------------------
# Redis key prefixes
# ---------------------------------------------------------------------------
BLACKLIST_PREFIX = "blacklist:jti:"
FAMILY_PREFIX = "token_family:"


def _redis() -> object:
    """Return the cache Redis client, raising if unavailable."""
    if cache_client is None:
        raise RuntimeError("Redis cache client not initialized")
    return cache_client


# ---------------------------------------------------------------------------
# Token blacklist (Redis)
# ---------------------------------------------------------------------------
async def blacklist_token(jti: str, expire_seconds: int) -> None:
    """Add *jti* to the blacklist with a TTL matching token expiry."""
    client = _redis()
    await client.setex(f"{BLACKLIST_PREFIX}{jti}", expire_seconds, "1")  # type: ignore[union-attr]


async def is_token_blacklisted(jti: str) -> bool:
    """Return True if *jti* has been revoked."""
    client = _redis()
    return await client.exists(f"{BLACKLIST_PREFIX}{jti}") > 0  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Token family tracking (refresh-token replay detection)
# ---------------------------------------------------------------------------
async def register_token_in_family(family_id: str, jti: str) -> None:
    """Record *jti* as the latest valid token in *family_id*."""
    client = _redis()
    key = f"{FAMILY_PREFIX}{family_id}"
    await client.sadd(key, jti)  # type: ignore[union-attr]
    # Family TTL matches refresh token lifetime (with small buffer)
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400 + 3600
    await client.expire(key, ttl)  # type: ignore[union-attr]


async def invalidate_token_family(family_id: str) -> None:
    """Destroy an entire token family — used on replay detection or logout."""
    client = _redis()
    key = f"{FAMILY_PREFIX}{family_id}"
    members = await client.smembers(key)  # type: ignore[union-attr]
    if members:
        pipe = client.pipeline()  # type: ignore[union-attr]
        for jti in members:
            pipe.setex(
                f"{BLACKLIST_PREFIX}{jti}",
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400 + 3600,
                "1",
            )
        pipe.delete(key)
        await pipe.execute()
    else:
        await client.delete(key)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch a non-deleted user by email (case-insensitive)."""
    stmt = select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_uuid(db: AsyncSession, user_uuid: uuid_pkg.UUID) -> User | None:
    """Fetch a non-deleted user by public UUID."""
    stmt = select(User).where(User.uuid == user_uuid, User.deleted_at.is_(None))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    """Create a new local user. Raises ``ConflictError`` if email is taken."""
    existing = await get_user_by_email(db, email)
    if existing is not None:
        raise ConflictError(detail="Email already registered")

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        is_verified=False,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Verify credentials and return the user.

    Uses ``pwd_context.dummy_verify()`` on user-not-found to mitigate
    timing side-channel attacks.
    """
    user = await get_user_by_email(db, email)
    if user is None:
        pwd_context.dummy_verify()
        raise UnauthorizedError(detail="Invalid email or password")

    if user.hashed_password is None:
        # OAuth-only account — no local password set
        raise UnauthorizedError(detail="This account uses social login. Please sign in with your OAuth provider.")

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
    user = await get_user_by_uuid(db, uuid_pkg.UUID(old_payload.sub))
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
def create_email_verification_token(user_uuid: uuid_pkg.UUID) -> str:
    """Create a short-lived JWT for email verification."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_uuid),
        "jti": str(uuid_pkg.uuid4()),
        "type": "verification",
        "purpose": "email_verify",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=24)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def verify_email(db: AsyncSession, token: str) -> User:
    """Decode a verification token and mark the user as verified.

    Raises appropriate errors for invalid/expired tokens or missing users.
    """
    try:
        raw = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        payload = TokenPayload(**raw)
    except JWTError as exc:
        raise BadRequestError(detail=f"Invalid or expired verification token: {exc}") from exc

    if payload.purpose != "email_verify":
        raise BadRequestError(detail="Token is not an email verification token")

    user = await get_user_by_uuid(db, uuid_pkg.UUID(payload.sub))
    if user is None:
        raise NotFoundError(detail="User not found")

    if user.is_verified:
        raise BadRequestError(detail="Email is already verified")

    user.is_verified = True
    await db.commit()
    await db.refresh(user)
    return user


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
            This link expires in 24 hours. If you didn't create an account, you can ignore this email.
        </p>
    </body>
    </html>
    """

    await send_email(
        to=email,
        subject=f"Verify your {settings.APP_NAME} email",
        html_body=html_body,
    )


# ---------------------------------------------------------------------------
# Superuser bootstrap
# ---------------------------------------------------------------------------
async def create_first_superuser(db: AsyncSession) -> None:
    """Create the initial superuser from env config if not already present.

    Called once during application startup. Silently returns if the admin
    account already exists.
    """
    existing = await get_user_by_email(db, settings.ADMIN_EMAIL)
    if existing is not None:
        logger.debug("Superuser already exists: %s", settings.ADMIN_EMAIL)
        return

    user = User(
        email=settings.ADMIN_EMAIL.lower(),
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        is_verified=True,
        is_superuser=True,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    logger.info("Superuser created: %s", settings.ADMIN_EMAIL)
