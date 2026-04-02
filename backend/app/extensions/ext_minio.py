"""MinIO extension — S3-compatible file storage with presigned URL support."""
import logging
from datetime import timedelta
from functools import partial

from minio import Minio

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton (initialized in init())
client: Minio | None = None


def init() -> None:
    """Initialize MinIO client and ensure bucket exists.

    Note: MinIO SDK is synchronous (urllib3-based). This is fine because:
    - init() runs once at startup
    - presigned URL generation is local crypto (no network I/O)
    - Only large uploads need run_in_executor wrapping
    """
    global client

    client = Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )

    # Auto-create bucket if it doesn't exist
    bucket = settings.MINIO_BUCKET_NAME
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        logger.info("Created MinIO bucket: %s", bucket)
    else:
        logger.info("MinIO bucket exists: %s", bucket)

    logger.info("MinIO client initialized: %s", settings.MINIO_ENDPOINT)


def shutdown() -> None:
    """No-op. MinIO SDK manages connections internally via urllib3."""
    global client
    client = None
    logger.info("MinIO client released")


def presigned_get_url(
    object_name: str,
    expires: int | None = None,
) -> str:
    """Generate a presigned GET URL for downloading an object.

    Args:
        object_name: The object key in the bucket.
        expires: Expiry in seconds. Defaults to MINIO_PRESIGNED_GET_EXPIRY (3600s).

    Returns:
        Presigned URL string.
    """
    if client is None:
        raise RuntimeError("MinIO not initialized. Call ext_minio.init() first.")

    expiry = timedelta(seconds=expires or settings.MINIO_PRESIGNED_GET_EXPIRY)
    return client.presigned_get_object(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=object_name,
        expires=expiry,
    )


def presigned_put_url(
    object_name: str,
    expires: int | None = None,
) -> str:
    """Generate a presigned PUT URL for uploading an object.

    Args:
        object_name: The object key in the bucket.
        expires: Expiry in seconds. Defaults to MINIO_PRESIGNED_PUT_EXPIRY (1800s).

    Returns:
        Presigned URL string.
    """
    if client is None:
        raise RuntimeError("MinIO not initialized. Call ext_minio.init() first.")

    expiry = timedelta(seconds=expires or settings.MINIO_PRESIGNED_PUT_EXPIRY)
    return client.presigned_put_object(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=object_name,
        expires=expiry,
    )


async def upload_file(
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    """Upload file data to MinIO. Wraps sync call in executor for async safety.

    Args:
        object_name: The object key in the bucket.
        data: File content as bytes.
        content_type: MIME type of the file.
    """
    import asyncio
    import io

    if client is None:
        raise RuntimeError("MinIO not initialized. Call ext_minio.init() first.")

    loop = asyncio.get_running_loop()
    stream = io.BytesIO(data)

    await loop.run_in_executor(
        None,
        partial(
            client.put_object,
            bucket_name=settings.MINIO_BUCKET_NAME,
            object_name=object_name,
            data=stream,
            length=len(data),
            content_type=content_type,
        ),
    )
