from pydantic import Field
from pydantic_settings import BaseSettings


class MinioConfig(BaseSettings):
    MINIO_ENDPOINT: str = Field(default="localhost:9000")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin")
    MINIO_SECRET_KEY: str = Field(default="minioadmin")
    MINIO_BUCKET_NAME: str = Field(default="papery")
    MINIO_SECURE: bool = Field(default=False)
    MINIO_PRESIGNED_GET_EXPIRY: int = Field(default=3600)  # 1 hour in seconds
    MINIO_PRESIGNED_PUT_EXPIRY: int = Field(default=1800)  # 30 minutes in seconds
