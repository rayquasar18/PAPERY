"""Project domain ORM models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

import uuid as uuid_pkg

from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class ProjectMemberRole(str, Enum):
    """ACL role for project membership."""

    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class Project(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Project container entity."""

    __tablename__ = "project"

    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped["User"] = relationship("User", lazy="selectin")
    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectMember(Base, TimestampMixin, UUIDMixin):
    """Membership link between user and project."""

    __tablename__ = "project_member"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member_project_user"),)

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[ProjectMemberRole] = mapped_column(
        SAEnum(ProjectMemberRole, name="project_member_role", native_enum=False),
        nullable=False,
        default=ProjectMemberRole.VIEWER,
    )

    project: Mapped[Project] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User", lazy="selectin")


class ProjectInvite(Base, TimestampMixin, UUIDMixin):
    """Project invitation with one-time acceptance and fixed role."""

    __tablename__ = "project_invite"

    project_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invited_by_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invitee_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    role: Mapped[ProjectMemberRole] = mapped_column(
        SAEnum(ProjectMemberRole, name="project_invite_role", native_enum=False),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship("Project", lazy="selectin")
    invited_by_user: Mapped["User"] = relationship("User", foreign_keys=[invited_by_user_id], lazy="selectin")
    accepted_by_user: Mapped["User"] = relationship("User", foreign_keys=[accepted_by_user_id], lazy="selectin")


def hash_invite_token(token: str) -> str:
    """Hash invite token with existing security helper."""
    from app.core.security import hash_password

    return hash_password(token)


def verify_invite_token(token: str, token_hash: str) -> bool:
    """Verify invite token against stored hash using existing helper."""
    from app.core.security import verify_password

    return verify_password(token, token_hash)


def generate_invite_token() -> str:
    """Generate random invite token."""
    return str(uuid_pkg.uuid4())
