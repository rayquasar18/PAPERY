"""Project ACL tests for owner/editor/viewer matrix."""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import UTC, datetime
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


async def test_owner_can_read_write_admin(async_client: AsyncClient) -> None:
    from app.api.dependencies import (
        get_current_active_user,
        require_project_admin_access,
        require_project_read_access,
        require_project_write_access,
    )
    from app.main import app

    owner = _user(10)
    project_uuid = uuid_pkg.uuid4()
    project_data = {
        "uuid": project_uuid,
        "owner_id": owner.id,
        "name": "Owner Project",
        "description": "desc",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }

    app.dependency_overrides[get_current_active_user] = lambda: owner
    app.dependency_overrides[require_project_read_access] = lambda: owner
    app.dependency_overrides[require_project_write_access] = lambda: owner
    app.dependency_overrides[require_project_admin_access] = lambda: owner

    with patch("app.api.v1.projects.ProjectService") as mock_service_cls:
        svc = mock_service_cls.return_value
        svc.get_project_for_user = AsyncMock(return_value=SimpleNamespace(**project_data))
        svc.update_project = AsyncMock(return_value=SimpleNamespace(**project_data))
        svc.soft_delete_project = AsyncMock(return_value=None)

        get_resp = await async_client.get(f"/api/v1/projects/{project_uuid}")
        patch_resp = await async_client.patch(f"/api/v1/projects/{project_uuid}", json={"name": "N"})
        delete_resp = await async_client.delete(f"/api/v1/projects/{project_uuid}")

        assert get_resp.status_code == 200
        assert patch_resp.status_code == 200
        assert delete_resp.status_code == 204

    app.dependency_overrides.clear()


async def test_editor_can_read_write_but_not_admin(async_client: AsyncClient) -> None:
    from app.api.dependencies import (
        ForbiddenError,
        get_current_active_user,
        require_project_admin_access,
        require_project_read_access,
        require_project_write_access,
    )
    from app.main import app

    editor = _user(11)
    project_uuid = uuid_pkg.uuid4()
    project_data = {
        "uuid": project_uuid,
        "owner_id": 10,
        "name": "Editor Project",
        "description": "desc",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }

    app.dependency_overrides[get_current_active_user] = lambda: editor
    app.dependency_overrides[require_project_read_access] = lambda: editor
    app.dependency_overrides[require_project_write_access] = lambda: editor

    async def deny_admin() -> MagicMock:
        raise ForbiddenError(detail="Insufficient project permissions")

    app.dependency_overrides[require_project_admin_access] = deny_admin

    with patch("app.api.v1.projects.ProjectService") as mock_service_cls:
        svc = mock_service_cls.return_value
        svc.get_project_for_user = AsyncMock(return_value=SimpleNamespace(**project_data))
        svc.update_project = AsyncMock(return_value=SimpleNamespace(**project_data))

        get_resp = await async_client.get(f"/api/v1/projects/{project_uuid}")
        patch_resp = await async_client.patch(f"/api/v1/projects/{project_uuid}", json={"name": "N"})
        delete_resp = await async_client.delete(f"/api/v1/projects/{project_uuid}")

        assert get_resp.status_code == 200
        assert patch_resp.status_code == 200
        assert delete_resp.status_code == 403

    app.dependency_overrides.clear()


async def test_viewer_read_only(async_client: AsyncClient) -> None:
    from app.api.dependencies import (
        ForbiddenError,
        get_current_active_user,
        require_project_admin_access,
        require_project_read_access,
        require_project_write_access,
    )
    from app.main import app

    viewer = _user(12)
    project_uuid = uuid_pkg.uuid4()
    project_data = {
        "uuid": project_uuid,
        "owner_id": 10,
        "name": "Viewer Project",
        "description": "desc",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }

    app.dependency_overrides[get_current_active_user] = lambda: viewer
    app.dependency_overrides[require_project_read_access] = lambda: viewer

    async def deny_write() -> MagicMock:
        raise ForbiddenError(detail="Insufficient project permissions")

    async def deny_admin() -> MagicMock:
        raise ForbiddenError(detail="Insufficient project permissions")

    app.dependency_overrides[require_project_write_access] = deny_write
    app.dependency_overrides[require_project_admin_access] = deny_admin

    with patch("app.api.v1.projects.ProjectService") as mock_service_cls:
        svc = mock_service_cls.return_value
        svc.get_project_for_user = AsyncMock(return_value=SimpleNamespace(**project_data))

        get_resp = await async_client.get(f"/api/v1/projects/{project_uuid}")
        patch_resp = await async_client.patch(f"/api/v1/projects/{project_uuid}", json={"name": "N"})
        delete_resp = await async_client.delete(f"/api/v1/projects/{project_uuid}")

        assert get_resp.status_code == 200
        assert patch_resp.status_code == 403
        assert delete_resp.status_code == 403

    app.dependency_overrides.clear()
