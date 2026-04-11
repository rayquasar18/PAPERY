"""Stripe billing service — checkout, portal, subscription status, webhook handling.

Manages Stripe integration for subscription billing:
- Checkout Session creation (new subscriptions)
- Customer Portal session (self-service management)
- Webhook event handlers (tier changes, payment events)

All Stripe API calls use the static API key pattern (set once at module
import time). The per-request StripeClient pattern can be adopted in v2.

Usage:
    service = StripeService(db)
    url = await service.create_checkout_session(user, tier)
"""

from __future__ import annotations

import logging

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.configs import settings
from app.core.exceptions import BadRequestError, NotFoundError

# Set API key once at module level — avoids redundant global mutation on
# every StripeService instantiation and is safe for async (single process).
stripe.api_key = settings.STRIPE_SECRET_KEY
from app.models.tier import Tier
from app.models.user import User
from app.repositories.tier_repository import TierRepository
from app.repositories.user_repository import UserRepository
from app.schemas.billing import SubscriptionStatusResponse
from app.utils.tier_cache import invalidate_tier_cache

logger = logging.getLogger(__name__)


class StripeService:
    """Class-based Stripe service — one instance per request lifecycle.

    Constructor accepts an ``AsyncSession``; all methods use the same
    repository instances created at construction time.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db: AsyncSession = db
        self._user_repo: UserRepository = UserRepository(db)
        self._tier_repo: TierRepository = TierRepository(db)
        # Set API key for all Stripe operations in this service
        stripe.api_key = settings.STRIPE_SECRET_KEY

    # ------------------------------------------------------------------
    # Checkout & Portal (user-facing)
    # ------------------------------------------------------------------

    async def create_checkout_session(self, user: User, tier: Tier) -> str:
        """Create a Stripe Checkout Session for a subscription.

        Returns the Checkout Session URL to redirect the user to.

        Raises:
            BadRequestError: If the tier has no stripe_price_id (e.g., free tier).
        """
        if not tier.stripe_price_id:
            raise BadRequestError(
                detail=f"Tier '{tier.slug}' does not have a Stripe price configured. Cannot create checkout.",
                error_code="NO_STRIPE_PRICE",
            )

        # Create or retrieve Stripe Customer
        if user.stripe_customer_id is None:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={
                    "user_uuid": str(user.uuid),
                    "papery_user_id": str(user.id),
                },
            )
            user.stripe_customer_id = customer.id
            await self._user_repo.update(user)
            logger.info("Created Stripe customer %s for user %s", customer.id, user.uuid)

        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            line_items=[{"price": tier.stripe_price_id, "quantity": 1}],
            mode="subscription",
            success_url=settings.STRIPE_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.STRIPE_CANCEL_URL,
            metadata={
                "user_uuid": str(user.uuid),
                "tier_slug": tier.slug,
            },
            subscription_data={
                "metadata": {
                    "user_uuid": str(user.uuid),
                    "tier_slug": tier.slug,
                },
            },
        )

        logger.info(
            "Created Stripe checkout session for user %s, tier %s",
            user.uuid,
            tier.slug,
        )
        return session.url

    async def create_portal_session(self, user: User) -> str:
        """Create a Stripe Customer Portal session for subscription management.

        Returns the portal URL to redirect the user to.

        Raises:
            BadRequestError: If the user has no Stripe customer ID.
        """
        if user.stripe_customer_id is None:
            raise BadRequestError(
                detail="No active subscription found. Subscribe to a plan first.",
                error_code="NO_STRIPE_CUSTOMER",
            )

        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=settings.STRIPE_PORTAL_RETURN_URL,
        )

        logger.info("Created Stripe portal session for user %s", user.uuid)
        return session.url

    async def get_subscription_status(self, user: User) -> SubscriptionStatusResponse:
        """Get the user's current subscription status.

        Returns a typed SubscriptionStatusResponse with tier info and Stripe subscription state.
        """
        tier = user.tier
        tier_slug = tier.slug if tier else "free"
        tier_name = tier.name if tier else "Free"
        has_stripe_subscription = user.stripe_customer_id is not None

        subscription_status: str | None = None
        current_period_end: int | None = None
        cancel_at_period_end: bool | None = None

        if user.stripe_customer_id:
            try:
                subscriptions = stripe.Subscription.list(
                    customer=user.stripe_customer_id,
                    status="active",
                    limit=1,
                )
                if subscriptions.data:
                    sub = subscriptions.data[0]
                    subscription_status = sub.status
                    current_period_end = sub.current_period_end
                    cancel_at_period_end = sub.cancel_at_period_end
                else:
                    subscription_status = "none"
            except stripe.error.StripeError as exc:
                logger.warning("Stripe API error fetching subscription: %s", exc)
                subscription_status = "unknown"

        return SubscriptionStatusResponse(
            tier_slug=tier_slug,
            tier_name=tier_name,
            has_stripe_subscription=has_stripe_subscription,
            subscription_status=subscription_status,
            current_period_end=current_period_end,
            cancel_at_period_end=cancel_at_period_end,
        )

    # ------------------------------------------------------------------
    # Webhook event handlers (called from billing router)
    # ------------------------------------------------------------------

    async def handle_checkout_completed(self, session_obj: dict) -> None:
        """Handle checkout.session.completed — new subscription created.

        Reads tier_slug from session metadata, updates user's tier_id.
        """
        user_uuid = session_obj.get("metadata", {}).get("user_uuid")
        tier_slug = session_obj.get("metadata", {}).get("tier_slug")
        stripe_customer_id = session_obj.get("customer")

        if not user_uuid or not tier_slug:
            logger.warning("checkout.session.completed missing metadata: %s", session_obj.get("id"))
            return

        user = await self._user_repo.get(uuid=user_uuid)
        if user is None:
            logger.error("checkout.session.completed — user not found: %s", user_uuid)
            return

        tier = await self._tier_repo.get(slug=tier_slug)
        if tier is None:
            logger.error("checkout.session.completed — tier not found: %s", tier_slug)
            return

        # Idempotency: skip if user already has this tier
        if user.tier_id == tier.id:
            logger.info("User %s already on tier %s — skipping", user_uuid, tier_slug)
            return

        # Update user
        user.tier_id = tier.id
        if stripe_customer_id and user.stripe_customer_id is None:
            user.stripe_customer_id = stripe_customer_id
        await self._user_repo.update(user)

        # Invalidate tier cache
        await invalidate_tier_cache(str(user.uuid))
        logger.info("checkout.session.completed — user %s upgraded to %s", user_uuid, tier_slug)

    async def handle_subscription_updated(self, subscription_obj: dict) -> None:
        """Handle customer.subscription.updated — plan change (upgrade/downgrade).

        Maps the subscription's price to a tier and updates the user.
        """
        customer_id = subscription_obj.get("customer")
        metadata = subscription_obj.get("metadata", {})
        tier_slug = metadata.get("tier_slug")

        if not customer_id:
            logger.warning("subscription.updated missing customer ID")
            return

        user = await self._user_repo.get(stripe_customer_id=customer_id)
        if user is None:
            logger.error("subscription.updated — user not found for customer: %s", customer_id)
            return

        # Try metadata first, then fall back to price-based lookup
        if tier_slug:
            tier = await self._tier_repo.get(slug=tier_slug)
        else:
            # Fall back: map price_id to tier
            items = subscription_obj.get("items", {}).get("data", [])
            price_id = items[0]["price"]["id"] if items else None
            tier = await self._tier_repo.get(stripe_price_id=price_id) if price_id else None

        if tier is None:
            logger.warning("subscription.updated — could not resolve tier for customer %s", customer_id)
            return

        # Idempotency check
        if user.tier_id == tier.id:
            logger.info("User %s already on tier %s — skipping", user.uuid, tier.slug)
            return

        user.tier_id = tier.id
        await self._user_repo.update(user)
        await invalidate_tier_cache(str(user.uuid))
        logger.info("subscription.updated — user %s changed to tier %s", user.uuid, tier.slug)

    async def handle_subscription_deleted(self, subscription_obj: dict) -> None:
        """Handle customer.subscription.deleted — cancellation.

        Downgrades user back to the free tier.
        """
        customer_id = subscription_obj.get("customer")
        if not customer_id:
            logger.warning("subscription.deleted missing customer ID")
            return

        user = await self._user_repo.get(stripe_customer_id=customer_id)
        if user is None:
            logger.error("subscription.deleted — user not found for customer: %s", customer_id)
            return

        free_tier = await self._tier_repo.get(slug="free")
        if free_tier is None:
            logger.error("subscription.deleted — free tier not found in database")
            return

        # Idempotency: skip if already on free tier
        if user.tier_id == free_tier.id:
            logger.info("User %s already on free tier — skipping", user.uuid)
            return

        user.tier_id = free_tier.id
        await self._user_repo.update(user)
        await invalidate_tier_cache(str(user.uuid))
        logger.info("subscription.deleted — user %s downgraded to free", user.uuid)

    async def handle_invoice_paid(self, invoice_obj: dict) -> None:
        """Handle invoice.paid — successful payment confirmation.

        Mostly a confirmation event. The tier should already be set
        by checkout.session.completed or subscription.updated.
        """
        customer_id = invoice_obj.get("customer")
        subscription_id = invoice_obj.get("subscription")
        logger.info(
            "invoice.paid — customer=%s subscription=%s amount=%s",
            customer_id,
            subscription_id,
            invoice_obj.get("amount_paid"),
        )

    async def handle_payment_failed(self, invoice_obj: dict) -> None:
        """Handle invoice.payment_failed — payment failure.

        Logs the failure. Future: send notification email to user.
        """
        customer_id = invoice_obj.get("customer")
        logger.warning(
            "invoice.payment_failed — customer=%s subscription=%s",
            customer_id,
            invoice_obj.get("subscription"),
        )
        # TODO: Send payment failure notification email in v2

    async def handle_customer_updated(self, customer_obj: dict) -> None:
        """Handle customer.updated — customer info change.

        Currently just logs. Could sync email changes in the future.
        """
        customer_id = customer_obj.get("id")
        logger.info("customer.updated — customer=%s", customer_id)
