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
        patch("app.core.db.session.init", new_callable=AsyncMock),
        patch("app.core.db.session.shutdown", new_callable=AsyncMock),
        patch("app.infra.redis.client.init", new_callable=AsyncMock),
        patch("app.infra.redis.client.shutdown", new_callable=AsyncMock),
        patch("app.infra.minio.client.init", new_callable=MagicMock),
        patch("app.infra.minio.client.shutdown", new_callable=MagicMock),
    ):
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
