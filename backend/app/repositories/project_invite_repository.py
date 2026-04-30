"""Project invite repository for invite lifecycle management."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectInvite
from app.repositories.base import BaseRepository


class ProjectInviteRepository(BaseRepository[ProjectInvite]):
    """Repository for invite persistence and one-time consume flow."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ProjectInvite, session)

    async def create_invite(
        self,
        *,
        project_id: int,
        invited_by_user_id: int,
        invitee_email: str | None,
        role,
        token_hash: str,
        expires_at: datetime,
    ) -> ProjectInvite:
        invite = ProjectInvite(
            project_id=project_id,
            invited_by_user_id=invited_by_user_id,
            invitee_email=invitee_email,
            role=role,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(invite)
        await self._session.commit()
        await self._session.refresh(invite)
        return invite

    async def get_active_invite_by_hash(self, *, token_hash: str) -> ProjectInvite | None:
        stmt = (
            select(ProjectInvite)
            .where(ProjectInvite.token_hash == token_hash)
            .where(ProjectInvite.accepted_at.is_(None))
            .where(ProjectInvite.expires_at > datetime.now(UTC))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_accepted(self, *, invite: ProjectInvite, accepted_by_user_id: int) -> ProjectInvite:
        invite.accepted_by_user_id = accepted_by_user_id
        invite.accepted_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(invite)
        return invite
