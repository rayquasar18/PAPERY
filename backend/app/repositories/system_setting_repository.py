"""SystemSetting repository — data access for system configuration."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_setting import SystemSetting
from app.repositories.base import BaseRepository


class SystemSettingRepository(BaseRepository[SystemSetting]):
    """Repository for SystemSetting model.

    Generic lookups inherited from BaseRepository:
        await repo.get(key="maintenance_mode")
        await repo.get(uuid=some_uuid)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SystemSetting, session)

    async def get_by_category(self, category: str) -> list[SystemSetting]:
        """Fetch all settings in a given category."""
        stmt = select(SystemSetting).where(SystemSetting.category == category)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(self) -> list[SystemSetting]:
        """Fetch all system settings, ordered by category then key."""
        stmt = select(SystemSetting).order_by(
            SystemSetting.category, SystemSetting.key
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(self, key: str, value: dict, category: str, description: str | None = None) -> SystemSetting:
        """Create or update a system setting by key.

        Used during seeding — if key exists, update value; if not, create.
        """
        existing = await self.get(key=key)
        if existing is not None:
            existing.value = value
            if description is not None:
                existing.description = description
            return await self.update(existing)

        setting = SystemSetting(
            key=key,
            value=value,
            category=category,
            description=description,
        )
        return await self.create(setting)
