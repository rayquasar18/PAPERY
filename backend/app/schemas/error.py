"""Error response schema — consistent JSON shape for all API errors."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response returned by all exception handlers.

    This schema is the API contract for error responses.
    Frontend uses `error_code` as an i18n lookup key.
    """

    success: bool = Field(default=False, description="Always false for error responses")
    error_code: str = Field(..., description="Machine-readable error code (UPPER_SNAKE_CASE)")
    message: str = Field(..., description="Human-readable error message (English default)")
    detail: Any | None = Field(default=None, description="Additional structured error data")
    request_id: str = Field(..., description="Unique request identifier for debugging")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": False,
                    "error_code": "RESOURCE_NOT_FOUND",
                    "message": "User not found",
                    "detail": {"uuid": "550e8400-e29b-41d4-a716-446655440000"},
                    "request_id": "req-abc123",
                }
            ]
        }
    }
