# Phase 5: User Profile & Account Management - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete user self-service — view/edit profile, avatar upload via MinIO, and account deletion (soft deactivation with full data retention). This phase builds on Phase 3-4 auth foundation (User model, JWT cookies, password management) and Phase 1 MinIO infrastructure to deliver USER-01, USER-02, and USER-04.

</domain>

<decisions>
## Implementation Decisions

### Avatar Upload
- **D-01:** Server-side upload flow — frontend sends multipart form data to backend → backend validates MIME type + file size → resizes → uploads to MinIO. No client-side presigned upload.
- **D-02:** File limits — max 2MB, allowed formats: JPEG, PNG, WebP. Backend validates both MIME type and file size before processing.
- **D-03:** Auto-resize with thumbnail — backend resizes to 200x200 (main avatar) and 50x50 (thumbnail). Both sizes stored in MinIO. Original file is not preserved.
- **D-04:** MinIO storage path — `avatars/{user_uuid}/avatar.webp` and `avatars/{user_uuid}/avatar_thumb.webp`. Overwritten on new upload. Converting to WebP for consistent format and smaller size.
- **D-05:** Avatar URL in profile — `avatar_url` field stores the MinIO object path (not presigned URL). Presigned GET URL generated on-demand when profile is requested. This allows URL expiry control and avoids stale URLs.

### Account Deletion
- **D-06:** Soft deactivation, no data deletion — user requests deletion → `is_active = false`, `deleted_at = now()`. User cannot login or access any resources. ALL data remains intact in the system (profile, projects, messages, files).
- **D-07:** No grace period cleanup — no scheduled task to anonymize or hard-delete. Data persists indefinitely. Admin can reactivate by setting `is_active = true`, `deleted_at = null`.
- **D-08:** Confirmation requires password — user must enter current password to confirm account deletion. For OAuth-only users (no password set), user types their email address as confirmation.
- **D-09:** Session invalidation on delete — all token families for the user are invalidated in Redis immediately (reuses `invalidate_all_user_sessions()` from Phase 4). Existing sessions are force-logged out.

### Profile API Design
- **D-10:** Separate `/users/me` namespace — profile endpoints under `/api/v1/users/`:
  - GET /users/me (view full profile)
  - PATCH /users/me (edit profile)
  - DELETE /users/me (delete account)
  - POST /users/me/avatar (upload avatar)
  - DELETE /users/me/avatar (remove avatar)
- **D-11:** Keep both /auth/me and /users/me — `/auth/me` remains as-is (lightweight, returns `UserPublicRead` for auth checks). `/users/me` returns `UserProfileRead` (full profile with tier info). Two endpoints, two purposes.
- **D-12:** Full profile response with tier placeholder — `UserProfileRead` includes all current fields + `tier_name: str = "free"` (hardcoded placeholder until Phase 6 Tier System). Also includes `has_password: bool` (whether user has a password set) and `oauth_providers: list[str]` (linked OAuth provider names).
- **D-13:** Editable fields: display_name and avatar only — PATCH /users/me accepts `display_name` (text) only. Avatar is uploaded via separate POST /users/me/avatar endpoint. Email change is out of scope (requires re-verification flow — future phase).

### User Service Layer
- **D-14:** Separate UserService(db) — new service class following AuthService pattern (constructor DI, uses UserRepository). Handles: get_profile, update_profile, upload_avatar, remove_avatar, delete_account.
- **D-15:** display_name validation — 2-50 characters, allowed: letters (unicode), digits, spaces, hyphens, underscores. Strip leading/trailing whitespace. Validated in Pydantic schema.
- **D-16:** New router file — `backend/app/api/v1/users.py`. Mounted under `/api/v1/users` prefix. All endpoints require authentication (get_current_user dependency).
- **D-17:** New schema file — `backend/app/schemas/user.py` with:
  - `UserProfileRead` — full profile response (extends UserPublicRead with tier_name, has_password, oauth_providers)
  - `UserProfileUpdate` — partial update (display_name only, all fields optional)
  - `DeleteAccountRequest` — password or email confirmation
  - `AvatarUploadResponse` — avatar_url and thumbnail_url after upload

### Claude's Discretion
- Image processing library choice (Pillow vs other)
- Exact WebP conversion quality settings
- Presigned URL expiry duration for avatar URLs
- Rate limits for profile update and avatar upload endpoints
- Whether to add `locale` preference field to User model (for future i18n)
- Exact error messages for validation failures

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Documentation
- `.planning/ROADMAP.md` — Phase 5 requirements (USER-01, USER-02, USER-04) and success criteria
- `.planning/REQUIREMENTS.md` — Full requirement details for USER-01 through USER-04
- `.planning/codebase/STRUCTURE.md` — Target directory layout (users.py router, user.py schemas)
- `.planning/codebase/CONVENTIONS.md` — Code style, naming conventions

### Existing Code (Phase 1-4 output)
- `backend/app/models/user.py` — User model with display_name, avatar_url fields already defined; SoftDeleteMixin with deleted_at
- `backend/app/models/base.py` — Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
- `backend/app/repositories/user_repository.py` — UserRepository(BaseRepository[User]) with generic get(**filters) and create_user()
- `backend/app/repositories/base.py` — BaseRepository with get/get_multi/create/update/soft_delete/delete
- `backend/app/services/auth_service.py` — AuthService class pattern (constructor DI template for UserService)
- `backend/app/core/security.py` — invalidate_all_user_sessions() for session cleanup on account deletion; verify_password() for delete confirmation
- `backend/app/infra/minio/client.py` — MinIO singleton with upload_file(), presigned_get_url(), presigned_put_url()
- `backend/app/api/v1/auth.py` — Existing auth routes with get_current_user dependency pattern
- `backend/app/api/dependencies.py` — Auth dependencies (get_current_user, require_verified)
- `backend/app/schemas/auth.py` — UserPublicRead schema (reference for UserProfileRead extension)
- `backend/app/utils/rate_limit.py` — check_rate_limit() utility for endpoint rate limiting

### Prior Phase Context
- `.planning/phases/01-backend-core-infrastructure/01-CONTEXT.md` — MinIO setup, dual-ID strategy, modular settings
- `.planning/phases/03-authentication-core-flows/03-CONTEXT.md` — User model design, auth patterns, JWT strategy
- `.planning/phases/04-authentication-advanced-password-management/04-CONTEXT.md` — Password management, session invalidation, OAuth patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `User` model: `display_name` and `avatar_url` fields already exist — no migration needed for basic profile
- `SoftDeleteMixin`: `soft_delete()` method sets `deleted_at` — reuse for account deletion
- `MinIO client`: `upload_file()` for avatar storage, `presigned_get_url()` for serving avatar URLs
- `UserRepository`: `get(**filters)`, `update()`, `soft_delete()` — all needed for profile operations
- `invalidate_all_user_sessions()`: Reuse for session cleanup on account deletion
- `verify_password()`: Reuse for delete confirmation password check
- `get_current_user` dependency: Reuse for all /users/* endpoints

### Established Patterns
- Class-based services with constructor DI: `AuthService(db)` → `UserService(db)`
- Repository pattern: services delegate data access to repositories
- Router mounting under `/api/v1/` prefix with router aggregator in `v1/__init__.py`
- Pydantic v2 schemas with ConfigDict (Read/Create/Update separation)
- HttpOnly cookie auth with JWT — all /users/* endpoints will use same auth dependency

### Integration Points
- `api/v1/__init__.py`: Mount new users_router alongside auth_router and health_router
- `services/__init__.py`: Export UserService
- `schemas/__init__.py`: Export new user profile schemas
- Phase 6 (Tier System) will replace the hardcoded `tier_name: "free"` with actual tier lookup
- Phase 9 (Frontend) will consume /users/me endpoints for profile page

</code_context>

<specifics>
## Specific Ideas

- **Follow AuthService pattern exactly** — UserService(db) creates UserRepository in __init__, exposes async methods, raises domain exceptions (NotFoundError, BadRequestError)
- **Avatar processing pipeline** — validate MIME → read bytes → resize with Pillow → convert to WebP → upload to MinIO → update user.avatar_url
- **Soft deactivation, not deletion** — user explicitly chose to keep ALL data intact. No anonymization, no scheduled cleanup. Admin reactivation is the recovery path.
- **OAuth-only delete confirmation** — since OAuth users may not have a password, they type their email address instead

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-user-profile-account-management*
*Context gathered: 2026-04-11*
