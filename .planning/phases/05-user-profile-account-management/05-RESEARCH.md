# Phase 5: User Profile & Account Management — Research

**Researched:** 2026-04-11
**Phase:** 05-user-profile-account-management
**Status:** Ready for planning

---

## 1. What This Phase Builds

Phase 5 delivers user self-service via three requirements:

| Req | Description | Complexity |
|-----|-------------|-----------|
| USER-01 | View own profile (name, email, avatar, tier, created date) | Low |
| USER-02 | Edit profile — display_name + avatar upload | Medium-High |
| USER-04 | Delete own account (soft deactivation + session invalidation) | Medium |

All three are backend-only (Phase 9 handles frontend). No new database migrations are needed — the `User` model already has all required fields.

---

## 2. Codebase Reality Check

### 2.1 What Already Exists (No Work Needed)

| Asset | Location | How Phase 5 Uses It |
|-------|----------|---------------------|
| `User.display_name` (String(100)) | `app/models/user.py:18` | Editable field in PATCH /users/me |
| `User.avatar_url` (Text, nullable) | `app/models/user.py:19` | Stores MinIO object path |
| `User.is_active` (Boolean) | `app/models/user.py:20` | Set to False on account deletion |
| `SoftDeleteMixin.deleted_at` | `app/models/base.py:49` | Set on account deletion |
| `BaseRepository.soft_delete()` | `app/repositories/base.py:109` | Reuse for account deletion |
| `BaseRepository.update()` | `app/repositories/base.py:103` | Reuse for profile update |
| `UserRepository` | `app/repositories/user_repository.py` | Extended by UserService |
| `invalidate_all_user_sessions()` | `app/core/security.py:252` | Reuse on account deletion (D-09) |
| `verify_password()` | `app/core/security.py:32` | Reuse for delete confirmation (D-08) |
| `get_current_user` dep | `app/api/dependencies.py:26` | All /users/* endpoints |
| `get_current_active_user` dep | `app/api/dependencies.py:61` | Required for mutation endpoints |
| `UserPublicRead` schema | `app/schemas/auth.py:83` | Base for `UserProfileRead` |
| `minio_client.upload_file()` | `app/infra/minio/client.py:100` | Avatar upload (async, executor-wrapped) |
| `minio_client.presigned_get_url()` | `app/infra/minio/client.py:52` | On-demand avatar URL generation |
| `check_rate_limit()` | `app/utils/rate_limit.py:18` | All mutation endpoints |
| `AuthService(db)` class pattern | `app/services/auth_service.py:53` | Template for `UserService(db)` |

### 2.2 What Must Be Created

| Artifact | File | Notes |
|----------|------|-------|
| `UserService` class | `app/services/user_service.py` | New service following AuthService pattern |
| User profile schemas | `app/schemas/user.py` | `UserProfileRead`, `UserProfileUpdate`, `DeleteAccountRequest`, `AvatarUploadResponse` |
| Users router | `app/api/v1/users.py` | 5 endpoints under `/api/v1/users` |
| Router registration | `app/api/v1/__init__.py` | Add `users_router` alongside `auth_router` |
| Pillow dependency | `pyproject.toml` | Image resize + WebP conversion |
| Service export | `app/services/__init__.py` | Export `UserService` (if file exists) |

### 2.3 Key Observations from Code Audit

**User model gaps for Phase 5 response:**
- `UserPublicRead` in `auth.py:83` has: uuid, email, display_name, avatar_url, is_verified, is_superuser, created_at
- `UserProfileRead` needs to add: `tier_name: str = "free"` (placeholder), `has_password: bool`, `oauth_providers: list[str]`
- `has_password` = `user.hashed_password is not None` — compute in service layer
- `oauth_providers` = list of `oauth_account.provider` strings — requires loading `user.oauth_accounts` relationship

**OAuthAccount relationship:**
- `User.oauth_accounts` is a `relationship("OAuthAccount", ...)` with `back_populates` — already defined
- SQLAlchemy async requires explicit `.selectinload()` or `.joinedload()` for eager loading — the basic `UserRepository.get()` uses `select(User)` without eager loading
- The profile endpoint needs `oauth_accounts` loaded → requires either custom query in `UserRepository` or explicit `.options()` in `UserService`

**MinIO avatar storage:**
- `avatar_url` on User stores the **object path** (e.g., `avatars/{uuid}/avatar.webp`), NOT the presigned URL (D-05)
- `presigned_get_url()` takes `object_name` (the stored path) + optional `expires` seconds → generates on-demand URL
- Avatar deletion: need `minio_client.client.remove_object()` (sync, needs executor wrapping)

**Account deletion semantics (D-06, D-07):**
- `SoftDeleteMixin.soft_delete()` sets `deleted_at = now()` but does **not** set `is_active = False`
- For account deletion we need BOTH: `is_active = False` AND `deleted_at = now()`
- `BaseRepository.soft_delete()` only sets `deleted_at` — the service must also set `is_active = False` before calling `update()` or do a combined operation
- `get_current_user` dep in `dependencies.py:54` fetches by UUID with soft-delete filter (`deleted_at IS NULL`) — after soft_delete, the user won't be findable, so sessions are naturally dead. But we still call `invalidate_all_user_sessions()` for immediate Redis-level invalidation (D-09)

---

## 3. Architecture Decisions (From Context)

All decisions are **locked in `05-CONTEXT.md`**. Key ones that affect implementation:

### 3.1 Avatar Upload Pipeline (D-01 to D-05)
```
Request (multipart/form-data)
  → Validate MIME type (image/jpeg, image/png, image/webp) + size (≤ 2MB)
  → Read bytes into memory
  → Pillow: resize to 200x200, convert to WebP (main)
  → Pillow: resize to 50x50, convert to WebP (thumbnail)
  → minio_client.upload_file("avatars/{uuid}/avatar.webp", data, "image/webp")
  → minio_client.upload_file("avatars/{uuid}/avatar_thumb.webp", data, "image/webp")
  → user.avatar_url = "avatars/{uuid}/avatar.webp"  ← store object path
  → UserRepository.update(user)
  → Generate presigned URL on-the-fly for response
  → Return AvatarUploadResponse(avatar_url=<presigned>, thumbnail_url=<presigned>)
```

**Pillow specifics:**
- `Pillow` (PyPI: `Pillow`) is the standard Python imaging library — install as `pillow` in pyproject.toml
- Resize strategy: `Image.thumbnail((200, 200), Image.LANCZOS)` for aspect-ratio preserving, or `Image.resize((200, 200), Image.LANCZOS)` for exact square crop
- WebP conversion: `img.save(buffer, format="WebP", quality=85)` — quality 85 is a good balance
- For exact 200x200 (square avatar): use `ImageOps.fit(img, (200, 200), Image.LANCZOS)` — crops to center
- Memory: `io.BytesIO()` for in-memory processing (no temp files)

### 3.2 API Design (D-10 to D-13)

```
GET    /api/v1/users/me          → UserProfileRead (full profile + presigned avatar URL)
PATCH  /api/v1/users/me          → UserProfileRead (returns updated profile)
DELETE /api/v1/users/me          → MessageResponse (204 or 200)
POST   /api/v1/users/me/avatar   → AvatarUploadResponse
DELETE /api/v1/users/me/avatar   → MessageResponse
```

- **GET /users/me vs GET /auth/me:** Both exist. `/auth/me` returns `UserPublicRead` (lightweight). `/users/me` returns `UserProfileRead` (full, with tier_name + has_password + oauth_providers). Two endpoints, two purposes (D-11).
- **PATCH /users/me:** Only `display_name` field. Avatar via separate POST endpoint (D-13).
- **DELETE /users/me:** Requires `DeleteAccountRequest` body (password or email confirmation per D-08).

### 3.3 UserService Design (D-14)

```python
class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._user_repo = UserRepository(db)

    async def get_profile(self, user: User) -> UserProfileRead: ...
    async def update_profile(self, user: User, data: UserProfileUpdate) -> User: ...
    async def upload_avatar(self, user: User, file_data: bytes, content_type: str) -> tuple[str, str]: ...
    async def remove_avatar(self, user: User) -> None: ...
    async def delete_account(self, user: User, confirmation: DeleteAccountRequest) -> None: ...
```

### 3.4 Account Deletion Flow (D-06 to D-09)

```
1. Receive DeleteAccountRequest(password=str | None, email=str | None)
2. If user.hashed_password is not None:
     → verify_password(request.password, user.hashed_password) — raise UnauthorizedError if wrong
3. Else (OAuth-only):
     → assert request.email.lower() == user.email — raise BadRequestError if mismatch
4. user.is_active = False
5. await self._user_repo.soft_delete(user)  → sets deleted_at + commits
6. await invalidate_all_user_sessions(user.uuid)  → Redis: revoke all families
7. Return (router clears cookies if needed)
```

Note: After soft_delete, the user's `deleted_at` is set. `get_current_user` dep filters `deleted_at IS NULL`, so the deleted user's tokens will fail on next request anyway. But immediate Redis invalidation (step 6) ensures in-flight requests are also blocked.

---

## 4. New Files to Create

### 4.1 `app/schemas/user.py`

```python
class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uuid: UUID
    email: str
    display_name: str | None
    avatar_url: str | None          # presigned URL (generated on-demand)
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    tier_name: str                  # hardcoded "free" until Phase 6
    has_password: bool              # not from_attributes — computed in service
    oauth_providers: list[str]      # not from_attributes — computed in service

class UserProfileUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=2, max_length=50, pattern=r"^[\w\s\-]+$")

class DeleteAccountRequest(BaseModel):
    password: str | None = None     # for users with password
    email: str | None = None        # for OAuth-only users

    @model_validator(mode="after")
    def exactly_one_must_be_provided(self): ...

class AvatarUploadResponse(BaseModel):
    avatar_url: str                 # presigned URL for 200x200
    thumbnail_url: str              # presigned URL for 50x50
    message: str
```

**Important:** `UserProfileRead` has `has_password` and `oauth_providers` that cannot be derived by `from_attributes=True` alone — they are computed fields. The service builds these manually and passes them when constructing the response schema.

### 4.2 `app/services/user_service.py`

Key methods and their logic:

**`get_profile(user)`:**
- Load `user.oauth_accounts` (requires eager load or explicit query)
- Generate presigned URL for `user.avatar_url` if set
- Build `UserProfileRead` manually (not `model_validate`) for the computed fields

**`update_profile(user, data)`:**
- Strip whitespace from `display_name`
- Update `user.display_name = data.display_name.strip()`
- `await self._user_repo.update(user)`
- Return updated `User`

**`upload_avatar(user, file_data, content_type)`:**
- Process with Pillow → 200x200 WebP + 50x50 WebP
- Upload both to MinIO
- Update `user.avatar_url = f"avatars/{user.uuid}/avatar.webp"`
- `await self._user_repo.update(user)`
- Return `(presigned_main_url, presigned_thumb_url)`

**`remove_avatar(user)`:**
- Delete from MinIO: both `avatars/{uuid}/avatar.webp` and `avatars/{uuid}/avatar_thumb.webp`
- Set `user.avatar_url = None`
- `await self._user_repo.update(user)`

**`delete_account(user, confirmation)`:**
- Validate confirmation (password or email)
- `user.is_active = False`
- `await self._user_repo.soft_delete(user)` — sets deleted_at, commits
- `await invalidate_all_user_sessions(user.uuid)` — Redis cleanup

### 4.3 `app/api/v1/users.py`

Router with 5 endpoints. All require `get_current_active_user`.

Rate limits (Claude's discretion per context):
- `GET /users/me` → 60 req/min per user (read-heavy, generous)
- `PATCH /users/me` → 10 req/min per user
- `POST /users/me/avatar` → 5 req/min per user (upload intensive)
- `DELETE /users/me/avatar` → 5 req/min per user
- `DELETE /users/me` → 3 req/min per user (destructive, low threshold)

### 4.4 `app/api/v1/__init__.py` (Modified)

Add import and registration:
```python
from app.api.v1.users import router as users_router
api_v1_router.include_router(users_router)
```

---

## 5. Technical Gotchas & Edge Cases

### 5.1 SQLAlchemy Async + Relationship Loading

**Problem:** `user.oauth_accounts` is a lazy-loaded relationship by default. In async SQLAlchemy, accessing lazy-loaded relationships raises `MissingGreenlet` error outside of a session context.

**Solution:** Two options:
1. **selectinload in UserRepository** — add a `get_with_oauth_accounts(uuid)` method that does `select(User).options(selectinload(User.oauth_accounts)).where(...)`. Cleanest for profile endpoint.
2. **Explicit session.refresh with attribute loading** — `await session.refresh(user, ["oauth_accounts"])`. Simpler but less reusable.

**Recommended:** Add `get_with_oauth_accounts(**filters)` to `UserRepository` following the established `get(**filters)` pattern, but with `selectinload`.

### 5.2 Pillow: Exact Square Crop vs Thumbnail

- `Image.thumbnail((200, 200))` — preserves aspect ratio, result may be rectangular
- `ImageOps.fit(img, (200, 200))` — center-crops to exact square ✅ (correct for avatar)

Use `ImageOps.fit()` for both sizes to ensure exact square dimensions.

### 5.3 MinIO: Object Deletion

`minio_client.client.remove_object(bucket, object_name)` is synchronous — must wrap in `run_in_executor` for async safety, same pattern as `upload_file()`.

Add a `delete_file()` function to `app/infra/minio/client.py`:
```python
async def delete_file(object_name: str) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        partial(client.remove_object, settings.MINIO_BUCKET_NAME, object_name)
    )
```

### 5.4 MIME Type Validation

FastAPI receives uploaded files as `UploadFile`. Validate:
1. `file.content_type` — but headers can be spoofed
2. Read first bytes and use `python-magic` or `filetype` library — OR use Pillow's `Image.open()` which will raise `UnidentifiedImageError` for invalid images

**Simple approach:** Use `file.content_type` for initial check, then let Pillow's `Image.open()` serve as secondary validation (if Pillow can't open it → bad file).

Allowed content types: `image/jpeg`, `image/png`, `image/webp`

### 5.5 File Size Limit (2MB)

FastAPI's `UploadFile` doesn't enforce size by itself. Two options:
1. Read all bytes first, then check `len(data) > 2 * 1024 * 1024` — simple, works for small files
2. Use `python-multipart` streaming with custom size guard

**Recommended:** Read bytes first (max 2MB for avatar is acceptable in memory), then validate.

```python
data = await file.read()
if len(data) > 2 * 1024 * 1024:
    raise BadRequestError(detail="File size exceeds 2MB limit")
```

### 5.6 Account Deletion: Cookie Cleanup

The router should clear auth cookies after successful account deletion — same as logout. Reuse `_clear_auth_cookies()` from `auth.py` or duplicate the pattern in `users.py`. Since routers don't import from other routers (STRUCTURE.md rule), duplicate the cookie-clearing logic in users.py or extract to a shared utility.

**Recommended:** Extract `_set_auth_cookies()` and `_clear_auth_cookies()` to `app/utils/cookies.py` (shared utility), then import from both `auth.py` and `users.py`. This avoids router cross-imports and eliminates duplication.

Alternatively, define the helper directly in `users.py` (simpler for now, DRY later in Phase 9).

### 5.7 `UserProfileRead.avatar_url` is Presigned, Not Stored Path

The `User.avatar_url` field stores `"avatars/{uuid}/avatar.webp"` (the MinIO object path). The API response must return a presigned URL, not the raw path. This transformation happens in the service's `get_profile()` method.

The `UserProfileRead` schema's `avatar_url` field contains the **presigned URL** at response time — it's **not** `from_attributes=True` compatible directly for this field. The service must build the response manually:

```python
presigned = minio_client.presigned_get_url(user.avatar_url) if user.avatar_url else None
return UserProfileRead(
    uuid=user.uuid,
    email=user.email,
    ...
    avatar_url=presigned,  # Override with presigned URL
    has_password=user.hashed_password is not None,
    oauth_providers=[acc.provider for acc in user.oauth_accounts],
)
```

### 5.8 `DeleteAccountRequest` Validation

The `@model_validator` must enforce: either `password` OR `email` is provided, not both None, not both provided:

```python
@model_validator(mode="after")
def exactly_one_must_be_provided(self):
    if self.password is None and self.email is None:
        raise ValueError("Either password or email must be provided for account deletion")
    if self.password is not None and self.email is not None:
        raise ValueError("Provide either password or email, not both")
    return self
```

### 5.9 `display_name` Validation (D-15)

The context specifies: 2-50 chars, letters (unicode), digits, spaces, hyphens, underscores.

Pydantic Field pattern for this:
```python
display_name: str | None = Field(
    None,
    min_length=2,
    max_length=50,
    pattern=r"^[\w\s\-]+$"  # \w = [a-zA-Z0-9_] + unicode by default in Python
)
```

Note: `\w` in Python regex includes Unicode word characters by default — this covers international names (Vietnamese, Chinese, etc.). Test this explicitly.

Strip whitespace **before** length validation → do in service layer, not schema.

---

## 6. Presigned URL Expiry Strategy

Decision deferred to Claude per context. Recommended values:

| Use Case | Expiry | Rationale |
|----------|--------|-----------|
| Avatar URL in profile response | 3600s (1 hour) | Default `MINIO_PRESIGNED_GET_EXPIRY` from settings |
| Avatar URL in upload response | 3600s (1 hour) | Same — consistent |

The `presigned_get_url()` function already defaults to `settings.MINIO_PRESIGNED_GET_EXPIRY` (3600s). No override needed — use the default.

---

## 7. Plan Breakdown Recommendation

Given scope and complexity, this phase should be split into **2 plans**:

### Plan 05-01: Foundation — Schemas + Service + GET/PATCH Profile
**Scope:**
- Create `app/schemas/user.py` with all 4 schema classes
- Create `app/services/user_service.py` with `get_profile()` and `update_profile()`
- Add `get_with_oauth_accounts()` to `UserRepository`
- Create `app/api/v1/users.py` with `GET /users/me` and `PATCH /users/me`
- Register router in `__init__.py`
- Add `pillow` dependency (even though used in Plan 02 — add early to unblock)
- Tests: profile read, profile update

**Why separate from avatar/delete:** GET + PATCH profile are the most fundamental and lowest risk. Clean foundation before adding binary upload complexity.

### Plan 05-02: Avatar Upload + Account Deletion
**Scope:**
- Add `delete_file()` to `app/infra/minio/client.py`
- Add `upload_avatar()` and `remove_avatar()` to `UserService`
- Add `delete_account()` to `UserService`
- Add `POST /users/me/avatar`, `DELETE /users/me/avatar`, `DELETE /users/me` endpoints
- Tests: avatar upload (mock MinIO), avatar removal, account deletion (both password and email paths)

---

## 8. Dependencies to Add

```toml
# pyproject.toml — add to project dependencies
pillow = ">=10.0.0"          # Image resize + WebP conversion
```

No other new dependencies needed. `python-multipart` is already required by FastAPI for `UploadFile`.

---

## 9. Test Strategy

| Test | Type | Assertions |
|------|------|-----------|
| GET /users/me — authenticated | Integration | Returns full profile, avatar_url is presigned URL |
| GET /users/me — unauthenticated | Integration | 401 |
| PATCH /users/me — valid display_name | Integration | Returns updated name |
| PATCH /users/me — too short name | Integration | 422 validation error |
| PATCH /users/me — invalid chars | Integration | 422 validation error |
| POST /users/me/avatar — valid JPEG | Integration | Returns avatar_url + thumbnail_url |
| POST /users/me/avatar — oversized | Integration | 400 BadRequest |
| POST /users/me/avatar — wrong type | Integration | 400 BadRequest |
| DELETE /users/me/avatar — has avatar | Integration | Clears avatar_url |
| DELETE /users/me/avatar — no avatar | Integration | 400 or no-op (define behavior) |
| DELETE /users/me — correct password | Integration | 200, user deactivated |
| DELETE /users/me — wrong password | Integration | 401 |
| DELETE /users/me — OAuth-only, correct email | Integration | 200, user deactivated |
| DELETE /users/me — OAuth-only, wrong email | Integration | 400 |
| GET /users/me after deletion | Integration | 401 (token invalidated) |

**MinIO mocking:** Use `unittest.mock.patch` or a fixture that mocks `minio_client.upload_file`, `minio_client.presigned_get_url`, and `minio_client.delete_file`. Tests should not require a running MinIO instance.

---

## 10. Integration Points with Future Phases

| Future Phase | What Phase 5 Provides | What Phase Must Do |
|-------------|----------------------|-------------------|
| Phase 6 (Tier System) | `tier_name: "free"` hardcoded in `UserProfileRead` | Replace hardcoded value with actual tier lookup from DB |
| Phase 7 (Admin Panel) | `is_active = False` + `deleted_at` on deleted users | Expose admin endpoint to reactivate (`is_active=True`, `deleted_at=None`) |
| Phase 9 (Frontend) | `GET/PATCH /users/me`, `POST/DELETE /users/me/avatar`, `DELETE /users/me` endpoints | Build profile page UI consuming these endpoints |

---

## 11. Files Touched Summary

| File | Action | Description |
|------|--------|-------------|
| `app/schemas/user.py` | **CREATE** | 4 new schema classes |
| `app/services/user_service.py` | **CREATE** | UserService class with 5 methods |
| `app/api/v1/users.py` | **CREATE** | 5 endpoint handlers |
| `app/api/v1/__init__.py` | **MODIFY** | Register users_router |
| `app/repositories/user_repository.py` | **MODIFY** | Add `get_with_oauth_accounts()` |
| `app/infra/minio/client.py` | **MODIFY** | Add `delete_file()` async function |
| `pyproject.toml` | **MODIFY** | Add `pillow` dependency |
| `backend/app/utils/cookies.py` | **CREATE** (optional) | Shared cookie helpers (if extracting from auth.py) |
| `tests/test_users.py` | **CREATE** | User profile endpoint tests |

**No database migrations needed** — all required columns (`display_name`, `avatar_url`, `is_active`, `deleted_at`) already exist in the `user` table.

---

## Validation Architecture

### Verification Approach

Phase 5 validation focuses on three pillars: **API correctness**, **file storage integrity**, and **account lifecycle safety**.

### Dimension Mapping

| Dimension | What to Validate | How |
|-----------|------------------|-----|
| Functional correctness | All 5 endpoints return correct status codes and response shapes | Integration tests with authenticated client |
| Input validation | display_name constraints (2-50 chars, allowed chars), file size (2MB), MIME type | Unit tests with edge cases |
| Security | Auth required on all endpoints, password verification on delete, session invalidation | Integration tests: unauthenticated returns 401, wrong password returns 401 |
| Data integrity | avatar_url stores object path (not presigned), soft_delete sets both is_active + deleted_at | Unit tests on UserService methods |
| Integration | MinIO upload/delete works, presigned URL generation works, router registration | Integration tests with mocked MinIO |
| Error handling | Invalid file type → 400, oversized file → 400, OAuth-only wrong email → 400 | Negative test cases |
| Idempotency | Double avatar delete is safe, profile read after delete returns 401 | Edge case tests |

### Testable Acceptance Criteria

1. `GET /api/v1/users/me` returns `UserProfileRead` with `tier_name`, `has_password`, `oauth_providers` fields
2. `PATCH /api/v1/users/me` with valid `display_name` returns updated profile
3. `PATCH /api/v1/users/me` with `display_name` < 2 chars returns 422
4. `POST /api/v1/users/me/avatar` with valid image returns `AvatarUploadResponse` with presigned URLs
5. `POST /api/v1/users/me/avatar` with file > 2MB returns 400
6. `DELETE /api/v1/users/me` with correct password sets `is_active=False` and `deleted_at != null`
7. `DELETE /api/v1/users/me` invalidates all user sessions in Redis
8. After account deletion, existing JWT token fails authentication (401)

### Risk Areas

- **Pillow processing in async context** — image processing is CPU-bound, may block event loop. Consider `run_in_executor` for large images.
- **MinIO connectivity** — must mock in tests, but verify presigned URL format is valid.
- **OAuth relationship loading** — `selectinload` must be used; lazy loading will crash in async.

---

*Researched: 2026-04-11*
*Phase: 05-user-profile-account-management*
