"""Tests for authentication request/response schemas (Plan 03-04-T2)."""

import uuid as uuid_pkg
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResendVerificationRequest,
    TokenPayload,
    UserPublicRead,
    VerifyEmailRequest,
)


class TestRegisterRequest:
    """Test RegisterRequest validation rules."""

    def test_valid_registration(self):
        """Accept valid email + password combination."""
        req = RegisterRequest(email="user@example.com", password="securepass123")
        assert req.email == "user@example.com"
        assert req.password == "securepass123"

    def test_password_too_short(self):
        """Reject passwords shorter than 8 characters."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="user@example.com", password="short")
        errors = exc_info.value.errors()
        assert any(e["type"] == "string_too_short" for e in errors)

    def test_password_too_long(self):
        """Reject passwords longer than 128 characters."""
        long_password = "a" * 129
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="user@example.com", password=long_password)
        errors = exc_info.value.errors()
        assert any(e["type"] == "string_too_long" for e in errors)

    def test_password_must_not_match_email(self):
        """Reject password that exactly matches the email address."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="user@example.com", password="user@example.com")
        assert "must not match" in str(exc_info.value).lower()

    def test_password_email_match_case_insensitive(self):
        """Email-password match check should be case-insensitive."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="User@Example.COM", password="user@example.com")
        assert "must not match" in str(exc_info.value).lower()

    def test_invalid_email(self):
        """Reject malformed email addresses."""
        with pytest.raises(ValidationError):
            RegisterRequest(email="not-an-email", password="securepass123")

    def test_boundary_password_8_chars(self):
        """Accept password exactly at 8-character minimum boundary."""
        req = RegisterRequest(email="user@example.com", password="12345678")
        assert len(req.password) == 8

    def test_boundary_password_128_chars(self):
        """Accept password exactly at 128-character maximum boundary."""
        password = "a" * 128
        req = RegisterRequest(email="user@example.com", password=password)
        assert len(req.password) == 128


class TestLoginRequest:
    """Test LoginRequest validation rules."""

    def test_valid_login(self):
        """Accept valid email + password."""
        req = LoginRequest(email="user@example.com", password="mypassword")
        assert req.email == "user@example.com"
        assert req.password == "mypassword"

    def test_invalid_email(self):
        """Reject malformed email."""
        with pytest.raises(ValidationError):
            LoginRequest(email="bad-email", password="mypassword")


class TestUserPublicRead:
    """Test UserPublicRead schema — especially from_attributes ORM mapping."""

    def test_from_attributes_orm_mapping(self):
        """UserPublicRead should populate from an ORM-like object via model_validate."""
        now = datetime.now(UTC)
        user_uuid = uuid_pkg.uuid4()

        class FakeUser:
            uuid = user_uuid
            email = "orm@example.com"
            display_name = "ORM User"
            avatar_url = "https://example.com/avatar.jpg"
            is_verified = True
            is_superuser = False
            created_at = now

        result = UserPublicRead.model_validate(FakeUser(), from_attributes=True)
        assert result.uuid == user_uuid
        assert result.email == "orm@example.com"
        assert result.display_name == "ORM User"
        assert result.avatar_url == "https://example.com/avatar.jpg"
        assert result.is_verified is True
        assert result.is_superuser is False
        assert result.created_at == now

    def test_no_password_leakage(self):
        """UserPublicRead must not expose password or internal id."""
        now = datetime.now(UTC)

        class FakeUser:
            uuid = uuid_pkg.uuid4()
            email = "user@example.com"
            display_name = None
            avatar_url = None
            is_verified = False
            is_superuser = False
            created_at = now
            # These should NOT appear in the output
            id = 42
            hashed_password = "$2b$12$secrethash"

        result = UserPublicRead.model_validate(FakeUser(), from_attributes=True)
        result_dict = result.model_dump()
        assert "id" not in result_dict
        assert "hashed_password" not in result_dict
        assert "password" not in result_dict

    def test_optional_fields_default_none(self):
        """display_name and avatar_url should default to None."""
        now = datetime.now(UTC)

        class FakeUser:
            uuid = uuid_pkg.uuid4()
            email = "user@example.com"
            display_name = None
            avatar_url = None
            is_verified = False
            is_superuser = False
            created_at = now

        result = UserPublicRead.model_validate(FakeUser(), from_attributes=True)
        assert result.display_name is None
        assert result.avatar_url is None


class TestAuthResponse:
    """Test AuthResponse construction."""

    def test_basic_construction(self):
        """AuthResponse should wrap a UserPublicRead and message."""
        now = datetime.now(UTC)
        user = UserPublicRead(
            uuid=uuid_pkg.uuid4(),
            email="test@example.com",
            display_name="Test",
            avatar_url=None,
            is_verified=True,
            is_superuser=False,
            created_at=now,
        )
        resp = AuthResponse(user=user, message="Success")
        assert resp.user.email == "test@example.com"
        assert resp.message == "Success"


class TestTokenPayload:
    """Test TokenPayload schema for different token types."""

    def test_access_token_payload(self):
        """Access tokens have no family or purpose."""
        payload = TokenPayload(
            sub="user-uuid-string",
            jti="token-jti",
            type="access",
            exp=9999999999,
            iat=1700000000,
        )
        assert payload.type == "access"
        assert payload.family is None
        assert payload.purpose is None

    def test_refresh_token_payload_with_family(self):
        """Refresh tokens carry a family claim."""
        payload = TokenPayload(
            sub="user-uuid-string",
            jti="token-jti",
            type="refresh",
            exp=9999999999,
            iat=1700000000,
            family="family-id-123",
        )
        assert payload.type == "refresh"
        assert payload.family == "family-id-123"
        assert payload.purpose is None

    def test_verification_token_payload_with_purpose(self):
        """Verification tokens carry a purpose claim."""
        payload = TokenPayload(
            sub="user-uuid-string",
            jti="token-jti",
            type="verification",
            exp=9999999999,
            iat=1700000000,
            purpose="email_verify",
        )
        assert payload.type == "verification"
        assert payload.purpose == "email_verify"


class TestMessageResponse:
    """Test MessageResponse schema."""

    def test_basic_construction(self):
        """MessageResponse should hold a message string."""
        resp = MessageResponse(message="Operation successful")
        assert resp.message == "Operation successful"

    def test_missing_message_raises(self):
        """MessageResponse requires a message field."""
        with pytest.raises(ValidationError):
            MessageResponse()


class TestVerifyEmailRequest:
    """Test VerifyEmailRequest schema."""

    def test_valid_token(self):
        """Accept any non-empty token string."""
        req = VerifyEmailRequest(token="some-jwt-token")
        assert req.token == "some-jwt-token"

    def test_missing_token_raises(self):
        """Token field is required."""
        with pytest.raises(ValidationError):
            VerifyEmailRequest()


class TestResendVerificationRequest:
    """Test ResendVerificationRequest schema."""

    def test_valid_email(self):
        """Accept valid email."""
        req = ResendVerificationRequest(email="user@example.com")
        assert req.email == "user@example.com"

    def test_invalid_email_raises(self):
        """Reject malformed email."""
        with pytest.raises(ValidationError):
            ResendVerificationRequest(email="bad-email")
