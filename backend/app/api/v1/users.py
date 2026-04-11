"""User profile route handlers — view, edit, avatar, account deletion.

All endpoints require authentication via HttpOnly cookie JWT.
Profile data is served under /api/v1/users/me — separate from /auth/me
which returns a lightweight UserPublicRead for auth checks only.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.core.db.session import get_session
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.user import AvatarUploadResponse, DeleteAccountRequest, UserProfileRead, UserProfileUpdate
from app.services.user_service import UserService
from app.utils.cookies import clear_auth_cookies
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


# ---------------------------------------------------------------------------
# 3. POST /users/me/avatar — upload avatar
# ---------------------------------------------------------------------------
@router.post("/me/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile,
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> AvatarUploadResponse:
    """Upload or replace the user's avatar image.

    Accepts JPEG, PNG, or WebP. Max 2MB. Auto-resizes to 200x200 (main)
    and 50x50 (thumbnail), converts to WebP, stores in MinIO.

    Rate limit: 5 requests / minute per user.
    """
    await check_rate_limit(f"users:me:avatar:post:{user.uuid}", max_requests=5, window_seconds=60)

    # Read file data
    file_data = await file.read()

    service = UserService(db)
    main_url, thumb_url = await service.upload_avatar(
        user, file_data, file.content_type or "application/octet-stream"
    )

    return AvatarUploadResponse(
        avatar_url=main_url,
        thumbnail_url=thumb_url,
        message="Avatar uploaded successfully",
    )


# ---------------------------------------------------------------------------
# 4. DELETE /users/me/avatar — remove avatar
# ---------------------------------------------------------------------------
@router.delete("/me/avatar", response_model=MessageResponse)
async def remove_avatar(
    request: Request,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Remove the user's avatar image from MinIO and clear the URL.

    Rate limit: 5 requests / minute per user.
    """
    await check_rate_limit(f"users:me:avatar:delete:{user.uuid}", max_requests=5, window_seconds=60)

    service = UserService(db)
    await service.remove_avatar(user)

    return MessageResponse(message="Avatar removed successfully")


# ---------------------------------------------------------------------------
# 5. DELETE /users/me — delete account
# ---------------------------------------------------------------------------
@router.delete("/me", response_model=MessageResponse)
async def delete_my_account(
    body: DeleteAccountRequest,
    request: Request,
    response: Response,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Soft-delete the authenticated user's account.

    Requires password confirmation (local users) or email confirmation
    (OAuth-only users). Deactivates account, invalidates all sessions,
    and clears auth cookies.

    Rate limit: 3 requests / minute per user.
    """
    await check_rate_limit(f"users:me:delete:{user.uuid}", max_requests=3, window_seconds=60)

    service = UserService(db)
    await service.delete_account(user, body)

    # Clear auth cookies
    clear_auth_cookies(response)

    return MessageResponse(message="Account deleted successfully")
