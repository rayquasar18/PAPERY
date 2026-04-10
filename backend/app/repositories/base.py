"""Generic base repository with async CRUD operations.

All concrete repositories inherit from ``BaseRepository[ModelType]``.
Soft-delete filtering is applied automatically when the model uses
``SoftDeleteMixin``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async repository providing common CRUD operations.

    Parameters
    ----------
    model:
        The SQLAlchemy model class this repository manages.
    session:
        An async database session (one per request).
    """

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _has_soft_delete(self) -> bool:
        """Return True if the model has a ``deleted_at`` column."""
        return hasattr(self._model, "deleted_at")

    def _not_deleted(self, stmt):  # noqa: ANN001, ANN202
        """Append ``deleted_at IS NULL`` filter when applicable."""
        if self._has_soft_delete():
            stmt = stmt.where(self._model.deleted_at.is_(None))  # type: ignore[union-attr]
        return stmt

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    async def get(self, **filters: Any) -> ModelType | None:
        """Fetch a single record matching all filters (soft-delete aware).

        Usage examples::

            await repo.get(id=1)
            await repo.get(uuid=some_uuid)
            await repo.get(email="user@example.com")

        Raises ``AttributeError`` if a filter key does not correspond to a
        column on the model — callers must only use valid column names.
        """
        stmt = select(self._model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self._model, field) == value)
        stmt = self._not_deleted(stmt)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        **filters: Any,
    ) -> list[ModelType]:
        """Fetch multiple records with pagination and optional filters (soft-delete aware).

        Usage examples::

            await repo.get_multi(skip=0, limit=20)
            await repo.get_multi(is_active=True, skip=0, limit=50)
        """
        stmt = select(self._model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self._model, field) == value)
        stmt = self._not_deleted(stmt)
        stmt = stmt.offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    async def create(self, instance: ModelType) -> ModelType:
        """Add a new record to the session, commit, and refresh."""
        self._session.add(instance)
        await self._session.commit()
        await self._session.refresh(instance)
        return instance

    async def update(self, instance: ModelType) -> ModelType:
        """Commit pending changes on an existing record and refresh."""
        await self._session.commit()
        await self._session.refresh(instance)
        return instance

    async def soft_delete(self, instance: ModelType) -> ModelType:
        """Mark a record as deleted by setting ``deleted_at``."""
        if not self._has_soft_delete():
            msg = f"{self._model.__name__} does not support soft delete"
            raise TypeError(msg)
        instance.deleted_at = datetime.now(UTC)  # type: ignore[attr-defined]
        await self._session.commit()
        await self._session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Hard-delete a record permanently.

        Use with caution — this removes the row from the database.
        Prefer ``soft_delete`` for most use cases.
        """
        await self._session.delete(instance)
        await self._session.commit()
