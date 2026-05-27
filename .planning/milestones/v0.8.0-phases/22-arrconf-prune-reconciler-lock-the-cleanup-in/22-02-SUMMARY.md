---
phase: 22-arrconf-prune-reconciler-lock-the-cleanup-in
plan: "02"
subsystem: operator-runbook
tags: [runbook, adr, live-cleanup, orphan-torrents, missing-records, sc2-gate, adr-6-snapshot]
dependency_graph:
  requires: [force_prune-path, "arrconf-image-0.15.0-deployed"]
  provides: [22-RUNBOOK, 22-ADR-PLAN-SPLIT, live-cleanup-executed, sc2-idempotence-verified]
  affects: [live-cluster-sonarr, live-cluster-radarr, live-cluster-qbittorrent]
tech_stack:
  added: []
  patterns: [adr-6-snapshot-before-after, surgical-id-delete, dry-run-gate-d06]
key_files:
  created:
    - .planning/phases/22-arrconf-prune-reconciler-lock-the-cleanup-in/22-RUNBOOK.md
    - .planning/phases/22-arrconf-prune-reconciler-lock-the-cleanup-in/22-ADR-PLAN-SPLIT.md
    - snapshots/before-phase22-cleanup-2026-05-27/
    - snapshots/after-phase22-cleanup-2026-05-27/
  modified: []
decisions:
  - "SC#2 dry-run gate passed with shipped config (prune=false): 0 plan_action on root_folders/tags/download_clients for sonarr+radarr — both BEFORE and AFTER the live cleanup (idempotent)."
  - "C (legacy config prune) executed as SURGICAL id-targeted DELETE, NOT via force_prune/prune=true apply. A prune=true dry-run preview revealed force_prune would over-delete: legacy tags tv(10)/family(3,8)/anime + the custom 1-moi tag (collateral) + legacy per-type DCs — because the cluster is in a mixed tag state (legacy + Category tags coexist). Shipped config stays prune=false."
  - "C scope reduced to the clearly-safe + ADR-documented targets only: 4 legacy root folders (content migrated in Phase 21) + the catch-all qBittorrent DC id=1 (ADR-2 target, priority=1 mis-route cause). Legacy per-type DCs (TV/Anime/Family/Movies) and legacy tags DEFERRED pending full Category tag migration (out of Phase 22 scope)."
  - "B (missing re-monitor): Radarr searched 5 released titles (ids 2,3,8,11,12); deferred 2 unreleased-2026 titles (Mario Galaxy, Jumpers). Sonarr: no manual search triggered — 9 series missing look like normal monitored backlog (Winx 52, Elena 25, NCIS Origins 34), left to the Sonarr scheduler to avoid an indexer storm (T-22-10)."
metrics:
  completed: "2026-05-27"
  tasks_completed: 2
  files_created: 4
---

# Phase 22 Plan 02: operator live cleanup + plan-split ADR Summary

Close the v0.2.0 legacy migration: ship the operator runbook + plan-split ADR (Task 1), then execute the live destructive cleanup against the my-kluster cluster running arrconf `:0.15.0` (Task 2, human-action checkpoint).

## What Was Built

**Task 1 — docs (commit `3964c90`):**
- `22-RUNBOOK.md` (321 lines, French) — pre-snapshot, port-forward+creds, SC#2 dry-run gate, 3 orphan-torrent deletes (full hashes, deleteFiles=true), 10 missing re-monitor + MissingMoviesSearch (2026-unreleased exception), post-snapshot+diff.
- `22-ADR-PLAN-SPLIT.md` (104 lines, Status: Accepted) — 2-plan split rationale + DC catch-all full-prune decision (no `unsorted` fallback).

**Task 2 — live cleanup (executed against cluster, arrconf `:0.15.0` deployed):**
- **SC#2 gate** — `arrconf apply --dry-run --apps sonarr,radarr` (shipped prune=false config via port-forward): **0 plan_action** on root_folders/tags/download_clients. D-06 gate PASS.
- **A — 3 orphan torrents deleted** (qBit `POST /api/v2/torrents/delete deleteFiles=true`, HTTP 200, all confirmed GONE):
  - `eebc5732…` Zelda Twilight Princess (ROM), `cfb5b5b9…` Home Alone 1990, `a766daa8…` Spy Kids 2001 (all stalledUP on /data/complete, no *arr match).
- **B — missing re-monitor**: Radarr RefreshMovie + MoviesSearch for 5 released (Solo Leveling, Dans tes rêves, Insaisissables, Les Alphas, La Planète des Alphas); 2 deferred (Mario Galaxy 2026, Jumpers 2026). Sonarr: no manual search (monitored → scheduler).
- **C — surgical legacy delete** (id-targeted DELETE, HTTP 200 each):
  - catch-all DC `qBittorrent` id=1 (sonarr + radarr) — ADR-2 target.
  - 4 legacy root folders: sonarr `/media/anime` (id2), `/media/family` (id3); radarr `/media/films-anime` (id2), `/media/films-family` (id3).
- **ADR-6 snapshots**: `before-` and `after-phase22-cleanup-2026-05-27/` captured (5/6 apps) + committed; diff bounded to expected mutations (qbit torrents, sonarr/radarr downloadclient + rootfolder, jellyfin storage freed).
- **Final SC#2 re-check** (post-cleanup, prune=false): **0 plan_action**, no legacy roots/catch-all in prune_skip — idempotent clean.

## Verification

- SC#2 dry-run = 0 plan_action (before AND after cleanup) — D-06 gate + idempotence proven live.
- 3 orphan hashes return `[]` on `GET /api/v2/torrents/info` — GONE.
- catch-all DC count=0 + legacy root count=0 on both sonarr/radarr post-delete.
- Snapshots committed (ADR-6 lossless, secrets auto-redacted, 0 leak scan).

## Deviations from Plan

- **C added beyond the original runbook scope** (operator decision this session). The runbook (Task 1) covered A (orphans) + B (missing) + SC#2 gate only. C (legacy config prune) was added live, then reduced to surgical id-targeted deletes after a prune=true dry-run preview exposed force_prune over-deletion in the cluster's mixed tag state.
- **B Sonarr**: no search triggered (backlog ambiguity + storm risk); records left monitored for the scheduler.
- **Legacy per-type DCs + legacy tags NOT removed** — deferred to a future Category tag migration (the `1-moi` custom tag and active content_routing tags would be collateral).

## Roadmap Success Criteria

- SC#2 (live dry-run 0 plan_action on arrconf :0.15.0): ✅ verified before + after cleanup.
- SC#4 (DC catch-all full-prune documented in phase ADR): ✅ 22-ADR-PLAN-SPLIT.md Decision 2 + catch-all id=1 removed live.
- CAT-CLEANUP-03 operator portion (D-09/10/11): ✅ 3 orphans deleted, missing records reconciled (5 searched / 2 deferred / Sonarr scheduler).

## Known Stubs

- Legacy per-type DCs (qBittorrent - TV/Anime/Family/Movies) + legacy tags (tv/family/anime/movies/1-moi) remain in-cluster — require full Category tag migration before safe removal (future milestone).

## Self-Check: PASSED
