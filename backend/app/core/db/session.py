"""Database session — async SQLAlchemy engine + session factory.

This is core infrastructure (not an optional extension).
Provides engine, session factory, lifecycle hooks, and a FastAPI dependency.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.configs import settings

logger = logging.getLogger(__name__)

# Module-level singletons (initialized in init())
engine = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init() -> None:
    """Initialize the async database engine and session factory."""
    global engine, async_session_factory

    engine = create_async_engine(
        settings.ASYNC_DATABASE_URI,
        pool_size=settings.POSTGRES_POOL_SIZE,
        max_overflow=settings.POSTGRES_MAX_OVERFLOW,
        pool_recycle=settings.POSTGRES_POOL_RECYCLE,
        pool_pre_ping=True,
        pool_timeout=30,
        echo=settings.DEBUG,
    )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Verify connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database engine initialized: %s", settings.POSTGRES_HOST)


async def shutdown() -> None:
    """Dispose the engine and release all connections."""
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
        logger.info("Database engine disposed")
    engine = None
    async_session_factory = None


async def get_session() -> AsyncSession:
    """Get an async session. Use as FastAPI dependency.

    Usage in routes:
        session: AsyncSession = Depends(get_session)
    """
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call db_session.init() first.")
    async with async_session_factory() as session:
        yield session  # type: ignore[misc]
