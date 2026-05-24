---
phase: 17-arrconf-ui-ci-coverage
plan: 17-A
status: complete
closed: 2026-05-24
retroactive: true
commits:
  - 9ea0ba2  # docs(17): capture phase context — arrconf-ui CI coverage
  - 31829e5  # feat(17): arrconf-ui CI coverage
  - 9f60f00  # chore(17): trigger tests.yml on tools/arrconf-ui/** path (Scenario 1 probe)
  - c53c9a3  # fix(17): commit arrconf-ui lockfiles for deterministic CI
  - 04e0e69  # docs(17): close Phase 17 — 3/3 CI jobs green + SC#3 dispositive
requirements_addressed:
  - REQ-arrconf-ui-ci-coverage
key_files:
  created:
    - tools/arrconf-ui/uv.lock
    - tools/arrconf-ui/web/package-lock.json
  modified:
    - .github/workflows/tests.yml
    - README.md
---

# Phase 17 Summary — arrconf-ui CI coverage

## What shipped

Extended `tests.yml` to cover the `tools/arrconf-ui/**` path with 2 new jobs:
- **arrconf-ui-backend** — `ruff format --check` + `ruff check` + `mypy .` + `pytest -q` (32 tests pass, 13 files mypy-clean) on the FastAPI backend
- **arrconf-ui-frontend** — `npm ci` + `npm run check` + `npm run typecheck` + `npm run build` on the Svelte frontend (92 files / 0 errors)

Path filter on `tests.yml` extended to include `tools/arrconf-ui/**` so UI changes trigger the new jobs.

Architectural SC#3 (D-17-WORKFLOW-01): `chart-lint.yml` is **intentionally NOT modified** — UI-only PRs do not trigger auto-tag (the auto-tag is reserved for chart/arrconf releases, not UI iterations).

## Why it shipped this way

The v0.4.0 Phase 15 introduced `arrconf-ui` (local config UI) but didn't wire up CI coverage. Without it, regressions would only surface at runtime. Phase 17 closes this gap.

## Success criteria status

| SC | Result | Evidence |
|----|--------|----------|
| SC#1 — 2 new jobs visible | ✓ | Commit `c53c9a3` triggers test + arrconf-ui-backend + arrconf-ui-frontend |
| SC#2 — Jobs are green | ✓ | 3/3 green on `c53c9a3` (closure commit) |
| SC#3 — Architectural isolation | ✓ | `chart-lint.yml` unchanged (verified `git diff --stat`) — UI-only PRs do NOT trigger auto-tag |

## Lessons

- **Lockfiles oversight** from Phase 15 (`uv.lock` and `package-lock.json` not committed) surfaced via `uv sync --frozen` failures and was fixed via `c53c9a3`. Worth adding a CI guard or pre-commit hook to prevent lockfile drift on future Python/Node sub-projects.
- **Path filter semantics**: `tests.yml` triggers ALL jobs (test + arrconf-ui-backend + arrconf-ui-frontend) on any matching path (`tools/arrconf/**` OR `tools/arrconf-ui/**` OR `schemas/**` OR `examples/**` OR `.github/workflows/tests.yml`). The 3 jobs are not path-scoped within the workflow — they all fire together. This is by design (D-17-WORKFLOW-01) and matches GitHub Actions convention (workflow-level path filter, not job-level).

## Note on this SUMMARY

Phase 17 was executed inline (pre-`/gsd-execute-phase` worktree convention) and no SUMMARY.md was written at the time. This file is a **retroactive close artifact** generated 2026-05-24 during v0.5.0 milestone archive, sourced from the 5 phase commits and the closure note in `.planning/ROADMAP.md`. Source of truth remains the commits + ROADMAP entry; this file is a convenience for milestone archival tooling.
