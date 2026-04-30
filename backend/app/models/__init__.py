"""
Model barrel imports — ALL models must be imported here.

Alembic autogenerate relies on this file to discover all models via
Base.metadata. If a model is not imported here, it will NOT be detected
by `alembic revision --autogenerate`.
"""

from app.models.ai_job import AIJob
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.project import Project, ProjectInvite, ProjectMember, ProjectMemberRole
from app.models.rate_limit_rule import RateLimitRule
from app.models.system_setting import SystemSetting
from app.models.tier import Tier
from app.models.usage_tracking import UsageTracking
from app.models.user import OAuthAccount, User

__all__ = [
    "AIJob",
    "Base",
    "OAuthAccount",
    "Project",
    "ProjectInvite",
    "ProjectMember",
    "ProjectMemberRole",
    "RateLimitRule",
    "SoftDeleteMixin",
    "SystemSetting",
    "Tier",
    "TimestampMixin",
    "UUIDMixin",
    "UsageTracking",
    "User",
]
