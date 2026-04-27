"""Project service — business logic for project CRUD."""

from __future__ import annotations

import uuid as uuid_pkg

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.project import Project
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.usage_service import UsageService


class ProjectService:
    """Class-based project service using repository-first data access."""

    def __init__(self, db: AsyncSession) -> None:
        self._repo = ProjectRepository(db)
        self._usage_service = UsageService(db)

    async def create_project(self, user: User, payload: ProjectCreate) -> Project:
        project = await self._repo.create_project_with_owner_member(
            owner_id=user.id,
            name=payload.name,
            description=payload.description,
        )
        await self._usage_service.increment_usage(user.id, "projects")
        return project

    async def get_project_for_user(self, user: User, project_uuid: uuid_pkg.UUID) -> Project:
        project = await self._repo.get_by_uuid_for_owner_or_member(project_uuid=project_uuid, user_id=user.id)
        if project is None:
            raise NotFoundError(detail="Project not found")
        return project

    async def update_project(
        self,
        user: User,
        project_uuid: uuid_pkg.UUID,
        payload: ProjectUpdate,
    ) -> Project:
        project = await self.get_project_for_user(user, project_uuid)

        if payload.name is not None:
            project.name = payload.name
        if payload.description is not None:
            project.description = payload.description

        return await self._repo.update(project)

    async def soft_delete_project(self, user: User, project_uuid: uuid_pkg.UUID) -> None:
        project = await self.get_project_for_user(user, project_uuid)
        await self._repo.soft_delete(project)
