---
phase: 30-cross-seed
plan: "02"
subsystem: helm-chart
tags: [cross-seed, helm, initContainer, secret-injection, app-template]
dependency_graph:
  requires: ["30-01"]
  provides: ["cross-seed Helm alias", "cross-seed-configmap.yaml", "cross-seed values block"]
  affects: ["charts/arr-stack/Chart.yaml", "charts/arr-stack/values.yaml", "charts/arr-stack/templates/"]
tech_stack:
  added: ["ghcr.io/cross-seed/cross-seed:6.13.7 (main + initContainer)", "app-template@5.0.0 alias #12"]
  patterns: ["advancedMounts per-container volume split", "initContainer Node.js secret substitution", "emptyDir subPath config injection (Pitfall 1 avoidance)"]
key_files:
  created:
    - charts/arr-stack/templates/cross-seed-configmap.yaml
  modified:
    - charts/arr-stack/Chart.yaml
    - charts/arr-stack/values.yaml
    - charts/arr-stack/values.schema.json
    - charts/arr-stack/Chart.lock
decisions:
  - "Used advancedMounts (per-controller/per-container) instead of globalMounts to isolate config-cm to initContainer only and surface emptyDir at /config/config.js in main container — prevents PVC shadowing (Pitfall 1)"
  - "Used cross-seed image itself as initContainer (Node.js script) instead of busybox+envsubst to avoid busybox envsubst compatibility uncertainty (RESEARCH Pitfall 4)"
  - "tcpSocket probes on 2468 instead of httpGet — cross-seed API requires apiKey auth, no confirmed no-auth health endpoint (RESEARCH Open Question 1)"
  - "values.schema.json extended with cross-seed property (additionalProperties: true) — top-level additionalProperties: false blocked helm template"
metrics:
  duration: "~6 minutes"
  completed: "2026-05-31"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 4
---

# Phase 30 Plan 02: cross-seed Helm Alias + Secret Injection Summary

**One-liner:** cross-seed deployed as the 12th app-template@5.0.0 alias with Node.js initContainer substituting PROWLARR_API_KEY/QBT_USER/QBT_PASS from arrconf-env SealedSecret into an emptyDir config.js mounted at /config/config.js via advancedMounts subPath.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add 12th Chart.yaml alias + ConfigMap template | 15cab9a | Chart.yaml, templates/cross-seed-configmap.yaml |
| 2 | Add cross-seed values.yaml block | ab599a5 | values.yaml, values.schema.json, Chart.lock |

## What Was Built

**Task 1 — Chart.yaml + ConfigMap template:**
- Added 12th `app-template@5.0.0` dependency alias `cross-seed` to `Chart.yaml` (after suggestarr)
- Created `charts/arr-stack/templates/cross-seed-configmap.yaml` mirroring configarr-configmap.yaml verbatim — 3 token changes: name (`cross-seed-config`), data key (`config.js:`), file path (`.Files.Get "files/cross-seed/config.js"`)

**Task 2 — values.yaml block:**
- Added `cross-seed:` alias block:
  - `type: deployment`, `replicas: 1` (D-03)
  - `initContainers.config-init`: uses `ghcr.io/cross-seed/cross-seed:6.13.7` with Node.js inline script that reads `/config-cm/config.js` (ConfigMap) and replaces `${PROWLARR_API_KEY}`, `${QBT_USER}`, `${QBT_PASS}` from `arrconf-env` SealedSecret env, writing resolved file to `/config-resolved/config.js` (emptyDir)
  - `containers.main`: `args: [daemon]`, `envFrom: arrconf-env`, `tcpSocket` probes on 2468, modest resources (250m/256Mi limits)
  - Service on port 2468, no ingress (cluster-internal, D-14 pattern)
  - 4 persistence volumes via `advancedMounts`: `config-cm` (ConfigMap, initContainer only), `config-resolved` (emptyDir, initContainer writes at `/config-resolved`, main surfaces at `/config/config.js` via subPath), `config` (PVC `cross-seed-config` at `/config`), `torrents` (hostPath `/media/data/torrents` at `/data`)
- Both image blocks (initContainer + main) have `# renovate: image=ghcr.io/cross-seed/cross-seed` annotations

## Verification Results

All acceptance criteria pass:
- `grep -c 'alias: cross-seed' Chart.yaml` = 1
- `grep -c 'alias:' Chart.yaml` = 12
- `cross-seed-configmap.yaml` has `name: cross-seed-config`, `config.js: |`, `.Files.Get "files/cross-seed/config.js"`, label helper
- `helm template` renders cross-seed Deployment with initContainer `config-init` in `spec.initContainers`
- config-resolved emptyDir surfaces at `/config/config.js` via subPath in main container
- `args: [daemon]`, port 2468, `envFrom: arrconf-env` on both containers
- `check-renovate-annotations.sh` exits 0
- `grep -c 'tag: latest' values.yaml` = 0
- `helm lint` passes (0 failures)
- PVC `cross-seed-config` at `/config` without shadowing by subPath file mount

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added cross-seed to values.schema.json**
- **Found during:** Task 2 verification — `helm template` failed with `additional properties 'cross-seed' not allowed`
- **Issue:** `values.schema.json` has top-level `"additionalProperties": false` and did not include a `cross-seed` property, blocking all helm operations
- **Fix:** Added `"cross-seed": { "type": "object", "additionalProperties": true }` to the schema properties, following the exact same pattern as the existing `suggestarr` entry
- **Files modified:** `charts/arr-stack/values.schema.json`
- **Commit:** ab599a5 (included in Task 2 commit)

**2. [Rule 3 - Blocking Issue] Chart.lock out of sync after adding 12th alias**
- **Found during:** Task 2 verification
- **Issue:** `helm dependency build` failed because `Chart.lock` was out of sync with the new `Chart.yaml` dependency; required `helm dependency update` to regenerate
- **Fix:** Ran `helm dependency update charts/arr-stack/` — `Chart.lock` updated, alias directories created locally
- **Files modified:** `charts/arr-stack/Chart.lock`
- **Commit:** ab599a5 (included in Task 2 commit)

## Self-Check

**Created files exist:**
- `charts/arr-stack/templates/cross-seed-configmap.yaml` — FOUND
- `charts/arr-stack/values.schema.json` (modified) — FOUND

**Commits exist:**
- `15cab9a` Task 1: feat(30-02): add cross-seed as 12th app-template alias + ConfigMap template
- `ab599a5` Task 2: feat(30-02): add cross-seed Deployment values block with initContainer secret injection

## Self-Check: PASSED

## Known Stubs

None. The config.js file committed in Plan 30-01 carries `${PROWLARR_API_KEY}`, `${QBT_USER}`, `${QBT_PASS}` tokens — these are intentional substitution tokens resolved at runtime by the initContainer, not stubs. The Helm chart is complete.

## Threat Flags

No new unmodeled trust boundaries introduced beyond what is captured in the plan's threat model (T-30-04 through T-30-08). The ConfigMap carries only `${...}` tokens (verified: values.yaml references ConfigMap by name only; no secret literals anywhere in committed files). The resolved config.js lives entirely in the ephemeral emptyDir volume.

## Operator Pre-Requisites (for ArgoCD sync)

These are runtime dependencies documented but not automated:
1. `cross-seed-config` PVC must exist in my-kluster before ArgoCD sync
2. `/media/data/torrents/cross-seed` directory must exist on the host node (`mkdir -p /media/data/torrents/cross-seed`)
3. `arrconf-env` SealedSecret must contain `PROWLARR_API_KEY`, `QBT_USER`, and `QBT_PASS` keys (Plan 03 runbook)
