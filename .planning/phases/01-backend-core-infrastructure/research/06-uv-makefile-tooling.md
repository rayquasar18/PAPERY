# Research: uv Package Manager, Makefile Automation & Dev Tooling

**Date:** 2026-04-02
**Scope:** uv, Makefile, ruff, mypy, pytest, pre-commit — Phase 1 dev tooling setup
**Sources:** Dify reference, open-notebook reference, uv/ruff/mypy/pydantic official docs

---

## 1. uv Package Manager

### 1.1 pyproject.toml Structure (Non-Package Mode)

PAPERY backend is an **application**, not a library. Use `package = false` to skip build/install.

```toml
[project]
name = "papery-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.35",
    "alembic>=1.14.0",
    "asyncpg>=0.30.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "redis[hiredis]>=5.2.0",
    "miniopy-async>=1.21",
    "python-multipart>=0.0.18",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "httpx>=0.28.0",
    "fastcrud>=0.16.0",
]

[tool.uv]
package = false
default-groups = ["dev"]
```

### 1.2 Dependency Groups (PEP 735)

Use `[dependency-groups]` (not `[project.optional-dependencies]`) for dev tools:

```toml
[dependency-groups]
dev = [
    "ruff>=0.15.0",
    "mypy>=1.14.0",
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.0.0",
    "pytest-mock>=3.14.0",
    "pre-commit>=4.0.0",
    "httpx>=0.28.0",          # TestClient needs this
    # Type stubs
    "types-redis>=4.6.0",
    "types-passlib>=1.7.7",
    "asyncpg-stubs>=0.30.0",
]
```

### 1.3 Key uv Commands

| Command | Purpose |
|---------|---------|
| `uv sync` | Install all deps + default groups into `.venv` |
| `uv sync --dev` | Same (dev is default group) |
| `uv sync --frozen` | Install from lockfile without re-resolving (CI) |
| `uv sync --locked` | Error if lockfile is stale (CI guard) |
| `uv lock` | Resolve and write `uv.lock` |
| `uv lock --upgrade` | Upgrade all packages |
| `uv lock --upgrade-package httpx` | Upgrade single package |
| `uv add fastapi` | Add runtime dependency |
| `uv add --dev pytest` | Add to `dev` group |
| `uv add --group lint ruff` | Add to custom `lint` group |
| `uv remove fastapi` | Remove dependency |
| `uv run pytest` | Run command in project env (auto-syncs) |
| `uv run --frozen pytest` | Run without re-syncing |
| `uv venv` | Create `.venv` (auto-done by sync) |

### 1.4 Key Patterns from Dify

- **`uv run --project api --dev <cmd>`** — run from root targeting subdirectory
- **`uv sync --dev`** in `prepare-api` target — one-step env setup
- **`uv.lock` committed to git** — deterministic builds across machines

### 1.5 PAPERY Adaptation

Since PAPERY uses monorepo with `backend/` subdirectory:
- `pyproject.toml` lives at `backend/pyproject.toml`
- Makefile commands use `cd backend && uv ...` or `uv --directory backend ...`
- `uv.lock` at `backend/uv.lock` — commit to git

---

## 2. Makefile Automation

### 2.1 Recommended Targets

```makefile
.DEFAULT_GOAL := help

# === Development Setup ===
.PHONY: dev-setup prepare-docker prepare-api dev-clean

dev-setup: prepare-docker prepare-api
	@echo "Development environment ready!"

prepare-docker:
	@cp -n .env.example .env 2>/dev/null || true
	@cd docker && docker compose -f docker-compose.middleware.yaml \
	    --env-file ../.env -p papery-dev up -d

prepare-api:
	@cd backend && uv sync --dev
	@cd backend && uv run alembic upgrade head

# === Code Quality ===
.PHONY: format check lint type-check

format:
	@uv run --directory backend ruff format .

check:
	@uv run --directory backend ruff check .

lint:
	@uv run --directory backend ruff format .
	@uv run --directory backend ruff check --fix .

type-check:
	@uv run --directory backend mypy .

# === Testing ===
.PHONY: test test-cov

test:
	@uv run --directory backend pytest

test-cov:
	@uv run --directory backend pytest --cov=app --cov-report=term-missing

# === Database ===
.PHONY: migrate migrate-new seed

migrate:
	@cd backend && uv run alembic upgrade head

migrate-new:
	@cd backend && uv run alembic revision --autogenerate -m "$(MSG)"

seed:
	@cd backend && uv run python -m scripts.seed

# === Cleanup ===
.PHONY: dev-clean clean-cache

dev-clean:
	@cd docker && docker compose -f docker-compose.middleware.yaml \
	    -p papery-dev down -v

clean-cache:
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# === Help ===
help:
	@echo "Setup:    make dev-setup | dev-clean"
	@echo "Quality:  make format | check | lint | type-check"
	@echo "Test:     make test | test-cov"
	@echo "DB:       make migrate | migrate-new MSG='...' | seed"
	@echo "Clean:    make clean-cache"
```

### 2.2 Design Principles from References

- **`@` prefix** on all commands — suppress command echo, show only output
- **`cp -n`** for env files — don't overwrite existing config
- **`uv run --directory`** or **`cd dir && uv run`** — both patterns work
- **`.PHONY` declarations** — every target since none produce files
- **Composable targets** — `dev-setup` chains `prepare-docker` + `prepare-api`

---

## 3. Pre-commit Configuration

### 3.1 .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.8  # pin to specific version
    hooks:
      - id: ruff-check
        args: [--fix]
        types_or: [python, pyi]
      - id: ruff-format
        types_or: [python, pyi]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.10.0
          - sqlalchemy[asyncio]>=2.0.35
          - fastapi>=0.115.0
        args: [--config-file=backend/pyproject.toml]
        pass_filenames: false
```

**Critical ordering:** ruff-check (with `--fix`) BEFORE ruff-format.

### 3.2 Installation

```makefile
pre-commit-install:
	@uv run --directory backend pre-commit install
```

---

## 4. Ruff Configuration

### 4.1 Recommended Config for FastAPI + SQLAlchemy + Pydantic v2

```toml
[tool.ruff]
target-version = "py312"
line-length = 120
exclude = ["migrations/", ".venv/"]

[tool.ruff.format]
quote-style = "double"

[tool.ruff.lint]
select = [
    "E",       # pycodestyle errors
    "W",       # pycodestyle warnings
    "F",       # pyflakes
    "I",       # isort
    "B",       # flake8-bugbear
    "C4",      # flake8-comprehensions
    "N",       # pep8-naming
    "UP",      # pyupgrade (modernize syntax for 3.12+)
    "SIM",     # flake8-simplify
    "S",       # flake8-bandit (security)
    "T201",    # print-found
    "RUF",     # ruff-specific rules
    "FURB",    # refurb
    "PT",      # flake8-pytest-style
    "ASYNC",   # flake8-async (important for FastAPI)
    "TRY",     # tryceratops (exception handling)
]

ignore = [
    "E501",    # line too long (handled by formatter)
    "B008",    # do not perform function calls in argument defaults (FastAPI Depends)
    "S105",    # hardcoded password (false positives in config schemas)
    "S106",    # hardcoded password in function arg
    "TRY003",  # long messages in exceptions
    "RUF012",  # mutable class variables (conflicts with SQLAlchemy)
]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"tests/**" = ["S101", "S106", "T201"]   # allow assert, hardcoded passwords, print
"migrations/**" = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["app"]
```

### 4.2 Key Rule Explanations

| Rule | Why |
|------|-----|
| `B008` ignore | FastAPI uses `Depends()` in function defaults — this is idiomatic |
| `ASYNC` | Catches common async mistakes (missing await, blocking calls) |
| `UP` | Auto-upgrades to Python 3.12+ syntax (f-strings, `X \| Y` unions) |
| `S` | Security checks (eval, exec, SQL injection patterns) |
| `RUF012` ignore | SQLAlchemy `__tablename__` etc. are mutable class vars by design |

---

## 5. Mypy Configuration

### 5.1 Recommended Config for SQLAlchemy 2.0 Async + Pydantic v2

```toml
[tool.mypy]
python_version = "3.12"
strict = false                        # start lenient, tighten over time
warn_return_any = true
warn_unused_configs = true
warn_redundant_casts = true
warn_unused_ignores = true
disallow_untyped_defs = true
check_untyped_defs = true
no_implicit_reexport = true
plugins = ["pydantic.mypy"]
exclude = ["migrations/", "tests/"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true

[[tool.mypy.overrides]]
module = ["fastcrud.*", "miniopy_async.*"]
ignore_missing_imports = true
```

### 5.2 Important Notes

- **SQLAlchemy mypy plugin is DEPRECATED** (removed in 2.1). Do NOT use it.
- SQLAlchemy 2.0+ with `Mapped[]` annotations works natively with mypy — no plugin needed.
- **Pydantic plugin IS needed** — `pydantic.mypy` improves `BaseModel.__init__` typing.
- Start with `strict = false` + selective strict flags. Migrate to `strict = true` later.
- Exclude `migrations/` (auto-generated) and potentially `tests/` initially.

---

## 6. Pytest Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"               # pytest-asyncio: auto-detect async tests
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--tb=short",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests requiring external services",
]
filterwarnings = [
    "ignore::DeprecationWarning:sqlalchemy.*",
]
```

---

## 7. Python 3.12+ Type Hint Features to Use

| Feature | Example | Benefit |
|---------|---------|---------|
| PEP 695 type params | `class Repo[T]:` | No more `TypeVar` boilerplate |
| `type` statement | `type UserId = int` | Lazy-evaluated, cleaner aliases |
| `@override` decorator | `@override def get(self):` | Catches typos in method overrides |
| `**kwargs` typing | `**kwargs: Unpack[Config]` | Precise kwargs with TypedDict |
| `X \| Y` unions | `str \| None` | Already in 3.10+, pyupgrade enforces |

---

## 8. File Placement Summary

```
PAPERY/
  Makefile                              # Root-level, manages all services
  .pre-commit-config.yaml              # Root-level
  .env.example                          # Root-level (D-17)
  backend/
    pyproject.toml                      # uv project config + tool configs
    uv.lock                             # Committed to git
    .python-version                     # "3.12" — uv reads this
    app/                                # Application code
    tests/                              # Test files
    migrations/                         # Alembic migrations
    scripts/                            # Seed scripts
```

---

## 9. Implementation Checklist

1. [ ] Create `backend/pyproject.toml` with deps + all tool configs
2. [ ] Run `cd backend && uv sync --dev` to generate `uv.lock`
3. [ ] Create `Makefile` at project root
4. [ ] Create `.pre-commit-config.yaml` at project root
5. [ ] Run `uv run --directory backend pre-commit install`
6. [ ] Create `backend/.python-version` with `3.12`
7. [ ] Add `uv.lock` to git
8. [ ] Verify: `make lint`, `make type-check`, `make test` all pass
