---
status: issues_found
phase: 05
depth: standard
files_reviewed: 12
findings:
  critical: 1
  warning: 4
  info: 4
  total: 9
---

# Phase 05 — Code Review: User Profile & Account Management

**Reviewer:** Claude Opus 4.6  
**Date:** 2026-04-11  
**Scope:** 12 files changed in Phase 05 (user profile, avatar, account deletion)

---

## Critical

### CR-01: [critical] Pillow decompression bomb — no `MAX_IMAGE_PIXELS` guard
- **File:** backend/app/services/user_service.py
- **Line:** 148–150
- **Issue:** The avatar upload pipeline validates file size (≤2MB on disk) but does not limit the decompressed pixel count. A crafted image can be small on disk (e.g., a highly-compressed PNG with millions of pixels) yet explode into gigabytes of RAM when Pillow decodes it. `Image.open()` + `verify()` + re-open still loads full pixel data into memory. Pillow's default `MAX_IMAGE_PIXELS` (178 million) may be too generous for a 200×200 avatar context. An attacker can submit repeated requests within the 5-per-minute rate limit to exhaust server memory.
- **Fix:** Set `Image.MAX_IMAGE_PIXELS` to a sensible cap (e.g., 4096 × 4096 = 16.7M) at module level, **or** check `img.size` after opening and reject images with width or height exceeding a threshold (e.g., 4096 px). Example:
  ```python
  img = Image.open(io.BytesIO(file_data))
  if img.width > 4096 or img.height > 4096:
      raise BadRequestError(detail="Image dimensions too large (max 4096×4096)")
  ```

---

## Warnings

### CR-02: [warning] `presigned_get_url` and `presigned_put_url` are synchronous but called in async context
- **File:** backend/app/infra/minio/client.py
- **Line:** 52–73, 76–97
- **Issue:** The docstring says "presigned URL generation is local crypto (no network I/O)" which is mostly true for MinIO's Python SDK. However, `presigned_get_url` is called directly (not via `run_in_executor`) inside the async `UserService.upload_avatar` (line 181–182 of user_service.py) and `UserService.get_profile` (line 72). If the MinIO SDK ever performs a credential refresh or clock-sync network call during presigning, this blocks the event loop. Low risk today, but worth noting.
- **Fix:** Either wrap presigned URL calls in `run_in_executor` (consistent with `upload_file` / `delete_file`), or document the assumption that presigning is always CPU-only with a comment + test assertion.

### CR-03: [warning] `update_profile` commits even when no fields changed
- **File:** backend/app/services/user_service.py
- **Line:** 94–106
- **Issue:** If the PATCH request body is `{}` (empty), `UserProfileUpdate` validates with `display_name=None`. The method then skips the `if data.display_name is not None` branch but still calls `self._user_repo.update(user)`, which runs `session.commit()` + `session.refresh()` — an unnecessary database round-trip on every empty PATCH.
- **Fix:** Track whether any field was actually modified and skip the `update()` call if nothing changed:
  ```python
  if data.display_name is not None:
      # ... set value ...
      return await self._user_repo.update(user)
  return user  # nothing to update
  ```

### CR-04: [warning] Broad exception catch hides actual image parsing errors
- **File:** backend/app/services/user_service.py
- **Line:** 151
- **Issue:** The except clause `except (UnidentifiedImageError, Exception)` catches **all** exceptions (since `Exception` is a superclass of everything). This means a Pillow internal bug, an `OSError` from disk, or even a `MemoryError` would be silently converted into a generic `BadRequestError("Invalid image file")`. This makes debugging production issues very difficult.
- **Fix:** Narrow the exception types:
  ```python
  except (UnidentifiedImageError, OSError, SyntaxError) as exc:
      raise BadRequestError(detail="Invalid image file") from exc
  ```
  These three cover all realistic Pillow decoding failures.

### CR-05: [warning] Avatar file data read into memory without server-side size limit enforcement
- **File:** backend/app/api/v1/users.py
- **Line:** 95
- **Issue:** `file_data = await file.read()` reads the entire uploaded file into memory before checking file size in `UserService.upload_avatar`. If FastAPI has no `max_request_body_size` configured (Uvicorn default is unlimited), an attacker can POST a 1GB file and consume server memory before the 2MB check in the service layer rejects it. The rate limit (5/min) only partially mitigates this.
- **Fix:** Either configure Uvicorn/Gunicorn `--limit-request-body` to a reasonable max (e.g., 5MB), or read the file in chunks and abort early when the 2MB threshold is exceeded:
  ```python
  chunks = []
  total = 0
  async for chunk in file:
      total += len(chunk)
      if total > 2 * 1024 * 1024:
          raise BadRequestError(detail="File too large (max 2MB)")
      chunks.append(chunk)
  file_data = b"".join(chunks)
  ```

---

## Info

### CR-06: [info] `display_name` regex pattern `^[\w\s\-]+$` behavior depends on Python regex flags
- **File:** backend/app/schemas/user.py
- **Line:** 35
- **Issue:** In Python's `re` module, `\w` matches Unicode word characters by default (letters, digits, underscore from any script). This means display names like `Nguyễn Văn Minh` or `田中太郎` pass validation, which may be intentional. However, the test `test_update_display_name_invalid_chars` tests `Name@#$!` as rejected — make sure the team understands that CJK, Arabic, Cyrillic, etc. are all accepted.
- **Fix:** If the intent is ASCII-only, use `^[a-zA-Z0-9_\s\-]+$`. If Unicode is intentional (likely for a multi-language product), document this in the schema docstring or comment.

### CR-07: [info] `importlib.import_module` indirection for MinIO client is fragile
- **File:** backend/app/services/user_service.py
- **Line:** 32
- **Issue:** Using `importlib.import_module("app.infra.minio.client")` at module level to avoid a naming collision adds a layer of indirection that is unusual and can confuse IDE tools, type checkers, and new developers. The comment explains the rationale (avoiding name collision with the module-level `client` singleton), but a simpler approach exists.
- **Fix:** Use a direct import with an alias:
  ```python
  from app.infra.minio import client as minio_client
  # or
  import app.infra.minio.client as minio_ops
  ```
  This is simpler, type-checker friendly, and avoids `importlib` overhead.

### CR-08: [info] Test cleanup uses `pop` instead of `finally` — override may leak on test failure
- **File:** backend/tests/test_users.py
- **Line:** 91 (and many others)
- **Issue:** All test methods follow this pattern:
  ```python
  app.dependency_overrides[dep] = lambda: mock
  # ... make request ...
  app.dependency_overrides.pop(dep, None)  # cleanup
  ```
  If the request raises an unexpected exception, the `pop` call is skipped and the override leaks to subsequent tests. This could cause flaky test behavior.
- **Fix:** Use `try/finally` or a pytest fixture for override cleanup:
  ```python
  try:
      response = await async_client.get(...)
  finally:
      app.dependency_overrides.pop(dep, None)
  ```

### CR-09: [info] Unused import `ASGITransport` in test file
- **File:** backend/tests/test_users.py
- **Line:** 9
- **Issue:** `ASGITransport` is imported but never used in this file (it's used in `conftest.py` instead). This triggers ruff rule F401 (unused import).
- **Fix:** Remove the unused import: `from httpx import ASGITransport, AsyncClient` → `from httpx import AsyncClient`.

---

## Summary

The implementation is well-structured with clear separation between router, service, and repository layers. Security fundamentals are solid (rate limiting, CSRF protection, password verification for account deletion, HttpOnly cookies). The main concern is the **decompression bomb** vulnerability (CR-01) which should be addressed before production. The remaining warnings are correctness and robustness improvements that can be addressed in a follow-up.

| Category | Count |
|----------|-------|
| Critical | 1 |
| Warning  | 4 |
| Info     | 4 |
| **Total** | **9** |
