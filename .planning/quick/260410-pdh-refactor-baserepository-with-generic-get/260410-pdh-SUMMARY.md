# Summary: Refactor BaseRepository with Generic Field-Based Filtering

**ID:** 260410-pdh
**Status:** complete
**Branch:** feature/refactor-base-repository-generic-get
**Commit:** edaca8c

---

## What Changed

### BaseRepository (`base.py`)
- **Removed:** `get_by_id(id)` and `get_by_uuid(uuid)` — hardcoded per-field lookups
- **Added:** `get(**filters)` — generic single-record lookup accepting any model column as a keyword filter
- **Added:** `get_multi(*, skip, limit, **filters)` — paginated multi-record listing with optional filters
- **Added:** `delete(instance)` — hard-delete (permanent row removal), complementing existing `soft_delete`
- **Removed:** unused `uuid_pkg` import
- **Added:** `Any` import from typing

### UserRepository (`user_repository.py`)
- **Removed:** `get_by_email(email)` — now handled by `repo.get(email=email.lower())`
- **Removed:** `get_active_by_uuid(uuid)` — now handled by `repo.get(uuid=uuid)` (soft-delete filtering is automatic via `_not_deleted()`)
- **Kept:** `create_user()` — domain-specific factory with email lowercasing
- **Removed:** unused imports (`uuid_pkg`, `select`, direct `User` from sqlalchemy)

### Consumers Updated
| File | Old Call | New Call |
|------|----------|---------|
| `auth_service.py` (3 sites) | `get_by_email(email)` | `get(email=email.lower())` |
| `auth_service.py` (2 sites) | `get_active_by_uuid(uuid)` | `get(uuid=uuid)` |
| `dependencies.py` (1 site) | `get_active_by_uuid(uuid)` | `get(uuid=uuid)` |
| `api/v1/auth.py` (1 site) | `get_active_by_uuid(uuid)` | `get(uuid=uuid)` |
| `api/v1/auth.py` (1 site) | `get_by_email(body.email)` | `get(email=body.email.lower())` |

### Tests Updated
- **`test_user_repository.py`:** Replaced `TestGetByEmail` and `TestGetActiveByUuid` classes with `TestGet` (6 tests for generic `get`), added `TestGetMulti` (3 tests) and `TestDelete` (1 test)
- **`test_auth_routes.py`:** Updated all mock configurations from `get_active_by_uuid`/`get_by_email` to `get`

---

## Validation

- **135 tests passed, 0 failed** (full suite)
- No lint errors
- All old method references eliminated from source (only test method names reference old names descriptively)

---

## Design Rationale

Hardcoded `get_by_X` methods on the base repository forced every new lookup field to require a new method. The generic `get(**filters)` pattern:
1. Eliminates method proliferation — any model column works as a filter
2. Keeps soft-delete awareness automatic via `_not_deleted()`
3. Validates column names at runtime via `getattr()` (raises `AttributeError` for invalid columns)
4. Moves domain-specific concerns (e.g., email lowercasing) to the caller/service layer where they belong
