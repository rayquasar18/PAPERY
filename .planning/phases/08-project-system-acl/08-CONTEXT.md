# Phase 8: Project System & ACL - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement project management backend capabilities: project CRUD (with soft delete), ACL role model (owner/editor/viewer), member management, invite flows (link + email), and project listing/search for owned and shared projects. This phase defines the reusable authorization model for project-scoped resources.

</domain>

<decisions>
## Implementation Decisions

### ACL Roles & Permission Matrix
- **D-01:** Keep three roles: `owner`, `editor`, `viewer`.
- **D-02:** Owner-only administration: only owner can manage members (invite, remove, change roles) and perform project-level administrative actions.
- **D-03:** Editor can modify project content/metadata but cannot manage membership.
- **D-04:** Viewer is strictly read-only.

### Project Lifecycle
- **D-05:** Project deletion is soft delete only in this phase.
- **D-06:** No restore endpoint in this phase (explicitly deferred) to keep scope tight.
- **D-07:** Soft-deleted projects must be excluded from normal listings immediately.

### Invite & Membership Flow
- **D-08:** Support both invite link and email invite in this phase.
- **D-09:** Invite expiration is fixed at 7 days.
- **D-10:** Role is selected at invite creation time and applied upon acceptance.

### Project Listing & Search
- **D-11:** Use one list endpoint covering both owned and shared projects.
- **D-12:** Each list item includes `relationship_type` (`owned` or `shared`) for frontend rendering.
- **D-13:** Search by project name.
- **D-14:** Default sorting is `updated_at DESC`.

### Claude's Discretion
- Exact schema shape for invite token metadata and acceptance payload.
- Internal ACL enforcement composition (dependency layout and service/repository boundaries) as long as D-01..D-04 remain strict.
- Pagination defaults and max page size for project listing endpoints.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` — Phase 8 goal, requirements PROJ-01..PROJ-06, and success criteria.
- `.planning/REQUIREMENTS.md` — Canonical requirement definitions for Project System.
- `.planning/PROJECT.md` — Product constraints and architecture context.

### Prior Decisions That Constrain Phase 8
- `.planning/phases/06-tier-system-permissions/06-CONTEXT.md` — Tier/usage enforcement patterns and permission-check conventions to reuse.
- `.planning/phases/07-admin-panel-backend/07-CONTEXT.md` — User status model and established admin/service/repository patterns.

### Existing Backend Code Context
- `backend/app/api/dependencies.py` — Current auth dependencies and reusable access/usage dependency patterns.
- `backend/app/models/user.py` — User model and status semantics relevant for membership and invite acceptance.
- `backend/app/services/admin_service.py` — Service layer patterns (DI + repository orchestration).
- `backend/app/api/v1/auth.py` — Existing authenticated route behavior and cookie/JWT conventions.
- `backend/app/api/v1/users.py` — API style conventions for authenticated resource operations.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `get_current_user` / `get_current_active_user` dependencies for project endpoint protection.
- Existing repository + service architecture patterns already in use by admin/tier/auth services.
- Existing soft-delete model pattern (`SoftDeleteMixin`) and UUID/public-id conventions.

### Established Patterns
- Layered architecture: Router → Dependencies → Service → Repository → Model.
- Dependency-driven authorization checks (feature/usage checks in `dependencies.py`) can be mirrored for ACL checks.
- Auth transport remains HttpOnly cookie JWT and existing token semantics.

### Integration Points
- Add project-domain models/services/repositories/routes under existing backend structure.
- Integrate ACL checks through dependency/service layer before project read/update/member operations.
- Reuse user identity + status state during invite acceptance and member management operations.

</code_context>

<specifics>
## Specific Ideas

- Role governance is intentionally strict: owner is the only membership authority.
- Listing API should be frontend-friendly by returning ownership relationship directly in each item.
- Invite mechanism should support both convenience (link) and directed collaboration (email) from day one of this phase.

</specifics>

<deferred>
## Deferred Ideas

- Project restore API after soft delete (deferred to a future phase).

</deferred>

---

*Phase: 08-project-system-acl*
*Context gathered: 2026-04-27*