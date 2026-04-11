"""Usage service — business logic for tier-aware usage quota enforcement.

Tracks and enforces per-user usage limits (projects, documents, fixes)
based on their tier's configured maximums.

Usage:
    service = UsageService(db)
    await service.enforce_limit(user, "projects")  # raises ForbiddenError if over limit
    await service.increment_usage(user.id, "projects")
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError
from app.models.user import User
from app.repositories.usage_tracking_repository import UsageTrackingRepository
from app.services.tier_service import TierService
from app.utils.tier_cache import get_cached_tier_data, set_cached_tier_data

logger = logging.getLogger(__name__)

# Maps metric names to tier data dict keys
METRIC_TO_LIMIT_KEY: dict[str, str] = {
    "projects": "max_projects",
    "documents": "max_docs_per_project",
    "fixes": "max_fixes_monthly",
}


class UsageService:
    """Class-based usage service — one instance per request lifecycle.

    Combines tier data resolution (via TierService + cache) with usage
    tracking (via UsageTrackingRepository) to enforce quotas.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db: AsyncSession = db
        self._usage_repo: UsageTrackingRepository = UsageTrackingRepository(db)
        self._tier_service: TierService = TierService(db)

    async def _resolve_tier_data(self, user: User) -> dict:
        """Get tier data from cache or DB (delegates to TierService)."""
        user_uuid_str = str(user.uuid)
        cached = await get_cached_tier_data(user_uuid_str)
        if cached is not None:
            return cached
        tier_data = await self._tier_service.get_user_tier_data(user)
        await set_cached_tier_data(user_uuid_str, tier_data)
        return tier_data

    async def enforce_limit(self, user: User, metric: str) -> None:
        """Check if the user has remaining quota for the given metric.

        Raises ForbiddenError with error_code USAGE_LIMIT_EXCEEDED
        if the user has reached or exceeded their tier's limit.

        Does nothing (returns None) if:
        - The metric is not in METRIC_TO_LIMIT_KEY (unknown metric — no limit)
        - The tier limit is -1 (unlimited)
        - The current usage is below the limit
        """
        limit_key = METRIC_TO_LIMIT_KEY.get(metric)
        if limit_key is None:
            logger.warning("Unknown usage metric: %s — skipping enforcement", metric)
            return

        tier_data = await self._resolve_tier_data(user)
        limit = tier_data.get(limit_key, 0)

        # -1 means unlimited (ultra tier convention)
        if limit == -1:
            return

        current = await self._usage_repo.get_current_period_count(user.id, metric)
        if current >= limit:
            raise ForbiddenError(
                detail=f"You've reached your {metric} limit ({limit}). Upgrade your plan to continue.",
                error_code="USAGE_LIMIT_EXCEEDED",
            )

    async def increment_usage(self, user_id: int, metric: str) -> int:
        """Increment the usage counter for the current billing period.

        Returns the new count after incrementing.
        Should be called AFTER the action succeeds (create project, upload doc, etc.).
        """
        return await self._usage_repo.increment_usage(user_id, metric)

    async def get_current_usage(self, user_id: int, metric: str) -> int:
        """Get the current period's usage count for a specific metric."""
        return await self._usage_repo.get_current_period_count(user_id, metric)

    async def get_usage_summary(self, user: User) -> dict[str, dict]:
        """Get a summary of all tracked metrics for the current period.

        Returns a dict like:
        {
            "projects": {"current": 2, "limit": 3},
            "documents": {"current": 8, "limit": 10},
            "fixes": {"current": 15, "limit": 20},
        }
        """
        tier_data = await self._resolve_tier_data(user)
        summary = {}

        for metric, limit_key in METRIC_TO_LIMIT_KEY.items():
            current = await self._usage_repo.get_current_period_count(user.id, metric)
            limit = tier_data.get(limit_key, 0)
            summary[metric] = {
                "current": current,
                "limit": limit,  # -1 means unlimited
            }

        return summary
