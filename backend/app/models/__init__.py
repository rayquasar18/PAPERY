"""
Model barrel imports — ALL models must be imported here.

Alembic autogenerate relies on this file to discover all models via
Base.metadata. If a model is not imported here, it will NOT be detected
by `alembic revision --autogenerate`.
"""

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.rate_limit_rule import RateLimitRule
from app.models.system_setting import SystemSetting
from app.models.tier import Tier
from app.models.usage_tracking import UsageTracking
from app.models.user import OAuthAccount, User

__all__ = [
    "Base",
    "OAuthAccount",
    "RateLimitRule",
    "SoftDeleteMixin",
    "SystemSetting",
    "Tier",
    "TimestampMixin",
    "UsageTracking",
    "UUIDMixin",
    "User",
]
