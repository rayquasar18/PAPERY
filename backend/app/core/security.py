"""Security primitives — password hashing, JWT lifecycle, Redis token blacklist.

This module contains stateless (or Redis-only) security building blocks.
Business logic that depends on the database lives in ``app.services.auth_service``.
"""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.configs import settings
from app.core.exceptions import UnauthorizedError
from app.infra.redis.client import cache_client
from app.schemas.auth import TokenPayload

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
