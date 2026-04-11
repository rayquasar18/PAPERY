"""Tier service — business logic for tier management and tier data resolution.

Handles tier CRUD (admin), tier data resolution with Redis caching,
and cache invalidation on tier changes.

Usage:
    service = TierService(db)
    tiers = await service.list_active_tiers()
    tier_data = await service.get_user_tier_data(user)
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.tier import Tier
from app.models.user import User
from app.repositories.tier_repository import TierRepository
from app.schemas.tier import TierCreate, TierUpdate
from app.utils.tier_cache import (
    get_cached_tier_data,
    invalidate_tier_cache,
    set_cached_tier_data,
)

logger = logging.getLogger(__name__)

# Reserved slugs that cannot be deleted or have slug changed
PROTECTED_TIER_SLUGS: set[str] = {"free"}


class TierService:
    """Class-based tier service — one instance per request lifecycle.

    Constructor accepts an ``AsyncSession``; all methods use the same
    ``TierRepository`` instance created at construction time.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db: AsyncSession = db
        self._tier_repo: TierRepository = TierRepository(db)

    # ------------------------------------------------------------------
    # Read operations (public)
    # ------------------------------------------------------------------

    async def list_active_tiers(self) -> list[Tier]:
        """List all active (non-deleted) tiers."""
        return await self._tier_repo.get_multi(skip=0, limit=100)

    async def get_tier_by_uuid(self, tier_uuid) -> Tier:
        """Get a single tier by UUID. Raises NotFoundError if missing."""
        tier = await self._tier_repo.get(uuid=tier_uuid)
        if tier is None:
            raise NotFoundError(detail="Tier not found")
        return tier

    async def get_tier_by_slug(self, slug: str) -> Tier:
        """Get a single tier by slug. Raises NotFoundError if missing."""
        tier = await self._tier_repo.get(slug=slug)
        if tier is None:
            raise NotFoundError(detail=f"Tier with slug '{slug}' not found")
        return tier

    # ------------------------------------------------------------------
    # Tier data resolution with cache (for feature flags / usage limits)
    # ------------------------------------------------------------------

    async def get_user_tier_data(self, user: User) -> dict:
        """Resolve the full tier data dict for a user, with Redis caching.

        Cache hit: return from Redis.
        Cache miss: load from DB via user.tier relationship, cache, return.

        Returns a dict with keys:
            tier_slug, tier_name, max_projects, max_docs_per_project,
            max_fixes_monthly, max_file_size_mb, allowed_models, feature_flags
        """
        user_uuid_str = str(user.uuid)

        # Check cache first
        cached = await get_cached_tier_data(user_uuid_str)
        if cached is not None:
            return cached

        # Cache miss — build from DB
        tier = user.tier
        if tier is None:
            # Fallback for users with NULL tier_id (during migration)
            logger.warning("User %s has no tier — returning free-tier defaults", user.uuid)
            tier_data = {
                "tier_slug": "free",
                "tier_name": "Free",
                "max_projects": 3,
                "max_docs_per_project": 10,
                "max_fixes_monthly": 20,
                "max_file_size_mb": 10,
                "allowed_models": ["gpt-4o-mini"],
                "feature_flags": {},
            }
        else:
            tier_data = {
                "tier_slug": tier.slug,
                "tier_name": tier.name,
                "max_projects": tier.max_projects,
                "max_docs_per_project": tier.max_docs_per_project,
                "max_fixes_monthly": tier.max_fixes_monthly,
                "max_file_size_mb": tier.max_file_size_mb,
                "allowed_models": tier.allowed_models or [],
                "feature_flags": tier.feature_flags or {},
            }

        # Write to cache
        await set_cached_tier_data(user_uuid_str, tier_data)
        return tier_data

    # ------------------------------------------------------------------
    # Admin CRUD operations
    # ------------------------------------------------------------------

    async def create_tier(self, data: TierCreate) -> Tier:
        """Create a new tier. Raises ConflictError if slug already exists."""
        existing = await self._tier_repo.get(slug=data.slug)
        if existing is not None:
            raise ConflictError(detail=f"Tier with slug '{data.slug}' already exists")

        existing_name = await self._tier_repo.get(name=data.name)
        if existing_name is not None:
            raise ConflictError(detail=f"Tier with name '{data.name}' already exists")

        tier = Tier(
            name=data.name,
            slug=data.slug,
            description=data.description,
            max_projects=data.max_projects,
            max_docs_per_project=data.max_docs_per_project,
            max_fixes_monthly=data.max_fixes_monthly,
            max_file_size_mb=data.max_file_size_mb,
            allowed_models=data.allowed_models,
            feature_flags=data.feature_flags,
            stripe_price_id=data.stripe_price_id,
        )
        return await self._tier_repo.create(tier)

    async def update_tier(self, tier: Tier, data: TierUpdate) -> Tier:
        """Update an existing tier. Only provided (non-None) fields are updated.

        Raises BadRequestError if trying to change the slug of a protected tier.
        Raises ConflictError if new slug or name conflicts with another tier.
        """
        if data.slug is not None and tier.slug in PROTECTED_TIER_SLUGS and data.slug != tier.slug:
            raise BadRequestError(
                detail=f"Cannot change slug of protected tier '{tier.slug}'"
            )

        # Check for slug conflicts
        if data.slug is not None and data.slug != tier.slug:
            existing = await self._tier_repo.get(slug=data.slug)
            if existing is not None:
                raise ConflictError(detail=f"Tier with slug '{data.slug}' already exists")

        # Check for name conflicts
        if data.name is not None and data.name != tier.name:
            existing = await self._tier_repo.get(name=data.name)
            if existing is not None:
                raise ConflictError(detail=f"Tier with name '{data.name}' already exists")

        # Apply non-None fields
        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(tier, field, value)

        return await self._tier_repo.update(tier)

    async def soft_delete_tier(self, tier: Tier) -> Tier:
        """Soft-delete a tier. Raises BadRequestError if it's a protected tier."""
        if tier.slug in PROTECTED_TIER_SLUGS:
            raise BadRequestError(
                detail=f"Cannot delete protected tier '{tier.slug}'. The free tier must always exist."
            )
        return await self._tier_repo.soft_delete(tier)
