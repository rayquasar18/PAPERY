"""Tests for the password reset flow (AUTH-06).

All service layer and infrastructure dependencies are mocked —
no real database, Redis, or SMTP needed.
"""

import uuid as uuid_pkg
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.exceptions import BadRequestError


def _make_mock_user(
    *,
    email: str = "test@example.com",
    is_active: bool = True,
    hashed_password: str | None = "$2b$12$mock_hash",
) -> MagicMock:
    """Create a mock User with all required attributes."""
    user = MagicMock()
    user.id = 1
    user.uuid = uuid_pkg.uuid4()
    user.email = email
    user.hashed_password = hashed_password
    user.display_name = "Test User"
    user.avatar_url = None
    user.is_active = is_active
    user.is_verified = True
    user.is_superuser = False
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = None
    return user


# ---------------------------------------------------------------------------
# POST /api/v1/auth/forgot-password
# ---------------------------------------------------------------------------
class TestForgotPassword:
    """POST /api/v1/auth/forgot-password tests."""

    async def test_forgot_password_existing_email_returns_success(
        self, async_client: AsyncClient
    ):
        """Request reset for existing email returns success message."""
        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch(
                "app.api.v1.auth.auth_service.request_password_reset",
                new_callable=AsyncMock,
            ),
        ):
            response = await async_client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "test@example.com"},
            )
        assert response.status_code == 200
        assert "If an account with that email exists" in response.json()["message"]

    async def test_forgot_password_nonexistent_email_returns_same_success(
        self, async_client: AsyncClient
    ):
        """Anti-enumeration: non-existent email returns same message."""
        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch(
                "app.api.v1.auth.auth_service.request_password_reset",
                new_callable=AsyncMock,
            ),
        ):
            response = await async_client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "noone@example.com"},
            )
        assert response.status_code == 200
        assert "If an account with that email exists" in response.json()["message"]

    async def test_forgot_password_service_exception_still_returns_success(
        self, async_client: AsyncClient
    ):
        """Service exceptions are swallowed — anti-enumeration still holds."""
        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch(
                "app.api.v1.auth.auth_service.request_password_reset",
                new_callable=AsyncMock,
                side_effect=Exception("SMTP failure"),
            ),
        ):
            response = await async_client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "test@example.com"},
            )
        assert response.status_code == 200
        assert "If an account with that email exists" in response.json()["message"]

    async def test_forgot_password_rate_limited(self, async_client: AsyncClient):
        """Rate limit enforced after 3 requests."""
        from app.core.exceptions import RateLimitedError

        call_count = 0

        async def _rate_limit_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 3:
                raise RateLimitedError(detail="Rate limit exceeded")

        with (
            patch("app.api.v1.auth.check_rate_limit", side_effect=_rate_limit_side_effect),
            patch(
                "app.api.v1.auth.auth_service.request_password_reset",
                new_callable=AsyncMock,
            ),
        ):
            for _ in range(3):
                r = await async_client.post(
                    "/api/v1/auth/forgot-password",
                    json={"email": "test@example.com"},
                )
                assert r.status_code == 200

            response = await async_client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "test@example.com"},
            )
        assert response.status_code == 429


# ---------------------------------------------------------------------------
# POST /api/v1/auth/reset-password
# ---------------------------------------------------------------------------
class TestResetPassword:
    """POST /api/v1/auth/reset-password tests."""

    async def test_reset_with_valid_token(self, async_client: AsyncClient):
        """Valid reset token updates password successfully."""
        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch(
                "app.api.v1.auth.auth_service.reset_password",
                new_callable=AsyncMock,
            ),
        ):
            response = await async_client.post(
                "/api/v1/auth/reset-password",
                json={"token": "valid.jwt.token", "new_password": "NewSecureP@ss1"},
            )
        assert response.status_code == 200
        assert "reset successfully" in response.json()["message"]

    async def test_reset_with_used_token_fails(self, async_client: AsyncClient):
        """Using an already-used reset token returns 400."""
        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch(
                "app.api.v1.auth.auth_service.reset_password",
                new_callable=AsyncMock,
                side_effect=BadRequestError(detail="This reset link has already been used"),
            ),
        ):
            response = await async_client.post(
                "/api/v1/auth/reset-password",
                json={"token": "used.jwt.token", "new_password": "AnotherP@ss2"},
            )
        assert response.status_code == 400
        assert "already been used" in response.json()["message"]

    async def test_reset_with_invalid_token_fails(self, async_client: AsyncClient):
        """Invalid JWT token returns 400."""
        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch(
                "app.api.v1.auth.auth_service.reset_password",
                new_callable=AsyncMock,
                side_effect=BadRequestError(detail="Invalid or expired reset token"),
            ),
        ):
            response = await async_client.post(
                "/api/v1/auth/reset-password",
                json={"token": "not-a-valid-jwt", "new_password": "NewSecureP@ss1"},
            )
        assert response.status_code == 400

    async def test_reset_password_too_short(self, async_client: AsyncClient):
        """Password under 8 chars returns 422 validation error."""
        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
        ):
            response = await async_client.post(
                "/api/v1/auth/reset-password",
                json={"token": "some.jwt.token", "new_password": "short"},
            )
        assert response.status_code == 422

    async def test_reset_password_rate_limited(self, async_client: AsyncClient):
        """Rate limit enforced after 5 requests per IP."""
        from app.core.exceptions import RateLimitedError

        call_count = 0

        async def _rate_limit_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 5:
                raise RateLimitedError(detail="Rate limit exceeded")

        with (
            patch("app.api.v1.auth.check_rate_limit", side_effect=_rate_limit_side_effect),
            patch(
                "app.api.v1.auth.auth_service.reset_password",
                new_callable=AsyncMock,
            ),
        ):
            for _ in range(5):
                r = await async_client.post(
                    "/api/v1/auth/reset-password",
                    json={"token": "valid.jwt.token", "new_password": "NewSecureP@ss1"},
                )
                assert r.status_code == 200

            response = await async_client.post(
                "/api/v1/auth/reset-password",
                json={"token": "valid.jwt.token", "new_password": "NewSecureP@ss1"},
            )
        assert response.status_code == 429


# ---------------------------------------------------------------------------
# Unit tests for service layer — create_password_reset_token
# ---------------------------------------------------------------------------
class TestCreatePasswordResetToken:
    """Unit tests for create_password_reset_token in security.py."""

    async def test_token_contains_password_reset_purpose(self):
        """Generated token has purpose=password_reset and type=password_reset."""
        import fakeredis.aioredis

        from app.core import security as sec

        fake_redis = fakeredis.aioredis.FakeRedis()
        with patch.object(sec, "cache_client", fake_redis):
            token = await sec.create_password_reset_token(uuid_pkg.uuid4())

        from jose import jwt as jose_jwt

        import os
        secret = os.environ.get("SECRET_KEY", "test-secret-key-minimum-32-characters-long!!")
        raw = jose_jwt.decode(token, secret, algorithms=["HS256"])
        assert raw["purpose"] == "password_reset"
        assert raw["type"] == "password_reset"

    async def test_previous_token_blacklisted_on_new_request(self):
        """Re-requesting a reset blacklists the previous token's JTI."""
        import fakeredis.aioredis

        from app.core import security as sec

        fake_redis = fakeredis.aioredis.FakeRedis()
        user_uuid = uuid_pkg.uuid4()

        with patch.object(sec, "cache_client", fake_redis):
            first_token = await sec.create_password_reset_token(user_uuid)

        import os
        from jose import jwt as jose_jwt

        secret = os.environ.get("SECRET_KEY", "test-secret-key-minimum-32-characters-long!!")
        first_jti = jose_jwt.decode(first_token, secret, algorithms=["HS256"])["jti"]

        with patch.object(sec, "cache_client", fake_redis):
            # Second request should blacklist first JTI
            await sec.create_password_reset_token(user_uuid)
            is_blacklisted = await sec.is_token_blacklisted(first_jti)

        assert is_blacklisted is True
