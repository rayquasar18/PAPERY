# Research: Modular Pydantic Settings + Startup Validation

**Researched:** 2026-04-02
**Requirement:** INFRA-09 — Environment-based configuration with startup validation
**Decisions:** D-15 (modular config), D-16 (prefix naming), D-17 (single .env.example), D-18 (strict validation)

---

## 1. Pattern Summary: Multiple Inheritance Composition

Dify's pattern: each domain gets its own `BaseSettings` subclass with only fields — no `model_config`. A final composed class inherits all of them and is the **only place** that defines `model_config` and `settings_customise_sources`.

```
DatabaseConfig(BaseSettings)     — POSTGRES_* fields
RedisConfig(BaseSettings)        — REDIS_* fields
SecurityConfig(BaseSettings)     — SECRET_KEY, JWT_* fields
    ...
AppConfig(DatabaseConfig, RedisConfig, SecurityConfig, ...)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

**Why this works:** Python MRO merges all fields into one flat namespace. Since only the leaf class defines `model_config`, there are no merge conflicts. Pydantic Settings reads the `.env` file once and maps all fields from all parents.

**Critical rule:** Never set `model_config` on intermediate config classes — only on the final composed class.

---

## 2. Recommended Module Layout

```
backend/app/core/config/
    __init__.py          # Exports `settings` singleton
    app.py               # AppGeneralConfig: APP_NAME, APP_VERSION, ENVIRONMENT, DEBUG
    database.py          # DatabaseConfig: POSTGRES_* + pool settings + computed URI
    redis.py             # RedisConfig: REDIS_CACHE_*, REDIS_QUEUE_*, REDIS_RATE_LIMIT_*
    minio.py             # MinIOConfig: MINIO_* fields
    security.py          # SecurityConfig: SECRET_KEY, JWT algorithm/expiry
    email.py             # EmailConfig: SMTP_* fields
    cors.py              # CORSConfig: CORS_ORIGINS
    _validators.py       # Shared startup validation logic (placeholder rejection)
```

### `__init__.py` — The Composed Config + Singleton

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from .app import AppGeneralConfig
from .database import DatabaseConfig
from .redis import RedisConfig
from .minio import MinIOConfig
from .security import SecurityConfig
from .email import EmailConfig
from .cors import CORSConfig

class AppConfig(
    AppGeneralConfig,
    DatabaseConfig,
    RedisConfig,
    MinIOConfig,
    SecurityConfig,
    EmailConfig,
    CORSConfig,
):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,    # env vars are case-sensitive on Linux
    )

settings = AppConfig()  # Validated at import time
```

**Import-time instantiation** means the app crashes immediately on bad config — exactly what we want. FastAPI won't start if config is invalid.

---

## 3. Individual Config Module Pattern

Each module is a standalone `BaseSettings` subclass. Use `Field()` with descriptions for self-documentation. Use Pydantic's built-in constrained types where possible.

### Example: `security.py`

```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

class SecurityConfig(BaseSettings):
    SECRET_KEY: str = Field(
        description="JWT signing key. Generate with: openssl rand -base64 42",
        min_length=32,
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1)

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def reject_placeholder_secret(cls, v: str) -> str:
        from ._validators import reject_placeholder
        return reject_placeholder(v, "SECRET_KEY")
```

### Example: `database.py`

```python
from pydantic import Field, NonNegativeInt, PositiveInt, computed_field
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus

class DatabaseConfig(BaseSettings):
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: PositiveInt = Field(default=5432)
    POSTGRES_USER: str = Field(default="papery")
    POSTGRES_PASSWORD: str = Field(default="")
    POSTGRES_DB: str = Field(default="papery")

    # Pool settings (D-09: enterprise pool config)
    POSTGRES_POOL_SIZE: NonNegativeInt = Field(default=20)
    POSTGRES_MAX_OVERFLOW: NonNegativeInt = Field(default=10)
    POSTGRES_POOL_RECYCLE: NonNegativeInt = Field(default=3600)
    POSTGRES_POOL_PRE_PING: bool = Field(default=True)
    POSTGRES_POOL_TIMEOUT: NonNegativeInt = Field(default=30)
    POSTGRES_ECHO: bool = Field(default=False)

    @computed_field
    @property
    def POSTGRES_URI(self) -> str:
        user = quote_plus(self.POSTGRES_USER)
        pwd = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{user}:{pwd}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
```

---

## 4. Strict Startup Validation (D-18)

### 4.1 Placeholder Rejection via Shared Helper

Create `_validators.py` with reusable validation functions:

```python
import re

_PLACEHOLDER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^changeme$", re.IGNORECASE),
    re.compile(r"^secret$", re.IGNORECASE),
    re.compile(r"^password$", re.IGNORECASE),
    re.compile(r"^sk-xxx", re.IGNORECASE),
    re.compile(r"^your[_-]", re.IGNORECASE),
    re.compile(r"^CHANGE[_-]?ME", re.IGNORECASE),
    re.compile(r"^TODO", re.IGNORECASE),
    re.compile(r"^xxx+$", re.IGNORECASE),
    re.compile(r"^placeholder", re.IGNORECASE),
]

def reject_placeholder(value: str, field_name: str) -> str:
    for pattern in _PLACEHOLDER_PATTERNS:
        if pattern.search(value):
            raise ValueError(
                f"{field_name} contains a placeholder value '{value}'. "
                f"Set a real value in .env or environment."
            )
    return value
```

### 4.2 Where to Apply Validators

| Validator Type | Use Case | Example |
|---|---|---|
| `Field(min_length=32)` | Built-in constraint | SECRET_KEY length |
| `Field(ge=1)` | Numeric minimum | Token expiry |
| `PositiveInt` / `NonNegativeInt` | Constrained types | Port, pool size |
| `@field_validator(mode="after")` | Placeholder rejection | SECRET_KEY, POSTGRES_PASSWORD |
| `@model_validator(mode="after")` | Cross-field checks | Production requires non-empty SMTP |
| `Literal["local", "staging", "production"]` | Enum constraint | ENVIRONMENT |

### 4.3 Environment-Aware Validation via model_validator

```python
from pydantic import model_validator
from typing_extensions import Self

class AppGeneralConfig(BaseSettings):
    APP_NAME: str = Field(default="PAPERY")
    ENVIRONMENT: Literal["local", "staging", "production"] = Field(default="local")
    DEBUG: bool = Field(default=False)

    @model_validator(mode="after")
    def enforce_production_rules(self) -> Self:
        if self.ENVIRONMENT == "production" and self.DEBUG:
            raise ValueError("DEBUG must be False in production")
        return self
```

This pattern extends to the composed class — e.g., reject empty `SMTP_*` in production.

---

## 5. Key Pydantic Settings v2 Features to Use

| Feature | Purpose |
|---|---|
| `SettingsConfigDict(env_file=".env")` | Load from dotenv |
| `case_sensitive=True` | Exact env var name matching |
| `extra="ignore"` | Don't fail on unrecognized env vars |
| `Field(description=...)` | Self-documenting config |
| `computed_field` + `@property` | Derived values (URIs, DSNs) |
| `field_validator(mode="after")` | Post-parse validation |
| `model_validator(mode="after")` | Cross-field validation |
| Constrained types (`PositiveInt`, etc.) | Built-in range checks |
| `Literal[...]` | Restrict to known values |

**Priority order** (highest wins): init args > env vars > .env file > defaults.

---

## 6. `.env.example` Template (D-17)

Single root file covering all modules. Group by service prefix per D-16.

```env
# ===== Application =====
APP_NAME=PAPERY
ENVIRONMENT=local          # local | staging | production
DEBUG=true

# ===== Security =====
SECRET_KEY=               # REQUIRED: min 32 chars, run: openssl rand -base64 42
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ===== PostgreSQL =====
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=papery
POSTGRES_PASSWORD=         # REQUIRED in staging/production
POSTGRES_DB=papery
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=10
POSTGRES_POOL_RECYCLE=3600
POSTGRES_POOL_PRE_PING=true
POSTGRES_POOL_TIMEOUT=30

# ===== Redis Cache (db=0) =====
REDIS_CACHE_HOST=localhost
REDIS_CACHE_PORT=6379
REDIS_CACHE_PASSWORD=
REDIS_CACHE_DB=0

# ===== Redis Queue (db=1) =====
REDIS_QUEUE_HOST=localhost
REDIS_QUEUE_PORT=6379
REDIS_QUEUE_PASSWORD=
REDIS_QUEUE_DB=1

# ===== Redis Rate Limit (db=2) =====
REDIS_RATE_LIMIT_HOST=localhost
REDIS_RATE_LIMIT_PORT=6379
REDIS_RATE_LIMIT_PASSWORD=
REDIS_RATE_LIMIT_DB=2

# ===== MinIO =====
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=papery
MINIO_USE_SSL=false

# ===== SMTP =====
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_TLS=true

# ===== CORS =====
CORS_ORIGINS=["http://localhost:3000"]

# ===== Admin Bootstrap =====
ADMIN_EMAIL=admin@papery.local
ADMIN_PASSWORD=            # REQUIRED: set a strong password
```

---

## 7. Gotchas and Recommendations

1. **No `env_prefix` on modules** — Since we use explicit prefixed field names (`POSTGRES_HOST`, `REDIS_CACHE_HOST`), do NOT use `env_prefix` on individual config classes. It would double-prefix: `POSTGRES_POSTGRES_HOST`.

2. **Only one `model_config`** — Define it exclusively on `AppConfig`. If any intermediate class also defines `model_config`, Python MRO picks one unpredictably and the others are silently ignored.

3. **`extra="ignore"` is essential** — Without it, any env var not matching a field causes a `ValidationError`. Docker and CI inject many system env vars.

4. **Import-time crash is intentional** — `settings = AppConfig()` in `__init__.py` means a bad `.env` file crashes the app before any request is served. This is the correct behavior for fail-fast.

5. **`computed_field` vs `@property`** — Use `computed_field` for values that should appear in `settings.model_dump()` (e.g., database URI). Use plain `@property` for truly internal helpers.

6. **Validator placement** — Put validators on the module where the field is defined, not on the composed class. This keeps validation co-located with the field it validates.

7. **Testing** — For tests, either use `AppConfig(_env_file=".env.test")` or pass values directly: `AppConfig(SECRET_KEY="x"*32, ...)`. Pydantic Settings accepts init kwargs that override env vars.

8. **CORS_ORIGINS as JSON list** — Use `list[str]` type with the env var containing a JSON array string. Pydantic v2 auto-parses JSON strings for complex types from env vars.

---

## 8. Implementation Checklist

- [ ] Create `backend/app/core/config/` directory with all modules
- [ ] Each module: `BaseSettings` subclass with typed fields + `Field(description=...)`
- [ ] `_validators.py`: placeholder rejection helper
- [ ] `__init__.py`: compose `AppConfig` via multiple inheritance, set `model_config`, export `settings`
- [ ] Add `@field_validator` for SECRET_KEY (min length + placeholder check)
- [ ] Add `@model_validator` for production safety checks (DEBUG=False, etc.)
- [ ] Use `computed_field` for `POSTGRES_URI`
- [ ] Create root `.env.example` with all vars grouped by service prefix
- [ ] Verify import-time crash on missing/invalid required config
- [ ] Write unit tests: valid config, placeholder rejection, missing required fields

---

*Research complete. Ready for implementation.*
