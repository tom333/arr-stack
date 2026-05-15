---
phase: "05-reconciler-qbittorrent-split-tv-anime-family"
plan: "06"
subsystem: "arrconf/reconcilers/radarr"
tags: [radarr, movie-editor, tags, remote-path-mapping, adr-7-split, d-05-order-01, d-05-split-02]

dependency_graph:
  requires: ["05-02 (config schema + MovieTagsSection)", "05-05 (Sonarr split — analog)"]
  provides: ["_reconcile_movie_tags", "_reconcile_tags (radarr)", "arrconf/reconcilers/_shared.py"]
  affects: ["reconcile_radarr ordering", "test_movie_editor.py (new)", "test_reconcilers_radarr.py (extended)"]

tech_stack:
  added: ["arrconf/reconcilers/_shared.py (byte-equivalent shared helpers)"]
  patterns:
    - "D-05-ORDER-01 mirror: fixed 9-step reconcile ordering with step_begin log events (Radarr)"
    - "Radarr schema divergence: movieIds (not seriesIds), addImportExclusion (not addImportListExclusion)"
    - "Shared helpers extracted to _shared.py: _reconcile_remote_path_mappings + _resolve_download_client_tag_labels"
    - "default_tag='movies' per D-05-SPLIT-02 (Radarr convention: matches qBit category 'radarr-movies')"
    - "Deferred default_tag lookup: only raises ReconcileError when untagged movies exist AND tag missing"

key_files:
  created:
    - tools/arrconf/arrconf/reconcilers/_shared.py
    - tools/arrconf/tests/test_movie_editor.py
  modified:
    - tools/arrconf/arrconf/reconcilers/radarr.py
    - tools/arrconf/arrconf/reconcilers/sonarr.py
    - tools/arrconf/tests/test_reconcilers_radarr.py

decisions:
  - "Shared helpers extracted to _shared.py (option a from plan): _reconcile_remote_path_mappings and _resolve_download_client_tag_labels are byte-equivalent between Sonarr and Radarr per PATTERNS line 391 — extracted once to avoid maintenance drift"
  - "sonarr.py updated to import from _shared.py: no behavioral change, import refactor only"
  - "REMOTE_PATH_MAPPING_PATH constant removed from sonarr.py: now owned by _shared.py internally"
  - "_reconcile_movie_tags stays in radarr.py: Radarr-specific endpoint + body field names"
  - "_reconcile_tags duplicated in radarr.py (not extracted to _shared): typed to RadarrClient, minor difference from sonarr.py's SonarrClient typing"

metrics:
  duration: "~35 minutes"
  completed_date: "2026-05-14"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 3
---

# Phase 05 Plan 06: Radarr ADR-7 Split — Movie Editor + Tags + Remote Path Mappings Summary

Mirrors Plan 05's Sonarr extensions onto Radarr with three key substitutions: `series` → `movie`, `default_tag="tv"` → `default_tag="movies"` (D-05-SPLIT-02), and `addImportListExclusion` → `addImportExclusion` (Radarr/Sonarr schema divergence per RESEARCH lines 220–231). Shared helpers extracted to `arrconf/reconcilers/_shared.py`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 6.1 | Extend reconcile_radarr (radarr.py + sonarr.py + _shared.py) | 15df455 | reconcilers/radarr.py, reconcilers/sonarr.py, reconcilers/_shared.py, tests/test_reconcilers_radarr.py |
| 6.2 | Author test_movie_editor.py + extend test_reconcilers_radarr.py | 76903cc | tests/test_movie_editor.py, tests/test_reconcilers_radarr.py |

## What Was Built

### Task 6.1 — reconcile_radarr extension

**`arrconf/reconcilers/_shared.py` (NEW)**

Extracted two byte-equivalent helpers from sonarr.py (PATTERNS line 391):
- `_reconcile_remote_path_mappings(client, items, prune, dry_run)` — composite-key DELETE+ADD
- `_resolve_download_client_tag_labels(items, all_tags, app_name)` — label→id resolver with per-app error message

Both sonarr.py and radarr.py now import from `_shared.py`. The `sonarr.py` file's own implementations were removed (no behavioral change).

**`arrconf/reconcilers/radarr.py` (EXTENDED)**

Three new functions added:

**`_reconcile_tags(client, section, dry_run) -> list[Tag]`**
- Mirror of sonarr._reconcile_tags; typed to RadarrClient
- Re-fetches `/tag` after reconcile to capture server-assigned IDs

**`_reconcile_movie_tags(client, section, all_tags, dry_run) -> list[str]`**
- Radarr-specific — stays in radarr.py (different endpoint + body field names)
- GET `/movie` (not `/series`)
- PUT `/movie/editor` (not `/series/editor`)
- Body uses `movieIds` (not `seriesIds`) — T-05-CONTENT threat mitigation
- Body uses `addImportExclusion: False` (not `addImportListExclusion`) — Radarr divergence per RESEARCH lines 220–231
- default_tag `"movies"` per D-05-SPLIT-02 (matches qBit category `radarr-movies`)
- All other invariants identical: `applyTags="add"`, `moveFiles=False`, `deleteFiles=False`

**`reconcile_radarr` — 9-step ordered execution (D-05-ORDER-01 mirror)**

Each step emits `log.info("step_begin", step="...", step_index=N)`:
1. managed_tag — `_ensure_managed_tag`
2. tags — `_reconcile_tags` (captures `all_tags`)
3. indexers — `_reconcile_list_resource`
4. root_folders — `_reconcile_list_resource`
5. remote_path_mappings — `_reconcile_remote_path_mappings` (from `_shared`)
6. download_clients — label resolver + `_reconcile_list_resource`
7. notifications — `_reconcile_list_resource`
8. host_config — `_reconcile_host_config`
9. movie_tags — `_reconcile_movie_tags`

### Task 6.2 — Test suite

**New `test_movie_editor.py` (9 tests):**
- `test_movie_editor_adds_default_tag_to_untagged_movies` — 11 movies → 1 PUT /movie/editor
- `test_movie_editor_idempotent_when_all_tagged` — no PUT when all tagged
- `test_movie_editor_preserves_existing_manual_tags` — 1 tagged → 10 updated
- `test_movie_editor_does_not_move_files` — moveFiles=False, deleteFiles=False invariant
- `test_movie_editor_uses_movieIds_not_seriesIds` — schema divergence guard (RESEARCH 220–231)
- `test_movie_editor_uses_addImportExclusion_not_addImportListExclusion` — schema divergence guard
- `test_movie_editor_dry_run_emits_no_put` — dry_run=True suppresses PUT
- `test_movie_editor_skipped_when_section_disabled` — enable=False: no GET /movie, no PUT
- `test_movie_tags_raises_when_default_tag_label_missing_from_yaml` — ReconcileError guard

**Extended `test_reconcilers_radarr.py` (3 new tests):**
- `test_split_three_tags_three_root_folders_three_download_clients_radarr` — ADR-7 split: 3 tag POSTs + 3 RF POSTs + 3 DC POSTs with integer IDs
- `test_reconcile_order_radarr` — D-05-ORDER-01 ordering regression (capsys JSON fallback)
- `test_download_client_tags_label_resolution_uses_just_created_id_radarr` — label resolver uses just-created ID (id=42)

**Coverage results:** 89% on `arrconf/reconcilers/radarr.py` (threshold: 70%). 83% overall. 185 tests pass.

## Shared Helper Extraction Decision

Per plan option (a): shared helpers extracted to `_shared.py` because `_reconcile_remote_path_mappings` and `_resolve_download_client_tag_labels` are byte-equivalent between Sonarr and Radarr (PATTERNS line 391). The `_reconcile_tags` function was NOT extracted — while functionally similar, it is typed to the concrete client class in each file (SonarrClient vs RadarrClient). The `_reconcile_movie_tags` function is Radarr-specific (different endpoint, different body field names) and stays in radarr.py.

## Sonarr/Radarr Schema Divergence Verification

Dispositive grep counts on `tools/arrconf/arrconf/reconcilers/radarr.py`:
- `grep -c '"addImportListExclusion"' radarr.py` → **0** (only appears in docstring, not code)
- `grep -c '"seriesIds"' radarr.py` → **0**

Both counts are 0 — schema divergence correctly applied.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing radarr tests broke due to new unmocked endpoints**
- **Found during:** Task 6.1 implementation (reconciler now always calls `/remotepathmapping` and `/movie`)
- **Issue:** `AllMockedAssertionError: RESPX: GET /remotepathmapping not mocked!` in test_reconcilers_radarr.py
- **Fix:** Added `remotepathmappings` and `movies` kwargs to `_mock_radarr_gets()` (same pattern as Plan 05 deviation #1 for sonarr.py)
- **Files modified:** tests/test_reconcilers_radarr.py
- **Commit:** 15df455

**2. [Rule 1 - Bug] Ruff E501 line-too-long in test files**
- **Found during:** Task 6.2 CI gate (ruff check)
- **Issue:** 4 lines exceeded 100-char limit in test_movie_editor.py and test_reconcilers_radarr.py
- **Fix:** Wrapped long string literals and shortened docstring first lines
- **Files modified:** tests/test_movie_editor.py, tests/test_reconcilers_radarr.py
- **Commit:** 76903cc

## Known Stubs

None — all data paths are wired through the real reconciler and API mocks.

## Threat Flags

None — no new network endpoints introduced to the reconciler's external surface. The reconciler only calls existing Radarr API endpoints (`/tag`, `/remotepathmapping`, `/movie`, `/movie/editor`). No new auth paths or trust boundaries added.

## Self-Check: PASSED

Files confirmed present:
- tools/arrconf/arrconf/reconcilers/radarr.py: FOUND
- tools/arrconf/arrconf/reconcilers/_shared.py: FOUND
- tools/arrconf/arrconf/reconcilers/sonarr.py: FOUND (updated)
- tools/arrconf/tests/test_movie_editor.py: FOUND
- tools/arrconf/tests/test_reconcilers_radarr.py: FOUND (updated)

Commits confirmed:
- 15df455 (Task 6.1): FOUND
- 76903cc (Task 6.2): FOUND

Test gate: 185 passed, 0 failed
Coverage gate: 89% on radarr.py >= 70% required; 84% overall >= 70% required
Mypy gate: 0 issues
Ruff gate: 0 issues
