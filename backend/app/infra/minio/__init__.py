"""MinIO infrastructure — S3-compatible file storage."""

from app.infra.minio.client import (
    client,
    delete_file,
    init,
    presigned_get_url,
    presigned_put_url,
    shutdown,
    upload_file,
)

__all__ = [
    "client",
    "delete_file",
    "init",
    "presigned_get_url",
    "presigned_put_url",
    "shutdown",
    "upload_file",
]
