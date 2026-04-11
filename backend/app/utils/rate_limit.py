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
