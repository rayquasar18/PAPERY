# Conventions — PAPERY

## Status

**Pre-development scaffold** — No application code exists yet. Conventions below are derived from:
- `CLAUDE.md` project instructions
- `CONTRIBUTING.md` guidelines
- `.gitignore` signals (Python + Next.js patterns)
- `.reference/open-notebook/` architecture patterns

## Planned Code Style

### Python (Backend)

- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes
- **Type hints:** Required on all functions (per CLAUDE.md)
- **Error handling:** Never silently swallow exceptions (per CLAUDE.md)
- **Comments/code:** English only
- **Linting:** Ruff (inferred from reference project)
- **Type checking:** mypy (inferred from `.mypy_cache/` in `.gitignore`)

### TypeScript (Frontend)

- **Naming:** `kebab-case` files, `PascalCase` components
- **Types:** TypeScript types required (per CLAUDE.md)
- **Style:** Likely Tailwind CSS (inferred from reference project patterns)

### Git Conventions

- **Commit format:** `<type>: <description>` (feat, fix, refactor, docs, test, chore, style, perf, ci)
- **Co-author:** `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- **Branch strategy:** Gitflow (main, develop, feature/*, hotfix/*, release/*)
- **Commit frequency:** Every change committed and pushed immediately

### Communication

- **User-facing:** Vietnamese (Tiếng Việt)
- **Code/docs/commits:** English

## Patterns to Establish

These patterns need to be decided during Phase 1:
- [ ] API error response format
- [ ] Logging strategy and levels
- [ ] Environment variable naming
- [ ] Database naming conventions
- [ ] Component file structure (frontend)
- [ ] State management patterns
- [ ] API client patterns

---
*Generated: 2026-04-01 from project scaffold analysis*
