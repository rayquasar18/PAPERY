"""Bootstrap script — create the first superuser.

Reads ADMIN_EMAIL and ADMIN_PASSWORD from environment / .env config
and creates the initial superuser account if it does not already exist.

Usage:
    cd backend && uv run python -m scripts.create_first_superuser
"""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Initialize database, create superuser, then shut down."""
    from app.core.db import session as db_session
    from app.services.auth_service import create_first_superuser

    await db_session.init()
    try:
        async for session in db_session.get_session():
            await create_first_superuser(session)
            logger.info("Bootstrap superuser check complete.")
            break
    finally:
        await db_session.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        sys.exit(1)
    except Exception:
        logger.exception("Failed to bootstrap superuser.")
        sys.exit(1)
