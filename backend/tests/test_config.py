"""Tests for Pydantic Settings configuration system (INFRA-09)."""

import os
from unittest.mock import patch

import pytest


class TestAppSettings:
    """Test AppSettings loading, validation, and computed fields."""

    def test_default_settings_load_in_local_env(self):
        """Settings should load with defaults when ENVIRONMENT=local."""
        with patch.dict(os.environ, {"ENVIRONMENT": "local"}, clear=False):
            from app.configs.app import AppConfig

            config = AppConfig()
            assert config.APP_NAME == "PAPERY"
            assert config.ENVIRONMENT == "local"

    def test_async_database_uri_computed(self):
        """ASYNC_DATABASE_URI should be computed from individual fields."""
        from app.configs.database import DatabaseConfig

        config = DatabaseConfig(
            POSTGRES_HOST="dbhost",
            POSTGRES_PORT=5432,
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="testdb",
        )
        assert config.ASYNC_DATABASE_URI == ("postgresql+asyncpg://user:pass@dbhost:5432/testdb")

    def test_async_database_uri_special_chars_in_password(self):
        """Password with special characters should be URL-encoded."""
        from app.configs.database import DatabaseConfig

        config = DatabaseConfig(
            POSTGRES_HOST="localhost",
            POSTGRES_PORT=5432,
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="p@ss:w0rd/special",
            POSTGRES_DB="testdb",
        )
        assert "p%40ss%3Aw0rd%2Fspecial" in config.ASYNC_DATABASE_URI

    def test_cors_origins_parses_csv_string(self):
        """CORS_ORIGINS should parse comma-separated string into list."""
        from app.configs.cors import CorsConfig

        config = CorsConfig(CORS_ORIGINS="http://a.com, http://b.com, http://c.com")
        assert config.CORS_ORIGINS == [
            "http://a.com",
            "http://b.com",
            "http://c.com",
        ]

    def test_cors_origins_accepts_list(self):
        """CORS_ORIGINS should accept a list directly."""
        from app.configs.cors import CorsConfig

        config = CorsConfig(CORS_ORIGINS=["http://a.com", "http://b.com"])
        assert config.CORS_ORIGINS == ["http://a.com", "http://b.com"]

    def test_staging_rejects_placeholder_secret_key(self):
        """Non-local environments must reject placeholder SECRET_KEY."""
        from app.configs import AppSettings

        with pytest.raises(ValueError, match="SECRET_KEY must be at least 32 characters"):
            AppSettings(
                ENVIRONMENT="staging",
                SECRET_KEY="CHANGE-ME-short",
                POSTGRES_PASSWORD="real_password",
                MINIO_SECRET_KEY="real_minio_key",
            )

    def test_production_requires_smtp_host(self):
        """Production environment must have SMTP_HOST configured."""
        from app.configs import AppSettings

        with pytest.raises(ValueError, match="SMTP_HOST is required in production"):
            AppSettings(
                ENVIRONMENT="production",
                SECRET_KEY="a-very-long-secret-key-that-is-at-least-32-characters!!",
                POSTGRES_PASSWORD="real_password",
                MINIO_SECRET_KEY="real_minio_key",
                SMTP_HOST="",
            )

    def test_local_env_accepts_all_defaults(self):
        """Local environment should accept all default/placeholder values."""
        from app.configs import AppSettings

        config = AppSettings(ENVIRONMENT="local")
        assert config.APP_NAME == "PAPERY"
        assert config.ENVIRONMENT == "local"
