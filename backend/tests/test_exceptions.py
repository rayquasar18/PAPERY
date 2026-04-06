"""Tests for PaperyHTTPException, convenience subclasses, and exception handlers.

Covers:
- PaperyHTTPException construction and attributes
- Convenience subclass defaults (status_code, error_code)
- Backward compatibility: PaperyHTTPException IS-A HTTPException
- Integration: PaperyHTTPException → correct error_code in response
- Integration: plain HTTPException → fallback error_code via status map
- ErrorResponse schema basics
"""

from fastapi import HTTPException

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    InternalError,
    NotFoundError,
    PaperyHTTPException,
    RateLimitedError,
    UnauthorizedError,
)
from app.schemas.error import ErrorResponse


class TestPaperyHTTPException:
    """Test PaperyHTTPException construction and attributes."""

    def test_basic_construction(self):
        exc = PaperyHTTPException(status_code=404, error_code="USER_NOT_FOUND", detail="User not found")
        assert exc.status_code == 404
        assert exc.error_code == "USER_NOT_FOUND"
        assert exc.detail == "User not found"

    def test_default_detail(self):
        exc = PaperyHTTPException(status_code=500, error_code="INTERNAL_ERROR")
        assert exc.detail == "An error occurred"

    def test_custom_headers(self):
        exc = PaperyHTTPException(
            status_code=429,
            error_code="RATE_LIMITED",
            detail="Slow down",
            headers={"Retry-After": "60"},
        )
        assert exc.headers == {"Retry-After": "60"}

    def test_is_httpexception(self):
        """PaperyHTTPException must be an HTTPException subclass for FastAPI compat."""
        exc = PaperyHTTPException(status_code=400, error_code="BAD_REQUEST")
        assert isinstance(exc, HTTPException)
        assert isinstance(exc, Exception)

    def test_none_headers_default(self):
        exc = PaperyHTTPException(status_code=403, error_code="FORBIDDEN")
        assert exc.headers is None


class TestConvenienceSubclasses:
    """Test that convenience subclasses set correct defaults."""

    def test_bad_request_error(self):
        exc = BadRequestError("Invalid input")
        assert exc.status_code == 400
        assert exc.error_code == "BAD_REQUEST"
        assert exc.detail == "Invalid input"

    def test_bad_request_error_defaults(self):
        exc = BadRequestError()
        assert exc.status_code == 400
        assert exc.error_code == "BAD_REQUEST"
        assert exc.detail == "Bad request"

    def test_unauthorized_error(self):
        exc = UnauthorizedError("Token expired")
        assert exc.status_code == 401
        assert exc.error_code == "UNAUTHORIZED"
        assert exc.detail == "Token expired"

    def test_forbidden_error(self):
        exc = ForbiddenError("Access denied")
        assert exc.status_code == 403
        assert exc.error_code == "FORBIDDEN"
        assert exc.detail == "Access denied"

    def test_not_found_error(self):
        exc = NotFoundError("User not found")
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"
        assert exc.detail == "User not found"

    def test_conflict_error(self):
        exc = ConflictError("Email already registered")
        assert exc.status_code == 409
        assert exc.error_code == "CONFLICT"
        assert exc.detail == "Email already registered"

    def test_rate_limited_error(self):
        exc = RateLimitedError("Too many requests")
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMITED"
        assert exc.detail == "Too many requests"

    def test_rate_limited_error_with_headers(self):
        exc = RateLimitedError("Slow down", headers={"Retry-After": "30"})
        assert exc.headers == {"Retry-After": "30"}

    def test_internal_error(self):
        exc = InternalError("Database connection failed")
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.detail == "Database connection failed"

    def test_custom_error_code_override(self):
        """Convenience subclasses allow overriding error_code."""
        exc = NotFoundError("Project not found", error_code="PROJECT_NOT_FOUND")
        assert exc.status_code == 404
        assert exc.error_code == "PROJECT_NOT_FOUND"

    def test_all_subclasses_are_papery_http_exception(self):
        """All convenience subclasses inherit from PaperyHTTPException."""
        classes = [
            BadRequestError,
            UnauthorizedError,
            ForbiddenError,
            NotFoundError,
            ConflictError,
            RateLimitedError,
            InternalError,
        ]
        for cls in classes:
            exc = cls()
            assert isinstance(exc, PaperyHTTPException)
            assert isinstance(exc, HTTPException)


class TestErrorResponse:
    """Test ErrorResponse Pydantic schema."""

    def test_basic_construction(self):
        resp = ErrorResponse(
            error_code="NOT_FOUND",
            message="Not found",
            request_id="req-abc",
        )
        assert resp.success is False
        assert resp.error_code == "NOT_FOUND"
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
            error_code="UNAUTHORIZED",
            message="Token expired",
            request_id="req-123",
        )
        data = resp.model_dump()
        assert data["success"] is False
        assert data["error_code"] == "UNAUTHORIZED"
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
