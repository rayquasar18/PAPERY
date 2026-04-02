from functools import cached_property
from urllib.parse import quote_plus

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_USER: str = Field(default="papery")
    POSTGRES_PASSWORD: str = Field(default="papery_dev_password")
    POSTGRES_DB: str = Field(default="papery")
    POSTGRES_POOL_SIZE: int = Field(default=20)
    POSTGRES_MAX_OVERFLOW: int = Field(default=10)
    POSTGRES_POOL_RECYCLE: int = Field(default=3600)

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def ASYNC_DATABASE_URI(self) -> str:
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
