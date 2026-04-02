"""Smoke tests for FastAPI app startup and health endpoint (INFRA-01)."""

from httpx import AsyncClient


class TestHealthEndpoint:
    """Test the /api/v1/health endpoint."""

    async def test_health_returns_200(self, async_client: AsyncClient):
        """GET /api/v1/health should return 200 OK."""
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200

    async def test_health_returns_status_ok(self, async_client: AsyncClient):
        """Health response should contain status: ok."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "ok"

    async def test_health_returns_app_name(self, async_client: AsyncClient):
        """Health response should contain app name PAPERY."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert data["app"] == "PAPERY"

    async def test_health_returns_version(self, async_client: AsyncClient):
        """Health response should contain version string."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.1.0"

    async def test_health_returns_environment(self, async_client: AsyncClient):
        """Health response should contain environment field."""
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert "environment" in data


class TestAppConfiguration:
    """Test FastAPI app configuration."""

    def test_app_title_is_papery(self):
        """App title should be PAPERY."""
        from app.main import app

        assert app.title == "PAPERY"

    def test_app_has_health_route(self):
        """App should have /api/v1/health route registered."""
        from app.main import app

        routes = [route.path for route in app.routes]
        assert "/api/v1/health" in routes

    def test_app_has_docs_in_debug_mode(self):
        """When DEBUG=true, /docs should be available."""
        from app.main import app

        assert app.docs_url is not None

    def test_app_has_cors_middleware(self):
        """App should have CORSMiddleware configured."""
        from app.main import app

        middleware_classes = [type(m).__name__ for m in getattr(app, "user_middleware", [])]
        # FastAPI wraps middleware, check via app.user_middleware
        assert any("CORS" in str(m) for m in app.user_middleware)
