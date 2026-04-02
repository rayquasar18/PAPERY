"""SQLAlchemy base model and mixins for all PAPERY models."""
import uuid as uuid_pkg
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Abstract base for all models. Provides auto-increment BigInteger PK."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )


class UUIDMixin:
    """Adds a public-facing UUID column. Used as API identifier instead of id."""

    uuid: Mapped[uuid_pkg.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid_pkg.uuid4,
        unique=True,
        nullable=False,
        index=True,
    )


class TimestampMixin:
    """Adds created_at and updated_at columns with server-side defaults."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """Soft delete via deleted_at timestamp. Records are never physically deleted."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Return True if this record has been soft-deleted."""
        return self.deleted_at is not None
