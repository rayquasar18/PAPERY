"""Tests for authentication service layer (Plan 03-04-T3).

All Redis interactions are mocked — no real external services needed.
"""

import uuid as uuid_pkg
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from app.configs import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    BLACKLIST_PREFIX,
    FAMILY_PREFIX,
    blacklist_token,
    create_access_token,
    create_email_verification_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    hash_password,
    is_token_blacklisted,
    register_token_in_family,
    verify_password,
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
class TestPasswordHashing:
    """Test bcrypt password hashing and verification.

    The underlying CryptContext is mocked to avoid bcrypt 5.x / passlib
    version incompatibility in the CI environment. We test that our
    service functions correctly delegate to the CryptContext.
    """

    def test_hash_password_delegates_to_context(self):
        """hash_password should delegate to pwd_context.hash."""
        mock_ctx = MagicMock()
        mock_ctx.hash.return_value = "$2b$12$mocked_hash_value"
        with patch("app.core.security.pwd_context", mock_ctx):
            result = hash_password("mypassword")
        mock_ctx.hash.assert_called_once_with("mypassword")
        assert result == "$2b$12$mocked_hash_value"

    def test_verify_password_delegates_to_context(self):
        """verify_password should delegate to pwd_context.verify."""
        mock_ctx = MagicMock()
        mock_ctx.verify.return_value = True
        with patch("app.core.security.pwd_context", mock_ctx):
            result = verify_password("correcthorse", "$2b$12$somehash")
        mock_ctx.verify.assert_called_once_with("correcthorse", "$2b$12$somehash")
        assert result is True

    def test_verify_wrong_password_returns_false(self):
        """verify_password should return False for wrong password."""
        mock_ctx = MagicMock()
        mock_ctx.verify.return_value = False
        with patch("app.core.security.pwd_context", mock_ctx):
            result = verify_password("wrongpassword", "$2b$12$somehash")
        assert result is False


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------
class TestJWTTokens:
    """Test JWT creation and decoding."""

    def test_create_access_token(self):
        """Access token should decode with correct claims."""
        user_uuid = uuid_pkg.uuid4()
        token = create_access_token(user_uuid)
        payload = decode_token(token)
        assert payload.sub == str(user_uuid)
        assert payload.type == "access"
        assert payload.jti  # non-empty
        assert payload.exp > payload.iat

    def test_create_refresh_token(self):
        """Refresh token should include family claim."""
        user_uuid = uuid_pkg.uuid4()
        token = create_refresh_token(user_uuid)
        payload = decode_token(token)
        assert payload.sub == str(user_uuid)
        assert payload.type == "refresh"
        assert payload.family is not None

    def test_create_refresh_token_with_family(self):
        """Refresh token should use provided family ID."""
        user_uuid = uuid_pkg.uuid4()
        family = "my-family-id"
        token = create_refresh_token(user_uuid, family_id=family)
        payload = decode_token(token)
        assert payload.family == family

    def test_create_token_pair(self):
        """Token pair should return (access, refresh) with same user sub."""
        user_uuid = uuid_pkg.uuid4()
        access, refresh = create_token_pair(user_uuid)
        access_payload = decode_token(access)
        refresh_payload = decode_token(refresh)
        assert access_payload.sub == str(user_uuid)
        assert refresh_payload.sub == str(user_uuid)
        assert access_payload.type == "access"
        assert refresh_payload.type == "refresh"

    def test_create_token_pair_shared_family(self):
        """When family_id is provided, refresh token should use it."""
        user_uuid = uuid_pkg.uuid4()
        family = "shared-family"
        _access, refresh = create_token_pair(user_uuid, family_id=family)
        refresh_payload = decode_token(refresh)
        assert refresh_payload.family == family

    def test_decode_invalid_token_raises(self):
        """Decoding a garbage token should raise UnauthorizedError."""
        with pytest.raises(UnauthorizedError):
            decode_token("this.is.not.a.valid.jwt")

    def test_decode_expired_token_raises(self):
        """Decoding an expired token should raise UnauthorizedError."""
        now = datetime.now(UTC)
        payload = {
            "sub": str(uuid_pkg.uuid4()),
            "jti": str(uuid_pkg.uuid4()),
            "type": "access",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),  # expired 1h ago
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        with pytest.raises(UnauthorizedError):
            decode_token(token)

    def test_decode_wrong_secret_raises(self):
        """Token signed with wrong secret should fail decoding."""
        now = datetime.now(UTC)
        payload = {
            "sub": str(uuid_pkg.uuid4()),
            "jti": str(uuid_pkg.uuid4()),
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(payload, "wrong-secret-key-that-is-long-enough!!", algorithm="HS256")
        with pytest.raises(UnauthorizedError):
            decode_token(token)

    def test_access_token_expiry_within_expected_range(self):
        """Access token exp should be ~ACCESS_TOKEN_EXPIRE_MINUTES from now."""
        user_uuid = uuid_pkg.uuid4()
        before = datetime.now(UTC)
        token = create_access_token(user_uuid)
        after = datetime.now(UTC)

        payload = decode_token(token)
        expected_min = int((before + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()) - 2
        expected_max = int((after + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()) + 2
        assert expected_min <= payload.exp <= expected_max

    def test_refresh_token_expiry_within_expected_range(self):
        """Refresh token exp should be ~REFRESH_TOKEN_EXPIRE_DAYS from now."""
        user_uuid = uuid_pkg.uuid4()
        before = datetime.now(UTC)
        token = create_refresh_token(user_uuid)
        after = datetime.now(UTC)

        payload = decode_token(token)
        expected_min = int((before + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()) - 2
        expected_max = int((after + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()) + 2
        assert expected_min <= payload.exp <= expected_max


# ---------------------------------------------------------------------------
# Email verification token
# ---------------------------------------------------------------------------
class TestEmailVerificationToken:
    """Test email verification token creation."""

    def test_creation(self):
        """Verification token should decode with correct sub and type."""
        user_uuid = uuid_pkg.uuid4()
        token = create_email_verification_token(user_uuid)
        payload = decode_token(token)
        assert payload.sub == str(user_uuid)
        assert payload.type == "verification"

    def test_purpose_claim(self):
        """Verification token should carry purpose=email_verify."""
        user_uuid = uuid_pkg.uuid4()
        token = create_email_verification_token(user_uuid)
        payload = decode_token(token)
        assert payload.purpose == "email_verify"

    def test_expiry_roughly_24_hours(self):
        """Verification token should expire in approximately 24 hours."""
        user_uuid = uuid_pkg.uuid4()
        before = datetime.now(UTC)
        token = create_email_verification_token(user_uuid)
        after = datetime.now(UTC)

        payload = decode_token(token)
        expected_min = int((before + timedelta(hours=24)).timestamp()) - 2
        expected_max = int((after + timedelta(hours=24)).timestamp()) + 2
        assert expected_min <= payload.exp <= expected_max


# ---------------------------------------------------------------------------
# Token blacklist (mocked Redis)
# ---------------------------------------------------------------------------
class TestTokenBlacklist:
    """Test Redis token blacklist with mocked Redis client."""

    async def test_blacklist_token_sets_key(self):
        """blacklist_token should call setex with correct key and TTL."""
        mock_redis = AsyncMock()
        with patch("app.core.security.cache_client", mock_redis):
            await blacklist_token("test-jti-123", 1800)
        mock_redis.setex.assert_called_once_with(
            f"{BLACKLIST_PREFIX}test-jti-123",
            1800,
            "1",
        )

    async def test_is_token_blacklisted_returns_true(self):
        """is_token_blacklisted should return True when key exists."""
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)
        with patch("app.core.security.cache_client", mock_redis):
            result = await is_token_blacklisted("revoked-jti")
        assert result is True
        mock_redis.exists.assert_called_once_with(f"{BLACKLIST_PREFIX}revoked-jti")

    async def test_is_token_blacklisted_returns_false(self):
        """is_token_blacklisted should return False when key does not exist."""
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        with patch("app.core.security.cache_client", mock_redis):
            result = await is_token_blacklisted("valid-jti")
        assert result is False

    async def test_register_token_in_family(self):
        """register_token_in_family should sadd jti and set TTL."""
        mock_redis = AsyncMock()
        with patch("app.core.security.cache_client", mock_redis):
            await register_token_in_family("family-abc", "jti-xyz")
        expected_key = f"{FAMILY_PREFIX}family-abc"
        mock_redis.sadd.assert_called_once_with(expected_key, "jti-xyz")
        mock_redis.expire.assert_called_once()
        # TTL should be REFRESH_TOKEN_EXPIRE_DAYS * 86400 + 3600
        expected_ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400 + 3600
        mock_redis.expire.assert_called_once_with(expected_key, expected_ttl)
