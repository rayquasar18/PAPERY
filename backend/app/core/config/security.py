from pydantic import Field
from pydantic_settings import BaseSettings


class SecurityConfig(BaseSettings):
    SECRET_KEY: str = Field(default="CHANGE-ME-IN-PRODUCTION-minimum-32-chars!!")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
