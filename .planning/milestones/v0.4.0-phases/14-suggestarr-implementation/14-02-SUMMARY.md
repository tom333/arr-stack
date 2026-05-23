---
phase: 14-suggestarr-implementation
plan: "02"
subsystem: helm-chart
tags:
  - helm
  - sidecar
  - categories-routing
  - suggestarr
dependency_graph:
  requires:
    - 14-01 (suggestarr alias vendored into charts/arr-stack/charts/suggestarr/)
  provides:
    - suggestarr: values block in charts/arr-stack/values.yaml
    - helm template renders Deployment + Service + PVC for suggestarr
  affects:
    - charts/arr-stack/values.yaml
tech_stack:
  added: []
  patterns:
    - bjw-s app-template Deployment alias pattern (matching other apps in umbrella chart)
    - Per-container env remap via secretKeyRef (D-01) — reuse arrconf-env keys under different env var names
    - PVC-backed config persistence (SuggestArr owns its SQLite + YAML; no ConfigMap)
key_files:
  created: []
  modified:
    - charts/arr-stack/values.yaml
decisions:
  - "D-01: Per-container env remap — JELLYFIN_TOKEN←JELLYFIN_API_KEY, SEER_TOKEN←SEERR_API_KEY, TMDB_API_KEY direct from arrconf-env"
  - "D-09: Registry-explicit Renovate annotation # renovate: image=docker.io/ciuse99/suggestarr"
  - "D-11: NO co-bump — arrconf.image.tag stays at 0.7.0 (no Python code touched)"
  - "D-14: NO Ingress — SuggestArr web UI stays cluster-internal-only"
  - "revision-2: NO ConfigMap template or source file — SuggestArr config is web-UI-managed per 13-RESEARCH line 488"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-22"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
---

# Phase 14 Plan 02: SuggestArr values.yaml block — Summary

**One-liner:** SuggestArr Deployment block wired to arrconf-env secrets with per-container env remap, 1Gi PVC persistence, no Ingress and no ConfigMap mount (revision-2 per 13-RESEARCH line 488).

## What Was Built

Task 2.1 (live cluster discovery) was already completed by the orchestrator inline — 4 evidence files were committed at `.planning/phases/14-suggestarr-implementation/evidence/`.

Task 2.2 added the `suggestarr:` block to `charts/arr-stack/values.yaml` (90 lines appended after the `configarr:` block). The block delivers:

- **Image:** `ciuse99/suggestarr:v2.7.3` with `pullPolicy: IfNotPresent`
- **Renovate annotation:** `# renovate: image=docker.io/ciuse99/suggestarr` (registry-explicit per D-09 + CLAUDE.md Annotations Renovate convention)
- **Env remap (D-01):** 3 env vars via `secretKeyRef.name=arrconf-env`:
  - `JELLYFIN_TOKEN` ← key `JELLYFIN_API_KEY`
  - `SEER_TOKEN` ← key `SEERR_API_KEY`
  - `TMDB_API_KEY` ← key `TMDB_API_KEY` (operator adds this key to SealedSecret separately per D-13)
- **Probes:** liveness + readiness on `GET /api/health/live` + `/api/health/ready` at port 5000
- **Resources:** 50m/250m CPU, 128Mi/256Mi memory
- **Service:** ClusterIP port 5000
- **Persistence:** 1Gi PVC at `/app/config/config_files` (SuggestArr's SQLite + YAML config)
- **No Ingress** (D-14 — web UI stays cluster-internal, accessed via port-forward at UAT time)
- **No ConfigMap** (revision-2 alignment — routing config entered via web UI post-deploy)

## Revision-2 ConfigMap Deletion Note

The original revision-1 plan invented a `charts/arr-stack/files/suggestarr-config.yml` mounted as a ConfigMap. This was a research-plan gap: 13-RESEARCH line 488 states "No ConfigMap needed for SuggestArr: config persists in the SQLite DB / YAML inside the PVC. The web UI is the configuration interface." Revision-2 (post plan-checker BLOCKER) deleted both `templates/suggestarr-configmap.yaml` and `files/suggestarr-config.yml` entirely. Neither was created in this execution. Verified: `test ! -f charts/arr-stack/templates/suggestarr-configmap.yaml` passes.

## Deviations from Plan

None — plan executed exactly as written. The 4 evidence files from Task 2.1 were confirmed present before Task 2.2 execution.

### Pre-existing Deviations Documented in Evidence Files

The following deviations were captured by the orchestrator's Task 2.1 (evidence files) and are documented in `derived-routing-values.md`. They affect the operator-entered web UI values, NOT the chart:

**[Pre-existing in evidence] D-07 deviation — radarr_service.activeAnimeDirectory absent:**
- `arrconf.yml::seerr.main.radarr_service` has no `activeAnimeDirectory` field.
- `anime_movie.rootFolder` was derived from `categories[]` entry `films-zoe.base_path` → `/media/films-zoe`.
- Documented in `evidence/derived-routing-values.md` for operator awareness at UAT time.

**[Pre-existing in evidence] D-06-SEERR-RADARR-LIMIT — anime_movie.profileId mirrored from Sonarr:**
- `arrconf.yml` has no `radarr_service.activeAnimeProfileId`.
- `anime_movie.profileId` set to `8` (mirrored from `sonarr_service.activeAnimeProfileId`; verified live Radarr also has id=8 "Anime" profile).

**[Pre-existing in evidence] Cluster reality — 2 Jellyfin super-libraries, not 10:**
- CONTEXT D-04 revision-2 wording referenced "10 Jellyfin libraries". Live cluster shows 2 VirtualFolders (Séries + Films as super-libraries with multi-path includes, per Phase 10-G Jellyfin wiring). Both cover all 10 category paths. ItemIds: `d565273fd114d77bdf349a2896867069` (Séries) + `db4c1708cbb5dd1676284a40f2950aba` (Films). Operator pastes BOTH into SuggestArr UI.

## helm template Verification

Running `helm template arr-stack charts/arr-stack/` (2395 lines, all 11 aliases rendered):

```
kind: Deployment
  name: suggestarr          ← rendered
kind: Service
  name: suggestarr          ← rendered
kind: PersistentVolumeClaim
  name: suggestarr          ← rendered (1Gi, RWO, /app/config/config_files)
kind: ServiceAccount
  name: suggestarr          ← rendered
```

Negative assertions confirmed:
- No `kind: ConfigMap` named `suggestarr-config` in the full template output.
- No `kind: Ingress` for suggestarr in the full template output.

## Confirmation Checklist

- [x] `suggestarr:` block in `charts/arr-stack/values.yaml` at correct position (appended after `configarr:`)
- [x] Renovate annotation `# renovate: image=docker.io/ciuse99/suggestarr` present (D-09)
- [x] Env remap: JELLYFIN_TOKEN, SEER_TOKEN, TMDB_API_KEY via `secretKeyRef.name=arrconf-env` (D-01)
- [x] 1Gi PVC at `/app/config/config_files` (13-RESEARCH §Phase 14 Implementation Guidance)
- [x] NO Ingress block in suggestarr (D-14)
- [x] NO ConfigMap mount in persistence (revision-2 per 13-RESEARCH line 488)
- [x] `templates/suggestarr-configmap.yaml` does NOT exist
- [x] `files/suggestarr-config.yml` does NOT exist
- [x] `arrconf.image.tag` stays `"0.7.0"` (D-11 NO co-bump)
- [x] `charts/arr-stack/files/arrconf.yml` NOT modified
- [x] `tools/arrconf/**` NOT modified
- [x] `helm lint charts/arr-stack/` exits 0
- [x] `helm template` produces Deployment + Service + PVC for suggestarr
- [x] D-13 SealedSecret YAML NOT added in this repo (procedure documented in 14-HUMAN-UAT.md)

## Handoff to Plan 03

Plan 03 (`14-03-PLAN.md`) delivers:
1. `tools/arrconf/tests/test_suggestarr_chart_artifacts.py` — pytest integration test asserting chart mechanics (D-10 revision-2 scope: env remap, Renovate annotation, no Ingress, alias listed, dep unpacked, helm template, PVC 1Gi, no ConfigMap suggestarr-config).
2. `14-HUMAN-UAT.md` — operator step-by-step including Scenario 3: web UI configuration using `evidence/derived-routing-values.md` as paste-ready source.

Operator pre-condition before ArgoCD sync: `TMDB_API_KEY` must be added to `arrconf-env` SealedSecret in my-kluster (D-13 ordering rule — separate PR, merges FIRST).

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `14-02-SUMMARY.md` exists | PASS |
| `charts/arr-stack/values.yaml` exists | PASS |
| `evidence/jellyfin-libraries.txt` exists | PASS |
| `evidence/sonarr-profiles.txt` exists | PASS |
| `evidence/radarr-profiles.txt` exists | PASS |
| `evidence/derived-routing-values.md` exists | PASS |
| `feat(14-02)` commit `18250ac` exists | PASS |
