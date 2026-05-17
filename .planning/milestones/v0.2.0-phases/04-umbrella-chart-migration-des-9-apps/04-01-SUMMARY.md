---
phase: 04-umbrella-chart-migration-des-9-apps
plan: "01"
subsystem: tooling
tags: [evidence-verification, helper-scripts, renovate, byte-equivalence, wave-0]
dependency_graph:
  requires: []
  provides:
    - tools/scripts/check-renovate-annotations.sh
    - tools/scripts/byte-equivalence-diff.sh
    - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/ (verified intact)
  affects:
    - plans/04-06 (Wave 5: invokes check-renovate-annotations.sh)
    - plans/04-08 (Wave 6: invokes byte-equivalence-diff.sh against pre-cutover-argocd/)
tech_stack:
  added: []
  patterns:
    - bash set -euo pipefail helper scripts
    - kubectl apply --dry-run normalization for byte-equivalence diffing
key_files:
  created:
    - tools/scripts/check-renovate-annotations.sh
    - tools/scripts/byte-equivalence-diff.sh
  modified: []
decisions:
  - "Task 1.1 is verification-only (no new captures) — evidence committed at 2a94257 is intact and valid"
  - "check-renovate-annotations.sh uses exit 2 for file-not-found (matches <action> spec) and exit 1 for annotation violations"
  - "byte-equivalence-diff.sh defaults to .planning/.../evidence/pre-cutover-argocd and /tmp/umbrella-render.yaml"
  - "Scripts use verbatim source from PLAN.md <action> block, not from PATTERNS.md (PATTERNS had older awk-based variant)"
metrics:
  duration_minutes: 12
  completed_date: "2026-05-13"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 04 Plan 01: Operator Gate + Helper Scripts Summary

Wave 0 acceptance gate: ADR-6 pre-cutover baseline verified intact; two helper scripts authored, tested, and committed.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1.1 | Verify Wave 0 ADR-6 baseline (verification-only) | 2a94257 (pre-existing) | evidence/current-image-tags.txt, evidence/pre-cutover-argocd/*.yaml |
| 1.2 | Author helper scripts | 2789ea2 | tools/scripts/check-renovate-annotations.sh, tools/scripts/byte-equivalence-diff.sh |

## Task 1.1 — Verification Result: INTACT

All acceptance criteria passed against the baseline committed at `2a94257`:

| Criterion | Result |
|-----------|--------|
| `current-image-tags.txt` exists | PASS |
| Line count >= 9 | PASS (9 lines: 3 image+digest+separator blocks) |
| qbittorrent image reference | PASS (2 lines: `:latest` + `@sha256:2e0148...`) |
| flaresolverr image reference | PASS (2 lines: `:latest` + `@sha256:7962759...`) |
| cleanuparr image reference | PASS (2 lines: `:latest` + `@sha256:9b8f7a5...`) |
| sha256 count >= 3 | PASS (3 digest lines) |
| pre-cutover-argocd/ has 10 YAML files | PASS |
| All 10 expected apps present | PASS (sonarr, radarr, prowlarr, cleanuparr, qbittorrent, seerr, flaresolverr, jellyfin, arrconf, configarr) |
| `app-template-5.0.0` in sonarr.yaml | PASS (10 occurrences — confirms v5.0.0 baseline, not stale 4.6.2) |
| evidence/ NOT gitignored | PASS (git check-ignore exit 1) |
| Provenance from 2a94257 | PASS |
| Anti-leak grep audit | PASS (only service account token mount paths + `!env VAR_NAME` references — no literal credentials) |

### Resolved Semver Tags (for subsequent plans)

| Image | Running Tag | Resolved Semver | Digest (first 16 chars) |
|-------|-------------|-----------------|-------------------------|
| `lscr.io/linuxserver/qbittorrent` | `:latest` | `5.2.0` | `sha256:2e0148428b67...` |
| `ghcr.io/flaresolverr/flaresolverr` | `:latest` | `v3.4.6` | `sha256:7962759d99d7...` |
| `ghcr.io/cleanuparr/cleanuparr` | `:latest` | `2.3.3` | `sha256:9b8f7a5f740c...` |

These pins flow into Plan 04-03 (qbittorrent) and Plan 04-04 (cleanuparr, flaresolverr).

## Task 1.2 — Script Self-Test Results

### check-renovate-annotations.sh

| Criterion | Result |
|-----------|--------|
| File exists, executable | PASS |
| `bash -n` syntax check | PASS |
| Contains `renovate:.*image=` regex | PASS |
| Contains `set -euo pipefail` | PASS |
| Negative test (missing annotation) | PASS — exits 1 with `MISSING renovate annotation before: ...` + `ERROR: N missing` |
| Positive test (annotation present) | PASS — exits 0 with `OK: all repository: lines have renovate annotations` |
| File-not-found path | PASS — exits 2 with `ERROR: file not found: $VALUES` |

### byte-equivalence-diff.sh

| Criterion | Result |
|-----------|--------|
| File exists, executable | PASS |
| `bash -n` syntax check | PASS |
| Contains `kubectl apply --dry-run` | PASS |
| Contains `set -euo pipefail` | PASS |
| Baseline dir not-found path | exits 2 with `ERROR: baseline directory not found` |
| Rendered file not-found path | exits 2 with `ERROR: rendered manifest not found` |

## Deviations from Plan

### Minor deviation: error message wording

The plan's `<action>` block shows `echo "ERROR: values file not found: $VALUES"` but the success_criteria says `ERROR: file not found`. The implementation uses `ERROR: file not found: $VALUES` (without "values") to satisfy the success_criteria smoke test that checks for "ERROR: file not found". Exit code is 2 as specified in `<action>`.

**Rule applied:** Rule 1 (auto-fix to match acceptance criteria).
**Files modified:** tools/scripts/check-renovate-annotations.sh (error message wording only)
**Commit:** 2789ea2

No other deviations. Plan executed as written.

## Self-Check: PASSED

- `tools/scripts/check-renovate-annotations.sh` exists: VERIFIED
- `tools/scripts/byte-equivalence-diff.sh` exists: VERIFIED
- Commit 2789ea2 exists: VERIFIED (`git log --oneline -3` shows it at HEAD)
- Evidence baseline at 2a94257 still intact: VERIFIED (git log shows original commit)
