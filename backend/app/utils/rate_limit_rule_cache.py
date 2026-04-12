"""Redis-backed cache for rate limit rule lookups.

Caches resolved rate limit rules per (tier_id, endpoint_pattern) in Redis
cache_client (db=0) with a 5-minute TTL. Explicit invalidation on admin
CRUD ensures rules update within one request cycle.

Usage:
    rule = await get_cached_rate_limit_rule(tier_id=1, endpoint="auth:login")
    if rule is None:
        rule = lookup_from_db(...)
        await set_cached_rate_limit_rule(tier_id=1, endpoint="auth:login", rule=rule)
"""

from __future__ import annotations

import json
import logging

from app.infra.redis import client as redis_client

logger = logging.getLogger(__name__)

RATE_RULE_CACHE_TTL: int = 300  # 5 minutes
RATE_RULE_CACHE_KEY_PREFIX: str = "rate_rule:"


def _build_cache_key(tier_id: int | None, endpoint: str) -> str:
    """Build a Redis key for a tier+endpoint combination."""
    tid = str(tier_id) if tier_id is not None else "default"
    return f"{RATE_RULE_CACHE_KEY_PREFIX}{tid}:{endpoint}"


async def get_cached_rate_limit_rule(
    tier_id: int | None, endpoint: str
) -> dict | None:
    """Read a rate limit rule from cache. Returns None on miss."""
    if redis_client.cache_client is None:
        logger.warning("Redis cache_client not initialized — skipping cache read")
        return None

    key = _build_cache_key(tier_id, endpoint)
    raw = await redis_client.cache_client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def set_cached_rate_limit_rule(
    tier_id: int | None, endpoint: str, rule: dict
) -> None:
    """Cache a rate limit rule with TTL."""
    if redis_client.cache_client is None:
        logger.warning("Redis cache_client not initialized — skipping cache write")
        return

    key = _build_cache_key(tier_id, endpoint)
    await redis_client.cache_client.setex(key, RATE_RULE_CACHE_TTL, json.dumps(rule))


async def invalidate_rate_limit_rule_cache(
    tier_id: int | None, endpoint: str
) -> None:
    """Remove a specific rule from cache."""
    if redis_client.cache_client is None:
        logger.warning("Redis cache_client not initialized — skipping cache invalidation")
        return

    key = _build_cache_key(tier_id, endpoint)
    await redis_client.cache_client.delete(key)
    logger.debug("Invalidated rate limit rule cache for tier=%s endpoint=%s", tier_id, endpoint)


async def invalidate_all_rate_limit_rule_cache() -> None:
    """Remove ALL rate limit rule cache entries.

    Uses SCAN to find all keys with the rate_rule: prefix.
    Called when admin makes broad changes (e.g., deletes a tier).
    """
    if redis_client.cache_client is None:
        return

    cursor = 0
    pattern = f"{RATE_RULE_CACHE_KEY_PREFIX}*"
    while True:
        cursor, keys = await redis_client.cache_client.scan(cursor, match=pattern, count=100)
        if keys:
            await redis_client.cache_client.delete(*keys)
        if cursor == 0:
            break
    logger.debug("Invalidated all rate limit rule cache entries")
