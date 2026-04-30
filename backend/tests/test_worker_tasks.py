"""Worker task execution tests for AI job orchestration."""

from __future__ import annotations

import uuid as uuid_pkg
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.ai_job import AIJobStatus


async def test_process_ai_job_marks_running_then_succeeded() -> None:
    from app.worker.tasks.ai_jobs import process_ai_job

    job_id = uuid_pkg.uuid4()
    fake_job = SimpleNamespace(
        uuid=job_id,
        action="summarize",
        prompt="hello",
        document_ids=["doc-1"],
        metadata_payload={},
    )
    provider_result = SimpleNamespace(output={"summary": "done"})

    with (
        patch("app.worker.tasks.ai_jobs.get_session_context") as get_session_context,
        patch("app.worker.tasks.ai_jobs.AIJobService") as service_cls,
    ):
        session = AsyncMock()
        ctx_manager = AsyncMock()
        ctx_manager.__aenter__.return_value = session
        ctx_manager.__aexit__.return_value = False
        get_session_context.return_value = ctx_manager

        service = service_cls.return_value
        service._repo.get = AsyncMock(return_value=fake_job)
        service.mark_running = AsyncMock(return_value=SimpleNamespace(status=AIJobStatus.RUNNING))
        service.build_provider_request = MagicMock(return_value=SimpleNamespace(job_id=str(job_id)))
        service._provider.process_job = MagicMock(return_value=provider_result)
        service.mark_succeeded = AsyncMock(return_value=SimpleNamespace(status=AIJobStatus.SUCCEEDED))

        result = await process_ai_job({"job_id": str(job_id), "attempt": 1})

    assert result["job_id"] == str(job_id)
    assert result["status"] == "succeeded"
    service.mark_running.assert_awaited_once()
    service.mark_succeeded.assert_awaited_once()


async def test_process_ai_job_requeues_retryable_failures() -> None:
    from app.worker.tasks.ai_jobs import process_ai_job

    job_id = uuid_pkg.uuid4()
    fake_job = SimpleNamespace(
        uuid=job_id,
        action="summarize",
        prompt="hello",
        document_ids=[],
        metadata_payload={},
    )

    with (
        patch("app.worker.tasks.ai_jobs.get_session_context") as get_session_context,
        patch("app.worker.tasks.ai_jobs.AIJobService") as service_cls,
        patch("app.worker.tasks.ai_jobs.asyncio.to_thread", new_callable=AsyncMock) as to_thread,
    ):
        session = AsyncMock()
        ctx_manager = AsyncMock()
        ctx_manager.__aenter__.return_value = session
        ctx_manager.__aexit__.return_value = False
        get_session_context.return_value = ctx_manager

        service = service_cls.return_value
        service._repo.get = AsyncMock(return_value=fake_job)
        service.mark_running = AsyncMock(return_value=SimpleNamespace(status=AIJobStatus.RUNNING))
        service.build_provider_request = MagicMock(return_value=SimpleNamespace(job_id=str(job_id)))
        to_thread.side_effect = TimeoutError
        service.mark_retryable_failure = AsyncMock(return_value=SimpleNamespace(status=AIJobStatus.PENDING, attempt=2))

        result = await process_ai_job({"job_id": str(job_id), "attempt": 1})

    assert result["status"] == "pending"
    assert result["attempt"] == 2
    service.mark_retryable_failure.assert_awaited_once()


async def test_process_ai_job_fast_fails_when_circuit_open() -> None:
    from app.worker.tasks.ai_jobs import process_ai_job

    job_id = uuid_pkg.uuid4()
    fake_job = SimpleNamespace(
        uuid=job_id,
        action="summarize",
        prompt="hello",
        document_ids=[],
        metadata_payload={},
    )

    with (
        patch("app.worker.tasks.ai_jobs.get_session_context") as get_session_context,
        patch("app.worker.tasks.ai_jobs.AIJobService") as service_cls,
    ):
        session = AsyncMock()
        ctx_manager = AsyncMock()
        ctx_manager.__aenter__.return_value = session
        ctx_manager.__aexit__.return_value = False
        get_session_context.return_value = ctx_manager

        service = service_cls.return_value
        service._repo.get = AsyncMock(return_value=fake_job)
        service.is_circuit_open = MagicMock(return_value=True)
        service.mark_circuit_open_failure = AsyncMock(return_value=SimpleNamespace(status=AIJobStatus.FAILED))

        result = await process_ai_job({"job_id": str(job_id), "attempt": 1})

    assert result["status"] == "failed"
    service.mark_circuit_open_failure.assert_awaited_once()
