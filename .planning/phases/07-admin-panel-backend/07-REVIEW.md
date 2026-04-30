---
status: issues_found
phase: 07-admin-panel-backend
depth: standard
files_reviewed: 33
findings:
  critical: 2
  warning: 8
  info: 5
  total: 15
---

# Code Review: Phase 07 — Admin Panel Backend

## Summary

Phase 07 is well-structured overall: the admin router-level `get_current_superuser` guard is correctly applied, service/repository separation is clean, and cache invalidation on write paths is consistent. However, two critical issues exist — a partial cache miss in the dynamic rate-limit lookup that can silently serve stale defaults, and an ILIKE search on `q` that is vulnerable to regex-injection via unescaped `%` and `_` wildcards. Several warnings cover data integrity gaps, missing guards, and test coverage blind spots.

---

## Findings

### CR-1 — ILIKE wildcard injection in user search

**File:** `backend/app/repositories/user_repository.py:117`  
**Severity:** critical  
**Description:**  
The search query `q` is interpolated directly into an ILIKE pattern with only a surrounding `%`:

```python
pattern = f"%{q}%"
search_filter = or_(
    User.email.ilike(pattern),
    User.display_name.ilike(pattern),
)
```

A caller who passes a value like `q="%"` or `q="___"` can trivially turn the query into a full-table scan or enumerate users via blind pattern matching. Although this is an admin-only endpoint, a compromised superuser session or a future mistake that widens access could be exploited. PostgreSQL ILIKE treats `%` and `_` as wildcards — an unescaped input string that contains these characters produces unintended behavior.  
**Fix:** Escape `%`, `_`, and `\` in `q` before embedding it in the pattern:
```python
escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
pattern = f"%{escaped}%"
# and pass escape="\\" to ilike()
```

---

### CR-2 — Cache miss path in `check_rate_limit_dynamic` skips DB lookup

**File:** `backend/app/utils/rate_limit.py:69-117`  
**Severity:** critical  
**Description:**  
`check_rate_limit_dynamic` only reads from the Redis cache. When the cache is cold (miss), it falls through to the hardcoded `fallback_max_requests`/`fallback_window_seconds` values — it never queries the database. Contrast this with `RateLimitRuleService.get_effective_rule()` which performs the correct cache → DB → fallback flow. Callers of `check_rate_limit_dynamic` will silently use the hardcoded fallback (60 req/min by default) on any Redis cache miss, effectively ignoring DB-configured admin rules until the cache is warm.  
**Fix:** Either call `RateLimitRuleService.get_effective_rule()` (which handles the DB fallback), or add a DB query path to `check_rate_limit_dynamic` when both cache lookups miss.

---

### WR-1 — Admin can ban themselves, locking out the only superuser

**File:** `backend/app/services/admin_service.py:85-126`  
**Severity:** warning  
**Description:**  
`update_user` applies any `status` change including `banned` without checking whether the target user is the currently-authenticated superuser. If a superuser accidentally (or via a script) bans their own account via `PATCH /admin/users/{own_uuid}`, they will trigger `invalidate_all_user_sessions` on themselves and be locked out. If they are the only superuser, recovery requires direct DB access.  
**Fix:** Before applying `status=banned` (or `status=deactivated`), check `user.uuid == requesting_admin.uuid` and raise a `BadRequestError`. The current route (`admin/users.py`) does not pass the requesting user to the service, so the endpoint signature also needs to be updated to receive it.

---

### WR-2 — `RateLimitRuleUpdate` can change `tier_uuid` but duplicate check is absent

**File:** `backend/app/services/rate_limit_rule_service.py:101-133`  
**Severity:** warning  
**Description:**  
`update_rule` allows changing `endpoint_pattern` and/or `tier_uuid`. There is no uniqueness check before writing — if the new (tier_id, endpoint_pattern) combination already exists as another active rule, the update will succeed silently at the service layer but fail at the DB level with a `UniqueConstraint` violation, producing a raw 500 rather than a clean 409. The database unique constraint `uq_rate_limit_tier_endpoint` catches this, but the service should catch it first.  
**Fix:** After resolving the new `tier_id` and new `endpoint_pattern`, call `repo.find_rule(new_tier_id, new_endpoint_pattern)` and raise `ConflictError` if the found rule's `id` differs from the current rule's `id`.

---

### WR-3 — `RateLimitRuleRead` exposes internal `tier_id` (integer PK)

**File:** `backend/app/schemas/rate_limit_rule.py:12-25`  
**Severity:** warning  
**Description:**  
The read schema includes `tier_id: int | None` which is the internal database primary key. Exposing internal PKs in API responses is a data-leakage issue that makes it easier to enumerate related records. `tier_slug` and `tier_name` are already present for display purposes.  
**Fix:** Remove `tier_id` from `RateLimitRuleRead` and rely on `tier_slug` / `tier_name` for client use. Alternatively, expose `tier_uuid` instead.

---

### WR-4 — `AdminUserRead` exposes `stripe_customer_id`

**File:** `backend/app/schemas/admin_user.py:26`  
**Severity:** warning  
**Description:**  
`stripe_customer_id` is a Stripe-internal identifier. While admins legitimately need to view billing info, the field is returned by the general `list_users` paginated response which could include dozens or hundreds of entries in a single response. Bulk exposure of Stripe customer IDs in list endpoints increases blast radius on any log leak or MITM.  
**Fix:** Consider moving `stripe_customer_id` to a separate `AdminUserDetailRead` used only by `GET /admin/users/{uuid}`, keeping the list response lean.

---

### WR-5 — `UniqueConstraint` on `(tier_id, endpoint_pattern)` does not enforce default-rule uniqueness correctly in PostgreSQL

**File:** `backend/app/models/rate_limit_rule.py:20-22`  
**Severity:** warning  
**Description:**  
The constraint `UniqueConstraint("tier_id", "endpoint_pattern")` covers the case where `tier_id` is a non-NULL value. However, in PostgreSQL **NULL values are not considered equal** in unique constraints, meaning multiple rows can exist with `tier_id=NULL` and the same `endpoint_pattern`. This defeats the intended uniqueness of "default" rules.  
**Fix:** Add a partial unique index to enforce uniqueness only for the default (NULL) case:
```sql
CREATE UNIQUE INDEX uq_rate_limit_default_endpoint
ON rate_limit_rule (endpoint_pattern)
WHERE tier_id IS NULL AND deleted_at IS NULL;
```
This needs a new migration and a corresponding `Index` definition in the SQLAlchemy model.

---

### WR-6 — `SystemSettingUpdate.value` is `Any` — no server-side pre-validation at schema layer

**File:** `backend/app/schemas/system_setting.py:123-126`  
**Severity:** warning  
**Description:**  
`SystemSettingUpdate.value: Any` means Pydantic will accept arbitrary nested structures (lists of dicts, objects, etc.) and pass them to `validate_setting_value()` in the service. While the service does validate, a deeply-nested or very large JSON payload will be fully deserialized before validation, creating a potential DoS vector if the endpoint is reached by a compromised superuser session or future access control regression. Additionally, setting a `list` value (e.g. `allowed_file_types`) accepts any list element types — there is no element-type validation in `validate_setting_value`.  
**Fix:** Add maximum payload depth/size validation (e.g. via a Pydantic validator) and extend the `list` type check in `validate_setting_value` to verify element types for known list settings.

---

### WR-7 — `downgrade()` migration drops foreign keys with `None` as constraint name

**File:** `backend/migrations/versions/2026_04_12_02136906e804_add_user_status_column_system_setting_.py:110-111`  
**Severity:** warning  
**Description:**  
The downgrade path uses `op.drop_constraint(None, 'user', type_='foreignkey')` and `op.drop_constraint(None, 'user', type_='unique')`. Passing `None` as the constraint name is unreliable — Alembic/SQLAlchemy will attempt to infer or generate a name, which can differ across databases and Alembic versions. This will likely fail with a `ProgrammingError` in production if a rollback is ever attempted.  
**Fix:** Capture the actual constraint name during the upgrade (or query `information_schema.table_constraints` in the migration itself) and use it explicitly in the downgrade.

---

### WR-8 — `get_all_settings()` cache returns raw `dict` (not `SystemSettingRead`) on cache hit

**File:** `backend/app/services/settings_service.py:45-68`  
**Severity:** warning  
**Description:**  
On a cache hit, `get_cached_all_settings()` returns the raw deserialized JSON dict that was stored via `model_dump(mode="json")`. The caller `get_all_settings()` returns this directly as `dict[str, list[SystemSettingRead]]`. However, the cached value is actually `dict[str, list[dict]]` — plain dicts, not `SystemSettingRead` instances. The `list_settings` endpoint then wraps this in `SystemSettingGroupedResponse(settings=grouped)`. Pydantic will attempt to coerce the inner lists, but only if `SystemSettingGroupedResponse` validates on construction — which it does in this case. However, the return type annotation `dict[str, list[SystemSettingRead]]` is incorrect for the cache hit path, creating a type-safety lie that may cause issues if the return value is used differently in future callers.  
**Fix:** Deserialize the cached dicts back into `SystemSettingRead` objects explicitly on cache hit, or change the return type to `dict[str, list[SystemSettingRead | dict]]` and add explicit conversion.

---

### IR-1 — `mock_superuser` fixture duplicated across all four test files

**File:** `backend/tests/test_admin_rate_limits.py`, `test_admin_settings.py`, `test_admin_tiers.py`, `test_admin_users.py`  
**Severity:** info  
**Description:**  
The `mock_superuser`, `mock_regular_user`, `_override_superuser`, `_override_regular_user`, and `_cleanup` fixtures are copy-pasted identically across all four test files. This violates DRY and means any change to the fixture structure must be replicated in four places.  
**Fix:** Extract shared fixtures and helper functions into `tests/conftest.py`.

---

### IR-2 — No test coverage for `check_rate_limit_dynamic` DB-miss path

**File:** `backend/app/utils/rate_limit.py:69`  
**Severity:** info  
**Description:**  
`check_rate_limit_dynamic` has no corresponding test. Given CR-2 (silent DB bypass), this function is both incorrect and untested.  
**Fix:** Add unit tests verifying that: (1) a cache hit uses the cached values, (2) a cache miss falls back to DB (once CR-2 is fixed), and (3) a DB miss uses the hardcoded fallback.

---

### IR-3 — `test_delete_tier` does not verify the free-tier guard

**File:** `backend/tests/test_admin_tiers.py:210-228`  
**Severity:** info  
**Description:**  
The tier service presumably has a guard preventing deletion of the `free` tier (per the docstring on the delete endpoint: *"Cannot delete the 'free' tier"*), but there is no test verifying that `DELETE /admin/tiers/{free_tier_uuid}` returns an error. The test only covers the happy path.  
**Fix:** Add a test case where `mock_tier_obj.slug = "free"` and assert that the response is 400 or 409, not 204.

---

### IR-4 — `allowed_file_types` list setting accepts any element type

**File:** `backend/app/schemas/system_setting.py:100-103`  
**Severity:** info  
**Description:**  
The `list` type check in `validate_setting_value` only confirms the value is a `list`. For `allowed_file_types`, a superuser could set the value to `[1, 2, 3]` or `[{"x": 1}]` and it would pass validation. This could cause silent failures downstream when file extension comparison is attempted.  
**Fix:** Add per-key element validation for list settings. For `allowed_file_types`, verify all elements are strings.

---

### IR-5 — `RateLimitRuleService.to_rule_read` accesses `rule.tier` which may not be loaded

**File:** `backend/app/services/rate_limit_rule_service.py:186-199`  
**Severity:** info  
**Description:**  
`to_rule_read` accesses `rule.tier.slug` and `rule.tier.name` with a null-guard (`if rule.tier`). The `RateLimitRule` model declares `tier` as `relationship("Tier", lazy="selectin")`, so in practice the relationship is always loaded. However, `to_rule_read` is a `@staticmethod` that could be called outside a DB session context (e.g., from a test or a future background task) where the lazy loader would raise a `MissingGreenlet` error. The `lazy="selectin"` annotation requires an active async session.  
**Fix:** This is low risk given current usage patterns, but document the session requirement in the method docstring, or use `getattr(rule, 'tier', None)` as a defensive fallback.
