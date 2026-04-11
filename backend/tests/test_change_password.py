"""Tests for change-password and set-password flows (USER-03)."""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_oauth_user():
    """Mock OAuth-only user with no hashed_password."""
    user = MagicMock()
    user.id = 2
    user.uuid = uuid_pkg.uuid4()
    user.email = "oauthonly@example.com"
    user.hashed_password = None  # OAuth-only
    user.display_name = "OAuth User"
    user.avatar_url = None
    user.is_active = True
    user.is_verified = True
    user.is_superuser = False
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = None
    # Tier relationship (added in phase 6)
    mock_tier = MagicMock()
    mock_tier.name = "Free"
    mock_tier.slug = "free"
    user.tier = mock_tier
    user.tier_id = 1
    user.stripe_customer_id = None
    return user


# ---------------------------------------------------------------------------
# TestChangePassword — route-level tests
# ---------------------------------------------------------------------------

class TestChangePassword:
    """POST /api/v1/auth/change-password tests."""

    async def test_change_password_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "any",
                "new_password": "NewSecureP@ss456",
            },
        )
        assert response.status_code == 401

    async def test_change_password_same_as_current_returns_422(
        self, async_client: AsyncClient, mock_user
    ):
        """New password same as current returns 422 (Pydantic model_validator)."""
        # Provide a valid access token cookie to pass auth
        fake_token = "fake-access-token"
        with (
            patch("app.api.dependencies.decode_token") as mock_decode,
            patch("app.api.dependencies.is_token_blacklisted", return_value=False),
            patch(
                "app.repositories.user_repository.UserRepository.get",
                return_value=mock_user,
            ),
        ):
            from app.schemas.auth import TokenPayload

            mock_decode.return_value = TokenPayload(
                sub=str(mock_user.uuid),
                jti="test-jti",
                type="access",
                exp=9999999999,
                iat=1000000000,
            )
            response = await async_client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "TestPassword123",
                    "new_password": "TestPassword123",
                },
                cookies={"access_token": fake_token},
            )
        assert response.status_code == 422

    async def test_change_password_with_valid_current(
        self, async_client: AsyncClient, mock_user
    ):
        """Valid current password + new password returns 200 success."""
        fake_token = "fake-access-token"
        with (
            patch("app.api.dependencies.decode_token") as mock_decode,
            patch("app.api.dependencies.is_token_blacklisted", return_value=False),
            patch(
                "app.repositories.user_repository.UserRepository.get",
                return_value=mock_user,
            ),
            patch(
                "app.services.auth_service.AuthService.change_password",
                new_callable=AsyncMock,
            ) as mock_change,
            patch(
                "app.utils.rate_limit.check_rate_limit",
                new_callable=AsyncMock,
            ),
        ):
            from app.schemas.auth import TokenPayload

            mock_decode.return_value = TokenPayload(
                sub=str(mock_user.uuid),
                jti="test-jti",
                type="access",
                exp=9999999999,
                iat=1000000000,
            )
            response = await async_client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "TestPassword123",
                    "new_password": "NewSecureP@ss456",
                },
                cookies={"access_token": fake_token},
            )

        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]
        mock_change.assert_called_once()

    async def test_change_password_wrong_current(
        self, async_client: AsyncClient, mock_user
    ):
        """Wrong current password — service raises UnauthorizedError → 401."""
        from app.core.exceptions import UnauthorizedError

        fake_token = "fake-access-token"
        with (
            patch("app.api.dependencies.decode_token") as mock_decode,
            patch("app.api.dependencies.is_token_blacklisted", return_value=False),
            patch(
                "app.repositories.user_repository.UserRepository.get",
                return_value=mock_user,
            ),
            patch(
                "app.services.auth_service.AuthService.change_password",
                new_callable=AsyncMock,
                side_effect=UnauthorizedError(detail="Current password is incorrect"),
            ),
            patch(
                "app.utils.rate_limit.check_rate_limit",
                new_callable=AsyncMock,
            ),
        ):
            from app.schemas.auth import TokenPayload

            mock_decode.return_value = TokenPayload(
                sub=str(mock_user.uuid),
                jti="test-jti",
                type="access",
                exp=9999999999,
                iat=1000000000,
            )
            response = await async_client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "WrongPassword999",
                    "new_password": "NewSecureP@ss456",
                },
                cookies={"access_token": fake_token},
            )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    async def test_change_password_invalidates_sessions(
        self, async_client: AsyncClient, mock_user
    ):
        """change_password service call triggers invalidate_all_user_sessions."""
        from app.core.security import hash_password

        # Service-level: verify the function calls invalidate_all_user_sessions
        real_user = MagicMock()
        real_user.uuid = uuid_pkg.uuid4()
        real_user.hashed_password = hash_password("OldPassword123")

        with (
            patch(
                "app.services.auth_service.invalidate_all_user_sessions",
                new_callable=AsyncMock,
            ) as mock_invalidate,
            patch(
                "app.repositories.user_repository.UserRepository.update",
                new_callable=AsyncMock,
                return_value=real_user,
            ),
        ):
            from app.services.auth_service import change_password

            mock_db = AsyncMock()
            await change_password(mock_db, real_user, "OldPassword123", "NewPass@word456")

        mock_invalidate.assert_called_once_with(real_user.uuid)

    async def test_change_password_oauth_only_user_rejected(self, mock_oauth_user):
        """OAuth-only user (no password) gets BadRequestError on change_password."""
        from app.core.exceptions import BadRequestError
        from app.services.auth_service import change_password

        mock_db = AsyncMock()

        with pytest.raises(BadRequestError, match="social login"):
            await change_password(mock_db, mock_oauth_user, "anything", "NewSecureP@ss456")


# ---------------------------------------------------------------------------
# TestSetPassword — service-level and route-level tests
# ---------------------------------------------------------------------------

class TestSetPassword:
    """POST /api/v1/auth/set-password tests."""

    async def test_set_password_requires_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.post(
            "/api/v1/auth/set-password",
            json={"new_password": "NewSecureP@ss456"},
        )
        assert response.status_code == 401

    async def test_set_password_oauth_user_success(self, mock_oauth_user):
        """OAuth-only user can set a password via service function."""
        from app.services.auth_service import set_password

        mock_db = AsyncMock()

        with patch(
            "app.repositories.user_repository.UserRepository.update",
            new_callable=AsyncMock,
            return_value=mock_oauth_user,
        ):
            await set_password(mock_db, mock_oauth_user, "MyNewP@ssw0rd")

        # hashed_password should now be set (not None)
        assert mock_oauth_user.hashed_password is not None

    async def test_set_password_existing_password_rejected(self, mock_user):
        """User with existing password gets BadRequestError on set_password."""
        from app.core.exceptions import BadRequestError
        from app.services.auth_service import set_password

        mock_db = AsyncMock()

        with pytest.raises(BadRequestError, match="already has a password"):
            await set_password(mock_db, mock_user, "NewP@ssw0rd")

    async def test_set_password_route_success(
        self, async_client: AsyncClient, mock_oauth_user
    ):
        """OAuth user hitting set-password endpoint gets 200 success."""
        fake_token = "fake-access-token"
        with (
            patch("app.api.dependencies.decode_token") as mock_decode,
            patch("app.api.dependencies.is_token_blacklisted", return_value=False),
            patch(
                "app.repositories.user_repository.UserRepository.get",
                return_value=mock_oauth_user,
            ),
            patch(
                "app.services.auth_service.AuthService.set_password",
                new_callable=AsyncMock,
            ) as mock_set,
            patch(
                "app.utils.rate_limit.check_rate_limit",
                new_callable=AsyncMock,
            ),
        ):
            from app.schemas.auth import TokenPayload

            mock_decode.return_value = TokenPayload(
                sub=str(mock_oauth_user.uuid),
                jti="test-jti-oauth",
                type="access",
                exp=9999999999,
                iat=1000000000,
            )
            response = await async_client.post(
                "/api/v1/auth/set-password",
                json={"new_password": "NewSecureP@ss456"},
                cookies={"access_token": fake_token},
            )

        assert response.status_code == 200
        assert "Password set successfully" in response.json()["message"]
        mock_set.assert_called_once()
