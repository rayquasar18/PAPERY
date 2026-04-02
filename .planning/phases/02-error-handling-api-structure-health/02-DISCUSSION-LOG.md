# Phase 2: Error Handling, API Structure & Health - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 02-error-handling-api-structure-health
**Areas discussed:** Error response format, Exception hierarchy, Health check depth, Production Docker

---

## Error Response Format

| Option | Description | Selected |
|--------|-------------|----------|
| Custom flat format | { success, error_code, message, detail, request_id } — frontend-friendly, error_code catalog, i18n-ready | ✓ |
| RFC 7807 Problem Details | application/problem+json — IETF standard with type, title, status, detail, instance | |

**User's choice:** Custom flat format
**Notes:** PAPERY is internal SaaS with single Next.js frontend — RFC 7807 adds friction without interop benefit. error_code serves as machine-readable key for i18n.

---

## Exception Hierarchy

| Option | Description | Selected |
|--------|-------------|----------|
| Domain-grouped | Base PaperyError → ResourceNotFoundError, AuthError, AccessDeniedError, etc. Each carries status_code + error_code + detail. 1 handler in main.py | ✓ |
| Flat HTTP-status | NotFoundException, UnauthorizedException, etc. 1 class per HTTP status. N handlers in main.py | |

**User's choice:** Domain-grouped
**Notes:** Matches layered architecture — CRUD/services raise domain exceptions, single catch-all handler. Scales across 8+ phases without touching main.py.

---

## Health Check Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Binary, no cache | 200/503, timeout 2-3s per service, no result caching. Simple, correct for VPS + Docker Compose | ✓ |
| Degraded + cache | 200 healthy / 200 degraded / 503 unhealthy, cache 5s TTL | |

**User's choice:** Follow Dify's pattern — binary healthy/unhealthy
**Notes:** User explicitly requested following Dify's approach. Also requested DDD-style flat directory structure (models, api, schemas, repository, services, core, extensions, config) instead of domain-module grouping. This was noted as a cross-cutting architectural decision affecting Phase 2 and beyond.

---

## Production Docker

| Option | Description | Selected |
|--------|-------------|----------|
| Gunicorn + slim + 2-stage | gunicorn + uvicorn-worker, WEB_CONCURRENCY=2, python:3.12-slim, 2-stage multi-stage build | ✓ |
| Uvicorn standalone + slim | uvicorn --workers N, python:3.12-slim, 2-stage build | |

**User's choice:** Gunicorn + slim + 2-stage
**Notes:** Follows Dify pattern. gunicorn provides process supervision, graceful restart, zero-downtime. uvicorn-worker package (by Kludex) replaces deprecated uvicorn.workers.

---

## Claude's Discretion

- Request ID generation strategy
- Exact error_code naming convention
- Exception class convenience factory methods
- Logging integration with error responses
- OpenAPI schema annotations

## Deferred Ideas

None — discussion stayed within phase scope
