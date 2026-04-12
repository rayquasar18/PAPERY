"""User-specific repository — data access for the User model.

Extracted from ``auth_service.py`` to separate pure data access
(SELECT/INSERT queries) from business logic (validation, exceptions).

Generic lookups (by id, uuid, email, etc.) are handled by
``BaseRepository.get(**filters)`` — this repository only adds
domain-specific factory methods.
"""

from __future__ import annotations

import uuid as uuid_pkg
from typing import Any

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tier import Tier
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model with domain-specific factory methods.

    Generic lookups are inherited from ``BaseRepository``::

        await repo.get(email="user@example.com")
        await repo.get(uuid=some_uuid)
        await repo.get(id=1)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def create_user(
        self,
        *,
        email: str,
        hashed_password: str | None,
        status: str = "active",
        is_verified: bool = False,
        is_superuser: bool = False,
        tier_id: int | None = None,
    ) -> User:
        """Create and persist a new User record.

        Returns the refreshed User instance with database-generated fields
        (id, uuid, created_at, etc.) populated.
        """
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            status=status,
            is_verified=is_verified,
            is_superuser=is_superuser,
            tier_id=tier_id,
        )
        return await self.create(user)

    async def get_with_oauth_accounts(self, **filters: Any) -> User | None:
        """Fetch a single user with oauth_accounts eagerly loaded.

        Uses ``selectinload`` to avoid ``MissingGreenlet`` errors in async
        SQLAlchemy when accessing the ``oauth_accounts`` relationship.

        Usage::

            user = await repo.get_with_oauth_accounts(uuid=some_uuid)
            providers = [acc.provider for acc in user.oauth_accounts]
        """
        stmt = select(User).options(selectinload(User.oauth_accounts))
        for field, value in filters.items():
            stmt = stmt.where(getattr(User, field) == value)
        stmt = self._not_deleted(stmt)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

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
        """Search users with filtering, pagination, and sorting.

        Returns a tuple of (items, total_count) for admin user listing.

        Supports:
        - q: partial match on email or display_name (ILIKE)
        - status: exact match on status column
        - tier_uuid: filter by tier UUID (joins Tier table)
        - is_verified: exact bool filter
        - is_superuser: exact bool filter
        - Pagination: page/per_page
        - Sorting: by created_at or email, asc/desc
        """
        stmt = select(User)
        count_stmt = select(func.count(User.id))

        # Apply soft-delete filter
        stmt = self._not_deleted(stmt)
        count_stmt = self._not_deleted(count_stmt)

        # Text search (ILIKE on email or display_name)
        if q:
            pattern = f"%{q}%"
            search_filter = or_(
                User.email.ilike(pattern),
                User.display_name.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        # Status filter
        if status is not None:
            stmt = stmt.where(User.status == status)
            count_stmt = count_stmt.where(User.status == status)

        # Tier UUID filter (requires join)
        if tier_uuid is not None:
            stmt = stmt.join(Tier, User.tier_id == Tier.id).where(Tier.uuid == tier_uuid)
            count_stmt = count_stmt.join(Tier, User.tier_id == Tier.id).where(Tier.uuid == tier_uuid)

        # Boolean filters
        if is_verified is not None:
            stmt = stmt.where(User.is_verified == is_verified)
            count_stmt = count_stmt.where(User.is_verified == is_verified)

        if is_superuser is not None:
            stmt = stmt.where(User.is_superuser == is_superuser)
            count_stmt = count_stmt.where(User.is_superuser == is_superuser)

        # Sorting
        sort_column = getattr(User, sort_by, User.created_at)
        order_func = desc if sort_order == "desc" else asc
        stmt = stmt.order_by(order_func(sort_column))

        # Pagination
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)

        # Execute both queries
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        return items, total
