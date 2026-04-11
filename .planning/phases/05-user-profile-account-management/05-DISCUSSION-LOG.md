# Phase 5: User Profile & Account Management - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 05-user-profile-account-management
**Areas discussed:** Avatar upload, Account deletion, Profile API design, User service layer

---

## Avatar Upload

### Upload Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Server-side upload (Recommended) | Frontend sends multipart to backend → validate → resize → upload MinIO. Simple, controlled, costs backend bandwidth. | ✓ |
| Client-side presigned | Backend creates presigned PUT URL → frontend uploads directly to MinIO → callback. Saves bandwidth but more complex (CORS, client validation). | |

**User's choice:** Server-side upload
**Notes:** None

### File Limits

| Option | Description | Selected |
|--------|-------------|----------|
| 2MB, standard images (Recommended) | JPEG, PNG, WebP. Max 2MB. Backend validates MIME type + file size. | ✓ |
| 5MB, with GIF | JPEG, PNG, WebP, GIF (animated). Max 5MB. | |

**User's choice:** 2MB, standard images
**Notes:** None

### Resize Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-resize + thumbnail (Recommended) | Backend auto-resizes to 200x200 (main) and 50x50 (thumbnail). Both stored in MinIO. | ✓ |
| Keep original, CSS handle | Store original file, frontend uses CSS to display. | |

**User's choice:** Auto-resize + thumbnail
**Notes:** None

### Storage Path

| Option | Description | Selected |
|--------|-------------|----------|
| avatars/{user_uuid}/ (Recommended) | e.g., avatars/{user_uuid}/avatar.webp — overwrite on new upload. | ✓ |
| avatars/{user_uuid}/{timestamp}/ | e.g., avatars/{user_uuid}/{timestamp}.webp — keep history. | |

**User's choice:** avatars/{user_uuid}/ with overwrite
**Notes:** None

---

## Account Deletion

### Grace Period Duration

| Option | Description | Selected |
|--------|-------------|----------|
| 30 days (Recommended) | Keep data 30 days, then anonymize. Standard SaaS pattern. | ✓ |
| 14 days | Shorter, faster. | |
| 90 days | Maximum protection, more storage. | |

**User's choice:** 30 days selected initially, but user clarified approach below
**Notes:** User asked what "grace period" means — explanation provided.

### Login During Grace Period

| Option | Description | Selected |
|--------|-------------|----------|
| Block login immediately (Recommended) | is_active = false. User cannot login. Reactivation via support/admin. | |
| Allow login + self-cancel | User can still login and cancel deletion request. | |

**User's choice:** Custom — "User cannot access anything, but account data stays fully intact in the system including all user resources"
**Notes:** User clarified that deleted accounts should be fully preserved in the system, not anonymized or cleaned up. Account becomes inaccessible but data remains intact indefinitely.

### Data Handling After Grace Period

| Option | Description | Selected |
|--------|-------------|----------|
| Anonymize fields (Recommended) | email → deleted_{uuid}@anon, clear personal data, keep record for FK integrity. | |
| Hard delete | Remove record entirely. Requires CASCADE on all FKs. | |

**User's choice:** Custom — "Keep all account data completely intact, user just can't access or login or use any resources. But it remains whole in the system"
**Notes:** No anonymization, no hard delete, no grace period cleanup. Pure soft deactivation with full data retention. Admin can reactivate at any time.

### Deletion Confirmation

| Option | Description | Selected |
|--------|-------------|----------|
| Password + confirm (Recommended) | Enter password before deletion. OAuth-only users type "DELETE" or email. | ✓ |
| Simple confirm button | Just click confirm, no password required. | |

**User's choice:** Password + confirm
**Notes:** None

---

## Profile API Design

### Endpoint Namespace

| Option | Description | Selected |
|--------|-------------|----------|
| /users/me (Recommended) | GET /users/me, PATCH /users/me, DELETE /users/me, POST /users/me/avatar. Separate from auth. | ✓ |
| Extend /auth/me | Add PATCH and DELETE to existing /auth/me. Everything in auth namespace. | |

**User's choice:** /users/me
**Notes:** None

### Profile Response Data

| Option | Description | Selected |
|--------|-------------|----------|
| Full profile + tier placeholder (Recommended) | All current fields + tier_name (placeholder "free" until Phase 6). | ✓ |
| Keep current | Only fields in UserPublicRead, no tier. | |

**User's choice:** Full profile + tier placeholder
**Notes:** None

### Editable Fields

| Option | Description | Selected |
|--------|-------------|----------|
| display_name + avatar only (Recommended) | Only display_name and avatar (Phase 5). Email change requires re-verify (future). | ✓ |
| Including email | Also allow email editing (needs re-verification flow). | |

**User's choice:** display_name + avatar only
**Notes:** None

### /auth/me vs /users/me Coexistence

| Option | Description | Selected |
|--------|-------------|----------|
| Keep both (Recommended) | /auth/me returns lightweight UserPublicRead. /users/me returns full UserProfileRead. Different purposes. | ✓ |
| Replace /auth/me | Remove /auth/me, move everything to /users/me. | |

**User's choice:** Keep both
**Notes:** None

---

## User Service Layer

### Service Organization

| Option | Description | Selected |
|--------|-------------|----------|
| Separate UserService (Recommended) | New UserService(db) — same pattern as AuthService. Handles profile, avatar, account deletion. | ✓ |
| Extend AuthService | Add profile methods to AuthService. Simpler but service becomes bloated. | |

**User's choice:** Separate UserService
**Notes:** None

### display_name Validation

| Option | Description | Selected |
|--------|-------------|----------|
| 2-50, basic chars (Recommended) | 2-50 chars, letters + digits + spaces + hyphens. Strip whitespace. | ✓ |
| 1-100, Unicode + emoji | 1-100 chars, allow emoji and full Unicode. More flexible. | |

**User's choice:** 2-50, basic chars
**Notes:** None

### Router File

| Option | Description | Selected |
|--------|-------------|----------|
| New users.py (Recommended) | backend/app/api/v1/users.py. Mount under /api/v1/users. Per STRUCTURE.md. | ✓ |
| In auth.py | Add routes to existing auth.py. | |

**User's choice:** New users.py
**Notes:** None

### Schema File

| Option | Description | Selected |
|--------|-------------|----------|
| New schemas/user.py (Recommended) | UserProfileRead, UserProfileUpdate, DeleteAccountRequest, AvatarUploadResponse. Keep UserPublicRead in auth.py. | ✓ |
| In schemas/auth.py | Add schemas to existing auth.py. | |

**User's choice:** New schemas/user.py
**Notes:** None

---

## Claude's Discretion

- Image processing library choice (Pillow vs other)
- WebP conversion quality settings
- Presigned URL expiry duration for avatar URLs
- Rate limits for profile update and avatar upload endpoints
- Whether to add locale preference field to User model
- Exact error messages for validation failures

## Deferred Ideas

None — discussion stayed within phase scope
