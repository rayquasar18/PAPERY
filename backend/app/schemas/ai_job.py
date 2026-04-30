"""Canonical request/response schemas for QuasarFlow AI job boundary."""

from __future__ import annotations

import uuid as uuid_pkg
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIJobStatus(StrEnum):
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


class AIJobCreate(BaseModel):
    """Public request payload for AI job submission."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(..., min_length=1, max_length=64)
    prompt: str = Field(..., min_length=1, max_length=20000)
    document_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIJobRead(BaseModel):
    """Polling-first API response for persisted AI jobs."""

    model_config = ConfigDict(from_attributes=True)

    job_id: uuid_pkg.UUID
    status: AIJobStatus
    action: str
    progress: int
    attempt: int
    max_attempts: int
    result_payload: dict[str, Any] | None = None
    error_payload: dict[str, Any] | None = None


class AIJobSubmitResponse(BaseModel):
    """Accepted response returned immediately after enqueue-style submission."""

    model_config = ConfigDict(from_attributes=True)

    job_id: uuid_pkg.UUID
    status: AIJobStatus
    action: str
    progress: int = 0
    attempt: int = 1
    max_attempts: int = 3
    result_payload: dict[str, Any] | None = None
    error_payload: dict[str, Any] | None = None


class AIJobErrorEnvelope(BaseModel):
    """Compact error envelope used by AI job polling endpoints."""

    code: str
    message: str


class AIJobErrorResponse(BaseModel):
    """Error contract expected by AI job API tests."""

    error: AIJobErrorEnvelope
    request_id: str | None = None



def build_ai_job_read(payload: Any) -> AIJobRead:
    """Normalize service/model objects into the public polling response shape."""

    return AIJobRead(
        job_id=payload.uuid,
        status=payload.status,
        action=payload.action,
        progress=getattr(payload, "progress", 0),
        attempt=getattr(payload, "attempt", 1),
        max_attempts=getattr(payload, "max_attempts", 3),
        result_payload=getattr(payload, "result_payload", None),
        error_payload=getattr(payload, "error_payload", None),
    )



def build_ai_job_submit_response(payload: Any) -> AIJobSubmitResponse:
    """Normalize service/model objects into the accepted submission response."""

    return AIJobSubmitResponse(
        job_id=payload.uuid,
        status=payload.status,
        action=payload.action,
        progress=getattr(payload, "progress", 0),
        attempt=getattr(payload, "attempt", 1),
        max_attempts=getattr(payload, "max_attempts", 3),
        result_payload=getattr(payload, "result_payload", None),
        error_payload=getattr(payload, "error_payload", None),
    )



def build_ai_job_error_response(code: str, message: str, request_id: str | None = None) -> AIJobErrorResponse:
    """Build the compact AI job endpoint error response."""

    return AIJobErrorResponse(error=AIJobErrorEnvelope(code=code, message=message), request_id=request_id)


__all__ = [
    "AIJobCreate",
    "AIJobErrorDetail",
    "AIJobErrorEnvelope",
    "AIJobErrorResponse",
    "AIJobProviderResponse",
    "AIJobRead",
    "AIJobRequest",
    "AIJobStatus",
    "AIJobSubmitResponse",
    "build_ai_job_error_response",
    "build_ai_job_read",
    "build_ai_job_submit_response",
]
