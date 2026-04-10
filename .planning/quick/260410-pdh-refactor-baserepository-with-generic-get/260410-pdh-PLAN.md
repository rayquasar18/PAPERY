# Quick Plan: Refactor BaseRepository with Generic Field-Based Filtering

**ID:** 260410-pdh
**Created:** 2026-04-10
**Status:** planned
**Branch:** feature/refactor-base-repository-generic-get

---

## Objective

Replace hardcoded `get_by_id()` / `get_by_uuid()` on `BaseRepository` with a generic `get(**filters)` method that accepts arbitrary field-based filtering. Add `get_multi()` for paginated listing and `delete()` for hard deletion. Simplify `UserRepository` by removing methods that are now redundant with the generic base.

---

## Current State

| File | Current API | Issue |
|------|-------------|-------|
| `base.py` | `get_by_id(id)`, `get_by_uuid(uuid)` | Hardcoded per-field lookups; every new field needs a new method |
| `user_repository.py` | `get_by_email(email)`, `get_active_by_uuid(uuid)` | `get_by_email` is just `get(email=email.lower())`; `get_active_by_uuid` is `get(uuid=uuid)` since `_not_deleted()` already filters |
| `auth_service.py` | Calls `user_repo.get_by_email(...)`, `user_repo.get_active_by_uuid(...)` | Needs updating to new API |
| `dependencies.py` | Calls `user_repo.get_active_by_uuid(...)` | Needs updating to new API |
| `test_user_repository.py` | Tests `get_by_email`, `get_active_by_uuid`, `get_by_id`, `get_by_uuid` | Needs updating to new API |

---

## Design

### BaseRepository new methods

```python
async def get(self, **filters: Any) -> ModelType | None:
    """Fetch a single record matching all filters (soft-delete aware)."""
    stmt = select(self._model)
    for field, value in filters.items():
        stmt = stmt.where(getattr(self._model, field) == value)
    stmt = self._not_deleted(stmt)
    result = await self._session.execute(stmt)
    return result.scalar_one_or_none()

async def get_multi(
    self, *, skip: int = 0, limit: int = 100, **filters: Any,
) -> list[ModelType]:
    """Fetch multiple records with pagination and optional filters (soft-delete aware)."""
    stmt = select(self._model)
    for field, value in filters.items():
        stmt = stmt.where(getattr(self._model, field) == value)
    stmt = self._not_deleted(stmt)
    stmt = stmt.offset(skip).limit(limit)
    result = await self._session.execute(stmt)
    return list(result.scalars().all())

async def delete(self, instance: ModelType) -> None:
    """Hard-delete a record permanently."""
    await self._session.delete(instance)
    await self._session.commit()
```

### Backward compatibility

- Remove `get_by_id()` and `get_by_uuid()` from `BaseRepository`
- Remove `get_by_email()` and `get_active_by_uuid()` from `UserRepository`
- Keep `create_user()` on `UserRepository` (domain-specific factory with email lowercasing)

### Consumer migration

| Consumer | Old call | New call |
|----------|----------|----------|
| `auth_service.register_user` | `user_repo.get_by_email(email)` | `user_repo.get(email=email.lower())` |
| `auth_service.authenticate_user` | `user_repo.get_by_email(email)` | `user_repo.get(email=email.lower())` |
| `auth_service.create_first_superuser` | `user_repo.get_by_email(admin_email)` | `user_repo.get(email=admin_email.lower())` |
| `auth_service.rotate_refresh_token` | `user_repo.get_active_by_uuid(uuid)` | `user_repo.get(uuid=uuid)` |
| `auth_service.verify_email` | `user_repo.get_active_by_uuid(uuid)` | `user_repo.get(uuid=uuid)` |
| `dependencies.get_current_user` | `user_repo.get_active_by_uuid(uuid)` | `user_repo.get(uuid=uuid)` |

### Field validation

The `get()` method will use `getattr(self._model, field)` which raises `AttributeError` if the field doesn't exist on the model. This is the correct behavior — callers should only filter on valid model columns.

---

## Tasks

### Task 1: Refactor BaseRepository — add generic `get`, `get_multi`, `delete`

**File:** `backend/app/repositories/base.py`

**Changes:**
1. Remove `get_by_id()` method
2. Remove `get_by_uuid()` method
3. Add `get(**filters)` — generic single-record lookup with soft-delete awareness
4. Add `get_multi(*, skip, limit, **filters)` — generic paginated listing with soft-delete awareness
5. Add `delete(instance)` — hard delete (permanent removal)
6. Add `from typing import Any` import

**Validation:** File compiles, type hints correct.

### Task 2: Simplify UserRepository + update consumers

**Files:**
- `backend/app/repositories/user_repository.py` — remove `get_by_email()`, `get_active_by_uuid()`; keep `create_user()`
- `backend/app/services/auth_service.py` — replace all old calls with `user_repo.get(field=value)`
- `backend/app/api/dependencies.py` — replace `get_active_by_uuid()` with `user_repo.get(uuid=uuid)`

**Changes in user_repository.py:**
- Remove `get_by_email()` method (BaseRepository.get handles it)
- Remove `get_active_by_uuid()` method (BaseRepository.get handles it — `_not_deleted()` already filters soft-deleted)
- Remove unused imports (`uuid_pkg`, `select`, `User` from sqlalchemy)

**Changes in auth_service.py:**
- `get_by_email(email)` → `get(email=email.lower())`  (3 call sites)
- `get_active_by_uuid(uuid)` → `get(uuid=uuid)` (2 call sites)

**Changes in dependencies.py:**
- `get_active_by_uuid(uuid)` → `get(uuid=uuid)` (1 call site)
- Remove unused `uuid_pkg` import if no longer needed (still needed for UUID cast)

### Task 3: Update tests

**File:** `backend/tests/test_user_repository.py`

**Changes:**
1. Remove `TestGetByEmail` class — replace with tests for `repo.get(email=...)` via BaseRepository
2. Remove `TestGetActiveByUuid` class — replace with tests for `repo.get(uuid=...)` via BaseRepository
3. Update `TestBaseRepositoryMethods`:
   - Remove `test_get_by_id` → replace with `test_get_by_id_filter`
   - Remove `test_get_by_uuid` → replace with `test_get_by_uuid_filter`
   - Add `test_get_multi` — basic pagination test
   - Add `test_delete` — hard delete test
4. Keep `TestCreateUser` as-is (API unchanged)

---

## Execution Order

```
Task 1 (base.py) → Task 2 (user_repo + consumers) → Task 3 (tests)
```

All three tasks should be committed as a single logical change.

---

## Risk Assessment

- **Low risk:** No new dependencies, no schema changes, no migration needed
- **Breaking:** Removes `get_by_id`, `get_by_uuid`, `get_by_email`, `get_active_by_uuid` — all consumers updated in same PR
- **Validation:** Run `make lint && make test` after all changes
