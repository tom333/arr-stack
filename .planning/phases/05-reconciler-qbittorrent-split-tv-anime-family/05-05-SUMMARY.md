---
phase: "05-reconciler-qbittorrent-split-tv-anime-family"
plan: "05"
subsystem: "arrconf/reconcilers/sonarr"
tags: [sonarr, tags, remote-path-mapping, series-editor, adr-7-split, d-05-order-01]

dependency_graph:
  requires: ["05-02 (config schema + tag_labels field)", "05-03 (Sonarr reconciler base)"]
  provides: ["_reconcile_tags", "_reconcile_remote_path_mappings", "_reconcile_series_tags", "_resolve_download_client_tag_labels"]
  affects: ["reconcile_sonarr ordering", "schemas/arrconf-schema.json"]

tech_stack:
  added: []
  patterns:
    - "D-05-ORDER-01: fixed 9-step reconcile ordering with step_begin log events"
    - "DELETE+ADD for remote_path_mappings (no PUT endpoint), composite-key (host, remotePath)"
    - "Deferred default_tag lookup: only raises ReconcileError when untagged series exist AND tag missing"
    - "label→id resolver: tag_labels (list[str]) resolved to int IDs after tags reconcile step"
    - "structlog.testing.capture_logs() with capsys JSON fallback for frozen-logger environments"

key_files:
  created:
    - tools/arrconf/tests/test_series_editor.py
    - tools/arrconf/tests/test_remote_path_mapping.py
  modified:
    - tools/arrconf/arrconf/reconcilers/sonarr.py
    - tools/arrconf/arrconf/resources/sonarr/download_client.py
    - tools/arrconf/tests/test_reconcilers_sonarr.py
    - tools/arrconf/tests/test_scope_violation.py
    - tools/arrconf/tests/test_cli.py
    - tools/arrconf/tests/test_managed_tag.py
    - tools/arrconf/tests/test_round_trip.py
    - schemas/arrconf-schema.json

decisions:
  - "Deferred default_tag error: ReconcileError only fires when untagged series exist AND the configured default_tag_label is not in all_tags — preserves idempotence when cluster is already tagged"
  - "Re-fetch tags after _reconcile_list_resource: the generic helper doesn't return server-assigned IDs, so a second GET /tag after the reconcile step provides the fresh id→label mapping for the label resolver"
  - "capsys fallback for test_reconcile_order: configure_logging() with cache_logger_on_first_use=True freezes the bound logger; structlog.testing.capture_logs() gets 0 events in full suite runs; fallback parses JSON lines from stdout"
  - "tag_labels field with exclude=True: separate from tags (list[int]) so label strings never reach the Sonarr API; resolver converts labels to IDs and merges into tags before reconcile"

metrics:
  duration: "~75 minutes (cross-session)"
  completed_date: "2026-05-14"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 8
---

# Phase 05 Plan 05: Sonarr ADR-7 Split — Tags, Remote Path Mappings, Series Tags Summary

Extends `reconcile_sonarr` with four new sub-reconcilers implementing the ADR-7 single-instance split: label-managed tags (`tv`/`anime`/`family`), composite-key remote path mappings (DELETE+ADD pattern), label→id resolver for download client routing, and bulk retroactive series tagging via `PUT /api/v3/series/editor` with D-05-ORDER-01 strict step ordering enforced by a regression test.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 5.1 | Extend reconcile_sonarr (sonarr.py + download_client.py) | fd58132 | reconcilers/sonarr.py, resources/sonarr/download_client.py |
| 5.2 | Test suite (new + extended) + schema regen | a29dea7 | 7 test files, schemas/arrconf-schema.json |

## What Was Built

### Task 5.1 — reconcile_sonarr extension

Four new functions added to `arrconf/reconcilers/sonarr.py`:

**`_reconcile_tags(client, section, dry_run) -> list[Tag]`**
- Delegates to generic `_reconcile_list_resource` with `match_key="label"`
- Re-fetches `/tag` after the reconcile pass to obtain server-assigned IDs
- Returns the fresh tag list for downstream label→id resolution

**`_resolve_download_client_tag_labels(items, all_tags) -> list[DownloadClient]`**
- Maps each `dc.tag_labels` string label to its integer ID from `all_tags`
- Raises `ReconcileError` immediately if any label is not found in the declared tags
- Merges resolved IDs into `dc.tags` without mutating the original

**`_reconcile_remote_path_mappings(client, items, prune, dry_run) -> list[str]`**
- Bespoke loop using composite key `(host, remotePath)` — no generic differ
- UPDATE = DELETE by id + POST (no PUT endpoint exists on Sonarr API)
- Verifies DELETE occurs before POST in the same update operation

**`_reconcile_series_tags(client, section, all_tags, dry_run) -> list[str]`**
- Fetches all series, filters those lacking the default tag ID
- Defers the default_tag lookup until after checking for untagged series (idempotence: no error if cluster is already fully tagged)
- Single `PUT /api/v3/series/editor` call with `applyTags="add"`, `moveFiles=False`, `deleteFiles=False`

**`reconcile_sonarr` — 9-step ordered execution (D-05-ORDER-01)**

Each step emits `log.info("step_begin", step="...", step_index=N)`:
1. managed_tag — `_ensure_managed_tag`
2. tags — `_reconcile_tags` (captures `all_tags`)
3. indexers — `_reconcile_list_resource`
4. root_folders — `_reconcile_list_resource`
5. remote_path_mappings — `_reconcile_remote_path_mappings`
6. download_clients — label resolver runs here, then `_reconcile_list_resource`
7. notifications — `_reconcile_list_resource`
8. host_config — `_reconcile_host_config`
9. series_tags — `_reconcile_series_tags`

**`DownloadClient.tag_labels: list[str]`** added with `exclude=True` — holds human-readable labels that the operator writes in YAML; never sent to the Sonarr API.

### Task 5.2 — Test suite

**New `test_series_editor.py` (7 tests):**
- `test_series_editor_adds_default_tag_to_untagged_series`
- `test_series_editor_idempotent_when_all_already_tagged`
- `test_series_editor_preserves_existing_manual_tags`
- `test_series_editor_does_not_move_files` (verifies `moveFiles=False`, `deleteFiles=False`)
- `test_series_editor_dry_run_emits_no_put`
- `test_series_tags_skipped_when_section_disabled`
- `test_series_tags_raises_when_default_tag_label_missing`

**New `test_remote_path_mapping.py` (6 tests):**
- `test_rpm_adds_new_mapping`
- `test_rpm_delete_plus_add_on_localpath_change` (verifies DELETE before POST)
- `test_rpm_no_op_when_in_sync`
- `test_rpm_match_by_host_and_remote_path_tuple` (prune=False skips orphan)
- `test_rpm_prune_true_deletes_orphan`
- `test_rpm_trailing_slash_invariant` (known gap: no auto-append; documented)

**Extended `test_reconcilers_sonarr.py` (3 new tests):**
- `test_split_three_tags_three_root_folders_three_download_clients`
- `test_reconcile_order` (D-05-ORDER-01 regression test; capsys fallback)
- `test_download_client_tags_label_resolution_uses_just_created_id`

**Extended `test_scope_violation.py` (2 new tests):**
- `test_series_tags_does_not_touch_quality_endpoints`
- `test_remote_path_mappings_does_not_touch_quality_endpoints`

**Coverage results:** 84% overall, 93% on `arrconf/reconcilers/sonarr.py` (threshold: 70%). 161 tests pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing tests broke due to new unmocked endpoints**
- **Found during:** Task 5.1 implementation (reconciler now always calls `/remotepathmapping` and `/series`)
- **Issue:** `AllMockedAssertionError: RESPX: GET /remotepathmapping not mocked` in test_cli.py, test_managed_tag.py, test_round_trip.py
- **Fix:** Added `respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))` and `respx_mock.get("/series").mock(...)` to all affected tests
- **Files modified:** tests/test_cli.py, tests/test_managed_tag.py, tests/test_round_trip.py, tests/test_reconcilers_sonarr.py
- **Commit:** a29dea7

**2. [Rule 1 - Bug] test_reconcile_order captures 0 structlog events in full suite**
- **Found during:** Task 5.2 test authoring
- **Issue:** `configure_logging()` in CLI tests sets `cache_logger_on_first_use=True`, freezing the bound logger; `structlog.testing.capture_logs()` cannot inject its capture processor into the frozen logger, so 0 events are captured when tests run in suite order
- **Fix:** Added capsys JSON-line fallback: if `cap_logs` is empty after reconcile, parse stdout lines as JSON and extract `step_begin` events with `step_index`
- **Files modified:** tests/test_reconcilers_sonarr.py

**3. [Rule 1 - Bug] SeriesTagsSection default `enable=True` caused ReconcileError in existing tests**
- **Found during:** Task 5.1 integration
- **Issue:** Existing tests construct `SonarrInstance` without a `series_tags` section (uses defaults); with `enable=True` default and no "tv" tag in `all_tags`, the reconciler raised `ReconcileError("default_tag_label 'tv' not found")`
- **Fix:** Moved the `default_tag` lookup AFTER checking whether `untagged_ids` is empty — early return if no series need tagging, so the error only fires when there's actual work to do AND the tag is not declared
- **Files modified:** arrconf/reconcilers/sonarr.py

**4. [Rule 1 - Bug] Schema mismatch in test_schema_committed_matches_regen**
- **Found during:** Task 5.1 (adding tag_labels to DownloadClient changed the generated schema)
- **Fix:** Regenerated `schemas/arrconf-schema.json` via `uv run python -m arrconf schema-gen`
- **Files modified:** schemas/arrconf-schema.json
- **Commit:** a29dea7

**5. [Rule 2 - Convention] Ruff N806 violation (JUST_CREATED_TV_ID uppercase constant)**
- **Found during:** Task 5.2 ruff check
- **Fix:** Renamed `JUST_CREATED_TV_ID` to `just_created_tv_id` (local variable, not module-level constant)
- **Files modified:** tests/test_reconcilers_sonarr.py

## Known Stubs

None — all data paths are wired through the real reconciler and API mocks.

## Threat Flags

None — no new network endpoints introduced to the reconciler's external surface. The reconciler only calls existing Sonarr API endpoints (`/tag`, `/remotepathmapping`, `/series`, `/series/editor`). No new auth paths or trust boundaries added.

## Self-Check: PASSED

Files confirmed present:
- tools/arrconf/arrconf/reconcilers/sonarr.py: FOUND
- tools/arrconf/tests/test_series_editor.py: FOUND
- tools/arrconf/tests/test_remote_path_mapping.py: FOUND
- schemas/arrconf-schema.json: FOUND

Commits confirmed:
- fd58132 (Task 5.1): FOUND
- a29dea7 (Task 5.2): FOUND

Test gate: 161 passed, 0 failed
Coverage gate: 84% >= 70% required
Mypy gate: 0 issues
Ruff gate: 0 issues
