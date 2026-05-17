---
phase: 04-umbrella-chart-migration-des-9-apps
plan: "06"
subsystem: infra
tags: [helm, github-actions, renovate, kubeconform, chart-lint, ci, auto-tag]

# Dependency graph
requires:
  - phase: 04-05
    provides: values.schema.json + examples/values-prod.yaml + 10/10 alias bodies (needed by helm lint + helm template in CI)
  - phase: 04-01
    provides: tools/scripts/check-renovate-annotations.sh (invoked verbatim from chart-lint.yml)
provides:
  - .github/workflows/chart-lint.yml (full CI gate: helm dep build + Helm 4 multi-alias workaround + lint + template + kubeconform 1.33.0 + annotation check + :latest guard + cronJobConfig guard + Python regex test + renovate-config-validator + auto-tag B3)
  - renovate.json customManagers regex matching all 10 image annotations in values.yaml
  - renovate.json packageRules (automerge minor/patch for docker+helmv3, manual major review)
affects: [04-08-cutover, 04-09-sc2-latency-validation]

# Tech tracking
tech-stack:
  added:
    - azure/setup-helm@v4 (Helm 3.18.0 pin — floor for app-template 5.0.0)
    - mathieudutour/github-tag-action@v6.2 (B3 auto-tag on push-to-main)
    - renovate-config-validator (npx --yes, no version pin — current stable)
    - kubeconform (installed via curl from GitHub releases, K8s 1.33.0 target)
  patterns:
    - "Helm 4 multi-alias workaround: helm dependency build + tar -xzf app-template-5.0.0.tgz -C charts/ so all 10 aliases find their chart copy (Helm issue #12748)"
    - "Python synthetic test in CI: verifies customManagers regex actually matches >=10 image entries — guards against annotation contract drift"
    - "B3 auto-tag: tag job gated to push-to-main, needs: lint, contents: write scoped only to tag job"
    - "Renovate regex uses named groups (?P<depName>...) / (?P<currentValue>...) — Renovate and Python re both support this syntax"

key-files:
  created:
    - .github/workflows/chart-lint.yml
  modified:
    - renovate.json

key-decisions:
  - "Helm 4 multi-alias workaround included (tar -xzf app-template-5.0.0.tgz) — without it helm template fails with 'found in Chart.yaml, but missing in charts/' for aliases 2-10"
  - "Helm 3.18.0 pinned via azure/setup-helm@v4 — this is the minimum version required by app-template 5.0.0"
  - "kubeconform installed via direct curl (no third-party action) — consistent with arrconf-image.yml install-binaries-on-the-fly pattern; targets K8s 1.33.0 (D-04-PIN-02)"
  - "Regex pattern uses (?P<depName>...)...\\n...\\n...(?P<currentValue>...) multi-line match — accounts for indentation and optional tag comments; verified at 10 matches"
  - "renovate-config-validator version: not pinned — npx --yes fetches current stable at CI runtime"
  - "github-tag-action@v6.2 used as documented stable; v6.2 is the latest stable as of 2026-05-13"
  - "Python synthetic test uses re.findall (not re.finditer) for simple count; both approaches produce 10 matches"

patterns-established:
  - "Pattern: Python synthetic test in CI workflow validates renovate.json customManagers regex against actual values.yaml at lint time — catches annotation drift before Renovate is confused"
  - "Pattern: Helm 4 multi-alias workaround is required any time app-template is used N>1 times with aliases; document in team runbook"
  - "Pattern: CI workflow has 2 jobs (lint = PR+push, tag = push-to-main only with contents:write); permissions scoped per job minimizes blast radius"

requirements-completed:
  - REQ-helm-validation
  - REQ-renovate-image-tracking

# Metrics
duration: 20min
completed: 2026-05-13
---

# Phase 04 Plan 06: chart-lint.yml CI workflow + renovate.json customManagers Summary

**GitHub Actions CI gate for the umbrella chart (helm lint + kubeconform 1.33.0 + 5 guards + auto-tag B3) and Renovate customManagers tracking all 10 image annotations in values.yaml**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-13T00:00:00Z
- **Completed:** 2026-05-13
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Authored `.github/workflows/chart-lint.yml` with the full CI gate: Helm dependency build + Helm 4 multi-alias workaround (tarball unpack) + helm lint + helm template + kubeconform 1.33.0 + 5 defensive guards + auto-tag job (B3 Path A)
- Extended `renovate.json` with `customManagers` regex that matches all 10 image entries in `charts/arr-stack/values.yaml` (depName + currentValue capture, docker datasource)
- Added `packageRules`: automerge minor/patch on custom.regex and helmv3 managers; manual review gated for major updates
- Verified Python synthetic test (run locally): regex matches = 10 (sonarr, radarr, prowlarr, qbittorrent, cleanuparr, seerr, flaresolverr, jellyfin, arrconf, configarr)

## Task Commits

1. **Task 6.1: chart-lint.yml CI workflow** - `3a6be94` (feat)
2. **Task 6.2: renovate.json customManagers + packageRules** - `8e6597d` (feat)

**Plan metadata:** (see final docs commit below)

## Files Created/Modified

- `.github/workflows/chart-lint.yml` — Full CI gate with 2 jobs (lint + auto-tag); Helm 4 workaround included; all 5 guards wired
- `renovate.json` — Extended from 3-line stub to full customManagers + packageRules config

## Decisions Made

- **Helm 4 multi-alias workaround included:** The prompt's `<plan_specific_notes>` explicitly requires unpacking `app-template-5.0.0.tgz` after `helm dependency build`. This is mandatory for Helm 4.x with multi-alias-of-same-chart (issue #12748). Without it, `helm template` would fail in CI.
- **Helm 3.18.0 pin:** `azure/setup-helm@v4` with `version: v3.18.0` — this is the minimum version floor for app-template 5.0.0 (per RESEARCH "Breaking Changes" section). The PLAN.md note says ">=3.18 required by app-template 5.0.0".
- **Regex pattern choice:** The RESEARCH.md regex (`#\\s*renovate:...\\nrepository:`) did NOT work (0 matches) because it doesn't account for the leading indentation in values.yaml. The PLAN task 6.2 regex (with `\\s*` before `repository:` and captures `tag:`) matches all 10 entries. Used the latter.
- **github-tag-action@v6.2:** Latest stable as of execution date; plan specifies v6.2 exactly.
- **renovate-config-validator:** Not pinned — `npx --yes renovate-config-validator` fetches current stable at CI time. Network availability required in CI (documented below).

## Deviations from Plan

None - plan executed exactly as written (with the Helm 4 workaround from `<plan_specific_notes>` incorporated into the workflow as directed).

Note: The RESEARCH.md regex pattern for customManagers was found to produce 0 matches during local verification (it lacks `\\s*` before `repository:`). The PLAN.md task 6.2 regex (the `<action>` body) was used instead and produces 10 matches — this is the intended regex. No plan-level deviation; the RESEARCH.md regex was superseded by the more specific plan task body.

## Issues Encountered

- **RESEARCH.md customManagers regex mismatches:** The RESEARCH.md §"Renovate customManagers" regex (`#\\s*renovate:\\s*image=(?<depName>[^\\n]+)\\s*\\nrepository:\\s*(?<currentValue>[^\\s]+)`) matched 0 entries because it doesn't account for indentation before `repository:`. The PLAN.md task 6.2 `<action>` body provides a corrected regex that handles arbitrary whitespace before each field and captures `currentValue` from `tag:` (not `repository:`). Used the plan action body regex.

## User Setup Required

None — no external service configuration required. The CI gates are GitHub Actions workflows that run automatically on PR/push.

Note: `npx --yes renovate-config-validator` requires npm/node and network access in the CI runner (ubuntu-24.04 satisfies both).

## Next Phase Readiness

- CI gate is ready for Plan 04-08 (cutover): `helm lint`, `helm template | kubeconform`, and annotation checks will run on the cutover PR
- Renovate is configured to track image bumps post-cutover and auto-merge minor/patch (SC#2 E2E latency validation target in Plan 04-09)
- Auto-tag (B3) will fire on each push-to-main after the cutover PR merges, creating the `vX.Y.Z` tag that `my-kluster`'s `targetRevision` will track

## Known Stubs

None — no stubs in the CI workflow or renovate.json.

## Threat Flags

None — CI workflow and Renovate config do not introduce new network endpoints, auth paths, or schema changes at trust boundaries.

## Self-Check

- [x] `.github/workflows/chart-lint.yml` exists and is valid YAML
- [x] `renovate.json` is valid JSON with customManagers
- [x] Commits `3a6be94` and `8e6597d` exist in git log
- [x] Python synthetic test: 10 matches confirmed locally
- [x] All 5 guards wired in chart-lint.yml (annotation, :latest, cronJobConfig, Python regex, renovate-config-validator)
- [x] Auto-tag job gated to push-to-main with `contents: write`

---
*Phase: 04-umbrella-chart-migration-des-9-apps*
*Completed: 2026-05-13*
