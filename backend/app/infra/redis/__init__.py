"""Redis infrastructure — three isolated namespace clients."""

from app.infra.redis.client import (
    cache_client,
    init,
    queue_client,
    rate_limit_client,
    shutdown,
)

__all__ = [
    "cache_client",
    "init",
    "queue_client",
    "rate_limit_client",
    "shutdown",
]
