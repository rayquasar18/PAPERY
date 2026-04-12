"""Tests for admin system settings endpoints (GET/PATCH /admin/settings)."""

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
    """Create a mock superuser for admin settings tests."""
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
def mock_setting_obj():
    """Create a mock SystemSetting model object."""
    setting = MagicMock()
    setting.uuid = uuid_pkg.uuid4()
    setting.key = "maintenance_mode"
    setting.value = {"v": False}
    setting.category = "general"
    setting.description = "When enabled, shows maintenance page."
    setting.created_at = datetime.now(UTC)
    setting.updated_at = datetime.now(UTC)
    return setting


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

class TestAdminSettingsAuthorization:
    """Non-superuser access to settings returns 403."""

    async def test_non_superuser_list_settings_403(
        self, async_client: AsyncClient, mock_regular_user
    ):
        """Non-superuser GET /admin/settings returns 403."""
        from app.main import app
        _override_regular_user(app, mock_regular_user)

        try:
            response = await async_client.get("/api/v1/admin/settings")
            assert response.status_code == 403
        finally:
            _cleanup(app)


# ---------------------------------------------------------------------------
# GET /api/v1/admin/settings — List settings
# ---------------------------------------------------------------------------

class TestAdminListSettings:
    """Tests for listing all system settings."""

    async def test_list_all_settings_grouped(
        self, async_client: AsyncClient, mock_superuser
    ):
        """GET /admin/settings returns settings grouped by category."""
        from app.main import app
        from app.schemas.system_setting import SystemSettingRead
        _override_superuser(app, mock_superuser)

        mock_grouped = {
            "general": [
                SystemSettingRead(
                    uuid=uuid_pkg.uuid4(),
                    key="maintenance_mode",
                    value={"v": False},
                    category="general",
                    description="Maintenance mode toggle",
                    updated_at=datetime.now(UTC),
                )
            ],
        }

        with patch("app.api.v1.admin.settings.SettingsService") as MockService:
            instance = MockService.return_value
            instance.get_all_settings = AsyncMock(return_value=mock_grouped)

            response = await async_client.get("/api/v1/admin/settings")

        _cleanup(app)

        assert response.status_code == 200
        data = response.json()
        assert "settings" in data
        assert isinstance(data["settings"], dict)


# ---------------------------------------------------------------------------
# GET /api/v1/admin/settings/{key} — Get single setting
# ---------------------------------------------------------------------------

class TestAdminGetSetting:
    """Tests for getting a single setting by key."""

    async def test_get_setting_by_key(
        self, async_client: AsyncClient, mock_superuser, mock_setting_obj
    ):
        """GET /admin/settings/maintenance_mode returns setting."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        with patch("app.api.v1.admin.settings.SettingsService") as MockService:
            instance = MockService.return_value
            instance.get_setting = AsyncMock(return_value=mock_setting_obj)

            response = await async_client.get("/api/v1/admin/settings/maintenance_mode")

        _cleanup(app)

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "maintenance_mode"
        assert "uuid" in data
        assert "value" in data
        assert "category" in data

    async def test_get_unknown_key_returns_400(
        self, async_client: AsyncClient, mock_superuser
    ):
        """GET /admin/settings/nonexistent_key returns 400."""
        from app.main import app
        from app.core.exceptions import BadRequestError
        _override_superuser(app, mock_superuser)

        with patch("app.api.v1.admin.settings.SettingsService") as MockService:
            instance = MockService.return_value
            instance.get_setting = AsyncMock(
                side_effect=BadRequestError(detail="Unknown setting key: 'nonexistent_key'")
            )

            response = await async_client.get("/api/v1/admin/settings/nonexistent_key")

        _cleanup(app)

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# PATCH /api/v1/admin/settings/{key} — Update setting
# ---------------------------------------------------------------------------

class TestAdminUpdateSetting:
    """Tests for updating system settings."""

    async def test_update_setting_value(
        self, async_client: AsyncClient, mock_superuser, mock_setting_obj
    ):
        """PATCH /admin/settings/maintenance_mode updates the value."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        updated_setting = MagicMock()
        updated_setting.uuid = mock_setting_obj.uuid
        updated_setting.key = "maintenance_mode"
        updated_setting.value = {"v": True}
        updated_setting.category = "general"
        updated_setting.description = mock_setting_obj.description
        updated_setting.updated_at = datetime.now(UTC)

        with patch("app.api.v1.admin.settings.SettingsService") as MockService:
            instance = MockService.return_value
            instance.update_setting = AsyncMock(return_value=updated_setting)

            response = await async_client.patch(
                "/api/v1/admin/settings/maintenance_mode",
                json={"value": True},
            )

        _cleanup(app)

        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "maintenance_mode"
        assert data["value"] == {"v": True}

    async def test_update_setting_invalid_type_returns_400(
        self, async_client: AsyncClient, mock_superuser
    ):
        """PATCH with invalid value type returns 400 (e.g. string for bool setting)."""
        from app.main import app
        from app.core.exceptions import BadRequestError
        _override_superuser(app, mock_superuser)

        with patch("app.api.v1.admin.settings.SettingsService") as MockService:
            instance = MockService.return_value
            instance.update_setting = AsyncMock(
                side_effect=BadRequestError(
                    detail="Setting 'maintenance_mode' must be a boolean, got str"
                )
            )

            response = await async_client.patch(
                "/api/v1/admin/settings/maintenance_mode",
                json={"value": "not_a_boolean"},
            )

        _cleanup(app)

        assert response.status_code == 400
