"""Shared pytest fixtures for all tests."""

import os
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

    Patches extension init/shutdown to avoid requiring real services.
    """
    with (
        patch("app.extensions.ext_database.init", new_callable=AsyncMock),
        patch("app.extensions.ext_database.shutdown", new_callable=AsyncMock),
        patch("app.extensions.ext_redis.init", new_callable=AsyncMock),
        patch("app.extensions.ext_redis.shutdown", new_callable=AsyncMock),
        patch("app.extensions.ext_minio.init", new_callable=MagicMock),
        patch("app.extensions.ext_minio.shutdown", new_callable=MagicMock),
    ):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
