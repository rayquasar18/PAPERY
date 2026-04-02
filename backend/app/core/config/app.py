from pydantic import Field
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    APP_NAME: str = Field(default="PAPERY")
    APP_VERSION: str = Field(default="0.1.0")
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="local")  # local | staging | production
