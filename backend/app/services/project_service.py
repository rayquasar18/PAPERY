"""Project service — business logic for project CRUD."""

from __future__ import annotations

import uuid as uuid_pkg
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.project import (
    Project,
    ProjectMemberRole,
    generate_invite_token,
    hash_invite_token,
    verify_invite_token,
)
from app.models.user import User
from app.repositories.project_invite_repository import ProjectInviteRepository
from app.repositories.project_member_repository import ProjectMemberRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import (
    ProjectCreate,
    ProjectInviteAcceptRead,
    ProjectInviteCreate,
    ProjectInviteRead,
    ProjectListRead,
    ProjectMemberUpdate,
    ProjectUpdate,
)
from app.services.usage_service import UsageService
from app.utils.email import send_email


class ProjectService:
    """Class-based project service using repository-first data access."""

    def __init__(self, db: AsyncSession) -> None:
        self._repo = ProjectRepository(db)
        self._member_repo = ProjectMemberRepository(db)
        self._invite_repo = ProjectInviteRepository(db)
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

    async def create_invite(
        self,
        *,
        owner: User,
        project_uuid: uuid_pkg.UUID,
        payload: ProjectInviteCreate,
    ) -> ProjectInviteRead:
        project = await self._repo.get_by_uuid(project_uuid=project_uuid)
        if project is None:
            raise NotFoundError(detail="Project not found")
        if project.owner_id != owner.id:
            raise ForbiddenError(detail="Only owner can create invites")

        token = generate_invite_token()
        token_hash = hash_invite_token(token)
        expires_at = datetime.now(UTC) + timedelta(days=7)

        await self._invite_repo.create_invite(
            project_id=project.id,
            invited_by_user_id=owner.id,
            invitee_email=payload.invitee_email,
            role=ProjectMemberRole(payload.role),
            token_hash=token_hash,
            expires_at=expires_at,
        )

        if payload.invitee_email:
            await send_email(
                to=payload.invitee_email,
                subject="Project invite",
                html_body=f"You were invited to a project. Use this token to accept: {token}",
            )

        return ProjectInviteRead(token=token, expires_at=expires_at, role=payload.role)

    async def accept_invite(self, *, user: User, token: str) -> ProjectInviteAcceptRead:
        invite = await self._find_active_invite_by_token(token)
        if invite is None:
            raise NotFoundError(detail="Invite not found or expired")
        if invite.accepted_at is not None:
            raise ConflictError(detail="Invite already used")

        existing = await self._repo.get_member_by_user(project_id=invite.project_id, user_id=user.id)
        if existing is None:
            await self._member_repo.create_member(project_id=invite.project_id, user_id=user.id, role=invite.role)

        await self._invite_repo.mark_accepted(invite=invite, accepted_by_user_id=user.id)

        project_entity = await self._repo.get(id=invite.project_id)
        if project_entity is None:
            raise NotFoundError(detail="Project not found")

        return ProjectInviteAcceptRead(project_uuid=project_entity.uuid, role=invite.role.value)

    async def _find_active_invite_by_token(self, token: str):
        rows = await self._invite_repo.get_multi(skip=0, limit=1000)
        now = datetime.now(UTC)
        for invite in rows:
            if invite.accepted_at is not None:
                continue
            if invite.expires_at <= now:
                continue
            if verify_invite_token(token, invite.token_hash):
                return invite
        return None

    async def update_member_role(
        self,
        *,
        owner: User,
        project_uuid: uuid_pkg.UUID,
        member_uuid: uuid_pkg.UUID,
        payload: ProjectMemberUpdate,
    ):
        project = await self._repo.get_by_uuid(project_uuid=project_uuid)
        if project is None:
            raise NotFoundError(detail="Project not found")
        if project.owner_id != owner.id:
            raise ForbiddenError(detail="Only owner can manage members")

        member = await self._member_repo.get_member_by_uuid(project_id=project.id, member_uuid=member_uuid)
        if member is None:
            raise NotFoundError(detail="Member not found")

        new_role = ProjectMemberRole(payload.role)
        if member.role == ProjectMemberRole.OWNER and new_role != ProjectMemberRole.OWNER:
            owner_count = await self._member_repo.count_owners(project_id=project.id)
            if owner_count <= 1:
                raise ConflictError(detail="Project must retain at least one owner")

        return await self._repo.update_member(member=member, role=new_role)

    async def remove_member(
        self,
        *,
        owner: User,
        project_uuid: uuid_pkg.UUID,
        member_uuid: uuid_pkg.UUID,
    ) -> None:
        project = await self._repo.get_by_uuid(project_uuid=project_uuid)
        if project is None:
            raise NotFoundError(detail="Project not found")
        if project.owner_id != owner.id:
            raise ForbiddenError(detail="Only owner can manage members")

        member = await self._member_repo.get_member_by_uuid(project_id=project.id, member_uuid=member_uuid)
        if member is None:
            raise NotFoundError(detail="Member not found")

        if member.role == ProjectMemberRole.OWNER:
            owner_count = await self._member_repo.count_owners(project_id=project.id)
            if owner_count <= 1:
                raise ConflictError(detail="Project must retain at least one owner")

        await self._member_repo.remove_member(member=member)

    async def list_projects_for_user(
        self,
        *,
        user: User,
        search: str | None,
        page: int,
        per_page: int,
    ) -> ProjectListRead:
        items, total = await self._repo.list_projects_for_user(
            user_id=user.id,
            search=search,
            page=page,
            per_page=per_page,
        )
        return ProjectListRead(items=items, page=page, per_page=per_page, total=total)
