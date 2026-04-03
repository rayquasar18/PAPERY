.PHONY: help install dev test test-cov lint format typecheck clean migrate migrate-new docker-up docker-down docker-build

# Default target
help: ## Show available targets
	@echo "PAPERY Backend — Development Commands"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with uv
	uv sync

dev: ## Run FastAPI dev server (uvicorn --reload)
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests with pytest
	uv run pytest

test-cov: ## Run tests with coverage report
	uv run pytest --cov=app --cov-report=term-missing

lint: ## Run ruff linter
	uv run ruff check .

format: ## Format code with ruff
	uv run ruff format .

typecheck: ## Run mypy type checker
	uv run mypy app/

clean: ## Remove cache directories
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache .pytest_cache .ruff_cache htmlcov .coverage

migrate: ## Run Alembic migrations (upgrade to head)
	uv run alembic upgrade head

migrate-new: ## Create new Alembic migration (usage: make migrate-new msg="add users table")
	uv run alembic revision --autogenerate -m "$(msg)"

docker-up: ## Start services with docker compose
	docker compose up -d

docker-down: ## Stop services with docker compose
	docker compose down

docker-build: ## Build backend Docker image
	docker build -t papery-backend .
