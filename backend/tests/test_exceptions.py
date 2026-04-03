"""Tests for PAPERY exception hierarchy and ErrorResponse schema.

Verifies PaperyHTTPException extends FastAPI's HTTPException and all
domain subclasses have correct status_code, error_code, and detail.
"""

from fastapi import HTTPException

from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    PaperyHTTPException,
    RateLimitError,
    StorageError,
    ValidationError,
)
from app.schemas.error import ErrorResponse


class TestPaperyHTTPExceptionBase:
    """Test PaperyHTTPException base class."""

    def test_inherits_from_fastapi_httpexception(self):
        """PaperyHTTPException must be a subclass of FastAPI's HTTPException."""
        assert issubclass(PaperyHTTPException, HTTPException)

    def test_default_attributes(self):
        """PaperyHTTPException has correct default status_code and error_code."""
        exc = PaperyHTTPException()
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.detail == "An unexpected error occurred"

    def test_custom_detail(self):
        """PaperyHTTPException accepts custom detail message."""
        exc = PaperyHTTPException(detail="Something broke")
        assert exc.detail == "Something broke"

    def test_override_error_code(self):
        """PaperyHTTPException constructor can override error_code."""
        exc = PaperyHTTPException(error_code="CUSTOM_CODE")
        assert exc.error_code == "CUSTOM_CODE"

    def test_override_status_code(self):
        """PaperyHTTPException constructor can override status_code."""
        exc = PaperyHTTPException(status_code=418, detail="I'm a teapot")
        assert exc.status_code == 418

    def test_is_exception(self):
        """PaperyHTTPException is a proper Exception subclass."""
        exc = PaperyHTTPException()
        assert isinstance(exc, Exception)
        assert isinstance(exc, HTTPException)

    def test_headers_support(self):
        """PaperyHTTPException supports custom headers."""
        exc = PaperyHTTPException(headers={"X-Custom": "value"})
        assert exc.headers == {"X-Custom": "value"}


class TestHTTPExceptions:
    """Test all HTTP exception subclasses."""

    def test_not_found_error(self):
        exc = NotFoundError("User not found")
        assert exc.status_code == 404
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert exc.detail == "User not found"
        assert isinstance(exc, PaperyHTTPException)
        assert isinstance(exc, HTTPException)

    def test_not_found_error_default_detail(self):
        exc = NotFoundError()
        assert exc.detail == "Resource not found"

    def test_authentication_error(self):
        exc = AuthenticationError("Invalid token")
        assert exc.status_code == 401
        assert exc.error_code == "AUTH_ERROR"
        assert exc.detail == "Invalid token"
        assert isinstance(exc, PaperyHTTPException)

    def test_authentication_error_default_detail(self):
        exc = AuthenticationError()
        assert exc.detail == "Authentication failed"

    def test_forbidden_error(self):
        exc = ForbiddenError("Insufficient permissions")
        assert exc.status_code == 403
        assert exc.error_code == "ACCESS_DENIED"
        assert isinstance(exc, PaperyHTTPException)

    def test_conflict_error(self):
        exc = ConflictError("Email already exists")
        assert exc.status_code == 409
        assert exc.error_code == "CONFLICT"
        assert isinstance(exc, PaperyHTTPException)

    def test_validation_error(self):
        exc = ValidationError("Invalid date range")
        assert exc.status_code == 422
        assert exc.error_code == "VALIDATION_ERROR"
        assert isinstance(exc, PaperyHTTPException)

    def test_rate_limit_error(self):
        exc = RateLimitError("Too many requests")
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert isinstance(exc, PaperyHTTPException)

    def test_storage_error(self):
        exc = StorageError("MinIO upload failed")
        assert exc.status_code == 502
        assert exc.error_code == "STORAGE_ERROR"
        assert isinstance(exc, PaperyHTTPException)

    def test_external_service_error(self):
        exc = ExternalServiceError("QuasarFlow timeout")
        assert exc.status_code == 503
        assert exc.error_code == "EXTERNAL_SERVICE_ERROR"
        assert isinstance(exc, PaperyHTTPException)

    def test_all_subclasses_inherit_httpexception(self):
        """Every domain exception must be catchable as HTTPException."""
        for cls in [
            NotFoundError,
            AuthenticationError,
            ForbiddenError,
            ConflictError,
            ValidationError,
            RateLimitError,
            StorageError,
            ExternalServiceError,
        ]:
            assert issubclass(cls, HTTPException), f"{cls.__name__} must inherit HTTPException"


class TestErrorResponse:
    """Test ErrorResponse Pydantic schema."""

    def test_basic_construction(self):
        resp = ErrorResponse(
            error_code="RESOURCE_NOT_FOUND",
            message="Not found",
            request_id="req-abc",
        )
        assert resp.success is False
        assert resp.error_code == "RESOURCE_NOT_FOUND"
        assert resp.message == "Not found"
        assert resp.detail is None
        assert resp.request_id == "req-abc"

    def test_with_detail(self):
        resp = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Bad input",
            detail=[{"loc": ["body", "email"], "msg": "invalid"}],
            request_id="req-xyz",
        )
        assert resp.detail == [{"loc": ["body", "email"], "msg": "invalid"}]

    def test_model_dump(self):
        resp = ErrorResponse(
            error_code="AUTH_ERROR",
            message="Token expired",
            request_id="req-123",
        )
        data = resp.model_dump()
        assert data["success"] is False
        assert data["error_code"] == "AUTH_ERROR"
        assert data["message"] == "Token expired"
        assert data["detail"] is None
        assert data["request_id"] == "req-123"

    def test_success_default_false(self):
        """success field defaults to False."""
        resp = ErrorResponse(
            error_code="TEST",
            message="test",
            request_id="req-1",
        )
        assert resp.success is False
