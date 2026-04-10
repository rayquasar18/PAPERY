"""OAuth-related schemas — provider user info."""

from __future__ import annotations

from pydantic import BaseModel


class OAuthUserInfo(BaseModel):
    """Normalized user info returned by an OAuth provider.

    All providers must map their response to this structure
    before passing to the auth service layer.
    """

    provider: str
    provider_user_id: str
    email: str
    name: str
