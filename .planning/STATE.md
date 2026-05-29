---
gsd_state_version: 1.0
milestone: v0.9.0
milestone_name: configarr-in-UI + Jellyfin skip-intro
status: executing
last_updated: "2026-05-29T03:31:43.516Z"
last_activity: 2026-05-29 -- Phase 24 planning complete
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 3
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.

**Current focus:** v0.9.0 Phase 24 ready — Jellyfin Intro Skipper (arrconf reconciler extension)

## Current Position

Phase: 24 — Jellyfin Intro Skipper
Plan: — (not started)
Status: Ready to execute
Last activity: 2026-05-29 -- Phase 24 planning complete

```
v0.9.0 [░░░░░░░░░░░░░░░░░░░░] 0%
Phase 24 [ ] Phase 25 [ ] Phase 26 [ ] Phase 27 [ ]
```

## Accumulated Context

### Decisions

Quick reference to 8 LOCKED ADRs (full text in `PROJECT.md` `<decisions>` block):

- **ADR-1** Script Python custom (vs Buildarr/Terraform/Flemmarr)
- **ADR-2** Helm dependencies sur app-template (Option A)
- **ADR-3** Image arrconf sur GHCR public
- **ADR-4** Repo séparé (vs extension my-kluster)
- **ADR-5** configarr conservé (frontière dure quality_profiles/custom_formats/quality_definitions/media_naming) — CRITIQUE pour Phases 25-27: `ConfigarrRootConfig` vit dans `tools/arrconf-ui/` UNIQUEMENT, jamais dans `tools/arrconf/`; aucune URL API *arr dans arrconf-ui
- **ADR-6** Snapshot baseline avant toute écriture — applicable Phase 24 (live Jellyfin writes)
- **ADR-7** Single instance Sonarr/Radarr + tags (pas multi-instance)
- **ADR-8** arrconf trusted controller — `?forceSave=true` PUT bypass (scoped to *arr v3, NOT qBit/Jellyfin)

v0.8.0 decisions captured Phases 20-22: ambiguous-item mapping (P20), DC catch-all full-prune vs `unsorted` fallback → **full prune chosen** (P22 ADR-PLAN-SPLIT D-01).

### v0.9.0 Roadmap Decisions (2026-05-27)

- **Phase ordering:** Phase 24 (Jellyfin) first — smaller scope, validates live Jellyfin plugin API before UI work; Phases 25-27 are a strict dependency chain (backend → frontend → pickers)
- **Phase 24 and Phase 25 are independently parallelizable** — no code dependency between the arrconf Python reconciler and the arrconf-ui pydantic model; documented for planning
- **Kodi non-gating:** Phase 24 success criteria gate on web/app/Swiftfin; Kodi spike result documented but does NOT block phase completion
- **CFGUI-06 scope boundary:** Recyclarr template picker is READ-ONLY reference (no `include:` insertion) — enforced in Phase 27 UI; deferring insert to v1.x due to merge-hazard with 6 hand-rolled French CFs
- **co-bump constraint:** Phase 24 touches `tools/arrconf/**` → MUST co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` in the same commit. Phases 25-27 touch only `tools/arrconf-ui/**` → NO arrconf image co-bump, no chart auto-tag trigger

### Blockers/Concerns

None blocking. Carry-forward from v0.8.0:

- Phase 22 `force_prune=true` live DELETE path never exercised (surgical deletes used) — re-verify before `prune:true` in `arrconf.yml`. Not relevant to v0.9.0 scope.
- `POST /Packages/Installed` exact parameter format against live Jellyfin 10.11.8 is MEDIUM confidence — must be confirmed during Phase 24 planning/early implementation.
- configarr `--dry-run` flag availability in v1.28.0 must be confirmed before adding to CI gate in Phase 25.

### Pending Todos

- `2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0` (area: ops) — migration filesystem média v0.2.0→v0.3.0 pas encore exécutée ⇒ 3 libs Jellyfin vides (Films, Films-Animation-Enfants, Séries-Émilie). Runbook déjà dans CLAUDE.md. Découvert Phase 23 UAT SC#5 (partial 7/10). Tâche opérateur manuelle, hors v0.9.0.

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

- Next: `/gsd-plan-phase 24` — Jellyfin Intro Skipper
- Note: confirm `POST /Packages/Installed` exact parameter format and `configarr --dry-run` flag availability during planning before coding begins
- ADR-6: snapshot `snapshots/before-phase-24-$(date +%F)/` before any live Jellyfin write
