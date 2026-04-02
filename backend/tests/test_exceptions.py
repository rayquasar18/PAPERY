"""Tests for PAPERY exception hierarchy and ErrorResponse schema (INFRA-06)."""

from app.core.exceptions import (
    AccessDeniedError,
    AuthError,
    ConflictError,
    ExternalServiceError,
    PaperyError,
    RateLimitError,
    ResourceNotFoundError,
    StorageError,
    ValidationError,
)
from app.schemas.error import ErrorResponse


class TestPaperyErrorBase:
    """Test PaperyError base class."""

    def test_default_attributes(self):
        """PaperyError has correct default status_code and error_code."""
        err = PaperyError()
        assert err.status_code == 500
        assert err.error_code == "INTERNAL_ERROR"
        assert err.message == "An unexpected error occurred"
        assert err.detail is None

    def test_custom_message(self):
        """PaperyError accepts custom message."""
        err = PaperyError("Something broke")
        assert err.message == "Something broke"
        assert str(err) == "Something broke"

    def test_custom_detail(self):
        """PaperyError accepts structured detail."""
        detail = {"field": "email", "reason": "duplicate"}
        err = PaperyError("Conflict", detail=detail)
        assert err.detail == {"field": "email", "reason": "duplicate"}

    def test_override_error_code(self):
        """PaperyError constructor can override error_code."""
        err = PaperyError("test", error_code="CUSTOM_CODE")
        assert err.error_code == "CUSTOM_CODE"

    def test_override_status_code(self):
        """PaperyError constructor can override status_code."""
        err = PaperyError("test", status_code=418)
        assert err.status_code == 418

    def test_is_exception(self):
        """PaperyError is a proper Exception subclass."""
        err = PaperyError("test")
        assert isinstance(err, Exception)


class TestDomainExceptions:
    """Test all domain exception subclasses."""

    def test_resource_not_found(self):
        err = ResourceNotFoundError("User not found")
        assert err.status_code == 404
        assert err.error_code == "RESOURCE_NOT_FOUND"
        assert err.message == "User not found"
        assert isinstance(err, PaperyError)

    def test_auth_error(self):
        err = AuthError("Invalid token")
        assert err.status_code == 401
        assert err.error_code == "AUTH_ERROR"
        assert isinstance(err, PaperyError)

    def test_access_denied(self):
        err = AccessDeniedError("Insufficient permissions")
        assert err.status_code == 403
        assert err.error_code == "ACCESS_DENIED"
        assert isinstance(err, PaperyError)

    def test_conflict_error(self):
        err = ConflictError("Email already exists")
        assert err.status_code == 409
        assert err.error_code == "CONFLICT"
        assert isinstance(err, PaperyError)

    def test_validation_error(self):
        err = ValidationError("Invalid date range")
        assert err.status_code == 422
        assert err.error_code == "VALIDATION_ERROR"
        assert isinstance(err, PaperyError)

    def test_storage_error(self):
        err = StorageError("MinIO upload failed")
        assert err.status_code == 502
        assert err.error_code == "STORAGE_ERROR"
        assert isinstance(err, PaperyError)

    def test_rate_limit_error(self):
        err = RateLimitError("Too many requests")
        assert err.status_code == 429
        assert err.error_code == "RATE_LIMIT_EXCEEDED"
        assert isinstance(err, PaperyError)

    def test_external_service_error(self):
        err = ExternalServiceError("QuasarFlow timeout")
        assert err.status_code == 503
        assert err.error_code == "EXTERNAL_SERVICE_ERROR"
        assert isinstance(err, PaperyError)

    def test_subclass_with_detail(self):
        """Domain exceptions accept detail dict."""
        err = ResourceNotFoundError(
            "Project not found",
            detail={"uuid": "abc-123"},
        )
        assert err.detail == {"uuid": "abc-123"}


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
