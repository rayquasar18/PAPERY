"""Shared pytest fixtures for all tests."""

import os
import uuid as uuid_pkg
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure test environment before any app imports
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-minimum-32-characters-long!!")


@pytest.fixture
async def async_client():
    """Create an async test client for the FastAPI app.

    Patches extension init/shutdown to avoid requiring real services,
    and overrides the get_session dependency to return a mock session.
    """
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.add = MagicMock()

    async def _mock_get_session():
        yield mock_session

    with (
        patch("app.core.db.session.init", new_callable=AsyncMock),
        patch("app.core.db.session.shutdown", new_callable=AsyncMock),
        patch("app.infra.redis.client.init", new_callable=AsyncMock),
        patch("app.infra.redis.client.shutdown", new_callable=AsyncMock),
        patch("app.infra.minio.client.init", new_callable=MagicMock),
        patch("app.infra.minio.client.shutdown", new_callable=MagicMock),
    ):
        from app.core.db.session import get_session
        from app.main import app

        app.dependency_overrides[get_session] = _mock_get_session

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

        app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def mock_user():
    """Create a mock User object for testing."""
    user = MagicMock()
    user.id = 1
    user.uuid = uuid_pkg.uuid4()
    user.email = "test@example.com"
    user.hashed_password = "$2b$12$mock_hash"
    user.display_name = "Test User"
    user.avatar_url = None
    user.is_active = True
    user.is_verified = True
    user.is_superuser = False
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = None
    return user


@pytest.fixture
def mock_db_session():
    """Create a mock AsyncSession for testing service layer."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    return session
