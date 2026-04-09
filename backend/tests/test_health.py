"""Tests for health endpoints and exception handler integration (INFRA-06, INFRA-07, INFRA-08)."""

from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient


class TestReadyEndpoint:
    """Test the /api/v1/ready deep health check."""

    async def test_ready_returns_200_when_all_healthy(self, async_client: AsyncClient):
        """GET /api/v1/ready returns 200 when all services are reachable."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        # Mock engine.connect() as async context manager
        mock_engine.connect = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(return_value=False),
            )
        )

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        mock_minio = MagicMock()
        mock_minio.list_buckets = MagicMock(return_value=[])

        with (
            patch("app.api.v1.health.db_session") as mock_db_ext,
            patch("app.api.v1.health.redis_client") as mock_redis_ext,
            patch("app.api.v1.health.minio_client") as mock_minio_ext,
        ):
            mock_db_ext.engine = mock_engine
            mock_redis_ext.cache_client = mock_redis
            mock_minio_ext.client = mock_minio

            response = await async_client.get("/api/v1/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["postgres"] == "ok"
        assert data["checks"]["redis"] == "ok"
        assert data["checks"]["minio"] == "ok"

    async def test_ready_returns_503_when_db_down(self, async_client: AsyncClient):
        """GET /api/v1/ready returns 503 when PostgreSQL is unreachable."""
        with (
            patch("app.api.v1.health.db_session") as mock_db_ext,
            patch("app.api.v1.health.redis_client") as mock_redis_ext,
            patch("app.api.v1.health.minio_client") as mock_minio_ext,
        ):
            mock_db_ext.engine = None  # Not initialized
            mock_redis_ext.cache_client = AsyncMock()
            mock_redis_ext.cache_client.ping = AsyncMock(return_value=True)
            mock_minio_ext.client = MagicMock()
            mock_minio_ext.client.list_buckets = MagicMock(return_value=[])

            response = await async_client.get("/api/v1/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data["checks"]["postgres"]

    async def test_ready_returns_503_when_redis_down(self, async_client: AsyncClient):
        """GET /api/v1/ready returns 503 when Redis is unreachable."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_engine.connect = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_conn),
                __aexit__=AsyncMock(return_value=False),
            )
        )

        with (
            patch("app.api.v1.health.db_session") as mock_db_ext,
            patch("app.api.v1.health.redis_client") as mock_redis_ext,
            patch("app.api.v1.health.minio_client") as mock_minio_ext,
        ):
            mock_db_ext.engine = mock_engine
            mock_redis_ext.cache_client = None  # Not initialized
            mock_minio_ext.client = MagicMock()
            mock_minio_ext.client.list_buckets = MagicMock(return_value=[])

            response = await async_client.get("/api/v1/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data["checks"]["redis"]


class TestExceptionHandlerIntegration:
    """Test exception handlers return consistent ErrorResponse format."""

    async def test_404_returns_error_response_format(self, async_client: AsyncClient):
        """Hitting a non-existent route returns ErrorResponse JSON."""
        response = await async_client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert data["error_code"] == "NOT_FOUND"
        assert "message" in data
        assert "request_id" in data

    async def test_405_returns_error_response_format(self, async_client: AsyncClient):
        """Using wrong HTTP method returns ErrorResponse JSON."""
        response = await async_client.delete("/api/v1/health")
        assert response.status_code == 405
        data = response.json()
        assert data["success"] is False
        assert "error_code" in data
        assert "request_id" in data


class TestRequestIDMiddleware:
    """Test X-Request-ID header presence."""

    async def test_response_has_request_id_header(self, async_client: AsyncClient):
        """Every response should have X-Request-ID header."""
        response = await async_client.get("/api/v1/health")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    async def test_client_request_id_propagated(self, async_client: AsyncClient):
        """Client-provided X-Request-ID should be propagated back."""
        custom_id = "my-trace-id-12345"
        response = await async_client.get(
            "/api/v1/health",
            headers={"X-Request-ID": custom_id},
        )
        assert response.headers["X-Request-ID"] == custom_id

    async def test_error_response_has_request_id(self, async_client: AsyncClient):
        """Error responses should contain request_id in body."""
        response = await async_client.get("/api/v1/nonexistent")
        data = response.json()
        assert "request_id" in data
        assert len(data["request_id"]) > 0


class TestOpenAPIVersionedDocs:
    """Test OpenAPI docs are at /api/v1/docs (INFRA-07)."""

    def test_openapi_url_versioned(self):
        """OpenAPI JSON should be at /api/v1/openapi.json."""
        from app.main import app

        # In DEBUG mode (test env), openapi_url should be set
        if app.openapi_url is not None:
            assert app.openapi_url == "/api/v1/openapi.json"

    def test_docs_url_versioned(self):
        """Swagger UI should be at /api/v1/docs."""
        from app.main import app

        if app.docs_url is not None:
            assert app.docs_url == "/api/v1/docs"

    async def test_openapi_json_accessible(self, async_client: AsyncClient):
        """GET /api/v1/openapi.json should return valid OpenAPI schema."""
        response = await async_client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
