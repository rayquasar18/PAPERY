"""Authentication route handlers — register, login, logout, refresh, me, verify, resend.

All token transport uses HttpOnly cookies (no tokens in response bodies).
This eliminates XSS-based token theft while remaining compatible with
SSR frameworks like Next.js.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user, get_current_user
from app.configs import settings
from app.core.db.session import get_session
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.security import (
    create_oauth_state,
    create_token_pair,
    decode_token,
    register_token_in_family,
    track_user_family,
    validate_oauth_state,
)
from app.infra.oauth.github import GitHubOAuthProvider
from app.infra.oauth.google import GoogleOAuthProvider
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SetPasswordRequest,
    UserPublicRead,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService
from app.utils.cookies import clear_auth_cookies
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



# ---------------------------------------------------------------------------
# 1. POST /auth/register
# ---------------------------------------------------------------------------
@router.post("/register", response_model=AuthResponse, status_code=201)
@limiter.limit("3/minute")
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> AuthResponse:
    """Register a new local user account.

    Rate limit: 3 requests / minute per IP (enforced by slowapi).
    """
    service = AuthService(db)
    user = await service.register_user(body.email, body.password)

    access_token, refresh_token = create_token_pair(user.uuid)

    # Register the refresh token in its family for replay detection
    refresh_payload = decode_token(refresh_token)
    await register_token_in_family(
        refresh_payload.family, refresh_payload.jti  # type: ignore[arg-type]
    )
    await track_user_family(user.uuid, refresh_payload.family)  # type: ignore[arg-type]

    _set_auth_cookies(response, access_token, refresh_token)

    # Fire-and-forget verification email (best effort)
    try:
        await service.send_verification_email(user.email, user.uuid)
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
@limiter.limit("5/minute")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> AuthResponse:
    """Authenticate with email + password.

    Rate limit: 5 requests / minute per IP (enforced by slowapi).
    """
    service = AuthService(db)
    user = await service.authenticate_user(body.email, body.password)

    access_token, refresh_token = create_token_pair(user.uuid)

    refresh_payload = decode_token(refresh_token)
    await register_token_in_family(
        refresh_payload.family, refresh_payload.jti  # type: ignore[arg-type]
    )
    await track_user_family(user.uuid, refresh_payload.family)  # type: ignore[arg-type]

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
    db: AsyncSession = Depends(get_session),
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
        service = AuthService(db)
        await service.logout_user(access_payload, refresh_jti=refresh_jti)

    clear_auth_cookies(response)

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

    service = AuthService(db)
    access_token, refresh_token = await service.rotate_refresh_token(old_payload)

    _set_auth_cookies(response, access_token, refresh_token)

    # Load user for response body via service helper (no direct repo in router)
    import uuid as uuid_pkg
    user = await service.get_user_by_uuid(uuid_pkg.UUID(old_payload.sub))
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
    service = AuthService(db)
    await service.verify_email(body.token)
    return MessageResponse(message="Email verified successfully.")


# ---------------------------------------------------------------------------
# 7. POST /auth/resend-verification
# ---------------------------------------------------------------------------
@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit("1/minute")
async def resend_verification(
    body: ResendVerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Resend verification email.

    Rate limit: 1 request / 60 seconds per IP (enforced by slowapi).
    Returns the same success message regardless of whether the email
    exists — this prevents user enumeration.
    """
    # Anti-enumeration: always return success, even if user doesn't exist
    service = AuthService(db)
    user = await service.get_user_by_email(body.email)
    if user is not None and not user.is_verified:
        try:
            await service.send_verification_email(user.email, user.uuid)
        except Exception:
            logger.warning(
                "Failed to resend verification email to %s",
                body.email,
                exc_info=True,
            )

    return MessageResponse(
        message="If an account with that email exists and is unverified, a verification email has been sent.",
    )


# ---------------------------------------------------------------------------
# 8. POST /auth/forgot-password
# ---------------------------------------------------------------------------
@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Request a password reset email.

    Rate limit: 3 requests / minute per IP (enforced by slowapi).
    Anti-enumeration: always returns the same success message.
    """
    # Fire-and-forget (best effort)
    try:
        service = AuthService(db)
        await service.request_password_reset(body.email)
    except Exception:
        logger.warning("Failed to process password reset for %s", body.email, exc_info=True)

    return MessageResponse(
        message="If an account with that email exists, a password reset email has been sent.",
    )


# ---------------------------------------------------------------------------
# 9. POST /auth/reset-password
# ---------------------------------------------------------------------------
@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Reset password using a valid reset token.

    Rate limit: 5 requests / minute per IP (enforced by slowapi).
    """
    service = AuthService(db)
    await service.reset_password(body.token, body.new_password)

    return MessageResponse(message="Password has been reset successfully.")


# ---------------------------------------------------------------------------
# OAuth provider helpers
# ---------------------------------------------------------------------------
def _get_google_provider() -> GoogleOAuthProvider:
    """Create a GoogleOAuthProvider; raises 404 if not configured."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise NotFoundError(detail="Google OAuth is not configured")
    return GoogleOAuthProvider(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        redirect_uri=f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/auth/google/callback",
    )


def _get_github_provider() -> GitHubOAuthProvider:
    """Create a GitHubOAuthProvider; raises 404 if not configured."""
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise NotFoundError(detail="GitHub OAuth is not configured")
    return GitHubOAuthProvider(
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
        redirect_uri=f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/auth/github/callback",
    )


# ---------------------------------------------------------------------------
# 10. GET /auth/google — initiate Google OAuth
# ---------------------------------------------------------------------------
@router.get("/google")
@limiter.limit("10/minute")
async def google_auth(request: Request) -> RedirectResponse:
    """Redirect user to Google OAuth consent page.

    Rate limit: 10 requests / minute per IP (enforced by slowapi).
    """
    provider = _get_google_provider()
    state = await create_oauth_state("google")
    auth_url = provider.get_authorization_url(state)
    return RedirectResponse(url=auth_url, status_code=302)


# ---------------------------------------------------------------------------
# 11. GET /auth/google/callback — Google OAuth callback
# ---------------------------------------------------------------------------
@router.get("/google/callback")
async def google_callback(
    request: Request,
    response: Response,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """Handle Google OAuth callback — exchange code, create/link user, set cookies.

    On success: redirects to frontend dashboard with auth cookies set.
    On failure: redirects to frontend login with error query param.
    """
    frontend_url = settings.FRONTEND_URL

    if error:
        logger.warning("Google OAuth error: %s", error)
        return RedirectResponse(url=f"{frontend_url}/login?error=oauth_denied", status_code=302)

    if not code or not state:
        return RedirectResponse(url=f"{frontend_url}/login?error=oauth_invalid", status_code=302)

    # CSRF validation
    if not await validate_oauth_state("google", state):
        logger.warning("Google OAuth: invalid state parameter")
        return RedirectResponse(url=f"{frontend_url}/login?error=oauth_csrf", status_code=302)

    try:
        provider = _get_google_provider()
        access_token = await provider.get_access_token(code)
        user_info = await provider.get_user_info(access_token)
        service = AuthService(db)
        user = await service.oauth_login_or_register(user_info)
    except Exception:
        logger.exception("Google OAuth callback failed")
        return RedirectResponse(url=f"{frontend_url}/login?error=oauth_failed", status_code=302)

    # Issue JWT token pair
    access_jwt, refresh_jwt = create_token_pair(user.uuid)
    refresh_payload = decode_token(refresh_jwt)
    await register_token_in_family(refresh_payload.family, refresh_payload.jti)  # type: ignore[arg-type]
    await track_user_family(user.uuid, refresh_payload.family)  # type: ignore[arg-type]

    # Set cookies on redirect response
    redirect = RedirectResponse(url=f"{frontend_url}/dashboard", status_code=302)
    _set_auth_cookies(redirect, access_jwt, refresh_jwt)
    return redirect


# ---------------------------------------------------------------------------
# 12. GET /auth/github — initiate GitHub OAuth
# ---------------------------------------------------------------------------
@router.get("/github")
@limiter.limit("10/minute")
async def github_auth(request: Request) -> RedirectResponse:
    """Redirect user to GitHub OAuth consent page.

    Rate limit: 10 requests / minute per IP (enforced by slowapi).
    """
    provider = _get_github_provider()
    state = await create_oauth_state("github")
    auth_url = provider.get_authorization_url(state)
    return RedirectResponse(url=auth_url, status_code=302)


# ---------------------------------------------------------------------------
# 13. GET /auth/github/callback — GitHub OAuth callback
# ---------------------------------------------------------------------------
@router.get("/github/callback")
async def github_callback(
    request: Request,
    response: Response,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """Handle GitHub OAuth callback — exchange code, create/link user, set cookies.

    On success: redirects to frontend dashboard with auth cookies set.
    On failure: redirects to frontend login with error query param.
    """
    frontend_url = settings.FRONTEND_URL

    if error:
        logger.warning("GitHub OAuth error: %s", error)
        return RedirectResponse(url=f"{frontend_url}/login?error=oauth_denied", status_code=302)

    if not code or not state:
        return RedirectResponse(url=f"{frontend_url}/login?error=oauth_invalid", status_code=302)

    # CSRF validation
    if not await validate_oauth_state("github", state):
        logger.warning("GitHub OAuth: invalid state parameter")
        return RedirectResponse(url=f"{frontend_url}/login?error=oauth_csrf", status_code=302)

    try:
        provider = _get_github_provider()
        access_token = await provider.get_access_token(code)
        user_info = await provider.get_user_info(access_token)
        service = AuthService(db)
        user = await service.oauth_login_or_register(user_info)
    except Exception:
        logger.exception("GitHub OAuth callback failed")
        return RedirectResponse(url=f"{frontend_url}/login?error=oauth_failed", status_code=302)

    # Issue JWT token pair
    access_jwt, refresh_jwt = create_token_pair(user.uuid)
    refresh_payload = decode_token(refresh_jwt)
    await register_token_in_family(refresh_payload.family, refresh_payload.jti)  # type: ignore[arg-type]
    await track_user_family(user.uuid, refresh_payload.family)  # type: ignore[arg-type]

    # Set cookies on redirect response
    redirect = RedirectResponse(url=f"{frontend_url}/dashboard", status_code=302)
    _set_auth_cookies(redirect, access_jwt, refresh_jwt)
    return redirect


# ---------------------------------------------------------------------------
# 14. POST /auth/change-password
# ---------------------------------------------------------------------------
@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Change password for an authenticated user with an existing password.

    Requires current password verification. Invalidates all sessions
    after successful change (forces re-login on all devices).

    Rate limit: 5 requests / minute per user.
    """
    await check_rate_limit(
        f"auth:change-password:{user.uuid}",
        max_requests=5,
        window_seconds=60,
    )

    service = AuthService(db)
    await service.change_password(user, body.current_password, body.new_password)

    return MessageResponse(
        message="Password changed successfully. Please log in again.",
    )


# ---------------------------------------------------------------------------
# 15. POST /auth/set-password
# ---------------------------------------------------------------------------
@router.post("/set-password", response_model=MessageResponse)
async def set_password(
    body: SetPasswordRequest,
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Set a password for an OAuth-only user (no existing password).

    Only allowed when the user has no password set (hashed_password is NULL).

    Rate limit: 5 requests / minute per user.
    """
    await check_rate_limit(
        f"auth:set-password:{user.uuid}",
        max_requests=5,
        window_seconds=60,
    )

    service = AuthService(db)
    await service.set_password(user, body.new_password)

    return MessageResponse(
        message="Password set successfully. You can now log in with email and password.",
    )
