"""Tests for admin tier management endpoints (POST/PATCH/DELETE /admin/tiers)."""

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
    """Create a mock superuser for admin tier tests."""
    user = MagicMock()
    user.id = 99
    user.uuid = uuid_pkg.uuid4()
    user.email = "admin@example.com"
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
    """Create a mock regular user for 403 tests."""
    user = MagicMock()
    user.id = 1
    user.uuid = uuid_pkg.uuid4()
    user.email = "user@example.com"
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


@pytest.fixture
def mock_tier_obj():
    """Create a mock Tier model object."""
    tier = MagicMock()
    tier.id = 10
    tier.uuid = uuid_pkg.uuid4()
    tier.name = "Test Tier"
    tier.slug = "test-tier"
    tier.description = "A test tier"
    tier.max_projects = 5
    tier.max_docs_per_project = 20
    tier.max_fixes_monthly = 50
    tier.max_file_size_mb = 25
    tier.allowed_models = ["gpt-4o-mini"]
    tier.feature_flags = {"can_export_pdf": True}
    tier.stripe_price_id = None
    tier.created_at = datetime.now(UTC)
    tier.updated_at = datetime.now(UTC)
    tier.deleted_at = None
    return tier


def _override_superuser(app, mock_superuser):
    from app.api.dependencies import get_current_superuser
    app.dependency_overrides[get_current_superuser] = lambda: mock_superuser


def _override_regular_user(app, mock_regular_user):
    from app.api.dependencies import get_current_active_user, get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_regular_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_regular_user


def _cleanup(app):
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Authorization guard
# ---------------------------------------------------------------------------

class TestAdminTierAuthorization:
    """Non-superuser access returns 403."""

    async def test_non_superuser_create_tier_403(
        self, async_client: AsyncClient, mock_regular_user
    ):
        """Non-superuser POST /admin/tiers returns 403."""
        from app.main import app
        _override_regular_user(app, mock_regular_user)

        try:
            response = await async_client.post(
                "/api/v1/admin/tiers",
                json={"name": "Test", "slug": "test"},
            )
            assert response.status_code == 403
        finally:
            _cleanup(app)


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

class TestAdminTierCRUD:
    """Superuser tier CRUD tests."""

    async def test_create_tier(
        self, async_client: AsyncClient, mock_superuser, mock_tier_obj
    ):
        """POST /admin/tiers creates a new tier and returns 201."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        with patch("app.services.tier_service.TierRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get = AsyncMock(return_value=None)  # No conflicts
            mock_repo.create = AsyncMock(return_value=mock_tier_obj)

            response = await async_client.post(
                "/api/v1/admin/tiers",
                json={
                    "name": "Test Tier",
                    "slug": "test-tier",
                    "max_projects": 5,
                    "max_docs_per_project": 20,
                    "max_fixes_monthly": 50,
                    "max_file_size_mb": 25,
                },
            )

        _cleanup(app)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Tier"
        assert data["slug"] == "test-tier"
        assert "uuid" in data

    async def test_update_tier(
        self, async_client: AsyncClient, mock_superuser, mock_tier_obj
    ):
        """PATCH /admin/tiers/{uuid} updates tier fields."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        updated_tier = MagicMock()
        updated_tier.id = mock_tier_obj.id
        updated_tier.uuid = mock_tier_obj.uuid
        updated_tier.name = "Updated Tier"
        updated_tier.slug = "test-tier"
        updated_tier.description = mock_tier_obj.description
        updated_tier.max_projects = 10
        updated_tier.max_docs_per_project = 20
        updated_tier.max_fixes_monthly = 50
        updated_tier.max_file_size_mb = 25
        updated_tier.allowed_models = ["gpt-4o-mini"]
        updated_tier.feature_flags = {"can_export_pdf": True}
        updated_tier.stripe_price_id = None
        updated_tier.created_at = mock_tier_obj.created_at
        updated_tier.updated_at = datetime.now(UTC)
        updated_tier.deleted_at = None

        with patch("app.services.tier_service.TierRepository") as MockRepo:
            mock_repo = MockRepo.return_value

            # get() is called multiple times:
            # 1. get(uuid=...) -> returns the tier to update
            # 2. get(name=...) -> returns None (no conflict)
            async def _smart_get(**kwargs):
                if "uuid" in kwargs:
                    return mock_tier_obj
                return None  # No name/slug conflicts

            mock_repo.get = AsyncMock(side_effect=_smart_get)
            mock_repo.update = AsyncMock(return_value=updated_tier)

            response = await async_client.patch(
                f"/api/v1/admin/tiers/{mock_tier_obj.uuid}",
                json={"name": "Updated Tier", "max_projects": 10},
            )

        _cleanup(app)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Tier"

    async def test_delete_tier(
        self, async_client: AsyncClient, mock_superuser, mock_tier_obj
    ):
        """DELETE /admin/tiers/{uuid} returns 204."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        with patch("app.services.tier_service.TierRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get = AsyncMock(return_value=mock_tier_obj)
            mock_repo.soft_delete = AsyncMock(return_value=mock_tier_obj)

            response = await async_client.delete(
                f"/api/v1/admin/tiers/{mock_tier_obj.uuid}"
            )

        _cleanup(app)

        assert response.status_code == 204


# ---------------------------------------------------------------------------
# Public tier listing still works
# ---------------------------------------------------------------------------

class TestPublicTierListing:
    """Public tier listing endpoint should work without auth."""

    async def test_public_list_tiers(
        self, async_client: AsyncClient, mock_tier_obj
    ):
        """GET /tiers returns list of tiers (no auth required)."""
        with patch("app.services.tier_service.TierRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_multi = AsyncMock(return_value=[mock_tier_obj])

            response = await async_client.get("/api/v1/tiers")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["slug"] == "test-tier"
