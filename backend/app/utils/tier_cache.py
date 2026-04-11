"""Redis-backed tier data cache for fast feature flag and limit lookups.

Caches the full tier payload per user UUID in Redis cache_client (db=0)
with a 5-minute TTL. Immediate invalidation on tier change ensures
permissions update within one request cycle (D-13).

Usage:
    data = await get_cached_tier_data(str(user.uuid))
    if data is None:
        data = build_tier_data_from_db(user)
        await set_cached_tier_data(str(user.uuid), data)
"""

from __future__ import annotations

import json
import logging

from app.infra.redis import client as redis_client

logger = logging.getLogger(__name__)

TIER_CACHE_TTL: int = 300  # 5 minutes (D-12)
TIER_CACHE_KEY_PREFIX: str = "tier:user:"


async def get_cached_tier_data(user_uuid: str) -> dict | None:
    """Read tier data from Redis cache. Returns None on cache miss."""
    if redis_client.cache_client is None:
        logger.warning("Redis cache_client not initialized — skipping cache read")
        return None

    key = f"{TIER_CACHE_KEY_PREFIX}{user_uuid}"
    raw = await redis_client.cache_client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def set_cached_tier_data(user_uuid: str, tier_data: dict) -> None:
    """Write tier data to cache with 5-minute TTL."""
    if redis_client.cache_client is None:
        logger.warning("Redis cache_client not initialized — skipping cache write")
        return

    key = f"{TIER_CACHE_KEY_PREFIX}{user_uuid}"
    await redis_client.cache_client.setex(key, TIER_CACHE_TTL, json.dumps(tier_data))


async def invalidate_tier_cache(user_uuid: str) -> None:
    """Remove tier cache entry immediately on tier change (D-13).

    Called by: StripeService webhook handlers, admin tier CRUD.
    """
    if redis_client.cache_client is None:
        logger.warning("Redis cache_client not initialized — skipping cache invalidation")
        return

    key = f"{TIER_CACHE_KEY_PREFIX}{user_uuid}"
    await redis_client.cache_client.delete(key)
    logger.debug("Invalidated tier cache for user %s", user_uuid)
