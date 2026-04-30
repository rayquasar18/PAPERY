"""Project invite flow tests."""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient


def _user(user_id: int) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.uuid = uuid_pkg.uuid4()
    user.email = f"u{user_id}@example.com"
    user.is_active = True
    return user


async def test_owner_can_create_invite_link(async_client: AsyncClient) -> None:
    from app.api.dependencies import get_current_active_user, require_project_admin_access
    from app.main import app

    owner = _user(30)
    project_uuid = uuid_pkg.uuid4()
    app.dependency_overrides[get_current_active_user] = lambda: owner
    app.dependency_overrides[require_project_admin_access] = lambda: owner

    with patch("app.api.v1.projects.ProjectService") as svc_cls:
        svc = svc_cls.return_value
        svc.create_invite = AsyncMock(
            return_value=SimpleNamespace(
                token="token-1",
                role="editor",
                expires_at=datetime.now(UTC) + timedelta(days=7),
            )
        )

        response = await async_client.post(
            f"/api/v1/projects/{project_uuid}/invites",
            json={"role": "editor"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["role"] == "editor"
        assert body["token"] == "token-1"

    app.dependency_overrides.clear()


async def test_accept_invite_endpoint(async_client: AsyncClient) -> None:
    from app.api.dependencies import get_current_active_user
    from app.main import app

    user = _user(31)
    app.dependency_overrides[get_current_active_user] = lambda: user

    with patch("app.api.v1.projects.ProjectService") as svc_cls:
        svc = svc_cls.return_value
        svc.accept_invite = AsyncMock(
            return_value=SimpleNamespace(project_uuid=uuid_pkg.uuid4(), role="viewer")
        )

        response = await async_client.post(
            "/api/v1/projects/invites/accept",
            json={"token": "abc"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["role"] == "viewer"

    app.dependency_overrides.clear()
