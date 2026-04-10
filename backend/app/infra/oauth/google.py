"""Google OAuth provider implementation.

Flow:
1. Redirect to accounts.google.com/o/oauth2/v2/auth
2. Callback receives code → POST to oauth2.googleapis.com/token
3. Fetch user info from googleapis.com/oauth2/v2/userinfo
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

import httpx

from app.infra.oauth.base import OAuthProvider
from app.schemas.oauth import OAuthUserInfo

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class GoogleOAuthProvider(OAuthProvider):
    """Google OAuth 2.0 provider."""

    def get_authorization_url(self, state: str) -> str:
        """Build the Google OAuth consent URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def get_access_token(self, code: str) -> str:
        """Exchange authorization code for an access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            access_token = data.get("access_token")
            if not access_token:
                raise ValueError("Google OAuth: no access_token in response")
            return access_token

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Fetch user profile from Google."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()

        email = data.get("email")
        if not email:
            raise ValueError("Google OAuth: no email in user info")

        return OAuthUserInfo(
            provider="google",
            provider_user_id=str(data["id"]),
            email=email,
            name=data.get("name", ""),
        )
