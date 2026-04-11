"""Shared auth cookie utilities.

Extracted from auth.py to avoid router cross-imports. Both auth.py
and users.py need to clear cookies (logout and account deletion).
"""

from __future__ import annotations

from fastapi import Response

from app.configs import settings

_SECURE_COOKIE = settings.ENVIRONMENT != "local"


def clear_auth_cookies(response: Response) -> None:
    """Delete both access_token and refresh_token HttpOnly cookies."""
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
