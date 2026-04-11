"""User-specific repository — data access for the User model.

Extracted from ``auth_service.py`` to separate pure data access
(SELECT/INSERT queries) from business logic (validation, exceptions).

Generic lookups (by id, uuid, email, etc.) are handled by
``BaseRepository.get(**filters)`` — this repository only adds
domain-specific factory methods.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
        is_active: bool = True,
        is_verified: bool = False,
        is_superuser: bool = False,
    ) -> User:
        """Create and persist a new User record.

        Returns the refreshed User instance with database-generated fields
        (id, uuid, created_at, etc.) populated.
        """
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            is_active=is_active,
            is_verified=is_verified,
            is_superuser=is_superuser,
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
