"""Billing routes — Stripe Checkout, Portal, subscription status, webhook."""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_active_user
from app.configs import settings
from app.core.db.session import get_session
from app.models.user import User
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
    SubscriptionStatusResponse,
)
from app.services.stripe_service import StripeService
from app.services.tier_service import TierService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# --------------------------------------------------------------------------
# Authenticated endpoints (JWT required)
# --------------------------------------------------------------------------


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    data: CheckoutRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> CheckoutResponse:
    """Create a Stripe Checkout Session and return the URL.

    The user will be redirected to this URL to complete payment.
    """
    tier_service = TierService(db)
    tier = await tier_service.get_tier_by_slug(data.tier_slug)

    stripe_service = StripeService(db)
    url = await stripe_service.create_checkout_session(user, tier)
    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> PortalResponse:
    """Create a Stripe Customer Portal session for subscription self-management.

    User can upgrade, downgrade, cancel, and update payment methods.
    """
    stripe_service = StripeService(db)
    url = await stripe_service.create_portal_session(user)
    return PortalResponse(portal_url=url)


@router.get("/subscription", response_model=SubscriptionStatusResponse)
async def get_subscription(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session),
) -> SubscriptionStatusResponse:
    """Get the current user's subscription status."""
    stripe_service = StripeService(db)
    return await stripe_service.get_subscription_status(user)


# --------------------------------------------------------------------------
# Webhook endpoint (NO JWT auth — authenticated via Stripe signature)
# --------------------------------------------------------------------------


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Handle Stripe webhook events.

    CRITICAL: This endpoint does NOT use JWT authentication.
    Authentication is via Stripe webhook signature verification.
    The raw request body MUST be read via request.body() — NOT request.json().
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        logger.warning("Stripe webhook: invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        logger.warning("Stripe webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Route to event handlers
    event_type = event["type"]
    event_data = event["data"]["object"]

    stripe_service = StripeService(db)

    handlers = {
        "checkout.session.completed": stripe_service.handle_checkout_completed,
        "customer.subscription.updated": stripe_service.handle_subscription_updated,
        "customer.subscription.deleted": stripe_service.handle_subscription_deleted,
        "invoice.paid": stripe_service.handle_invoice_paid,
        "invoice.payment_failed": stripe_service.handle_payment_failed,
        "customer.updated": stripe_service.handle_customer_updated,
    }

    handler = handlers.get(event_type)
    if handler:
        await handler(event_data)
        logger.info("Processed Stripe webhook event: %s", event_type)
    else:
        logger.debug("Unhandled Stripe webhook event type: %s", event_type)

    return {"status": "ok"}
