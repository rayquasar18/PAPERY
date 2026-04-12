"""RateLimitRule repository — data access for rate limit configuration."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_limit_rule import RateLimitRule
from app.repositories.base import BaseRepository


class RateLimitRuleRepository(BaseRepository[RateLimitRule]):
    """Repository for RateLimitRule model.

    Generic lookups inherited from BaseRepository:
        await repo.get(uuid=some_uuid)
        await repo.get_multi(skip=0, limit=50)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RateLimitRule, session)

    async def find_rule(
        self, tier_id: int | None, endpoint_pattern: str
    ) -> RateLimitRule | None:
        """Find the most specific rule for a tier + endpoint.

        Priority: tier-specific rule > default rule (tier_id=NULL).
        Returns None if no matching rule exists.
        """
        # Try tier-specific rule first
        if tier_id is not None:
            specific = await self.get(tier_id=tier_id, endpoint_pattern=endpoint_pattern)
            if specific is not None:
                return specific

        # Fall back to default rule (tier_id=NULL)
        stmt = (
            select(RateLimitRule)
            .where(
                RateLimitRule.tier_id.is_(None),
                RateLimitRule.endpoint_pattern == endpoint_pattern,
            )
        )
        stmt = self._not_deleted(stmt)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active(self) -> list[RateLimitRule]:
        """Fetch all active (non-deleted) rate limit rules."""
        stmt = (
            select(RateLimitRule)
            .order_by(RateLimitRule.endpoint_pattern, RateLimitRule.tier_id)
        )
        stmt = self._not_deleted(stmt)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
