"""Project listing endpoint tests."""

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


async def test_list_projects_returns_owned_and_shared(async_client: AsyncClient) -> None:
    from app.api.dependencies import get_current_active_user
    from app.main import app

    user = _user(50)
    app.dependency_overrides[get_current_active_user] = lambda: user

    now = datetime.now(UTC)
    owned = {
        "uuid": str(uuid_pkg.uuid4()),
        "owner_id": user.id,
        "name": "Owned Project",
        "description": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "relationship_type": "owned",
    }
    shared = {
        "uuid": str(uuid_pkg.uuid4()),
        "owner_id": 999,
        "name": "Shared Project",
        "description": "x",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "relationship_type": "shared",
    }

    with patch("app.api.v1.projects.ProjectService") as svc_cls:
        svc = svc_cls.return_value
        svc.list_projects_for_user = AsyncMock(
            return_value=SimpleNamespace(items=[owned, shared], page=1, per_page=20, total=2)
        )

        response = await async_client.get("/api/v1/projects")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert {item["relationship_type"] for item in body["items"]} == {"owned", "shared"}

    app.dependency_overrides.clear()


async def test_list_projects_supports_search(async_client: AsyncClient) -> None:
    from app.api.dependencies import get_current_active_user
    from app.main import app

    user = _user(51)
    app.dependency_overrides[get_current_active_user] = lambda: user

    with patch("app.api.v1.projects.ProjectService") as svc_cls:
        svc = svc_cls.return_value
        svc.list_projects_for_user = AsyncMock(
            return_value=SimpleNamespace(items=[], page=1, per_page=20, total=0)
        )

        response = await async_client.get("/api/v1/projects", params={"search": "paper"})
        assert response.status_code == 200
        svc.list_projects_for_user.assert_awaited_once()
        _, kwargs = svc.list_projects_for_user.await_args
        assert kwargs["search"] == "paper"

    app.dependency_overrides.clear()
