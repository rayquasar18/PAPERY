"""Admin user management endpoints — search, view, update users."""

from __future__ import annotations

import uuid as uuid_pkg

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import get_session
from app.schemas.admin_user import AdminUserListResponse, AdminUserRead, AdminUserUpdate
from app.services.admin_service import AdminService

router = APIRouter(prefix="/users", tags=["admin-users"])


@router.get("", response_model=AdminUserListResponse)
async def list_users(
    q: str | None = Query(None, description="Search by email or display name (ILIKE)"),
    status: str | None = Query(None, pattern=r"^(active|deactivated|banned)$"),
    tier_uuid: uuid_pkg.UUID | None = Query(None, description="Filter by tier UUID"),
    is_verified: bool | None = Query(None),
    is_superuser: bool | None = Query(None),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", pattern=r"^(created_at|email)$"),
    sort_order: str = Query("desc", pattern=r"^(asc|desc)$"),
    db: AsyncSession = Depends(get_session),
) -> AdminUserListResponse:
    """List and search users with filtering, pagination, and sorting.

    Superuser only. Supports text search, status/tier/verification filters.
    """
    service = AdminService(db)
    users, total = await service.search_users(
        q=q,
        status=status,
        tier_uuid=tier_uuid,
        is_verified=is_verified,
        is_superuser=is_superuser,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    items = [AdminService.to_admin_user_read(u) for u in users]
    return AdminUserListResponse.build(items=items, total=total, page=page, per_page=per_page)


@router.get("/{user_uuid}", response_model=AdminUserRead)
async def get_user(
    user_uuid: uuid_pkg.UUID,
    db: AsyncSession = Depends(get_session),
) -> AdminUserRead:
    """Get full user details by UUID. Superuser only."""
    service = AdminService(db)
    user = await service.get_user_by_uuid(user_uuid)
    return AdminService.to_admin_user_read(user)


@router.patch("/{user_uuid}", response_model=AdminUserRead)
async def update_user(
    user_uuid: uuid_pkg.UUID,
    data: AdminUserUpdate,
    db: AsyncSession = Depends(get_session),
) -> AdminUserRead:
    """Update user fields (status, tier, permissions). Superuser only.

    Ban triggers immediate session invalidation.
    """
    service = AdminService(db)
    updated = await service.update_user(user_uuid, data)
    return AdminService.to_admin_user_read(updated)
