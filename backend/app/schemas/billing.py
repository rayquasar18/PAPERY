"""Billing request/response schemas — Stripe Checkout, Portal, subscription status."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CheckoutRequest(BaseModel):
    """Request body for creating a Stripe Checkout session."""

    tier_slug: str = Field(..., min_length=1, max_length=50)


class CheckoutResponse(BaseModel):
    """Response with the Stripe Checkout Session URL."""

    checkout_url: str


class PortalResponse(BaseModel):
    """Response with the Stripe Customer Portal URL."""

    portal_url: str


class SubscriptionStatusResponse(BaseModel):
    """Typed response for the subscription status endpoint.

    Replaces the previously untyped dict return from
    ``StripeService.get_subscription_status()``.
    """

    tier_slug: str
    tier_name: str
    has_stripe_subscription: bool
    subscription_status: str | None = None
    current_period_end: int | None = None
    cancel_at_period_end: bool | None = None
