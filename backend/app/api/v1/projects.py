"""Project route handlers — project CRUD endpoints."""

from __future__ import annotations

import uuid as uuid_pkg

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    CheckUsageLimit,
    get_current_active_user,
    require_project_admin_access,
    require_project_read_access,
    require_project_write_access,
)
from app.core.db.session import get_session
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectInviteAcceptRead,
    ProjectInviteAcceptRequest,
    ProjectInviteCreate,
    ProjectInviteRead,
    ProjectListRead,
    ProjectMemberUpdate,
    ProjectRead,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])
create_project_usage_guard = CheckUsageLimit("projects")


@router.get("", response_model=ProjectListRead)
async def list_projects(
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> ProjectListRead:
    service = ProjectService(db)
    return await service.list_projects_for_user(user=user, search=search, page=page, per_page=per_page)


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(create_project_usage_guard)],
)
async def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> ProjectRead:
    service = ProjectService(db)
    project = await service.create_project(user, payload)
    return ProjectRead.model_validate(project)


@router.get("/{project_uuid}", response_model=ProjectRead)
async def get_project(
    project_uuid: uuid_pkg.UUID,
    user: User = Depends(require_project_read_access),
    db: AsyncSession = Depends(get_session),
) -> ProjectRead:
    service = ProjectService(db)
    project = await service.get_project_for_user(user, project_uuid)
    return ProjectRead.model_validate(project)


@router.patch("/{project_uuid}", response_model=ProjectRead)
async def update_project(
    project_uuid: uuid_pkg.UUID,
    payload: ProjectUpdate,
    user: User = Depends(require_project_write_access),
    db: AsyncSession = Depends(get_session),
) -> ProjectRead:
    service = ProjectService(db)
    project = await service.update_project(user, project_uuid, payload)
    return ProjectRead.model_validate(project)


@router.delete("/{project_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_uuid: uuid_pkg.UUID,
    user: User = Depends(require_project_admin_access),
    db: AsyncSession = Depends(get_session),
) -> Response:
    service = ProjectService(db)
    await service.soft_delete_project(user, project_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_uuid}/invites", response_model=ProjectInviteRead)
async def create_project_invite(
    project_uuid: uuid_pkg.UUID,
    payload: ProjectInviteCreate,
    user: User = Depends(require_project_admin_access),
    db: AsyncSession = Depends(get_session),
) -> ProjectInviteRead:
    service = ProjectService(db)
    return await service.create_invite(owner=user, project_uuid=project_uuid, payload=payload)


@router.post("/invites/accept", response_model=ProjectInviteAcceptRead)
async def accept_project_invite(
    payload: ProjectInviteAcceptRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> ProjectInviteAcceptRead:
    service = ProjectService(db)
    return await service.accept_invite(user=user, token=payload.token)


@router.patch("/{project_uuid}/members/{member_uuid}", response_model=ProjectRead)
async def update_project_member(
    project_uuid: uuid_pkg.UUID,
    member_uuid: uuid_pkg.UUID,
    payload: ProjectMemberUpdate,
    user: User = Depends(require_project_admin_access),
    db: AsyncSession = Depends(get_session),
) -> ProjectRead:
    service = ProjectService(db)
    member = await service.update_member_role(
        owner=user,
        project_uuid=project_uuid,
        member_uuid=member_uuid,
        payload=payload,
    )
    project = await service.get_project_for_user(user, project_uuid)
    _ = member
    return ProjectRead.model_validate(project)


@router.delete("/{project_uuid}/members/{member_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_uuid: uuid_pkg.UUID,
    member_uuid: uuid_pkg.UUID,
    user: User = Depends(require_project_admin_access),
    db: AsyncSession = Depends(get_session),
) -> Response:
    service = ProjectService(db)
    await service.remove_member(owner=user, project_uuid=project_uuid, member_uuid=member_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
