"""Canonical request/response schemas for QuasarFlow AI job boundary."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIJobStatus(str, Enum):
    """AI job lifecycle statuses used across providers and service boundaries."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class AIJobErrorDetail(BaseModel):
    """Structured error payload for failed provider responses."""

    code: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=2000)
    retriable: bool = False
    details: dict[str, Any] | None = None


class AIJobRequest(BaseModel):
    """Canonical request shape passed to QuasarFlow provider clients."""

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(..., min_length=1, max_length=128)
    action: str = Field(..., min_length=1, max_length=64)
    document_ids: list[str] = Field(default_factory=list)
    prompt: str = Field(..., min_length=1, max_length=20000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) != len(value):
            raise ValueError("document_ids must contain non-empty IDs")
        return cleaned


class AIJobProviderResponse(BaseModel):
    """Canonical provider response shape validated at service boundary."""

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(..., min_length=1, max_length=128)
    status: AIJobStatus
    action: str = Field(..., min_length=1, max_length=64)
    output: dict[str, Any] | None = None
    progress: int = Field(..., ge=0, le=100)
    attempt: int = Field(..., ge=1, le=50)
    max_attempts: int = Field(..., ge=1, le=50)
    error: AIJobErrorDetail | None = None

    @field_validator("max_attempts")
    @classmethod
    def validate_attempt_window(cls, value: int, info: Any) -> int:
        attempt = info.data.get("attempt")
        if isinstance(attempt, int) and attempt > value:
            raise ValueError("max_attempts must be greater than or equal to attempt")
        return value

    @field_validator("error")
    @classmethod
    def require_error_for_failure(cls, value: AIJobErrorDetail | None, info: Any) -> AIJobErrorDetail | None:
        status = info.data.get("status")
        if status in {AIJobStatus.FAILED, AIJobStatus.TIMED_OUT} and value is None:
            raise ValueError("error is required for failed or timed_out status")
        return value
