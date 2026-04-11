"""Tests for OAuth login/register flows (AUTH-07, AUTH-08).

Route-level tests mock all infrastructure (Redis, DB, HTTP calls to providers)
so no real services are needed. Service-level tests use the mock DB session
from conftest.py.
"""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.oauth import OAuthUserInfo


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_mock_user(
    *,
    email: str = "oauthuser@example.com",
    is_verified: bool = True,
    is_active: bool = True,
    hashed_password: str | None = None,
    display_name: str | None = "OAuth User",
) -> MagicMock:
    """Create a mock User object suitable for OAuth tests."""
    user = MagicMock()
    user.id = 42
    user.uuid = uuid_pkg.uuid4()
    user.email = email
    user.hashed_password = hashed_password
    user.display_name = display_name
    user.avatar_url = None
    user.is_active = is_active
    user.is_verified = is_verified
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


def _make_token_payload(
    user_uuid: uuid_pkg.UUID,
    family: str = "test-family",
    token_type: str = "refresh",
) -> MagicMock:
    """Create a mock TokenPayload for decode_token mocking."""
    payload = MagicMock()
    payload.sub = str(user_uuid)
    payload.jti = str(uuid_pkg.uuid4())
    payload.type = token_type
    payload.family = family
    payload.exp = int(datetime.now(UTC).timestamp()) + 3600
    return payload


# ---------------------------------------------------------------------------
# TestOAuthDisabled — OAuth credentials not configured
# ---------------------------------------------------------------------------

class TestOAuthDisabled:
    """Tests when OAuth credentials are not configured."""

    async def test_google_auth_returns_404_when_not_configured(
        self, async_client: AsyncClient
    ):
        """GET /auth/google returns 404 if GOOGLE_CLIENT_ID is empty."""
        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch("app.api.v1.auth.settings") as mock_settings,
        ):
            mock_settings.GOOGLE_CLIENT_ID = ""
            mock_settings.GOOGLE_CLIENT_SECRET = ""
            response = await async_client.get(
                "/api/v1/auth/google", follow_redirects=False
            )
        assert response.status_code == 404

    async def test_github_auth_returns_404_when_not_configured(
        self, async_client: AsyncClient
    ):
        """GET /auth/github returns 404 if GITHUB_CLIENT_ID is empty."""
        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch("app.api.v1.auth.settings") as mock_settings,
        ):
            mock_settings.GITHUB_CLIENT_ID = ""
            mock_settings.GITHUB_CLIENT_SECRET = ""
            response = await async_client.get(
                "/api/v1/auth/github", follow_redirects=False
            )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestOAuthStateValidation — CSRF state parameter tests
# ---------------------------------------------------------------------------

class TestOAuthStateValidation:
    """CSRF state parameter tests."""

    async def test_google_callback_invalid_state_redirects_with_csrf_error(
        self, async_client: AsyncClient
    ):
        """Google callback with invalid/unknown state redirects to login with oauth_csrf."""
        with patch(
            "app.api.v1.auth.validate_oauth_state",
            new_callable=AsyncMock,
            return_value=False,  # State not found in Redis
        ):
            response = await async_client.get(
                "/api/v1/auth/google/callback",
                params={"code": "fake-code", "state": "invalid-state"},
                follow_redirects=False,
            )
        assert response.status_code == 302
        assert "error=oauth_csrf" in response.headers.get("location", "")

    async def test_github_callback_missing_code_redirects_with_invalid_error(
        self, async_client: AsyncClient
    ):
        """GitHub callback missing code redirects to login with oauth_invalid."""
        response = await async_client.get(
            "/api/v1/auth/github/callback",
            params={"state": "some-state"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "error=oauth_invalid" in response.headers.get("location", "")

    async def test_google_callback_missing_state_redirects_with_invalid_error(
        self, async_client: AsyncClient
    ):
        """Google callback missing state redirects to login with oauth_invalid."""
        response = await async_client.get(
            "/api/v1/auth/google/callback",
            params={"code": "some-code"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "error=oauth_invalid" in response.headers.get("location", "")

    async def test_callback_with_error_param_redirects_with_denied_error(
        self, async_client: AsyncClient
    ):
        """Callback with error=access_denied redirects to login with oauth_denied."""
        response = await async_client.get(
            "/api/v1/auth/google/callback",
            params={"error": "access_denied"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "error=oauth_denied" in response.headers.get("location", "")

    async def test_github_callback_with_error_param_redirects(
        self, async_client: AsyncClient
    ):
        """GitHub callback with error param redirects to login with oauth_denied."""
        response = await async_client.get(
            "/api/v1/auth/github/callback",
            params={"error": "access_denied"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "error=oauth_denied" in response.headers.get("location", "")


# ---------------------------------------------------------------------------
# TestOAuthCallbackSuccess — successful OAuth flow
# ---------------------------------------------------------------------------

class TestOAuthCallbackSuccess:
    """Tests for successful OAuth callback flows."""

    async def test_google_callback_success_redirects_to_dashboard(
        self, async_client: AsyncClient
    ):
        """Successful Google callback sets cookies and redirects to /dashboard."""
        mock_user = _make_mock_user()
        mock_payload = _make_token_payload(mock_user.uuid)

        with (
            patch(
                "app.api.v1.auth.validate_oauth_state",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("app.api.v1.auth._get_google_provider") as mock_provider_factory,
            patch(
                "app.api.v1.auth.auth_service.oauth_login_or_register",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "app.api.v1.auth.create_token_pair",
                return_value=("access-jwt", "refresh-jwt"),
            ),
            patch("app.api.v1.auth.decode_token", return_value=mock_payload),
            patch(
                "app.api.v1.auth.register_token_in_family", new_callable=AsyncMock
            ),
            patch("app.api.v1.auth.track_user_family", new_callable=AsyncMock),
            patch("app.api.v1.auth.settings") as mock_settings,
        ):
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            mock_settings.ENVIRONMENT = "local"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 7

            # Configure mock provider
            mock_provider = MagicMock()
            mock_provider.get_access_token = AsyncMock(return_value="provider-access-token")
            mock_provider.get_user_info = AsyncMock(
                return_value=OAuthUserInfo(
                    provider="google",
                    provider_user_id="google-123",
                    email=mock_user.email,
                    name="OAuth User",
                )
            )
            mock_provider_factory.return_value = mock_provider

            response = await async_client.get(
                "/api/v1/auth/google/callback",
                params={"code": "valid-code", "state": "valid-state"},
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "/dashboard" in response.headers.get("location", "")

    async def test_github_callback_success_redirects_to_dashboard(
        self, async_client: AsyncClient
    ):
        """Successful GitHub callback sets cookies and redirects to /dashboard."""
        mock_user = _make_mock_user(email="githubuser@example.com")
        mock_payload = _make_token_payload(mock_user.uuid)

        with (
            patch(
                "app.api.v1.auth.validate_oauth_state",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("app.api.v1.auth._get_github_provider") as mock_provider_factory,
            patch(
                "app.api.v1.auth.auth_service.oauth_login_or_register",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "app.api.v1.auth.create_token_pair",
                return_value=("access-jwt", "refresh-jwt"),
            ),
            patch("app.api.v1.auth.decode_token", return_value=mock_payload),
            patch(
                "app.api.v1.auth.register_token_in_family", new_callable=AsyncMock
            ),
            patch("app.api.v1.auth.track_user_family", new_callable=AsyncMock),
            patch("app.api.v1.auth.settings") as mock_settings,
        ):
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            mock_settings.ENVIRONMENT = "local"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 7

            mock_provider = MagicMock()
            mock_provider.get_access_token = AsyncMock(return_value="gh-access-token")
            mock_provider.get_user_info = AsyncMock(
                return_value=OAuthUserInfo(
                    provider="github",
                    provider_user_id="github-456",
                    email=mock_user.email,
                    name="GitHub User",
                )
            )
            mock_provider_factory.return_value = mock_provider

            response = await async_client.get(
                "/api/v1/auth/github/callback",
                params={"code": "valid-code", "state": "valid-state"},
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "/dashboard" in response.headers.get("location", "")

    async def test_callback_provider_exception_redirects_with_failed_error(
        self, async_client: AsyncClient
    ):
        """Provider HTTP failure redirects to login with oauth_failed."""
        with (
            patch(
                "app.api.v1.auth.validate_oauth_state",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("app.api.v1.auth._get_google_provider") as mock_provider_factory,
            patch("app.api.v1.auth.settings") as mock_settings,
        ):
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            mock_settings.GOOGLE_CLIENT_ID = "configured"
            mock_settings.GOOGLE_CLIENT_SECRET = "configured"
            mock_settings.OAUTH_REDIRECT_BASE_URL = "http://localhost:8000"

            mock_provider = MagicMock()
            mock_provider.get_access_token = AsyncMock(
                side_effect=ValueError("Token exchange failed")
            )
            mock_provider_factory.return_value = mock_provider

            response = await async_client.get(
                "/api/v1/auth/google/callback",
                params={"code": "bad-code", "state": "valid-state"},
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "error=oauth_failed" in response.headers.get("location", "")

    async def test_github_callback_provider_exception_redirects_with_failed_error(
        self, async_client: AsyncClient
    ):
        """GitHub provider HTTP failure redirects to login with oauth_failed."""
        with (
            patch(
                "app.api.v1.auth.validate_oauth_state",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("app.api.v1.auth._get_github_provider") as mock_provider_factory,
            patch("app.api.v1.auth.settings") as mock_settings,
        ):
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            mock_settings.GITHUB_CLIENT_ID = "configured"
            mock_settings.GITHUB_CLIENT_SECRET = "configured"
            mock_settings.OAUTH_REDIRECT_BASE_URL = "http://localhost:8000"

            mock_provider = MagicMock()
            mock_provider.get_access_token = AsyncMock(
                side_effect=ValueError("Token exchange failed")
            )
            mock_provider_factory.return_value = mock_provider

            response = await async_client.get(
                "/api/v1/auth/github/callback",
                params={"code": "bad-code", "state": "valid-state"},
                follow_redirects=False,
            )

        assert response.status_code == 302
        assert "error=oauth_failed" in response.headers.get("location", "")

    async def test_github_callback_calls_oauth_login_or_register(
        self, async_client: AsyncClient
    ):
        """GitHub callback calls oauth_login_or_register and create_token_pair."""
        mock_user = _make_mock_user(email="ghflow@example.com")
        mock_payload = _make_token_payload(mock_user.uuid)

        mock_oauth_login = AsyncMock(return_value=mock_user)
        mock_create_pair = MagicMock(return_value=("gh-access", "gh-refresh"))

        with (
            patch(
                "app.api.v1.auth.validate_oauth_state",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("app.api.v1.auth._get_github_provider") as mock_provider_factory,
            patch(
                "app.api.v1.auth.auth_service.oauth_login_or_register",
                new=mock_oauth_login,
            ),
            patch("app.api.v1.auth.create_token_pair", new=mock_create_pair),
            patch("app.api.v1.auth.decode_token", return_value=mock_payload),
            patch(
                "app.api.v1.auth.register_token_in_family", new_callable=AsyncMock
            ),
            patch("app.api.v1.auth.track_user_family", new_callable=AsyncMock),
            patch("app.api.v1.auth.settings") as mock_settings,
        ):
            mock_settings.FRONTEND_URL = "http://localhost:3000"
            mock_settings.ENVIRONMENT = "local"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 7

            mock_provider = MagicMock()
            mock_provider.get_access_token = AsyncMock(return_value="gh-token")
            mock_provider.get_user_info = AsyncMock(
                return_value=OAuthUserInfo(
                    provider="github",
                    provider_user_id="github-flow-789",
                    email="ghflow@example.com",
                    name="GH Flow User",
                )
            )
            mock_provider_factory.return_value = mock_provider

            response = await async_client.get(
                "/api/v1/auth/github/callback",
                params={"code": "valid-code", "state": "valid-state"},
                follow_redirects=False,
            )

        # Verify the code path was fully executed
        mock_oauth_login.assert_called_once()
        mock_create_pair.assert_called_once_with(mock_user.uuid)
        assert response.status_code == 302
        assert "/dashboard" in response.headers.get("location", "")


# ---------------------------------------------------------------------------
# TestOAuthLoginOrRegister — service-level logic
# ---------------------------------------------------------------------------

class TestOAuthLoginOrRegister:
    """Service-level tests for oauth_login_or_register module function."""

    async def test_creates_new_user_for_new_oauth_account(
        self, mock_db_session: AsyncMock
    ):
        """New OAuth user creates both User and OAuthAccount."""
        import uuid as uuid_pkg

        from app.services.auth_service import oauth_login_or_register

        user_info = OAuthUserInfo(
            provider="google",
            provider_user_id="google-new-12345",
            email="brandnew@example.com",
            name="Brand New User",
        )

        # Mock OAuthAccountRepository: no existing OAuth account, no existing user
        mock_oauth_account = MagicMock()
        mock_oauth_account.user_id = 99
        mock_new_user = MagicMock()
        mock_new_user.id = 99
        mock_new_user.uuid = uuid_pkg.uuid4()
        mock_new_user.email = "brandnew@example.com"
        mock_new_user.is_verified = True
        mock_new_user.hashed_password = None
        mock_new_user.display_name = None  # Will be set from user_info.name
        mock_new_user.is_active = True

        # Mock free tier for tier assignment during registration
        mock_free_tier = MagicMock()
        mock_free_tier.id = 1
        mock_free_tier.slug = "free"

        with (
            patch("app.services.auth_service.OAuthAccountRepository") as MockOAuthRepo,
            patch("app.services.auth_service.UserRepository") as MockUserRepo,
            patch("app.services.auth_service.TierRepository") as MockTierRepo,
        ):
            mock_oauth_repo = MagicMock()
            mock_oauth_repo.get = AsyncMock(return_value=None)  # No existing OAuth
            mock_oauth_repo.create_oauth_account = AsyncMock(
                return_value=mock_oauth_account
            )
            MockOAuthRepo.return_value = mock_oauth_repo

            mock_user_repo = MagicMock()
            mock_user_repo.get = AsyncMock(return_value=None)  # No existing user
            mock_user_repo.create_user = AsyncMock(return_value=mock_new_user)
            mock_user_repo.update = AsyncMock(return_value=mock_new_user)
            MockUserRepo.return_value = mock_user_repo

            mock_tier_repo = MagicMock()
            mock_tier_repo.get = AsyncMock(return_value=mock_free_tier)
            MockTierRepo.return_value = mock_tier_repo

            user = await oauth_login_or_register(mock_db_session, user_info)

        assert user.email == "brandnew@example.com"
        assert user.is_verified is True
        assert user.hashed_password is None
        # display_name should be set from user_info.name
        mock_user_repo.update.assert_called_once()

    async def test_returns_existing_user_for_known_oauth(
        self, mock_db_session: AsyncMock
    ):
        """Existing OAuth account returns the same user without creating anything new."""
        from app.services.auth_service import oauth_login_or_register

        user_info = OAuthUserInfo(
            provider="google",
            provider_user_id="google-repeat-999",
            email="repeat@example.com",
            name="Repeat User",
        )

        mock_existing_oauth = MagicMock()
        mock_existing_oauth.user_id = 7
        mock_existing_user = MagicMock()
        mock_existing_user.id = 7
        mock_existing_user.uuid = uuid_pkg.uuid4()
        mock_existing_user.email = "repeat@example.com"
        mock_existing_user.is_active = True
        mock_existing_user.is_verified = True

        with (
            patch("app.services.auth_service.OAuthAccountRepository") as MockOAuthRepo,
            patch("app.services.auth_service.UserRepository") as MockUserRepo,
        ):
            mock_oauth_repo = MagicMock()
            # First call: finds existing OAuth account
            mock_oauth_repo.get = AsyncMock(return_value=mock_existing_oauth)
            MockOAuthRepo.return_value = mock_oauth_repo

            mock_user_repo = MagicMock()
            mock_user_repo.get = AsyncMock(return_value=mock_existing_user)
            MockUserRepo.return_value = mock_user_repo

            user = await oauth_login_or_register(mock_db_session, user_info)

        assert user.id == 7
        # No new user or OAuth account should be created
        mock_user_repo.create_user.assert_not_called() if hasattr(mock_user_repo, "create_user") else None

    async def test_auto_links_oauth_to_existing_email_user(
        self, mock_db_session: AsyncMock
    ):
        """OAuth with matching email auto-links to existing user (D-14)."""
        from app.services.auth_service import oauth_login_or_register

        existing_user_uuid = uuid_pkg.uuid4()
        user_info = OAuthUserInfo(
            provider="github",
            provider_user_id="github-link-id-555",
            email="existing@example.com",
            name="Existing User",
        )

        mock_existing_user = MagicMock()
        mock_existing_user.id = 5
        mock_existing_user.uuid = existing_user_uuid
        mock_existing_user.email = "existing@example.com"
        mock_existing_user.is_active = True
        mock_existing_user.is_verified = True

        mock_new_oauth = MagicMock()

        with (
            patch("app.services.auth_service.OAuthAccountRepository") as MockOAuthRepo,
            patch("app.services.auth_service.UserRepository") as MockUserRepo,
        ):
            mock_oauth_repo = MagicMock()
            # First call: no existing OAuth for this provider+id
            # Second call (D-15 check): no existing OAuth for this user_id either
            mock_oauth_repo.get = AsyncMock(side_effect=[None, None])
            mock_oauth_repo.create_oauth_account = AsyncMock(return_value=mock_new_oauth)
            MockOAuthRepo.return_value = mock_oauth_repo

            mock_user_repo = MagicMock()
            mock_user_repo.get = AsyncMock(return_value=mock_existing_user)
            mock_user_repo.update = AsyncMock(return_value=mock_existing_user)
            MockUserRepo.return_value = mock_user_repo

            user = await oauth_login_or_register(mock_db_session, user_info)

        # Should return the existing user (linked, not new)
        assert user.id == 5
        assert user.uuid == existing_user_uuid
        # OAuth account should be created for the existing user
        mock_oauth_repo.create_oauth_account.assert_called_once_with(
            user_id=5,
            provider="github",
            provider_user_id="github-link-id-555",
            provider_email="existing@example.com",
        )

    async def test_rejects_second_oauth_provider_for_same_user(
        self, mock_db_session: AsyncMock
    ):
        """D-15: Linking a second OAuth provider to a user already linked raises ConflictError."""
        from app.core.exceptions import ConflictError
        from app.services.auth_service import oauth_login_or_register

        user_info = OAuthUserInfo(
            provider="github",
            provider_user_id="github-conflict-id",
            email="alreadylinked@example.com",
            name="Already Linked",
        )

        mock_existing_user = MagicMock()
        mock_existing_user.id = 10
        mock_existing_user.uuid = uuid_pkg.uuid4()
        mock_existing_user.email = "alreadylinked@example.com"
        mock_existing_user.is_active = True

        mock_existing_google_oauth = MagicMock()  # User already has Google linked

        with (
            patch("app.services.auth_service.OAuthAccountRepository") as MockOAuthRepo,
            patch("app.services.auth_service.UserRepository") as MockUserRepo,
        ):
            mock_oauth_repo = MagicMock()
            # First get: no GitHub account for this provider_user_id
            # Second get (D-15): finds existing Google account for this user
            mock_oauth_repo.get = AsyncMock(
                side_effect=[None, mock_existing_google_oauth]
            )
            MockOAuthRepo.return_value = mock_oauth_repo

            mock_user_repo = MagicMock()
            mock_user_repo.get = AsyncMock(return_value=mock_existing_user)
            MockUserRepo.return_value = mock_user_repo

            with pytest.raises(ConflictError):
                await oauth_login_or_register(mock_db_session, user_info)
