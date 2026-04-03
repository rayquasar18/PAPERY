"""PAPERY exception hierarchy.

Usage:
    from app.core.exceptions import NotFoundError, AuthenticationError
    raise NotFoundError("User not found")
"""

from app.core.exceptions.base import PaperyHTTPException
from app.core.exceptions.http import (
    AuthenticationError,
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    StorageError,
    ValidationError,
)

__all__ = [
    "AuthenticationError",
    "ConflictError",
    "ExternalServiceError",
    "ForbiddenError",
    "NotFoundError",
    "PaperyHTTPException",
    "RateLimitError",
    "StorageError",
    "ValidationError",
]
