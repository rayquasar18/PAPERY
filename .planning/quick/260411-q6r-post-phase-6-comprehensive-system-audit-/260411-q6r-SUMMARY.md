# Quick Task 260411-q6r: Post-Phase-6 Comprehensive System Audit — Summary

**Completed:** 2026-04-11
**Commits:** e2b3789, f2b089c, 6197708, a4b3a2a
**Files changed:** 12 files (+440, -233)

---

## Issues Found & Fixed

### 1. Billing schemas in wrong location (FIXED)
**Problem:** `CheckoutRequest`, `CheckoutResponse`, `PortalResponse` were defined inline in `api/v1/billing.py` instead of `schemas/billing.py`.
**Fix:** Created `schemas/billing.py` with all billing schemas. Added new `SubscriptionStatusResponse` to type the `/subscription` endpoint (was returning untyped `dict`).

### 2. Inconsistent auth service patterns (FIXED)
**Problem:** Auth router mixed class-based `AuthService(db)` with module-level function calls (`auth_service.oauth_login_or_register()`, `auth_service.change_password()`, `auth_service.set_password()`).
**Fix:** Added `oauth_login_or_register`, `change_password`, `set_password` as class methods on `AuthService`. Updated auth router to use class-based pattern exclusively. Module-level functions kept as deprecated wrappers for backward compatibility.

### 3. Rate limiting architecture (IMPROVED)
**Problem:** Custom Redis INCR+EXPIRE rate limiting instead of using the standard `slowapi` library.
**Fix:** Installed `slowapi` with Redis backend. Replaced 7 IP-based rate limits in auth routes with `@limiter.limit()` decorators. Kept manual `check_rate_limit()` for user-UUID-based limits (cleaner DI integration). Hybrid approach: slowapi for public endpoints, manual for authenticated.

### 4. Stripe SDK deprecations (FIXED)
**Problem:** Used deprecated `stripe.error.SignatureVerificationError` and `stripe.error.StripeError` (pre-v6 paths). Also set `stripe.api_key` globally on every service instantiation (redundant).
**Fix:** Updated to `stripe.SignatureVerificationError` and `stripe.StripeError`. Moved API key initialization to module-level (set once at import time).

---

## Architecture After Audit

- All schemas in `schemas/` directory ✅
- All service calls use class-based pattern ✅
- Rate limiting: slowapi (IP) + Redis manual (user UUID) ✅
- Stripe SDK: modern exception paths, module-level config ✅
- All endpoints have typed response_model ✅
