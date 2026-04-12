# Plan 07-01 Summary — Admin Models & User Status Migration

**Status:** COMPLETE
**Executed:** 2026-04-12
**Tasks:** 4/4 completed
**Commits:** 4 atomic commits

## Tasks Completed

### Task 07-01-01: Add UserStatus enum and migrate User model from is_active to status
- Added `UserStatus(str, Enum)` with `ACTIVE`, `DEACTIVATED`, `BANNED` values to `backend/app/models/user.py`
- Replaced `is_active: Mapped[bool]` column with `status: Mapped[str] = mapped_column(String(20), ...)` with `server_default="active"` and `index=True`
- Added backward-compatible `@property is_active` returning `self.status == UserStatus.ACTIVE.value`
- Updated `UserRepository.create_user()` parameter from `is_active: bool` to `status: str`
- Updated `UserService.delete_account()` to set `user.status = UserStatus.DEACTIVATED.value`
- Updated `get_current_active_user()` to distinguish `ACCOUNT_BANNED` vs `ACCOUNT_INACTIVE` errors
- Updated all three `create_user()` calls in `AuthService` (register, superuser bootstrap, OAuth) to use `status=UserStatus.ACTIVE.value`
- **Commit:** `54bfd49`

### Task 07-01-02: Create SystemSetting model
- Created `backend/app/models/system_setting.py` with `SystemSetting(Base, UUIDMixin, TimestampMixin)`
- Key (String(100), unique, indexed), value (JSONB), category (String(50), indexed), description (Text, nullable)
- No SoftDeleteMixin — settings are never deleted, only updated
- **Commit:** `7a9fafe`

### Task 07-01-03: Create RateLimitRule model
- Created `backend/app/models/rate_limit_rule.py` with `RateLimitRule(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin)`
- tier_id (BigInteger FK to tier.id, nullable, CASCADE), endpoint_pattern (String(200), indexed), max_requests, window_seconds, description
- UniqueConstraint on (tier_id, endpoint_pattern) named `uq_rate_limit_tier_endpoint`
- Tier relationship with `lazy="selectin"`
- **Commit:** `e817367`

### Task 07-01-04: Register new models in barrel import and generate Alembic migration
- Added `RateLimitRule` and `SystemSetting` imports to `backend/app/models/__init__.py` and `__all__`
- Generated Alembic migration `02136906e804` with autogenerate
- Edited migration to include data backfill: `UPDATE "user" SET status = CASE WHEN is_active = true THEN 'active' ELSE 'deactivated' END`
- Downgrade includes reverse backfill from status to is_active
- Migration also captured tier, usage_tracking tables (from previous phases not yet migrated)
- `alembic upgrade head` completed successfully
- `alembic check` confirms no pending changes
- **Commit:** `a2e1036`

## Verification Results

| Check | Result |
|-------|--------|
| `alembic check` — no pending changes | PASS |
| `from app.models import SystemSetting, RateLimitRule` | PASS |
| `UserStatus.BANNED.value == "banned"` | PASS |
| DB has `system_setting` table | PASS |
| DB has `rate_limit_rule` table | PASS |
| User table has `status` column | PASS |
| User table does NOT have `is_active` column | PASS |

## Files Modified

| File | Change |
|------|--------|
| `backend/app/models/user.py` | Added UserStatus enum, replaced is_active with status, added @property is_active |
| `backend/app/models/system_setting.py` | NEW — SystemSetting model |
| `backend/app/models/rate_limit_rule.py` | NEW — RateLimitRule model |
| `backend/app/models/__init__.py` | Registered SystemSetting and RateLimitRule |
| `backend/app/repositories/user_repository.py` | Updated create_user() parameter |
| `backend/app/services/user_service.py` | Updated delete_account() to use UserStatus |
| `backend/app/services/auth_service.py` | Updated all create_user() calls to use status param |
| `backend/app/api/dependencies.py` | Added ACCOUNT_BANNED vs ACCOUNT_INACTIVE distinction |
| `backend/migrations/versions/2026_04_12_...py` | NEW — Migration with backfill |

## Must-Haves Checklist

- [x] `UserStatus` enum with `active`, `deactivated`, `banned` values exists in `models/user.py`
- [x] User model has `status` String(20) column (not `is_active` boolean)
- [x] `@property is_active` on User returns `self.status == "active"` for backward compatibility
- [x] `SystemSetting` model with key (unique), value (JSONB), category, description columns
- [x] `RateLimitRule` model with tier_id (FK nullable), endpoint_pattern, max_requests, window_seconds
- [x] Both new models registered in `models/__init__.py`
- [x] Alembic migration applied successfully with backfill from is_active to status
- [x] `get_current_active_user` returns distinct errors for ACCOUNT_BANNED vs ACCOUNT_INACTIVE
- [x] All `create_user()` calls updated to use `status=` parameter instead of `is_active=`
