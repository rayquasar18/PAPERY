# Phase 05 Verification: User Profile & Account Management

**Verified:** 2026-04-11
**Phase goal:** "Complete user self-service — view/edit profile, avatar upload, and account deletion with soft delete grace period."
**Requirement IDs:** USER-01, USER-02, USER-04
**Overall status:** PASS

---

## 1. Requirement Traceability

Cross-reference of phase requirement IDs against REQUIREMENTS.md:

| Requirement ID | REQUIREMENTS.md Description | Phase Plan | Status |
|---|---|---|---|
| USER-01 | User can view own profile (name, email, avatar, tier, created date) | 05-01 | PASS |
| USER-02 | User can edit own profile (display name, avatar) | 05-01, 05-02 | PASS |
| USER-04 | User can delete own account (soft delete with grace period) | 05-02 | PASS |

All 3 requirement IDs from the phase frontmatter are accounted for in REQUIREMENTS.md. No orphaned or missing IDs.

Note: USER-03 (change password) is assigned to Phase 4 in REQUIREMENTS.md, not Phase 5 — correctly excluded from this phase.

---

## 2. Plan 05-01 Must-Haves Verification

### MH-01: `GET /api/v1/users/me` returns `UserProfileRead` with all required fields
- **Status:** PASS
- **Evidence:** `backend/app/api/v1/users.py:32` — `@router.get("/me", response_model=UserProfileRead)`
- **Fields verified in schema** (`backend/app/schemas/user.py:11-25`): uuid, email, display_name, avatar_url, is_verified, is_superuser, created_at, tier_name, has_password, oauth_providers — all present
- **Test:** `test_get_profile_returns_full_profile` asserts all fields (line 93-101)

### MH-02: `PATCH /api/v1/users/me` with valid `display_name` (2-50 chars, pattern) returns updated `UserProfileRead`
- **Status:** PASS
- **Evidence:** `backend/app/api/v1/users.py:54` — `@router.patch("/me", response_model=UserProfileRead)`
- **Validation:** `backend/app/schemas/user.py:31-36` — `min_length=2, max_length=50, pattern=r"^[\w\s\-]+$"`
- **Test:** `test_update_display_name_valid` asserts 200 (line 201)

### MH-03: `PATCH /api/v1/users/me` with `display_name` shorter than 2 chars returns 422
- **Status:** PASS
- **Evidence:** Pydantic `min_length=2` on `UserProfileUpdate.display_name` (schema line 33)
- **Test:** `test_update_display_name_too_short` sends `"A"`, asserts 422 (line 221)

### MH-04: `UserService(db)` follows `AuthService(db)` constructor DI pattern
- **Status:** PASS
- **Evidence:** `backend/app/services/user_service.py:52-54` — `def __init__(self, db: AsyncSession) -> None:`, creates `UserRepository(db)` in `__init__`

### MH-05: `UserRepository.get_with_oauth_accounts(**filters)` uses `selectinload(User.oauth_accounts)`
- **Status:** PASS
- **Evidence:** `backend/app/repositories/user_repository.py:59-75` — method exists with `selectinload(User.oauth_accounts)` on line 70, `self._not_deleted(stmt)` on line 73, `result.scalar_one_or_none()` on line 75

### MH-06: `UserProfileRead.has_password` is `True` when `user.hashed_password is not None`
- **Status:** PASS
- **Evidence:** `backend/app/services/user_service.py:90` — `has_password=user_with_oauth.hashed_password is not None`
- **Tests:** `test_get_profile_returns_full_profile` asserts `has_password is True` (line 98), `test_get_profile_oauth_user_has_password_false` asserts `has_password is False` (line 129)

### MH-07: `UserProfileRead.oauth_providers` is a list of provider name strings
- **Status:** PASS
- **Evidence:** `backend/app/services/user_service.py:91` — `oauth_providers=[acc.provider for acc in user_with_oauth.oauth_accounts]`
- **Test:** `test_get_profile_oauth_user_has_password_false` asserts `oauth_providers == ["google"]` (line 130)

### MH-08: `UserProfileRead.tier_name` is hardcoded `"free"`
- **Status:** PASS
- **Evidence:** `backend/app/schemas/user.py:23` — `tier_name: str = "free"` and `backend/app/services/user_service.py:89` — `tier_name="free"`
- **Test:** `test_get_profile_returns_full_profile` asserts `tier_name == "free"` (line 97)

### MH-09: `UserProfileRead.avatar_url` contains presigned MinIO URL (not raw object path)
- **Status:** PASS
- **Evidence:** `backend/app/services/user_service.py:70-78` — calls `_get_presigned_url(user_with_oauth.avatar_url)` to generate presigned URL
- **Test:** `test_get_profile_with_avatar_generates_presigned_url` asserts presigned URL returned (line 164)

### MH-10: `users_router` registered in `app/api/v1/__init__.py` under `/users` prefix
- **Status:** PASS
- **Evidence:** `backend/app/api/v1/__init__.py:7` — `from app.api.v1.users import router as users_router`, line 12 — `api_v1_router.include_router(users_router)`. Router prefix `/users` is set in `users.py:26`.

### MH-11: `pillow` dependency added to `pyproject.toml`
- **Status:** PASS
- **Evidence:** `backend/pyproject.toml:26` — `"pillow>=10.0.0",`

### MH-12: All endpoints require authentication via `get_current_active_user`
- **Status:** PASS
- **Evidence:** All 5 endpoints in `users.py` use `Depends(get_current_active_user)`:
  - GET /me (line 35)
  - PATCH /me (line 58)
  - POST /me/avatar (line 81)
  - DELETE /me/avatar (line 115)
  - DELETE /me (line 138)
- **Tests:** Unauthenticated tests all assert 401 (lines 67, 262, 365, 535)

### MH-13: Tests pass: `pytest tests/test_users.py -x -q` exits 0
- **Status:** PASS
- **Evidence:** `20 passed, 1 warning in 0.63s` — exit code 0

---

## 3. Plan 05-02 Must-Haves Verification

### MH-01: `POST /api/v1/users/me/avatar` — full avatar upload pipeline
- **Status:** PASS
- **Evidence:**
  - Endpoint: `backend/app/api/v1/users.py:78` — `@router.post("/me/avatar", response_model=AvatarUploadResponse)`
  - MIME validation: `user_service.py:132-136` — checks `_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}`
  - Size validation: `user_service.py:139-142` — checks `_MAX_FILE_SIZE = 2 * 1024 * 1024` (2MB)
  - Resize 200x200: `user_service.py:159` — `ImageOps.fit(img, self._AVATAR_SIZE, Image.LANCZOS)`
  - Resize 50x50: `user_service.py:165` — `ImageOps.fit(img, self._THUMB_SIZE, Image.LANCZOS)`
  - WebP conversion: `user_service.py:161,167` — `format="WebP"`
  - MinIO upload: `user_service.py:171-174` — uploads to `avatars/{uuid}/avatar.webp` and `avatar_thumb.webp`
  - Returns `AvatarUploadResponse`: `users.py:102-106` — with presigned URLs
- **Test:** `test_upload_avatar_valid_jpeg` asserts 200 with correct response shape (line 308-312)

### MH-02: `DELETE /api/v1/users/me/avatar` removes MinIO objects and clears `avatar_url`
- **Status:** PASS
- **Evidence:**
  - Endpoint: `backend/app/api/v1/users.py:112` — `@router.delete("/me/avatar", response_model=MessageResponse)`
  - Service: `user_service.py:187-209` — calls `delete_file()` for both sizes, sets `user.avatar_url = None`, calls `update()`
- **Test:** `test_remove_avatar_success` asserts 200, `test_remove_avatar_no_avatar` asserts 400 (lines 400, 419)

### MH-03: `DELETE /api/v1/users/me` — account deletion with verification, soft delete, session invalidation, cookie clearing
- **Status:** PASS
- **Evidence:**
  - Endpoint: `backend/app/api/v1/users.py:133` — `@router.delete("/me", response_model=MessageResponse)`
  - Password verification (local): `user_service.py:222-227` — `verify_password(confirmation.password, user.hashed_password)`
  - Email verification (OAuth): `user_service.py:229-233` — `confirmation.email.lower().strip() != user.email.lower()`
  - Deactivation: `user_service.py:236` — `user.is_active = False`
  - Soft delete: `user_service.py:237` — `await self._user_repo.soft_delete(user)` (sets `deleted_at`)
  - Session invalidation: `user_service.py:240` — `await invalidate_all_user_sessions(user.uuid)`
  - Cookie clearing: `users.py:155` — `clear_auth_cookies(response)`
- **Tests:** `test_delete_account_correct_password` asserts 200 + `is_active is False` (lines 454-457)

### MH-04: `delete_file()` async function in `app/infra/minio/client.py` using `run_in_executor`
- **Status:** PASS
- **Evidence:** `backend/app/infra/minio/client.py:134-156` — `async def delete_file(object_name: str) -> None:` with `loop.run_in_executor(None, partial(client.remove_object, ...))` pattern

### MH-05: Shared `clear_auth_cookies()` utility in `app/utils/cookies.py`
- **Status:** PASS
- **Evidence:**
  - Utility: `backend/app/utils/cookies.py:16` — `def clear_auth_cookies(response: Response) -> None:`
  - Used in auth.py: `auth.py:46` — `from app.utils.cookies import clear_auth_cookies`, line 199 — `clear_auth_cookies(response)`
  - Used in users.py: `users.py:21` — `from app.utils.cookies import clear_auth_cookies`, line 155 — `clear_auth_cookies(response)`
  - Old `_clear_auth_cookies` removed: grep confirms no `_clear_auth_cookies` in `auth.py`

### MH-06: Invalid file type returns 400, oversized file returns 400, wrong password returns 401
- **Status:** PASS
- **Evidence:**
  - Invalid MIME → `BadRequestError` (400): `user_service.py:133-136`
  - Oversized → `BadRequestError` (400): `user_service.py:139-142`
  - Wrong password → `UnauthorizedError` (401): `user_service.py:226-227`
- **Tests:** `test_upload_avatar_invalid_mime` asserts 400 (line 359), `test_upload_avatar_oversized` asserts 400 (line 337), `test_delete_account_wrong_password` asserts 401 (line 480)

### MH-07: After account deletion, user cannot authenticate (token invalidated)
- **Status:** PASS
- **Evidence:**
  - `user_service.py:236` — `user.is_active = False` (prevents future authentication)
  - `user_service.py:237` — `soft_delete(user)` sets `deleted_at` (soft-deleted users filtered by `_not_deleted`)
  - `user_service.py:240` — `invalidate_all_user_sessions(user.uuid)` — clears all Redis session tokens
  - `users.py:155` — `clear_auth_cookies(response)` — removes cookies from browser
- **Test:** `test_delete_account_correct_password` verifies `is_active is False` (line 457)

### MH-08: Tests pass: `pytest tests/test_users.py -x -q` exits 0
- **Status:** PASS
- **Evidence:** `20 passed, 1 warning in 0.63s` — exit code 0

---

## 4. Test Execution Results

```
$ cd backend && .venv/bin/python -m pytest tests/test_users.py -x -q
....................                                                     [100%]
20 passed, 1 warning in 0.63s
```

### Test Inventory (20 tests)

| # | Test Class | Test Name | Status |
|---|---|---|---|
| 1 | TestGetProfile | test_get_profile_unauthenticated | PASS |
| 2 | TestGetProfile | test_get_profile_returns_full_profile | PASS |
| 3 | TestGetProfile | test_get_profile_oauth_user_has_password_false | PASS |
| 4 | TestGetProfile | test_get_profile_with_avatar_generates_presigned_url | PASS |
| 5 | TestUpdateProfile | test_update_display_name_valid | PASS |
| 6 | TestUpdateProfile | test_update_display_name_too_short | PASS |
| 7 | TestUpdateProfile | test_update_display_name_too_long | PASS |
| 8 | TestUpdateProfile | test_update_display_name_invalid_chars | PASS |
| 9 | TestUpdateProfile | test_update_profile_unauthenticated | PASS |
| 10 | TestAvatarUpload | test_upload_avatar_valid_jpeg | PASS |
| 11 | TestAvatarUpload | test_upload_avatar_oversized | PASS |
| 12 | TestAvatarUpload | test_upload_avatar_invalid_mime | PASS |
| 13 | TestAvatarUpload | test_upload_avatar_unauthenticated | PASS |
| 14 | TestAvatarRemove | test_remove_avatar_success | PASS |
| 15 | TestAvatarRemove | test_remove_avatar_no_avatar | PASS |
| 16 | TestDeleteAccount | test_delete_account_correct_password | PASS |
| 17 | TestDeleteAccount | test_delete_account_wrong_password | PASS |
| 18 | TestDeleteAccount | test_delete_account_oauth_correct_email | PASS |
| 19 | TestDeleteAccount | test_delete_account_oauth_wrong_email | PASS |
| 20 | TestDeleteAccount | test_delete_account_unauthenticated | PASS |

---

## 5. Files Verified

| File | Exists | Content Verified |
|---|---|---|
| backend/app/schemas/user.py | YES | UserProfileRead, UserProfileUpdate, DeleteAccountRequest, AvatarUploadResponse |
| backend/app/services/user_service.py | YES | UserService with get_profile, update_profile, upload_avatar, remove_avatar, delete_account |
| backend/app/api/v1/users.py | YES | 5 endpoints: GET/PATCH/POST/DELETE /me, DELETE /me/avatar |
| backend/app/repositories/user_repository.py | YES | get_with_oauth_accounts with selectinload |
| backend/app/api/v1/__init__.py | YES | users_router registered |
| backend/app/utils/cookies.py | YES | clear_auth_cookies shared utility |
| backend/app/infra/minio/client.py | YES | delete_file async wrapper |
| backend/app/services/__init__.py | YES | UserService documented |
| backend/pyproject.toml | YES | pillow>=10.0.0 dependency |
| backend/tests/test_users.py | YES | 20 tests, all passing |

---

## 6. Known Issues (Pre-existing, Not Caused by Phase 05)

- `test_change_password_same_as_current_returns_422` in `test_change_password.py` — pre-existing failure from Phase 4, unrelated to Phase 5 changes. Does not affect Phase 5 verification.

---

## 7. Summary

| Metric | Value |
|---|---|
| Requirements covered | 3/3 (USER-01, USER-02, USER-04) |
| Plan 05-01 must_haves | 13/13 PASS |
| Plan 05-02 must_haves | 8/8 PASS |
| Total must_haves | 21/21 PASS |
| Tests passing | 20/20 |
| Overall verdict | **PASS** |

Phase 05 goal — "Complete user self-service — view/edit profile, avatar upload, and account deletion with soft delete grace period" — is fully achieved.

---
*Verified: 2026-04-11*
*Verification method: Manual code inspection + automated test execution*
