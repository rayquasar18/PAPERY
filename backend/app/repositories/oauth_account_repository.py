"""OAuthAccount-specific repository — data access for OAuth provider links.

Generic lookups are handled by ``BaseRepository.get(**filters)`` — this
repository adds a convenience factory method for creating OAuth accounts.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import OAuthAccount
from app.repositories.base import BaseRepository


class OAuthAccountRepository(BaseRepository[OAuthAccount]):
    """Repository for OAuthAccount model with domain-specific factory methods.

    Generic lookups are inherited from ``BaseRepository``::

        await repo.get(provider="google", provider_user_id="12345")
        await repo.get(user_id=1)
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OAuthAccount, session)

    async def create_oauth_account(
        self,
        *,
        user_id: int,
        provider: str,
        provider_user_id: str,
        provider_email: str | None = None,
    ) -> OAuthAccount:
        """Create and persist a new OAuthAccount record.

        Returns the refreshed OAuthAccount instance with database-generated
        fields (id, created_at, etc.) populated.
        """
        account = OAuthAccount(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
        )
        return await self.create(account)
