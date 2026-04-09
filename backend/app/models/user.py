"""User and OAuthAccount ORM models."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """User account - primary identity entity."""

    __tablename__ = "user"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    # Relationship to OAuth accounts (one user -> many OAuth providers)
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User uuid={self.uuid} email={self.email}>"


class OAuthAccount(Base, TimestampMixin):
    """OAuth provider link - stores third-party identity associations."""

    __tablename__ = "oauth_account"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    # Back-reference to user
    user: Mapped[User] = relationship("User", back_populates="oauth_accounts")

    def __repr__(self) -> str:
        return f"<OAuthAccount provider={self.provider} user_id={self.user_id}>"
