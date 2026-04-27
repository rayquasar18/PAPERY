"""Project domain ORM models."""

from __future__ import annotations

from enum import Enum

from sqlalchemy import BigInteger, Enum as SAEnum, ForeignKey, String, Text, UniqueConstraint
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


class ProjectMember(Base, TimestampMixin):
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
