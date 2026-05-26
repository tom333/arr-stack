---
phase: 21-filesystem-metadata-migration
plan: 01
subsystem: migration-script
tags: [phase-21, cat-cleanup-02, migration, throwaway-script, halt-on-error]
status: awaiting-human-action
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
  duration: "~10 minutes"
  completed_date: 2026-05-26
  tasks_completed: 6
  tasks_pending: 1
  files_created: 2
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

## Task 7 — BLOCKING checkpoint awaiting operator

Task 7 is `<task type="checkpoint:human-action" gate="blocking">` — Claude **cannot** automate the live cluster apply for these reasons (locked in CONTEXT §"D-21-TOOL-04" + threat model T-21-02):

1. Operator workstation has the kubectl context for `my-kluster` and the 4 port-forwards.
2. Operator workstation has the NFS mount at `/mnt/nas/media-stack/` — `os.rename` happens on the host, not in this sandbox.
3. Operator extracts the sealed-secret `arrconf-env` at run time (5 API credentials cross trust boundary live).
4. Snapshot pre/post commits (Étape 1 + Étape 5) bracket the destructive run as ADR-6 forensic evidence.
5. Halt-on-first-error requires operator judgment to diagnose before re-running.

### Operator next steps (follow 21-RUNBOOK.md verbatim)

1. **Étape 1** — `tools/snapshot/snapshot.sh --output snapshots/before-categories-cleanup-$(date +%F)/` + commit `snapshot(21): pre-categories-cleanup baseline`
2. **Étape 2** — `kubectl port-forward` on radarr/sonarr/qbittorrent/jellyfin + extract `arrconf-env`
3. **Étape 3** — `uv run python tools/scripts/migrate-categories.py --audit … --dry-run` (mandatory pre-flight)
4. **Étape 4** — `uv run python tools/scripts/migrate-categories.py --audit … --apply` (halt-on-error; re-run if halt)
5. **Étape 5** — Post-snapshot + diff (bounded to audit-driven mutations) + commit `snapshot(21): post-categories-cleanup baseline` + audit-verify sanity check

### Expected SC outcomes (per ROADMAP)

- **SC1** — both `before-categories-cleanup-$(date +%F)/` and `after-categories-cleanup-$(date +%F)/` exist + committed
- **SC2** — 11 Radarr movies now on Category `rootFolderPath` (none on `/media/films` legacy)
- **SC3** — 10 Sonarr series anchored on Category roots; episode files re-detected after RefreshSeries
- **SC4** — 37 qBit torrents on `/data/torrents/<cat>/`; 3 orphans remain on `/data/complete` (Phase 22 owns)
- **SC5** — Jellyfin 10 Category libs each ItemCount > 0 post `/Library/Refresh`

## Deviations from Plan

**None.** Plan executed exactly as written. The plan's anti-pattern guards (acceptance criteria check for grep-zero on `moveFiles`, `forceSave=`, retry loops, pause/resume, etc.) were all hit on the first pass — no rework needed.

Minor format-driven adjustments:
- Triade Python required `UP017` fix: `from datetime import timezone` + `datetime.now(timezone.utc)` → `from datetime import UTC, datetime` + `datetime.now(UTC)` (Python 3.11+ idiom). Functionally identical.
- Triade Python required `no-any-return` fix in `_load_state`: explicit `isinstance(loaded, dict)` narrowing + sys.exit(2) on non-dict (defensive — covers a corrupt-state edge case).
- Ruff format reflowed multi-line argparse / function calls — no semantic changes.

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
