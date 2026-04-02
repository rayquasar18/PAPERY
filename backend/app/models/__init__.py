"""
Model barrel imports — ALL models must be imported here.

Alembic autogenerate relies on this file to discover all models via
Base.metadata. If a model is not imported here, it will NOT be detected
by `alembic revision --autogenerate`.
"""
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

__all__ = [
    "Base",
    "SoftDeleteMixin",
    "TimestampMixin",
    "UUIDMixin",
]
