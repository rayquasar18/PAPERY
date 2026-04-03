from typing import Self

from pydantic import model_validator
from pydantic_settings import SettingsConfigDict

from app.configs.admin import AdminConfig
from app.configs.app import AppConfig
from app.configs.cors import CorsConfig
from app.configs.database import DatabaseConfig
from app.configs.email import EmailConfig
from app.configs.minio import MinioConfig
from app.configs.redis import RedisConfig
from app.configs.security import SecurityConfig


class AppSettings(
    AppConfig,
    DatabaseConfig,
    RedisConfig,
    MinioConfig,
    SecurityConfig,
    EmailConfig,
    CorsConfig,
    AdminConfig,
):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @model_validator(mode="after")
    def validate_startup(self) -> Self:
        # Reject placeholder SECRET_KEY in non-local environments
        if self.ENVIRONMENT != "local":
            if "CHANGE-ME" in self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters and not a placeholder "
                    f"in {self.ENVIRONMENT} environment"
                )
            if self.POSTGRES_PASSWORD in ("papery_dev_password", ""):
                raise ValueError(
                    f"POSTGRES_PASSWORD must be set in {self.ENVIRONMENT} environment"
                )
            if self.MINIO_SECRET_KEY in ("minioadmin", ""):
                raise ValueError(
                    f"MINIO_SECRET_KEY must be set in {self.ENVIRONMENT} environment"
                )
            if "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "CORS wildcard '*' is not allowed in non-local environments. "
                    "Set explicit origins in CORS_ORIGINS."
                )
        if self.ENVIRONMENT == "production" and not self.SMTP_HOST:
            raise ValueError("SMTP_HOST is required in production environment")
        return self


settings = AppSettings()
