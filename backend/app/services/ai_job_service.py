"""AI job service orchestration for submit, status, and worker-side lifecycle."""

from __future__ import annotations

import uuid as uuid_pkg
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.ai_job import AIJob
from app.models.user import User
from app.repositories.ai_job_repository import AIJobRepository
from app.schemas.ai_job import AIJobCreate, AIJobErrorDetail, AIJobRead, AIJobRequest, AIJobStatus
from app.services.quasarflow.stub_client import QuasarFlowStubClient


@dataclass(slots=True)
class CircuitState:
    failure_count: int = 0
    opened_until: datetime | None = None


class AIJobService:
    """Service for polling-first async AI jobs with bounded resilience behavior."""

    MAX_ATTEMPTS = 3
    TIMEOUT_SECONDS = 3
    RETRY_BACKOFF_SECONDS = (1, 2)
    CIRCUIT_FAIL_THRESHOLD = 3
    CIRCUIT_RECOVERY_SECONDS = 30

    _circuit_state = CircuitState()

    def __init__(self, db: AsyncSession) -> None:
        self._repo = AIJobRepository(db)
        self._provider = QuasarFlowStubClient()

    async def submit_job(self, user: User, payload: AIJobCreate) -> AIJobRead:
        job = await self._repo.create_pending_job(
            user_id=user.id,
            action=payload.action,
            prompt=payload.prompt,
            document_ids=payload.document_ids,
            metadata_payload=payload.metadata,
            max_attempts=self.MAX_ATTEMPTS,
        )
        return AIJobRead.model_validate(job)

    async def get_job_status_for_user(self, user: User, job_uuid: uuid_pkg.UUID) -> AIJobRead:
        job = await self._repo.get_for_user(job_uuid=job_uuid, user_id=user.id)
        if job is None:
            raise NotFoundError(detail="Job not found")
        return AIJobRead.model_validate(job)

    async def mark_running(self, *, job_id: uuid_pkg.UUID, attempt: int) -> AIJob:
        job = await self._repo.get(uuid=job_id)
        if job is None:
            raise NotFoundError(detail="Job not found")
        return await self._repo.transition_status(job=job, to_status=AIJobStatus.RUNNING, progress=10, attempt=attempt)

    async def mark_succeeded(self, *, job_id: uuid_pkg.UUID, result_payload: dict, attempt: int) -> AIJob:
        job = await self._repo.get(uuid=job_id)
        if job is None:
            raise NotFoundError(detail="Job not found")
        self._close_circuit_on_success()
        return await self._repo.transition_status(
            job=job,
            to_status=AIJobStatus.SUCCEEDED,
            progress=100,
            result_payload=result_payload,
            attempt=attempt,
            error_payload=None,
        )

    async def mark_retryable_failure(self, *, job_id: uuid_pkg.UUID, error: AIJobErrorDetail, attempt: int) -> AIJob:
        job = await self._repo.get(uuid=job_id)
        if job is None:
            raise NotFoundError(detail="Job not found")

        self._register_failure()
        terminal_status = AIJobStatus.TIMED_OUT if error.code == "TIMEOUT" else AIJobStatus.FAILED
        if attempt < job.max_attempts:
            return await self._repo.transition_status(
                job=job,
                to_status=AIJobStatus.PENDING,
                progress=0,
                attempt=attempt + 1,
                error_payload=error.model_dump(),
            )

        return await self._repo.transition_status(
            job=job,
            to_status=terminal_status,
            progress=100,
            attempt=attempt,
            error_payload=error.model_dump(),
        )

    async def mark_circuit_open_failure(self, *, job_id: uuid_pkg.UUID) -> AIJob:
        job = await self._repo.get(uuid=job_id)
        if job is None:
            raise NotFoundError(detail="Job not found")
        return await self._repo.transition_status(
            job=job,
            to_status=AIJobStatus.FAILED,
            progress=100,
            error_payload={
                "code": "CIRCUIT_OPEN",
                "message": "Provider temporarily unavailable. Retry later.",
                "retriable": True,
                "details": {"recovery_seconds": self.CIRCUIT_RECOVERY_SECONDS},
            },
        )

    def build_provider_request(self, *, job: AIJob) -> AIJobRequest:
        return AIJobRequest(
            job_id=str(job.uuid),
            action=job.action,
            document_ids=job.document_ids,
            prompt=job.prompt,
            metadata=job.metadata_payload,
        )

    def is_circuit_open(self) -> bool:
        opened_until = self._circuit_state.opened_until
        return opened_until is not None and datetime.now(UTC) < opened_until

    def _register_failure(self) -> None:
        state = self._circuit_state
        state.failure_count += 1
        if state.failure_count >= self.CIRCUIT_FAIL_THRESHOLD:
            state.opened_until = datetime.now(UTC) + timedelta(seconds=self.CIRCUIT_RECOVERY_SECONDS)

    def _close_circuit_on_success(self) -> None:
        self._circuit_state.failure_count = 0
        self._circuit_state.opened_until = None
