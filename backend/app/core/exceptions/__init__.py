"""PAPERY exception hierarchy.

Usage:
    from app.core.exceptions import ResourceNotFoundError, AuthError
    raise ResourceNotFoundError("User not found", detail={"uuid": user_uuid})
"""

from app.core.exceptions.base import PaperyError
from app.core.exceptions.domain import (
    AccessDeniedError,
    AuthError,
    ConflictError,
    ExternalServiceError,
    RateLimitError,
    ResourceNotFoundError,
    StorageError,
    ValidationError,
)

__all__ = [
    "PaperyError",
    "ResourceNotFoundError",
    "AuthError",
    "AccessDeniedError",
    "ConflictError",
    "ValidationError",
    "StorageError",
    "RateLimitError",
    "ExternalServiceError",
]
