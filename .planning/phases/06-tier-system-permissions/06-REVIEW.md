---
status: issues_found
phase: "06"
depth: standard
files_reviewed: 24
findings:
  critical: 4
  warning: 9
  info: 6
  total: 19
---

# Code Review: Phase 06 — Tier System & Permissions

## Summary

The tier system and billing integration are well-structured overall, with clean separation of concerns across models, repositories, services, and routes. However, four critical security issues were found — most notably an empty STRIPE_WEBHOOK_SECRET that permits unauthenticated webhook processing in non-production environments, a user UUID passed as a raw string (not UUID object) to the repository causing a potential query miss, a race condition in usage enforcement, and a silent tier escalation path via `checkout.session.completed`.

---

## Findings

### CR-001: Webhook signature bypassed when STRIPE_WEBHOOK_SECRET is empty string

- **Severity:** critical
- **File:** `backend/app/api/v1/billing.py`
- **Line:** 117–127
- **Issue:** `stripe.Webhook.construct_event()` is called with `secret=settings.STRIPE_WEBHOOK_SECRET`. In non-production environments (local, staging), `STRIPE_WEBHOOK_SECRET` defaults to `""` (empty string per `configs/stripe.py` line 16). The Stripe library does **not** raise `SignatureVerificationError` when the secret is empty — it may silently accept the `sig_header` or skip validation depending on library version. This means any attacker who can reach `/api/v1/billing/webhook` can POST a crafted payload to trigger arbitrary tier upgrades without a valid Stripe signature. The `validate_startup` guard only enforces `STRIPE_WEBHOOK_SECRET` in `production`; `staging` is left exposed.
- **Fix:** Add a guard at the top of the webhook handler: if `not settings.STRIPE_WEBHOOK_SECRET`, return a 503 or raise `HTTPException(status_code=503, detail="Webhook not configured")`. Also extend `validate_startup` to require `STRIPE_WEBHOOK_SECRET` in `staging` as well as `production`.

---

### CR-002: UUID passed as string to UserRepository.get() in handle_checkout_completed

- **Severity:** critical
- **File:** `backend/app/services/stripe_service.py`
- **Line:** 175
- **Issue:** `user_uuid` is extracted from Stripe metadata as a raw string (`str`). It is passed directly to `self._user_repo.get(uuid=user_uuid)` without converting to a `uuid.UUID` object. The `BaseRepository.get()` method uses SQLAlchemy equality comparison `where(User.uuid == user_uuid)`. If the SQLAlchemy dialect does not auto-cast a string to UUID for the PostgreSQL `uuid` column, the query returns `None`, causing the webhook handler to silently log an error and skip the tier upgrade. Additionally, there is no validation that `user_uuid` is a well-formed UUID string — a corrupted metadata value would cause an unhandled exception.
- **Fix:** Wrap the lookup with `uuid_pkg.UUID(user_uuid)` and catch `ValueError` for malformed UUIDs. Example: `user = await self._user_repo.get(uuid=uuid_pkg.UUID(user_uuid))`.

---

### CR-003: Race condition in enforce_limit — TOCTOU between check and increment

- **Severity:** critical
- **File:** `backend/app/services/usage_service.py`
- **Line:** 56–84 (enforce_limit) + line 86–92 (increment_usage)
- **Issue:** `enforce_limit` reads the current count, and if it is below the limit, returns without holding any lock. `increment_usage` then atomically increments via `INSERT ... ON CONFLICT DO UPDATE`. Between the `get_current_period_count` SELECT and the subsequent `increment_usage` call (which is made by the caller after the business action succeeds), concurrent requests from the same user can both pass `enforce_limit`, both perform the action, and both call `increment_usage` — resulting in the user exceeding their quota. This is a classic TOCTOU (time-of-check / time-of-use) race condition. At high concurrency, a user on the Free tier (limit=3 projects) could create 4 or more projects simultaneously.
- **Fix:** The atomic increment should return the new count, and the caller should verify `new_count <= limit` inside the same atomic operation. Alternatively, change `increment_usage` to enforce the limit in-database using a conditional `DO UPDATE ... WHERE count < limit` or a `CHECK` constraint approach.

---

### CR-004: Tier escalation without payment verification in handle_checkout_completed

- **Severity:** critical
- **File:** `backend/app/services/stripe_service.py`
- **Line:** 162–198
- **Issue:** `handle_checkout_completed` trusts `tier_slug` from `session["metadata"]["tier_slug"]` to determine which tier to assign. However, `checkout.session.completed` fires even when the checkout mode is not `subscription`, and the metadata could have been set by anyone who crafted the session (e.g., via the Stripe Dashboard or a compromised integration). There is no verification that the event's `payment_status` is `"paid"` or that `mode` is `"subscription"` before promoting the user's tier. An attacker with access to the Stripe webhook endpoint (see CR-001) or a misconfigured Stripe product with `payment_status: "unpaid"` could elevate a user to a paid tier without actual payment.
- **Fix:** Add guards: `if session_obj.get("payment_status") != "paid": return` and `if session_obj.get("mode") != "subscription": return` before processing the tier upgrade.

---

### WR-001: stripe.api_key set per-instance — thread safety risk at high concurrency

- **Severity:** warning
- **File:** `backend/app/services/stripe_service.py`
- **Line:** 46
- **Issue:** `stripe.api_key = settings.STRIPE_SECRET_KEY` modifies the global `stripe` module state on every `StripeService` instantiation. While the value is constant across instances, this pattern is not thread-safe and can cause subtle bugs if different Stripe API keys are ever used (e.g., test vs live key switching). Every request instantiates a new `StripeService`, creating redundant global writes.
- **Fix:** Set `stripe.api_key` once at application startup (e.g., in `lifespan` or module-level in `stripe_service.py`) rather than in `__init__`. Or, adopt the `stripe.StripeClient` pattern for explicit client scoping.

---

### WR-002: Stripe Checkout session URL may be None — unguarded return

- **Severity:** warning
- **File:** `backend/app/services/stripe_service.py`
- **Line:** 102
- **Issue:** `session.url` is returned directly without a None-check. `stripe.checkout.Session.create()` can return a session where `url` is `None` (e.g., when `after_expiration` recovery is enabled or in certain embedded UIs). The function signature declares `-> str`, but could return `None`, which would cause a runtime error downstream in the billing router at `CheckoutResponse(checkout_url=url)`.
- **Fix:** Add: `if not session.url: raise BadRequestError(detail="Stripe did not return a checkout URL", error_code="STRIPE_NO_URL")`.

---

### WR-003: UsageTracking has no primary key — Alembic migration will fail

- **Severity:** warning
- **File:** `backend/app/models/usage_tracking.py`
- **Line:** 13–37
- **Issue:** `UsageTracking` inherits from `Base` and `TimestampMixin` only — it does NOT inherit `UUIDMixin` or define a primary key column (`id`). SQLAlchemy ORM requires every mapped class to have a primary key. Without one, `alembic revision --autogenerate` will fail or produce a broken migration, and SQLAlchemy will raise a `SAWarning` or `ArgumentError` at startup.
- **Fix:** Add a primary key, either by inheriting `UUIDMixin` (consistent with other models) or by adding `id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)`.

---

### WR-004: update_tier does not invalidate Redis tier cache after update

- **Severity:** warning
- **File:** `backend/app/services/tier_service.py`
- **Line:** 148–176
- **Issue:** `update_tier` modifies tier data in the database but never calls `invalidate_tier_cache`. Since tier data is cached per-user for 5 minutes (TTL=300s), all users on the updated tier will continue operating with stale limits and feature flags for up to 5 minutes after an admin changes the tier configuration. The same gap exists for `create_tier` (less critical, but still inconsistent).
- **Fix:** After `await self._tier_repo.update(tier)`, broadcast a cache invalidation. Because multiple users may share a tier, either: (1) invalidate by a `tier:<slug>:*` wildcard scan, or (2) accept the TTL lag (document it as an intentional design decision), or (3) use a short enough TTL. At minimum, document the known staleness window.

---

### WR-005: soft_delete_tier does not check for existing users on the tier

- **Severity:** warning
- **File:** `backend/app/services/tier_service.py`
- **Line:** 178–184
- **Issue:** `soft_delete_tier` soft-deletes a tier without checking if any active users still have `tier_id` pointing to it. The database FK is `ondelete="RESTRICT"` which would prevent a hard delete, but soft delete just sets `deleted_at` on the tier row and commits — the FK constraint is not triggered. Users on the deleted tier now reference a soft-deleted tier. The `get_user_tier_data` cache miss path (`user.tier`) will still load the deleted tier because `BaseRepository.get()` filters `deleted_at IS NULL` only for the primary model, not loaded relationships.
- **Fix:** Before soft-deleting, verify no active users reference the tier: query `User` count where `tier_id == tier.id AND deleted_at IS NULL`. If any exist, raise `BadRequestError`.

---

### WR-006: _resolve_tier_data in UsageService duplicates TierService logic — double cache read

- **Severity:** warning
- **File:** `backend/app/services/usage_service.py`
- **Line:** 46–54
- **Issue:** `UsageService._resolve_tier_data` reads from the cache, and if missed, calls `TierService.get_user_tier_data` — which *also* reads from the cache internally (lines 85–87 of `tier_service.py`). This results in two redundant Redis `GET` calls on cache miss before the DB read. Additionally, `UsageService` calls `set_cached_tier_data` *again* after `TierService` has already set it, which is a harmless but confusing double-write.
- **Fix:** Remove the cache read/write from `UsageService._resolve_tier_data` and simply delegate directly to `TierService.get_user_tier_data`, which already handles caching internally.

---

### WR-007: checkout endpoint allows a user to initiate checkout for their current tier

- **Severity:** warning
- **File:** `backend/app/api/v1/billing.py`
- **Line:** 52–67
- **Issue:** `create_checkout` does not verify that the requested `tier_slug` differs from the user's current tier, and does not prevent a free-tier user from creating a checkout for the free tier (which has `stripe_price_id=None`). The `BadRequestError` in `StripeService.create_checkout_session` catches the free tier case, but the user is allowed to create Stripe Checkout sessions for the tier they are already subscribed to — resulting in duplicate subscriptions in Stripe.
- **Fix:** Add a guard: `if user.tier and user.tier.slug == data.tier_slug: raise BadRequestError(detail="You are already on this plan.")`.

---

### WR-008: STRIPE_WEBHOOK_SECRET validation only in production, not staging

- **Severity:** warning
- **File:** `backend/app/configs/__init__.py`
- **Line:** 55–57
- **Issue:** The `validate_startup` validator only enforces `STRIPE_WEBHOOK_SECRET` in `production`. In `staging` environments — which are typically used for pre-release testing with real Stripe test-mode webhooks — the secret is not validated. A developer misconfiguring staging will silently run without webhook authentication (compounding CR-001).
- **Fix:** Change condition to `if self.ENVIRONMENT in ("production", "staging")`.

---

### WR-009: UsageService.get_usage_summary makes N+1 queries for metrics

- **Severity:** warning
- **File:** `backend/app/services/usage_service.py`
- **Line:** 98–119
- **Issue:** `get_usage_summary` iterates over `METRIC_TO_LIMIT_KEY` (3 metrics) and calls `get_current_period_count` for each — issuing 3 separate SELECT queries per call. Combined with the tier data resolution (potentially 1 more query), this is 4 DB round-trips for a single endpoint.
- **Fix:** Add a batch method to `UsageTrackingRepository` that fetches all metrics for a user in one query: `WHERE user_id = ? AND period_start = ? AND metric IN (?)`.

---

### IR-001: TierCreate/TierUpdate allow setting stripe_price_id to any arbitrary string

- **Severity:** info
- **File:** `backend/app/schemas/tier.py`
- **Line:** 45, 60
- **Issue:** `stripe_price_id` in `TierCreate` and `TierUpdate` has no format validation. An admin could accidentally set it to a non-Stripe price ID string (e.g., a UUID, a slug, or a live key when the app is in test mode). There is no `pattern` validator to enforce the `price_*` prefix.
- **Fix:** Add `pattern=r"^price_[A-Za-z0-9]+$"` validator on `stripe_price_id` fields, with `None` still allowed.

---

### IR-002: get_tier_by_uuid has untyped parameter — missing type hint

- **Severity:** info
- **File:** `backend/app/services/tier_service.py`
- **Line:** 54
- **Issue:** `async def get_tier_by_uuid(self, tier_uuid)` is missing a type annotation for `tier_uuid`. All other methods in the codebase have full type hints. `mypy` with `warn_return_any = true` will flag this.
- **Fix:** Change signature to `async def get_tier_by_uuid(self, tier_uuid: uuid_pkg.UUID) -> Tier:` and add `import uuid as uuid_pkg` at the top of the file.

---

### IR-003: ADMIN_PASSWORD in .env.example is a weak placeholder that could be committed

- **Severity:** info
- **File:** `backend/.env.example`
- **Line:** 57
- **Issue:** `ADMIN_PASSWORD=admin-dev-password-change-me` is a predictable placeholder. The `validate_startup` validator checks `POSTGRES_PASSWORD`, `MINIO_SECRET_KEY`, and `SECRET_KEY` for weak values in non-local environments — but does **not** check `ADMIN_PASSWORD`. A misconfigured staging deployment would bootstrap an admin account with a guessable password.
- **Fix:** Add `ADMIN_PASSWORD` to the `validate_startup` checks for non-local environments: `if self.ADMIN_PASSWORD in ("admin-dev-password-change-me", ""): raise ValueError(...)`.

---

### IR-004: seed_tiers.py does not filter soft-deleted tiers during existence check

- **Severity:** info
- **File:** `backend/scripts/seed_tiers.py`
- **Line:** 75–78
- **Issue:** The seed script checks `select(Tier).where(Tier.slug == tier_data["slug"])` without filtering `deleted_at IS NULL`. If a tier was previously soft-deleted, the script will find it and skip the re-seed. The application would then have no active free tier, causing `AuthService._get_free_tier_id()` to raise `RuntimeError` on every registration attempt.
- **Fix:** Add `.where(Tier.deleted_at.is_(None))` to the seed's existence check query.

---

### IR-005: UsageTracking model uses Integer for count — may overflow at scale

- **Severity:** info
- **File:** `backend/app/models/usage_tracking.py`
- **Line:** 30
- **Issue:** `count: Mapped[int] = mapped_column(Integer, ...)` uses a 32-bit `Integer` column. For high-usage metrics (e.g., a "fixes" counter in the future with API call tracking), this limits the count to ~2.1 billion. Other ID columns in the project use `BigInteger`.
- **Fix:** Consider changing `count` to `BigInteger` for consistency and future-proofing. Low-risk change with minimal impact.

---

### IR-006: Stripe Subscription list uses status="active" only — misses trialing subscriptions

- **Severity:** info
- **File:** `backend/app/services/stripe_service.py`
- **Line:** 143–144
- **Issue:** `stripe.Subscription.list(customer=..., status="active", limit=1)` only fetches subscriptions with `status="active"`. New subscriptions frequently start in `status="trialing"` (if a trial period is configured). A user who just completed checkout and has a trialing subscription would see `subscription_status: "none"` in `get_subscription_status`, causing confusion.
- **Fix:** Pass `status="all"` or use two calls, or filter in post-processing for `status in ("active", "trialing")`. Alternatively, document that trials are not supported.

---

## Files Reviewed

| File | Status |
|------|--------|
| `backend/app/models/tier.py` | ✅ Pass |
| `backend/app/models/usage_tracking.py` | ❌ Issues (WR-003) |
| `backend/app/models/__init__.py` | ✅ Pass |
| `backend/app/models/user.py` | ✅ Pass |
| `backend/app/configs/stripe.py` | ❌ Issues (CR-001, WR-008) |
| `backend/app/configs/__init__.py` | ❌ Issues (WR-008, IR-003) |
| `backend/app/repositories/tier_repository.py` | ✅ Pass |
| `backend/app/repositories/usage_tracking_repository.py` | ✅ Pass |
| `backend/app/repositories/user_repository.py` | ✅ Pass |
| `backend/app/schemas/tier.py` | ❌ Issues (IR-001) |
| `backend/app/schemas/user.py` | ✅ Pass |
| `backend/app/services/auth_service.py` | ✅ Pass |
| `backend/app/services/tier_service.py` | ❌ Issues (WR-004, WR-005, IR-002) |
| `backend/app/services/usage_service.py` | ❌ Issues (CR-003, WR-006, WR-009) |
| `backend/app/services/stripe_service.py` | ❌ Issues (CR-001, CR-002, CR-004, WR-001, WR-002, IR-006) |
| `backend/app/services/user_service.py` | ✅ Pass |
| `backend/app/utils/tier_cache.py` | ✅ Pass |
| `backend/app/api/dependencies.py` | ✅ Pass |
| `backend/app/api/v1/tiers.py` | ✅ Pass |
| `backend/app/api/v1/billing.py` | ❌ Issues (CR-001, WR-007) |
| `backend/app/api/v1/__init__.py` | ✅ Pass |
| `backend/scripts/seed_tiers.py` | ❌ Issues (IR-004) |
| `backend/.env.example` | ❌ Issues (IR-003) |
| `backend/pyproject.toml` | ✅ Pass |
