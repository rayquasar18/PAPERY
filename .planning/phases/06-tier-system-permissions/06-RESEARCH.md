# Phase 6: Tier System & Permissions — Research

**Researched:** 2026-04-11
**Status:** Complete — ready for plan creation

---

## 1. Overview: What This Phase Builds

Phase 6 implements the subscription/tier layer that gates all SaaS features:

1. **Tier data model** — `Tier` table with dedicated columns + JSONB for feature flags
2. **UsageTracking model** — tracks per-user monthly quotas
3. **User ↔ Tier link** — `tier_id` FK on `User`, auto-assigned to "free" on registration
4. **Feature flag dependencies** — `require_feature('can_export_pdf')` pattern via FastAPI DI
5. **Usage limit enforcement** — `check_usage('documents')` before quota-bound operations
6. **Redis tier cache** — 5-min TTL cache on `cache_client` (db=0) per user UUID
7. **Stripe billing** — Checkout Session + Customer Portal + webhook event handling
8. **StripeConfig** — new Pydantic Settings module added to `AppSettings`

---

## 2. Tier Data Model Design

### 2.1 SQLAlchemy Model with JSONB (D-01, D-06–D-10)

```python
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin

class Tier(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tier"

    # Human-readable name + slug
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # "Free", "Pro", "Ultra"
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)   # "free", "pro", "ultra"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Dedicated columns for typed, query-able limits (D-06–D-10) ---
    max_projects: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_docs_per_project: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_fixes_monthly: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    max_file_size_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    # --- JSONB for flexible data ---
    # allowed_models: ["gpt-4o-mini"] | ["gpt-4o", "claude-sonnet"] | ["*"]
    allowed_models: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # feature_flags: {"can_export_pdf": false, "can_translate": false, "priority_support": false}
    feature_flags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Stripe price ID for this tier (nullable for free tier)
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # users relationship (back-populated from User.tier)
```

**JSONB key insight:** SQLAlchemy's `JSONB` (from `sqlalchemy.dialects.postgresql`) is native PostgreSQL JSONB — binary storage, indexable, supports `has_key()`, `contains()`, `@>` operators. Python dicts/lists map directly to JSONB columns.

### 2.2 Three Default Tiers (D-02)

| Slug | name | max_projects | max_docs | max_fixes/month | max_file_mb | feature_flags notes |
|------|------|-------------|----------|-----------------|-------------|---------------------|
| `free` | Free | 3 | 10 | 20 | 10 | All flags off |
| `pro` | Pro | 20 | 100 | 500 | 50 | export_pdf, translate on |
| `ultra` | Ultra | unlimited (-1) | unlimited (-1) | unlimited (-1) | 100 | All flags on |

Convention: `-1` means unlimited — check `limit == -1` before enforcing.

### 2.3 User FK Addition (D-05)

Add to `User` model:
```python
# In User model
tier_id: Mapped[int] = mapped_column(
    BigInteger,
    ForeignKey("tier.id", ondelete="RESTRICT"),  # Prevent tier deletion if users exist
    nullable=False,
    index=True,
)
tier: Mapped["Tier"] = relationship("Tier", lazy="selectin")
```

**Migration concern:** Existing `User` rows have no `tier_id`. Migration must:
1. Create `tier` table and seed the 3 default tiers
2. Add `tier_id` column as nullable first
3. Backfill: `UPDATE user SET tier_id = (SELECT id FROM tier WHERE slug = 'free')`
4. Add `NOT NULL` constraint in a second step

---

## 3. UsageTracking Model (D-17)

```python
class UsageTracking(Base, TimestampMixin):
    __tablename__ = "usage_tracking"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(100), nullable=False)     # "projects", "documents", "fixes"
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "metric", "period_start", name="uq_usage_user_metric_period"),
        Index("ix_usage_user_metric_active", "user_id", "metric", "period_end"),
    )
```

**Period logic:** Monthly periods. `period_start` = first day of current month (UTC), `period_end` = last day. On upsert: `INSERT ... ON CONFLICT DO UPDATE SET count = count + 1`.

---

## 4. Registration: Auto-Assign Free Tier (D-04)

Modify `UserRepository.create_user()` to accept `tier_id`:

```python
async def create_user(self, *, email, hashed_password, is_active, is_verified, is_superuser, tier_id: int) -> User:
    user = User(email=..., tier_id=tier_id, ...)
    return await self.create(user)
```

In `AuthService.register_user()` and `oauth_login_or_register()`:
```python
free_tier = await tier_repo.get(slug="free")
if free_tier is None:
    raise RuntimeError("Free tier not seeded — run database seeder")
user = await self._user_repo.create_user(..., tier_id=free_tier.id)
```

**`UserProfileRead` fix (D-12 Phase 5):** Replace hardcoded `tier_name: str = "free"` with actual tier data:
```python
tier_name: str           # populated from user.tier.slug via relationship
tier_slug: str           # same as tier.slug
```

---

## 5. Redis Tier Cache (D-12, D-13)

**Cache key pattern:** `tier:user:{user_uuid}` stored in `cache_client` (Redis db=0, existing).

```python
import json
from app.infra.redis import client as redis_client

TIER_CACHE_TTL = 300  # 5 minutes (D-12)
TIER_CACHE_KEY_PREFIX = "tier:user:"

async def get_cached_tier_data(user_uuid: str) -> dict | None:
    """Read tier data from Redis cache."""
    key = f"{TIER_CACHE_KEY_PREFIX}{user_uuid}"
    raw = await redis_client.cache_client.get(key)
    return json.loads(raw) if raw else None

async def set_cached_tier_data(user_uuid: str, tier_data: dict) -> None:
    """Write tier data to cache with 5-min TTL."""
    key = f"{TIER_CACHE_KEY_PREFIX}{user_uuid}"
    await redis_client.cache_client.setex(key, TIER_CACHE_TTL, json.dumps(tier_data))

async def invalidate_tier_cache(user_uuid: str) -> None:
    """Remove cache entry immediately on tier change (D-13)."""
    key = f"{TIER_CACHE_KEY_PREFIX}{user_uuid}"
    await redis_client.cache_client.delete(key)
```

**Cache payload structure** (serialize from Tier model):
```json
{
  "tier_slug": "pro",
  "tier_name": "Pro",
  "max_projects": 20,
  "max_docs_per_project": 100,
  "max_fixes_monthly": 500,
  "max_file_size_mb": 50,
  "allowed_models": ["gpt-4o", "claude-sonnet"],
  "feature_flags": {"can_export_pdf": true, "can_translate": true}
}
```

---

## 6. Feature Flag Dependency Injection (D-11)

**Pattern:** Callable class with `__init__` accepting the feature name, `__call__` resolving via existing `get_current_active_user` dependency.

```python
# app/api/dependencies.py additions

class RequireFeature:
    """Dependency that enforces a feature flag from the user's tier.
    
    Usage: Depends(RequireFeature("can_export_pdf"))
    """
    def __init__(self, feature: str) -> None:
        self.feature = feature

    async def __call__(
        self,
        user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_session),
    ) -> User:
        tier_data = await get_cached_tier_data(str(user.uuid))
        if tier_data is None:
            # Cache miss — load from DB and cache
            tier_service = TierService(db)
            tier_data = await tier_service.get_user_tier_data(user)
            await set_cached_tier_data(str(user.uuid), tier_data)

        flags = tier_data.get("feature_flags", {})
        if not flags.get(self.feature, False):
            raise ForbiddenError(
                detail=f"Your plan does not include '{self.feature}'. Upgrade to access this feature.",
                error_code="FEATURE_NOT_AVAILABLE",
            )
        return user


# Usage on routes:
@router.post("/documents/export-pdf")
async def export_pdf(user: User = Depends(RequireFeature("can_export_pdf"))):
    ...
```

---

## 7. Usage Limit Dependency Injection (D-18)

```python
class CheckUsageLimit:
    """Dependency that enforces a usage quota for the current billing period.
    
    Usage: Depends(CheckUsageLimit("documents"))
    """
    def __init__(self, metric: str) -> None:
        self.metric = metric

    async def __call__(
        self,
        user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_session),
    ) -> User:
        usage_service = UsageService(db)
        await usage_service.enforce_limit(user, self.metric)
        return user


# Usage:
@router.post("/projects")
async def create_project(user: User = Depends(CheckUsageLimit("projects"))):
    ...
```

**`UsageService.enforce_limit()` logic:**
```python
async def enforce_limit(self, user: User, metric: str) -> None:
    tier_data = await get_or_cache_tier_data(user)
    limit_key = f"max_{metric}"  # "max_projects", "max_docs_per_project", etc.
    limit = tier_data.get(limit_key, 0)
    
    if limit == -1:  # Unlimited (ultra tier)
        return
    
    current = await self._usage_repo.get_current_period_count(user.id, metric)
    if current >= limit:
        raise ForbiddenError(
            detail=f"You've reached your {metric} limit ({limit}). Upgrade to continue.",
            error_code="USAGE_LIMIT_EXCEEDED",
        )
```

---

## 8. Stripe Billing Integration

### 8.1 StripeConfig (new config module)

```python
# app/configs/stripe.py
from pydantic import Field
from pydantic_settings import BaseSettings

class StripeConfig(BaseSettings):
    STRIPE_SECRET_KEY: str = Field(default="")           # sk_test_... / sk_live_...
    STRIPE_PUBLISHABLE_KEY: str = Field(default="")      # pk_test_... / pk_live_...
    STRIPE_WEBHOOK_SECRET: str = Field(default="")       # whsec_...
    STRIPE_SUCCESS_URL: str = Field(default="")          # frontend redirect after checkout
    STRIPE_CANCEL_URL: str = Field(default="")           # frontend redirect on cancel
    STRIPE_PORTAL_RETURN_URL: str = Field(default="")    # frontend redirect from portal
```

Add to `AppSettings(StripeConfig, ...)` in `configs/__init__.py`.

### 8.2 Stripe User Model: stripe_customer_id on User

Add to `User` model:
```python
stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
```

This links PAPERY users to Stripe Customers — required for portal sessions and webhook reconciliation.

### 8.3 Checkout Session (D-19)

```python
import stripe

async def create_checkout_session(user: User, tier: Tier, success_url: str, cancel_url: str) -> str:
    """Create a Stripe Checkout Session. Returns the session URL."""
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Create or retrieve Stripe Customer
    if user.stripe_customer_id is None:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_uuid": str(user.uuid), "papery_user_id": str(user.id)},
        )
        # Persist stripe_customer_id to User
        user.stripe_customer_id = customer.id
        await user_repo.update(user)
    
    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        line_items=[{"price": tier.stripe_price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"user_uuid": str(user.uuid), "tier_slug": tier.slug},
        subscription_data={
            "metadata": {"user_uuid": str(user.uuid), "tier_slug": tier.slug}
        },
    )
    return session.url
```

### 8.4 Customer Portal Session (D-20)

```python
async def create_portal_session(user: User, return_url: str) -> str:
    """Create a Stripe Customer Portal session. Returns the portal URL."""
    if user.stripe_customer_id is None:
        raise BadRequestError(detail="No active subscription found")
    
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url,
    )
    return session.url
```

### 8.5 Webhook Handler (D-21, D-23)

**Critical requirement:** Raw request body must reach `stripe.Webhook.construct_event()` — FastAPI's `Request.body()` returns raw bytes, which is correct. Do NOT parse through Pydantic first.

```python
# app/api/v1/billing.py

from fastapi import APIRouter, Request, HTTPException
import stripe

router = APIRouter(prefix="/billing", tags=["billing"])

@router.post("/webhook", include_in_schema=False)  # Exclude from OpenAPI docs
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_session)):
    payload = await request.body()  # Raw bytes — MUST NOT use request.json()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Route to event handlers
    event_type = event["type"]
    stripe_service = StripeService(db)
    
    handlers = {
        "checkout.session.completed":       stripe_service.handle_checkout_completed,
        "customer.subscription.updated":    stripe_service.handle_subscription_updated,
        "customer.subscription.deleted":    stripe_service.handle_subscription_deleted,
        "invoice.paid":                     stripe_service.handle_invoice_paid,
        "invoice.payment_failed":           stripe_service.handle_payment_failed,
        "customer.updated":                 stripe_service.handle_customer_updated,
    }
    
    handler = handlers.get(event_type)
    if handler:
        await handler(event["data"]["object"])
    
    return {"status": "ok"}
```

### 8.6 Webhook Event Logic

**`checkout.session.completed`:**
- `session.metadata["tier_slug"]` → find Tier by slug
- `session.customer` → user by `stripe_customer_id`
- Update `user.tier_id` to new tier
- Invalidate Redis tier cache for user
- Create/update subscription record (optional: `Subscription` model for audit trail)

**`customer.subscription.updated`:**
- Get subscription's `metadata.tier_slug` or map `price.id` → tier
- Update `user.tier_id`
- Invalidate cache

**`customer.subscription.deleted`:**
- Downgrade user back to "free" tier
- Invalidate cache

**`invoice.payment_failed`:**
- Log event, optionally notify user via email
- Could add a `payment_status` field to User or separate table for audit

**`invoice.paid`:**
- Idempotency check — tier may already be set from `checkout.session.completed`
- Confirm subscription is still active

### 8.7 Idempotency

Stripe may retry webhook events. All handlers must be idempotent:
- Check current state before applying change
- Use `stripe_event_id` (from `event["id"]`) to deduplicate if needed
- Example: "if user already has pro tier, skip tier update"

---

## 9. API Routes

### 9.1 Tiers Router (`app/api/v1/tiers.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/tiers` | Public | List all active tiers |
| `GET` | `/tiers/{tier_uuid}` | Public | Get tier details |
| `POST` | `/tiers` | Superuser | Create tier (admin) |
| `PATCH` | `/tiers/{tier_uuid}` | Superuser | Update tier (admin) |
| `DELETE` | `/tiers/{tier_uuid}` | Superuser | Soft-delete tier (admin) |

### 9.2 Billing Router (`app/api/v1/billing.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/billing/checkout` | JWT | Create Checkout Session → return URL |
| `POST` | `/billing/portal` | JWT | Create Customer Portal Session → return URL |
| `GET` | `/billing/subscription` | JWT | Get user's current subscription status |
| `POST` | `/billing/webhook` | None (Stripe sig) | Stripe webhook endpoint |

---

## 10. Service Layer Architecture

```
TierService(db)
  - get_user_tier_data(user) → dict (with cache check/fill)
  - get_tier_by_slug(slug) → Tier
  - list_tiers() → list[Tier]
  - create_tier(data) → Tier
  - update_tier(tier, data) → Tier
  - soft_delete_tier(tier) → Tier

UsageService(db)
  - enforce_limit(user, metric) → None | raise ForbiddenError
  - increment_usage(user_id, metric) → None
  - get_current_usage(user_id, metric) → int
  - reset_monthly_usage(user_id, metric) → None

StripeService(db)
  - create_checkout_session(user, tier) → str (URL)
  - create_portal_session(user) → str (URL)
  - get_subscription_status(user) → dict
  - handle_checkout_completed(session_obj) → None
  - handle_subscription_updated(subscription_obj) → None
  - handle_subscription_deleted(subscription_obj) → None
  - handle_invoice_paid(invoice_obj) → None
  - handle_payment_failed(invoice_obj) → None
  - handle_customer_updated(customer_obj) → None
```

---

## 11. File Tree (New Files This Phase)

```
backend/app/
├── models/
│   ├── tier.py                      # Tier model (JSONB columns)
│   └── usage_tracking.py            # UsageTracking model
├── repositories/
│   ├── tier_repository.py           # TierRepository(BaseRepository[Tier])
│   └── usage_tracking_repository.py # UsageTrackingRepository
├── schemas/
│   └── tier.py                      # TierRead, TierCreate, TierUpdate, TierReadPublic
├── services/
│   ├── tier_service.py              # TierService + Redis cache helpers
│   ├── usage_service.py             # UsageService
│   └── stripe_service.py            # StripeService (Checkout + Portal + webhooks)
├── api/v1/
│   ├── tiers.py                     # Tier CRUD routes
│   └── billing.py                   # Billing + webhook routes
├── configs/
│   └── stripe.py                    # StripeConfig (new Pydantic Settings module)
└── utils/
    └── tier_cache.py                # Redis cache helpers for tier data

migrations/versions/
    └── xxxx_phase6_tier_system.py   # Single migration: tier + usage_tracking tables,
                                     # User.tier_id FK, User.stripe_customer_id
```

**Modified files:**
- `backend/app/models/user.py` — add `tier_id` FK, `stripe_customer_id`, `tier` relationship
- `backend/app/models/__init__.py` — register Tier and UsageTracking in barrel import
- `backend/app/configs/__init__.py` — add `StripeConfig` to `AppSettings`
- `backend/app/api/dependencies.py` — add `RequireFeature`, `CheckUsageLimit` callables
- `backend/app/api/v1/__init__.py` or router registration — include tiers + billing routers
- `backend/app/services/auth_service.py` — auto-assign free tier in `register_user()` and `oauth_login_or_register()`
- `backend/app/repositories/user_repository.py` — add `tier_id` param to `create_user()`
- `backend/app/schemas/user.py` — replace hardcoded `tier_name: str = "free"` with real tier fields

---

## 12. Key Design Patterns from Codebase

| Pattern | How to Apply |
|---------|-------------|
| `BaseRepository[Model]` generic | `TierRepository(BaseRepository[Tier])`, `UsageTrackingRepository(BaseRepository[UsageTracking])` |
| `AuthService(db)` constructor DI | `TierService(db)`, `UsageService(db)`, `StripeService(db)` — same pattern |
| `get_current_user` → `get_current_active_user` chain | `RequireFeature.__call__` depends on `get_current_active_user` |
| `PaperyHTTPException` subclasses | `ForbiddenError` for feature/usage violations, `NotFoundError` for missing tiers |
| `SecurityConfig` in `configs/security.py` | New `StripeConfig` in `configs/stripe.py`, added to `AppSettings` |
| Soft delete via `SoftDeleteMixin` | Apply to `Tier` model (admin can soft-delete custom tiers) |
| Dual ID: `id` (int) + `uuid` (public) | Apply to `Tier` model via `UUIDMixin` |
| `server_default=func.now()` | Use in `UsageTracking.period_start/period_end` if computed server-side |
| Redis `cache_client` (db=0) | Already exists — use for tier cache with `setex`/`get`/`delete` |

---

## 13. Critical Decisions to Carry Into Planning

1. **Migration strategy** for existing users: Two-step migration (add nullable → backfill → add NOT NULL) to avoid downtime.

2. **`tier_id` on `User` with `lazy="selectin"`** — loads Tier automatically with User. Avoids N+1 in API responses that include tier_name.

3. **Stripe webhook path must NOT use auth middleware** — the `/billing/webhook` route must be excluded from `get_current_user` dependency. Use FastAPI `APIRouter` without auth deps for that route.

4. **Raw body preservation** — FastAPI `Request.body()` returns raw bytes. Never call `request.json()` before `stripe.Webhook.construct_event()` or signature verification will fail.

5. **`-1` convention for unlimited tiers** — check `if limit == -1: return` in all usage enforcement logic for the Ultra tier.

6. **Free tier is never soft-deleted** — add guard in `TierService.soft_delete_tier()` that raises `BadRequestError` if `tier.slug == "free"`.

7. **`stripe_price_id` is nullable on Tier** — free tier has no Stripe price. Checkout endpoint must validate tier has a price before creating session.

8. **Webhook idempotency** — handlers must check current state before mutating. On `subscription.deleted`, check user is not already on free tier before downgrading.

9. **UserProfileRead fix** — `tier_name: str = "free"` (Phase 5 D-12 placeholder) must be replaced. Add `tier_slug` and `tier_name` populated from `user.tier` relationship (selectin-loaded).

---

## 14. Environment Variables Required

```bash
# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_SUCCESS_URL=http://localhost:3000/billing/success
STRIPE_CANCEL_URL=http://localhost:3000/billing/cancel
STRIPE_PORTAL_RETURN_URL=http://localhost:3000/account
```

---

## 15. Dependencies to Add

```toml
# pyproject.toml / uv add
stripe = ">=10.0.0"     # Stripe Python SDK v10+ (latest major, includes StripeClient)
```

Stripe Python SDK v10+ supports both legacy `stripe.checkout.Session.create()` (still valid) and the new `StripeClient` pattern. Using legacy static API for simplicity is acceptable — set `stripe.api_key = settings.STRIPE_SECRET_KEY` at app startup.

---

*Research complete — 2026-04-11*
*Next: Create plan documents (06-01 through 06-N)*
