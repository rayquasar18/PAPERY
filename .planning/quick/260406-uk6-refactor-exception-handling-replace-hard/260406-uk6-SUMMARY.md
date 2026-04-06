# Quick Task Summary: 260406-uk6

**Task:** Refactor Exception Handling — Replace Hardcoded Error Map
**Type:** refactor
**Branch:** `develop`
**Status:** ✅ Complete
**Commit:** `d0d49e1`

---

## What Changed

### Task 1: PaperyHTTPException + convenience subclasses
**File:** `backend/app/core/exceptions/__init__.py`

- Created `PaperyHTTPException(HTTPException)` with `error_code: str` attribute
- Created 7 convenience subclasses: `BadRequestError`, `UnauthorizedError`, `ForbiddenError`, `NotFoundError`, `ConflictError`, `RateLimitedError`, `InternalError`
- Each subclass sets default `status_code` + `error_code`, accepts optional `detail` and `headers`
- All subclasses allow `error_code` override via keyword arg for domain-specific codes
- Moved `HTTP_STATUS_ERROR_CODE_MAP` constant here as the fallback mapping

### Task 2: Exception handlers module
**File:** `backend/app/core/exceptions/handlers.py` (new)

- Moved `http_exception_handler`, `validation_error_handler`, `unhandled_exception_handler` from `main.py`
- Moved `_get_request_id()` helper (private to this module)
- Added `register_exception_handlers(app)` wiring function
- `http_exception_handler` now checks `isinstance(exc, PaperyHTTPException)` → uses `exc.error_code` directly; otherwise falls back to `HTTP_STATUS_ERROR_CODE_MAP`

### Task 3: Slim main.py + updated tests
**File:** `backend/app/main.py`

- Removed ~50 lines of inline exception handling logic
- Replaced with single `register_exception_handlers(app)` call
- Removed unused imports: `RequestValidationError`, `JSONResponse`, `StarletteHTTPException`, `Request`, `ErrorResponse`

**File:** `backend/tests/test_exceptions.py`

- Added `TestPaperyHTTPException` class (5 tests): construction, default detail, headers, isinstance checks
- Added `TestConvenienceSubclasses` class (11 tests): each subclass defaults, headers, error_code override, isinstance chain
- Retained `TestErrorResponse` class (4 tests): unchanged schema tests

---

## Validation

```
31 passed in 0.44s
```

- All 20 exception tests pass (new)
- All 11 health/integration tests pass (unchanged)
- 404/405 error format integration tests confirm backward compatibility

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| PaperyHTTPException inherits HTTPException | Yes | IS-A relationship; FastAPI catches it natively |
| 7 convenience subclasses | Yes | `raise NotFoundError("msg")` >> `raise PaperyHTTPException(404, "NOT_FOUND", "msg")` |
| error_code overridable on subclasses | keyword arg | `raise NotFoundError("...", error_code="PROJECT_NOT_FOUND")` for domain-specific codes |
| register_exception_handlers() pattern | Function call | main.py stays clean — single line to wire all handlers |
| Fallback map preserved | HTTP_STATUS_ERROR_CODE_MAP | Plain HTTPException from middleware/deps still gets proper error_code |

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `backend/app/core/exceptions/__init__.py` | Rewritten | 155 |
| `backend/app/core/exceptions/handlers.py` | Created | 93 |
| `backend/app/main.py` | Slimmed | 70 (was 152) |
| `backend/tests/test_exceptions.py` | Rewritten | 158 |
