"""Tests for admin user management endpoints (GET/PATCH /admin/users)."""

import uuid as uuid_pkg
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_superuser():
    """Create a mock superuser for admin tests."""
    user = MagicMock()
    user.id = 99
    user.uuid = uuid_pkg.uuid4()
    user.email = "admin@example.com"
    user.hashed_password = "$2b$12$mock_hash"
    user.display_name = "Admin"
    user.avatar_url = None
    user.status = "active"
    user.is_active = True
    user.is_verified = True
    user.is_superuser = True
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = None
    mock_tier = MagicMock()
    mock_tier.name = "Ultra"
    mock_tier.slug = "ultra"
    user.tier = mock_tier
    user.tier_id = 3
    user.stripe_customer_id = None
    return user


@pytest.fixture
def mock_regular_user():
    """Create a mock regular (non-superuser) for admin tests."""
    user = MagicMock()
    user.id = 1
    user.uuid = uuid_pkg.uuid4()
    user.email = "user@example.com"
    user.hashed_password = "$2b$12$mock_hash"
    user.display_name = "Regular User"
    user.avatar_url = None
    user.status = "active"
    user.is_active = True
    user.is_verified = True
    user.is_superuser = False
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = None
    mock_tier = MagicMock()
    mock_tier.name = "Free"
    mock_tier.slug = "free"
    user.tier = mock_tier
    user.tier_id = 1
    user.stripe_customer_id = None
    return user


def _override_superuser(app, mock_superuser):
    """Override get_current_superuser dependency with mock superuser."""
    from app.api.dependencies import get_current_superuser
    app.dependency_overrides[get_current_superuser] = lambda: mock_superuser


def _override_active_user_as_regular(app, mock_regular_user):
    """Override get_current_active_user with a regular (non-superuser) user.

    This bypasses get_current_user but still hits get_current_superuser
    which should reject non-superusers with 403.
    """
    from app.api.dependencies import get_current_active_user, get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_regular_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_regular_user


def _cleanup_overrides(app):
    """Remove all dependency overrides."""
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /api/v1/admin/users — Authorization guard
# ---------------------------------------------------------------------------

class TestAdminUserAuthorization:
    """Non-superuser access to admin endpoints returns 403."""

    async def test_non_superuser_gets_403(self, async_client: AsyncClient, mock_regular_user):
        """Non-superuser GET /admin/users returns 403."""
        from app.main import app
        _override_active_user_as_regular(app, mock_regular_user)

        try:
            response = await async_client.get("/api/v1/admin/users")
            assert response.status_code == 403
        finally:
            _cleanup_overrides(app)

    async def test_unauthenticated_gets_401(self, async_client: AsyncClient):
        """Unauthenticated request to /admin/users returns 401."""
        response = await async_client.get("/api/v1/admin/users")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/admin/users — List users
# ---------------------------------------------------------------------------

class TestAdminListUsers:
    """Tests for superuser listing users."""

    async def test_superuser_can_list_users(
        self, async_client: AsyncClient, mock_superuser, mock_regular_user
    ):
        """Superuser GET /admin/users returns paginated response structure."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        with patch("app.services.admin_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search_users = AsyncMock(return_value=([mock_regular_user], 1))

            response = await async_client.get("/api/v1/admin/users")

        _cleanup_overrides(app)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "pages" in data
        assert data["total"] == 1
        assert data["page"] == 1
        assert len(data["items"]) == 1

    async def test_search_by_email(
        self, async_client: AsyncClient, mock_superuser, mock_regular_user
    ):
        """GET /admin/users?q=user@ filters results by email."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        with patch("app.services.admin_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search_users = AsyncMock(return_value=([mock_regular_user], 1))

            response = await async_client.get("/api/v1/admin/users?q=user@")

        _cleanup_overrides(app)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    async def test_filter_by_status(
        self, async_client: AsyncClient, mock_superuser, mock_regular_user
    ):
        """GET /admin/users?status=active returns only active users."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        with patch("app.services.admin_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.search_users = AsyncMock(return_value=([mock_regular_user], 1))

            response = await async_client.get("/api/v1/admin/users?status=active")

        _cleanup_overrides(app)

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/v1/admin/users/{uuid} — User detail
# ---------------------------------------------------------------------------

class TestAdminGetUser:
    """Tests for superuser getting user detail."""

    async def test_get_user_detail(
        self, async_client: AsyncClient, mock_superuser, mock_regular_user
    ):
        """GET /admin/users/{uuid} returns AdminUserRead fields."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        with patch("app.services.admin_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get = AsyncMock(return_value=mock_regular_user)

            response = await async_client.get(
                f"/api/v1/admin/users/{mock_regular_user.uuid}"
            )

        _cleanup_overrides(app)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"
        assert data["status"] == "active"
        assert "uuid" in data
        assert "is_verified" in data
        assert "is_superuser" in data
        assert "tier_slug" in data
        assert "tier_name" in data
        assert "created_at" in data

    async def test_get_nonexistent_user_returns_404(
        self, async_client: AsyncClient, mock_superuser
    ):
        """GET /admin/users/{random_uuid} returns 404."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        random_uuid = uuid_pkg.uuid4()

        with patch("app.services.admin_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get = AsyncMock(return_value=None)

            response = await async_client.get(
                f"/api/v1/admin/users/{random_uuid}"
            )

        _cleanup_overrides(app)

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/v1/admin/users/{uuid} — Update user
# ---------------------------------------------------------------------------

class TestAdminUpdateUser:
    """Tests for superuser updating users."""

    async def test_ban_user(
        self, async_client: AsyncClient, mock_superuser, mock_regular_user
    ):
        """PATCH /admin/users/{uuid} with status=banned sets user status to banned."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        # After update, mock_regular_user will have status=banned
        updated_user = MagicMock()
        updated_user.uuid = mock_regular_user.uuid
        updated_user.email = mock_regular_user.email
        updated_user.display_name = mock_regular_user.display_name
        updated_user.avatar_url = None
        updated_user.status = "banned"
        updated_user.is_verified = True
        updated_user.is_superuser = False
        updated_user.created_at = mock_regular_user.created_at
        updated_user.updated_at = datetime.now(UTC)
        mock_tier = MagicMock()
        mock_tier.name = "Free"
        mock_tier.slug = "free"
        updated_user.tier = mock_tier
        updated_user.stripe_customer_id = None

        with (
            patch("app.services.admin_service.UserRepository") as MockUserRepo,
            patch("app.services.admin_service.TierRepository") as MockTierRepo,
            patch("app.services.admin_service.invalidate_all_user_sessions", new_callable=AsyncMock),
        ):
            mock_user_repo = MockUserRepo.return_value
            mock_user_repo.get = AsyncMock(return_value=mock_regular_user)
            mock_user_repo.update = AsyncMock(return_value=updated_user)

            response = await async_client.patch(
                f"/api/v1/admin/users/{mock_regular_user.uuid}",
                json={"status": "banned"},
            )

        _cleanup_overrides(app)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "banned"

    async def test_update_user_status_deactivated(
        self, async_client: AsyncClient, mock_superuser, mock_regular_user
    ):
        """PATCH with status=deactivated updates user status."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        updated_user = MagicMock()
        updated_user.uuid = mock_regular_user.uuid
        updated_user.email = mock_regular_user.email
        updated_user.display_name = mock_regular_user.display_name
        updated_user.avatar_url = None
        updated_user.status = "deactivated"
        updated_user.is_verified = True
        updated_user.is_superuser = False
        updated_user.created_at = mock_regular_user.created_at
        updated_user.updated_at = datetime.now(UTC)
        mock_tier = MagicMock()
        mock_tier.name = "Free"
        mock_tier.slug = "free"
        updated_user.tier = mock_tier
        updated_user.stripe_customer_id = None

        with (
            patch("app.services.admin_service.UserRepository") as MockUserRepo,
            patch("app.services.admin_service.TierRepository") as MockTierRepo,
        ):
            mock_user_repo = MockUserRepo.return_value
            mock_user_repo.get = AsyncMock(return_value=mock_regular_user)
            mock_user_repo.update = AsyncMock(return_value=updated_user)

            response = await async_client.patch(
                f"/api/v1/admin/users/{mock_regular_user.uuid}",
                json={"status": "deactivated"},
            )

        _cleanup_overrides(app)

        assert response.status_code == 200
        assert response.json()["status"] == "deactivated"

    async def test_invalid_status_returns_422(
        self, async_client: AsyncClient, mock_superuser
    ):
        """PATCH with invalid status value returns 422 (Pydantic validation)."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        response = await async_client.patch(
            f"/api/v1/admin/users/{uuid_pkg.uuid4()}",
            json={"status": "invalid_status"},
        )

        _cleanup_overrides(app)

        assert response.status_code == 422
