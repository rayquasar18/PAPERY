# Phase 7: Admin Panel (Backend) - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Build admin-only backend endpoints under a centralized `/api/v1/admin/*` route group for: user management (search, view, status changes, ban with session invalidation), tier configuration (CRUD, moved from v1/tiers.py), rate limit rule management (tier-aware DB-backed rules), and runtime system settings (DB-backed key-value with Redis cache). All admin endpoints are superuser-only via router-level dependency.

</domain>

<decisions>
## Implementation Decisions

### Admin Route Structure
- **D-01:** Centralized `/api/v1/admin/*` route group — dedicated `api/v1/admin/` directory with sub-routers: `users.py`, `tiers.py`, `rate_limits.py`, `settings.py`. Satisfies ADMIN-06.
- **D-02:** Router-level superuser auth — `APIRouter(dependencies=[Depends(get_current_superuser)])` on the admin router aggregator. Every endpoint under admin/ automatically requires superuser. No per-endpoint dependency needed.
- **D-03:** Public tier listing stays at `v1/tiers.py` — GET `/tiers` and GET `/tiers/{uuid}` remain public (for pricing page). Admin tier CRUD (POST/PATCH/DELETE) moves to `admin/tiers.py`. No logic duplication — TierService shared.

### User Management
- **D-04:** User status enum replaces is_active boolean — `UserStatus(str, Enum)` with 3 values: `active`, `deactivated`, `banned`. Single `status` column on User model (String(20), indexed). No impossible states, single-field check.
- **D-05:** Backward-compatible `is_active` property — `@property def is_active(self) -> bool: return self.status == UserStatus.ACTIVE`. Existing code using `user.is_active` or `filter(User.is_active == True)` continues to work. Migration backfills status from is_active.
- **D-06:** Single PATCH endpoint for admin user update — `PATCH /admin/users/{uuid}` with partial update schema (status, tier_uuid, is_superuser, is_verified, display_name). Special-case only when truly needed. Simple API surface.
- **D-07:** Ban triggers immediate session invalidation — when status is changed to `banned`, all refresh token families for that user are invalidated in Redis (same mechanism as force-logout). Access tokens expire naturally (30 min). Side effect handled in AdminService.
- **D-08:** Full user search endpoint — `GET /admin/users` with query params: `q` (email/display_name partial match, ILIKE), `status` (enum filter), `tier_uuid` (filter), `is_verified` (bool filter), `is_superuser` (bool filter). Pagination: `page`/`per_page`. Sort: `created_at`, `email`. Response includes `items`, `total`, `page`, `per_page`, `pages`.
- **D-09:** Admin user detail endpoint — `GET /admin/users/{uuid}` returns full user data (including admin-only fields). No ownership check — admin can view any user. Separate from `/users/me` (self-service).

### System Settings
- **D-10:** DB-backed system_settings table — key-value pairs with JSONB value column, category (String), description (Text). Persisted, queryable, auditable.
- **D-11:** Redis cache with TTL — SettingsService reads cache first, falls back to DB. Auto-invalidate cache on PATCH. Hot-reload without restart.
- **D-12:** Allowlist (code-defined) keys — admin can only edit values of pre-defined setting keys. Cannot create new keys via API. Validation per-key (e.g., maintenance_mode must be boolean, max_upload_size_mb must be positive integer). Safe and predictable.
- **D-13:** Initial settings (seed data): `maintenance_mode` (bool, general), `max_upload_size_mb` (int, storage), `allowed_file_types` (array, storage), `default_tier` (string, billing), `signup_enabled` (bool, auth). More can be added in code.
- **D-14:** Admin settings API: GET `/admin/settings` (list all, grouped by category), GET `/admin/settings/{key}` (single), PATCH `/admin/settings/{key}` (update value).

### Rate Limit Rule Management
- **D-15:** DB table `rate_limit_rule` — columns: id, uuid, tier_id (FK nullable), endpoint_pattern (String), max_requests (int), window_seconds (int), description (Text), timestamps, soft delete. tier_id NULL = default rule (all tiers). tier_id set = override for specific tier.
- **D-16:** Redis cache for rule lookup — cache rules per (tier_id, endpoint_pattern) with TTL. Auto-invalidate on admin CRUD. Hot-reload. Overhead ~0.5ms per lookup (Redis GET).
- **D-17:** Extend existing rate_limit.py — add DB/cache rule lookup layer. Priority: tier-specific rule > default rule (tier_id=NULL) > hardcoded fallback. Existing anti-abuse logic stays unchanged. Custom approach, standard SaaS pattern.
- **D-18:** Admin rate-limit API: GET `/admin/rate-limits` (list all rules), POST `/admin/rate-limits` (create), PATCH `/admin/rate-limits/{uuid}` (update), DELETE `/admin/rate-limits/{uuid}` (soft delete).

### Claude's Discretion
- Exact Redis TTL for settings and rate-limit rule cache (suggested 5 min, can adjust)
- Migration strategy for is_active → status enum conversion
- AdminUserUpdate schema exact fields and validation rules
- system_settings table schema details (indexes, constraints)
- Seed data migration approach for default settings and rate limit rules
- AdminService internal structure (single service or split per domain)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture
- `.planning/codebase/ARCHITECTURE.md` — Overall system architecture and layered pattern
- `.planning/codebase/CONVENTIONS.md` — Code conventions and patterns
- `.planning/codebase/STRUCTURE.md` — Target directory layout

### Prior Phase Context (Admin Dependencies)
- `.planning/phases/03-authentication-core-flows/03-CONTEXT.md` — D-03: Redis JTI blacklist, D-04: token family invalidation, D-07: is_superuser flag
- `.planning/phases/05-user-profile-account-management/05-CONTEXT.md` — User profile patterns, UserService
- `.planning/phases/06-tier-system-permissions/06-CONTEXT.md` — D-01~D-05: Tier model, D-14~D-16: rate limit vs usage limit distinction, D-12: Redis tier cache pattern

### Existing Code (Critical)
- `backend/app/api/dependencies.py` — `get_current_superuser` dependency (ready to use), `RequireFeature`, `CheckUsageLimit` patterns
- `backend/app/api/v1/tiers.py` — Existing tier CRUD with superuser protection (admin endpoints to be moved)
- `backend/app/models/user.py` — User model with `is_active`, `is_superuser`, `tier_id`, `stripe_customer_id`
- `backend/app/models/tier.py` — Tier model
- `backend/app/services/tier_service.py` — TierService with admin CRUD methods
- `backend/app/services/user_service.py` — UserService pattern (class-based DI)
- `backend/app/services/auth_service.py` — Token family invalidation logic (needed for ban)
- `backend/app/utils/rate_limit.py` — Current Redis INCR+EXPIRE rate limiting (to be extended)
- `backend/app/utils/tier_cache.py` — Redis cache pattern for tier data (reference for settings/rate-limit cache)
- `backend/app/repositories/base.py` — BaseRepository with get/get_multi/delete generic methods
- `backend/app/models/base.py` — Base model with UUIDMixin, TimestampMixin, SoftDeleteMixin

### Requirements
- `.planning/REQUIREMENTS.md` — ADMIN-01 through ADMIN-06 requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `get_current_superuser` dependency — ready to use as router-level dependency for admin group
- `BaseRepository[ModelType]` — extend for RateLimitRuleRepository, SystemSettingRepository
- `TierService` — already has admin CRUD methods, shared between public and admin routers
- `UserService` / `AuthService` — patterns for AdminService, session invalidation logic
- `tier_cache.py` — Redis cache with invalidation pattern, reference for settings and rate-limit rule caching
- `PaperyHTTPException` subclasses — reuse for admin-specific errors

### Established Patterns
- **Layered architecture:** Router → Dependencies → Service → Repository → Model
- **Schema separation:** Read, ReadInternal, Create, Update variants
- **Dual ID:** int id (internal) + UUID (public API) — apply to SystemSetting and RateLimitRule
- **Soft delete:** SoftDeleteMixin on all core entities
- **Redis cache:** cache namespace (DB 0) with TTL + explicit invalidation
- **Class-based services:** Constructor DI pattern — `ServiceClass(db)`

### Integration Points
- `User.status` column — replaces `is_active` boolean, needs Alembic migration + backfill
- `v1/tiers.py` — admin CRUD endpoints move to `admin/tiers.py`, public endpoints stay
- `rate_limit.py` — extend with DB rule lookup + cache layer
- `main.py` — mount admin_router alongside existing routers
- `models/__init__.py` — register SystemSetting and RateLimitRule for Alembic

</code_context>

<specifics>
## Specific Ideas

- User explicitly chose single PATCH endpoint for admin user updates rather than separate action endpoints — simpler API surface, separate only truly special-case actions
- Rate limiting extends existing custom Redis-based approach — not slowapi. Standard SaaS pattern used by Stripe, Auth0, etc.
- is_active → status enum is a backward-compatible migration: keep `@property is_active` so existing code works
- System settings use allowlist approach — admin cannot create arbitrary keys, only edit predefined ones with validation per key type

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-admin-panel-backend*
*Context gathered: 2026-04-11*
