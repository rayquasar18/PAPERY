# Research: Docker Compose Split Setup for Development

**Researcher:** Claude
**Date:** 2026-04-02
**Requirement:** INFRA-11
**Decisions:** D-12 (Split Docker Compose), D-13 (Split Dockerfiles), D-14 (Makefile)

---

## 1. Split Strategy Overview

Two compose files under `docker/`:

| File | Purpose | When to use |
|------|---------|-------------|
| `docker-compose.middleware.yaml` | PostgreSQL + Redis + MinIO only | Daily dev — run middleware in containers, backend/frontend locally with hot-reload |
| `docker-compose.yaml` | Full stack (api + worker + middleware + nginx) | CI, staging, production, or testing full integration |

**Key insight from Dify:** The middleware file uses a separate `middleware.env` for service-specific vars, while the full stack uses the root `.env`. PAPERY simplifies this — single `.env.example` at root (decision D-17), Docker Compose reads from `docker/.env` (symlinked or copied from root).

---

## 2. docker-compose.middleware.yaml — Service Definitions

### 2.1 PostgreSQL 17

```yaml
services:
  postgres:
    image: postgres:17-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-papery}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-papery_dev_secret}
      POSTGRES_DB: ${POSTGRES_DB:-papery}
      PGDATA: /var/lib/postgresql/data/pgdata
    command: >
      postgres
        -c max_connections=${POSTGRES_MAX_CONNECTIONS:-100}
        -c shared_buffers=${POSTGRES_SHARED_BUFFERS:-128MB}
        -c work_mem=${POSTGRES_WORK_MEM:-4MB}
        -c maintenance_work_mem=${POSTGRES_MAINTENANCE_WORK_MEM:-64MB}
        -c effective_cache_size=${POSTGRES_EFFECTIVE_CACHE_SIZE:-512MB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "${EXPOSE_POSTGRES_PORT:-5432}:5432"
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "${POSTGRES_USER:-papery}", "-d", "${POSTGRES_DB:-papery}"]
      interval: 5s
      timeout: 3s
      retries: 15
      start_period: 10s
```

**Notes:**
- `postgres:17-alpine` — minimal image, PG 17 for latest JSON/performance improvements
- `pg_isready` is the standard health check — no extra packages needed
- `unless-stopped` for dev (not `always`) — respects manual stops but survives reboots
- Named volume `postgres_data` (not bind mount) — better performance on macOS, survives `docker compose down`
- Performance params via `-c` flags — tunable per environment without custom `postgresql.conf`
- `start_period` gives PG time to initialize before health checks begin

### 2.2 Redis 7

```yaml
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: >
      redis-server
        --requirepass ${REDIS_PASSWORD:-papery_dev_secret}
        --maxmemory 256mb
        --maxmemory-policy allkeys-lru
        --databases 4
    volumes:
      - redis_data:/data
    ports:
      - "${EXPOSE_REDIS_PORT:-6379}:6379"
    healthcheck:
      test: ["CMD-SHELL", "redis-cli -a ${REDIS_PASSWORD:-papery_dev_secret} ping | grep -q PONG"]
      interval: 5s
      timeout: 3s
      retries: 10
```

**Notes:**
- `--databases 4` — supports namespace isolation: db0=cache, db1=queue, db2=rate_limit, db3=token_blacklist (per INFRA-03)
- `allkeys-lru` eviction for dev safety — prevents OOM
- Health check uses `redis-cli ping` — simple and reliable

### 2.3 MinIO

```yaml
  minio:
    image: minio/minio:latest
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-minioadmin}
    volumes:
      - minio_data:/data
    ports:
      - "${EXPOSE_MINIO_PORT:-9000}:9000"
      - "${EXPOSE_MINIO_CONSOLE_PORT:-9001}:9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 5s
```

**Notes:**
- Two ports: 9000 (S3 API) + 9001 (web console for debugging uploads)
- `mc ready local` is MinIO's official health check command (replaces deprecated `curl /minio/health/live`)
- Default bucket creation handled by app startup or init script, not Docker entrypoint

### 2.4 Volumes and Network

```yaml
volumes:
  postgres_data:
  redis_data:
  minio_data:

networks:
  default:
    name: papery-dev
```

**Why named volumes over bind mounts:**
- Better I/O performance on macOS (Docker Desktop volume caching)
- Data persists across `docker compose down` (deleted only with `-v` flag)
- No host filesystem permission issues
- Named network `papery-dev` allows local backend to connect via `localhost:PORT`

---

## 3. docker-compose.yaml — Full Stack

Extends middleware with application services. Uses YAML anchors for shared env:

```yaml
x-shared-env: &shared-backend-env
  POSTGRES_HOST: postgres
  POSTGRES_PORT: 5432
  POSTGRES_USER: ${POSTGRES_USER:-papery}
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-papery_dev_secret}
  POSTGRES_DB: ${POSTGRES_DB:-papery}
  REDIS_HOST: redis
  REDIS_PORT: 6379
  REDIS_PASSWORD: ${REDIS_PASSWORD:-papery_dev_secret}
  MINIO_ENDPOINT: minio:9000
  MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY:-minioadmin}
  MINIO_SECRET_KEY: ${MINIO_SECRET_KEY:-minioadmin}
  SECRET_KEY: ${SECRET_KEY:-change-me-in-production}
  ENVIRONMENT: ${ENVIRONMENT:-local}

services:
  api:
    build:
      context: ../backend
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      <<: *shared-backend-env
      APP_MODE: api
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    ports:
      - "${EXPOSE_API_PORT:-8000}:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s

  worker:
    build:
      context: ../backend
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      <<: *shared-backend-env
      APP_MODE: worker
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Middleware services (same definitions as middleware yaml)
  postgres: ...
  redis: ...
  minio: ...
```

**Key patterns from Dify:**
- Same image for `api` and `worker` — differentiated by `APP_MODE` env var
- `depends_on` with `condition: service_healthy` — ensures middleware is ready before app starts
- YAML anchors (`x-shared-env`) eliminate env var duplication between api/worker

---

## 4. Dockerfile.dev (Quick Backend Build)

Optimized for fast rebuilds during development:

```dockerfile
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies (cached layer — only rebuilds when lock changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source (changes frequently — last layer)
COPY . .

EXPOSE 8000

# Entrypoint script handles api vs worker mode
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key differences from production Dockerfile:**
- Single stage (no multi-stage) — faster builds
- No non-root user setup — dev convenience
- `--no-dev` still excludes test deps from image (tests run locally)
- `uv sync --frozen` — uses lockfile exactly, fast install

---

## 5. Environment Variable Flow

```
.env.example (root, committed)
    │
    ├── cp → .env (root, gitignored — backend reads this locally)
    │
    └── cp → docker/.env (gitignored — Docker Compose reads this)
```

**Docker Compose env resolution order:**
1. `environment:` in compose file (highest priority)
2. Shell environment variables
3. `.env` file in the same directory as compose file
4. Default values in `${VAR:-default}` syntax

**Convention:** All Docker Compose vars use `${VAR:-default}` syntax so the stack works with zero config for dev (`docker compose up` just works).

---

## 6. Dev Workflow Commands (Makefile targets)

```makefile
# Start middleware only (daily dev workflow)
dev-middleware:
	cp -n .env.example docker/.env 2>/dev/null || true
	cd docker && docker compose -f docker-compose.middleware.yaml \
		-p papery-middleware up -d

# Start full stack
dev-stack:
	cp -n .env.example docker/.env 2>/dev/null || true
	cd docker && docker compose -f docker-compose.yaml \
		-p papery up -d

# Teardown middleware (preserve data)
dev-down:
	cd docker && docker compose -f docker-compose.middleware.yaml \
		-p papery-middleware down

# Full clean (destroy volumes)
dev-clean:
	cd docker && docker compose -f docker-compose.middleware.yaml \
		-p papery-middleware down -v

# View middleware logs
dev-logs:
	cd docker && docker compose -f docker-compose.middleware.yaml \
		-p papery-middleware logs -f
```

**Project name (`-p`):** Using explicit project names prevents conflicts with other Docker Compose projects and makes `docker ps` output clear.

---

## 7. Network Configuration

### Dev mode (middleware containers + local backend)
```
┌─────────────────────────────────┐
│  Docker: papery-dev network     │
│  ┌──────────┐  ┌─────┐  ┌────┐ │
│  │ postgres │  │redis│  │minio│ │
│  │  :5432   │  │:6379│  │:9000│ │
│  └────┬─────┘  └──┬──┘  └──┬─┘ │
│       │           │        │    │
├───────┼───────────┼────────┼────┤  Port mapping
│       │           │        │    │  to localhost
└───────┼───────────┼────────┼────┘
        ▼           ▼        ▼
   localhost:    localhost:  localhost:
     5432         6379     9000/9001
        │           │        │
   ┌────┴───────────┴────────┴───┐
   │  Local: backend (uvicorn)   │
   │  localhost:8000              │
   └─────────────────────────────┘
```

Backend connects to middleware via `localhost:PORT` (mapped ports). No Docker networking complexity.

### Full stack mode (everything in Docker)
Services connect via Docker DNS names (`postgres`, `redis`, `minio`) on the default network. No port mapping needed for inter-service communication — only expose ports for external access (API, MinIO console).

---

## 8. Implementation Recommendations

1. **Start with middleware-only** — get `make dev-middleware` working first, add full stack later
2. **Use named volumes** — never bind-mount database data directories on macOS
3. **Health checks on everything** — `depends_on.condition: service_healthy` prevents race conditions
4. **`start_period` on slow services** — PostgreSQL and MinIO need initialization time
5. **Explicit project names** — `papery-middleware` vs `papery` distinguishes dev vs full stack
6. **Default passwords in compose** — safe for dev, production overrides via `.env`
7. **MinIO bucket init** — handle in app startup code (check-and-create pattern), not Docker entrypoint scripts
8. **Don't over-tune** — dev environment defaults work fine; save PostgreSQL tuning for production

---

## 9. Files to Create (Phase 1)

| File | Purpose |
|------|---------|
| `docker/docker-compose.middleware.yaml` | PostgreSQL + Redis + MinIO for dev |
| `docker/docker-compose.yaml` | Full stack (api + worker + middleware) |
| `backend/Dockerfile.dev` | Quick dev build (single stage) |
| `backend/Dockerfile` | Production build (multi-stage, slim) |
| `.env.example` | All env vars with safe defaults |
| `Makefile` | Dev workflow commands |

---

*Research complete. Scope: Docker Compose split setup only.*
*Does NOT cover: PostgreSQL internals, Redis internals, MinIO SDK, config validation, FastAPI app setup.*
