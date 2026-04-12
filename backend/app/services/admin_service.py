"""Admin service — business logic for admin user management.

Handles user search, user detail, user status changes (with ban session
invalidation), and admin user profile updates. Delegates data access to
UserRepository and TierRepository.

Usage:
    service = AdminService(db)
    users, total = await service.search_users(q="test@")
"""

from __future__ import annotations

import logging
import uuid as uuid_pkg

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import invalidate_all_user_sessions
from app.models.user import User, UserStatus
from app.repositories.tier_repository import TierRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin_user import AdminUserRead, AdminUserUpdate

logger = logging.getLogger(__name__)


class AdminService:
    """Class-based admin service — one instance per request lifecycle."""

    def __init__(self, db: AsyncSession) -> None:
        self._db: AsyncSession = db
        self._user_repo: UserRepository = UserRepository(db)
        self._tier_repo: TierRepository = TierRepository(db)

    # ------------------------------------------------------------------
    # User search & detail
    # ------------------------------------------------------------------

    async def search_users(
        self,
        *,
        q: str | None = None,
        status: str | None = None,
        tier_uuid: uuid_pkg.UUID | None = None,
        is_verified: bool | None = None,
        is_superuser: bool | None = None,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[User], int]:
        """Search users with filters and pagination. Delegates to UserRepository."""
        # Validate sort_by
        allowed_sort = {"created_at", "email"}
        if sort_by not in allowed_sort:
            sort_by = "created_at"
        if sort_order not in {"asc", "desc"}:
            sort_order = "desc"

        return await self._user_repo.search_users(
            q=q,
            status=status,
            tier_uuid=tier_uuid,
            is_verified=is_verified,
            is_superuser=is_superuser,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def get_user_by_uuid(self, user_uuid: uuid_pkg.UUID) -> User:
        """Get a single user by UUID. Raises NotFoundError if missing."""
        user = await self._user_repo.get(uuid=user_uuid)
        if user is None:
            raise NotFoundError(detail="User not found")
        return user

    # ------------------------------------------------------------------
    # User update (admin)
    # ------------------------------------------------------------------

    async def update_user(
        self, user_uuid: uuid_pkg.UUID, data: AdminUserUpdate
    ) -> User:
        """Update user fields as admin.

        Special handling:
        - status change to 'banned' triggers session invalidation (D-07)
        - tier_uuid resolves to tier_id via TierRepository
        """
        user = await self.get_user_by_uuid(user_uuid)
        old_status = user.status

        update_fields = data.model_dump(exclude_unset=True)

        # Handle tier_uuid -> tier_id resolution
        if "tier_uuid" in update_fields:
            tier_uuid_val = update_fields.pop("tier_uuid")
            if tier_uuid_val is not None:
                tier = await self._tier_repo.get(uuid=tier_uuid_val)
                if tier is None:
                    raise NotFoundError(detail="Tier not found")
                user.tier_id = tier.id
            else:
                user.tier_id = None

        # Apply remaining fields directly
        for field, value in update_fields.items():
            if hasattr(user, field):
                setattr(user, field, value)

        updated_user = await self._user_repo.update(user)

        # D-07: Ban triggers immediate session invalidation
        new_status = updated_user.status
        if new_status == UserStatus.BANNED.value and old_status != UserStatus.BANNED.value:
            await invalidate_all_user_sessions(updated_user.uuid)
            logger.info(
                "User %s banned by admin — all sessions invalidated",
                updated_user.uuid,
            )

        return updated_user

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def to_admin_user_read(user: User) -> AdminUserRead:
        """Convert a User model to AdminUserRead schema."""
        return AdminUserRead(
            uuid=user.uuid,
            email=user.email,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            status=user.status,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            tier_slug=user.tier.slug if user.tier else None,
            tier_name=user.tier.name if user.tier else None,
            stripe_customer_id=user.stripe_customer_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
