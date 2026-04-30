"""Tests for admin rate limit rule endpoints (CRUD /admin/rate-limits)."""

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
    """Create a mock superuser for admin rate limit tests."""
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
def mock_rate_limit_rule():
    """Create a mock RateLimitRule model object."""
    rule = MagicMock()
    rule.id = 1
    rule.uuid = uuid_pkg.uuid4()
    rule.tier_id = None
    rule.tier = None
    rule.endpoint_pattern = "auth:login"
    rule.max_requests = 10
    rule.window_seconds = 60
    rule.description = "Login rate limit"
    rule.created_at = datetime.now(UTC)
    rule.updated_at = datetime.now(UTC)
    rule.deleted_at = None
    return rule


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

class TestAdminRateLimitsAuthorization:
    """Non-superuser access returns 403."""

    async def test_non_superuser_list_rate_limits_403(
        self, async_client: AsyncClient, mock_regular_user
    ):
        """Non-superuser GET /admin/rate-limits returns 403."""
        from app.main import app
        _override_regular_user(app, mock_regular_user)

        try:
            response = await async_client.get("/api/v1/admin/rate-limits")
            assert response.status_code == 403
        finally:
            _cleanup(app)


# ---------------------------------------------------------------------------
# GET /api/v1/admin/rate-limits — List rules
# ---------------------------------------------------------------------------

class TestAdminListRateLimits:
    """Tests for listing rate limit rules."""

    async def test_list_rate_limit_rules(
        self, async_client: AsyncClient, mock_superuser, mock_rate_limit_rule
    ):
        """GET /admin/rate-limits returns array of rules."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        with (
            patch("app.services.rate_limit_rule_service.RateLimitRuleRepository") as MockRepo,
            patch("app.services.rate_limit_rule_service.TierRepository"),
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_all_active = AsyncMock(return_value=[mock_rate_limit_rule])

            response = await async_client.get("/api/v1/admin/rate-limits")

        _cleanup(app)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["endpoint_pattern"] == "auth:login"
        assert data[0]["max_requests"] == 10


# ---------------------------------------------------------------------------
# POST /api/v1/admin/rate-limits — Create rule
# ---------------------------------------------------------------------------

class TestAdminCreateRateLimit:
    """Tests for creating rate limit rules."""

    async def test_create_rate_limit_rule(
        self, async_client: AsyncClient, mock_superuser, mock_rate_limit_rule
    ):
        """POST /admin/rate-limits creates a new rule and returns 201."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        with (
            patch("app.services.rate_limit_rule_service.RateLimitRuleRepository") as MockRepo,
            patch("app.services.rate_limit_rule_service.TierRepository"),
            patch(
                "app.services.rate_limit_rule_service.invalidate_rate_limit_rule_cache",
                new_callable=AsyncMock,
            ),
        ):
            mock_repo = MockRepo.return_value
            mock_repo.find_rule = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=mock_rate_limit_rule)

            response = await async_client.post(
                "/api/v1/admin/rate-limits",
                json={
                    "endpoint_pattern": "auth:login",
                    "max_requests": 10,
                    "window_seconds": 60,
                    "description": "Login rate limit",
                },
            )

        _cleanup(app)

        assert response.status_code == 201
        data = response.json()
        assert data["endpoint_pattern"] == "auth:login"
        assert data["max_requests"] == 10
        assert "uuid" in data

    async def test_create_duplicate_rule_returns_409(
        self, async_client: AsyncClient, mock_superuser, mock_rate_limit_rule
    ):
        """POST with duplicate tier+endpoint returns 409."""
        from app.main import app
        from app.core.exceptions import ConflictError
        _override_superuser(app, mock_superuser)

        with (
            patch("app.services.rate_limit_rule_service.RateLimitRuleRepository") as MockRepo,
            patch("app.services.rate_limit_rule_service.TierRepository"),
        ):
            mock_repo = MockRepo.return_value
            # find_rule returns an existing rule — triggers ConflictError
            mock_repo.find_rule = AsyncMock(return_value=mock_rate_limit_rule)

            response = await async_client.post(
                "/api/v1/admin/rate-limits",
                json={
                    "endpoint_pattern": "auth:login",
                    "max_requests": 10,
                    "window_seconds": 60,
                },
            )

        _cleanup(app)

        assert response.status_code == 409


# ---------------------------------------------------------------------------
# PATCH /api/v1/admin/rate-limits/{uuid} — Update rule
# ---------------------------------------------------------------------------

class TestAdminUpdateRateLimit:
    """Tests for updating rate limit rules."""

    async def test_update_rate_limit_rule(
        self, async_client: AsyncClient, mock_superuser, mock_rate_limit_rule
    ):
        """PATCH /admin/rate-limits/{uuid} updates rule fields."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        updated_rule = MagicMock()
        updated_rule.uuid = mock_rate_limit_rule.uuid
        updated_rule.tier_id = None
        updated_rule.tier = None
        updated_rule.endpoint_pattern = "auth:login"
        updated_rule.max_requests = 20
        updated_rule.window_seconds = 60
        updated_rule.description = "Updated login rate limit"
        updated_rule.created_at = mock_rate_limit_rule.created_at
        updated_rule.updated_at = datetime.now(UTC)

        with (
            patch("app.services.rate_limit_rule_service.RateLimitRuleRepository") as MockRepo,
            patch("app.services.rate_limit_rule_service.TierRepository"),
            patch(
                "app.services.rate_limit_rule_service.invalidate_rate_limit_rule_cache",
                new_callable=AsyncMock,
            ),
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get = AsyncMock(return_value=mock_rate_limit_rule)
            mock_repo.update = AsyncMock(return_value=updated_rule)

            response = await async_client.patch(
                f"/api/v1/admin/rate-limits/{mock_rate_limit_rule.uuid}",
                json={"max_requests": 20, "description": "Updated login rate limit"},
            )

        _cleanup(app)

        assert response.status_code == 200
        data = response.json()
        assert data["max_requests"] == 20


# ---------------------------------------------------------------------------
# DELETE /api/v1/admin/rate-limits/{uuid} — Delete rule
# ---------------------------------------------------------------------------

class TestAdminDeleteRateLimit:
    """Tests for deleting rate limit rules."""

    async def test_delete_rate_limit_rule(
        self, async_client: AsyncClient, mock_superuser, mock_rate_limit_rule
    ):
        """DELETE /admin/rate-limits/{uuid} returns 204."""
        from app.main import app
        _override_superuser(app, mock_superuser)

        with (
            patch("app.services.rate_limit_rule_service.RateLimitRuleRepository") as MockRepo,
            patch("app.services.rate_limit_rule_service.TierRepository"),
            patch(
                "app.services.rate_limit_rule_service.invalidate_rate_limit_rule_cache",
                new_callable=AsyncMock,
            ),
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get = AsyncMock(return_value=mock_rate_limit_rule)
            mock_repo.soft_delete = AsyncMock(return_value=mock_rate_limit_rule)

            response = await async_client.delete(
                f"/api/v1/admin/rate-limits/{mock_rate_limit_rule.uuid}"
            )

        _cleanup(app)

        assert response.status_code == 204
