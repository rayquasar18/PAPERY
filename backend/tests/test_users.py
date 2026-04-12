"""Tests for user profile endpoints (GET /users/me, PATCH /users/me)."""

import io
import uuid as uuid_pkg
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.schemas.user import UserProfileRead


@pytest.fixture
def mock_user_with_oauth():
    """Create a mock User with oauth_accounts for profile tests."""
    user = MagicMock()
    user.id = 1
    user.uuid = uuid_pkg.uuid4()
    user.email = "profile@example.com"
    user.hashed_password = "$2b$12$mock_hash"
    user.display_name = "Test User"
    user.avatar_url = None
    user.is_active = True
    user.is_verified = True
    user.is_superuser = False
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = None
    user.oauth_accounts = []
    # Tier relationship (added in phase 6)
    mock_tier = MagicMock()
    mock_tier.name = "Free"
    mock_tier.slug = "free"
    user.tier = mock_tier
    user.tier_id = 1
    user.stripe_customer_id = None
    return user


@pytest.fixture
def mock_oauth_user():
    """Create a mock OAuth-only User (no password) with one provider."""
    user = MagicMock()
    user.id = 2
    user.uuid = uuid_pkg.uuid4()
    user.email = "oauth@example.com"
    user.hashed_password = None
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

    oauth_account = MagicMock()
    oauth_account.provider = "google"
    user.oauth_accounts = [oauth_account]
    return user


# ---------------------------------------------------------------------------
# GET /api/v1/users/me
# ---------------------------------------------------------------------------
class TestGetProfile:
    """Tests for GET /api/v1/users/me endpoint."""

    async def test_get_profile_unauthenticated(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_get_profile_returns_full_profile(
        self, async_client: AsyncClient, mock_user_with_oauth
    ):
        """Authenticated user gets full profile with computed fields."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        with (
            patch(
                "app.services.user_service.UserRepository"
            ) as MockRepo,
            patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock),
        ):
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_with_oauth_accounts = AsyncMock(
                return_value=mock_user_with_oauth
            )

            response = await async_client.get("/api/v1/users/me")

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "profile@example.com"
        assert data["display_name"] == "Test User"
        assert data["tier_name"] == "Free"
        assert data["has_password"] is True
        assert data["oauth_providers"] == []
        assert "uuid" in data
        assert "created_at" in data

    async def test_get_profile_oauth_user_has_password_false(
        self, async_client: AsyncClient, mock_oauth_user
    ):
        """OAuth-only user shows has_password=False and provider list."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_oauth_user

        with (
            patch(
                "app.services.user_service.UserRepository"
            ) as MockRepo,
            patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock),
        ):
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_with_oauth_accounts = AsyncMock(
                return_value=mock_oauth_user
            )

            response = await async_client.get("/api/v1/users/me")

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 200
        data = response.json()
        assert data["has_password"] is False
        assert data["oauth_providers"] == ["google"]

    async def test_get_profile_with_avatar_generates_presigned_url(
        self, async_client: AsyncClient, mock_user_with_oauth
    ):
        """When user has avatar_url, response contains presigned URL (not raw path)."""
        mock_user_with_oauth.avatar_url = "avatars/some-uuid/avatar.webp"

        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        with (
            patch(
                "app.services.user_service.UserRepository"
            ) as MockRepo,
            patch(
                "app.services.user_service._get_presigned_url",
                return_value="https://minio.local/presigned-avatar-url",
            ),
            patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock),
        ):
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_with_oauth_accounts = AsyncMock(
                return_value=mock_user_with_oauth
            )

            response = await async_client.get("/api/v1/users/me")

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 200
        data = response.json()
        assert data["avatar_url"] == "https://minio.local/presigned-avatar-url"


# ---------------------------------------------------------------------------
# PATCH /api/v1/users/me
# ---------------------------------------------------------------------------
class TestUpdateProfile:
    """Tests for PATCH /api/v1/users/me endpoint."""

    async def test_update_display_name_valid(
        self, async_client: AsyncClient, mock_user_with_oauth
    ):
        """Valid display_name update returns updated profile."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        with (
            patch(
                "app.services.user_service.UserRepository"
            ) as MockRepo,
            patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock),
        ):
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.update = AsyncMock(return_value=mock_user_with_oauth)
            mock_repo_instance.get_with_oauth_accounts = AsyncMock(
                return_value=mock_user_with_oauth
            )

            response = await async_client.patch(
                "/api/v1/users/me",
                json={"display_name": "New Name"},
            )

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 200
        data = response.json()
        assert "uuid" in data
        assert data["tier_name"] == "Free"

    async def test_update_display_name_too_short(self, async_client: AsyncClient, mock_user_with_oauth):
        """display_name shorter than 2 chars returns 422."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        with patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock):
            response = await async_client.patch(
                "/api/v1/users/me",
                json={"display_name": "A"},
            )

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 422

    async def test_update_display_name_too_long(self, async_client: AsyncClient, mock_user_with_oauth):
        """display_name longer than 50 chars returns 422."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        with patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock):
            response = await async_client.patch(
                "/api/v1/users/me",
                json={"display_name": "A" * 51},
            )

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 422

    async def test_update_display_name_invalid_chars(self, async_client: AsyncClient, mock_user_with_oauth):
        """display_name with special chars (not letters/digits/spaces/hyphens/underscores) returns 422."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        with patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock):
            response = await async_client.patch(
                "/api/v1/users/me",
                json={"display_name": "Name@#$!"},
            )

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 422

    async def test_update_profile_unauthenticated(self, async_client: AsyncClient):
        """Unauthenticated PATCH request returns 401."""
        response = await async_client.patch(
            "/api/v1/users/me",
            json={"display_name": "New Name"},
        )
        assert response.status_code == 401


@pytest.fixture
def valid_jpeg_bytes():
    """Generate a small valid JPEG image for upload tests."""
    img = Image.new("RGB", (400, 400), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# POST /api/v1/users/me/avatar
# ---------------------------------------------------------------------------
class TestAvatarUpload:
    """Tests for POST /api/v1/users/me/avatar endpoint."""

    async def test_upload_avatar_valid_jpeg(
        self, async_client: AsyncClient, mock_user_with_oauth, valid_jpeg_bytes
    ):
        """Valid JPEG upload returns AvatarUploadResponse with presigned URLs."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        with (
            patch("app.services.user_service.UserRepository") as MockRepo,
            patch("app.services.user_service._minio_client_module") as mock_minio,
            patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock),
        ):
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.update = AsyncMock(return_value=mock_user_with_oauth)
            mock_minio.upload_file = AsyncMock()
            mock_minio.presigned_get_url = MagicMock(return_value="https://minio.local/presigned")

            response = await async_client.post(
                "/api/v1/users/me/avatar",
                files={"file": ("avatar.jpg", valid_jpeg_bytes, "image/jpeg")},
            )

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 200
        data = response.json()
        assert "avatar_url" in data
        assert "thumbnail_url" in data
        assert data["message"] == "Avatar uploaded successfully"

    async def test_upload_avatar_oversized(
        self, async_client: AsyncClient, mock_user_with_oauth
    ):
        """File larger than 2MB returns 400."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        # Create 3MB of data
        oversized_data = b"x" * (3 * 1024 * 1024)

        with (
            patch("app.services.user_service.UserRepository"),
            patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock),
        ):
            response = await async_client.post(
                "/api/v1/users/me/avatar",
                files={"file": ("big.jpg", oversized_data, "image/jpeg")},
            )

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 400

    async def test_upload_avatar_invalid_mime(
        self, async_client: AsyncClient, mock_user_with_oauth
    ):
        """Non-image MIME type returns 400."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        with (
            patch("app.services.user_service.UserRepository"),
            patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock),
        ):
            response = await async_client.post(
                "/api/v1/users/me/avatar",
                files={"file": ("doc.pdf", b"fake pdf data", "application/pdf")},
            )

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 400

    async def test_upload_avatar_unauthenticated(self, async_client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await async_client.post(
            "/api/v1/users/me/avatar",
            files={"file": ("avatar.jpg", b"data", "image/jpeg")},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/v1/users/me/avatar
# ---------------------------------------------------------------------------
class TestAvatarRemove:
    """Tests for DELETE /api/v1/users/me/avatar endpoint."""

    async def test_remove_avatar_success(
        self, async_client: AsyncClient, mock_user_with_oauth
    ):
        """Remove avatar when user has one returns success."""
        mock_user_with_oauth.avatar_url = "avatars/some-uuid/avatar.webp"

        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        with (
            patch("app.services.user_service.UserRepository") as MockRepo,
            patch("app.services.user_service._minio_client_module") as mock_minio,
            patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock),
        ):
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.update = AsyncMock(return_value=mock_user_with_oauth)
            mock_minio.delete_file = AsyncMock()

            response = await async_client.delete("/api/v1/users/me/avatar")

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 200
        assert response.json()["message"] == "Avatar removed successfully"

    async def test_remove_avatar_no_avatar(
        self, async_client: AsyncClient, mock_user_with_oauth
    ):
        """Remove avatar when user has no avatar returns 400."""
        mock_user_with_oauth.avatar_url = None

        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        with patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock):
            response = await async_client.delete("/api/v1/users/me/avatar")

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/v1/users/me
# ---------------------------------------------------------------------------
class TestDeleteAccount:
    """Tests for DELETE /api/v1/users/me endpoint."""

    async def test_delete_account_correct_password(
        self, async_client: AsyncClient, mock_user_with_oauth
    ):
        """Account deletion with correct password succeeds."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        with (
            patch("app.services.user_service.UserRepository") as MockRepo,
            patch("app.services.user_service.verify_password", return_value=True),
            patch("app.services.user_service.invalidate_all_user_sessions", new_callable=AsyncMock),
            patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock),
        ):
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.soft_delete = AsyncMock(return_value=mock_user_with_oauth)

            response = await async_client.request(
                "DELETE",
                "/api/v1/users/me",
                json={"password": "correct-password"},
            )

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 200
        assert response.json()["message"] == "Account deleted successfully"
        # Verify status was set to "deactivated" (core USER-04 requirement)
        assert mock_user_with_oauth.status == "deactivated"

    async def test_delete_account_wrong_password(
        self, async_client: AsyncClient, mock_user_with_oauth
    ):
        """Account deletion with wrong password returns 401."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user_with_oauth

        with (
            patch("app.services.user_service.verify_password", return_value=False),
            patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock),
        ):
            response = await async_client.request(
                "DELETE",
                "/api/v1/users/me",
                json={"password": "wrong-password"},
            )

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 401

    async def test_delete_account_oauth_correct_email(
        self, async_client: AsyncClient, mock_oauth_user
    ):
        """OAuth-only user deletion with correct email succeeds."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_oauth_user

        with (
            patch("app.services.user_service.UserRepository") as MockRepo,
            patch("app.services.user_service.invalidate_all_user_sessions", new_callable=AsyncMock),
            patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock),
        ):
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.soft_delete = AsyncMock(return_value=mock_oauth_user)

            response = await async_client.request(
                "DELETE",
                "/api/v1/users/me",
                json={"email": "oauth@example.com"},
            )

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 200

    async def test_delete_account_oauth_wrong_email(
        self, async_client: AsyncClient, mock_oauth_user
    ):
        """OAuth-only user deletion with wrong email returns 400."""
        from app.api.dependencies import get_current_active_user
        from app.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_oauth_user

        with patch("app.api.v1.users.check_rate_limit", new_callable=AsyncMock):
            response = await async_client.request(
                "DELETE",
                "/api/v1/users/me",
                json={"email": "wrong@example.com"},
            )

        app.dependency_overrides.pop(get_current_active_user, None)

        assert response.status_code == 400

    async def test_delete_account_unauthenticated(self, async_client: AsyncClient):
        """Unauthenticated deletion returns 401."""
        response = await async_client.request(
            "DELETE",
            "/api/v1/users/me",
            json={"password": "any"},
        )
        assert response.status_code == 401
