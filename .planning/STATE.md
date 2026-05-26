---
gsd_state_version: 1.0
milestone: v0.8.0
milestone_name: Categories cleanup — v0.2.0 legacy migration close-out
status: executing
last_updated: "2026-05-26T22:19:21.519Z"
last_activity: 2026-05-26 -- Phase 22 execution started
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 4
  completed_plans: 2
  percent: 50
---

# Project State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.

**Current focus:** Phase 22 — arrconf-prune-reconciler-lock-the-cleanup-in

## Current Position

Phase: 22 (arrconf-prune-reconciler-lock-the-cleanup-in) — EXECUTING
Plan: 1 of 2
Status: Executing Phase 22
Last activity: 2026-05-26 -- Phase 22 execution started

### Phase 21 close-out notes (carry into Phase 22)

- Audit-vs-disk drift: 10 of 11 FS-move items were `both_missing` at apply (files removed
  between Phase 20 audit and the 2026-05-27 run). Their Radarr/Sonarr DB records were
  synced to Category root folders anyway (operator decision) — they now show as MISSING
  on disk. Phase 22 / operator must decide per-item (re-download via monitored search, or
  remove from the *arr).

- Script gained `--media-root` (host NFS translation), `_maybe_rename` (disk-state-keyed),
  and `both_missing` soft-skip during the live run. See 21-01-SUMMARY.md §Deviations.

- Leftover `series-zoe/Winx Club` (bare, no year) dir remains beside moved `Winx Club (2004)`
  — harmless, operator may prune.

- 3 PRUNE_PHASE_22 orphan torrents still on `/data/complete` — Phase 22 owns.

### Phase 20 success criteria (from ROADMAP.md)

1. `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md` exists and lists every Radarr movie + Sonarr series whose `rootFolderPath` is a legacy v0.2.0 path, with target Category path resolved per item.
2. Audit captures every qBit torrent whose `save_path` starts with a legacy `/data/torrents/<legacy>/` segment, with target Category save_path resolved.
3. Audit enumerates every Radarr/Sonarr tag that is legacy (`movies`, `family`, `films`, `anime`) vs Category, with proposed prune/rename action per tag.
4. `legacy_path → Category` and `legacy_tag → Category_tag` mapping tables are committed and validated against CLAUDE.md "Filesystem migration v0.2.0 → v0.3.0" reference table.

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

v0.8.0 decisions to be captured during `/gsd-discuss-phase 20` → `22` (anticipated: ambiguous-item mapping rules in Phase 20; DC catch-all `qBittorrent` disposition in Phase 22 — prune vs `unsorted` low-priority fallback).

### Blockers/Concerns

**Phase 21 complete** (live migration applied 2026-05-27, SC1-SC5 verified, PASS-WITH-CONCERNS). Carry-forward into Phase 22 (now folded into P22 scope per D-09/10/11 in 22-CONTEXT.md):

- 10 missing-on-disk *arr records → re-monitor + search (D-10)
- 3 PRUNE_PHASE_22 orphan torrents on `/data/complete` → delete torrent + data (D-11)

**ROADMAP Phase 23 SC error to fix** (flagged in 22-CONTEXT `<deferred>`): SC#1/SC#2 wrongly list `/media/films` + `/media/series` as legacy — they are valid default Categories. Only 4 paths are truly legacy: `/media/films-anime`, `/media/films-family` (Radarr), `/media/anime`, `/media/family` (Sonarr).

Risk register documented in `.planning/REQUIREMENTS.md` — Phase 22 destructive concerns (over-prune at apply, DC prune cutting in-flight torrents) gated by Triade Python + respx tests + `--dry-run` discipline + allowlist=categories[] safety boundary.

### Pending Todos

None at roadmap-ready. To be populated during `/gsd-discuss-phase 20` → `/gsd-plan-phase 20`.

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

1. **Phase 22 planning** — `/clear` then `/gsd-plan-phase 22` (consumes `22-CONTEXT.md`).
   Scope: arrconf prune steps (allowlist=categories[]) + pydantic legacy denylist guard

   + chart co-bump `0.14.1 → 0.15.0` + operator cleanup step (3 orphans + 10 missing).
2. Phase 22 will bump `arrconf.image.tag` 0.14.1 → 0.15.0 per CLAUDE.md §"Release pin co-bump pattern".
3. Then Phase 23 (UAT dispositive) — and fix the Phase 23 SC#1/#2 legacy-path error first.
