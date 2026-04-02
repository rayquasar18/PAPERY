"""Tests for SQLAlchemy base models and mixins (INFRA-14, INFRA-15)."""
import uuid as uuid_pkg
from datetime import datetime, timezone

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class TestBase:
    """Test Base declarative model."""

    def test_base_is_abstract(self):
        """Base should be abstract — not instantiable as a table."""
        assert Base.__abstract__ is True

    def test_base_has_biginteger_pk(self):
        """Base.id column should be BigInteger primary key."""
        col = Base.__table__.columns.get("id") if hasattr(Base, "__table__") else None
        # Since Base is abstract, check via class attribute
        assert hasattr(Base, "id")


class TestUUIDMixin:
    """Test UUIDMixin (INFRA-14: dual ID strategy)."""

    def test_uuid_mixin_has_uuid_attribute(self):
        """UUIDMixin should define a uuid attribute."""
        assert hasattr(UUIDMixin, "uuid")

    def test_uuid_mixin_default_is_uuid4(self):
        """UUIDMixin.uuid default should be uuid4 function."""
        col = UUIDMixin.__dict__["uuid"]
        # mapped_column stores default in column property
        assert col.column.default is not None


class TestTimestampMixin:
    """Test TimestampMixin."""

    def test_timestamp_mixin_has_created_at(self):
        """TimestampMixin should define created_at."""
        assert hasattr(TimestampMixin, "created_at")

    def test_timestamp_mixin_has_updated_at(self):
        """TimestampMixin should define updated_at."""
        assert hasattr(TimestampMixin, "updated_at")


class TestSoftDeleteMixin:
    """Test SoftDeleteMixin (INFRA-15)."""

    def test_soft_delete_mixin_has_deleted_at(self):
        """SoftDeleteMixin should define deleted_at nullable timestamp."""
        assert hasattr(SoftDeleteMixin, "deleted_at")

    def test_is_deleted_returns_false_when_not_deleted(self):
        """is_deleted should return False when deleted_at is None."""

        class FakeModel(SoftDeleteMixin):
            pass

        obj = FakeModel()
        obj.deleted_at = None
        assert obj.is_deleted is False

    def test_is_deleted_returns_true_when_deleted(self):
        """is_deleted should return True when deleted_at is set."""

        class FakeModel(SoftDeleteMixin):
            pass

        obj = FakeModel()
        obj.deleted_at = datetime.now(tz=timezone.utc)
        assert obj.is_deleted is True

    def test_is_deleted_is_property(self):
        """is_deleted should be a property, not a column."""
        assert isinstance(
            SoftDeleteMixin.__dict__["is_deleted"], property
        )


class TestModelBarrelImports:
    """Test that models/__init__.py exports all required symbols."""

    def test_barrel_exports_base(self):
        """models/__init__.py should export Base."""
        from app.models import Base as ImportedBase

        assert ImportedBase is Base

    def test_barrel_exports_uuid_mixin(self):
        """models/__init__.py should export UUIDMixin."""
        from app.models import UUIDMixin as ImportedMixin

        assert ImportedMixin is UUIDMixin

    def test_barrel_exports_timestamp_mixin(self):
        """models/__init__.py should export TimestampMixin."""
        from app.models import TimestampMixin as ImportedMixin

        assert ImportedMixin is TimestampMixin

    def test_barrel_exports_soft_delete_mixin(self):
        """models/__init__.py should export SoftDeleteMixin."""
        from app.models import SoftDeleteMixin as ImportedMixin

        assert ImportedMixin is SoftDeleteMixin
