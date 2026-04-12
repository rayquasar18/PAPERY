# Phase 7: Admin Panel (Backend) - Research

**Researched:** 2026-04-12
**Status:** Complete

## 1. Codebase Analysis

### 1.1 Existing Infrastructure to Leverage

**Authentication & Authorization (Ready to Use):**
- `get_current_superuser` dependency in `app/api/dependencies.py` — chains `get_current_user` → `get_current_active_user` → superuser check. Returns 403 with `SUPERUSER_REQUIRED` error code. Ready for router-level `dependencies=[Depends(get_current_superuser)]`.
- JWT access tokens from HttpOnly cookies (not Authorization header) — 30-minute expiry.
- `invalidate_all_user_sessions(user_uuid)` in `app/core/security.py` — invalidates all refresh token families for a user via Redis. This is exactly what ban needs.

**Repository Pattern (Extend):**
- `BaseRepository[ModelType]` in `app/repositories/base.py` — generic async CRUD with `get(**filters)`, `get_multi(skip, limit, **filters)`, `create()`, `update()`, `soft_delete()`, `delete()`. Auto-applies `deleted_at IS NULL`.
- Current repos: `UserRepository`, `TierRepository`, `OAuthAccountRepository`, `UsageTrackingRepository` — all follow same pattern.
- **Gap:** `BaseRepository.get_multi()` does not support: ILIKE search, count for pagination, multi-column sorting, OR-based filters. Admin user search (D-08) needs these — extend at repository level or add a custom method.

**Service Pattern (Reference):**
- Class-based DI: `ServiceClass(db: AsyncSession)` creates internal repos in `__init__`.
- `AuthService` — has `invalidate_all_user_sessions()` import, token family management.
- `TierService` — complete admin CRUD (create, update, soft_delete) + Redis cache integration via `tier_cache.py`.
- `UserService` — handles profile updates, avatar, account deletion.

**Redis Cache Pattern (Replicate):**
- `app/utils/tier_cache.py` — `get_cached_tier_data()`, `set_cached_tier_data()`, `invalidate_tier_cache()` using `redis_client.cache_client` (DB 0) with 5-min TTL and JSON serialization. This pattern should be replicated for settings cache and rate limit rule cache.

**Rate Limiting (Extend):**
- `app/middleware/rate_limit.py` — slowapi `Limiter` for IP-based rate limiting on public endpoints.
- `app/utils/rate_limit.py` — manual `check_rate_limit()` using Redis INCR+EXPIRE for user-UUID-keyed limits. Currently hardcoded `max_requests` and `window_seconds` per call site.
- **Extension needed (D-17):** Add a DB lookup layer: `get_rate_limit_rule(tier_id, endpoint_pattern)` → check Redis cache first → fall back to DB → fall back to hardcoded. Priority: tier-specific > default (tier_id=NULL) > hardcoded.

**Model Patterns (Follow):**
- `Base` with BigInteger PK + `UUIDMixin` + `TimestampMixin` + `SoftDeleteMixin`.
- `Tier` model — JSONB columns for `allowed_models` (list) and `feature_flags` (dict). Reference for `SystemSetting.value` (JSONB).

**Schema Patterns (Follow):**
- Naming: `Read`, `PublicRead`, `Create`, `Update` suffixes.
- `TierPublicRead` (public) vs `TierRead` (admin, includes `stripe_price_id`).
- `ConfigDict(from_attributes=True)` on all Read schemas.
- `model_dump(exclude_unset=True)` for partial updates.

**Router Aggregation:**
- `app/api/v1/__init__.py` — imports individual routers and includes them on `api_v1_router` (prefix `/api/v1`).
- Admin router should be added here as `admin_router` with prefix `/admin` and `dependencies=[Depends(get_current_superuser)]`.

### 1.2 Current User Model State

```python
class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    email: Mapped[str]           # String(320), unique, indexed
    hashed_password: Mapped[str | None]
    display_name: Mapped[str | None]
    avatar_url: Mapped[str | None]
    is_active: Mapped[bool]      # Boolean, default=True — TO BE REPLACED by status enum
    is_verified: Mapped[bool]
    is_superuser: Mapped[bool]
    tier_id: Mapped[int | None]  # FK to tier.id
    stripe_customer_id: Mapped[str | None]
```

**Migration considerations (D-04, D-05):**
- `is_active` column currently a Boolean. Need Alembic migration to:
  1. Add `status` column (String(20), default='active')
  2. Backfill: `is_active=True` → `status='active'`, `is_active=False` → `status='deactivated'`
  3. Keep `is_active` as a hybrid property or remove column (D-05 says keep as `@property`)
  4. Add index on `status` column for admin search filtering

### 1.3 Files That Need Modification

| File | Change |
|------|--------|
| `backend/app/models/user.py` | Add `UserStatus` enum, `status` column, `is_active` property |
| `backend/app/api/v1/__init__.py` | Include admin router |
| `backend/app/api/v1/tiers.py` | Remove admin CRUD endpoints (move to admin/) |
| `backend/app/api/dependencies.py` | Update `get_current_active_user` to use `status` check |
| `backend/app/utils/rate_limit.py` | Extend with DB rule lookup + cache |

### 1.4 New Files Required

| File | Purpose |
|------|---------|
| `backend/app/api/v1/admin/__init__.py` | Admin router aggregator with superuser dependency |
| `backend/app/api/v1/admin/users.py` | Admin user management endpoints |
| `backend/app/api/v1/admin/tiers.py` | Admin tier CRUD (moved from v1/tiers.py) |
| `backend/app/api/v1/admin/rate_limits.py` | Rate limit rule management |
| `backend/app/api/v1/admin/settings.py` | System settings management |
| `backend/app/models/system_setting.py` | SystemSetting model |
| `backend/app/models/rate_limit_rule.py` | RateLimitRule model |
| `backend/app/repositories/system_setting_repository.py` | SystemSetting repo |
| `backend/app/repositories/rate_limit_rule_repository.py` | RateLimitRule repo |
| `backend/app/services/admin_service.py` | Admin business logic (user mgmt, ban + session invalidation) |
| `backend/app/services/settings_service.py` | Settings read/write with cache |
| `backend/app/services/rate_limit_rule_service.py` | Rate limit rule CRUD with cache |
| `backend/app/schemas/admin_user.py` | Admin user schemas |
| `backend/app/schemas/system_setting.py` | System setting schemas |
| `backend/app/schemas/rate_limit_rule.py` | Rate limit rule schemas |
| `backend/app/utils/settings_cache.py` | Redis cache for system settings |
| `backend/app/utils/rate_limit_rule_cache.py` | Redis cache for rate limit rules |
| `migrations/versions/xxx_add_user_status_enum.py` | Alembic migration |
| `migrations/versions/xxx_add_system_settings.py` | Alembic migration |
| `migrations/versions/xxx_add_rate_limit_rules.py` | Alembic migration |
| `scripts/seed_settings.py` | Seed default system settings |
| `scripts/seed_rate_limits.py` | Seed default rate limit rules |

## 2. Technical Approach

### 2.1 Admin Router Architecture

```python
# app/api/v1/admin/__init__.py
from fastapi import APIRouter, Depends
from app.api.dependencies import get_current_superuser

admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_superuser)],  # D-02: router-level auth
)

# Include sub-routers
admin_router.include_router(users_router)
admin_router.include_router(tiers_router)
admin_router.include_router(rate_limits_router)
admin_router.include_router(settings_router)
```

This means every endpoint under `/api/v1/admin/*` automatically requires superuser. No per-endpoint `Depends(get_current_superuser)` needed.

### 2.2 UserStatus Enum Strategy

```python
class UserStatus(str, Enum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    BANNED = "banned"

class User(Base, ...):
    status: Mapped[str] = mapped_column(
        String(20), default=UserStatus.ACTIVE.value, 
        server_default="active", nullable=False, index=True
    )
    
    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE.value
```

**Why `String(20)` not `SQLAlchemy Enum`:** PostgreSQL native ENUMs require `ALTER TYPE` for changes, which is non-trivial in production. String with application-level enum validation is more flexible and follows the existing pattern (tier slugs are strings too).

### 2.3 Admin User Search Implementation (D-08)

`BaseRepository.get_multi()` doesn't support ILIKE or count. Options:

**Chosen approach:** Add a custom `search_users()` method to `UserRepository` that returns `(items, total)`. This follows the principle of keeping domain-specific queries in the repository layer while keeping `BaseRepository` generic.

```python
async def search_users(
    self, *, q: str | None, status: str | None, tier_uuid: UUID | None,
    is_verified: bool | None, is_superuser: bool | None,
    page: int = 1, per_page: int = 20, sort_by: str = "created_at", sort_order: str = "desc"
) -> tuple[list[User], int]:
    # Build dynamic query with ILIKE, filters, pagination
    # Return (items, total_count)
```

### 2.4 Ban + Session Invalidation (D-07)

When admin sets user status to `banned`:
1. Update `user.status = "banned"` in DB
2. Call `invalidate_all_user_sessions(str(user.uuid))` — already exists in `core/security.py`
3. Access tokens expire naturally (30 min TTL)
4. On next login attempt, `get_current_active_user` returns 403 because `is_active` property returns `False`

### 2.5 System Settings Design (D-10 to D-14)

```python
class SystemSetting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "system_setting"
    
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)  # Stores typed value in {"v": ...}
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Allowlist registry (D-12):**
```python
SETTINGS_REGISTRY: dict[str, SettingDefinition] = {
    "maintenance_mode": SettingDefinition(type=bool, category="general", default=False),
    "max_upload_size_mb": SettingDefinition(type=int, category="storage", default=50, min_value=1),
    "allowed_file_types": SettingDefinition(type=list, category="storage", default=["pdf","docx","xlsx","pptx","csv","txt","md"]),
    "default_tier": SettingDefinition(type=str, category="billing", default="free"),
    "signup_enabled": SettingDefinition(type=bool, category="auth", default=True),
}
```

### 2.6 Rate Limit Rule Design (D-15 to D-18)

```python
class RateLimitRule(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "rate_limit_rule"
    
    tier_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("tier.id"), nullable=True, index=True)
    endpoint_pattern: Mapped[str] = mapped_column(String(200), nullable=False)
    max_requests: Mapped[int] = mapped_column(Integer, nullable=False)
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Extension to `check_rate_limit()` (D-17):**
```python
async def get_effective_rate_limit(tier_id: int | None, endpoint: str) -> tuple[int, int]:
    # 1. Check cache: "rate_rule:{tier_id}:{endpoint}"
    # 2. Cache miss → DB lookup: tier-specific rule > default rule (tier_id=NULL) > hardcoded
    # 3. Cache result with 5-min TTL
    # Return (max_requests, window_seconds)
```

### 2.7 Admin Tier CRUD Migration (D-03)

Move POST/PATCH/DELETE from `v1/tiers.py` to `admin/tiers.py`. Keep GET (public listing) in `v1/tiers.py`. Both routers share `TierService` — no logic duplication.

**v1/tiers.py after migration:**
- `GET /tiers` — list active tiers (public)
- `GET /tiers/{uuid}` — get single tier (public)

**admin/tiers.py:**
- `POST /admin/tiers` — create tier
- `PATCH /admin/tiers/{uuid}` — update tier
- `DELETE /admin/tiers/{uuid}` — soft-delete tier

## 3. Dependencies & Ordering

```
Wave 1: Models + Migrations (no API dependencies)
  - UserStatus enum + status column + migration
  - SystemSetting model + migration
  - RateLimitRule model + migration
  
Wave 2: Repositories + Cache Utils (depend on models)
  - SystemSettingRepository
  - RateLimitRuleRepository
  - settings_cache.py
  - rate_limit_rule_cache.py
  - Extend UserRepository with search_users()
  
Wave 3: Services (depend on repositories + cache)
  - AdminService (user management + ban)
  - SettingsService
  - RateLimitRuleService
  - Extend rate_limit.py with DB lookup
  
Wave 4: Routers + Integration (depend on services)
  - admin/__init__.py (router aggregator)
  - admin/users.py
  - admin/tiers.py (move from v1/tiers.py)
  - admin/rate_limits.py
  - admin/settings.py
  - Update v1/__init__.py to include admin router
  - Update v1/tiers.py (remove admin endpoints)
  
Wave 5: Seeds + Tests
  - Seed scripts for settings and rate limits
  - Integration tests
```

## 4. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `is_active` → `status` migration breaks existing code | Medium | High | Keep `@property is_active`, test all auth flows |
| BaseRepository.get_multi inadequate for search | Certain | Low | Custom search_users() method — isolated change |
| Rate limit rule cache stale data | Low | Medium | 5-min TTL + explicit invalidation on admin CRUD |
| SystemSetting JSONB validation edge cases | Low | Low | Allowlist with per-key type validators |
| Admin tier CRUD move breaks existing tests | Low | Medium | Update import paths in tests |

## 5. Validation Architecture

### Test Strategy
- **Unit tests:** Service layer (AdminService, SettingsService, RateLimitRuleService) with mocked repos
- **Integration tests:** Admin endpoints with superuser vs regular user (403), CRUD operations
- **Migration tests:** Verify is_active → status backfill correctness
- **Cache tests:** Verify cache hit/miss/invalidation for settings and rate limit rules

### Key Assertions
- Non-superuser gets 403 on all `/admin/*` endpoints
- Banned user cannot login (refresh token invalidated, access token check fails)
- Tier CRUD via admin/ works, public listing still works via v1/tiers
- System settings only accept allowlisted keys
- Rate limit rules with tier_id override default rules

---

## RESEARCH COMPLETE

*Phase: 07-admin-panel-backend*
*Research completed: 2026-04-12*
