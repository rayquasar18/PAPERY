.DEFAULT_GOAL := help

# === Development Setup ===
.PHONY: dev-setup prepare-docker prepare-api dev-clean

dev-setup: prepare-docker prepare-api  ## Full dev environment setup
	@echo "Development environment ready!"

prepare-docker:  ## Start Docker middleware (PostgreSQL, Redis, MinIO)
	@cp -n .env.example .env 2>/dev/null || true
	@cp -n docker/middleware.env.example docker/middleware.env 2>/dev/null || true
	@cd docker && docker compose -f docker-compose.middleware.yaml \
	    -p papery-dev up -d

prepare-api:  ## Install Python dependencies and run migrations
	@cd backend && uv sync --dev
	@cd backend && uv run alembic upgrade head

dev-clean:  ## Stop Docker middleware and remove volumes
	@cd docker && docker compose -f docker-compose.middleware.yaml \
	    -p papery-dev down -v

# === Code Quality ===
.PHONY: format check lint type-check

format:  ## Format code with ruff
	@cd backend && uv run ruff format .

check:  ## Check code with ruff (no fix)
	@cd backend && uv run ruff check .

lint:  ## Format + fix code with ruff
	@cd backend && uv run ruff format .
	@cd backend && uv run ruff check --fix .

type-check:  ## Run mypy type checking
	@cd backend && uv run mypy app/

# === Testing ===
.PHONY: test test-cov test-unit

test:  ## Run all tests
	@cd backend && uv run pytest tests/ -v --tb=short

test-cov:  ## Run tests with coverage report
	@cd backend && uv run pytest tests/ --cov=app --cov-report=term-missing

test-unit:  ## Run unit tests only (no integration)
	@cd backend && uv run pytest tests/ -v --tb=short -m "not integration"

# === Database ===
.PHONY: migrate migrate-new

migrate:  ## Apply all pending migrations
	@cd backend && uv run alembic upgrade head

migrate-new:  ## Create new migration (usage: make migrate-new MSG='add users table')
	@cd backend && uv run alembic revision --autogenerate -m "$(MSG)"

# === Cleanup ===
.PHONY: clean-cache

clean-cache:  ## Remove Python cache directories
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# === Help ===
help:  ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	    awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
