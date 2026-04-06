"""Tests for exception handling and ErrorResponse schema.

PAPERY uses FastAPI's built-in HTTPException directly.
The exception handler adds request_id and maps status codes to error codes.
"""

from fastapi import HTTPException

from app.schemas.error import ErrorResponse


class TestHTTPExceptionDefaults:
    """Test that FastAPI's HTTPException works as expected for PAPERY usage."""

    def test_httpexception_has_status_code(self):
        """HTTPException carries status_code."""
        exc = HTTPException(status_code=404, detail="Not found")
        assert exc.status_code == 404

    def test_httpexception_has_detail(self):
        """HTTPException carries detail message."""
        exc = HTTPException(status_code=400, detail="Bad request")
        assert exc.detail == "Bad request"

    def test_httpexception_supports_headers(self):
        """HTTPException supports custom headers."""
        exc = HTTPException(status_code=429, detail="Too many requests", headers={"Retry-After": "60"})
        assert exc.headers == {"Retry-After": "60"}

    def test_httpexception_is_exception(self):
        """HTTPException is a proper Exception subclass."""
        exc = HTTPException(status_code=500)
        assert isinstance(exc, Exception)


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
