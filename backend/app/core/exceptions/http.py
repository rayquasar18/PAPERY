"""HTTP exception subclasses for PAPERY domain errors.

Each exception sets a default status_code and error_code.
Raise these directly in routes and services — the exception handler
in main.py catches PaperyHTTPException and returns ErrorResponse JSON.

Usage:
    from app.core.exceptions import NotFoundError, AuthenticationError
    raise NotFoundError("User not found")
"""

from app.core.exceptions.base import PaperyHTTPException


class NotFoundError(PaperyHTTPException):
    """Raised when a requested resource does not exist."""

    error_code = "RESOURCE_NOT_FOUND"

    def __init__(self, detail: str = "Resource not found", **kwargs) -> None:
        super().__init__(status_code=404, detail=detail, error_code=self.error_code, **kwargs)


class AuthenticationError(PaperyHTTPException):
    """Raised for authentication failures (invalid credentials, expired token)."""

    error_code = "AUTH_ERROR"

    def __init__(self, detail: str = "Authentication failed", **kwargs) -> None:
        super().__init__(status_code=401, detail=detail, error_code=self.error_code, **kwargs)


class ForbiddenError(PaperyHTTPException):
    """Raised when user lacks permission for the requested action."""

    error_code = "ACCESS_DENIED"

    def __init__(self, detail: str = "Access denied", **kwargs) -> None:
        super().__init__(status_code=403, detail=detail, error_code=self.error_code, **kwargs)


class ConflictError(PaperyHTTPException):
    """Raised when operation conflicts with existing state (duplicate email, etc.)."""

    error_code = "CONFLICT"

    def __init__(self, detail: str = "Resource conflict", **kwargs) -> None:
        super().__init__(status_code=409, detail=detail, error_code=self.error_code, **kwargs)


class ValidationError(PaperyHTTPException):
    """Raised for business-logic validation failures (not Pydantic request validation)."""

    error_code = "VALIDATION_ERROR"

    def __init__(self, detail: str = "Validation failed", **kwargs) -> None:
        super().__init__(status_code=422, detail=detail, error_code=self.error_code, **kwargs)


class RateLimitError(PaperyHTTPException):
    """Raised when user exceeds their tier's rate limit."""

    error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(self, detail: str = "Too many requests", **kwargs) -> None:
        super().__init__(status_code=429, detail=detail, error_code=self.error_code, **kwargs)


class StorageError(PaperyHTTPException):
    """Raised when file storage operations fail (MinIO upload, presign, etc.)."""

    error_code = "STORAGE_ERROR"

    def __init__(self, detail: str = "Storage operation failed", **kwargs) -> None:
        super().__init__(status_code=502, detail=detail, error_code=self.error_code, **kwargs)


class ExternalServiceError(PaperyHTTPException):
    """Raised when an external service call fails (QuasarFlow, email, OAuth provider)."""

    error_code = "EXTERNAL_SERVICE_ERROR"

    def __init__(self, detail: str = "External service unavailable", **kwargs) -> None:
        super().__init__(status_code=503, detail=detail, error_code=self.error_code, **kwargs)
