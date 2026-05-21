---
phase: 12-categories-deprecation
plan: A
subsystem: arrconf-core
tags: [reconciler-refactor, merge-with-manual, cleanup, co-bump]
dependency_graph:
  requires: []
  provides: [new-reconciler-signatures, merge_with_manual-deleted]
  affects: [tools/arrconf/arrconf/reconcilers/, tools/arrconf/arrconf/__main__.py, tools/arrconf/arrconf/diff_cmd.py]
tech_stack:
  added: []
  patterns: [D-03-derived-param, D-04-generator-callsite]
key_files:
  created: []
  modified:
    - tools/arrconf/arrconf/reconcilers/_shared.py
    - tools/arrconf/arrconf/reconcilers/sonarr.py
    - tools/arrconf/arrconf/reconcilers/radarr.py
    - tools/arrconf/arrconf/reconcilers/qbittorrent.py
    - tools/arrconf/arrconf/reconcilers/jellyfin.py
    - tools/arrconf/arrconf/reconcilers/seerr.py
    - tools/arrconf/arrconf/__main__.py
    - tools/arrconf/arrconf/diff_cmd.py
    - charts/arr-stack/values.yaml
  deleted:
    - tools/arrconf/tests/test_merge_with_manual.py
decisions:
  - "Plan A shim pattern: diff branches set instance.*.items from derived so diff_cmd.py functions keep their existing 2-arg wrapper signatures until Plan B removes the .items attribute entirely"
  - "diff_cmd.py updated (Rule 1 auto-fix): functions called reconcilers with 2-arg signatures that no longer existed after Task A.1; wired generators inside each diff_* function"
  - "Category test file rewrites (Rule 1 auto-fix): merge_with_manual deletion broke module-level imports in test_sonarr_categories.py, test_radarr_categories.py, test_qbittorrent_categories.py, test_jellyfin_categories.py, test_seerr_animetags.py; replaced with direct derived usage"
metrics:
  duration_minutes: 90
  completed_date: "2026-05-22"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 25
---

# Phase 12 Plan A: Reconciler Refactor Summary

Strips the v0.2.0 transition layer (`merge_with_manual`) from arrconf's Python core: deleted the function from `_shared.py`, removed all 22 callsites from `__main__.py`, refactored 5 reconciler entry points to accept generator output directly, and co-bumped the chart's arrconf image tag 0.6.7 → 0.7.0.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| A.1 | Reconciler entry-point new signatures | 5dd19a5 | reconcilers/sonarr.py, radarr.py, qbittorrent.py, seerr.py, jellyfin.py |
| A.2 | Delete merge_with_manual, wire callsites, co-bump | c7f95f1 | _shared.py, __main__.py, diff_cmd.py, 18 test files, values.yaml |

## What Changed

### Task A.1 — Reconciler entry points (5 files)

Each of the 5 reconciler entry points gained a new required positional parameter (Plan A pattern: intra-function shim reads `.items` internally so no deeper changes needed):

- `reconcile_sonarr(client, instance, derived: SonarrDerived, *, dry_run)` — shim sets `instance.{tags,root_folders,download_clients,remote_path_mappings}.items`
- `reconcile_radarr(client, instance, derived: RadarrDerived, *, dry_run)` — mirror of sonarr
- `reconcile_qbittorrent(client, instance, categories: list[QbitCategory], *, dry_run)` — shim sets `instance.categories.items`
- `reconcile_jellyfin(client, instance, libraries: list[JellyfinLibrary], *, dry_run)` — shim sets `instance.libraries.items`
- `reconcile_seerr(client, instance, anime_tags: list[int], *, dry_run)` — shim sets `instance.sonarr_service.animeTags`

### Task A.2 — Callsite removal + deletion + co-bump (20 files)

- `_shared.py`: deleted `merge_with_manual()` function (61 lines removed); file retains `_reconcile_remote_path_mappings` and `_resolve_download_client_tag_labels`
- `__main__.py` apply branches: removed 11 `merge_with_manual(...)` blocks; reconciler calls updated to pass the derived variable as 3rd positional arg
- `__main__.py` diff branches: removed 11 `merge_with_manual(...)` blocks; Plan A shim sets `instance.*.items = derived.*` so `diff_cmd.py` functions see same desired-state as apply
- `diff_cmd.py`: added `generate_*` imports; each diff function now calls generator and passes result as 3rd arg to reconciler
- `tests/test_merge_with_manual.py`: deleted
- 17 test files: callsites updated to pass derived/categories/libraries/animeTags as 3rd arg
- `charts/arr-stack/values.yaml`: `arrconf.image.tag: "0.6.7"` → `"0.7.0"` (minor bump, co-bump rule)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] diff_cmd.py had 2-arg reconciler calls that no longer matched signatures**
- **Found during:** Task A.2
- **Issue:** After Task A.1 added the required 3rd parameter, `diff_cmd.py`'s `diff_sonarr`, `diff_radarr`, `diff_qbittorrent`, `diff_jellyfin` functions still called reconcilers with the old 2-arg signature. This was a direct consequence of Task A.1's changes.
- **Fix:** Added `generate_*` imports to `diff_cmd.py`; each function now calls the relevant generator and passes the result as the 3rd arg.
- **Files modified:** `tools/arrconf/arrconf/diff_cmd.py`
- **Commit:** c7f95f1

**2. [Rule 1 - Bug] Category test files had module-level `merge_with_manual` imports that would break pytest collection**
- **Found during:** Task A.2
- **Issue:** `test_sonarr_categories.py`, `test_radarr_categories.py`, `test_qbittorrent_categories.py`, `test_jellyfin_categories.py`, `test_seerr_animetags.py` all imported `merge_with_manual` from `_shared.py` at module level. After deleting `merge_with_manual`, any pytest run would fail at collection even with the plan's `-k` filter (module-level import failure is not skippable by filter).
- **Fix:** Removed `merge_with_manual` usage; replaced `merge_with_manual([], derived.X, ...)` with direct `derived.X`. Removed per-resource override tests (e.g., `test_sonarr_per_resource_override_tags_only`) whose logic tested the now-deleted feature — these are the tests excluded by the plan's `-k` filter.
- **Files modified:** 5 category test files
- **Commit:** c7f95f1

**3. [Rule 1 - Bug] `test_remote_path_mapping.py` referenced undefined `instance` variable in two tests**
- **Found during:** ruff check F821 during Task A.2
- **Issue:** After the bulk test update in the prior session, two tests (`test_rpm_match_by_host_and_remote_path_tuple`, `test_rpm_prune_true_deletes_orphan`) had `SonarrDerived(tags=instance.tags.items, ...)` but the local variable was `instance_no_prune` / `instance_prune`.
- **Fix:** Replaced `instance.` with `instance_no_prune.` and `instance_prune.` respectively.
- **Files modified:** `tests/test_remote_path_mapping.py`
- **Commit:** c7f95f1

**4. [Rule 1 - Bug] `test_reconcilers_seerr.py` had 2 missed callsites without `anime_tags` arg**
- **Found during:** mypy run (2 extra errors above 47 baseline)
- **Issue:** Lines 730 and 759 called `reconcile_seerr(_make_client(), instance, dry_run=False)` without the new required `anime_tags` parameter.
- **Fix:** Added `instance.sonarr_service.animeTags` as 3rd arg.
- **Files modified:** `tests/test_reconcilers_seerr.py`
- **Commit:** c7f95f1

## Verification

- Python triad: ruff format OK, ruff check clean, mypy 47 errors (same as pre-Phase-12 baseline)
- pytest with plan filter: 370 passed, 1 deselected
- pytest full suite: 371 passed (13 tests deleted — 11 test_merge_with_manual.py + 2 per-resource override tests in category test files)
- `merge_with_manual` confirmed absent from all `arrconf/` source files (only appears in docstring/comment text)
- `values.yaml#arrconf.image.tag` = `"0.7.0"` (co-bump confirmed)

## Known Stubs

None. All reconciler changes are functional — Plan A shims are intentional bridge code (documented with "Plan B removes the .items attribute entirely" comments), not UI stubs or placeholder values.

## Threat Flags

None. This plan removes code (merge_with_manual) and refactors signatures — no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

- Commit 5dd19a5 exists: verified via git log
- Commit c7f95f1 exists: verified via git log
- `tools/arrconf/arrconf/reconcilers/_shared.py` exists without `merge_with_manual`: confirmed
- `tools/arrconf/tests/test_merge_with_manual.py` deleted: confirmed
- `charts/arr-stack/values.yaml` tag = "0.7.0": confirmed
- Python triad: all passed (ruff format clean, ruff check clean, mypy 47 errors)
- pytest: 371 passed
