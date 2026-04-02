# Research: Modular Pydantic Settings + Startup Validation

> INFRA-09 | Decisions: D-15, D-16, D-17, D-18

## 1. Core Pattern: Multiple Inheritance Composition

Pydantic Settings v2 composes a single `AppSettings` from many `BaseSettings` subclasses via **multiple inheritance**. Each module owns its env vars; the root class declares `model_config` once. Pattern studied from `.reference/dify/api/configs/`.

```python
class DatabaseConfig(BaseSettings):
    POSTGRES_HOST: str = "localhost"

class RedisConfig(BaseSettings):
    REDIS_CACHE_HOST: str = "localhost"

class AppSettings(DatabaseConfig, RedisConfig, ...):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8",
        extra="ignore", case_sensitive=True,
    )
```

**Rules:**
- `model_config` on **root class only** — avoids MRO conflicts.
- `extra="ignore"` — unknown vars in `.env` don't error.
- `case_sensitive=True` — PAPERY uses UPPER_CASE exclusively (D-16).
- Do NOT use `env_prefix` — explicit naming (`POSTGRES_*`, `REDIS_CACHE_*`) per D-16.

## 2. Module Layout

```
backend/app/core/config/
├── __init__.py      # `settings = AppSettings()` singleton (validates at import)
├── app.py           # AppConfig: APP_NAME, ENVIRONMENT, DEBUG
├── database.py      # DatabaseConfig: POSTGRES_* + computed ASYNC_DATABASE_URI
├── redis.py         # RedisConfig: REDIS_CACHE_*, REDIS_QUEUE_*, REDIS_RATE_LIMIT_*
├── minio.py         # MinioConfig: MINIO_*
├── security.py      # SecurityConfig: SECRET_KEY, ALGORITHM, *_TOKEN_EXPIRE_*
├── email.py         # EmailConfig: SMTP_*
├── cors.py          # CorsConfig: CORS_ORIGINS
├── admin.py         # AdminConfig: ADMIN_EMAIL, ADMIN_PASSWORD
└── settings.py      # AppSettings(all modules) + model_config + startup validation
```

## 3. Key Module Patterns

### 3.1 Computed field + URL encoding (`database.py`)
```python
from urllib.parse import quote_plus
from pydantic import Field, PositiveInt, computed_field
from pydantic_settings import BaseSettings

class DatabaseConfig(BaseSettings):
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: PositiveInt = Field(default=5432)
    POSTGRES_USER: str = Field(default="papery")
    POSTGRES_PASSWORD: str = Field(default="")
    POSTGRES_DB: str = Field(default="papery")
    POSTGRES_POOL_SIZE: int = Field(default=20, ge=1)
    POSTGRES_MAX_OVERFLOW: int = Field(default=10, ge=0)

    @computed_field
    @property
    def ASYNC_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{quote_plus(self.POSTGRES_USER)}"
            f":{quote_plus(self.POSTGRES_PASSWORD)}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
```

`quote_plus()` handles special chars in passwords (`@`, `#`, `/`).

### 3.2 Three Redis namespaces (`redis.py`)
```python
class RedisConfig(BaseSettings):
    REDIS_CACHE_HOST: str = Field(default="localhost")
    REDIS_CACHE_PORT: PositiveInt = Field(default=6379)
    REDIS_CACHE_DB: int = Field(default=0, ge=0, le=15)
    REDIS_CACHE_PASSWORD: str = Field(default="")
    # Queue: DB=1, Rate Limit: DB=2 — same field pattern
```

### 3.3 CSV parsing with `field_validator(mode="before")` (`cors.py`)
```python
class CorsConfig(BaseSettings):
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v
```

## 4. Startup Validation

```python
import re
from typing import Self
from pydantic import model_validator

_PLACEHOLDER_RE = re.compile(
    r"^(changeme|change.?me|secret|password|xxx|sk-xxx|"
    r"your[_-]?.+|CHANGE_ME|TODO|fixme|replace.?me)$",
    re.IGNORECASE,
)

class AppSettings(AppConfig, DatabaseConfig, RedisConfig, MinioConfig,
                  SecurityConfig, EmailConfig, CorsConfig, AdminConfig):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8",
        extra="ignore", case_sensitive=True,
    )

    @model_validator(mode="after")
    def validate_startup(self) -> Self:
        errors: list[str] = []

        # SECRET_KEY: always enforce
        if _PLACEHOLDER_RE.match(self.SECRET_KEY):
            errors.append("SECRET_KEY is a placeholder — run: openssl rand -base64 42")
        if len(self.SECRET_KEY) < 32:
            errors.append(f"SECRET_KEY must be >= 32 chars (got {len(self.SECRET_KEY)})")

        # Non-local: reject placeholder passwords
        if self.ENVIRONMENT != "local":
            for name in ("POSTGRES_PASSWORD", "MINIO_SECRET_KEY"):
                val = getattr(self, name, "")
                if val and _PLACEHOLDER_RE.match(val):
                    errors.append(f"{name} contains a placeholder value")

        # Production: require SMTP
        if self.ENVIRONMENT == "production" and not getattr(self, "SMTP_HOST", ""):
            errors.append("SMTP_HOST required in production")

        if errors:
            raise ValueError("Config validation failed:\n" +
                             "\n".join(f"  - {e}" for e in errors))
        return self
```

## 5. Validator Cheatsheet

| Type | Decorator | Use Case |
|---|---|---|
| Field (before) | `@field_validator("X", mode="before")` + `@classmethod` | Parse raw input (CSV → list) |
| Field (after) | `@field_validator("X", mode="after")` + `@classmethod` | Validate typed value |
| Model (after) | `@model_validator(mode="after")` | Cross-field / env-dependent checks |
| Computed | `@computed_field` + `@property` | Derived values (DATABASE_URI) |

## 6. Env Loading Priority (First Wins)

1. Init kwargs → 2. Environment variables → 3. `.env` file → 4. Secrets dir → 5. Defaults

Real env vars override `.env` → correct for Docker/CI deployments.

## 7. `.env.example` (D-17: Single Root File)

```bash
# PAPERY — copy to .env and fill in real values
APP_NAME=PAPERY
ENVIRONMENT=local                    # local | staging | production
DEBUG=true

SECRET_KEY=changeme-generate-a-real-key-at-least-32-chars  # openssl rand -base64 42
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=papery
POSTGRES_PASSWORD=papery_dev_password
POSTGRES_DB=papery

REDIS_CACHE_HOST=localhost
REDIS_CACHE_PORT=6379
REDIS_CACHE_DB=0
REDIS_CACHE_PASSWORD=
REDIS_QUEUE_HOST=localhost
REDIS_QUEUE_PORT=6379
REDIS_QUEUE_DB=1
REDIS_QUEUE_PASSWORD=
REDIS_RATE_LIMIT_HOST=localhost
REDIS_RATE_LIMIT_PORT=6379
REDIS_RATE_LIMIT_DB=2
REDIS_RATE_LIMIT_PASSWORD=

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=papery
MINIO_SECRET_KEY=papery_minio_dev
MINIO_BUCKET=papery-documents
MINIO_USE_SSL=false

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@papery.app
SMTP_USE_TLS=true

CORS_ORIGINS=http://localhost:3000,http://localhost:3001
ADMIN_EMAIL=admin@papery.app
ADMIN_PASSWORD=changeme
```

## 8. Design Decisions

| Decision | Choice | Why |
|---|---|---|
| Composition | Multiple inheritance | Dify-proven, clean module separation |
| `model_config` | Root class only | Avoids MRO conflicts |
| `env_prefix` | NOT used | D-16: explicit naming per service |
| Startup validation | `@model_validator(mode="after")` | Cross-field, clear errors |
| Placeholder rejection | Regex match | D-18: prevents insecure deploys |
| Singleton | `settings = AppSettings()` | Validates at import, fail-fast |
| Password in URIs | `quote_plus()` | Handles special chars |
| `.env.example` | Single root file | D-17: one source of truth |

## 9. Implementation Checklist

- [ ] Create `backend/app/core/config/` with 9 modules + `__init__.py`
- [ ] Each module: `BaseSettings`, `Field(description=...)`, typed fields
- [ ] Root `AppSettings`: multiple inheritance + `@model_validator`
- [ ] Singleton `settings = AppSettings()` in `__init__.py`
- [ ] Reject placeholders (regex), enforce `SECRET_KEY >= 32 chars`
- [ ] Production: stricter checks (SMTP, no empty passwords)
- [ ] `@computed_field` for `ASYNC_DATABASE_URI` with `quote_plus()`
- [ ] `@field_validator(mode="before")` for `CORS_ORIGINS`
- [ ] Create `.env.example` at project root
- [ ] Test: app crashes on placeholder SECRET_KEY in production
