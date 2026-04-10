"""Authentication route handlers — register, login, logout, refresh, me, verify, resend.

All token transport uses HttpOnly cookies (no tokens in response bodies).
This eliminates XSS-based token theft while remaining compatible with
SSR frameworks like Next.js.
"""

from __future__ import annotations

import logging
import uuid as uuid_pkg

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.configs import settings
from app.core.db.session import get_session
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_token_pair,
    decode_token,
    register_token_in_family,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResendVerificationRequest,
    UserPublicRead,
    VerifyEmailRequest,
)
from app.services import auth_service
from app.utils.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------
_SECURE_COOKIE: bool = settings.ENVIRONMENT != "local"


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """Set HttpOnly auth cookies on the response.

    - ``access_token``: scoped to ``/``, short-lived.
    - ``refresh_token``: scoped to the refresh endpoint only.
    """
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=_SECURE_COOKIE,
        samesite="lax",
        path="/",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=_SECURE_COOKIE,
        samesite="lax",
        path="/api/v1/auth/refresh",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Delete both auth cookies."""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=_SECURE_COOKIE,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=_SECURE_COOKIE,
        samesite="lax",
        path="/api/v1/auth/refresh",
    )


# ---------------------------------------------------------------------------
# 1. POST /auth/register
# ---------------------------------------------------------------------------
@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> AuthResponse:
    """Register a new local user account.

    Rate limit: 3 requests / minute per IP.
    """
    client_ip = request.client.host if request.client else "unknown"
    await check_rate_limit(f"auth:register:{client_ip}", max_requests=3, window_seconds=60)

    user = await auth_service.register_user(db, body.email, body.password)

    access_token, refresh_token = create_token_pair(user.uuid)

    # Register the refresh token in its family for replay detection
    refresh_payload = decode_token(refresh_token)
    await register_token_in_family(
        refresh_payload.family, refresh_payload.jti  # type: ignore[arg-type]
    )

    _set_auth_cookies(response, access_token, refresh_token)

    # Fire-and-forget verification email (best effort)
    try:
        await auth_service.send_verification_email(user.email, user.uuid)
    except Exception:
        logger.warning("Failed to send verification email to %s", user.email, exc_info=True)

    return AuthResponse(
        user=UserPublicRead.model_validate(user),
        message="Registration successful. Please check your email to verify your account.",
    )


# ---------------------------------------------------------------------------
# 2. POST /auth/login
# ---------------------------------------------------------------------------
@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> AuthResponse:
    """Authenticate with email + password.

    Rate limit: 5 requests / minute per IP.
    """
    client_ip = request.client.host if request.client else "unknown"
    await check_rate_limit(f"auth:login:{client_ip}", max_requests=5, window_seconds=60)

    user = await auth_service.authenticate_user(db, body.email, body.password)

    access_token, refresh_token = create_token_pair(user.uuid)

    refresh_payload = decode_token(refresh_token)
    await register_token_in_family(
        refresh_payload.family, refresh_payload.jti  # type: ignore[arg-type]
    )

    _set_auth_cookies(response, access_token, refresh_token)

    return AuthResponse(
        user=UserPublicRead.model_validate(user),
        message="Login successful.",
    )


# ---------------------------------------------------------------------------
# 3. POST /auth/logout
# ---------------------------------------------------------------------------
@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    _user: User = Depends(get_current_user),
) -> MessageResponse:
    """Logout — blacklist tokens and clear cookies.

    Requires a valid access token.
    """
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    # Blacklist the access token (+ family if present)
    if access_token:
        access_payload = decode_token(access_token)
        refresh_jti: str | None = None
        if refresh_token:
            try:
                refresh_payload = decode_token(refresh_token)
                refresh_jti = refresh_payload.jti
            except Exception:
                logger.debug("Refresh token decode failed during logout — likely expired")
        await auth_service.logout_user(access_payload, refresh_jti=refresh_jti)

    _clear_auth_cookies(response)

    return MessageResponse(message="Logged out successfully.")


# ---------------------------------------------------------------------------
# 4. POST /auth/refresh
# ---------------------------------------------------------------------------
@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> AuthResponse:
    """Rotate tokens using the refresh cookie.

    The old refresh token is blacklisted and a new pair is issued
    in the same token family (for replay detection).
    """
    token = request.cookies.get("refresh_token")
    if not token:
        raise UnauthorizedError(detail="Refresh token missing")

    old_payload = decode_token(token)

    access_token, refresh_token = await auth_service.rotate_refresh_token(db, old_payload)

    _set_auth_cookies(response, access_token, refresh_token)

    # Load user for response body
    user_repo = UserRepository(db)
    user = await user_repo.get_active_by_uuid(uuid_pkg.UUID(old_payload.sub))
    if user is None:
        raise UnauthorizedError(detail="User not found")

    return AuthResponse(
        user=UserPublicRead.model_validate(user),
        message="Tokens refreshed successfully.",
    )


# ---------------------------------------------------------------------------
# 5. GET /auth/me
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserPublicRead)
async def me(
    user: User = Depends(get_current_user),
) -> UserPublicRead:
    """Return the current authenticated user's public profile."""
    return UserPublicRead.model_validate(user)


# ---------------------------------------------------------------------------
# 6. POST /auth/verify-email
# ---------------------------------------------------------------------------
@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Verify user email using a verification token."""
    await auth_service.verify_email(db, body.token)
    return MessageResponse(message="Email verified successfully.")


# ---------------------------------------------------------------------------
# 7. POST /auth/resend-verification
# ---------------------------------------------------------------------------
@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    body: ResendVerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Resend verification email.

    Rate limit: 1 request / 60 seconds per email address.
    Returns the same success message regardless of whether the email
    exists — this prevents user enumeration.
    """
    client_ip = request.client.host if request.client else "unknown"
    await check_rate_limit(
        f"auth:resend-verification:{body.email.lower()}:{client_ip}",
        max_requests=1,
        window_seconds=60,
    )

    # Anti-enumeration: always return success, even if user doesn't exist
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(body.email)
    if user is not None and not user.is_verified:
        try:
            await auth_service.send_verification_email(user.email, user.uuid)
        except Exception:
            logger.warning(
                "Failed to resend verification email to %s",
                body.email,
                exc_info=True,
            )

    return MessageResponse(
        message="If an account with that email exists and is unverified, a verification email has been sent.",
    )
