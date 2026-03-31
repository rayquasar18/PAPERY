# Testing — PAPERY

## Status

**Pre-development scaffold** — No tests exist yet. Testing strategy below is derived from:
- `CLAUDE.md` project instructions ("Write tests for new features and bug fixes")
- `.gitignore` signals (`.pytest_cache/` present)
- `.reference/open-notebook/` testing patterns

## Planned Testing Stack

### Backend (Python)

- **Framework:** pytest (confirmed via `.pytest_cache/` in `.gitignore`)
- **Async testing:** pytest-asyncio (needed for FastAPI async endpoints)
- **Mocking:** unittest.mock / AsyncMock
- **Coverage:** pytest-cov (to be configured)

### Frontend (TypeScript)

- **Framework:** Vitest (inferred from reference project)
- **Component testing:** Testing Library (@testing-library/react)
- **E2E:** TBD (Playwright or Cypress)

## Testing Patterns from Reference

### Backend Patterns (from open-notebook)
- Mock database calls at repository layer (`repo_query`)
- Test API endpoints via FastAPI TestClient
- Separate unit tests from integration tests
- Use fixtures for common test data

### Frontend Patterns (from open-notebook)
- Locale parity tests (ensure all i18n keys present in all languages)
- Component render tests with Testing Library
- Hook testing with renderHook
- Mock API calls at fetch layer

## To Establish

- [ ] Test directory structure (`tests/` for backend, `__tests__/` or co-located for frontend)
- [ ] CI pipeline for automated testing
- [ ] Minimum coverage thresholds
- [ ] Test data fixtures/factories
- [ ] Integration test strategy (with real DB or mocked)

---
*Generated: 2026-04-01 from project scaffold analysis*
