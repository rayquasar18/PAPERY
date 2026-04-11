# Phase 7: Admin Panel (Backend) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 07-admin-panel-backend
**Areas discussed:** Admin route structure, User management scope, System settings model, Rate limit rule management

---

## Admin Route Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Centralized /admin/* | Dedicated admin/ directory with sub-routers, router-level superuser auth | ✓ |
| Distributed (keep in each router) | Admin endpoints in respective routers, per-endpoint dependency | |
| Hybrid: admin/* + public stays | admin/ for admin-only, public stays in original routers | |

**User's choice:** Centralized /admin/* (Recommended)
**Notes:** Matches ADMIN-06 requirement for separate route group

### Follow-up: Public tier listing

| Option | Description | Selected |
|--------|-------------|----------|
| Keep public tiers.py | Public GET stays at v1/tiers.py, admin CRUD moves to admin/tiers.py | ✓ |
| Merge all into admin/tiers.py | Everything under admin/ | |

**User's choice:** Keep public tiers.py (Recommended)

### Follow-up: Admin auth enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| Router-level dependency | `APIRouter(dependencies=[Depends(get_current_superuser)])` | ✓ |
| Custom middleware class | Separate middleware for admin routes | |
| Per-endpoint dependency | Each endpoint declares own dependency | |

**User's choice:** Router-level dependency (Recommended)

---

## User Management Scope

### User account states

| Option | Description | Selected |
|--------|-------------|----------|
| 3 states: active/deactivated/banned | Separate states with different behaviors | ✓ |
| 2 states: active/inactive only | Simple toggle, no ban distinction | |

**User's choice:** 3 states: active/deactivated/banned (Recommended)
**Notes:** User asked about using single field instead of two booleans — discussion led to status enum approach

### Status model implementation

| Option | Description | Selected |
|--------|-------------|----------|
| Status enum + keep is_active compat | New status column, @property is_active for backward compat | ✓ |
| Replace is_active with status (clean break) | Remove is_active, update all code | |

**User's choice:** Status enum + keep is_active compat (Recommended)
**Notes:** User suggested single field approach themselves — aligned with best practice

### Admin user search

| Option | Description | Selected |
|--------|-------------|----------|
| Full search + filter | q, status, tier_uuid, pagination, sort — comprehensive search endpoint | ✓ |
| Basic search only | Email search + list only | |

**User's choice:** Full search + filter (Recommended)
**Notes:** User specified: separate search endpoint from UUID get, admin can GET any user by UUID without ownership check, regular users can only GET their own resources

### Admin user actions

| Option | Description | Selected |
|--------|-------------|----------|
| Separate action endpoints | Each action (status, tier, role) as separate PATCH endpoint | |
| Single PATCH endpoint | One PATCH /admin/users/{uuid} with partial update | ✓ |

**User's choice:** Single PATCH endpoint
**Notes:** User chose simpler approach — "tạm thời dùng chung, chỉ có những đặc thù lắm mới cần separate action"

### Ban session behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Ban = force logout (side effect in PATCH) | Invalidate all refresh token families immediately | ✓ |
| Lazy check on next request | Only block on next request via active check | |

**User's choice:** Ban = force logout (side effect in PATCH)

---

## System Settings Model

### Runtime settings storage

| Option | Description | Selected |
|--------|-------------|----------|
| DB-backed + Redis cache | system_settings table, JSONB values, Redis cache, hot-reload | ✓ |
| Read-only view (env-based) | View-only from Pydantic Settings, no edit via API | |
| Redis-only (no persistence) | Fast but volatile, data lost on restart | |

**User's choice:** DB-backed + Redis cache (Recommended)

### Settings key management

| Option | Description | Selected |
|--------|-------------|----------|
| Allowlist (code-defined keys) | Admin can only edit pre-defined keys, validated per type | ✓ |
| Free-form (any key) | Admin can create any key, hard to validate | |

**User's choice:** Allowlist (code-defined keys) (Recommended)

---

## Rate Limit Rule Management

### Rate limit rules model

| Option | Description | Selected |
|--------|-------------|----------|
| DB table + tier-aware | rate_limit_rule table, tier_id FK, endpoint_pattern, admin CRUD | ✓ |
| Config-only (no DB) | Rules in code/config, admin view-only | |

**User's choice:** DB table + tier-aware (Recommended)

### Rule cache and enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| Redis cache + auto-invalidate | Cache rules in Redis, invalidate on admin CRUD, hot-reload | ✓ |
| Direct DB query per request | Simple but slower per-request DB query | |

**User's choice:** Redis cache + auto-invalidate (Recommended)

### Integration approach (extended discussion)

**User asked:** "Is this standard with slowapi? In SaaS do they do it this way or use slowapi?"

**Analysis provided:**
- slowapi: decorator-based, static limits in code, not tier-aware, requires deploy to change
- Custom Redis: already working, extensible, dynamic rules, hot-reload
- SaaS reality: Stripe, Auth0, Clerk all use custom rate limiting, not slowapi — tier-aware rules need dynamic lookup

**User asked:** "Will adding this manual check slow down requests? How many ms overhead?"

**Performance analysis provided:**
- Rate limit rule cache lookup: ~0.5ms (Redis GET)
- Rate limit counter INCR: ~0.5ms (existing)
- Total overhead: ~1ms — negligible vs business logic (5-500ms)
- Optimization available: Redis pipeline to batch commands

| Option | Description | Selected |
|--------|-------------|----------|
| Custom extend (current approach) | Extend rate_limit.py with DB rules + Redis cache | ✓ |
| slowapi + custom hybrid | slowapi for anti-abuse, custom for tier-aware | |
| slowapi only | Static limits, no tier-aware, simpler | |

**User's choice:** Custom extend — proceed (Recommended)

---

## Claude's Discretion

- Redis TTL durations for settings and rate-limit caches
- Migration strategy details for is_active → status enum conversion
- AdminService internal structure
- system_settings table schema details
- Seed data approach

## Deferred Ideas

None — discussion stayed within phase scope
