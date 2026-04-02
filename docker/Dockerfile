# ============================================================================
# PAPERY Backend — Production Dockerfile
# Multi-stage build: builder installs deps, runtime copies only .venv
# ============================================================================

# --- Stage 1: Builder — install dependencies with uv ---
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install only production dependencies (no dev group)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# --- Stage 2: Runtime — minimal production image ---
FROM python:3.12-slim AS runtime

# Security: run as non-root user
RUN groupadd --gid 1000 papery && \
    useradd --uid 1000 --gid papery --shell /bin/bash --create-home papery

WORKDIR /app

# Copy only the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY backend/ /app/

# Set PATH to use .venv binaries
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WEB_CONCURRENCY=2

# Switch to non-root user
USER papery

EXPOSE 8000

# Health check uses stdlib urllib — no curl required in minimal image
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

# Production entrypoint: gunicorn with uvicorn workers (shell form for env var expansion)
CMD gunicorn app.main:app \
    --bind 0.0.0.0:8000 \
    --workers ${WEB_CONCURRENCY:-2} \
    --worker-class uvicorn_worker.UvicornWorker \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile -
