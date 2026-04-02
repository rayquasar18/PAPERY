# Phase 1: Backend Core Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 01-backend-core-infrastructure
**Areas discussed:** Project Structure, Database & Migrations, Docker Compose Setup, Config & Env vars

---

## Project Structure

### Repository Layout
| Option | Description | Selected |
|--------|-------------|----------|
| Monorepo kiểu Dify (Recommended) | backend/ và frontend/ cùng repo. Giống Dify (api/ + web/ + docker/). Chia sẻ Makefile, CI, docker-compose. | ✓ |
| Monorepo với nested src/ | v0 style: backend/src/app/ với nested src. Sâu hơn 1 level. | |

**User's choice:** Monorepo kiểu Dify
**Notes:** User wants to follow Dify enterprise patterns for infrastructure organization.

### Backend Directory Structure
| Option | Description | Selected |
|--------|-------------|----------|
| Monorepo kiểu Dify flat app/ (Recommended) | Flat backend/app/ structure (Dify-style). | ✓ |
| Nested src/app/ | v0 style backend/src/app/. | |

**User's choice:** Flat app/ (selected as part of Monorepo Dify recommendation)

### Package Manager
| Option | Description | Selected |
|--------|-------------|----------|
| uv (Recommended) | Fastest available, Rust-based, Dify has migrated to uv. | ✓ |
| Poetry | Mature, stable. Virtual env management. | |

**User's choice:** uv (part of Dify-style recommendation)
**Notes:** User emphasized wanting the latest tech stack across the board.

---

## Database & Migrations

### PostgreSQL Version
| Option | Description | Selected |
|--------|-------------|----------|
| PostgreSQL 17 (Recommended) | Latest stable with JSON improvements. | ✓ |
| PostgreSQL 16 | Stable, used by Dify. | |

**User's choice:** PostgreSQL 17

### Alembic Workflow
| Option | Description | Selected |
|--------|-------------|----------|
| Auto-generate (Recommended) | Dify-style: auto-generate from model changes, review before apply. | ✓ |
| Manual only | Write migration by hand. | |

**User's choice:** Auto-generate

### Database Naming
| Option | Description | Selected |
|--------|-------------|----------|
| snake_case (Recommended) | Standard PostgreSQL convention. | ✓ |
| PascalCase tables | Not common with PostgreSQL. | |

**User's choice:** snake_case

### Seed Data Strategy
| Option | Description | Selected |
|--------|-------------|----------|
| CLI scripts (Recommended) | Dify-style: scripts/ with CLI commands. | ✓ |
| In migrations | Seed in Alembic migrations. | |

**User's choice:** CLI scripts

### SQLAlchemy Pool Config
| Option | Description | Selected |
|--------|-------------|----------|
| Full pool config (Recommended) | Dify-style: all pool params configurable via env vars. | ✓ |
| Minimal (URL only) | Just database URL, default pool. | |

**User's choice:** Full pool config

### Test Database Strategy
| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral test DB (Recommended) | Create/drop per test run. Isolated. | ✓ |
| Transaction rollback | Faster but can leak state. | |

**User's choice:** Ephemeral test DB

### Migration Git Strategy
| Option | Description | Selected |
|--------|-------------|----------|
| Commit migrations (Recommended) | Migration files committed to git. Team sync, CI auto-migration. | ✓ |
| Gitignore migrations | Only local. Hard to sync. | |

**User's choice:** Commit migrations

---

## Docker Compose Setup

### Docker Compose Split
| Option | Description | Selected |
|--------|-------------|----------|
| Split (Dify-style, Recommended) | Separate middleware.yaml for dev, full stack for prod. | ✓ |
| All-in-one | Everything in one file. | |

**User's choice:** Split (Dify-style)

### Dockerfile Strategy
| Option | Description | Selected |
|--------|-------------|----------|
| Split Dev/Prod (Recommended) | Dockerfile.dev + Dockerfile for separate concerns. | ✓ |
| Multi-stage single file | One Dockerfile with build args. | |

**User's choice:** Split Dev/Prod

### Dev Setup Tool
| Option | Description | Selected |
|--------|-------------|----------|
| Makefile (Dify-style, Recommended) | make dev-setup, make dev-clean, etc. | ✓ |
| Shell scripts | scripts/ folder with shell scripts. | |
| Makefile + scripts/ | Combined approach. | |

**User's choice:** Makefile (Dify-style)
**Notes:** User initially needed explanation of what Makefile is. After understanding it as "enterprise shortcut commands", confirmed wanting Dify-style Makefile approach.

---

## Config & Environment Variables

### Pydantic Settings Structure
| Option | Description | Selected |
|--------|-------------|----------|
| Modular (Dify-style, Recommended) | Separate config modules composed via inheritance. | ✓ |
| Single file | All config in one config.py. | |

**User's choice:** Modular (Dify-style)

### Env Variable Naming
| Option | Description | Selected |
|--------|-------------|----------|
| Service prefix (Recommended) | POSTGRES_*, REDIS_*, MINIO_*, SMTP_*. | ✓ |
| App prefix (PAPERY_*) | All vars prefixed with PAPERY_. | |

**User's choice:** Service prefix

### Env File Strategy
| Option | Description | Selected |
|--------|-------------|----------|
| Per-component (Dify-style, Recommended) | Separate .env.example per component. | |
| Single root .env.example | One file for everything. | ✓ |

**User's choice:** Single root .env.example
**Notes:** Diverged from Dify pattern here — user prefers centralized env file.

### Startup Validation
| Option | Description | Selected |
|--------|-------------|----------|
| Strict validation (Recommended) | Reject placeholders, enforce minimums. | ✓ |
| Basic type check only | Only Pydantic type validation. | |

**User's choice:** Strict validation

---

## Claude's Discretion

- Extensions init pattern (FastAPI lifespan vs startup events)
- Logging setup and levels
- Test fixtures organization
- Pre-commit hook configuration

## Deferred Ideas

None — discussion stayed within phase scope
