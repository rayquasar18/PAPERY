# STACK.md — Technology Stack

> **Status:** Pre-development (scaffold phase)
> Last updated: 2026-04-01

PAPERY is currently in the scaffold/planning stage. No application source code has been written yet. This document captures what is **confirmed** from existing project files, and what is **planned/inferred** from project signals (`.gitignore`, `README.md`, `CLAUDE.md`).

---

## 1. Project State

| Artifact | Exists? | Notes |
|---|---|---|
| Application source code | ❌ | Not yet written |
| `package.json` / `pyproject.toml` | ❌ | Not yet created |
| Docker / CI config | ❌ | Not yet created |
| Project scaffold files | ✅ | `README.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `.gitignore`, `LICENSE` |
| Planning config | ✅ | `.planning/config.json` — AI agent model profiles |
| Reference material | ✅ | `.reference/open-notebook/` — read-only architectural reference |

---

## 2. Confirmed: Languages & Runtimes

### 2.1 Python (Backend)
**Signal:** `.gitignore` contains comprehensive Python tooling exclusions.

| Signal | Detail |
|---|---|
| `__pycache__/`, `*.pyc`, `*.pyo` | Python bytecode |
| `.venv/`, `venv/`, `env/` | Python virtual environments |
| `poetry.lock` (ignored), `.pdm.toml` | Poetry / PDM package managers |
| `celerybeat-schedule`, `celerybeat.pid` | Celery task queue |
| `db.sqlite3` | SQLite (Django or similar) |
| `local_settings.py` | Django-style local settings pattern |
| `migrations/versions/` | Alembic database migrations |
| `.mypy_cache/`, `.pyre/`, `.pytype/` | Python type checkers |
| `pytest` cache (`.pytest_cache/`) | Python testing framework |
| `.ipynb_checkpoints` | Jupyter notebooks |

**Inferred Python version:** ≥ 3.11 (modern type hints, async/await patterns expected)

### 2.2 TypeScript / JavaScript (Frontend)
**Signal:** `.gitignore` contains Next.js and Node.js-specific exclusions.

| Signal | Detail |
|---|---|
| `/.next/`, `/out/` | Next.js build outputs |
| `/node_modules/` | Node.js packages |
| `*.tsbuildinfo`, `next-env.d.ts` | TypeScript / Next.js generated files |
| `.vercel` | Vercel deployment |
| `npm-debug.log*`, `yarn-debug.log*`, `yarn-error.log*` | npm / Yarn package managers |
| `/.pnp`, `.pnp.js`, `.yarn/install-state.gz` | Yarn PnP mode |
| `/coverage` | Test coverage output |

**Inferred:** Next.js (App Router or Pages Router), TypeScript, Node.js runtime.

---

## 3. Planned: Framework Stack (Inferred)

Based on `.gitignore` signals and the feature set described in `README.md`:

### 3.1 Backend
| Component | Technology | Confidence | Basis |
|---|---|---|---|
| Language | Python 3.11+ | High | `.gitignore` signals |
| Web framework | FastAPI | Medium | Alembic migrations signal + reference architecture |
| Task queue | Celery | Medium | `celerybeat-*` in `.gitignore` |
| Database migrations | Alembic | Medium | `migrations/versions/` in `.gitignore` |
| Package manager | Poetry or PDM | Medium | Both in `.gitignore` |
| Testing | Pytest | High | `.pytest_cache/` in `.gitignore` |
| Type checking | Mypy | Medium | `.mypy_cache/` in `.gitignore` |
| Notebooks/exploration | Jupyter | Low | `.ipynb_checkpoints` in `.gitignore` |

### 3.2 Frontend
| Component | Technology | Confidence | Basis |
|---|---|---|---|
| Language | TypeScript | High | `*.tsbuildinfo`, `next-env.d.ts` in `.gitignore` |
| Framework | Next.js | High | `/.next/`, `next-env.d.ts` in `.gitignore` |
| Runtime | Node.js | High | `/node_modules/` in `.gitignore` |
| Package manager | npm or Yarn | High | lock file patterns in `.gitignore` |
| Deployment target | Vercel (optional) | Low | `.vercel` in `.gitignore` |

### 3.3 AI / ML Layer (Planned)
Based on `README.md` feature descriptions:

| Feature | Technology Options | Notes |
|---|---|---|
| LLM orchestration | LangChain / LangGraph | Multi-agent research workflows required |
| Embedding & vector search | OpenAI, Cohere, or local | Semantic Q&A, cross-doc analysis |
| Document parsing | pdfplumber, python-docx, openpyxl | PDF, DOCX, XLSX support listed in README |
| Multi-language translation | LLM-based or DeepL | Structure-preserving translation |
| OCR (if needed) | Tesseract, Surya, or cloud OCR | For scanned PDFs |

---

## 4. Configuration

### 4.1 Environment Variables
`.gitignore` reveals the environment variable strategy:

```
.env                      # Base env file (gitignored)
.env*.local               # Local overrides (gitignored)
.env*.development         # Development env (gitignored)
.env*.production          # Production env (gitignored)
```

No `.env.example` exists yet. Expected variables (TBD):
- AI provider API keys (OpenAI, Anthropic, Google, etc.)
- Database connection strings
- JWT/auth secrets
- Storage configuration (S3 or local)

### 4.2 Planning Agent Config
`.planning/config.json` — AI agent model profiles used for internal development planning:

```json
{
  "model_profile": "quality",
  "model_overrides": {
    "gsd-planner": "opus",
    "gsd-roadmapper": "opus",
    "gsd-executor": "opus",
    "gsd-phase-researcher": "opus",
    "gsd-project-researcher": "opus",
    "gsd-research-synthesizer": "sonnet",
    "gsd-debugger": "opus",
    "gsd-codebase-mapper": "sonnet",
    "gsd-verifier": "sonnet",
    "gsd-plan-checker": "sonnet",
    "gsd-integration-checker": "sonnet",
    "gsd-nyquist-auditor": "sonnet"
  }
}
```

This is a meta-config for Claude Code agents — not part of the runtime application stack.

---

## 5. Development Tooling (Inferred)

| Tool | Signal |
|---|---|
| `ruff` | Expected (standard Python linter for modern projects) |
| `mypy` | `.mypy_cache/` in `.gitignore` |
| `pytest` | `.pytest_cache/` in `.gitignore` |
| `pre-commit` | Likely (common in Python projects using ruff + mypy) |
| `docker` / `docker compose` | Likely (not yet confirmed) |

---

## 6. Architecture Overview (Planned)

Based on `README.md` features and `.gitignore` signals, the expected architecture is:

```
┌──────────────────────────────────────────────────────┐
│           Frontend (Next.js / TypeScript)             │
│           Document viewer, chat UI, editor            │
├──────────────────────────────────────────────────────┤
│           REST API (FastAPI / Python)                 │
│           Document processing, AI orchestration       │
├──────────────────────────────────────────────────────┤
│           AI Layer                                    │
│           LLM, embeddings, multi-agent workflows      │
├──────────────────────────────────────────────────────┤
│           Data Layer                                  │
│           Relational DB + Vector store + File storage │
└──────────────────────────────────────────────────────┘
```

---

## 7. Open Decisions

The following stack decisions have not yet been finalized:

- [ ] Primary database: PostgreSQL vs SurrealDB vs other
- [ ] Vector store: pgvector vs Qdrant vs Weaviate vs Chroma
- [ ] File storage: Local filesystem vs S3-compatible
- [ ] Auth system: Clerk / Auth.js / Supabase Auth / custom JWT
- [ ] Task queue: Celery+Redis vs native async vs BullMQ (Node)
- [ ] Frontend styling: Tailwind CSS vs other
- [ ] Component library: Shadcn/ui vs Radix vs other
- [ ] Container orchestration: Docker Compose vs Kubernetes
- [ ] CI/CD: GitHub Actions vs other
- [ ] Monorepo vs multi-repo structure

---

*This document reflects the scaffold state of the project. Update as decisions are finalized and source code is added.*
