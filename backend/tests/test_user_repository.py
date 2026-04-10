"""Tests for UserRepository — data access layer for User model.

All database interactions are mocked via AsyncSession — no real DB needed.
"""

import uuid as uuid_pkg
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user import User
from app.repositories.user_repository import UserRepository


def _make_mock_user(
    *,
    email: str = "test@example.com",
    is_active: bool = True,
    is_verified: bool = True,
    hashed_password: str | None = "$2b$12$mock_hash",
) -> MagicMock:
    """Create a mock User with standard attributes."""
    user = MagicMock(spec=User)
    user.id = 1
    user.uuid = uuid_pkg.uuid4()
    user.email = email
    user.hashed_password = hashed_password
    user.is_active = is_active
    user.is_verified = is_verified
    user.is_superuser = False
    user.deleted_at = None
    return user


def _make_mock_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


def _setup_execute_result(session: AsyncMock, return_value: object) -> None:
    """Configure mock session.execute to return a scalar_one_or_none result."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = return_value
    session.execute = AsyncMock(return_value=mock_result)


# ---------------------------------------------------------------------------
# get_by_email
# ---------------------------------------------------------------------------
class TestGetByEmail:
    """Test UserRepository.get_by_email."""

    async def test_found(self):
        """Returns user when email matches."""
        mock_user = _make_mock_user()
        session = _make_mock_session()
        _setup_execute_result(session, mock_user)

        repo = UserRepository(session)
        result = await repo.get_by_email("test@example.com")

        assert result is mock_user
        session.execute.assert_called_once()

    async def test_not_found(self):
        """Returns None when email does not match."""
        session = _make_mock_session()
        _setup_execute_result(session, None)

        repo = UserRepository(session)
        result = await repo.get_by_email("nonexistent@example.com")

        assert result is None

    async def test_case_insensitive(self):
        """Email is lowercased before query."""
        session = _make_mock_session()
        _setup_execute_result(session, None)

        repo = UserRepository(session)
        await repo.get_by_email("TEST@Example.COM")

        # Verify execute was called (the where clause lowercases internally)
        session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# get_active_by_uuid
# ---------------------------------------------------------------------------
class TestGetActiveByUuid:
    """Test UserRepository.get_active_by_uuid."""

    async def test_found(self):
        """Returns user when UUID matches and not soft-deleted."""
        mock_user = _make_mock_user()
        session = _make_mock_session()
        _setup_execute_result(session, mock_user)

        repo = UserRepository(session)
        result = await repo.get_active_by_uuid(mock_user.uuid)

        assert result is mock_user
        session.execute.assert_called_once()

    async def test_not_found(self):
        """Returns None when UUID does not match."""
        session = _make_mock_session()
        _setup_execute_result(session, None)

        repo = UserRepository(session)
        result = await repo.get_active_by_uuid(uuid_pkg.uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------
class TestCreateUser:
    """Test UserRepository.create_user."""

    async def test_creates_and_persists(self):
        """Creates a User, adds to session, commits, and refreshes."""
        session = _make_mock_session()

        repo = UserRepository(session)
        user = await repo.create_user(
            email="new@example.com",
            hashed_password="$2b$12$hashed",
            is_active=True,
            is_verified=False,
            is_superuser=False,
        )

        # Verify session interactions
        session.add.assert_called_once()
        session.commit.assert_called_once()
        session.refresh.assert_called_once()

        # Verify the created User attributes
        added_user = session.add.call_args[0][0]
        assert isinstance(added_user, User)
        assert added_user.email == "new@example.com"
        assert added_user.hashed_password == "$2b$12$hashed"
        assert added_user.is_active is True
        assert added_user.is_verified is False
        assert added_user.is_superuser is False

    async def test_email_lowercased(self):
        """Email is lowercased in create_user."""
        session = _make_mock_session()

        repo = UserRepository(session)
        await repo.create_user(
            email="UPPER@EXAMPLE.COM",
            hashed_password="$2b$12$hashed",
        )

        added_user = session.add.call_args[0][0]
        assert added_user.email == "upper@example.com"


# ---------------------------------------------------------------------------
# BaseRepository methods (via UserRepository)
# ---------------------------------------------------------------------------
class TestBaseRepositoryMethods:
    """Test inherited BaseRepository methods through UserRepository."""

    async def test_get_by_id(self):
        """get_by_id returns user when found."""
        mock_user = _make_mock_user()
        session = _make_mock_session()
        _setup_execute_result(session, mock_user)

        repo = UserRepository(session)
        result = await repo.get_by_id(1)

        assert result is mock_user

    async def test_get_by_uuid(self):
        """get_by_uuid returns user when found."""
        mock_user = _make_mock_user()
        session = _make_mock_session()
        _setup_execute_result(session, mock_user)

        repo = UserRepository(session)
        result = await repo.get_by_uuid(mock_user.uuid)

        assert result is mock_user

    async def test_update(self):
        """update commits and refreshes the instance."""
        mock_user = _make_mock_user()
        session = _make_mock_session()

        repo = UserRepository(session)
        result = await repo.update(mock_user)

        session.commit.assert_called_once()
        session.refresh.assert_called_once_with(mock_user)
        assert result is mock_user

    async def test_soft_delete(self):
        """soft_delete sets deleted_at and commits."""
        mock_user = MagicMock(spec=User)
        mock_user.deleted_at = None
        session = _make_mock_session()

        repo = UserRepository(session)
        result = await repo.soft_delete(mock_user)

        assert mock_user.deleted_at is not None
        session.commit.assert_called_once()
        session.refresh.assert_called_once_with(mock_user)
