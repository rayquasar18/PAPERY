"""Generic base repository with async CRUD operations.

All concrete repositories inherit from ``BaseRepository[ModelType]``.
Soft-delete filtering is applied automatically when the model uses
``SoftDeleteMixin``.
"""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import UTC, datetime
from typing import Generic, TypeVar

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
    async def get_by_id(self, id: int) -> ModelType | None:  # noqa: A002
        """Fetch a single record by internal integer PK (soft-delete aware)."""
        stmt = select(self._model).where(self._model.id == id)
        stmt = self._not_deleted(stmt)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_uuid(self, uuid: uuid_pkg.UUID) -> ModelType | None:
        """Fetch a single record by public UUID (soft-delete aware).

        Only works for models that include ``UUIDMixin``.
        """
        stmt = select(self._model).where(self._model.uuid == uuid)  # type: ignore[attr-defined]
        stmt = self._not_deleted(stmt)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

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
