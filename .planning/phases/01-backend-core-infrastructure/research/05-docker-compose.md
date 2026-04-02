# Research: Docker Compose Split Setup for Development

**Date:** 2026-04-02
**Scope:** Docker Compose split strategy, dev workflow, service definitions, health checks, volumes, networking, Dockerfile.dev
**Requirements:** INFRA-11 (D-12, D-13)
**Reference:** `.reference/dify/docker/` — split compose pattern

---

## 1. Split Strategy

| File | Purpose | Usage |
|------|---------|-------|
| `docker/docker-compose.middleware.yaml` | DB + Redis + MinIO only | **Daily dev** — middleware in Docker, app locally |
| `docker/docker-compose.yaml` | Full stack (middleware + app) | CI, staging, production |

**Key insight from Dify:** Middleware file is standalone (NOT an override). Each works independently.
Dify uses `env_file: [./middleware.env]` for middleware and YAML anchors (`x-shared-env: &shared-api-worker-env`) for shared env in full stack.

### File Layout

```
docker/
├── docker-compose.yaml             # Full stack
├── docker-compose.middleware.yaml   # Middleware only
├── .env.example                     # Full env template (host-side substitution)
├── middleware.env.example           # Middleware-only env (container env_file)
└── volumes/                         # Persistent data (gitignored)
    ├── postgres/data/
    ├── redis/data/
    └── minio/data/
```

### Env Strategy

- `docker/middleware.env` — loaded via `env_file:` in middleware compose (container-side)
- `docker/.env` — loaded by Docker Compose for `${VAR}` substitution (host-side)
- Use `${VAR:-default}` everywhere — compose runs even without `.env`
- **Critical:** Backend `.env` and Docker env files MUST share same credential defaults

---

## 2. Dev Workflow

```bash
# Start middleware → run backend/frontend locally
cd docker && docker compose -f docker-compose.middleware.yaml --env-file middleware.env up -d
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && pnpm dev
```

Backend connects to `localhost:5432` / `:6379` / `:9000` — all exposed by middleware containers.

### Makefile Targets

```makefile
dev-up:     cd docker && docker compose -f docker-compose.middleware.yaml --env-file middleware.env -p papery-dev up -d
dev-down:   cd docker && docker compose -f docker-compose.middleware.yaml -p papery-dev down
dev-reset:  cd docker && docker compose -f docker-compose.middleware.yaml -p papery-dev down -v
stack-up:   cd docker && docker compose -f docker-compose.yaml up -d --build
stack-down: cd docker && docker compose -f docker-compose.yaml down
```

---

## 3. Middleware Service Definitions

```yaml
services:
  db:
    image: postgres:17-alpine
    restart: unless-stopped
    env_file: [./middleware.env]
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-papery}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-papery_dev_pass}
      POSTGRES_DB: ${POSTGRES_DB:-papery}
      PGDATA: /var/lib/postgresql/data/pgdata
    command: >
      postgres -c max_connections=${POSTGRES_MAX_CONNECTIONS:-100}
               -c shared_buffers=${POSTGRES_SHARED_BUFFERS:-128MB}
               -c work_mem=${POSTGRES_WORK_MEM:-4MB}
               -c maintenance_work_mem=${POSTGRES_MAINTENANCE_WORK_MEM:-64MB}
               -c effective_cache_size=${POSTGRES_EFFECTIVE_CACHE_SIZE:-1GB}
    volumes: ["./volumes/postgres/data:/var/lib/postgresql/data"]
    ports: ["${EXPOSE_POSTGRES_PORT:-5432}:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-papery} -d ${POSTGRES_DB:-papery}"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    environment:
      REDISCLI_AUTH: ${REDIS_PASSWORD:-papery_dev_pass}  # suppresses -a warning in healthcheck
    command: redis-server --requirepass ${REDIS_PASSWORD:-papery_dev_pass} --appendonly yes
    volumes: ["./volumes/redis/data:/data"]
    ports: ["${EXPOSE_REDIS_PORT:-6379}:6379"]
    healthcheck:
      test: ["CMD-SHELL", "redis-cli ping | grep -q PONG"]
      interval: 5s
      timeout: 3s
      retries: 10

  minio:
    image: minio/minio:latest
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-papery_minio}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-papery_minio_pass}
    volumes: ["./volumes/minio/data:/data"]
    ports: ["${EXPOSE_MINIO_API_PORT:-9000}:9000", "${EXPOSE_MINIO_CONSOLE_PORT:-9001}:9001"]
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9000/minio/health/live || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s
```

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| PostgreSQL 17 | `postgres:17-alpine` | Latest stable, small image |
| Redis 7 | `redis:7-alpine` | `--appendonly yes` for AOF durability |
| MinIO | `minio/minio:latest` | S3-compatible, console UI at `:9001` |
| Restart | `unless-stopped` | Survives reboot, stops on `down` |
| Volumes | Bind mounts `./volumes/` | Easy to inspect/wipe, gitignored |
| MinIO healthcheck | `curl /minio/health/live` | Built-in endpoint, no `mc` dependency needed |
| Redis `REDISCLI_AUTH` | Env var | Avoids `-a password` warning in healthcheck |

---

## 4. Health Checks

| Service | Command | Notes |
|---------|---------|-------|
| PostgreSQL | `pg_isready -U <user> -d <db>` | Built-in, checks real readiness |
| Redis | `redis-cli ping \| grep PONG` | Uses `REDISCLI_AUTH` env for auth |
| MinIO | `curl -f localhost:9000/minio/health/live` | Official health endpoint |

**Dev:** `interval: 5s`, `timeout: 3s`, `retries: 10`, `start_period: 10s`.
**Production:** `interval: 30s`, `start_period: 30-60s`.

---

## 5. Volume & Network

**Volumes:** Bind mounts for dev (easy to inspect/wipe). `docker/volumes/` → `.gitignore`.
Named volumes are better for production. Fresh start: `down -v && rm -rf docker/volumes/`.

**Dev network:** Default bridge + exposed ports → backend connects via `localhost`.

**Full stack network:** Custom bridge, services communicate by name:

```yaml
services:
  api:
    depends_on:
      db:    { condition: service_healthy }
      redis: { condition: service_healthy }
      minio: { condition: service_healthy }
    environment:
      POSTGRES_HOST: db
      REDIS_HOST: redis
      MINIO_ENDPOINT: minio:9000
    networks: [papery-net]
networks:
  papery-net:
    driver: bridge
```

| Context | PostgreSQL | Redis | MinIO |
|---------|-----------|-------|-------|
| Local dev | `localhost:5432` | `localhost:6379` | `localhost:9000` |
| Full stack | `db:5432` | `redis:6379` | `minio:9000` |

**Dify pattern:** `condition: service_healthy` for hard deps. `required: false` for optional services (not needed Phase 1).

---

## 6. Dockerfile.dev (Backend)

For full-stack containerized dev (NOT daily workflow — use `uv run` locally).

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- `python:3.12-slim` not Alpine (avoids musl/wheel issues)
- Deps cached separately for fast rebuilds
- In full compose, bind-mount source + anonymous volume for `.venv`:
  `volumes: ["../backend:/app", "/app/.venv"]`

---

## 7. Env Variable Passing

| Mechanism | Scope | Use for |
|-----------|-------|---------|
| `env_file:` | Container env vars | Service credentials, tuning |
| `${VAR:-default}` in YAML | Host-side substitution | Ports, paths, image tags |
| `environment:` | Per-service overrides | Service-specific config |
| YAML anchors (`x-shared-env: &name`) | Shared env blocks | Full-stack `api` + `worker` shared vars |

---

## 8. Implementation Checklist

- [ ] `docker/docker-compose.middleware.yaml` — db, redis, minio
- [ ] `docker/docker-compose.yaml` — full stack (middleware + api + worker + frontend)
- [ ] `docker/middleware.env.example` + `docker/.env.example`
- [ ] `backend/Dockerfile.dev` + `backend/Dockerfile` (multi-stage prod)
- [ ] Add `docker/volumes/` to `.gitignore`
- [ ] Makefile targets: `dev-up`, `dev-down`, `dev-reset`, `stack-up`, `stack-down`
