---
phase: 5
slug: user-profile-account-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pyproject.toml` or `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest tests/test_users.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_users.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | USER-01 | — | Auth required, returns own profile only | unit | `pytest tests/test_users.py::test_get_profile -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | USER-01 | — | Computed fields (has_password, oauth_providers) correct | unit | `pytest tests/test_users.py::test_profile_computed_fields -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | USER-02 | — | display_name validation (2-50 chars, allowed chars) | unit | `pytest tests/test_users.py::test_update_profile_validation -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | USER-02 | — | PATCH returns updated profile | integration | `pytest tests/test_users.py::test_update_profile -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | USER-02 | — | Avatar upload validates MIME + size, stores in MinIO | integration | `pytest tests/test_users.py::test_avatar_upload -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | USER-02 | — | Oversized file (>2MB) rejected with 400 | unit | `pytest tests/test_users.py::test_avatar_oversized -x` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 2 | USER-02 | — | Invalid MIME type rejected with 400 | unit | `pytest tests/test_users.py::test_avatar_invalid_type -x` | ❌ W0 | ⬜ pending |
| 05-02-04 | 02 | 2 | USER-02 | — | Avatar removal clears avatar_url, deletes MinIO objects | integration | `pytest tests/test_users.py::test_avatar_remove -x` | ❌ W0 | ⬜ pending |
| 05-02-05 | 02 | 2 | USER-04 | T-05-01 | Password verified before account deletion | integration | `pytest tests/test_users.py::test_delete_account_password -x` | ❌ W0 | ⬜ pending |
| 05-02-06 | 02 | 2 | USER-04 | T-05-02 | OAuth-only user uses email confirmation | integration | `pytest tests/test_users.py::test_delete_account_oauth -x` | ❌ W0 | ⬜ pending |
| 05-02-07 | 02 | 2 | USER-04 | T-05-03 | All sessions invalidated in Redis after delete | integration | `pytest tests/test_users.py::test_delete_invalidates_sessions -x` | ❌ W0 | ⬜ pending |
| 05-02-08 | 02 | 2 | USER-04 | — | Deleted user cannot authenticate (401) | integration | `pytest tests/test_users.py::test_deleted_user_auth_fails -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_users.py` — stubs for USER-01, USER-02, USER-04
- [ ] `tests/conftest.py` — shared fixtures (authenticated client, test user, mocked MinIO)
- [ ] Pillow install — `pillow` dependency in pyproject.toml

*Existing pytest infrastructure from prior phases covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Avatar displays correctly in browser | USER-02 | Visual verification of WebP rendering | Upload avatar via API, open presigned URL in browser, verify 200x200 and 50x50 display |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
