# Phase 10 Validation Notes

Updated: 2026-04-30
Phase: 10-dashboard-admin-ui-quasarflow-stubs
Scope: Plan 10-04 verify-only CI alignment

## Canonical Local Verify Commands

### Frontend
```bash
cd frontend && pnpm lint && pnpm typecheck && pnpm build
```

### Backend
```bash
cd backend && make verify
```

`make verify` expands to:
```bash
uv run ruff check .
uv run mypy app/
uv run pytest -q
```

## GitHub Actions Verify Workflow

Workflow file:
- `.github/workflows/verify.yml`

Trigger matrix:
- push to `main`
- push to `develop`
- push to `feature/**`
- push to `hotfix/**`
- push to `release/**`
- all `pull_request` events

Jobs:
- `backend` — setup Python 3.12 + uv, then run lint, mypy, pytest
- `frontend` — setup Node 22 + pnpm, then run lint, typecheck, build

## Verify-only Policy Compliance

Confirmed exclusions:
- no deploy job
- no publish/release job
- no environment promotion steps
- no secret-requiring delivery stage

## Local Validation Results

### Frontend
Status: PASS

Command run:
```bash
cd frontend && pnpm lint && pnpm typecheck && pnpm build
```

Notes:
- `pnpm lint` emits existing React Compiler compatibility warnings in unrelated pre-existing files (`register-form.tsx`, `data-table.tsx`) but does not fail.
- `pnpm typecheck` passes.
- `pnpm build` passes.

### Backend
Status: FAILING REPOSITORY BASELINE

Command run:
```bash
cd backend && make verify
```

Outcome:
- Phase 10 scoped files were corrected to satisfy their own lint issues.
- Repository-wide backend verify still fails because of numerous pre-existing lint violations outside phase 10 scope (for example in `app/api/v1/billing.py`, `app/infra/oauth/base.py`, `tests/test_password_reset.py`, `tests/test_users.py`, and other older files).

Interpretation:
- CI workflow is valid and verify-only.
- Frontend command surface is canonical and green.
- Backend canonical command surface is in place, but current repository baseline is not yet globally green.
- A follow-up cleanup pass is required if the team wants the backend CI job to pass immediately on this branch.

## Troubleshooting Notes

- If GitHub Actions frontend install fails, ensure `frontend/package-lock.json` remains committed and in sync with `package.json`.
- If backend verify fails in CI, compare failing files against local `make verify` output before changing workflow logic.
- Do not weaken the workflow by skipping lint or type-check to compensate for repository baseline issues.
