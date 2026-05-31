---
phase: 28-generate-foundation
plan: "05"
subsystem: ci
tags: [ci, generate, idempotence, guard, tests-yml]
dependency_graph:
  requires: [28-03, 28-04]
  provides: [INTENT-03-ci-guard]
  affects: [.github/workflows/tests.yml]
tech_stack:
  added: []
  patterns: [generate-idempotence job, path trigger guard, D-09 isolation]
key_files:
  modified:
    - .github/workflows/tests.yml
decisions:
  - "Guard placed in tests.yml (not chart-lint.yml) per D-09 — isolates from mathieudutour auto-tagger"
  - "charts/arr-stack/files/** added to both PR and push path triggers (RESEARCH Pitfall 2)"
  - "CI-only change: no arrconf.image.tag co-bump required"
metrics:
  duration: "~5min"
  completed: "2026-05-31"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 1
---

# Phase 28 Plan 05: Generate Idempotence CI Guard Summary

**One-liner:** CI guard running `arrconf generate --check` in an isolated `generate-idempotence` job with `charts/arr-stack/files/**` path trigger, keeping the guard out of chart-lint.yml (D-09).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add charts/arr-stack/files/** path trigger | 83d3344 | .github/workflows/tests.yml |
| 2 | Add generate-idempotence job | 83d3344 | .github/workflows/tests.yml |

Both tasks were committed atomically in a single commit since they are both modifications to the same file and the path trigger is a prerequisite for the job to be meaningful.

## What Was Done

### Task 1: Path trigger

Added `'charts/arr-stack/files/**'` to both `on.pull_request.paths` and `on.push.paths` in `tests.yml`. This ensures that PRs modifying `intent.yml` or any generated config (e.g., `cross-seed/config.js`) trigger the `generate-idempotence` guard — without this, an operator who edits `intent.yml` directly would bypass the CI check entirely (RESEARCH Pitfall 2).

### Task 2: generate-idempotence job

Added a new parallel job `generate-idempotence` to `tests.yml` with:
- `runs-on: ubuntu-24.04`, `permissions: contents: read` (read-only, no write access)
- `defaults.run.working-directory: tools/arrconf` (same as the `test` job)
- Setup uv, Install dependencies steps copied verbatim from the `test` job
- Guard step running `arrconf generate --check --intent ../../charts/arr-stack/files/intent.yml --output-dir ../../charts/arr-stack/files/` with explicit paths (required because defaults are cwd-relative and CI cwd is `tools/arrconf`)
- Friendly `::error::` message on failure pointing to the fix command

The job is kept in `tests.yml` and NOT added to `chart-lint.yml` per D-09: the `chart-lint.yml` carries the `mathieudutour/github-tag-action` auto-tagger job, and mixing a generate guard there would risk interfering with the tag → GHCR release chain.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

```
grep -c "charts/arr-stack/files" .github/workflows/tests.yml  → 4 (2 path triggers + 2 in job step)
grep -q "generate-idempotence:" .github/workflows/tests.yml   → match (job defined)
grep -q "arrconf generate --check" .github/workflows/tests.yml → match
! grep -q "generate-idempotence" .github/workflows/chart-lint.yml → no match (D-09 preserved)
python3 yaml.safe_load(tests.yml) → valid YAML
git diff -- charts/arr-stack/values.yaml → empty (no tag bump)
```

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced. Guard is read-only (`permissions: contents: read`, `--check` flag writes nothing).

## Self-Check: PASSED

- [x] `.github/workflows/tests.yml` modified: confirmed (commit 83d3344, 34 insertions)
- [x] Commit 83d3344 exists: confirmed via `git log --oneline -3`
- [x] No file deletions: confirmed
- [x] No untracked files: confirmed
- [x] `charts/arr-stack/values.yaml` unchanged: confirmed (no diff)
- [x] `chart-lint.yml` unchanged: confirmed (no `generate-idempotence` reference)
