# Phase 8: Project System & ACL - Research

**Researched:** 2026-04-27
**Domain:** FastAPI backend project-domain ACL (owner/editor/viewer), membership, invite flow, project listing/search
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Keep three roles: `owner`, `editor`, `viewer`.
- **D-02:** Owner-only administration: only owner can manage members (invite, remove, change roles) and perform project-level administrative actions.
- **D-03:** Editor can modify project content/metadata but cannot manage membership.
- **D-04:** Viewer is strictly read-only.
- **D-05:** Project deletion is soft delete only in this phase.
- **D-06:** No restore endpoint in this phase (explicitly deferred) to keep scope tight.
- **D-07:** Soft-deleted projects must be excluded from normal listings immediately.
- **D-08:** Support both invite link and email invite in this phase.
- **D-09:** Invite expiration is fixed at 7 days.
- **D-10:** Role is selected at invite creation time and applied upon acceptance.
- **D-11:** Use one list endpoint covering both owned and shared projects.
- **D-12:** Each list item includes `relationship_type` (`owned` or `shared`) for frontend rendering.
- **D-13:** Search by project name.
- **D-14:** Default sorting is `updated_at DESC`.

### Claude's Discretion
- Exact schema shape for invite token metadata and acceptance payload.
- Internal ACL enforcement composition (dependency layout and service/repository boundaries) as long as D-01..D-04 remain strict.
- Pagination defaults and max page size for project listing endpoints.

### Deferred Ideas (OUT OF SCOPE)
- Project restore API after soft delete (deferred to a future phase).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROJ-01 | User can create a project (name, description) | Project model + `ProjectService.create_project` with owner ACL seed and usage limit dependency [VERIFIED: codebase] |
| PROJ-02 | User can view, edit, and soft-delete own projects | SoftDeleteMixin + repository soft-delete pattern + owner/editor/viewer read/write guards [VERIFIED: codebase] |
| PROJ-03 | Project has ACL — owner, editor, viewer roles | Dedicated membership table with role enum and uniqueness constraints [ASSUMED] |
| PROJ-04 | Owner can invite users to project via invite link or email | Invite entity with token hash, role-at-create, expiry 7 days, acceptance endpoint [ASSUMED] |
| PROJ-05 | Owner can change member roles or remove members | Owner-only admin dependency and member mutation service methods [VERIFIED: codebase] |
| PROJ-06 | User can list and search own projects (owned + shared with) | Single query merging owned/shared + `relationship_type` projection + name search + `updated_at DESC` [ASSUMED] |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Use layered architecture and existing conventions; keep data access in repositories, business logic in services [VERIFIED: codebase].
- Never copy/import code from `.reference/`; use only as conceptual reference [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/CLAUDE.md].
- Use English for technical artifacts/code/comments; communicate to user in Vietnamese [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/CLAUDE.md].
- Never commit secrets (`.env`, credentials) [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/CLAUDE.md].
- Keep soft-delete pattern, UUID public IDs, and repository-first query discipline [VERIFIED: codebase].

## Summary

Phase 8 should be planned as a backend domain extension that plugs into already-established patterns: `Router -> Dependency -> Service -> Repository -> Model` with shared auth dependencies and soft-delete semantics. This is strongly supported by existing files in `backend/app/api/dependencies.py`, `backend/app/repositories/base.py`, and service examples like `admin_service.py` [VERIFIED: codebase].

The most important planning principle is **strict separation of ACL authorization from project business actions**: owner-only member administration (D-02), editor content mutation (D-03), viewer read-only (D-04), and immediate exclusion of soft-deleted projects from all normal reads/lists (D-07) [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/.planning/phases/08-project-system-acl/08-CONTEXT.md].

**Primary recommendation:** Implement ACL with first-class DB entities (`project`, `project_member`, `project_invite`) and explicit dependency guards per operation, not ad-hoc role checks in routers [ASSUMED].

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | `>=0.115.0` (project minimum) | API routing + DI dependencies | Existing backend already uses dependency-injected auth/access patterns [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/pyproject.toml] |
| SQLAlchemy asyncio | `>=2.0.35` (project minimum) | Async ORM for models/repos | BaseRepository and AsyncSession are current canonical data path [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/repositories/base.py] |
| Alembic | `>=1.14.0` (project minimum) | DB migrations for new ACL tables | Existing migration tooling already configured [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/pyproject.toml] |
| Pydantic v2 | `>=2.10.0` (project minimum) | Request/response schema contracts | Existing route/service/schema style depends on it [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/pyproject.toml] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Redis | `redis[hiredis]>=5.2.0` | Invite token one-time consumption/rate limiting cache if needed | Use for revocation/consumption flags and anti-replay optimizations [ASSUMED] |
| slowapi | `>=0.1.9` | Invite/create/list endpoint rate limits | Use for abuse-prone endpoints (invite create/accept) [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/pyproject.toml] |
| aiosmtplib + Jinja2 | `>=3.0.0`, `>=3.1.0` | Email invite delivery templates | Use for D-08 email invite flow [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/pyproject.toml] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-house ACL checks in each router | Central ACL dependency classes | Less duplication, fewer inconsistent authorization bugs [ASSUMED] |
| Soft-delete flag only in service logic | BaseRepository soft-delete filter | Existing code already enforces this pattern globally [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/repositories/base.py] |

**Installation:**
```bash
cd backend && uv sync
```

## Architecture Patterns

### Recommended Project Structure
```text
backend/app/
├── models/
│   ├── project.py              # project + invite + membership ORM
│   └── __init__.py             # model registration for metadata
├── repositories/
│   ├── project_repository.py
│   ├── project_member_repository.py
│   └── project_invite_repository.py
├── services/
│   └── project_service.py      # orchestration + ACL rules
├── schemas/
│   └── project.py              # Create/Read/Update/List/Invite payloads
└── api/v1/
    └── projects.py             # endpoints + dependencies
```

### Pattern 1: Dependency-first authorization
**What:** Guard endpoints with dependencies resolving current user + project role before service mutation [VERIFIED: codebase].
**When to use:** Every project-scoped operation except public invite-accept endpoint [ASSUMED].
**Example:**
```python
# Source: backend/app/api/dependencies.py
class CheckUsageLimit:
    def __init__(self, metric: str) -> None:
        self.metric = metric
```

### Pattern 2: Repository-mediated soft delete
**What:** Use `BaseRepository.soft_delete()` and rely on `_not_deleted()` for read filtering [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/repositories/base.py].
**When to use:** Project delete endpoint and all list/detail repository methods [VERIFIED: codebase].

### Anti-Patterns to Avoid
- **Role checks inside SQL query builders only:** causes inconsistent 403/404 semantics at API layer [ASSUMED].
- **Hard-delete for project in Phase 8:** violates D-05 and creates irreversible audit loss [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/.planning/phases/08-project-system-acl/08-CONTEXT.md].
- **Multiple list endpoints (owned/shared separated):** contradicts D-11 and increases frontend coupling [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/.planning/phases/08-project-system-acl/08-CONTEXT.md].

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password/token crypto for invites | Custom crypto primitives | Existing secure token/JWT patterns + hashed token storage | Reduces crypto foot-guns [ASSUMED] |
| Row filtering for soft-delete | Per-query manual `deleted_at is NULL` everywhere | BaseRepository shared filter helper | Already standardized and testable [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/repositories/base.py] |
| API auth extraction | Manual cookie parsing in each route | `get_current_user` / `get_current_active_user` dependencies | Existing tested pattern [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/api/dependencies.py] |

**Key insight:** Reusing existing dependency/repository contracts is lower risk than introducing a new ACL framework in this phase [VERIFIED: codebase].

## Common Pitfalls

### Pitfall 1: Owner demotion deadlock
**What goes wrong:** Last owner is demoted/removed, leaving project without admin authority [ASSUMED].
**Why it happens:** Member update endpoint does not enforce minimum one owner invariant [ASSUMED].
**How to avoid:** Reject role change/remove when target is final owner; require ownership transfer flow [ASSUMED].
**Warning signs:** Project has members but zero `owner` rows [ASSUMED].

### Pitfall 2: Invite replay acceptance
**What goes wrong:** Same invite token accepted multiple times or by different users [ASSUMED].
**Why it happens:** Token not marked consumed atomically [ASSUMED].
**How to avoid:** Store invite token hash + `accepted_at`; enforce one-time transition with transaction/unique guarantee [ASSUMED].
**Warning signs:** Duplicate membership insert attempts from same invite ID [ASSUMED].

### Pitfall 3: Data leakage in list endpoint
**What goes wrong:** Shared projects from unrelated users appear due to incorrect joins [ASSUMED].
**Why it happens:** Ownership and membership filters combined incorrectly with OR precedence [ASSUMED].
**How to avoid:** Encapsulate query in repository method with explicit predicate groups and tests [ASSUMED].
**Warning signs:** User sees project UUID not present in owner/member relation tables [ASSUMED].

## Code Examples

### Auth dependency baseline
```python
# Source: backend/app/api/dependencies.py
async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_active:
        ...
    return user
```

### Soft-delete repository baseline
```python
# Source: backend/app/repositories/base.py
async def soft_delete(self, instance: ModelType) -> ModelType:
    instance.deleted_at = datetime.now(UTC)
    await self._session.commit()
    await self._session.refresh(instance)
    return instance
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Services querying SQLAlchemy directly | Repository layer with DI services | 2026-04-10 decisions log | New Project ACL code should be repository-first [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/.planning/STATE.md] |
| Ad-hoc exception formats | `PaperyHTTPException` + mapped codes | Phase 2 completion | ACL errors should use consistent 403/404/409 contracts [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/core/exceptions/__init__.py] |

**Deprecated/outdated:**
- Direct CRUD/service coupling without repository abstraction is no longer the project pattern [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/.planning/STATE.md].

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Need dedicated `project_member` table with unique `(project_id, user_id)` and role enum | Standard Stack / Architecture | Medium: migration redesign late in phase |
| A2 | Invite acceptance should be one-time with token hash and `accepted_at` | Pitfalls / Architecture | High: security and membership integrity bugs |
| A3 | Single list query should merge owned/shared with relationship projection in SQL | Phase Requirements / Architecture | Medium: pagination/sort inconsistencies |
| A4 | Redis should be used for optional invite replay hardening | Supporting Stack | Low: can fallback to DB-only safeguards |

## Open Questions (RESOLVED)

1. **Should invite link be account-bound or anonymous until acceptance?**
   - **RESOLVED:** Invite links remain shareable, but acceptance is authenticated and binds the invite to the currently signed-in PAPERY account at acceptance time.
   - **Why:** This preserves D-08 link convenience while preventing anonymous membership creation and keeping ACL state tied to a known user identity.
   - **Planning impact:** Invite creation may omit target email for link mode, but POST `/projects/invites/accept` must require authenticated user context and record `accepted_by_user_id`.

2. **403 vs 404 for unauthorized project access?**
   - **RESOLVED:** Return `404 Not Found` for unauthorized project detail/update/delete access when the caller lacks project visibility, and reserve `403 Forbidden` for authenticated users hitting a known project through an allowed read scope but attempting a higher-privilege action they are not permitted to perform.
   - **Why:** This minimizes existence disclosure for outsider UUID probing while still giving precise authorization feedback within established membership context.
   - **Planning impact:** Read/detail dependencies should hide inaccessible projects as not found; admin/member-mutation paths can use `403` after membership/read scope is established.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 | Backend runtime/testing | ✓ | 3.9.6 | Use project venv Python if 3.12 required |
| uv | Dependency management | ✓ | 0.10.9 | pip (partial) |
| docker | Local integration stack | ✓ | 29.2.1 | Native local services |
| node | Tooling scripts | ✓ | v25.8.0 | — |
| npm | Frontend/tooling scripts | ✓ | 11.11.0 | — |
| pytest | Validation commands | ✗ (not in PATH) | — | `uv run pytest` inside backend [ASSUMED] |
| alembic | Migration commands | ✗ (not in PATH) | — | `uv run alembic` inside backend [ASSUMED] |
| psql | Manual DB diagnostics | ✗ (not in PATH) | — | app-level tests/query verification |
| redis-cli | Manual Redis diagnostics | ✗ (not in PATH) | — | app-level health/tests |

**Missing dependencies with no fallback:**
- None blocking for planning stage [VERIFIED: local environment probes].

**Missing dependencies with fallback:**
- pytest/alembic CLI via `uv run ...` in backend environment [ASSUMED].

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (`asyncio_mode=auto`) [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/pyproject.toml] |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`) [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/pyproject.toml] |
| Quick run command | `cd backend && uv run pytest tests/test_app.py -q` [ASSUMED] |
| Full suite command | `cd backend && uv run pytest` [ASSUMED] |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROJ-01 | Create project with owner seed | integration | `cd backend && uv run pytest tests/test_projects.py::test_create_project_owner_seed -q` | ❌ Wave 0 |
| PROJ-02 | View/edit/soft-delete own project | integration | `cd backend && uv run pytest tests/test_projects.py::test_owner_soft_delete_excluded_from_list -q` | ❌ Wave 0 |
| PROJ-03 | ACL owner/editor/viewer matrix | unit+integration | `cd backend && uv run pytest tests/test_project_acl.py -q` | ❌ Wave 0 |
| PROJ-04 | Invite link + email acceptance role apply | integration | `cd backend && uv run pytest tests/test_project_invites.py -q` | ❌ Wave 0 |
| PROJ-05 | Owner role change/remove member rules | integration | `cd backend && uv run pytest tests/test_project_members.py -q` | ❌ Wave 0 |
| PROJ-06 | Combined owned/shared list + search/sort | integration | `cd backend && uv run pytest tests/test_project_listing.py -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/test_project_acl.py -q` [ASSUMED]
- **Per wave merge:** `cd backend && uv run pytest tests/test_project_*.py -q` [ASSUMED]
- **Phase gate:** Full suite green before `/gsd-verify-work` [ASSUMED]

### Wave 0 Gaps
- [ ] `backend/tests/test_projects.py` — core project CRUD + soft delete behavior
- [ ] `backend/tests/test_project_acl.py` — role matrix + permission boundaries
- [ ] `backend/tests/test_project_invites.py` — invite creation/accept/replay/expiry
- [ ] `backend/tests/test_project_members.py` — role changes + owner invariants
- [ ] `backend/tests/test_project_listing.py` — owned/shared/search/sort/pagination

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Existing cookie JWT auth dependencies [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/api/dependencies.py] |
| V3 Session Management | yes | Existing token family/blacklist patterns [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/api/v1/auth.py] |
| V4 Access Control | yes | Project role-based ACL (owner/editor/viewer) + owner-only admin actions [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/.planning/phases/08-project-system-acl/08-CONTEXT.md] |
| V5 Input Validation | yes | Pydantic schemas on request payloads [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/backend/pyproject.toml] |
| V6 Cryptography | yes | JWT/token handling from existing security module; no custom crypto [VERIFIED: codebase] |

### Known Threat Patterns for FastAPI + SQLAlchemy ACL stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on project UUID | Elevation of Privilege | Resolve project membership before returning resource; deny by default [ASSUMED] |
| Invite token replay | Tampering | One-time token consumption and expiration checks [ASSUMED] |
| Membership escalation by editor | Elevation of Privilege | Owner-only mutation dependency for member actions [VERIFIED: /Users/mqcbook/Documents/github/my-source/PAPERY/.planning/phases/08-project-system-acl/08-CONTEXT.md] |
| Search endpoint over-exposure | Information Disclosure | Filter by owner/member relation before search predicate [ASSUMED] |

## Sources

### Primary (HIGH confidence)
- `/Users/mqcbook/Documents/github/my-source/PAPERY/.planning/phases/08-project-system-acl/08-CONTEXT.md` - locked decisions, scope boundaries
- `/Users/mqcbook/Documents/github/my-source/PAPERY/.planning/REQUIREMENTS.md` - canonical PROJ-01..06 requirements
- `/Users/mqcbook/Documents/github/my-source/PAPERY/CLAUDE.md` - mandatory project constraints
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/api/dependencies.py` - auth/usage dependency patterns
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/repositories/base.py` - soft-delete + repository architecture pattern
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/models/base.py` - UUID/soft-delete mixins
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/app/core/exceptions/__init__.py` - API error model
- `/Users/mqcbook/Documents/github/my-source/PAPERY/backend/pyproject.toml` - backend stack + test framework config

### Secondary (MEDIUM confidence)
- `/Users/mqcbook/Documents/github/my-source/PAPERY/.planning/ROADMAP.md` - phase ordering and success criteria references
- `/Users/mqcbook/Documents/github/my-source/PAPERY/.planning/STATE.md` - established architecture decisions timeline

### Tertiary (LOW confidence)
- None (all external-tech claims requiring internet confirmation are tagged `[ASSUMED]`)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - derived from project `pyproject.toml` and existing backend modules.
- Architecture: MEDIUM - patterns are verified, but project/invite schema specifics are still discretionary.
- Pitfalls: MEDIUM - technically plausible but partly assumption-based until implementation decisions lock.

**Research date:** 2026-04-27
**Valid until:** 2026-05-27
