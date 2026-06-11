---
phase: 30-cross-seed
plan: "03"
subsystem: helm-ci
tags: [cross-seed, helm, ci, operator-runbook]
dependency_graph:
  requires: ["30-02"]
  provides: ["XSEED-03-ci-surface", "cross-seed-operator-runbook"]
  affects: [".github/workflows/chart-lint.yml", "README.md"]
tech_stack:
  added: []
  patterns:
    - "per-alias cp loop in CI Vendor step for Helm 4 multi-alias workaround"
    - "renovate synthetic-test threshold update after new alias addition"
key_files:
  created:
    - ".planning/phases/30-cross-seed/30-OPERATOR-RUNBOOK.md"
  modified:
    - ".github/workflows/chart-lint.yml"
    - "README.md"
decisions:
  - "Threshold raised from 10 to 12 (not 13) per plan spec: cross-seed adds 2 new renovate-tracked repository lines; actual count is 13 which passes the >= 12 gate"
  - "CI alias loop now explicitly copies app-template to charts/arr-stack/charts/cross-seed — idempotent, adds < 1s CI time"
  - "Runbook references only key NAMES (PROWLARR_API_KEY, QBT_USER, QBT_PASS), never values — T-30-09 threat mitigated"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-31"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
---

# Phase 30 Plan 03: CI + Operator Surface Summary

CI resolves the 12th helm alias (cross-seed) via explicit per-alias copy loop; renovate synthetic test threshold raised to 12; README local-verification loop updated; operator runbook documents PVC + host dir pre-reqs, post-sync verification, out-of-stack teardown, and rollback.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Update chart-lint.yml alias loop + image-count threshold + README | 4a05899 | `.github/workflows/chart-lint.yml`, `README.md` |
| 2 | Create operator runbook for PVC + host dir + teardown | a197ac0 | `.planning/phases/30-cross-seed/30-OPERATOR-RUNBOOK.md` |

## What Was Built

**Task 1 — CI alias unpack + threshold update:**

In `.github/workflows/chart-lint.yml`, the "Vendor app-template" step previously only unpacked the `app-template-5.0.0.tgz` tarball (single `tar` command). This produced `charts/arr-stack/charts/app-template/` but no per-alias directories. For Helm 3.18 to resolve `alias: cross-seed` in `Chart.yaml`, it needs `charts/arr-stack/charts/cross-seed/` to exist. The fix adds a `for alias in ... cross-seed; do cp -r ... done` loop (12 aliases total) idempotent-guarded by `[ ! -d ... ]`. The comment is updated from "10 aliases" to "12 aliases".

The `customManagers regex synthetic test` threshold was raised from `< 10` to `< 12`: cross-seed adds 2 renovate-tracked `repository:` lines (initContainer + main container, both `ghcr.io/cross-seed/cross-seed`). The actual current count is 13 (11 pre-existing + 2 cross-seed), which passes the `>= 12` gate. All three occurrence sites updated: step name, condition, and both print statements.

In `README.md`, the local-verification alias loop (`for alias in ...`) now includes `cross-seed` (12th entry), and the comment "11 aliases du même chart" is updated to "12 aliases du même chart".

**Task 2 — Operator runbook:**

`.planning/phases/30-cross-seed/30-OPERATOR-RUNBOOK.md` documents the four categories of manual operator actions:

1. **Pre-reqs BEFORE ArgoCD sync**: verify `arrconf-env` has `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`; create `cross-seed-config` PVC (ReadWriteOnce, 1Gi); run `mkdir -p /media/data/torrents/cross-seed` on the MicroK8s node.
2. **Post-sync verification**: pod reaches Running (initContainer completed), cross-seed logs show torznab auth success, optional check of `/config/config.js` for unresolved tokens.
3. **Out-of-stack teardown**: optional `config.db` migration to preserve search history; `docker stop cross-seed` (or docker-compose / systemd equivalent).
4. **Rollback**: `kubectl scale deployment cross-seed --replicas=0`, restart old instance, no data loss (dedicated PVC untouched).

Security: the runbook references only secret key NAMES, never values. The optional token-check command warns operators not to paste output (T-30-09 mitigation).

## Verification

```
grep "configarr cross-seed; do" .github/workflows/chart-lint.yml  → 1 match
grep "total_matches < 10" .github/workflows/chart-lint.yml         → 0 matches
grep "total_matches < 12" .github/workflows/chart-lint.yml         → 1 match
grep "configarr cross-seed; do" README.md                          → 1 match
OPERATOR-RUNBOOK.md exists with cross-seed-config, mkdir -p /media/data/torrents/cross-seed, arrconf-env
synthetic test (current values.yaml): 13 matches >= 12 threshold   → PASS
```

## Deviations from Plan

None — plan executed exactly as written.

Minor calibration: the plan stated "10 → 12" as the threshold change. The actual current count in `values.yaml` is 13 (plan 30-02 had already added the 2 cross-seed entries before this plan ran). The threshold `12` is still the correct floor per the plan specification (accounting for the 2 new cross-seed images added in this phase); the actual count of 13 exceeds it cleanly.

## Known Stubs

None. This plan is CI + documentation only; no code stubs introduced.

## Threat Flags

No new security-relevant surface introduced:
- `chart-lint.yml` changes are read-only CI validation (no secret handling)
- `30-OPERATOR-RUNBOOK.md` references only secret key names per T-30-09

## Self-Check: PASSED

- [x] `.github/workflows/chart-lint.yml` modified, commit 4a05899 exists
- [x] `README.md` modified, commit 4a05899 exists
- [x] `.planning/phases/30-cross-seed/30-OPERATOR-RUNBOOK.md` created, commit a197ac0 exists
- [x] No `STATE.md` or `ROADMAP.md` modified (orchestrator owns those)
- [x] No `tools/arrconf/**` modified — no co-bump required
