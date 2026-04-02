---
phase: 1
slug: backend-core-infrastructure
status: draft
nyquist_compliant: false
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 1 | INFRA-01 | unit | `uv run pytest tests/test_app.py -v` | ❌ W0 | ⬜ pending |
| TBD | 02 | 1 | INFRA-09 | unit | `uv run pytest tests/test_config.py -v` | ❌ W0 | ⬜ pending |
| TBD | 03 | 1 | INFRA-02 | integration | `uv run pytest tests/test_database.py -v` | ❌ W0 | ⬜ pending |
| TBD | 03 | 1 | INFRA-14 | unit | `uv run pytest tests/test_models.py -v` | ❌ W0 | ⬜ pending |
| TBD | 03 | 1 | INFRA-15 | unit | `uv run pytest tests/test_models.py -v` | ❌ W0 | ⬜ pending |
| TBD | 04 | 2 | INFRA-03 | integration | `uv run pytest tests/test_redis.py -v` | ❌ W0 | ⬜ pending |
| TBD | 04 | 2 | INFRA-04 | integration | `uv run pytest tests/test_minio.py -v` | ❌ W0 | ⬜ pending |
| TBD | 05 | 2 | INFRA-11 | manual | `docker compose -f docker/docker-compose.middleware.yaml up -d` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/conftest.py` — shared fixtures (async session, test client, cleanup)
- [ ] `backend/tests/test_app.py` — FastAPI app startup smoke test
- [ ] `backend/tests/test_config.py` — config loading and validation tests
- [ ] `backend/tests/test_models.py` — dual-ID + soft-delete mixin tests
- [ ] `backend/tests/test_database.py` — database connection + Alembic migration tests
- [ ] `backend/tests/test_redis.py` — Redis 3-namespace isolation tests
- [ ] `backend/tests/test_minio.py` — MinIO presigned URL generation tests
- [ ] pytest + pytest-asyncio + httpx installed in dev dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker Compose starts all services | INFRA-11 | Requires Docker daemon | `docker compose -f docker/docker-compose.middleware.yaml up -d && docker compose -f docker/docker-compose.middleware.yaml ps` — all services healthy |
| MinIO presigned upload works end-to-end | INFRA-04 | Requires running MinIO + curl | Generate presigned PUT URL, `curl -T testfile.txt <url>`, verify 200 |
| Alembic migration applies cleanly | INFRA-02 | Requires running database | `cd backend && uv run alembic upgrade head && uv run alembic check` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
