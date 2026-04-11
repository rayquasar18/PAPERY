# Plan 06-02 Execution Summary

**Plan:** 06-02 — User Model FK, Repositories, Tier Schemas, Registration Update
**Status:** COMPLETE
**Date:** 2026-04-11
**Branch:** develop
**Commits:** 5 atomic commits pushed to origin/develop

---

## Tasks Completed

### Task 1 — Add tier_id FK and stripe_customer_id to User model
**File:** `backend/app/models/user.py`
**Commit:** `66d6350`

- Added `tier_id: Mapped[int | None]` with `ForeignKey("tier.id", ondelete="RESTRICT")`, `index=True`, nullable for migration-safe two-step pattern
- Added `stripe_customer_id: Mapped[str | None]` with `String(255)`, nullable, unique
- Added `tier: Mapped["Tier"] = relationship("Tier", lazy="selectin")` — string reference avoids circular import; selectin loading prevents N+1

### Task 2 — Create TierRepository
**File:** `backend/app/repositories/tier_repository.py` (NEW)
**Commit:** `d078a9a`

- `TierRepository(BaseRepository[Tier])` — no custom methods (YAGNI)
- All lookups via inherited `get(slug="free")`, `get_multi()`, etc.

### Task 3 — Create UsageTrackingRepository with upsert and period query
**File:** `backend/app/repositories/usage_tracking_repository.py` (NEW)
**Commit:** `09098b6`

- `_current_period_boundaries()` — computes UTC month start/end with Dec→Jan rollover handling
- `get_current_period_count(user_id, metric)` — returns `int` (0 when no record), never `None`
- `increment_usage(user_id, metric)` — PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` atomic upsert via `pg_insert`, returns new count

### Task 4 — Create Tier Pydantic schemas
**File:** `backend/app/schemas/tier.py` (NEW)
**Commit:** `414b1e3`

- `TierPublicRead` — safe for all users (no `stripe_price_id`)
- `TierRead(TierPublicRead)` — adds `stripe_price_id` for admin use
- `TierCreate` — validates slug with `^[a-z0-9\-]+$`, `ge=-1` for unlimited convention
- `TierUpdate` — all fields optional for PATCH semantics

### Task 5 — Update UserProfileRead to use real tier data
**Files:** `backend/app/schemas/user.py`, `backend/app/services/user_service.py`
**Commit:** `6e532d7`

- Removed `tier_name: str = "free"` placeholder; replaced with `tier_name: str` + `tier_slug: str` (no defaults)
- `UserService.get_profile` now populates from `user.tier` relationship with graceful fallback for nullable transition period

### Task 6 — Update registration flows to auto-assign free tier
**Files:** `backend/app/repositories/user_repository.py`, `backend/app/services/auth_service.py`
**Commit:** `817954a`

- `UserRepository.create_user` accepts `tier_id: int | None = None`
- `AuthService.__init__` creates `self._tier_repo: TierRepository`
- `AuthService._get_free_tier_id()` — resolves free tier, raises `RuntimeError` if not seeded
- `register_user` — calls `_get_free_tier_id()` before creating user
- `create_first_superuser` — calls `_get_free_tier_id()` before creating admin
- `oauth_login_or_register` — instantiates `TierRepository(db)`, resolves free tier, passes `tier_id=free_tier.id`

---

## Files Modified

| File | Status |
|------|--------|
| `backend/app/models/user.py` | Modified — tier_id FK + stripe_customer_id + tier relationship |
| `backend/app/repositories/tier_repository.py` | Created |
| `backend/app/repositories/usage_tracking_repository.py` | Created |
| `backend/app/schemas/tier.py` | Created |
| `backend/app/schemas/user.py` | Modified — tier_name/tier_slug without defaults |
| `backend/app/services/user_service.py` | Modified — real tier data in get_profile |
| `backend/app/repositories/user_repository.py` | Modified — tier_id param in create_user |
| `backend/app/services/auth_service.py` | Modified — TierRepository, _get_free_tier_id, tier_id on all reg flows |

---

## Security Notes

- `tier_id` is never accepted from user input — set server-side only via `_get_free_tier_id()`
- `stripe_customer_id` excluded from `UserProfileRead` (only in internal use)
- `ondelete="RESTRICT"` prevents accidental tier deletion when users reference it

---

## Verification Results

All acceptance criteria passed:
- ✅ `tier_id` FK with `ondelete="RESTRICT"` in User model
- ✅ `stripe_customer_id` nullable unique column in User model
- ✅ `tier` relationship with `lazy="selectin"` in User model
- ✅ No direct `from app.models.tier import Tier` in user.py (string reference used)
- ✅ `TierRepository(BaseRepository[Tier])` created
- ✅ `UsageTrackingRepository` with `increment_usage` + `get_current_period_count`
- ✅ PostgreSQL upsert via `on_conflict_do_update(constraint="uq_usage_user_metric_period")`
- ✅ All 4 Tier schemas created (`TierPublicRead`, `TierRead`, `TierCreate`, `TierUpdate`)
- ✅ `UserProfileRead` has `tier_name: str` and `tier_slug: str` without hardcoded defaults
- ✅ `UserService.get_profile` reads from `user.tier` relationship
- ✅ `create_user` accepts `tier_id` parameter
- ✅ `_get_free_tier_id()` helper in `AuthService`
- ✅ `register_user`, `create_first_superuser`, `oauth_login_or_register` all assign free tier
