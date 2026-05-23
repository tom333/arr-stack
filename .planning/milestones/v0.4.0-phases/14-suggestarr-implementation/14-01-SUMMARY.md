---
phase: 14-suggestarr-implementation
plan: "01"
subsystem: helm-chart
tags:
  - helm
  - chart-vendoring
  - sidecar
  - suggestarr
dependency_graph:
  requires: []
  provides:
    - charts/arr-stack/charts/suggestarr/ (unpacked bjw-s/app-template@5.0.0 vendored directory)
    - 11th alias entry in Chart.yaml
  affects:
    - charts/arr-stack/Chart.yaml
    - charts/arr-stack/Chart.lock
    - charts/arr-stack/values.schema.json
tech_stack:
  added: []
  patterns:
    - Helm 4 multi-alias unpack workaround (tar -xzf + cp -r per CLAUDE.md convention)
key_files:
  created:
    - charts/arr-stack/charts/suggestarr/ (157 files — full unpacked bjw-s/app-template@5.0.0)
  modified:
    - charts/arr-stack/Chart.yaml (1 alias block added, 10 → 11 deps)
    - charts/arr-stack/Chart.lock (new digest entry for suggestarr)
    - charts/arr-stack/values.schema.json (suggestarr stub added — additionalProperties: true)
decisions:
  - "values.schema.json required a stub entry for suggestarr (additionalProperties: true) because the root-level schema uses additionalProperties: false — without the stub, helm lint failed with 'additional properties not allowed'"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  files_modified: 4
---

# Phase 14 Plan 01: SuggestArr Helm Chart Vendoring Summary

Vendor the 11th bjw-s/app-template@5.0.0 alias (suggestarr) into the arr-stack umbrella chart, committed as an unpacked directory so ArgoCD can consume it without running helm dependency build.

## What Was Done

### Task 1.1: Chart.yaml + Chart.lock update

Added the 11th dependency alias block to `charts/arr-stack/Chart.yaml` after the `configarr` entry:

```yaml
  - name: app-template
    alias: suggestarr
    version: 5.0.0
    repository: https://bjw-s-labs.github.io/helm-charts
```

Ran `helm dependency update charts/arr-stack/` to regenerate `Chart.lock` with the new digest entry (note: `helm dependency build` failed because the lock was out of sync with the new Chart.yaml — `helm dependency update` is the correct command when adding a new dependency, not just rebuilding).

### Task 1.2: Helm 4 multi-alias unpack workaround

Applied the documented workaround from CLAUDE.md verbatim:

```bash
tar -xzf charts/arr-stack/charts/app-template-5.0.0.tgz -C charts/arr-stack/charts/
cp -r charts/arr-stack/charts/app-template charts/arr-stack/charts/suggestarr
```

Verification: `diff -r charts/arr-stack/charts/arrconf charts/arr-stack/charts/suggestarr` produced empty output — byte-identical to the existing alias dirs (same upstream tgz).

The unpacked directory structure:
- `Chart.yaml` (name: app-template, version: 5.0.0)
- `Chart.lock`
- `values.yaml`
- `values.schema.json`
- `templates/common.yaml`
- `charts/common/` (bjw-s common library, ~150 template files)
- `.helmignore`, `LICENSE`, `README.md`

## Verification Outputs

All 5 verification commands passed:

```
SC1 pass: 11 aliases (grep -c '  - name: app-template' Chart.yaml → 11)
SC2 pass: Chart.lock exists
SC3 pass: all 11 unpacked dirs exist (sonarr radarr prowlarr qbittorrent cleanuparr seerr flaresolverr jellyfin arrconf configarr suggestarr)
SC4 pass: helm lint (1 chart linted, 0 failed)
SC5 pass: helm template -f examples/values-prod.yaml (exit 0)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] values.schema.json required a suggestarr stub entry**

- **Found during:** Task 1.2 verification (helm lint)
- **Issue:** `charts/arr-stack/values.schema.json` uses `"additionalProperties": false` at the root level. When Helm resolves the 11th alias, it passes `suggestarr: {}` as a values key. Without a corresponding schema property, helm lint failed with: `additional properties 'suggestarr' not allowed`
- **Fix:** Added a minimal stub to `values.schema.json` — `"suggestarr": { "type": "object", "additionalProperties": true }` — matching the pattern all other aliases use. Plan 02 will replace this stub with a proper schema when it adds the actual values block.
- **Files modified:** `charts/arr-stack/values.schema.json`
- **Commit:** fc3c96d (same atomic commit)

**2. [Rule 3 - Blocking] helm dependency build vs. helm dependency update**

- **Found during:** Task 1.1 execution
- **Issue:** Plan said to run `helm dependency build` but this failed with "lock file is out of sync" because a new dep was added. `helm dependency build` only works when the lock already matches Chart.yaml.
- **Fix:** Used `helm dependency update` instead, which is the correct command when adding new dependencies. This is documented behavior — `build` rebuilds from existing lock, `update` resolves and re-locks.
- **Impact:** None — Chart.lock regenerated correctly with the new suggestarr digest entry.

## Commit

| Hash | Description |
|------|-------------|
| fc3c96d | chore(14-01): vendor suggestarr alias into umbrella chart |

## Self-Check: PASSED

- [x] `charts/arr-stack/Chart.yaml` — exists, 11 aliases, `alias: suggestarr` present
- [x] `charts/arr-stack/Chart.lock` — exists, regenerated
- [x] `charts/arr-stack/charts/suggestarr/Chart.yaml` — exists, `name: app-template`, `version: 5.0.0`
- [x] `helm lint charts/arr-stack/` — exit 0
- [x] `helm template charts/arr-stack/ -f examples/values-prod.yaml` — exit 0
- [x] No `tools/arrconf/**` Python files touched (no co-bump needed)
- [x] No `charts/arr-stack/values.yaml` modifications
- [x] Commit fc3c96d exists: `git log --oneline | grep fc3c96d` — found
