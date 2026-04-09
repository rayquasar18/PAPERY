"""MinIO infrastructure — S3-compatible file storage."""

from app.infra.minio.client import (
    client,
    init,
    presigned_get_url,
    presigned_put_url,
    shutdown,
    upload_file,
)

__all__ = [
    "client",
    "init",
    "presigned_get_url",
    "presigned_put_url",
    "shutdown",
    "upload_file",
]
