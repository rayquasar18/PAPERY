"""Tier-specific repository — data access for the Tier model.

Generic lookups (by id, uuid, slug, etc.) are handled by
``BaseRepository.get(**filters)``.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tier import Tier
from app.repositories.base import BaseRepository


class TierRepository(BaseRepository[Tier]):
    """Repository for Tier model.

    Generic lookups are inherited from ``BaseRepository``::

        await repo.get(slug="free")
        await repo.get(uuid=some_uuid)
        await repo.get_multi(skip=0, limit=20)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Tier, session)
