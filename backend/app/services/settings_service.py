"""System settings service — business logic for runtime configuration.

Reads settings from Redis cache first, falls back to DB. Validates
values against the SETTINGS_REGISTRY allowlist before writing.

Usage:
    service = SettingsService(db)
    all_settings = await service.get_all_settings()
    await service.update_setting("maintenance_mode", True)
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.system_setting import SystemSetting
from app.repositories.system_setting_repository import SystemSettingRepository
from app.schemas.system_setting import (
    SETTINGS_REGISTRY,
    SystemSettingRead,
    validate_setting_value,
)
from app.utils.settings_cache import (
    get_cached_all_settings,
    get_cached_setting,
    invalidate_setting_cache,
    set_cached_all_settings,
    set_cached_setting,
)

logger = logging.getLogger(__name__)


class SettingsService:
    """Class-based settings service — one instance per request lifecycle."""

    def __init__(self, db: AsyncSession) -> None:
        self._db: AsyncSession = db
        self._repo: SystemSettingRepository = SystemSettingRepository(db)

    async def get_all_settings(self) -> dict[str, list[SystemSettingRead]]:
        """Get all settings grouped by category. Uses cache when available."""
        # Try cache first
        cached = await get_cached_all_settings()
        if cached is not None:
            return cached

        # Cache miss — load from DB
        settings = await self._repo.get_all()

        # Group by category
        grouped: dict[str, list[SystemSettingRead]] = {}
        for s in settings:
            read = SystemSettingRead.model_validate(s)
            grouped.setdefault(s.category, []).append(read)

        # Serialize for cache (convert Pydantic models to dicts)
        cache_data = {
            cat: [item.model_dump(mode="json") for item in items]
            for cat, items in grouped.items()
        }
        await set_cached_all_settings(cache_data)

        return grouped

    async def get_setting(self, key: str) -> SystemSetting:
        """Get a single setting by key. Raises NotFoundError if missing."""
        if key not in SETTINGS_REGISTRY:
            raise BadRequestError(detail=f"Unknown setting key: '{key}'")

        setting = await self._repo.get(key=key)
        if setting is None:
            raise NotFoundError(detail=f"Setting '{key}' not found in database. Run seed script.")
        return setting

    async def get_setting_value(self, key: str) -> Any:
        """Get the unwrapped value of a setting. Uses cache."""
        # Try cache
        cached = await get_cached_setting(key)
        if cached is not None:
            return cached.get("v")

        setting = await self.get_setting(key)
        value = setting.value.get("v", SETTINGS_REGISTRY[key].default)

        # Cache it
        await set_cached_setting(key, setting.value)
        return value

    async def update_setting(self, key: str, value: Any) -> SystemSetting:
        """Update a setting value. Validates against registry, invalidates cache."""
        if key not in SETTINGS_REGISTRY:
            raise BadRequestError(detail=f"Unknown setting key: '{key}'")

        # Validate the value type and constraints
        try:
            validated = validate_setting_value(key, value)
        except ValueError as e:
            raise BadRequestError(detail=str(e)) from e

        setting = await self._repo.get(key=key)
        if setting is None:
            raise NotFoundError(detail=f"Setting '{key}' not found in database. Run seed script.")

        setting.value = {"v": validated}
        updated = await self._repo.update(setting)

        # Invalidate cache for this key + all-settings cache
        await invalidate_setting_cache(key)

        logger.info("System setting '%s' updated to: %s", key, validated)
        return updated

    async def seed_defaults(self) -> int:
        """Seed all settings from SETTINGS_REGISTRY if they don't exist yet.

        Returns the number of settings created.
        """
        created = 0
        for key, defn in SETTINGS_REGISTRY.items():
            existing = await self._repo.get(key=key)
            if existing is None:
                await self._repo.upsert(
                    key=key,
                    value={"v": defn.default},
                    category=defn.category,
                    description=defn.description,
                )
                created += 1
                logger.info("Seeded setting: %s = %s", key, defn.default)
        return created
