---
status: partial
phase: 01-backend-core-infrastructure
source: [01-VERIFICATION.md]
started: 2026-04-02T05:40:00Z
updated: 2026-04-02T05:40:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Docker Compose middleware starts all 3 services
expected: All containers start, healthchecks pass (healthy state within 30s)
command: cd docker && cp middleware.env.example middleware.env && docker compose -f docker-compose.middleware.yaml -p papery-dev up -d
result: [pending]

### 2. FastAPI app starts and responds when middleware is running
expected: Startup logs show extensions connected; curl http://localhost:8000/api/v1/health returns JSON
command: cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
result: [pending]

### 3. Alembic generates and applies migrations
expected: alembic heads returns no heads (no models yet); no errors
command: cd backend && uv run alembic heads && uv run alembic upgrade head
result: [pending]

### 4. Redis 3-namespace isolation verified end-to-end
expected: Logs show 3 separate ping() calls for cache(db=0), queue(db=1), rate_limit(db=2)
result: [pending]

### 5. MinIO presigned upload URL functional
expected: Returns signed URL with X-Amz-Signature= parameter and expiry ~1800s
result: [pending]

### 6. make dev-setup full automation works
expected: Copies .env files, starts docker middleware, runs uv sync, runs alembic upgrade — no errors
command: make dev-setup
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
