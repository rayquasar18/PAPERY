"""Repository layer for persisted AI job reads and status updates."""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_job import AIJob
from app.schemas.ai_job import AIJobStatus
from app.repositories.base import BaseRepository

_ALLOWED_TRANSITIONS: dict[AIJobStatus, set[AIJobStatus]] = {
    AIJobStatus.PENDING: {AIJobStatus.RUNNING, AIJobStatus.FAILED, AIJobStatus.TIMED_OUT},
    AIJobStatus.RUNNING: {AIJobStatus.SUCCEEDED, AIJobStatus.FAILED, AIJobStatus.TIMED_OUT},
    AIJobStatus.SUCCEEDED: set(),
    AIJobStatus.FAILED: set(),
    AIJobStatus.TIMED_OUT: set(),
}


class AIJobRepository(BaseRepository[AIJob]):
    """Data access for AI job records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AIJob, session)

    async def get_for_user(self, *, job_uuid: uuid_pkg.UUID, user_id: int) -> AIJob | None:
        return await self.get(uuid=job_uuid, user_id=user_id)

    async def create_pending_job(
        self,
        *,
        user_id: int,
        action: str,
        prompt: str,
        document_ids: list[str],
        metadata_payload: dict,
        max_attempts: int = 3,
    ) -> AIJob:
        job = AIJob(
            user_id=user_id,
            action=action,
            prompt=prompt,
            document_ids=document_ids,
            metadata_payload=metadata_payload,
            status=AIJobStatus.PENDING,
            progress=0,
            attempt=1,
            max_attempts=max_attempts,
            queued_at=datetime.now(UTC),
        )
        return await self.create(job)

    async def transition_status(
        self,
        *,
        job: AIJob,
        to_status: AIJobStatus,
        progress: int | None = None,
        attempt: int | None = None,
        result_payload: dict | None = None,
        error_payload: dict | None = None,
    ) -> AIJob:
        if to_status not in _ALLOWED_TRANSITIONS[job.status] and job.status != to_status:
            msg = f"Illegal AI job transition from {job.status.value} to {to_status.value}"
            raise ValueError(msg)

        job.status = to_status
        if progress is not None:
            job.progress = progress
        if attempt is not None:
            job.attempt = attempt
        if result_payload is not None:
            job.result_payload = result_payload
        if error_payload is not None:
            job.error_payload = error_payload

        if to_status == AIJobStatus.RUNNING and job.started_at is None:
            job.started_at = datetime.now(UTC)
        if to_status in {AIJobStatus.SUCCEEDED, AIJobStatus.FAILED, AIJobStatus.TIMED_OUT}:
            job.completed_at = datetime.now(UTC)

        return await self.update(job)
