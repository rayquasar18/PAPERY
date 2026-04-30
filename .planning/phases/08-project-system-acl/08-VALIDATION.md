---
phase: 08
slug: project-system-acl
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && uv run pytest tests/test_project_acl.py -q` |
| **Full suite command** | `cd backend && uv run pytest tests/test_project_*.py -q` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/test_project_acl.py -q`
- **After every plan wave:** Run `cd backend && uv run pytest tests/test_project_*.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | PROJ-01 | T-08-01 | Project create requires authenticated user and seeds owner membership | integration | `cd backend && uv run pytest tests/test_projects.py::test_create_project_owner_seed -q` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | PROJ-02 | T-08-02 | Soft-deleted projects are excluded from normal reads/lists | integration | `cd backend && uv run pytest tests/test_projects.py::test_owner_soft_delete_excluded_from_list -q` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 1 | PROJ-03 | T-08-03 | ACL enforces owner/editor/viewer matrix for read/write/admin actions | unit+integration | `cd backend && uv run pytest tests/test_project_acl.py -q` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 2 | PROJ-04 | T-08-04 | Invite tokens are one-time, role-bound, and expire after 7 days | integration | `cd backend && uv run pytest tests/test_project_invites.py -q` | ❌ W0 | ⬜ pending |
| 08-03-02 | 03 | 2 | PROJ-05 | T-08-05 | Only owner can mutate members; last-owner invariant preserved | integration | `cd backend && uv run pytest tests/test_project_members.py -q` | ❌ W0 | ⬜ pending |
| 08-04-01 | 04 | 2 | PROJ-06 | T-08-06 | Listing returns owned+shared with relationship_type, search, and updated_at DESC | integration | `cd backend && uv run pytest tests/test_project_listing.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_projects.py` — project CRUD + soft-delete behavior coverage
- [ ] `backend/tests/test_project_acl.py` — role matrix and permission boundaries
- [ ] `backend/tests/test_project_invites.py` — invite create/accept/replay/expiry scenarios
- [ ] `backend/tests/test_project_members.py` — member role changes and owner invariants
- [ ] `backend/tests/test_project_listing.py` — owned/shared/search/sort/pagination coverage

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Invite email rendering and delivery path | PROJ-04 | SMTP and template rendering may depend on environment services | Start local stack, create email invite, verify message template fields and acceptance link behavior end-to-end |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
