"""Admin tier management endpoints — CRUD for tiers. Superuser only."""

from __future__ import annotations

import uuid as uuid_pkg

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import get_session
from app.schemas.tier import TierCreate, TierRead, TierUpdate
from app.services.tier_service import TierService

router = APIRouter(prefix="/tiers", tags=["admin-tiers"])


@router.post("", response_model=TierRead, status_code=201)
async def create_tier(
    data: TierCreate,
    db: AsyncSession = Depends(get_session),
) -> TierRead:
    """Create a new tier. Superuser only (enforced by admin router)."""
    service = TierService(db)
    tier = await service.create_tier(data)
    return TierRead.model_validate(tier)


@router.patch("/{tier_uuid}", response_model=TierRead)
async def update_tier(
    tier_uuid: uuid_pkg.UUID,
    data: TierUpdate,
    db: AsyncSession = Depends(get_session),
) -> TierRead:
    """Update an existing tier. Superuser only (enforced by admin router)."""
    service = TierService(db)
    tier = await service.get_tier_by_uuid(tier_uuid)
    updated = await service.update_tier(tier, data)
    return TierRead.model_validate(updated)


@router.delete("/{tier_uuid}", status_code=204)
async def delete_tier(
    tier_uuid: uuid_pkg.UUID,
    db: AsyncSession = Depends(get_session),
) -> None:
    """Soft-delete a tier. Superuser only. Cannot delete the 'free' tier."""
    service = TierService(db)
    tier = await service.get_tier_by_uuid(tier_uuid)
    await service.soft_delete_tier(tier)
