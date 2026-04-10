"""Tests for authentication route handlers (Plan 03-04-T4).

All service layer and infrastructure dependencies are mocked —
no real database, Redis, or SMTP needed.
"""

import uuid as uuid_pkg
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient

from app.core.exceptions import ConflictError, UnauthorizedError
from app.schemas.auth import TokenPayload


def _make_mock_user(
    *,
    email: str = "test@example.com",
    is_verified: bool = True,
    is_active: bool = True,
    is_superuser: bool = False,
) -> MagicMock:
    """Create a mock User with all required attributes."""
    user = MagicMock()
    user.id = 1
    user.uuid = uuid_pkg.uuid4()
    user.email = email
    user.hashed_password = "$2b$12$mock_hash"
    user.display_name = "Test User"
    user.avatar_url = None
    user.is_active = is_active
    user.is_verified = is_verified
    user.is_superuser = is_superuser
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = None
    return user


def _make_token_payload(
    user_uuid: uuid_pkg.UUID,
    *,
    token_type: str = "access",  # noqa: S107
    family: str | None = None,
) -> TokenPayload:
    """Create a TokenPayload for mocking decode_token."""
    now = int(datetime.now(UTC).timestamp())
    return TokenPayload(
        sub=str(user_uuid),
        jti=str(uuid_pkg.uuid4()),
        type=token_type,
        exp=now + 3600,
        iat=now,
        family=family,
    )


def _make_mock_service(mock_user: MagicMock | None = None) -> MagicMock:
    """Create a mock AuthService instance with async methods pre-configured."""
    service = MagicMock()
    service.register_user = AsyncMock(return_value=mock_user)
    service.authenticate_user = AsyncMock(return_value=mock_user)
    service.logout_user = AsyncMock()
    service.rotate_refresh_token = AsyncMock(return_value=("new-access-token", "new-refresh-token"))
    service.verify_email = AsyncMock(return_value=mock_user)
    service.send_verification_email = AsyncMock()
    service.request_password_reset = AsyncMock()
    service.reset_password = AsyncMock()
    service.get_user_by_uuid = AsyncMock(return_value=mock_user)
    service.get_user_by_email = AsyncMock(return_value=mock_user)
    return service


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------
class TestRegisterRoute:
    """Test POST /api/v1/auth/register."""

    async def test_register_success(self, async_client: AsyncClient):
        """Successful registration returns 201 with auth cookies."""
        mock_user = _make_mock_user(is_verified=False)
        mock_service = _make_mock_service(mock_user)
        mock_service.register_user = AsyncMock(return_value=mock_user)
        mock_service.send_verification_email = AsyncMock()

        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch("app.api.v1.auth.AuthService", return_value=mock_service),
            patch(
                "app.api.v1.auth.create_token_pair",
                return_value=("mock-access-token", "mock-refresh-token"),
            ),
            patch(
                "app.api.v1.auth.decode_token",
                return_value=_make_token_payload(mock_user.uuid, token_type="refresh", family="fam-1"),
            ),
            patch("app.api.v1.auth.register_token_in_family", new_callable=AsyncMock),
        ):
            response = await async_client.post(
                "/api/v1/auth/register",
                json={"email": "new@example.com", "password": "securepass123"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Registration successful. Please check your email to verify your account."
        assert data["user"]["email"] == mock_user.email
        # Verify auth cookies are set
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    async def test_register_duplicate_email(self, async_client: AsyncClient):
        """Duplicate email returns 409 Conflict."""
        mock_service = _make_mock_service()
        mock_service.register_user = AsyncMock(
            side_effect=ConflictError(detail="Email already registered")
        )

        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch("app.api.v1.auth.AuthService", return_value=mock_service),
        ):
            response = await async_client.post(
                "/api/v1/auth/register",
                json={"email": "dup@example.com", "password": "securepass123"},
            )

        assert response.status_code == 409

    async def test_register_validation_error(self, async_client: AsyncClient):
        """Invalid payload (short password) returns 422."""
        with patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock):
            response = await async_client.post(
                "/api/v1/auth/register",
                json={"email": "user@example.com", "password": "short"},
            )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------
class TestLoginRoute:
    """Test POST /api/v1/auth/login."""

    async def test_login_success(self, async_client: AsyncClient):
        """Successful login returns 200 with auth cookies."""
        mock_user = _make_mock_user()
        mock_service = _make_mock_service(mock_user)
        mock_service.authenticate_user = AsyncMock(return_value=mock_user)

        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch("app.api.v1.auth.AuthService", return_value=mock_service),
            patch(
                "app.api.v1.auth.create_token_pair",
                return_value=("mock-access-token", "mock-refresh-token"),
            ),
            patch(
                "app.api.v1.auth.decode_token",
                return_value=_make_token_payload(mock_user.uuid, token_type="refresh", family="fam-1"),
            ),
            patch("app.api.v1.auth.register_token_in_family", new_callable=AsyncMock),
        ):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "mypassword"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Login successful."
        assert data["user"]["email"] == mock_user.email
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    async def test_login_invalid_credentials(self, async_client: AsyncClient):
        """Wrong credentials returns 401."""
        mock_service = _make_mock_service()
        mock_service.authenticate_user = AsyncMock(
            side_effect=UnauthorizedError(detail="Invalid email or password")
        )

        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch("app.api.v1.auth.AuthService", return_value=mock_service),
        ):
            response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "wrongpass"},
            )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------
class TestLogoutRoute:
    """Test POST /api/v1/auth/logout."""

    async def test_logout_success(self, async_client: AsyncClient):
        """Authenticated logout returns 200 and clears cookies."""
        mock_user = _make_mock_user()
        access_payload = _make_token_payload(mock_user.uuid)

        mock_dep_repo = AsyncMock()
        mock_dep_repo.get = AsyncMock(return_value=mock_user)

        mock_service = _make_mock_service(mock_user)
        mock_service.logout_user = AsyncMock()

        with (
            patch(
                "app.api.dependencies.decode_token",
                return_value=access_payload,
            ),
            patch(
                "app.api.dependencies.is_token_blacklisted",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.api.dependencies.UserRepository",
                return_value=mock_dep_repo,
            ),
            patch(
                "app.api.v1.auth.decode_token",
                return_value=access_payload,
            ),
            patch("app.api.v1.auth.AuthService", return_value=mock_service),
        ):
            response = await async_client.post(
                "/api/v1/auth/logout",
                cookies={"access_token": "valid-mock-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Logged out successfully."

    async def test_logout_no_token(self, async_client: AsyncClient):
        """Logout without access token returns 401."""
        response = await async_client.post("/api/v1/auth/logout")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------
class TestRefreshRoute:
    """Test POST /api/v1/auth/refresh."""

    async def test_refresh_success(self, async_client: AsyncClient):
        """Valid refresh returns 200 with new cookies."""
        mock_user = _make_mock_user()
        old_refresh_payload = _make_token_payload(
            mock_user.uuid, token_type="refresh", family="fam-1"
        )

        mock_service = _make_mock_service(mock_user)
        mock_service.rotate_refresh_token = AsyncMock(
            return_value=("new-access-token", "new-refresh-token")
        )
        mock_service.get_user_by_uuid = AsyncMock(return_value=mock_user)

        with (
            patch(
                "app.api.v1.auth.decode_token",
                return_value=old_refresh_payload,
            ),
            patch("app.api.v1.auth.AuthService", return_value=mock_service),
        ):
            response = await async_client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": "old-refresh-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Tokens refreshed successfully."
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    async def test_refresh_no_token(self, async_client: AsyncClient):
        """Refresh without cookie returns 401."""
        response = await async_client.post("/api/v1/auth/refresh")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------
class TestGetMeRoute:
    """Test GET /api/v1/auth/me."""

    async def test_me_success(self, async_client: AsyncClient):
        """Authenticated user gets their profile (no password)."""
        mock_user = _make_mock_user()
        access_payload = _make_token_payload(mock_user.uuid)

        mock_repo_instance = AsyncMock()
        mock_repo_instance.get = AsyncMock(return_value=mock_user)

        with (
            patch(
                "app.api.dependencies.decode_token",
                return_value=access_payload,
            ),
            patch(
                "app.api.dependencies.is_token_blacklisted",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "app.api.dependencies.UserRepository",
                return_value=mock_repo_instance,
            ),
        ):
            response = await async_client.get(
                "/api/v1/auth/me",
                cookies={"access_token": "valid-mock-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == mock_user.email
        assert "hashed_password" not in data
        assert "password" not in data
        assert "id" not in data

    async def test_me_no_auth(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/auth/verify-email
# ---------------------------------------------------------------------------
class TestVerifyEmailRoute:
    """Test POST /api/v1/auth/verify-email."""

    async def test_verify_email_success(self, async_client: AsyncClient):
        """Valid token returns 200 with success message."""
        mock_user = _make_mock_user(is_verified=True)
        mock_service = _make_mock_service(mock_user)
        mock_service.verify_email = AsyncMock(return_value=mock_user)

        with patch("app.api.v1.auth.AuthService", return_value=mock_service):
            response = await async_client.post(
                "/api/v1/auth/verify-email",
                json={"token": "valid-verification-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Email verified successfully."

    async def test_verify_email_invalid_token(self, async_client: AsyncClient):
        """Invalid verification token returns 400."""
        from app.core.exceptions import BadRequestError

        mock_service = _make_mock_service()
        mock_service.verify_email = AsyncMock(
            side_effect=BadRequestError(detail="Invalid or expired verification token")
        )

        with patch("app.api.v1.auth.AuthService", return_value=mock_service):
            response = await async_client.post(
                "/api/v1/auth/verify-email",
                json={"token": "expired-or-invalid-token"},
            )

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/v1/auth/resend-verification
# ---------------------------------------------------------------------------
class TestResendVerificationRoute:
    """Test POST /api/v1/auth/resend-verification."""

    async def test_resend_verification_success(self, async_client: AsyncClient):
        """Existing unverified user triggers email and returns 200."""
        mock_user = _make_mock_user(is_verified=False)
        mock_service = _make_mock_service(mock_user)
        mock_service.get_user_by_email = AsyncMock(return_value=mock_user)
        mock_service.send_verification_email = AsyncMock()

        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch("app.api.v1.auth.AuthService", return_value=mock_service),
        ):
            response = await async_client.post(
                "/api/v1/auth/resend-verification",
                json={"email": "test@example.com"},
            )

        assert response.status_code == 200
        mock_service.send_verification_email.assert_called_once()

    async def test_resend_verification_unknown_email_returns_200(self, async_client: AsyncClient):
        """Unknown email still returns 200 (anti-enumeration)."""
        mock_service = _make_mock_service()
        mock_service.get_user_by_email = AsyncMock(return_value=None)

        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch("app.api.v1.auth.AuthService", return_value=mock_service),
        ):
            response = await async_client.post(
                "/api/v1/auth/resend-verification",
                json={"email": "unknown@example.com"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "verification email has been sent" in data["message"]

    async def test_resend_verification_already_verified(self, async_client: AsyncClient):
        """Already-verified user should NOT trigger email send."""
        mock_user = _make_mock_user(is_verified=True)
        mock_service = _make_mock_service(mock_user)
        mock_service.get_user_by_email = AsyncMock(return_value=mock_user)
        mock_service.send_verification_email = AsyncMock()

        with (
            patch("app.api.v1.auth.check_rate_limit", new_callable=AsyncMock),
            patch("app.api.v1.auth.AuthService", return_value=mock_service),
        ):
            response = await async_client.post(
                "/api/v1/auth/resend-verification",
                json={"email": "test@example.com"},
            )

        assert response.status_code == 200
        mock_service.send_verification_email.assert_not_called()
