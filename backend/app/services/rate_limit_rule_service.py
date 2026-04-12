"""Rate limit rule service — business logic for admin rate limit management.

Handles CRUD for rate limit rules with Redis cache integration.
Also provides the lookup method used by the rate limiting utility to
resolve effective limits at runtime.

Usage:
    service = RateLimitRuleService(db)
    rule = await service.create_rule(data)
    effective = await service.get_effective_rule(tier_id=1, endpoint="auth:login")
"""

from __future__ import annotations

import logging
import uuid as uuid_pkg

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.rate_limit_rule import RateLimitRule
from app.repositories.rate_limit_rule_repository import RateLimitRuleRepository
from app.repositories.tier_repository import TierRepository
from app.schemas.rate_limit_rule import RateLimitRuleCreate, RateLimitRuleRead, RateLimitRuleUpdate
from app.utils.rate_limit_rule_cache import (
    get_cached_rate_limit_rule,
    invalidate_all_rate_limit_rule_cache,
    invalidate_rate_limit_rule_cache,
    set_cached_rate_limit_rule,
)

logger = logging.getLogger(__name__)


class RateLimitRuleService:
    """Class-based rate limit rule service — one instance per request lifecycle."""

    def __init__(self, db: AsyncSession) -> None:
        self._db: AsyncSession = db
        self._rule_repo: RateLimitRuleRepository = RateLimitRuleRepository(db)
        self._tier_repo: TierRepository = TierRepository(db)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_rules(self) -> list[RateLimitRule]:
        """List all active rate limit rules."""
        return await self._rule_repo.get_all_active()

    async def get_rule_by_uuid(self, rule_uuid: uuid_pkg.UUID) -> RateLimitRule:
        """Get a single rule by UUID. Raises NotFoundError if missing."""
        rule = await self._rule_repo.get(uuid=rule_uuid)
        if rule is None:
            raise NotFoundError(detail="Rate limit rule not found")
        return rule

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_rule(self, data: RateLimitRuleCreate) -> RateLimitRule:
        """Create a new rate limit rule.

        Resolves tier_uuid to tier_id. Raises ConflictError if a rule for
        the same tier+endpoint already exists.
        """
        tier_id: int | None = None
        if data.tier_uuid is not None:
            tier = await self._tier_repo.get(uuid=data.tier_uuid)
            if tier is None:
                raise NotFoundError(detail="Tier not found")
            tier_id = tier.id

        # Check for duplicate
        existing = await self._rule_repo.find_rule(tier_id, data.endpoint_pattern)
        if existing is not None and (
            (tier_id is None and existing.tier_id is None)
            or (tier_id is not None and existing.tier_id == tier_id)
        ):
            raise ConflictError(
                detail=f"Rate limit rule for endpoint '{data.endpoint_pattern}' "
                f"and tier already exists"
            )

        rule = RateLimitRule(
            tier_id=tier_id,
            endpoint_pattern=data.endpoint_pattern,
            max_requests=data.max_requests,
            window_seconds=data.window_seconds,
            description=data.description,
        )
        created = await self._rule_repo.create(rule)

        # Invalidate cache for this combination
        await invalidate_rate_limit_rule_cache(tier_id, data.endpoint_pattern)

        logger.info("Created rate limit rule: %s (tier_id=%s)", data.endpoint_pattern, tier_id)
        return created

    async def update_rule(
        self, rule_uuid: uuid_pkg.UUID, data: RateLimitRuleUpdate
    ) -> RateLimitRule:
        """Update a rate limit rule. Only provided fields are applied."""
        rule = await self.get_rule_by_uuid(rule_uuid)
        old_tier_id = rule.tier_id
        old_endpoint = rule.endpoint_pattern

        update_fields = data.model_dump(exclude_unset=True)

        # Handle tier_uuid -> tier_id resolution
        if "tier_uuid" in update_fields:
            tier_uuid_val = update_fields.pop("tier_uuid")
            if tier_uuid_val is not None:
                tier = await self._tier_repo.get(uuid=tier_uuid_val)
                if tier is None:
                    raise NotFoundError(detail="Tier not found")
                rule.tier_id = tier.id
            else:
                rule.tier_id = None

        # Apply remaining fields
        for field, value in update_fields.items():
            if hasattr(rule, field):
                setattr(rule, field, value)

        updated = await self._rule_repo.update(rule)

        # Invalidate caches for both old and new combinations
        await invalidate_rate_limit_rule_cache(old_tier_id, old_endpoint)
        await invalidate_rate_limit_rule_cache(updated.tier_id, updated.endpoint_pattern)

        logger.info("Updated rate limit rule: %s", rule_uuid)
        return updated

    async def delete_rule(self, rule_uuid: uuid_pkg.UUID) -> None:
        """Soft-delete a rate limit rule."""
        rule = await self.get_rule_by_uuid(rule_uuid)
        await self._rule_repo.soft_delete(rule)

        # Invalidate cache
        await invalidate_rate_limit_rule_cache(rule.tier_id, rule.endpoint_pattern)

        logger.info("Deleted rate limit rule: %s", rule_uuid)

    # ------------------------------------------------------------------
    # Runtime lookup (used by rate limiting utility)
    # ------------------------------------------------------------------

    async def get_effective_rule(
        self, tier_id: int | None, endpoint: str
    ) -> tuple[int, int] | None:
        """Resolve the effective rate limit for a tier + endpoint.

        Priority: tier-specific > default (tier_id=NULL) > None.
        Uses Redis cache with fallback to DB.

        Returns (max_requests, window_seconds) or None if no rule applies.
        """
        # Check cache for tier-specific rule
        if tier_id is not None:
            cached = await get_cached_rate_limit_rule(tier_id, endpoint)
            if cached is not None:
                return cached["max_requests"], cached["window_seconds"]

        # Check cache for default rule
        cached_default = await get_cached_rate_limit_rule(None, endpoint)
        if cached_default is not None:
            return cached_default["max_requests"], cached_default["window_seconds"]

        # Cache miss — query DB
        rule = await self._rule_repo.find_rule(tier_id, endpoint)
        if rule is None:
            return None

        # Cache the result
        rule_data = {
            "max_requests": rule.max_requests,
            "window_seconds": rule.window_seconds,
        }
        await set_cached_rate_limit_rule(rule.tier_id, endpoint, rule_data)

        return rule.max_requests, rule.window_seconds

    @staticmethod
    def to_rule_read(rule: RateLimitRule) -> RateLimitRuleRead:
        """Convert a RateLimitRule model to RateLimitRuleRead schema."""
        return RateLimitRuleRead(
            uuid=rule.uuid,
            tier_id=rule.tier_id,
            tier_slug=rule.tier.slug if rule.tier else None,
            tier_name=rule.tier.name if rule.tier else None,
            endpoint_pattern=rule.endpoint_pattern,
            max_requests=rule.max_requests,
            window_seconds=rule.window_seconds,
            description=rule.description,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )
