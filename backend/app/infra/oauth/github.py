"""GitHub OAuth provider implementation.

Flow:
1. Redirect to github.com/login/oauth/authorize
2. Callback receives code → POST to github.com/login/oauth/access_token
3. Fetch user info from api.github.com/user
4. If email is private, fallback to api.github.com/user/emails

~30% of GitHub users have private emails — the fallback is mandatory.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

import httpx

from app.infra.oauth.base import OAuthProvider
from app.schemas.oauth import OAuthUserInfo

logger = logging.getLogger(__name__)

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


class GitHubOAuthProvider(OAuthProvider):
    """GitHub OAuth 2.0 provider with private email fallback."""

    def get_authorization_url(self, state: str) -> str:
        """Build the GitHub OAuth consent URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        return f"{GITHUB_AUTH_URL}?{urlencode(params)}"

    async def get_access_token(self, code: str) -> str:
        """Exchange authorization code for an access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            access_token = data.get("access_token")
            if not access_token:
                error = data.get("error_description", "unknown error")
                raise ValueError(f"GitHub OAuth: token exchange failed — {error}")
            return access_token

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Fetch user profile from GitHub, with private email fallback.

        When a GitHub user has "Keep my email addresses private" enabled,
        the /user endpoint returns email=None. In that case, we call
        /user/emails to find their primary verified email. If that also
        fails, we construct a noreply address.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient() as client:
            # Step 1: Get user profile
            response = await client.get(GITHUB_USER_URL, headers=headers)
            response.raise_for_status()
            user_data = response.json()

            github_id = str(user_data["id"])
            name = user_data.get("name") or user_data.get("login", "")
            email = user_data.get("email")

            # Step 2: Private email fallback
            if not email:
                email = await self._fetch_primary_email(client, headers, github_id)

        return OAuthUserInfo(
            provider="github",
            provider_user_id=github_id,
            email=email,
            name=name,
        )

    async def _fetch_primary_email(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        github_id: str,
    ) -> str:
        """Fetch primary verified email from /user/emails endpoint.

        Falls back to {github_id}+noreply@users.noreply.github.com
        if no primary verified email is found.
        """
        try:
            response = await client.get(GITHUB_EMAILS_URL, headers=headers)
            response.raise_for_status()
            emails = response.json()

            # Find primary + verified email
            for entry in emails:
                if entry.get("primary") and entry.get("verified"):
                    return entry["email"]

            # Fallback: first verified email
            for entry in emails:
                if entry.get("verified"):
                    return entry["email"]

        except Exception:
            logger.warning("Failed to fetch GitHub emails for user %s", github_id, exc_info=True)

        # Final fallback: noreply address
        return f"{github_id}+noreply@users.noreply.github.com"
