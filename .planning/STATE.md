---
gsd_state_version: 1.0
milestone: v0.8.0
milestone_name: Categories cleanup — v0.2.0 legacy migration close-out
status: executing
last_updated: "2026-05-27T01:36:50.569Z"
last_activity: 2026-05-27 -- Phase 23 execution started
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 5
  completed_plans: 4
  percent: 80
---

# Project State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.

**Current focus:** Phase 23 — uat-dispositive-end-to-end-verification

## Current Position

Phase: 23 (uat-dispositive-end-to-end-verification) — EXECUTING
Plan: 1 of 1
Status: Executing Phase 23
Last activity: 2026-05-27 -- Phase 23 execution started

### Phase 22 DONE (2026-05-27) — closed live

- Code: `force_prune` path + legacy-name guard + Sonarr/Radarr wiring + tests (455 pass) shipped → `arrconf:0.15.0` on GHCR + deployed in cluster (CronJob on `:0.15.0`).
- Live cleanup executed: 3 orphan torrents deleted (`deleteFiles=true`); catch-all DC `qBittorrent` id=1 + 4 legacy roots (`/media/{anime,family,films-anime,films-family}`) deleted (surgical id DELETE, NOT force_prune); 5 Radarr missing re-searched / 2 deferred (2026); SC#2 dry-run `0 plan_action` before+after (idempotent). ADR-6 snapshots committed.
- Carry-forward residue (future milestone): legacy per-type DCs (TV/Anime/Family/Movies) + legacy tags (`tv`/`family`/`anime`/`1-moi`) left in-cluster — need full Category tag migration first. Mario Galaxy + Jumpers (2026) monitored, unreleased.

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

**⚠ ROADMAP Phase 23 SC error to fix FIRST** (flagged in 22-CONTEXT `<deferred>`): SC#1/SC#2 wrongly list `/media/films` + `/media/series` as legacy — they are valid default Categories. Only 4 paths are truly legacy: `/media/films-anime`, `/media/films-family` (Radarr), `/media/anime`, `/media/family` (Sonarr). Fix before `/gsd-plan-phase 23`.

**Phase 22 carry-forward RESOLVED** (2026-05-27 live): 3 orphan torrents deleted (D-11); missing records reconciled — Radarr 5 searched / 2 deferred, Sonarr left to scheduler (D-10).

### Pending Todos

- `2026-05-27-activer-qbit-autotmm-via-arrconf-preferences-allowlist` (area: arrconf) — qBit `auto_tmm_enabled`/`category_changed_tmm_enabled` = false ⇒ nouveaux grabs tombent dans `/data/complete` au lieu de `/data/torrents/<category>`. Fix = activer `preferences.enable` dans `arrconf.yml`. Découvert Phase 23 UAT SC#3 (routage OK, save_path KO). Chart change → hors scope P23.
- `2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0` (area: ops) — migration filesystem média v0.2.0→v0.3.0 pas encore exécutée ⇒ 3 libs Jellyfin vides (Films, Films-Animation-Enfants, Séries-Émilie). Runbook déjà dans CLAUDE.md. Découvert Phase 23 UAT SC#5 (partial 7/10). Tâche opérateur manuelle, hors v0.8.0.

## Deferred Items

Items carried from v0.3.0 / v0.4.0 / v0.5.0 close — not in v0.8.0 scope, may be re-evaluated for v0.9.0+:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| uat_gap | phase-09 initContainer NFS uid=1000 cluster-time write test (09-HUMAN-UAT.md, 2 open scenarios) | partial — code correct, runtime UAT pending | v0.3.0 close (2026-05-22) |
| verification_gap | phase-09 VERIFICATION status human_needed (UAT-driven) | human_needed | v0.3.0 close (2026-05-22) |
| verification_gap | phase-10 VERIFICATION status human_needed (SC#1 cluster materialization + SC#3 TVDB-anime live routing) | human_needed | v0.3.0 close (2026-05-22) |
| infra_gap | SuggestArr ingress + auto-submit (currently port-forward + manual approval) | deferred | v0.4.0 close (2026-05-23) |
| infra_gap | arrconf-ui distribution (currently runs from source via `uv run`) | deferred | v0.4.0 close (2026-05-23) |
| upgrade_check | D-07-PLAYLIST-MGMT-NULL re-verify on Jellyfin 11.x upgrade | watch-only | v0.3.0 close (2026-05-22) |
| process | HUMAN-UAT frontmatter standardization (audit-open parser compat) | deferred | v0.5.0 close (2026-05-24) |

## Quick Tasks Completed

| Quick ID | Description | Date | Commit | Tests |
|----------|-------------|------|--------|-------|
| 260525-bj5 | client_base.py 4xx response.text[:500] logging (OBS-01) + respx test + chart co-bump 0.12.1 → 0.14.0 | 2026-05-25 | 9726d81 | 416 pass (+5 new) |

## Operator Next Steps

1. **Fix Phase 23 SC#1/#2 legacy-path error** in ROADMAP (`/media/films` + `/media/series` are NOT legacy — only the 4 `films-anime`/`films-family`/`anime`/`family` paths are).
2. `/gsd-discuss-phase 23` → `/gsd-plan-phase 23` — UAT dispositive (end-to-end verification), last phase of v0.8.0.
3. Optional future: full Category tag migration to retire residual legacy per-type DCs + tags (see Phase 22 DONE note).
