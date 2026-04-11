"""Tier CRUD routes — public tier listing + admin tier management."""

from __future__ import annotations

import uuid as uuid_pkg

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_superuser
from app.core.db.session import get_session
from app.models.user import User
from app.schemas.tier import TierCreate, TierPublicRead, TierRead, TierUpdate
from app.services.tier_service import TierService

router = APIRouter(prefix="/tiers", tags=["tiers"])


# --------------------------------------------------------------------------
# Public endpoints (no auth required)
# --------------------------------------------------------------------------


@router.get("", response_model=list[TierPublicRead])
async def list_tiers(
    db: AsyncSession = Depends(get_session),
) -> list[TierPublicRead]:
    """List all active tiers. Public endpoint for pricing page."""
    service = TierService(db)
    tiers = await service.list_active_tiers()
    return [TierPublicRead.model_validate(t) for t in tiers]


@router.get("/{tier_uuid}", response_model=TierPublicRead)
async def get_tier(
    tier_uuid: uuid_pkg.UUID,
    db: AsyncSession = Depends(get_session),
) -> TierPublicRead:
    """Get a single tier by UUID. Public endpoint."""
    service = TierService(db)
    tier = await service.get_tier_by_uuid(tier_uuid)
    return TierPublicRead.model_validate(tier)


# --------------------------------------------------------------------------
# Admin endpoints (superuser only)
# --------------------------------------------------------------------------


@router.post("", response_model=TierRead, status_code=201)
async def create_tier(
    data: TierCreate,
    _: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_session),
) -> TierRead:
    """Create a new tier. Superuser only."""
    service = TierService(db)
    tier = await service.create_tier(data)
    return TierRead.model_validate(tier)


@router.patch("/{tier_uuid}", response_model=TierRead)
async def update_tier(
    tier_uuid: uuid_pkg.UUID,
    data: TierUpdate,
    _: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_session),
) -> TierRead:
    """Update an existing tier. Superuser only."""
    service = TierService(db)
    tier = await service.get_tier_by_uuid(tier_uuid)
    updated = await service.update_tier(tier, data)
    return TierRead.model_validate(updated)


@router.delete("/{tier_uuid}", status_code=204)
async def delete_tier(
    tier_uuid: uuid_pkg.UUID,
    _: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_session),
) -> None:
    """Soft-delete a tier. Superuser only. Cannot delete the 'free' tier."""
    service = TierService(db)
    tier = await service.get_tier_by_uuid(tier_uuid)
    await service.soft_delete_tier(tier)
