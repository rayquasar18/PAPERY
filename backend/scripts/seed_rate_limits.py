"""Seed default rate limit rules into the database.

Creates sensible default rules (tier_id=NULL, apply to all tiers) for
common endpoints. Idempotent — skips rules that already exist.

Usage:
    cd backend && python -m scripts.seed_rate_limits
"""

import asyncio
import logging
import sys

from app.core.db.session import async_session_factory, init, shutdown
from app.models.rate_limit_rule import RateLimitRule
from app.repositories.rate_limit_rule_repository import RateLimitRuleRepository

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Default rate limit rules (tier_id=NULL → applies to all tiers)
DEFAULT_RULES = [
    {
        "endpoint_pattern": "auth:login",
        "max_requests": 10,
        "window_seconds": 60,
        "description": "Login attempts — 10 per minute",
    },
    {
        "endpoint_pattern": "auth:register",
        "max_requests": 5,
        "window_seconds": 60,
        "description": "Registration — 5 per minute",
    },
    {
        "endpoint_pattern": "auth:password-reset",
        "max_requests": 3,
        "window_seconds": 300,
        "description": "Password reset requests — 3 per 5 minutes",
    },
    {
        "endpoint_pattern": "auth:change-password",
        "max_requests": 5,
        "window_seconds": 60,
        "description": "Password change — 5 per minute",
    },
    {
        "endpoint_pattern": "documents:upload",
        "max_requests": 20,
        "window_seconds": 60,
        "description": "Document upload — 20 per minute",
    },
]


async def main() -> None:
    """Seed default rate limit rules."""
    await init()

    async with async_session_factory() as session:
        repo = RateLimitRuleRepository(session)
        created = 0

        for rule_data in DEFAULT_RULES:
            # Check if rule already exists (default rule, tier_id=NULL)
            existing = await repo.find_rule(
                tier_id=None,
                endpoint_pattern=rule_data["endpoint_pattern"],
            )
            if existing is not None:
                logger.info("Rule already exists: %s — skipping", rule_data["endpoint_pattern"])
                continue

            rule = RateLimitRule(
                tier_id=None,
                endpoint_pattern=rule_data["endpoint_pattern"],
                max_requests=rule_data["max_requests"],
                window_seconds=rule_data["window_seconds"],
                description=rule_data["description"],
            )
            await repo.create(rule)
            created += 1
            logger.info("Created rule: %s", rule_data["endpoint_pattern"])

        logger.info("Rate limit seeding complete: %d new rules created", created)

    await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error("Failed to seed rate limit rules: %s", e)
        sys.exit(1)
