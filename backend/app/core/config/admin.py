from pydantic import Field
from pydantic_settings import BaseSettings


class AdminConfig(BaseSettings):
    ADMIN_EMAIL: str = Field(default="admin@papery.local")
    ADMIN_PASSWORD: str = Field(default="admin_dev_password")
