"""PAPERY exception classes.

PaperyHTTPException extends FastAPI's HTTPException with a machine-readable
``error_code`` attribute. Convenience subclasses provide short aliases for
common HTTP error scenarios.

Usage:
    from app.core.exceptions import NotFoundError, ConflictError

    raise NotFoundError("User not found")
    raise ConflictError("Email already registered")

The global exception handlers (registered via ``register_exception_handlers``)
detect PaperyHTTPException and use its ``error_code`` directly. For plain
HTTPException, a fallback status-code → error-code map is applied.
"""

from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Status-code → error-code fallback map
# Used by the exception handler when a plain HTTPException (without
# error_code) is raised — e.g. from middleware or third-party deps.
# ---------------------------------------------------------------------------
HTTP_STATUS_ERROR_CODE_MAP: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    408: "REQUEST_TIMEOUT",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}


# ---------------------------------------------------------------------------
# Base custom exception
# ---------------------------------------------------------------------------
class PaperyHTTPException(HTTPException):
    """HTTPException with an explicit ``error_code`` for structured responses.

    Inherits from FastAPI's HTTPException so that FastAPI's built-in
    exception catching still works. The ``error_code`` is surfaced in
    the ErrorResponse JSON instead of being derived from the status code.
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        detail: str = "An error occurred",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


# ---------------------------------------------------------------------------
# Convenience subclasses
# ---------------------------------------------------------------------------
class BadRequestError(PaperyHTTPException):
    """400 Bad Request."""

    def __init__(
        self,
        detail: str = "Bad request",
        *,
        error_code: str = "BAD_REQUEST",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=400, error_code=error_code, detail=detail, headers=headers)


class UnauthorizedError(PaperyHTTPException):
    """401 Unauthorized."""

    def __init__(
        self,
        detail: str = "Unauthorized",
        *,
        error_code: str = "UNAUTHORIZED",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=401, error_code=error_code, detail=detail, headers=headers)


class ForbiddenError(PaperyHTTPException):
    """403 Forbidden."""

    def __init__(
        self,
        detail: str = "Forbidden",
        *,
        error_code: str = "FORBIDDEN",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=403, error_code=error_code, detail=detail, headers=headers)


class NotFoundError(PaperyHTTPException):
    """404 Not Found."""

    def __init__(
        self,
        detail: str = "Not found",
        *,
        error_code: str = "NOT_FOUND",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=404, error_code=error_code, detail=detail, headers=headers)


class ConflictError(PaperyHTTPException):
    """409 Conflict."""

    def __init__(
        self,
        detail: str = "Conflict",
        *,
        error_code: str = "CONFLICT",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=409, error_code=error_code, detail=detail, headers=headers)


class RateLimitedError(PaperyHTTPException):
    """429 Too Many Requests."""

    def __init__(
        self,
        detail: str = "Too many requests",
        *,
        error_code: str = "RATE_LIMITED",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=429, error_code=error_code, detail=detail, headers=headers)


class InternalError(PaperyHTTPException):
    """500 Internal Server Error."""

    def __init__(
        self,
        detail: str = "Internal server error",
        *,
        error_code: str = "INTERNAL_ERROR",
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=500, error_code=error_code, detail=detail, headers=headers)


__all__ = [
    "HTTP_STATUS_ERROR_CODE_MAP",
    "PaperyHTTPException",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ConflictError",
    "RateLimitedError",
    "InternalError",
]
