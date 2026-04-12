"""Rate limiting utility using Redis sliding window counter.

.. deprecated::
    IP-based rate limiting on public endpoints has been migrated to slowapi
    (see ``app.middleware.rate_limit``). This module is retained **only** for
    user-UUID-keyed limits on authenticated endpoints where slowapi's
    decorator model does not integrate cleanly with FastAPI's DI.

    Do NOT add new IP-based rate limit calls here — use ``@limiter.limit()``
    from ``app.middleware.rate_limit`` instead.

Uses a simple INCR + EXPIRE strategy per key. The key encodes
the resource (endpoint) and the caller identity (IP or user UUID).

Usage:
    await check_rate_limit(f"auth:change-password:{user.uuid}", max_requests=5, window_seconds=60)
"""

import logging

from app.core.exceptions import RateLimitedError
from app.infra.redis import client as redis_client
from app.utils.rate_limit_rule_cache import (
    get_cached_rate_limit_rule,
)

logger = logging.getLogger(__name__)


async def check_rate_limit(
    key: str,
    max_requests: int,
    window_seconds: int,
) -> None:
    """Enforce a rate limit using Redis INCR + EXPIRE.

    Increments a counter for *key*. On the first hit the key is given
    a TTL of *window_seconds*. If the counter exceeds *max_requests*
    a ``RateLimitedError`` (HTTP 429) is raised with a ``Retry-After``
    header.

    Args:
        key: Redis key — should include the endpoint + caller identity.
        max_requests: Maximum allowed requests within the window.
        window_seconds: Window duration in seconds.

    Raises:
        RuntimeError: If the Redis rate_limit client is not initialized.
        RateLimitedError: If the caller has exceeded the limit.
    """
    if redis_client.rate_limit_client is None:
        raise RuntimeError("Redis rate_limit client not initialized")

    count = await redis_client.rate_limit_client.incr(key)
    if count == 1:
        await redis_client.rate_limit_client.expire(key, window_seconds)

    if count > max_requests:
        ttl = await redis_client.rate_limit_client.ttl(key)
        if ttl < 0:
            ttl = window_seconds
        raise RateLimitedError(
            detail=f"Too many requests. Retry after {ttl} seconds.",
            error_code="RATE_LIMITED",
            headers={"Retry-After": str(ttl)},
        )


async def check_rate_limit_dynamic(
    key: str,
    tier_id: int | None,
    endpoint: str,
    fallback_max_requests: int = 60,
    fallback_window_seconds: int = 60,
) -> None:
    """Enforce a rate limit with dynamic DB-backed rules.

    Lookup priority (D-17):
    1. Tier-specific rule from cache/DB
    2. Default rule (tier_id=NULL) from cache/DB
    3. Hardcoded fallback values

    This extends the existing check_rate_limit() with configurable,
    admin-managed rules. The original function is preserved for cases
    where hardcoded limits are intentional (e.g., anti-abuse).

    Args:
        key: Redis key — should include endpoint + caller identity.
        tier_id: The user's tier ID (from user.tier_id). None for unauthenticated.
        endpoint: Endpoint pattern to match rules (e.g., "auth:login").
        fallback_max_requests: Hardcoded fallback if no DB rule exists.
        fallback_window_seconds: Hardcoded fallback window.
    """
    max_requests = fallback_max_requests
    window_seconds = fallback_window_seconds

    # Try tier-specific rule from cache
    if tier_id is not None:
        cached = await get_cached_rate_limit_rule(tier_id, endpoint)
        if cached is not None:
            max_requests = cached["max_requests"]
            window_seconds = cached["window_seconds"]
        else:
            # Try default rule from cache
            cached_default = await get_cached_rate_limit_rule(None, endpoint)
            if cached_default is not None:
                max_requests = cached_default["max_requests"]
                window_seconds = cached_default["window_seconds"]
    else:
        # No tier — try default rule
        cached_default = await get_cached_rate_limit_rule(None, endpoint)
        if cached_default is not None:
            max_requests = cached_default["max_requests"]
            window_seconds = cached_default["window_seconds"]

    # Delegate to existing check_rate_limit with resolved values
    await check_rate_limit(key, max_requests, window_seconds)
