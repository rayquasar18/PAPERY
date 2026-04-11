"""Stripe billing configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings


class StripeConfig(BaseSettings):
    """Stripe API keys and redirect URLs.

    All values default to empty string for local development.
    Production deployment must set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET.
    """

    STRIPE_SECRET_KEY: str = Field(default="")
    STRIPE_PUBLISHABLE_KEY: str = Field(default="")
    STRIPE_WEBHOOK_SECRET: str = Field(default="")
    STRIPE_SUCCESS_URL: str = Field(default="http://localhost:3000/billing/success")
    STRIPE_CANCEL_URL: str = Field(default="http://localhost:3000/billing/cancel")
    STRIPE_PORTAL_RETURN_URL: str = Field(default="http://localhost:3000/account")
