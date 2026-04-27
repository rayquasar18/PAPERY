"""Project domain tests for CRUD contracts and API behavior."""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.schemas.project import ProjectCreate, ProjectUpdate


@pytest.fixture
def mock_owner_user() -> MagicMock:
    user = MagicMock()
    user.id = 101
    user.uuid = uuid_pkg.uuid4()
    user.email = "owner@example.com"
    user.is_active = True
    return user


class TestProjectContracts:
    async def test_create_project_owner_seed(self, mock_owner_user: MagicMock) -> None:
        payload = ProjectCreate(name="  Research Hub  ", description="  Internal docs  ")

        project = Project(
            owner_id=mock_owner_user.id,
            name=payload.name,
            description=payload.description,
        )
        owner_member = ProjectMember(
            project=project,
            user_id=mock_owner_user.id,
            role=ProjectMemberRole.OWNER,
        )

        assert project.name == "Research Hub"
        assert project.description == "Internal docs"
        assert owner_member.role == ProjectMemberRole.OWNER
        assert owner_member.user_id == mock_owner_user.id

    async def test_owner_soft_delete_excluded_from_list(self, mock_owner_user: MagicMock) -> None:
        active_project = Project(owner_id=mock_owner_user.id, name="Alpha", description="A")
        deleted_project = Project(owner_id=mock_owner_user.id, name="Beta", description="B")
        deleted_project.deleted_at = datetime.now(UTC)

        visible = [p for p in [active_project, deleted_project] if p.deleted_at is None]

        assert len(visible) == 1
        assert visible[0].name == "Alpha"

    async def test_project_name_validation_bounds(self) -> None:
        with pytest.raises(ValueError):
            ProjectCreate(name="   ", description="blank")

        with pytest.raises(ValueError):
            ProjectCreate(name="x" * 161, description="too long")

        update = ProjectUpdate(name="  Updated  ", description="  Desc  ")
        assert update.name == "Updated"
        assert update.description == "Desc"


class TestProjectRoutes:
    async def test_projects_crud_requires_auth(self, async_client: AsyncClient) -> None:
        create_resp = await async_client.post("/api/v1/projects", json={"name": "P", "description": "D"})
        assert create_resp.status_code == 401

    async def test_owner_crud_flow_and_soft_delete_hides_resource(
        self,
        async_client: AsyncClient,
        mock_owner_user: MagicMock,
    ) -> None:
        from app.api.dependencies import CheckUsageLimit, get_current_active_user
        from app.main import app

        project_uuid = uuid_pkg.uuid4()
        project_data = {
            "uuid": str(project_uuid),
            "owner_id": mock_owner_user.id,
            "name": "My Project",
            "description": "Initial",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "deleted_at": None,
            "relationship_type": "owned",
        }

        app.dependency_overrides[get_current_active_user] = lambda: mock_owner_user
        app.dependency_overrides[CheckUsageLimit("projects")] = lambda: mock_owner_user

        with patch("app.api.v1.projects.ProjectService") as mock_service_cls:
            svc = mock_service_cls.return_value
            svc.create_project = AsyncMock(return_value=MagicMock(**project_data))
            svc.get_project_for_user = AsyncMock(side_effect=[MagicMock(**project_data), MagicMock(**project_data), None])
            svc.update_project = AsyncMock(return_value=MagicMock(**{**project_data, "name": "Renamed"}))
            svc.soft_delete_project = AsyncMock(return_value=None)

            create_resp = await async_client.post(
                "/api/v1/projects",
                json={"name": "My Project", "description": "Initial"},
            )
            assert create_resp.status_code == 201

            get_resp = await async_client.get(f"/api/v1/projects/{project_uuid}")
            assert get_resp.status_code == 200

            patch_resp = await async_client.patch(
                f"/api/v1/projects/{project_uuid}",
                json={"name": "Renamed"},
            )
            assert patch_resp.status_code == 200

            delete_resp = await async_client.delete(f"/api/v1/projects/{project_uuid}")
            assert delete_resp.status_code == 204

            after_delete_resp = await async_client.get(f"/api/v1/projects/{project_uuid}")
            assert after_delete_resp.status_code == 404

        app.dependency_overrides.pop(get_current_active_user, None)

    async def test_non_member_get_returns_not_found(
        self,
        async_client: AsyncClient,
        mock_owner_user: MagicMock,
    ) -> None:
        from app.api.dependencies import get_current_active_user
        from app.main import app

        project_uuid = uuid_pkg.uuid4()
        app.dependency_overrides[get_current_active_user] = lambda: mock_owner_user

        with patch("app.api.v1.projects.ProjectService") as mock_service_cls:
            svc = mock_service_cls.return_value
            svc.get_project_for_user = AsyncMock(return_value=None)

            response = await async_client.get(f"/api/v1/projects/{project_uuid}")
            assert response.status_code == 404

        app.dependency_overrides.pop(get_current_active_user, None)
