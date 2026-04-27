"""Project route handlers — project CRUD endpoints."""

from __future__ import annotations

import uuid as uuid_pkg

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CheckUsageLimit, get_current_active_user
from app.core.db.session import get_session
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])
create_project_usage_guard = CheckUsageLimit("projects")


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
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> ProjectRead:
    service = ProjectService(db)
    project = await service.get_project_for_user(user, project_uuid)
    return ProjectRead.model_validate(project)


@router.patch("/{project_uuid}", response_model=ProjectRead)
async def update_project(
    project_uuid: uuid_pkg.UUID,
    payload: ProjectUpdate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> ProjectRead:
    service = ProjectService(db)
    project = await service.update_project(user, project_uuid, payload)
    return ProjectRead.model_validate(project)


@router.delete("/{project_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_uuid: uuid_pkg.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    service = ProjectService(db)
    await service.soft_delete_project(user, project_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
