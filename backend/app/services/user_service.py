"""User profile service — business logic for profile management.

Handles profile viewing, editing, avatar management, and account deletion.
Delegates data access to ``UserRepository`` following the AuthService pattern.

Usage:
    service = UserService(db)
    profile = await service.get_profile(user)
"""

from __future__ import annotations

import importlib
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserProfileRead, UserProfileUpdate

logger = logging.getLogger(__name__)

# Import the minio client module by string to avoid name collision with the
# module-level ``client`` singleton exported from ``app.infra.minio.__init__``.
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
