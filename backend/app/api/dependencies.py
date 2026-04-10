"""Shared FastAPI dependencies (auth, db session, etc.).

All auth dependencies read the ``access_token`` from an HttpOnly cookie
rather than an Authorization header — this avoids XSS token theft while
still being fully compatible with SSR frameworks (Next.js).
"""

from __future__ import annotations

import logging
import uuid as uuid_pkg

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import get_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token, is_token_blacklisted
from app.models.user import User
from app.services import auth_service

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    """Extract and validate the access token from cookies, return the user.

    Steps:
        1. Read ``access_token`` from HttpOnly cookie.
        2. Decode the JWT and validate claims.
        3. Ensure the token is not blacklisted.
        4. Load the user from the database.

    Raises:
        UnauthorizedError: If the token is missing, invalid, blacklisted,
            or the user no longer exists.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise UnauthorizedError(detail="Not authenticated")

    payload = decode_token(token)

    if payload.type != "access":
        raise UnauthorizedError(detail="Invalid token type")

    if await is_token_blacklisted(payload.jti):
        raise UnauthorizedError(detail="Token has been revoked")

    user = await auth_service.get_user_by_uuid(
        db, uuid_pkg.UUID(payload.sub)
    )
    if user is None:
        raise UnauthorizedError(detail="User not found")

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Return the user only if the account is active.

    Raises:
        ForbiddenError: If the user account is deactivated.
    """
    if not user.is_active:
        raise ForbiddenError(detail="Account is deactivated", error_code="ACCOUNT_INACTIVE")
    return user


async def get_current_superuser(
    user: User = Depends(get_current_active_user),
) -> User:
    """Return the user only if they are an active superuser.

    Raises:
        ForbiddenError: If the user is not a superuser.
    """
    if not user.is_superuser:
        raise ForbiddenError(detail="Superuser privileges required", error_code="SUPERUSER_REQUIRED")
    return user
