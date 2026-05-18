---
phase: 09-categories-data-model-chart-initcontainer
plan: 09-D-docs-release
subsystem: documentation + chart
tags:
  - documentation
  - release
  - chart-pin
  - CF-07-CHART-PIN-LOOP
dependency_graph:
  requires:
    - 09-A-python-schema
    - 09-B-helm-job
    - 09-C-arrconf-yml-tests
  provides:
    - REQ-filesystem-operator-migration
    - CF-07-CHART-PIN-LOOP closure (pilot)
  affects:
    - CLAUDE.md (new operator runbook section)
    - charts/arr-stack/values.yaml (arrconf image tag pin)
tech_stack:
  added: []
  patterns:
    - CF-07-CHART-PIN-LOOP pre-bump pattern (piloted here, formalized in Phase 10)
    - ADR-6 snapshot discipline reinforced in operator runbook
key_files:
  created: []
  modified:
    - CLAUDE.md
    - charts/arr-stack/values.yaml
decisions:
  - Pre-bumping arrconf.image.tag in the same PR as Phase 9 reduces my-kluster Renovate PRs from 2 to 1 (CF-07-CHART-PIN-LOOP pilot)
  - No bash helper script for the migration — high-trust, low-automation per D-17 + 09-CONTEXT.md deferred lines 477-479
metrics:
  duration: "~8 minutes"
  completed: "2026-05-18"
  tasks_completed: 2
  files_modified: 2
---

# Phase 09 Plan D: Docs + Release Summary

**One-liner:** Operator filesystem migration runbook added to CLAUDE.md and arrconf.image.tag pre-bumped from stale 0.5.0 to 0.5.3 (CF-07-CHART-PIN-LOOP pilot, catching up 3 releases of drift).

## Tasks Executed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| D1 | Add filesystem migration runbook to CLAUDE.md | `2c9f82c` | `CLAUDE.md` (+90 lines) |
| D2 | Pre-bump arrconf.image.tag 0.5.0 → 0.5.3 | `de904c9` | `charts/arr-stack/values.yaml` (1 line) |

## D-NN Coverage

| Decision | Status | Evidence |
|----------|--------|----------|
| D-17 (Filesystem migration runbook) | FULLY IMPLEMENTED | New `## Filesystem migration: v0.2.0 flat → v0.3.0 Categories` section in CLAUDE.md with 6-row mapping table (verbatim from 09-CONTEXT.md §D-17 + 09-RESEARCH.md) and 4-step runbook (Pre-check, Execution, Post-check, Rollback) |

## CF-07-CHART-PIN-LOOP Closure Evidence

| Item | Value |
|------|-------|
| Latest existing git tag at plan time | `v0.5.2` (confirmed `git tag --sort=-version:refname \| head -1`) |
| Auto-tag action bump policy | `default_bump: patch` (chart-lint.yml line ~164, `mathieudutour/github-tag-action@v6.2`) |
| Computed next auto-tag | `v0.5.3` (patch bump, NOT minor — unconditional regardless of commit prefix) |
| Chart pin written | `tag: "0.5.3"` (without `v` prefix per existing chart convention) |
| Pre-existing drift caught up | Chart was at `"0.5.0"` while cluster runs `v0.5.2` — 3-release gap corrected in this edit |
| values.yaml diff | `-tag: "0.5.0"` → `+tag: "0.5.3"` (single line, Renovate annotation preserved above) |
| Rendered in CronJob | `image: ghcr.io/tom333/arr-stack-arrconf:0.5.3` confirmed via `helm template --show-only charts/arrconf/templates/common.yaml` line 62 |
| CF-07-CHART-PIN-LOOP result | Reduces my-kluster follow-up to **1** Renovate PR (not 2) after Phase 9 merge |

## CLAUDE.md Section Changes

| Metric | Value |
|--------|-------|
| Section title | `## Filesystem migration: v0.2.0 flat → v0.3.0 Categories` (exact — grep verified) |
| Insertion position | After `## Pattern single-instance + tags`, before `## Intégration avec my-kluster` |
| Lines added | +90 (1 section header + mapping table + 4 étapes + notes) |
| Table rows | 7 (1 header + 6 data rows matching 09-CONTEXT.md §D-17) |
| Bash helper script | NOT included (explicitly deferred per 09-CONTEXT.md §Deferred lines 477-479) |
| ADR-6 discipline | Pre-check step invokes `tools/snapshot/snapshot.sh --output snapshots/before-categories-migration-$(date +%F)/` |
| Execution pod | `kubectl exec -n selfhost -it deployment/jellyfin -- bash` (only pod with `media-nas-pvc` mounted RW) |
| Post-check commands | `curl POST /api/v3/command` with `RescanSeries` (Sonarr) and `RescanMovie` (Radarr) using env var API keys |

## Operator Cluster-Time Follow-Up Checklist

- [ ] Auto-tag action cut `v0.5.3` (patch bump from `v0.5.2` — triggered automatically on push to `main`)
- [ ] `arrconf-image.yml` built `ghcr.io/tom333/arr-stack-arrconf:0.5.3` and pushed to GHCR
- [ ] Renovate opened 1 PR in `my-kluster` bumping `targetRevision: v0.5.2 → v0.5.3`
- [ ] `tools/snapshot/snapshot.sh --output snapshots/before-phase-9-$(date +%F)/` run and committed (ADR-6 discipline — BEFORE merging Renovate PR)
- [ ] Renovate PR merged; ArgoCD synced to `v0.5.3`
- [ ] Job `arr-stack-categories-init` ran and emitted 10 `media_dir_ensured` JSON lines (`kubectl logs job/arr-stack-categories-init -n selfhost`)
- [ ] All 10 `/media/<name>` dirs present (`kubectl exec -n selfhost deployment/jellyfin -- ls /media/`)
- [ ] (Optional, post-deploy) Run filesystem migration from CLAUDE.md runbook if ready to move content

## Deviations from Plan

None — plan executed exactly as written.

Note on kubeconform: `kubeconform` is not installed on this machine (only `kubeseal` found at `/usr/local/bin/`). The `helm lint` acceptance criterion passed (0 chart(s) failed). The rendered image tag was verified directly via `helm template --show-only charts/arrconf/templates/common.yaml | grep 'ghcr.io/tom333/arr-stack-arrconf:0.5.3'` confirming `image: ghcr.io/tom333/arr-stack-arrconf:0.5.3` at line 62. The kubeconform check will run in CI (`chart-lint.yml`).

## Threat Flags

None found. All bash commands in the new CLAUDE.md section use env var references (`$SONARR_API_KEY`, `$RADARR_API_KEY`) with no literal secrets. The `mv` commands are taken verbatim from 09-RESEARCH.md §"Operator Migration Runbook" and operate exclusively within `/media`.

## Self-Check: PASSED

- `CLAUDE.md` section exists: confirmed (`grep -F '## Filesystem migration: v0.2.0 flat → v0.3.0 Categories' CLAUDE.md` exits 0)
- `charts/arr-stack/values.yaml` tag bumped: confirmed (`grep -F 'tag: "0.5.3"' charts/arr-stack/values.yaml` exits 0)
- Renovate annotation preserved: confirmed (`grep -B3 'tag: "0.5.3"' ...` shows `# renovate: image=ghcr.io/tom333/arr-stack-arrconf`)
- Commit `2c9f82c` exists: D1 (CLAUDE.md)
- Commit `de904c9` exists: D2 (values.yaml)
