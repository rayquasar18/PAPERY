"""Resilience behavior tests for AI job service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.schemas.ai_job import AIJobErrorDetail, AIJobStatus
from app.services.ai_job_service import AIJobService, CircuitState


async def test_mark_retryable_failure_requeues_before_terminal(mock_db_session) -> None:
    service = AIJobService(mock_db_session)
    job = SimpleNamespace(uuid="job-1", max_attempts=3)
    service._repo.get = lambda **_: job
    service._repo.transition_status = lambda **kwargs: kwargs["job"]

    calls = {}

    async def fake_get(**kwargs):
        return job

    async def fake_transition_status(**kwargs):
        calls.update(kwargs)
        return kwargs["job"]

    service._repo.get = fake_get
    service._repo.transition_status = fake_transition_status

    error = AIJobErrorDetail(code="UPSTREAM_TIMEOUT", message="timeout", retriable=True)
    await service.mark_retryable_failure(job_id=job.uuid, error=error, attempt=1)

    assert calls["to_status"] == AIJobStatus.PENDING
    assert calls["attempt"] == 2


async def test_mark_retryable_failure_times_out_terminally(mock_db_session) -> None:
    service = AIJobService(mock_db_session)
    job = SimpleNamespace(uuid="job-2", max_attempts=3)
    calls = {}

    async def fake_get(**kwargs):
        return job

    async def fake_transition_status(**kwargs):
        calls.update(kwargs)
        return kwargs["job"]

    service._repo.get = fake_get
    service._repo.transition_status = fake_transition_status

    error = AIJobErrorDetail(code="TIMEOUT", message="timed out", retriable=True)
    await service.mark_retryable_failure(job_id=job.uuid, error=error, attempt=3)

    assert calls["to_status"] == AIJobStatus.TIMED_OUT
    assert calls["attempt"] == 3


def test_circuit_breaker_opens_after_threshold(mock_db_session) -> None:
    service = AIJobService(mock_db_session)
    service._circuit_state = CircuitState()

    service._register_failure()
    service._register_failure()
    assert service.is_circuit_open() is False

    service._register_failure()
    assert service.is_circuit_open() is True


def test_circuit_breaker_recovers_after_window(mock_db_session) -> None:
    service = AIJobService(mock_db_session)
    service._circuit_state = CircuitState(
        failure_count=service.CIRCUIT_FAIL_THRESHOLD,
        opened_until=datetime.now(UTC) - timedelta(seconds=1),
    )

    assert service.is_circuit_open() is False
