"""OAuth provider configuration.

Credentials default to empty strings — when empty, OAuth endpoints
return 404 (graceful disable per D-12).
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class OAuthConfig(BaseSettings):
    GOOGLE_CLIENT_ID: str = Field(default="")
    GOOGLE_CLIENT_SECRET: str = Field(default="")
    GITHUB_CLIENT_ID: str = Field(default="")
    GITHUB_CLIENT_SECRET: str = Field(default="")
    OAUTH_REDIRECT_BASE_URL: str = Field(default="http://localhost:8000")
