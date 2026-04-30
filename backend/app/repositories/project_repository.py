"""Project repository — data access for project entities."""

from __future__ import annotations

import uuid as uuid_pkg

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectMember, ProjectMemberRole
from app.schemas.project import ProjectListItemRead
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

    async def list_projects_for_user(
        self,
        *,
        user_id: int,
        search: str | None,
        page: int,
        per_page: int,
    ) -> tuple[list[ProjectListItemRead], int]:
        relationship_type = case(
            (Project.owner_id == user_id, "owned"),
            else_="shared",
        ).label("relationship_type")

        stmt = (
            select(Project, relationship_type)
            .outerjoin(ProjectMember, ProjectMember.project_id == Project.id)
            .where(Project.deleted_at.is_(None))
            .where(or_(Project.owner_id == user_id, ProjectMember.user_id == user_id))
        )

        if search:
            stmt = stmt.where(Project.name.ilike(f"%{search.strip()}%"))

        stmt = stmt.distinct(Project.id).order_by(Project.updated_at.desc())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self._session.execute(count_stmt)
        total = int(count_result.scalar_one())

        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        result = await self._session.execute(stmt)

        items: list[ProjectListItemRead] = []
        for project, rel in result.all():
            items.append(
                ProjectListItemRead(
                    uuid=project.uuid,
                    owner_id=project.owner_id,
                    name=project.name,
                    description=project.description,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                    relationship_type=rel,
                )
            )
        return items, total

    async def get_by_uuid(self, *, project_uuid: uuid_pkg.UUID) -> Project | None:
        stmt = select(Project).where(Project.uuid == project_uuid)
        stmt = self._not_deleted(stmt)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_member_by_user(
        self,
        *,
        project_id: int,
        user_id: int,
    ) -> ProjectMember | None:
        stmt = (
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .where(ProjectMember.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_member(self, *, member: ProjectMember, role: ProjectMemberRole) -> ProjectMember:
        member.role = role
        await self._session.commit()
        await self._session.refresh(member)
        return member

    async def find_user_by_email(self, *, email: str):
        from app.models.user import User

        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
