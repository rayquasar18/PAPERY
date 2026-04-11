"""User profile route handlers — view, edit, avatar, account deletion.

All endpoints require authentication via HttpOnly cookie JWT.
Profile data is served under /api/v1/users/me — separate from /auth/me
which returns a lightweight UserPublicRead for auth checks only.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.core.db.session import get_session
from app.models.user import User
from app.schemas.user import UserProfileRead, UserProfileUpdate
from app.services.user_service import UserService
from app.utils.rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


# ---------------------------------------------------------------------------
# 1. GET /users/me — view full profile
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserProfileRead)
async def get_my_profile(
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> UserProfileRead:
    """Return the full profile of the authenticated user.

    Includes computed fields: tier_name, has_password, oauth_providers.
    Avatar URL is a presigned MinIO URL (not the raw object path).

    Rate limit: 60 requests / minute per user.
    """
    await check_rate_limit(f"users:me:get:{user.uuid}", max_requests=60, window_seconds=60)

    service = UserService(db)
    return await service.get_profile(user)


# ---------------------------------------------------------------------------
# 2. PATCH /users/me — edit profile
# ---------------------------------------------------------------------------
@router.patch("/me", response_model=UserProfileRead)
async def update_my_profile(
    body: UserProfileUpdate,
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> UserProfileRead:
    """Update the authenticated user's profile.

    Currently only display_name is editable. Avatar is managed via
    separate POST/DELETE /users/me/avatar endpoints.

    Rate limit: 10 requests / minute per user.
    """
    await check_rate_limit(f"users:me:patch:{user.uuid}", max_requests=10, window_seconds=60)

    service = UserService(db)
    await service.update_profile(user, body)
    return await service.get_profile(user)
