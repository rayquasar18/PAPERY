"""User profile service — business logic for profile management.

Handles profile viewing, editing, avatar management, and account deletion.
Delegates data access to ``UserRepository`` following the AuthService pattern.

Usage:
    service = UserService(db)
    profile = await service.get_profile(user)
"""

from __future__ import annotations

import importlib
import io
import logging

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, UnauthorizedError
from app.core.security import invalidate_all_user_sessions, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import DeleteAccountRequest, UserProfileRead, UserProfileUpdate

logger = logging.getLogger(__name__)

# Import the minio client module by string to avoid name collision with the
# module-level ``client`` singleton exported from ``app.infra.minio.__init__``.
# Using importlib ensures we always get the live module (with the initialized
# client singleton), not a stale reference captured at import time.
_minio_client_module = importlib.import_module("app.infra.minio.client")


def _get_presigned_url(object_name: str) -> str:
    """Thin wrapper around minio presigned_get_url — patchable in tests."""
    return _minio_client_module.presigned_get_url(object_name)


class UserService:
    """Class-based user service — one instance per request lifecycle.

    Constructor accepts an ``AsyncSession``; all methods use the same
    ``UserRepository`` instance created at construction time.

    Example::

        service = UserService(db)
        profile = await service.get_profile(user)
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db: AsyncSession = db
        self._user_repo: UserRepository = UserRepository(db)

    async def get_profile(self, user: User) -> UserProfileRead:
        """Build full user profile with computed fields.

        Loads oauth_accounts eagerly and generates presigned avatar URL.
        """
        # Reload user with oauth_accounts eagerly loaded
        user_with_oauth = await self._user_repo.get_with_oauth_accounts(uuid=user.uuid)
        if user_with_oauth is None:
            # Shouldn't happen — user just authenticated. Defensive check.
            from app.core.exceptions import NotFoundError
            raise NotFoundError(detail="User not found")

        # Generate presigned avatar URL if avatar exists
        avatar_presigned: str | None = None
        if user_with_oauth.avatar_url:
            try:
                avatar_presigned = _get_presigned_url(user_with_oauth.avatar_url)
            except Exception:
                logger.warning(
                    "Failed to generate presigned URL for avatar: %s",
                    user_with_oauth.avatar_url,
                    exc_info=True,
                )

        # Build response with computed fields
        return UserProfileRead(
            uuid=user_with_oauth.uuid,
            email=user_with_oauth.email,
            display_name=user_with_oauth.display_name,
            avatar_url=avatar_presigned,
            is_verified=user_with_oauth.is_verified,
            is_superuser=user_with_oauth.is_superuser,
            created_at=user_with_oauth.created_at,
            tier_name="free",  # Placeholder until Phase 6
            has_password=user_with_oauth.hashed_password is not None,
            oauth_providers=[acc.provider for acc in user_with_oauth.oauth_accounts],
        )

    async def update_profile(self, user: User, data: UserProfileUpdate) -> User:
        """Update user profile fields.

        Currently only display_name is editable (D-13).
        Strips leading/trailing whitespace before saving.
        """
        if data.display_name is not None:
            stripped = data.display_name.strip()
            if len(stripped) < 2:
                raise BadRequestError(detail="Display name must be at least 2 characters after trimming whitespace")
            user.display_name = stripped

        return await self._user_repo.update(user)

    # Allowed MIME types and max file size
    _ALLOWED_MIME_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}
    _MAX_FILE_SIZE: int = 2 * 1024 * 1024  # 2MB
    _AVATAR_SIZE: tuple[int, int] = (200, 200)
    _THUMB_SIZE: tuple[int, int] = (50, 50)
    _WEBP_QUALITY: int = 85

    async def upload_avatar(
        self,
        user: User,
        file_data: bytes,
        content_type: str,
    ) -> tuple[str, str]:
        """Process and upload avatar image to MinIO.

        Pipeline: validate MIME + size -> Pillow open -> resize 200x200 ->
        convert WebP -> resize 50x50 -> convert WebP -> upload both -> update user.

        Returns:
            Tuple of (presigned_main_url, presigned_thumb_url).

        Raises:
            BadRequestError: If file type, size, or image format is invalid.
        """
        # 1. Validate MIME type
        if content_type not in self._ALLOWED_MIME_TYPES:
            raise BadRequestError(
                detail=f"Invalid file type: {content_type}. Allowed: JPEG, PNG, WebP"
            )

        # 2. Validate file size
        if len(file_data) > self._MAX_FILE_SIZE:
            raise BadRequestError(
                detail=f"File size {len(file_data)} exceeds 2MB limit"
            )

        # 3. Open with Pillow (secondary validation — rejects non-image data)
        # NOTE: Pillow processing is CPU-bound but acceptable for ≤2MB avatars.
        # For production scaling with high upload volume, wrap in run_in_executor.
        try:
            img = Image.open(io.BytesIO(file_data))
            img.verify()  # Verify integrity
            img = Image.open(io.BytesIO(file_data))  # Re-open after verify
        except (UnidentifiedImageError, Exception) as exc:
            raise BadRequestError(detail="Invalid image file") from exc

        # 4. Convert to RGB if necessary (e.g., RGBA PNG → RGB for WebP)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        # 5. Resize to 200x200 (center-crop to exact square)
        main_img = ImageOps.fit(img, self._AVATAR_SIZE, Image.LANCZOS)
        main_buffer = io.BytesIO()
        main_img.save(main_buffer, format="WebP", quality=self._WEBP_QUALITY)
        main_bytes = main_buffer.getvalue()

        # 6. Resize to 50x50 thumbnail
        thumb_img = ImageOps.fit(img, self._THUMB_SIZE, Image.LANCZOS)
        thumb_buffer = io.BytesIO()
        thumb_img.save(thumb_buffer, format="WebP", quality=self._WEBP_QUALITY)
        thumb_bytes = thumb_buffer.getvalue()

        # 7. Upload both to MinIO
        main_path = f"avatars/{user.uuid}/avatar.webp"
        thumb_path = f"avatars/{user.uuid}/avatar_thumb.webp"
        await _minio_client_module.upload_file(main_path, main_bytes, "image/webp")
        await _minio_client_module.upload_file(thumb_path, thumb_bytes, "image/webp")

        # 8. Update user record
        user.avatar_url = main_path
        await self._user_repo.update(user)

        # 9. Generate presigned URLs for response
        main_url = _minio_client_module.presigned_get_url(main_path)
        thumb_url = _minio_client_module.presigned_get_url(thumb_path)

        logger.info("Avatar uploaded for user %s", user.uuid)
        return main_url, thumb_url

    async def remove_avatar(self, user: User) -> None:
        """Remove avatar from MinIO and clear user's avatar_url.

        Raises:
            BadRequestError: If user has no avatar.
        """
        if not user.avatar_url:
            raise BadRequestError(detail="No avatar to remove")

        # Delete both sizes from MinIO
        main_path = f"avatars/{user.uuid}/avatar.webp"
        thumb_path = f"avatars/{user.uuid}/avatar_thumb.webp"

        try:
            await _minio_client_module.delete_file(main_path)
            await _minio_client_module.delete_file(thumb_path)
        except Exception:
            logger.warning("Failed to delete avatar files from MinIO for user %s", user.uuid, exc_info=True)

        # Clear avatar_url on user record
        user.avatar_url = None
        await self._user_repo.update(user)
        logger.info("Avatar removed for user %s", user.uuid)

    async def delete_account(self, user: User, confirmation: DeleteAccountRequest) -> None:
        """Soft-delete user account after verification.

        For local users: verifies password. For OAuth-only users: verifies email.
        Sets is_active=False, sets deleted_at, invalidates all sessions.

        Raises:
            UnauthorizedError: If password verification fails.
            BadRequestError: If email confirmation doesn't match (OAuth-only).
        """
        # 1. Verify confirmation
        if user.hashed_password is not None:
            # Local user — verify password
            if confirmation.password is None:
                raise BadRequestError(detail="Password required for account deletion")
            if not verify_password(confirmation.password, user.hashed_password):
                raise UnauthorizedError(detail="Incorrect password")
        else:
            # OAuth-only user — verify email
            if confirmation.email is None:
                raise BadRequestError(detail="Email confirmation required for OAuth account deletion")
            if confirmation.email.lower().strip() != user.email.lower():
                raise BadRequestError(detail="Email does not match account email")

        # 2. Deactivate account
        user.is_active = False
        await self._user_repo.soft_delete(user)  # Sets deleted_at + commits

        # 3. Invalidate all sessions in Redis
        await invalidate_all_user_sessions(user.uuid)  # UUID object, not str

        logger.info("Account deleted (soft) for user %s", user.uuid)
