# Phase 10: Dashboard, Admin UI & QuasarFlow Stubs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 10-dashboard-admin-ui-quasarflow-stubs
**Areas discussed:** Dashboard UX, Admin UI scope, QFlow async flow, CI/CD policy

---

## Dashboard UX

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid (Recommended) | Table/list-first with toggle to card view | ✓ |
| Table-first | Strict table/list only | |
| Card-first | Card-focused first | |

**User's choice:** Hybrid
**Notes:** User chose practical control set for this phase: Search + Sort only. Empty state must be actionable with create-project CTA.

---

## Admin UI scope

| Option | Description | Selected |
|--------|-------------|----------|
| Core full (Recommended) | users/tiers/rate-limits/settings with production-ready basic operations | ✓ |
| MVP minimal | users + tiers only | |
| Full advanced | include advanced/bulk analytics-heavy tooling | |

**User's choice:** Core full
**Notes:** Clarified architecture concern about enterprise practice. Decision locked: keep one shared frontend codebase; isolate admin via route and permission boundaries rather than separate app.

---

## QFlow async flow

| Option | Description | Selected |
|--------|-------------|----------|
| Polling trước (Recommended) | Polling default with future SSE-compatible contract | ✓ |
| SSE mặc định | SSE-first in this phase | |
| Dual mode | Polling + SSE both now | |

**User's choice:** Polling-first
**Notes:** Retry strategy selected: timeout + light bounded retry with backoff; expose terminal failed state for manual retry.

---

## CI/CD policy

| Option | Description | Selected |
|--------|-------------|----------|
| Verify-only CI (Recommended) | lint/type/test/build on PR/push | ✓ |
| CI + auto deploy | include branch-driven deployment now | |
| CI + manual deploy | verify CI + manual deploy gate | |

**User's choice:** Verify-only CI
**Notes:** Deployment automation intentionally deferred to keep Phase 10 scope focused.

---

## Claude's Discretion

- Exact numeric values for polling interval, timeout, retry count, and backoff profile.
- Exact component/module breakdown while preserving locked architectural decisions.

## Deferred Ideas

- Separate standalone admin frontend codebase.
- SSE-first or dual transport implementation in this phase.
- Deployment automation in this phase.
