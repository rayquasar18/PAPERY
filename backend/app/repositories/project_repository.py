"""Project repository — data access for project entities."""

from __future__ import annotations

import uuid as uuid_pkg

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository for project reads/writes with ACL-scoped lookups."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Project, session)

    async def get_by_uuid_for_owner_or_member(
        self,
        *,
        project_uuid: uuid_pkg.UUID,
        user_id: int,
    ) -> Project | None:
        stmt = (
            select(Project)
            .options(selectinload(Project.members))
            .outerjoin(ProjectMember, ProjectMember.project_id == Project.id)
            .where(Project.uuid == project_uuid)
            .where(or_(Project.owner_id == user_id, ProjectMember.user_id == user_id))
        )
        stmt = self._not_deleted(stmt)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_project_with_owner_member(
        self,
        *,
        owner_id: int,
        name: str,
        description: str | None,
    ) -> Project:
        project = Project(owner_id=owner_id, name=name, description=description)
        self._session.add(project)
        await self._session.flush()

        owner_member = ProjectMember(
            project_id=project.id,
            user_id=owner_id,
            role=ProjectMemberRole.OWNER,
        )
        self._session.add(owner_member)

        await self._session.commit()
        await self._session.refresh(project)
        return project
