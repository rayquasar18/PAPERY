"""Tier public endpoints — tier listing for pricing page."""

from __future__ import annotations

import uuid as uuid_pkg

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import get_session
from app.schemas.tier import TierPublicRead
from app.services.tier_service import TierService

router = APIRouter(prefix="/tiers", tags=["tiers"])


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
