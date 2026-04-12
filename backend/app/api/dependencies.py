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
from app.models.user import User, UserStatus
from app.repositories.user_repository import UserRepository
from app.services.tier_service import TierService
from app.services.usage_service import UsageService

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

    user_repo = UserRepository(db)
    user = await user_repo.get(uuid=uuid_pkg.UUID(payload.sub))
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
        if user.status == UserStatus.BANNED.value:
            raise ForbiddenError(detail="Account has been banned", error_code="ACCOUNT_BANNED")
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


class RequireFeature:
    """Dependency that enforces a feature flag from the user's tier.

    Usage on routes:
        @router.post("/documents/export-pdf")
        async def export_pdf(user: User = Depends(RequireFeature("can_export_pdf"))):
            ...
    """

    def __init__(self, feature: str) -> None:
        self.feature = feature

    async def __call__(
        self,
        user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_session),
    ) -> User:
        tier_service = TierService(db)
        tier_data = await tier_service.get_user_tier_data(user)

        flags = tier_data.get("feature_flags", {})
        if not flags.get(self.feature, False):
            raise ForbiddenError(
                detail=f"Your plan does not include '{self.feature}'. Upgrade to access this feature.",
                error_code="FEATURE_NOT_AVAILABLE",
            )
        return user


class CheckUsageLimit:
    """Dependency that enforces a usage quota for the current billing period.

    Usage on routes:
        @router.post("/projects")
        async def create_project(user: User = Depends(CheckUsageLimit("projects"))):
            ...
    """

    def __init__(self, metric: str) -> None:
        self.metric = metric

    async def __call__(
        self,
        user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_session),
    ) -> User:
        usage_service = UsageService(db)
        await usage_service.enforce_limit(user, self.metric)
        return user
