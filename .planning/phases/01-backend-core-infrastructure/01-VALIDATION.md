---
phase: 1
slug: backend-core-infrastructure
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-02
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio |
| **Config file** | `backend/pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `cd backend && uv run pytest tests/ -x -q --tb=short` |
| **Full suite command** | `cd backend && uv run pytest tests/ -v --tb=long` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -v --tb=long`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 1.1 | 01 | 1 | INFRA-01 | unit | `uv run python -c "import fastapi"` | ⬜ pending |
| 1.2 | 01 | 1 | INFRA-01 | unit | `ls backend/app/__init__.py` | ⬜ pending |
| 1.3 | 01 | 1 | INFRA-09 | unit | `uv run python -c "from app.core.config import settings"` | ⬜ pending |
| 1.4 | 01 | 1 | INFRA-09 | unit | `grep POSTGRES_HOST .env.example` | ⬜ pending |
| 1.5 | 01 | 1 | INFRA-01 | unit | `uv run python -c "from app.main import app"` | ⬜ pending |
| 1.6 | 01 | 1 | INFRA-01 | unit | `cat .pre-commit-config.yaml` | ⬜ pending |
| 2.1 | 02 | 1 | INFRA-11 | manual | `docker compose -f docker/docker-compose.middleware.yaml config` | ⬜ pending |
| 2.2 | 02 | 1 | INFRA-11 | manual | `docker compose -f docker/docker-compose.yaml config` | ⬜ pending |
| 2.3 | 02 | 1 | INFRA-11 | unit | `grep "docker/volumes/" .gitignore` | ⬜ pending |
| 3.1 | 03 | 2 | INFRA-14, INFRA-15 | unit | `uv run pytest tests/test_models.py -v` | ⬜ pending |
| 3.2 | 03 | 2 | INFRA-02 | unit | `uv run python -c "from app.extensions.ext_database import init"` | ⬜ pending |
| 3.3 | 03 | 2 | INFRA-02 | integration | `uv run alembic check` | ⬜ pending |
| 3.4 | 03 | 2 | INFRA-02 | unit | `grep "ext_database.init" backend/app/main.py` | ⬜ pending |
| 4.1 | 04 | 2 | INFRA-03 | unit | `uv run python -c "from app.extensions.ext_redis import cache_client"` | ⬜ pending |
| 4.2 | 04 | 2 | INFRA-04 | unit | `uv run python -c "from app.extensions.ext_minio import presigned_get_url"` | ⬜ pending |
| 4.3 | 04 | 2 | INFRA-03, INFRA-04 | unit | `grep "ext_redis.init" backend/app/main.py` | ⬜ pending |
| 5.1 | 05 | 3 | INFRA-11 | unit | `make help` | ⬜ pending |
| 5.2 | 05 | 3 | ALL | unit | `uv run pytest tests/conftest.py --collect-only` | ⬜ pending |
| 5.3 | 05 | 3 | INFRA-09, INFRA-14, INFRA-15 | unit | `uv run pytest tests/test_config.py tests/test_models.py -v` | ⬜ pending |
| 5.4 | 05 | 3 | INFRA-01 | unit | `uv run pytest tests/test_app.py -v` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/pyproject.toml` — pytest + pytest-asyncio + httpx in dev dependencies (Plan 01, Task 1.1)
- [ ] `backend/tests/__init__.py` — empty package init (Plan 01, Task 1.2)
- [ ] `backend/tests/conftest.py` — shared fixtures with extension mocks (Plan 05, Task 5.2)
- [ ] `backend/tests/test_app.py` — FastAPI app startup smoke test (Plan 05, Task 5.4)
- [ ] `backend/tests/test_config.py` — config loading and validation tests (Plan 05, Task 5.3)
- [ ] `backend/tests/test_models.py` — dual-ID + soft-delete mixin tests (Plan 05, Task 5.3)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker Compose starts all services | INFRA-11 | Requires Docker daemon | `docker compose -f docker/docker-compose.middleware.yaml up -d && docker compose -f docker/docker-compose.middleware.yaml ps` — all services healthy |
| MinIO presigned upload works end-to-end | INFRA-04 | Requires running MinIO + curl | Generate presigned PUT URL, `curl -T testfile.txt <url>`, verify 200 |
| Alembic migration applies cleanly | INFRA-02 | Requires running database | `cd backend && uv run alembic upgrade head && uv run alembic check` |
| Full dev-setup flow | INFRA-11 | Requires Docker + network | `make dev-setup` — all services start, migrations apply |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending execution
