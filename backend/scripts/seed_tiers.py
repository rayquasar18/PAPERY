"""Seed default tiers into the database.

Usage: python -m scripts.seed_tiers
Must be run from the backend/ directory with the venv active.
"""

import asyncio
import logging

from sqlalchemy import select

from app.core.db.session import async_session_factory, init, shutdown
from app.models.tier import Tier

logger = logging.getLogger(__name__)

DEFAULT_TIERS = [
    {
        "name": "Free",
        "slug": "free",
        "description": "Basic access with limited features",
        "max_projects": 3,
        "max_docs_per_project": 10,
        "max_fixes_monthly": 20,
        "max_file_size_mb": 10,
        "allowed_models": ["gpt-4o-mini"],
        "feature_flags": {
            "can_export_pdf": False,
            "can_translate": False,
            "priority_support": False,
        },
        "stripe_price_id": None,
    },
    {
        "name": "Pro",
        "slug": "pro",
        "description": "Advanced features for professionals",
        "max_projects": 20,
        "max_docs_per_project": 100,
        "max_fixes_monthly": 500,
        "max_file_size_mb": 50,
        "allowed_models": ["gpt-4o", "gpt-4o-mini", "claude-sonnet"],
        "feature_flags": {
            "can_export_pdf": True,
            "can_translate": True,
            "priority_support": False,
        },
        "stripe_price_id": None,  # Set via admin or env after Stripe product creation
    },
    {
        "name": "Ultra",
        "slug": "ultra",
        "description": "Unlimited access with all features",
        "max_projects": -1,
        "max_docs_per_project": -1,
        "max_fixes_monthly": -1,
        "max_file_size_mb": 100,
        "allowed_models": ["*"],
        "feature_flags": {
            "can_export_pdf": True,
            "can_translate": True,
            "priority_support": True,
        },
        "stripe_price_id": None,  # Set via admin or env after Stripe product creation
    },
]


async def seed_tiers() -> None:
    """Insert default tiers if they don't already exist (idempotent)."""
    await init()

    async with async_session_factory() as session:
        for tier_data in DEFAULT_TIERS:
            existing = await session.execute(
                select(Tier).where(Tier.slug == tier_data["slug"])
            )
            if existing.scalar_one_or_none() is not None:
                logger.info("Tier '%s' already exists — skipping", tier_data["slug"])
                continue

            tier = Tier(**tier_data)
            session.add(tier)
            logger.info("Created tier: %s", tier_data["slug"])

        await session.commit()

    await shutdown()
    logger.info("Tier seeding complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_tiers())
