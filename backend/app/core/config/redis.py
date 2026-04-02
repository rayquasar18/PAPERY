from pydantic import Field
from pydantic_settings import BaseSettings


class RedisConfig(BaseSettings):
    REDIS_CACHE_HOST: str = Field(default="localhost")
    REDIS_CACHE_PORT: int = Field(default=6379)
    REDIS_CACHE_DB: int = Field(default=0)
    REDIS_CACHE_PASSWORD: str = Field(default="")

    REDIS_QUEUE_HOST: str = Field(default="localhost")
    REDIS_QUEUE_PORT: int = Field(default=6379)
    REDIS_QUEUE_DB: int = Field(default=1)
    REDIS_QUEUE_PASSWORD: str = Field(default="")

    REDIS_RATE_LIMIT_HOST: str = Field(default="localhost")
    REDIS_RATE_LIMIT_PORT: int = Field(default=6379)
    REDIS_RATE_LIMIT_DB: int = Field(default=2)
    REDIS_RATE_LIMIT_PASSWORD: str = Field(default="")
