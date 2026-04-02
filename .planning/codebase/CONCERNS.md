# PAPERY — Codebase Concerns

> **Status:** Pre-implementation. No application source code exists yet (all backend/frontend was wiped in commit `348f121`). This document analyses technical debt, known issues, and risk areas derived from:
> 1. The **deleted codebase** (v1 backend — recoverable from git history).
> 2. The **current project skeleton** (docs, config, git structure).
> 3. The **planned feature set** described in README.md.
>
> Severity scale: 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Low

---

## 1. Project State Debt

### 1.1 Complete Code Wipe — Zero Implementation
- 🔴 **Severity: Critical**
- The entire backend (FastAPI/Python) and frontend (Next.js/React) were deleted in commit `348f121` ("Reset project: clean slate for new project requirements").
- The project is currently a documentation shell with no deployable code.
- Every feature listed in `README.md` (document ingestion, Q&A, citation, translation, multi-agent workflows) is unimplemented.
- **Risk:** The README describes a mature, feature-rich platform — there is zero code backing any of it. Contributors and users arriving via GitHub will find nothing runnable.

### 1.2 Prior Art in Git History — Re-use vs. Rebuild Ambiguity
- 🟠 **Severity: High**
- A substantial v1 codebase exists in git history (commits prior to `348f121`). It is fully recoverable.
- There is no explicit decision record about whether this code should be salvaged, refactored, or replaced from scratch.
- **Risk:** Without a documented decision, future contributors may unknowingly rebuild what already exists, or worse, restore old code that carries its own bugs and security issues documented below.

### 1.3 Stale Branch Structure
- 🟡 **Severity: Medium**
- Branches `develop`, `feature/base`, `hotfix/base`, `staging`, `release/v1`, `release/v2` all exist but all point to the pre-wipe codebase or empty placeholder commits.
- `release/v1` and `release/v2` diverged from a `Toricat/PAPERY` fork — the relationship to the current repo's ownership is unclear.
- **Risk:** Accidental merge of stale branches into `main` would reintroduce deleted/outdated code.

---

## 2. Security Concerns (from v1 Codebase — Still in Git History)

### 2.1 Weak Default Admin Password in `.env.example`
- 🔴 **Severity: Critical**
- `ADMIN_PASSWORD="123456"` is hardcoded as the default in `.env.example` (commit `faead34`).
- Even as an example value, this is dangerous: developers frequently copy `.env.example` to `.env` without changing defaults, especially in early development.
- **Recommendation:** Replace with a clearly invalid placeholder like `ADMIN_PASSWORD=CHANGE_ME_BEFORE_RUNNING`.

### 2.2 Refresh Token Transmitted in Request Body (Not HttpOnly Cookie)
- 🔴 **Severity: Critical**
- `POST /logout` and `POST /refresh-token` accept the refresh token via JSON body (`RefreshToken` schema), not via an `HttpOnly` cookie.
- The cookie-based approach was implemented but commented out in `auth.py`:
  ```python
  # response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, ...)
  ```
- Transmitting refresh tokens in the response body and accepting them in the request body exposes them to XSS attacks — any malicious script can read `localStorage` or intercept the body.
- **Recommendation:** Reinstate `HttpOnly` + `Secure` cookie for the refresh token.

### 2.3 Token Blacklist Uses Database, Not Redis — No Expiry Cleanup
- 🟠 **Severity: High**
- Access/refresh token blacklisting (`crud_token_blacklist`) stores revoked tokens in PostgreSQL.
- The `blacklist_tokens` function records `expires_at` but there is no evidence of a scheduled job to purge expired entries.
- Over time the blacklist table will grow unboundedly, degrading query performance on every authenticated request.
- **Recommendation:** Either migrate blacklist to Redis with native TTL expiry, or implement a periodic cleanup job.

### 2.4 File Upload Validation Relies Solely on MIME Type (Client-Supplied)
- 🟠 **Severity: High**
- In `documents.py`, the upload endpoint validates file type using `file.content_type` from the HTTP request:
  ```python
  content_type = file.content_type if file.content_type else "application/octet-stream"
  if content_type not in DOCUMENT_MIME_TYPES:
      raise CustomException(...)
  ```
- `file.content_type` is a client-supplied header — it can be trivially spoofed. An attacker can upload an executable, HTML file, or polyglot with `Content-Type: application/pdf`.
- **Recommendation:** Perform server-side magic-byte inspection (e.g., using `python-magic` or `filetype`) to verify actual file content type.

### 2.5 No File Size Limit Enforced at API Layer
- 🟠 **Severity: High**
- The `create_document` endpoint accepts `UploadFile` without any enforced maximum file size.
- `file.size` is used only for metadata recording, not for rejection.
- An unauthenticated attacker could not exploit this (auth is required), but any authenticated user could upload arbitrarily large files, exhausting storage and memory.
- **Recommendation:** Add a `max_upload_size` setting and enforce it before streaming to MinIO. FastAPI's `Request.body()` size limit or a custom middleware is needed.

### 2.6 CORS Configured with Wildcard Methods and Headers
- 🟡 **Severity: Medium**
- Default `.env.example` values: `CORS_METHODS=["*"]`, `CORS_HEADERS=["*"]`.
- Wildcard CORS configuration, especially combined with `CORS_CREDENTIALS=true`, can be exploited by cross-origin requests.
- Note: `CORS_CREDENTIALS=true` with `CORS_ORIGINS` containing specific origins is acceptable, but the wildcard methods/headers increases surface area.
- **Recommendation:** Explicitly enumerate allowed methods and headers. Never allow `credentials: true` with `origins: ["*"]` (browsers block it, but it indicates misconfiguration intent).

### 2.7 `python-jose` Library — Known Vulnerabilities
- 🟡 **Severity: Medium**
- The v1 backend used `python-jose ^3.3.0` for JWT encoding/decoding.
- `python-jose` has had known vulnerabilities (algorithm confusion attacks, CVE-2022-29217). It is also largely unmaintained.
- **Recommendation:** Migrate to `PyJWT` (actively maintained) or `authlib` for JWT operations in the new implementation.

### 2.8 MinIO Credentials Use Default Values
- 🟡 **Severity: Medium**
- Default `.env.example` values: `MINIO_ACCESS_KEY="minioadmin"`, `MINIO_SECRET_KEY="minioadmin"`.
- These are the out-of-the-box MinIO defaults. Developers who forget to change them expose object storage to anyone with network access.
- `MINIO_SECURE=false` by default disables TLS, meaning credentials and file contents travel unencrypted.
- **Recommendation:** Force-require non-default MinIO credentials on startup. Enable TLS in any non-local environment.

### 2.9 No Input Sanitization on Object Storage Path
- 🟡 **Severity: Medium**
- The MinIO object name is constructed as:
  ```python
  object_name = f"{project_uuid}/{filename}"
  ```
- `filename` comes directly from `file.filename` (user-supplied). If the filename contains `../` sequences or special characters, it could cause path traversal issues in the storage key namespace.
- **Recommendation:** Sanitize filenames (strip path separators, normalize to ASCII or UUID-based names) before using as object keys.

---

## 3. Architecture & Technical Debt (from v1)

### 3.1 `pyproject.toml` Lists Both `poetry` and `project` Sections Incorrectly
- 🟠 **Severity: High**
- The `pyproject.toml` mixes PEP 517 `[project]` metadata with `[tool.poetry]` and `[tool.poetry.dependencies]` sections — this is an inconsistent dual-mode configuration.
- Using `[project]` with Poetry 1.x's expected `[tool.poetry.dependencies]` leads to dependency management ambiguity.
- The `license` field was set to `"MIT"` despite the project having switched to `CC BY-NC 4.0`.
- **Recommendation:** Unify under either `[tool.poetry]` or `[project]` (PEP 621). Update license metadata.

### 3.2 No Connection Pooling Configuration for PostgreSQL
- 🟠 **Severity: High**
- `database.py` creates the async engine with no pool configuration:
  ```python
  async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
  ```
- No `pool_size`, `max_overflow`, `pool_timeout`, or `pool_recycle` parameters.
- Under load, the default pool can be exhausted or leak stale connections.
- **Recommendation:** Configure pool parameters explicitly, tuned to deployment environment.

### 3.3 Redis Retry Logic Uses `threading.Thread` + `asyncio.run()` Inside Async Application
- 🟠 **Severity: High**
- Both `redis.py` and `minio.py` implement background retry using:
  ```python
  threading.Thread(target=lambda: asyncio.run(redis_queue.enqueue(...)), daemon=True).start()
  ```
- Spawning a new event loop via `asyncio.run()` inside a thread within an already-running async application is an anti-pattern. It can cause event loop conflicts, resource leaks, and unpredictable behavior.
- **Recommendation:** Use `asyncio.create_task()` for background retry within the existing event loop, or use a proper background task system (Celery, arq, or FastAPI `BackgroundTasks`).

### 3.4 Celery and ARQ Both Present — Redundant Task Queue Systems
- 🟠 **Severity: High**
- The v1 backend had both `arq` and `celery` listed as dependencies (`pyproject.toml`).
- `redis_queue.py` implements a Celery-based queue, while `docker-compose.yml` runs an ARQ worker.
- These two systems serve the same purpose (async background task processing) and having both creates confusion, double maintenance burden, and potential for tasks to be routed incorrectly.
- **Recommendation:** Choose one task queue system and remove the other.

### 3.5 `create_tables()` Auto-Migration in Production
- 🟡 **Severity: Medium**
- `setup.py` defines `create_tables()` which runs `Base.metadata.create_all` on startup.
- Alembic is also present for proper schema migrations.
- Auto-creating tables bypasses migration history, making it impossible to track schema changes, perform rollbacks, or safely evolve the schema.
- **Recommendation:** Disable `create_tables_on_start` in production. All schema changes must go through Alembic migrations.

### 3.6 Paginated Queries Have N+1 Access Control Lookup Pattern
- 🟡 **Severity: Medium**
- `read_projects` fetches all ACL entries for a user, extracts `resource_id` list, then queries projects with `id__in=project_ids`.
- This produces two separate queries. For large datasets (many projects per user), the `id__in` list can become very large.
- Similar patterns exist for documents and chat sessions.
- **Recommendation:** Use JOIN-based queries to fetch resources with their ACL in a single database round-trip.

### 3.7 Sequence Number Race Condition in Chat Messages
- 🟡 **Severity: Medium**
- `chat_messages.py` computes the next sequence number via a raw SQL `MAX()` query:
  ```python
  result = await db.execute(text("SELECT MAX(sequence_number) FROM chat_message WHERE ..."))
  max_seq = result.scalar() or 0
  next_seq = max_seq + 1
  ```
- This is not atomic. Under concurrent requests (e.g., two messages sent simultaneously), both could receive the same `sequence_number`, creating duplicate sequence values.
- **Recommendation:** Use a database sequence, `SERIAL`/auto-increment column, or a `SELECT ... FOR UPDATE` lock.

### 3.8 `meta_info` Column Typed as `Text` but Annotated as `dict`
- 🟡 **Severity: Medium**
- In `document.py` (model): `meta_info: Mapped[dict] = mapped_column(Text, nullable=True)`.
- Storing a dict in a `Text` column requires manual serialization/deserialization. SQLAlchemy will not automatically serialize dicts to JSON text, and this type mismatch will cause runtime errors.
- **Recommendation:** Use `mapped_column(JSON)` or `mapped_column(JSONB)` for PostgreSQL.

### 3.9 Soft Delete Not Enforced on All Query Paths
- 🟡 **Severity: Medium**
- Most queries pass `is_deleted=False` explicitly, but this relies on developers remembering to include it on every query.
- Some admin endpoints (e.g., `admin_read_document`) query by `id` without the `is_deleted` filter, which means deleted documents can still be retrieved by admins.
- **Recommendation:** Implement a global query filter (SQLAlchemy event or custom CRUDBase method) that automatically excludes soft-deleted records, with an explicit opt-in to include them.

### 3.10 Document Types Limited to PDF, DOCX, TXT — Mismatched with README
- 🟢 **Severity: Low**
- `DOCUMENT_MIME_TYPES` in `document.py` only supports `text/plain`, `application/msword`, and `application/pdf`.
- README promises support for XLSX, PPTX, CSV, Markdown, and more.
- **Risk:** Feature-documentation mismatch could mislead contributors about the actual scope needed.

---

## 4. Performance Concerns

### 4.1 No Caching Layer for Document/Project Data
- 🟡 **Severity: Medium**
- Redis infrastructure is present but used only for token blacklisting and rate limiting, not for caching frequently accessed data.
- Every request re-queries PostgreSQL for user data, project membership, and ACL checks.
- **Recommendation:** Cache user profiles and ACL lookups in Redis with short TTLs (e.g., 60s). Invalidate on update/delete.

### 4.2 File Uploads Are Fully Buffered in Memory
- 🟡 **Severity: Medium**
- In `create_document`, the entire uploaded file is passed to `minio.upload_file(file.file, ...)`. FastAPI stores the file in memory for small files and as a temp file for large ones, but the MinIO client streams from the file object.
- The problem: `file.size` (used as `length`) is FastAPI's reported size from Content-Length — if the client lies or the header is absent, the upload may fail silently or upload wrong data.
- **Recommendation:** Always stream-check file size server-side. Consider chunked/multipart upload for large documents.

### 4.3 Presigned URLs Generated On Every Document Read Request
- 🟢 **Severity: Low**
- `read_document` generates a new presigned MinIO URL on every request. Presigned URL generation is a crypto operation and an external API call.
- For read-heavy workloads, this adds latency on every document fetch.
- **Recommendation:** Cache presigned URLs in Redis with TTL slightly shorter than the presigned URL expiry window (default: 3600s).

### 4.4 Uvicorn Running with `--reload` in Docker
- 🟠 **Severity: High**
- `docker-compose.yml` runs: `command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- `--reload` enables file watching for hot-reload — this is a development-only flag that adds significant overhead, disables worker process management, and should never run in production or staging.
- **Recommendation:** Use Gunicorn with UvicornWorker for production. The commented-out gunicorn command in `docker-compose.yml` is the correct approach.

---

## 5. Infrastructure & Operations Concerns

### 5.1 No Health Check Endpoints Documented
- 🟡 **Severity: Medium**
- Redis and MinIO both have `health_check()` methods, but there is no `/health` or `/healthz` API endpoint exposed.
- Without health endpoints, container orchestration (Kubernetes, Docker Swarm) cannot determine if the application is ready to serve traffic.

### 5.2 Single Redis Instance for Three Purposes
- 🟡 **Severity: Medium**
- The `.env.example` uses the same Redis instance for cache, queue, and rate limiting (all point to `localhost:6379`), with only different logical databases (0, 1).
- Comment in `.env.example` warns: "the recommendation is using two separate containers for production."
- A single Redis failure takes down caching, task queuing, and rate limiting simultaneously.

### 5.3 PostgreSQL Version Pinned to `postgres:13`
- 🟢 **Severity: Low**
- `docker-compose.yml` uses `postgres:13` — PostgreSQL 13 reached End of Life in November 2025.
- **Recommendation:** Upgrade to PostgreSQL 16 or 17.

### 5.4 No Alembic Migrations Directory Tracked in Repository
- 🟠 **Severity: High**
- `.gitignore` includes `migrations/versions/` — this means all Alembic migration files are excluded from version control.
- Without migration history tracked in git, it is impossible to reproduce the database schema from scratch, roll back changes, or collaborate on schema evolution.
- **Recommendation:** Remove `migrations/versions/` from `.gitignore`. Migration files must be committed.

### 5.5 Worker Dockerfile Separate but No Worker Source Code
- 🟡 **Severity: Medium**
- `docker-compose.yml` references a `Dockerfile.worker` and runs `arq app.core.worker.settings.WorkerSettings`.
- Worker task definitions and registration are ad-hoc (registered at runtime via `redis_queue.register_function()`), not in a central worker module.
- **Recommendation:** Centralize all worker task definitions in a dedicated `workers/` module.

---

## 6. Code Quality & Maintainability

### 6.1 No Test Coverage
- 🟠 **Severity: High**
- The v1 codebase had `pytest` and `pytest-mock` as dependencies, and a pytest Docker service was defined in `docker-compose.yml` (commented out).
- No test files were found in the git history.
- **Recommendation:** Establish a minimum coverage baseline before adding new features. Critical paths (auth, document upload, ACL) must have integration tests.

### 6.2 Inconsistent Language in Code Comments
- 🟢 **Severity: Low**
- Many docstrings and inline comments in the v1 backend are written in Vietnamese (e.g., `"""Đăng nhập và lấy access token."""`, `# Lấy access control project`).
- Per `CLAUDE.md`, code comments must be in English.
- **Recommendation:** Establish and enforce the English-only comment policy from the start of the new implementation.

### 6.3 `CONTRIBUTING.md` Instructs Merging to `main` Directly
- 🟡 **Severity: Medium**
- `CONTRIBUTING.md` says: "Open a Pull Request to the main repository" with no mention of the `develop` branch.
- `CLAUDE.md` explicitly prohibits direct commits to `main` (all work goes to `develop` first via Gitflow).
- These two documents contradict each other.
- **Recommendation:** Update `CONTRIBUTING.md` to reflect the Gitflow process defined in `CLAUDE.md`.

### 6.4 LICENSE Metadata Mismatch
- 🟡 **Severity: Medium**
- `pyproject.toml` (v1) declared `license = "MIT"`, but the project LICENSE file is `CC BY-NC 4.0`.
- These are fundamentally different licenses with different permissions. Any package metadata declaring MIT would be legally inaccurate.
- **Recommendation:** Ensure all `pyproject.toml`, `package.json`, and metadata files declare `CC-BY-NC-4.0`.

### 6.5 `CODE_OF_CONDUCT.md` References Personal Email
- 🟢 **Severity: Low**
- The enforcement contact in `CODE_OF_CONDUCT.md` is `igor.magalhaes.r@gmail.com` — a personal email from the Contributor Covenant template that was never updated.
- **Recommendation:** Replace with an official project contact email.

### 6.6 `datetime.utcnow()` Usage (Deprecated)
- 🟢 **Severity: Low**
- `auth.py` uses `datetime.utcnow()` which is deprecated in Python 3.12+.
- `TimestampMixin` uses `datetime.now(UTC)` correctly, but scattered `datetime.utcnow()` calls will produce deprecation warnings and eventually break.
- **Recommendation:** Replace all `datetime.utcnow()` with `datetime.now(UTC)`.

---

## 7. Planned Feature Risks

### 7.1 Multi-Agent Research Workflows — Complexity Cliff
- 🟠 **Severity: High (Design Risk)**
- Multi-agent workflows are the most architecturally complex feature in the roadmap. They require: agent orchestration, state management across long-running tasks, error recovery, output formatting, and template rendering.
- None of this is scaffolded. There is no task queue designed for multi-step workflows, no agent framework selected, and no data model for workflow state.
- **Recommendation:** Define the agent architecture (LangGraph, CrewAI, custom FSM, etc.) early. This decision affects the entire data model and infrastructure.

### 7.2 Multi-Language Translation with Structure Preservation
- 🟠 **Severity: High (Design Risk)**
- "Preserving original structure and formatting" during document translation is a hard, unsolved problem — especially for PDFs (which encode layout, not semantics).
- No document processing pipeline (extraction, layout analysis, re-rendering) has been designed or started (the two empty files `layout-document.py` and `read-document.py` from commit `faead34` were stubs only).
- **Recommendation:** Prototype translation with structure preservation on multiple document types before committing to it as a feature.

### 7.3 Knowledge Graph Generation — Infrastructure Gap
- 🟡 **Severity: Medium (Design Risk)**
- The roadmap includes "Knowledge graph and topic clustering." This requires a graph database or graph-capable storage (Neo4j, Weaviate, or vector DB with graph extensions).
- The current infrastructure design (PostgreSQL + Redis + MinIO) has no provision for graph storage.
- **Recommendation:** Determine whether this is a v1 feature or future roadmap item and plan infrastructure accordingly.

### 7.4 Template Marketplace — License Compliance Risk
- 🟡 **Severity: Medium (Legal Risk)**
- A community template marketplace means user-generated content distributed under the platform's `CC BY-NC 4.0` license.
- If contributors upload templates they don't own (copyrighted academic templates, proprietary document formats), PAPERY could face IP claims.
- **Recommendation:** Design a terms-of-service and upload policy that clarifies contributor IP ownership and platform usage rights before launching the marketplace.

---

## 8. Summary Table

| # | Area | Concern | Severity |
|---|------|---------|----------|
| 1.1 | Project State | No application code exists | 🔴 Critical |
| 2.1 | Security | Weak default admin password in `.env.example` | 🔴 Critical |
| 2.2 | Security | Refresh token in response body, not HttpOnly cookie | 🔴 Critical |
| 2.3 | Security | Token blacklist has no expiry cleanup | 🟠 High |
| 2.4 | Security | File type validated via client-supplied MIME type | 🟠 High |
| 2.5 | Security | No enforced file upload size limit | 🟠 High |
| 3.2 | Architecture | No DB connection pool configuration | 🟠 High |
| 3.3 | Architecture | `asyncio.run()` inside thread inside async app | 🟠 High |
| 3.4 | Architecture | Celery + ARQ both present — redundant systems | 🟠 High |
| 4.4 | Performance | `--reload` flag in Docker (dev-only, used everywhere) | 🟠 High |
| 5.4 | Operations | `migrations/versions/` excluded from git | 🟠 High |
| 3.6 | Architecture | N+1-style ACL lookup pattern on list endpoints | 🟡 Medium |
| 3.7 | Architecture | Race condition in chat message sequence numbers | 🟡 Medium |
| 3.8 | Architecture | `dict` mapped to `Text` column (type mismatch) | 🟡 Medium |
| 7.1 | Feature Risk | Multi-agent workflow complexity — no design | 🟠 High |
| 7.2 | Feature Risk | Structure-preserving translation — unsolved problem | 🟠 High |

---

*Generated: 2026-04-01*
