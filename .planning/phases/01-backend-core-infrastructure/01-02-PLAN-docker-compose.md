---
plan: "02"
title: "Docker Compose Dev Environment"
phase: 1
wave: 1
depends_on: []
requirements:
  - INFRA-11
files_modified:
  - docker/docker-compose.middleware.yaml
  - docker/middleware.env.example
  - docker/docker-compose.yaml
  - docker/Dockerfile.dev
  - docker/.gitkeep
  - .gitignore
autonomous: true
estimated_tasks: 3
---

# Plan 02 — Docker Compose Dev Environment

## Goal

Create the split Docker Compose setup: a lightweight middleware-only file for daily development (PostgreSQL 17 + Redis 7 + MinIO) and a full-stack file for CI/staging. All services must have healthchecks, proper volume mounts, and env-file configuration.

---

## Tasks

### Task 2.1 — Create docker-compose.middleware.yaml for daily dev

<read_first>
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 7: Docker Compose Dev Environment)
- .planning/phases/01-backend-core-infrastructure/research/05-docker-compose.md
</read_first>

<action>
Create `docker/docker-compose.middleware.yaml`:

```yaml
# Docker Compose — Middleware only (daily development)
# Usage: docker compose -f docker/docker-compose.middleware.yaml up -d

services:
  db:
    image: postgres:17-alpine
    container_name: papery-db
    restart: unless-stopped
    env_file: [./middleware.env]
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - ./volumes/postgres:/var/lib/postgresql/data
    command:
      - "postgres"
      - "-c"
      - "max_connections=200"
      - "-c"
      - "shared_buffers=256MB"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-papery} -d ${POSTGRES_DB:-papery}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: papery-redis
    restart: unless-stopped
    env_file: [./middleware.env]
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - ./volumes/redis:/data
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD:-papery_redis_dev}
      --appendonly yes
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD-SHELL", "redis-cli -a ${REDIS_PASSWORD:-papery_redis_dev} ping | grep PONG"]
      interval: 5s
      timeout: 5s
      retries: 5
    environment:
      REDISCLI_AUTH: ${REDIS_PASSWORD:-papery_redis_dev}

  minio:
    image: minio/minio:latest
    container_name: papery-minio
    restart: unless-stopped
    env_file: [./middleware.env]
    ports:
      - "${MINIO_API_PORT:-9000}:9000"
      - "${MINIO_CONSOLE_PORT:-9001}:9001"
    volumes:
      - ./volumes/minio:/data
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-minioadmin}
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5
```
</action>

<acceptance_criteria>
- `docker/docker-compose.middleware.yaml` exists
- File contains `image: postgres:17-alpine`
- File contains `image: redis:7-alpine`
- File contains `image: minio/minio:latest`
- File contains `pg_isready` in healthcheck
- File contains `redis-cli` in healthcheck (with PONG grep)
- File contains `curl -f http://localhost:9000/minio/health/live` in healthcheck
- File contains `restart: unless-stopped` for all 3 services
- File contains `./volumes/postgres:/var/lib/postgresql/data`
- File contains `./volumes/redis:/data`
- File contains `./volumes/minio:/data`
- File contains `env_file: [./middleware.env]` for all services
- File contains `REDISCLI_AUTH` environment variable for redis service
- File contains `--console-address ":9001"` in minio command
</acceptance_criteria>

---

### Task 2.2 — Create middleware.env.example and full-stack docker-compose.yaml

<read_first>
- docker/docker-compose.middleware.yaml (created in Task 2.1)
- .planning/phases/01-backend-core-infrastructure/01-RESEARCH.md (section 7)
</read_first>

<action>
Create `docker/middleware.env.example`:

```env
# =============================================================================
# Docker Compose Middleware — Environment Variables
# Copy to middleware.env before running docker compose.
# =============================================================================

# --- PostgreSQL ---
POSTGRES_USER=papery
POSTGRES_PASSWORD=papery_dev_password
POSTGRES_DB=papery
POSTGRES_PORT=5432

# --- Redis ---
REDIS_PASSWORD=papery_redis_dev
REDIS_PORT=6379

# --- MinIO ---
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
```

Create `docker/docker-compose.yaml` (full-stack with backend service):

```yaml
# Docker Compose — Full stack (CI, staging, production)
# Usage: docker compose -f docker/docker-compose.yaml up -d

services:
  db:
    image: postgres:17-alpine
    container_name: papery-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-papery}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-papery_dev_password}
      POSTGRES_DB: ${POSTGRES_DB:-papery}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    command:
      - "postgres"
      - "-c"
      - "max_connections=200"
      - "-c"
      - "shared_buffers=256MB"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-papery} -d ${POSTGRES_DB:-papery}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: papery-redis
    restart: unless-stopped
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD:-papery_redis_dev}
      --appendonly yes
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD-SHELL", "redis-cli -a ${REDIS_PASSWORD:-papery_redis_dev} ping | grep PONG"]
      interval: 5s
      timeout: 5s
      retries: 5
    environment:
      REDISCLI_AUTH: ${REDIS_PASSWORD:-papery_redis_dev}

  minio:
    image: minio/minio:latest
    container_name: papery-minio
    restart: unless-stopped
    ports:
      - "${MINIO_API_PORT:-9000}:9000"
      - "${MINIO_CONSOLE_PORT:-9001}:9001"
    volumes:
      - minio_data:/data
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-minioadmin}
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build:
      context: ../backend
      dockerfile: ../docker/Dockerfile.dev
    container_name: papery-web
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ../backend:/app
    env_file:
      - ../.env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

Create `docker/Dockerfile.dev`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copy application code
COPY . .

# Run with hot-reload
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```
</action>

<acceptance_criteria>
- `docker/middleware.env.example` exists
- `docker/middleware.env.example` contains `POSTGRES_USER=papery`
- `docker/middleware.env.example` contains `REDIS_PASSWORD=papery_redis_dev`
- `docker/middleware.env.example` contains `MINIO_ACCESS_KEY=minioadmin`
- `docker/docker-compose.yaml` exists
- `docker/docker-compose.yaml` contains `service_healthy` in depends_on for web service
- `docker/docker-compose.yaml` contains `volumes:` section at bottom with named volumes
- `docker/docker-compose.yaml` contains `web:` service with build context
- `docker/Dockerfile.dev` exists
- `docker/Dockerfile.dev` contains `FROM python:3.12-slim`
- `docker/Dockerfile.dev` contains `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/`
- `docker/Dockerfile.dev` contains `uv sync --frozen --no-install-project`
- `docker/Dockerfile.dev` contains `uvicorn app.main:app`
</acceptance_criteria>

---

### Task 2.3 — Update .gitignore for docker volumes

<read_first>
- .gitignore (existing project gitignore)
</read_first>

<action>
Append the following to `.gitignore`:

```
# Docker volumes (local development data)
docker/volumes/
docker/middleware.env
```

These entries ensure that:
1. Local bind-mount data (postgres, redis, minio) is not committed
2. The actual middleware.env with credentials is not committed (only the .example is)
</action>

<acceptance_criteria>
- `.gitignore` contains `docker/volumes/`
- `.gitignore` contains `docker/middleware.env`
</acceptance_criteria>

---

## Verification

After all tasks complete:
1. `docker compose -f docker/docker-compose.middleware.yaml config` validates without errors
2. `docker compose -f docker/docker-compose.yaml config` validates without errors
3. `docker/Dockerfile.dev` is a valid Dockerfile (no syntax errors)
4. `docker/middleware.env.example` has all required variables
5. `.gitignore` excludes `docker/volumes/` and `docker/middleware.env`

## must_haves

- [ ] `docker/docker-compose.middleware.yaml` defines db, redis, minio services with healthchecks
- [ ] `docker/docker-compose.yaml` defines full stack including web service with `depends_on: condition: service_healthy`
- [ ] `docker/Dockerfile.dev` uses `python:3.12-slim` + uv for dependency management
- [ ] `docker/middleware.env.example` documents all middleware env vars
- [ ] All services use `restart: unless-stopped`
- [ ] PostgreSQL uses `postgres:17-alpine` with `pg_isready` healthcheck
- [ ] Redis uses `redis:7-alpine` with password auth and `REDISCLI_AUTH`
- [ ] MinIO has both API (9000) and console (9001) ports
- [ ] Docker volumes are gitignored
