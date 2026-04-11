"""Rate limiting middleware using slowapi + Redis backend.

Provides a global ``limiter`` instance configured with Redis-backed storage
for IP-based rate limiting on public endpoints. The Redis storage URI is
built from the app's RedisConfig at import time.

User-based (UUID-keyed) rate limits continue to use the manual
``check_rate_limit()`` utility in ``app.utils.rate_limit`` because
slowapi decorators execute before FastAPI dependency injection resolves
the authenticated user.

Usage on route handlers:
    from app.middleware.rate_limit import limiter

    @router.post("/register")
    @limiter.limit("3/minute")
    async def register(request: Request, ...):
        ...
"""

from __future__ import annotations

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.configs import settings

logger = logging.getLogger(__name__)


def _build_redis_uri() -> str:
    """Build a Redis connection URI from rate-limit settings.

    The ``limits`` library (used by slowapi internally) accepts URIs
    in the format ``redis://[:password@]host:port/db``.
    """
    password_part = f":{settings.REDIS_RATE_LIMIT_PASSWORD}@" if settings.REDIS_RATE_LIMIT_PASSWORD else ""
    return (
        f"redis://{password_part}"
        f"{settings.REDIS_RATE_LIMIT_HOST}"
        f":{settings.REDIS_RATE_LIMIT_PORT}"
        f"/{settings.REDIS_RATE_LIMIT_DB}"
    )


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_build_redis_uri(),
    strategy="fixed-window",
)
