"""Project member management tests."""

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


async def test_owner_can_update_and_remove_member(async_client: AsyncClient) -> None:
    from app.api.dependencies import get_current_active_user, require_project_admin_access
    from app.main import app

    owner = _user(40)
    project_uuid = uuid_pkg.uuid4()
    member_uuid = uuid_pkg.uuid4()

    app.dependency_overrides[get_current_active_user] = lambda: owner
    app.dependency_overrides[require_project_admin_access] = lambda: owner

    with patch("app.api.v1.projects.ProjectService") as svc_cls:
        svc = svc_cls.return_value
        svc.update_member_role = AsyncMock(return_value=SimpleNamespace())
        svc.remove_member = AsyncMock(return_value=None)
        svc.get_project_for_user = AsyncMock(
            return_value=SimpleNamespace(
                uuid=project_uuid,
                owner_id=owner.id,
                name="P",
                description=None,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )

        patch_resp = await async_client.patch(
            f"/api/v1/projects/{project_uuid}/members/{member_uuid}",
            json={"role": "viewer"},
        )
        delete_resp = await async_client.delete(
            f"/api/v1/projects/{project_uuid}/members/{member_uuid}"
        )

        assert patch_resp.status_code == 200
        assert delete_resp.status_code == 204

    app.dependency_overrides.clear()


async def test_non_owner_cannot_manage_members(async_client: AsyncClient) -> None:
    from app.api.dependencies import ForbiddenError, get_current_active_user, require_project_admin_access
    from app.main import app

    editor = _user(41)
    project_uuid = uuid_pkg.uuid4()
    member_uuid = uuid_pkg.uuid4()

    app.dependency_overrides[get_current_active_user] = lambda: editor

    async def deny_admin() -> MagicMock:
        raise ForbiddenError(detail="Insufficient project permissions")

    app.dependency_overrides[require_project_admin_access] = deny_admin

    patch_resp = await async_client.patch(
        f"/api/v1/projects/{project_uuid}/members/{member_uuid}",
        json={"role": "viewer"},
    )
    delete_resp = await async_client.delete(f"/api/v1/projects/{project_uuid}/members/{member_uuid}")

    assert patch_resp.status_code == 403
    assert delete_resp.status_code == 403

    app.dependency_overrides.clear()
