"""Project membership repository for ACL role resolution."""

from __future__ import annotations

import uuid as uuid_pkg

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.repositories.base import BaseRepository


class ProjectMemberRepository(BaseRepository[ProjectMember]):
    """Repository for project membership and ACL queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ProjectMember, session)

    async def get_role_for_user(
        self,
        *,
        project_uuid: uuid_pkg.UUID,
        user_id: int,
    ) -> ProjectMemberRole | None:
        owner_stmt = (
            select(Project.id)
            .where(Project.uuid == project_uuid)
            .where(Project.deleted_at.is_(None))
            .where(Project.owner_id == user_id)
        )
        owner_result = await self._session.execute(owner_stmt)
        if owner_result.scalar_one_or_none() is not None:
            return ProjectMemberRole.OWNER

        member_stmt = (
            select(ProjectMember.role)
            .join(Project, Project.id == ProjectMember.project_id)
            .where(Project.uuid == project_uuid)
            .where(Project.deleted_at.is_(None))
            .where(ProjectMember.user_id == user_id)
        )
        member_result = await self._session.execute(member_stmt)
        return member_result.scalar_one_or_none()

    async def can_read(self, *, project_uuid: uuid_pkg.UUID, user_id: int) -> bool:
        role = await self.get_role_for_user(project_uuid=project_uuid, user_id=user_id)
        return role in {ProjectMemberRole.OWNER, ProjectMemberRole.EDITOR, ProjectMemberRole.VIEWER}

    async def count_owners(self, *, project_id: int) -> int:
        stmt = (
            select(func.count(ProjectMember.id))
            .where(ProjectMember.project_id == project_id)
            .where(ProjectMember.role == ProjectMemberRole.OWNER)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_member_by_uuid(self, *, project_id: int, member_uuid: uuid_pkg.UUID) -> ProjectMember | None:
        stmt = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .where(ProjectMember.uuid == member_uuid)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_member(self, *, project_id: int, user_id: int, role: ProjectMemberRole) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self._session.add(member)
        await self._session.commit()
        await self._session.refresh(member)
        return member

    async def remove_member(self, *, member: ProjectMember) -> None:
        await self._session.delete(member)
        await self._session.commit()
