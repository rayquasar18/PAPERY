"""AI job polling-first API flow tests."""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import NotFoundError


async def test_submit_endpoint_returns_pending_job_immediately(async_client) -> None:
    from app.api.dependencies import get_current_active_user
    from app.main import app

    user = MagicMock()
    user.id = 101
    user.uuid = uuid_pkg.uuid4()
    user.is_active = True

    app.dependency_overrides[get_current_active_user] = lambda: user

    job_uuid = uuid_pkg.uuid4()
    submitted = SimpleNamespace(
        uuid=job_uuid,
        status="pending",
        action="summarize",
        created_at=datetime.now(UTC),
    )

    with patch("app.api.v1.ai_jobs.AIJobService") as service_cls:
        service = service_cls.return_value
        service.submit_job = AsyncMock(return_value=submitted)

        response = await async_client.post(
            "/api/v1/ai-jobs",
            json={
                "action": "summarize",
                "prompt": "Summarize this",
                "document_ids": ["doc-1"],
                "metadata": {},
            },
        )

    app.dependency_overrides.pop(get_current_active_user, None)

    assert response.status_code == 202
    body = response.json()
    assert body["job_id"] == str(job_uuid)
    assert body["status"] == "pending"


async def test_status_endpoint_returns_only_owned_job_state(async_client) -> None:
    from app.api.dependencies import get_current_active_user
    from app.main import app

    user = MagicMock()
    user.id = 101
    user.uuid = uuid_pkg.uuid4()
    user.is_active = True

    app.dependency_overrides[get_current_active_user] = lambda: user

    job_uuid = uuid_pkg.uuid4()
    status_payload = SimpleNamespace(
        uuid=job_uuid,
        status="running",
        action="summarize",
        progress=45,
        attempt=1,
        max_attempts=3,
        result_payload=None,
        error_payload=None,
        updated_at=datetime.now(UTC),
    )

    with patch("app.api.v1.ai_jobs.AIJobService") as service_cls:
        service = service_cls.return_value
        service.get_job_status_for_user = AsyncMock(return_value=status_payload)

        response = await async_client.get(f"/api/v1/ai-jobs/{job_uuid}")

    app.dependency_overrides.pop(get_current_active_user, None)

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == str(job_uuid)
    assert body["status"] == "running"
    assert body["progress"] == 45


async def test_status_endpoint_hides_foreign_or_missing_job(async_client) -> None:
    from app.api.dependencies import get_current_active_user
    from app.main import app

    user = MagicMock()
    user.id = 101
    user.uuid = uuid_pkg.uuid4()
    user.is_active = True

    app.dependency_overrides[get_current_active_user] = lambda: user

    job_uuid = uuid_pkg.uuid4()

    with patch("app.api.v1.ai_jobs.AIJobService") as service_cls:
        service = service_cls.return_value
        service.get_job_status_for_user = AsyncMock(side_effect=NotFoundError(detail="Job not found"))

        response = await async_client.get(f"/api/v1/ai-jobs/{job_uuid}")

    app.dependency_overrides.pop(get_current_active_user, None)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
