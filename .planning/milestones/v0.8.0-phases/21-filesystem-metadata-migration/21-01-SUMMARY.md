---
phase: 21-filesystem-metadata-migration
plan: 01
subsystem: migration-script
tags: [phase-21, cat-cleanup-02, migration, throwaway-script, halt-on-error]
status: complete
requires:
  - .planning/phases/20-categories-cleanup-audit/20-AUDIT.md (YAML appendix consumed)
  - tools/arrconf/arrconf/client_base.py (RadarrClient/SonarrClient/QbittorrentClient/JellyfinClient via path injection)
  - tools/arrconf/arrconf/exceptions.py (ApiClientError/AuthError/NotFoundError/ServerError)
  - tools/snapshot/snapshot.sh (ADR-6 pre + post baselines)
provides:
  - tools/scripts/migrate-categories.py (one-shot migration executable)
  - .planning/phases/21-filesystem-metadata-migration/21-RUNBOOK.md (operator runbook)
  - .gitignore entries for .migration-state.json + tempfile pattern
affects:
  - tools/scripts/ (new file — hors arrconf per D-21-TOOL-01)
  - .gitignore (appended state-file patterns)
tech_stack:
  added: []
  patterns:
    - "Path-injection import (sys.path.insert) — reuse arrconf client classes without packaging"
    - "Atomic state persistence (tempfile in same dir + os.rename, POSIX atomic)"
    - "Halt-on-first-error with per-item state checkpointing (D-21-FAIL-01)"
    - "Dry-run zero-HTTP gate — all HTTP-triggering construction gated on `not args.dry_run`"
key_files:
  created:
    - tools/scripts/migrate-categories.py
    - .planning/phases/21-filesystem-metadata-migration/21-RUNBOOK.md
  modified:
    - .gitignore
decisions:
  - "D-21-TOOL-01 — script lives under tools/scripts/, NOT under tools/arrconf/"
  - "D-21-TOOL-02 — NO chart-pin co-bump (script hors arrconf, not packaged in GHCR image)"
  - "D-21-TOOL-03 — NO respx tests (throwaway script); Triade Python (ruff/mypy) green"
  - "D-21-ORDER-01 — filesystem os.rename FIRST, then API PUT — never delegate move to Radarr"
  - "D-21-ORDER-02 — resume via re-running same command; .migration-state.json skips completed"
  - "D-21-ORDER-03 — batched RefreshMovie/RefreshSeries at end of each *arr loop"
  - "D-21-ORDER-04 — retag_only items skip os.rename, only PUT"
  - "D-21-QBIT-01 — direct setLocation, NO pause/resume"
  - "D-21-QBIT-02 — setCategory immediately after setLocation in same loop iteration"
  - "D-21-QBIT-03 — 3 PRUNE_PHASE_22 orphans skipped silently"
  - "D-21-JF-01 — single global POST /Library/Refresh via _request bypass (204 empty body)"
  - "D-21-FAIL-01 — halt-on-first-error, no retry, no continue-on-error"
metrics:
  duration: "~10 minutes (build) + live operator run 2026-05-27"
  completed_date: 2026-05-27
  tasks_completed: 7
  tasks_pending: 0
  files_created: 4
  files_modified: 1
  lines_added: 623
---

# Phase 21 Plan 21-01: Filesystem + metadata migration Summary

**One-liner:** One-shot Python migration script (hors arrconf) + operator runbook deliver the deterministic plan from 20-AUDIT.md — 11 Radarr + 10 Sonarr + 37 qBit + Jellyfin global refresh, halt-on-first-error, atomic resume state; live cluster apply awaits operator (Task 7 BLOCKING checkpoint).

## What's Built

**6 of 7 tasks executed and committed** (Task 7 is a `checkpoint:human-action gate="blocking"` requiring the operator's live cluster execution per D-21-TOOL-04 — see Resume Signal below).

### Commits

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| 1 | `fd6353d` | feat(21) | Migration script skeleton — CLI + env-gate + YAML loader + state.json + .gitignore |
| 2 | `16dcddc` | feat(21) | Radarr migration loop — os.rename + PUT /movie/{id} + batched RefreshMovie |
| 3 | `06a05e3` | feat(21) | Sonarr migration loop — os.rename + PUT /series/{id} + batched RefreshSeries |
| 4 | `37d9bb4` | feat(21) | qBittorrent migration loop — setLocation + setCategory, skip 3 orphans |
| 5 | `35573d5` | feat(21) | Jellyfin global refresh + finalize main() — dry-run smoke green |
| 6 | `9049a8d` | docs(21) | Operator runbook 21-RUNBOOK.md — French, mirrors CLAUDE.md FS migration shape |
| 7a | `80d2b20` | fix(21) | `--media-root` + `_to_host_path()` — cluster→host path translation for os.rename |
| 7b | `f6c34bb` | fix(21) | `_maybe_rename()` — conditional rename keyed on disk state (drift handling) |
| 7c | `62a3d30` | fix(21) | both_missing → soft-skip to API PUT (operator decision) |
| 7d | `0dad89c` | snapshot(21) | pre-categories-cleanup baseline (ADR-6) |
| 7e | `bfdd8a2` | snapshot(21) | post-categories-cleanup baseline (ADR-6) — SC1-SC5 verified |

### Files

**Created (2):**
- `tools/scripts/migrate-categories.py` (623 lines) — standalone `__main__`, NOT a Typer subcommand, hors arrconf per D-21-TOOL-01. Reuses `RadarrClient` / `SonarrClient` / `QbittorrentClient` / `JellyfinClient` from `arrconf.client_base` via `sys.path` injection.
- `.planning/phases/21-filesystem-metadata-migration/21-RUNBOOK.md` (159 lines) — French operator runbook mirroring `CLAUDE.md §"Filesystem migration: v0.2.0 flat → v0.3.0 Categories"` shape: Pré-requis / Étape 1-5 / Troubleshooting / Rollback.

**Modified (1):**
- `.gitignore` — added `.migration-state.json` + `.migration-state.*.tmp` (live IDs, not a project artifact).

### Script feature matrix

| Feature | Locked decision | Implementation |
|---------|-----------------|----------------|
| CLI flags | argparse, 5 flags | `--audit / --apply / --dry-run / --state-file / --verbose` (NO `--resume-from`) |
| Env-var gate | D-21-FAIL-01 | `_check_env_vars` exits 2 on any missing of 5 required vars |
| Audit input | YAML appendix | `_load_audit_appendix` — regex + ruyaml (mirrors arrconf/audit.py:925-943) |
| State persistence | atomic POSIX | `_save_state` — tempfile in same dir + `os.rename` |
| Radarr loop | D-21-ORDER-01 | os.rename → `radarr.put('/movie', id=mid, json=body)` (force-save auto-injected by `_ArrV3Client.put`, ADR-8) |
| Sonarr loop | D-21-ORDER-01 | Mechanically symmetric to Radarr — `/series/{id}` + RefreshSeries |
| qBit loop | D-21-QBIT-01/02/03 | direct setLocation → setCategory same iteration; 3 PRUNE_PHASE_22 orphans skipped |
| Jellyfin | D-21-JF-01 | Single global `jellyfin._request("POST", "/Library/Refresh")` (bypasses `.json()` for 204) |
| Dry-run | zero-HTTP | All client construction + GET /tag calls gated on `not args.dry_run` |
| Halt-on-error | D-21-FAIL-01 | per-item try/except → `migration_halt` structlog + `sys.exit(1)`. No retry, no sleep. |

### Dry-run smoke test (verified locally)

```
RADARR_API_KEY=dummy SONARR_API_KEY=dummy QBT_USER=dummy QBT_PASS=dummy JELLYFIN_API_KEY=dummy \
  uv run --project tools/arrconf python tools/scripts/migrate-categories.py \
  --audit .planning/phases/20-categories-cleanup-audit/20-AUDIT.md --dry-run
```

Output ends with:
```
migration_complete dry_run=True jellyfin_refreshed=True qbit_migrated=37 radarr_migrated=11 sonarr_migrated=10
```

Counts confirm:
- 11 Radarr movies, 10 Sonarr series — match 20-AUDIT.md counts
- 37 qBit torrents migrated + 3 orphans skipped (PRUNE_PHASE_22) = 40 total in audit
- Jellyfin refresh would dispatch (skipped under dry-run)
- ZERO HTTP traffic (dummy creds, no port-forwards required for dry-run)

### Triade Python — green

```
cd tools/arrconf && uv run ruff format --check ../scripts/migrate-categories.py  # OK
cd tools/arrconf && uv run ruff check ../scripts/migrate-categories.py           # All checks passed
cd tools/arrconf && uv run mypy ../scripts/migrate-categories.py                 # Success: no issues
```

## Task 7 — Live operator run COMPLETE (2026-05-27)

The operator (assisted by Claude driving the runbook) ran the migration live against `my-kluster` / `selfhost`. All 5 ROADMAP success criteria verified.

### Étapes executed

1. **Étape 2** (port-forwards + creds) — 4 forwards (radarr 7878 / sonarr 8989 / qbittorrent 8080 / jellyfin 8096) via a background supervisor; `arrconf-env` sealed-secret extracted to a `umask 077` temp file (cleaned up post-run).
2. **Étape 1** (pre-snapshot) — `snapshots/before-categories-cleanup-2026-05-27/` (4 apps, 0 secret leaks) committed `0dad89c`.
3. **Étape 3** (dry-run) — reached `migration_complete dry_run=True radarr=11 sonarr=10 qbit=37`; surfaced the disk-state drift (see Deviations).
4. **Étape 4** (apply) — `migration_complete dry_run=False jellyfin_refreshed=True qbit_migrated=37 radarr_migrated=11 sonarr_migrated=10`. **No halt.** 1 real FS move (Winx Club anime→series-zoe); 10 items `fs_move_skip_file_missing`; 3 orphans skipped.
5. **Étape 5** (post-snapshot + diff) — `snapshots/after-categories-cleanup-2026-05-27/` committed `bfdd8a2`; diff bounded to expected mutations only.

### SC outcomes — ALL VERIFIED (live curls)

- **SC1** ✓ — pre (`0dad89c`) + post (`bfdd8a2`) snapshots committed; `diff -rq` bounded to: 37 qBit save_path+category, Jellyfin scheduled_tasks (refresh ran) + system_storage timestamps, Radarr rootfolder freeSpace. 0 secret leaks both snapshots.
- **SC2** ✓ — Radarr: 0 movies on `/media/films`; 11 distributed as 5 films-animation-enfants + 3 films-enfants + 2 films-zoe + 1 nouveaux-films.
- **SC3** ✓ — Sonarr: 0 series on `/media/anime`; 10 distributed as 6 series + 4 series-zoe.
- **SC4** ✓ — qBit: 3 torrents remain on `/data/complete` (exactly the PRUNE_PHASE_22 orphans); 37 relocated to `/data/torrents/<cat>/` with matching category (1 films-animation-enfants + 3 films-enfants + 2 films-zoe + 22 series + 9 series-zoe).
- **SC5** ✓ — Jellyfin `/Library/Refresh` dispatched 204; all 10 Category VirtualFolders present (Séries, Nouveaux Films, Séries - Zoé, Séries - Garçons, Films - Animation Enfants, Films - Enfants, Séries - Thomas, Films, Films - Zoé, Séries - Émilie). ItemCount populates async post-refresh.

## Deviations from Plan

**Material deviation: audit-vs-disk drift discovered at live run.** The plan assumed the disk matched the Phase 20 audit (2026-05-25). At apply time (2026-05-27), the filesystem had drifted — manual cleanup/moves had happened between audit capture and apply. Three script fixes were required mid-run (all committed, Triade green):

| Commit | Fix | Why |
|--------|-----|-----|
| `80d2b20` | `--media-root` flag + `_to_host_path()` — translate cluster `/media/<x>` → host `/mnt/nas/media-stack/<x>` for `os.rename` only (API PUTs keep cluster paths) | The script ran from the host per D-21-TOOL-04 but did `os.rename` on raw cluster paths — `/media/films` doesn't exist on the host (NFS mounted at `/mnt/nas/media-stack`). Would have hard-failed on Radarr item 1. |
| `f6c34bb` | `_maybe_rename()` — conditional rename keyed on src/dst existence (src_only→rename, dst_only→skip, both_missing→halt, both_exist→halt) | Some files already moved into Category dirs; some vanished. A blind `os.rename` would fail. |
| `62a3d30` | `both_missing` → soft-skip to API PUT (was halt) — **operator decision** | 10 of 11 FS-move items were `both_missing` (files removed since audit). Operator chose to sync the DB anyway; items surface as missing on next library scan, cleaned up later. |

**Resulting disk states at apply:**
- 1× `src_only` → real `os.rename` (Winx Club: `anime/Winx Club (2004)` → `series-zoe/Winx Club (2004)`).
- 10× `both_missing` → `fs_move_skip_file_missing` warning + API PUT only (DB synced to Category path; file absent).
- All 21 *arr API PUTs succeeded (`put_force_save_used` ×21, ADR-8 forceSave).

**Follow-up for Phase 22 / operator:** the 10 `both_missing` movies/series now point at Category root folders but have no file on disk — they will show as "missing" in Radarr/Sonarr. Operator should decide per-item (re-download via monitored search, or remove from the *arr). A leftover `series-zoe/Winx Club` (bare, no year) dir remains alongside the moved `Winx Club (2004)` — harmless, operator may prune.

Minor build-time format adjustments (executor, Tasks 1-6):
- `UP017`: `datetime.now(timezone.utc)` → `datetime.now(UTC)` (Python 3.11+ idiom). Functionally identical.
- `no-any-return` in `_load_state`: explicit `isinstance(loaded, dict)` narrowing + sys.exit(2) on corrupt state.

## D-21-TOOL-02 Compliance — chart-pin UNCHANGED

```
$ git diff main -- charts/arr-stack/values.yaml | grep -cE '^[+-]\s+tag:'
0
```

Confirmed: `charts/arr-stack/values.yaml#arrconf.image.tag` was NOT modified in any of the 6 commits. The script is hors `tools/arrconf/`, not packaged in `ghcr.io/tom333/arr-stack-arrconf`, so the CLAUDE.md §"Release pin co-bump pattern" §Exception applies — no co-bump required. Phase 22 (arrconf prune reconciler) will be the next trigger for an image bump.

## Authentication Gates

None encountered during executor run (dry-run smoke uses dummy creds). The script's env-var gate (`_check_env_vars`) is itself an auth gate but is not triggered until Task 7 (live apply). At Task 7, the operator extracts the sealed-secret `arrconf-env` and sets the 5 env vars per Runbook Étape 2 — this is a normal flow gate, not a failure.

## Known Stubs

None. Every function in the script is fully implemented (no `pass`, no placeholder returns). The only `# TODO` markers were transient between tasks (e.g. `# TODO Task 3:` after Task 2) — all were removed by Task 5 per the plan's acceptance criterion `grep -cE '# TODO Task' == 0`.

## Threat Flags

None new. Phase 21's `<threat_model>` already enumerated T-21-01 through T-21-12, all of which were implemented per the mitigations specified in the plan. No new surface introduced outside that register.

## Pointer to Phase 22

Phase 22 (`CAT-CLEANUP-03 — arrconf prune reconciler`) consumes the now-clean cluster state produced by Task 7. Pending v0.8.0 work after Task 7 sign-off:

- Phase 22 implements `prune: true` reconciler logic for the 4 legacy paths/tags (`/media/films` legacy roots, `films` / `anime` / `family` / `movies` legacy tags) inside `arrconf/`.
- Phase 22 will bump `arrconf.image.tag` (minor, `0.14.x → 0.15.0`) — that's the next chart-pin co-bump trigger.
- Phase 22 also owns the DC catch-all decision (prune vs `unsorted` fallback) and the 3 PRUNE_PHASE_22 orphan torrents.

## Self-Check: PASSED

Verified post-write:
- `tools/scripts/migrate-categories.py` — FOUND
- `.planning/phases/21-filesystem-metadata-migration/21-RUNBOOK.md` — FOUND
- `.gitignore` contains `.migration-state.json` + `.migration-state.*.tmp` — FOUND
- Commits `fd6353d`, `16dcddc`, `06a05e3`, `37d9bb4`, `35573d5`, `9049a8d` — all FOUND in `git log`
- `tools/arrconf/arrconf/migrate_categories.py` — correctly NOT present (D-21-TOOL-01)
- `charts/arr-stack/values.yaml#arrconf.image.tag` — UNCHANGED (D-21-TOOL-02)
