"""UsageTracking repository — data access for quota tracking.

Provides upsert (increment) and current-period lookup methods
beyond the generic BaseRepository CRUD.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_tracking import UsageTracking
from app.repositories.base import BaseRepository


def _current_period_boundaries() -> tuple[datetime, datetime]:
    """Return (period_start, period_end) for the current UTC month.

    period_start: first day of current month at 00:00:00 UTC
    period_end: first day of next month at 00:00:00 UTC
    """
    now = datetime.now(UTC)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Next month: handle December → January rollover
    if now.month == 12:
        period_end = period_start.replace(year=now.year + 1, month=1)
    else:
        period_end = period_start.replace(month=now.month + 1)
    return period_start, period_end


class UsageTrackingRepository(BaseRepository[UsageTracking]):
    """Repository for UsageTracking model with domain-specific methods.

    Generic lookups are inherited from ``BaseRepository``.
    Domain methods handle monthly period logic and atomic upsert.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UsageTracking, session)

    async def get_current_period_count(self, user_id: int, metric: str) -> int:
        """Get the current month's usage count for a user and metric.

        Returns 0 if no record exists for the current period.
        """
        period_start, period_end = _current_period_boundaries()
        stmt = (
            select(UsageTracking.count)
            .where(
                UsageTracking.user_id == user_id,
                UsageTracking.metric == metric,
                UsageTracking.period_start == period_start,
                UsageTracking.period_end == period_end,
            )
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return row if row is not None else 0

    async def increment_usage(self, user_id: int, metric: str) -> int:
        """Atomically increment the usage counter for the current period.

        Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE (upsert) to
        handle both first-use and subsequent increments in a single
        statement. Returns the new count after incrementing.
        """
        period_start, period_end = _current_period_boundaries()

        stmt = (
            pg_insert(UsageTracking)
            .values(
                user_id=user_id,
                metric=metric,
                count=1,
                period_start=period_start,
                period_end=period_end,
            )
            .on_conflict_do_update(
                constraint="uq_usage_user_metric_period",
                set_={"count": UsageTracking.count + 1},
            )
            .returning(UsageTracking.count)
        )

        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.scalar_one()
