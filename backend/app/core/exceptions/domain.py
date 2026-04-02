from app.core.exceptions.base import PaperyError


class ResourceNotFoundError(PaperyError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    error_code = "RESOURCE_NOT_FOUND"


class AuthError(PaperyError):
    """Raised for authentication failures (invalid credentials, expired token)."""

    status_code = 401
    error_code = "AUTH_ERROR"


class AccessDeniedError(PaperyError):
    """Raised when user lacks permission for the requested action."""

    status_code = 403
    error_code = "ACCESS_DENIED"


class ConflictError(PaperyError):
    """Raised when operation conflicts with existing state (duplicate email, etc.)."""

    status_code = 409
    error_code = "CONFLICT"


class ValidationError(PaperyError):
    """Raised for business-logic validation failures (not Pydantic request validation)."""

    status_code = 422
    error_code = "VALIDATION_ERROR"


class StorageError(PaperyError):
    """Raised when file storage operations fail (MinIO upload, presign, etc.)."""

    status_code = 502
    error_code = "STORAGE_ERROR"


class RateLimitError(PaperyError):
    """Raised when user exceeds their tier's rate limit."""

    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"


class ExternalServiceError(PaperyError):
    """Raised when an external service call fails (QuasarFlow, email, OAuth provider)."""

    status_code = 503
    error_code = "EXTERNAL_SERVICE_ERROR"
