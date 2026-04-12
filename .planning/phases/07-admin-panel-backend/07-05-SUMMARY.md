# Plan 07-05 Summary — Seed Scripts & Integration Tests

**Status:** COMPLETE
**Executed:** 2026-04-12
**Tasks:** 4/4 completed
**Commits:** 4 atomic commits

## Tasks Completed

### Task 07-05-01: Create seed script for system settings
- Created `backend/scripts/seed_settings.py` following `seed_tiers.py` pattern
- Bootstraps async context with `init()` / `shutdown()` lifecycle
- Delegates to `SettingsService(session).seed_defaults()` which creates missing settings from `SETTINGS_REGISTRY`
- Idempotent — safe to run multiple times
- **Commit:** `e7fbf90`

### Task 07-05-02: Create seed script for rate limit rules
- Created `backend/scripts/seed_rate_limits.py` with 5 default rate limit rules
- Default rules (tier_id=NULL): `auth:login` (10/60s), `auth:register` (5/60s), `auth:password-reset` (3/300s), `auth:change-password` (5/60s), `documents:upload` (20/60s)
- Idempotent via `repo.find_rule(tier_id=None, endpoint_pattern=...)` check before insertion
- Follows same `init()` / `shutdown()` lifecycle pattern
- **Commit:** `dbd7e83`

### Task 07-05-03: Create integration tests for admin user endpoints
- Created `backend/tests/test_admin_users.py` with 10 test functions across 4 test classes
- `TestAdminUserAuthorization`: 403 for non-superuser, 401 unauthenticated
- `TestAdminListUsers`: paginated response structure (items, total, page, per_page, pages), search by email, filter by status
- `TestAdminGetUser`: user detail with AdminUserRead fields, 404 for nonexistent UUID
- `TestAdminUpdateUser`: ban user (status=banned), deactivate user, 422 for invalid status
- **Commit:** `4cdab56`

### Task 07-05-04: Create integration tests for admin tiers, settings, and rate limits
- Created `backend/tests/test_admin_tiers.py` with 5 tests: 403 guard, create (201), update, delete (204), public listing still works
- Created `backend/tests/test_admin_settings.py` with 6 tests: 403 guard, grouped list, get by key, unknown key (400), update value, invalid type (400)
- Created `backend/tests/test_admin_rate_limits.py` with 6 tests: 403 guard, list rules, create (201), duplicate (409), update, delete (204)
- Smart mock pattern for `TierRepository.get()` using `side_effect` to handle uuid vs name/slug conflict checks
- Proper patch targets (`app.api.v1.admin.settings.SettingsService` instead of service module) to match FastAPI import resolution
- **Commit:** `9eddfe7`

## Verification Results

| Check | Result |
|-------|--------|
| `uv run pytest tests/test_admin_users.py -v` — 10 tests | PASS |
| `uv run pytest tests/test_admin_tiers.py -v` — 5 tests | PASS |
| `uv run pytest tests/test_admin_settings.py -v` — 6 tests | PASS |
| `uv run pytest tests/test_admin_rate_limits.py -v` — 6 tests | PASS |
| All 27 admin tests pass together | PASS |
| `seed_settings.py` contains SettingsService import and seed_defaults() call | PASS |
| `seed_rate_limits.py` contains 5 DEFAULT_RULES with idempotency check | PASS |

## Files Created

| File | Description |
|------|-------------|
| `backend/scripts/seed_settings.py` | Seed script for system settings from SETTINGS_REGISTRY |
| `backend/scripts/seed_rate_limits.py` | Seed script for default rate limit rules |
| `backend/tests/test_admin_users.py` | Integration tests for admin user endpoints (10 tests) |
| `backend/tests/test_admin_tiers.py` | Integration tests for admin tier endpoints (5 tests) |
| `backend/tests/test_admin_settings.py` | Integration tests for admin settings endpoints (6 tests) |
| `backend/tests/test_admin_rate_limits.py` | Integration tests for admin rate limit endpoints (6 tests) |

## Must-Haves Checklist

- [x] `seed_settings.py` creates all 5 default settings from SETTINGS_REGISTRY
- [x] `seed_rate_limits.py` creates default rate limit rules for auth and document endpoints
- [x] Both seed scripts are idempotent (safe to run multiple times)
- [x] Tests verify 403 for non-superuser on all admin endpoints
- [x] Tests verify admin user CRUD including ban + status verification
- [x] Tests verify admin tier CRUD (create 201, update, delete 204) and public tier listing still works
- [x] Tests verify system settings CRUD with allowlist enforcement (unknown key 400, invalid type 400)
- [x] Tests verify rate limit rule CRUD with duplicate detection (409)
