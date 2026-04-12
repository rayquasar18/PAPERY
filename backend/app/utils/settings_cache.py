"""Redis-backed cache for system settings.

Caches individual setting values and full settings map in Redis cache_client (db=0)
with a 5-minute TTL. Explicit invalidation on admin PATCH ensures
settings update within one request cycle.

Usage:
    value = await get_cached_setting("maintenance_mode")
    if value is None:
        value = fetch_from_db(...)
        await set_cached_setting("maintenance_mode", value)
"""

from __future__ import annotations

import json
import logging

from app.infra.redis import client as redis_client

logger = logging.getLogger(__name__)

SETTINGS_CACHE_TTL: int = 300  # 5 minutes
SETTINGS_CACHE_KEY_PREFIX: str = "settings:"
SETTINGS_ALL_CACHE_KEY: str = "settings:__all__"


async def get_cached_setting(key: str) -> dict | None:
    """Read a single setting value from Redis cache. Returns None on miss."""
    if redis_client.cache_client is None:
        logger.warning("Redis cache_client not initialized — skipping cache read")
        return None

    cache_key = f"{SETTINGS_CACHE_KEY_PREFIX}{key}"
    raw = await redis_client.cache_client.get(cache_key)
    if raw is None:
        return None
    return json.loads(raw)


async def set_cached_setting(key: str, value: dict) -> None:
    """Write a single setting value to cache with TTL."""
    if redis_client.cache_client is None:
        logger.warning("Redis cache_client not initialized — skipping cache write")
        return

    cache_key = f"{SETTINGS_CACHE_KEY_PREFIX}{key}"
    await redis_client.cache_client.setex(cache_key, SETTINGS_CACHE_TTL, json.dumps(value))


async def invalidate_setting_cache(key: str) -> None:
    """Remove a single setting from cache + invalidate the all-settings cache."""
    if redis_client.cache_client is None:
        logger.warning("Redis cache_client not initialized — skipping cache invalidation")
        return

    cache_key = f"{SETTINGS_CACHE_KEY_PREFIX}{key}"
    await redis_client.cache_client.delete(cache_key)
    await redis_client.cache_client.delete(SETTINGS_ALL_CACHE_KEY)
    logger.debug("Invalidated settings cache for key=%s", key)


async def get_cached_all_settings() -> dict | None:
    """Read the full settings map from cache. Returns None on miss."""
    if redis_client.cache_client is None:
        return None

    raw = await redis_client.cache_client.get(SETTINGS_ALL_CACHE_KEY)
    if raw is None:
        return None
    return json.loads(raw)


async def set_cached_all_settings(settings_map: dict) -> None:
    """Cache the full settings map with TTL."""
    if redis_client.cache_client is None:
        return

    await redis_client.cache_client.setex(
        SETTINGS_ALL_CACHE_KEY, SETTINGS_CACHE_TTL, json.dumps(settings_map)
    )
