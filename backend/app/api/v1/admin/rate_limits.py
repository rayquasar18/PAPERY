"""Admin rate limit rule management endpoints — CRUD for rate limiting rules."""

from __future__ import annotations

import uuid as uuid_pkg

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import get_session
from app.schemas.rate_limit_rule import (
    RateLimitRuleCreate,
    RateLimitRuleRead,
    RateLimitRuleUpdate,
)
from app.services.rate_limit_rule_service import RateLimitRuleService

router = APIRouter(prefix="/rate-limits", tags=["admin-rate-limits"])


@router.get("", response_model=list[RateLimitRuleRead])
async def list_rate_limit_rules(
    db: AsyncSession = Depends(get_session),
) -> list[RateLimitRuleRead]:
    """List all active rate limit rules. Superuser only."""
    service = RateLimitRuleService(db)
    rules = await service.list_rules()
    return [RateLimitRuleService.to_rule_read(r) for r in rules]


@router.post("", response_model=RateLimitRuleRead, status_code=201)
async def create_rate_limit_rule(
    data: RateLimitRuleCreate,
    db: AsyncSession = Depends(get_session),
) -> RateLimitRuleRead:
    """Create a new rate limit rule. Superuser only."""
    service = RateLimitRuleService(db)
    rule = await service.create_rule(data)
    return RateLimitRuleService.to_rule_read(rule)


@router.patch("/{rule_uuid}", response_model=RateLimitRuleRead)
async def update_rate_limit_rule(
    rule_uuid: uuid_pkg.UUID,
    data: RateLimitRuleUpdate,
    db: AsyncSession = Depends(get_session),
) -> RateLimitRuleRead:
    """Update a rate limit rule. Superuser only."""
    service = RateLimitRuleService(db)
    updated = await service.update_rule(rule_uuid, data)
    return RateLimitRuleService.to_rule_read(updated)


@router.delete("/{rule_uuid}", status_code=204)
async def delete_rate_limit_rule(
    rule_uuid: uuid_pkg.UUID,
    db: AsyncSession = Depends(get_session),
) -> None:
    """Soft-delete a rate limit rule. Superuser only."""
    service = RateLimitRuleService(db)
    await service.delete_rule(rule_uuid)
