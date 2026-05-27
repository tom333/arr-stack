---
gsd_state_version: 1.0
milestone: v0.9.0
milestone_name: configarr-in-UI + Jellyfin skip-intro
status: planning
last_updated: "2026-05-27T04:48:28.356Z"
last_activity: 2026-05-27
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.

**Current focus:** v0.9.0 en cadrage — définition des requirements (configarr-in-UI + Jellyfin skip-intro)

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-05-27 — Milestone v0.9.0 started

## Accumulated Context

### Decisions

Quick reference to 8 LOCKED ADRs (full text in `PROJECT.md` `<decisions>` block):

- **ADR-1** Script Python custom (vs Buildarr/Terraform/Flemmarr)
- **ADR-2** Helm dependencies sur app-template (Option A)
- **ADR-3** Image arrconf sur GHCR public
- **ADR-4** Repo séparé (vs extension my-kluster)
- **ADR-5** configarr conservé (frontière dure quality_profiles/custom_formats/quality_definitions/media_naming)
- **ADR-6** Snapshot baseline avant toute écriture
- **ADR-7** Single instance Sonarr/Radarr + tags (pas multi-instance)
- **ADR-8** arrconf trusted controller — `?forceSave=true` PUT bypass (scoped to *arr v3, NOT qBit/Jellyfin)

v0.8.0 decisions captured Phases 20-22: ambiguous-item mapping (P20), DC catch-all full-prune vs `unsorted` fallback → **full prune chosen** (P22 ADR-PLAN-SPLIT D-01).

### Blockers/Concerns

None blocking. v0.8.0 closed as `tech_debt` (no blockers). Carry-forward debt tracked in "Deferred Items" below. Two items to re-surface in v0.9.0 planning: (1) Phase 22 had no VERIFICATION.md (cross-verified by P23 — accept or backfill); (2) `force_prune=true` live DELETE path never exercised — re-verify before ever setting `prune:true` in `arrconf.yml` (mixed legacy+Category tag state risks over-deletion until full Category-tag migration lands).

_Historical (resolved during v0.8.0):_ ROADMAP Phase 23 SC#1/SC#2 legacy-path wording error fixed pre-plan; Phase 22 live carry-forward resolved (3 orphan torrents deleted D-11; Radarr 5 searched / 2 deferred, Sonarr left to scheduler D-10).

### Pending Todos

- `2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0` (area: ops) — migration filesystem média v0.2.0→v0.3.0 pas encore exécutée ⇒ 3 libs Jellyfin vides (Films, Films-Animation-Enfants, Séries-Émilie). Runbook déjà dans CLAUDE.md. Découvert Phase 23 UAT SC#5 (partial 7/10). Tâche opérateur manuelle, hors v0.8.0.

## Deferred Items

Items carried from v0.3.0 / v0.4.0 / v0.5.0 close — not in v0.8.0 scope, may be re-evaluated for v0.9.0+:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| uat_gap | phase-09 initContainer NFS uid=1000 cluster-time write test (09-HUMAN-UAT.md, 2 open scenarios) | partial — code correct, runtime UAT pending | v0.3.0 close (2026-05-22) |
| verification_gap | phase-09 VERIFICATION status human_needed (UAT-driven) | human_needed | v0.3.0 close (2026-05-22) |
| verification_gap | phase-10 VERIFICATION status human_needed (SC#1 cluster materialization + SC#3 TVDB-anime live routing) | human_needed | v0.3.0 close (2026-05-22) |
| infra_gap | SuggestArr ingress + auto-submit (currently port-forward + manual approval) | deferred | v0.4.0 close (2026-05-23) |
| upgrade_check | D-07-PLAYLIST-MGMT-NULL re-verify on Jellyfin 11.x upgrade | watch-only | v0.3.0 close (2026-05-22) |

### Acknowledged at v0.8.0 close (2026-05-27)

8 open artifact-audit items acknowledged and deferred at milestone close (audit = `tech_debt`, no blockers — see `v0.8.0-MILESTONE-AUDIT.md`):

| Category | Item | Status |
|----------|------|--------|
| verification_gap | phase-21 VERIFICATION human_needed (live file-present + qBit re-hash + Jellyfin ItemCount; cluster torn down) | human_needed — mechanism PASS-WITH-CONCERNS |
| verification_gap | phase-22 NO VERIFICATION.md (deliverable cross-verified by P23 + integration checker) | accepted — process gap |
| coverage_gap | phase-22 force_prune=true DELETE path never exercised live (surgical direct-API deletes used) | re-verify before prune:true in arrconf.yml |
| migration_gap | phase-21 10 records missing-on-disk (disk drift); DB Category-anchored, files absent | operator follow-up (re-download/remove) |
| uat_gap | phase-23 SC#5 — 3 Jellyfin libs empty pending media filesystem migration | partial-deferred, operator-accepted |
| todo | 2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0 (ops) | pending — manual operator task |
| quick_task | 260527-jfk autoTMM reconcile (artifact status `missing`) | DONE (commit df280f8) — artifact frontmatter only |
| uat_gap+verification_gap | phase-09 + phase-10 carry-forward (NFS write test, TVDB-anime routing) | non-blocking — see table above |

## Quick Tasks Completed

| Quick ID | Description | Date | Commit | Tests |
|----------|-------------|------|--------|-------|
| 260525-bj5 | client_base.py 4xx response.text[:500] logging (OBS-01) + respx test + chart co-bump 0.12.1 → 0.14.0 | 2026-05-25 | 9726d81 | 416 pass (+5 new) |
| 260527-jfk | enable qBit autoTMM reconcile (preferences.enable+auto_tmm+category_changed) in arrconf.yml — Phase 23 SC#3 save_path fix ; no image co-bump (ConfigMap-only) | 2026-05-27 | df280f8 | config parse OK (no Python change) |

## Operator Next Steps

- v0.9.0 en cadrage : research → requirements → roadmap (en cours via `/gsd-new-milestone`)
