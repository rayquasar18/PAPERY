# CLAUDE.md — Project Instructions for AI Agents

> These instructions are **mandatory**. They override any default behavior.

## Project Overview

PAPERY is an AI-powered document intelligence platform. It helps users work with documents (PDF, DOCX, Excel, etc.) for research, Q&A, learning, extraction, citation, summarization, insight generation, multi-language translation (preserving document structure), and multi-agent research workflows that produce formatted outputs (scientific reports, templates, marketplace rules, etc.).

**This project is licensed under CC BY-NC 4.0 — commercial use is strictly prohibited.**

---

## 1. Git Workflow — MANDATORY

### 1.1 Commit Immediately After Every Change

- **Every code change MUST be committed and pushed immediately** — no batching, no waiting.
- One logical change = one commit. Do not accumulate uncommitted work.
- Write clear, descriptive commit messages (English) explaining the "why", not just the "what".
- Always push to the correct remote branch right after committing.

### 1.2 Branch Strategy (Gitflow)

| Branch | Purpose | Base | Merges into |
|---|---|---|---|
| `main` | Production-ready, stable releases | — | — |
| `develop` | Integration branch for features | `main` | `main` (via release) |
| `feature/*` | New features | `develop` | `develop` |
| `hotfix/*` | Urgent production fixes | `main` | `main` + `develop` |
| `release/*` | Release preparation & QA | `develop` | `main` + `develop` |
| `staging` | Pre-production testing | `develop` | — |

**Rules:**
- Never commit directly to `main` — only via `hotfix/*` or `release/*` merges.
- All feature work goes on `feature/<name>` branched from `develop`.
- Hotfixes branch from `main`, merge back to both `main` and `develop`.
- Always use descriptive branch names: `feature/pdf-parser`, `hotfix/auth-crash`, `release/v1.2`.
- Delete feature/hotfix branches after merge.

### 1.3 Commit Message Format

```
<type>: <short description>

<optional body explaining why>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `style`, `perf`, `ci`

---

## 2. `.reference/` Directory — READ-ONLY REFERENCE

### 2.1 Absolute Isolation

- `.reference/` contains cloned repositories and documents **for reference only**.
- These are **completely independent** from PAPERY source code.
- **NEVER** import, copy, symlink, or directly use any code from `.reference/` in the project.
- **NEVER** modify any file inside `.reference/`.
- **NEVER** let reference repos influence the project's dependency tree, configs, or structure.
- Reference material is for **reading, understanding patterns, and learning approaches** — then implement independently in PAPERY.

### 2.2 What's Inside

- `open-notebook/` — Open source document AI platform (architecture reference)
- Additional repos or documents may be added over time.

### 2.3 How to Use References

✅ DO: Read code to understand architectural patterns and approaches.
✅ DO: Learn from their solutions to similar problems.
✅ DO: Use as inspiration for PAPERY's own independent implementation.
❌ DON'T: Copy-paste code from references.
❌ DON'T: Add reference repos as git submodules or dependencies.
❌ DON'T: Reference their file paths in any PAPERY source file or config.

---

## 3. Code Quality

- Write clean, well-documented, production-quality code.
- Follow existing project conventions and patterns.
- Include type hints (Python) / TypeScript types (frontend).
- Write tests for new features and bug fixes.
- Handle errors gracefully — never silently swallow exceptions.

---

## 4. Communication

- When explaining, asking questions, or communicating with the user: **always use Vietnamese (Tiếng Việt)**.
- Code, comments, commit messages, documentation, and technical content: **English**.

---

## 5. Security

- Never commit secrets, API keys, tokens, or credentials.
- Use `.env` files for environment variables (already in `.gitignore`).
- Never commit `.env`, `credentials.json`, or similar files.

---

## 6. Project Naming

- This project is **PAPERY** — an independent, original project.
- Do not reference, mention, or compare to any specific commercial product names in the codebase or documentation.
