"""Abstract base class for OAuth providers.

Each provider subclass implements the three-step OAuth flow:
1. Generate authorization URL (redirect user to provider)
2. Exchange authorization code for access token
3. Fetch user info from provider API

Uses httpx.AsyncClient for all HTTP calls (per-request, no lifecycle mgmt).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import httpx

from app.schemas.oauth import OAuthUserInfo

logger = logging.getLogger(__name__)


class OAuthProvider(ABC):
    """Base OAuth provider with httpx.AsyncClient."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Return the URL to redirect the user to for OAuth consent."""
        ...

    @abstractmethod
    async def get_access_token(self, code: str) -> str:
        """Exchange the authorization code for an access token."""
        ...

    @abstractmethod
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Fetch the user's profile from the provider API."""
        ...
