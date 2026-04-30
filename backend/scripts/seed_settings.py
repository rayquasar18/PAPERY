"""Seed default system settings into the database.

Reads from SETTINGS_REGISTRY and creates any missing settings.
Idempotent — safe to run multiple times.

Usage:
    cd backend && python -m scripts.seed_settings
"""

import asyncio
import logging
import sys

from app.core.db.session import async_session_factory, init, shutdown
from app.services.settings_service import SettingsService

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """Seed default system settings."""
    await init()

    async with async_session_factory() as session:
        service = SettingsService(session)
        created = await service.seed_defaults()
        logger.info("Settings seeding complete: %d new settings created", created)

    await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error("Failed to seed settings: %s", e)
        sys.exit(1)
