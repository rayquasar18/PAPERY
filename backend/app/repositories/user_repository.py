"""User-specific repository — data access for the User model.

Extracted from ``auth_service.py`` to separate pure data access
(SELECT/INSERT queries) from business logic (validation, exceptions).
"""

from __future__ import annotations

import uuid as uuid_pkg

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model with domain-specific query methods."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a non-deleted user by email (case-insensitive).

        Returns None if no matching user exists.
        """
        stmt = select(User).where(
            User.email == email.lower(),
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_uuid(self, uuid: uuid_pkg.UUID) -> User | None:
        """Fetch a non-deleted user by public UUID.

        Returns None if the user does not exist or is soft-deleted.
        This is the primary lookup used by authentication dependencies.
        """
        stmt = select(User).where(
            User.uuid == uuid,
            User.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

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
