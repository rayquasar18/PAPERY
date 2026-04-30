"""ARQ-executable AI job task handlers."""

from __future__ import annotations

import asyncio
import uuid as uuid_pkg
from contextlib import asynccontextmanager
from typing import Any

from app.core.db.session import async_session_factory
from app.schemas.ai_job import AIJobErrorDetail
from app.services.ai_job_service import AIJobService

DEFAULT_TIMEOUT_SECONDS = 3


def _worker_timeout_seconds() -> int:
    """Return stable worker timeout independent of mocked service instances."""

    return DEFAULT_TIMEOUT_SECONDS


@asynccontextmanager
async def get_session_context():
    """Yield an async database session for worker execution."""

    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call db_session.init() first.")
    async with async_session_factory() as session:
        yield session


async def process_ai_job(ctx: dict[str, Any]) -> dict[str, Any]:
    """Process one queued AI job with timeout, retry, and circuit-open handling."""

    job_id = uuid_pkg.UUID(str(ctx["job_id"]))
    attempt = int(ctx.get("attempt", 1))

    async with get_session_context() as db:
        service = AIJobService(db)
        job = await service._repo.get(uuid=job_id)
        if job is None:
            msg = f"AI job {job_id} not found"
            raise ValueError(msg)

        if service.is_circuit_open() is True:
            failed = await service.mark_circuit_open_failure(job_id=job_id)
            return {
                "job_id": str(job_id),
                "status": failed.status.value,
                "attempt": getattr(failed, "attempt", attempt),
            }

        await service.mark_running(job_id=job_id, attempt=attempt)
        request = service.build_provider_request(job=job)

        try:
            provider_result = await asyncio.wait_for(
                asyncio.to_thread(service._provider.process_job, request),
                timeout=_worker_timeout_seconds(),
            )
        except TimeoutError:
            failed = await service.mark_retryable_failure(
                job_id=job_id,
                error=AIJobErrorDetail(code="TIMEOUT", message="Provider execution timed out", retriable=True),
                attempt=attempt,
            )
            return {
                "job_id": str(job_id),
                "status": failed.status.value,
                "attempt": getattr(failed, "attempt", attempt),
            }

        succeeded = await service.mark_succeeded(
            job_id=job_id,
            result_payload=provider_result.output or {},
            attempt=attempt,
        )
        return {
            "job_id": str(job_id),
            "status": succeeded.status.value,
            "attempt": getattr(succeeded, "attempt", attempt),
        }


__all__ = ["get_session_context", "process_ai_job"]
