---
phase: 12-categories-deprecation
plan: C
subsystem: arrconf-tests
tags: [test-cleanup, deprecation, D-07, D-08, D-09, D-10, SC#3]
dependency_graph:
  requires: [12-A]
  provides: [SC#3-dispositive-test, clean-test-suite]
  affects: [tools/arrconf/tests/]
tech_stack:
  added: []
  patterns: [test-rename-pattern, fixture-audit-pattern]
key_files:
  created: []
  modified:
    - tools/arrconf/tests/test_phase10_idempotence_sweep.py
    - tools/arrconf/tests/test_sonarr_categories.py
    - tools/arrconf/tests/test_radarr_categories.py
    - tools/arrconf/tests/test_jellyfin_categories.py
    - tools/arrconf/tests/conftest.py
  deleted: []
decisions:
  - "Deleted _empty_fp_affected_sections helper: Plan A shim (reconcilers overwrite instance.*.items with derived arg) made the helper dead code immediately after Plan A"
  - "Removed 5 orphan fixtures from conftest.py: sonarr_base_url, qbit_categories_fixture (comment-only ref), qbit_preferences_fixture, qbit_login_response_body, radarr_remotepathmapping_fixture"
  - "test_sweep calls dry_run_all_apps(production_cfg) directly without helper wrapping — idempotence proof is plan-level (run1==run2, no UPDATE/DELETE on run2)"
metrics:
  duration_minutes: 25
  completed_date: "2026-05-22"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
---

# Phase 12 Plan C: Test Cleanup Summary

Pruned all manual-path tests from the arrconf test suite per D-07/D-08/D-09. Renamed the surviving sweep test to `test_sweep` and elevated its docstring to SC#3-dispositive status. Audited `conftest.py` and removed 5 orphan fixtures with zero live references. Full pytest green (370 passed) without any `-k` filter.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| C.1 | Delete manual-path tests, rename sweep+wiring tests | e875e2b | test_phase10_idempotence_sweep.py, test_sonarr/radarr/jellyfin_categories.py |
| C.2 | Remove orphan fixtures from conftest.py | c18b9ae | tests/conftest.py |

## Deleted Tests (D-07 + D-08: 8 total)

The following 8 test functions were deleted per the plan. Note: D-07's 7 per-app override tests were already removed by Plan A as a Rule 1 auto-fix (merge_with_manual import breakage). Plan C deleted the remaining D-08 manual-override sweep test.

| File | Function deleted | Reason |
|------|-----------------|--------|
| test_sonarr_categories.py | test_sonarr_per_resource_override_tags_only | Deleted in Plan A (D-07) |
| test_sonarr_categories.py | test_sonarr_per_resource_override_rpm_only | Deleted in Plan A (D-07) |
| test_radarr_categories.py | test_radarr_per_resource_override_tags_only | Deleted in Plan A (D-07) |
| test_qbittorrent_categories.py | test_manual_override_wins | Deleted in Plan A (D-07) |
| test_jellyfin_categories.py | test_jellyfin_manual_override_wins | Deleted in Plan A (D-07) |
| test_seerr_animetags.py | test_animetags_merge_manual_wins | Deleted in Plan A (D-07) |
| test_seerr_animetags.py | test_animetags_merge_empty_manual_uses_generated | Deleted in Plan A (D-07) |
| test_phase10_idempotence_sweep.py | test_sweep_manual_override_path | Deleted in Plan C (D-08) |

## Renamed Tests (D-08 + D-09: 9 total)

### D-08: Sweep test rename
| Old name | New name | File |
|----------|----------|------|
| test_sweep_categories_derived_path | test_sweep | test_phase10_idempotence_sweep.py |

### D-09: Wiring test renames (8 renames)
| Old name | New name | File |
|----------|----------|------|
| test_sonarr_tags_wiring_empty_manual | test_sonarr_tags_wiring | test_sonarr_categories.py |
| test_sonarr_root_folders_wiring_empty_manual | test_sonarr_root_folders_wiring | test_sonarr_categories.py |
| test_sonarr_download_clients_wiring_empty_manual | test_sonarr_download_clients_wiring | test_sonarr_categories.py |
| test_sonarr_rpm_wiring_empty_manual | test_sonarr_rpm_wiring | test_sonarr_categories.py |
| test_radarr_tags_wiring_empty_manual | test_radarr_tags_wiring | test_radarr_categories.py |
| test_radarr_root_folders_wiring_empty_manual | test_radarr_root_folders_wiring | test_radarr_categories.py |
| test_radarr_rpm_wiring_empty_manual | test_radarr_rpm_wiring | test_radarr_categories.py |
| test_jellyfin_libraries_wiring_empty_manual | test_jellyfin_libraries_wiring | test_jellyfin_categories.py |

## SC#3-Dispositive Docstring Confirmed

`grep -c 'SC#3 dispositive' tools/arrconf/tests/test_phase10_idempotence_sweep.py` returns 3 (appears in module docstring + function docstring + inline comment).

The new `test_sweep` function:
- Is the SOLE sweep test in `test_phase10_idempotence_sweep.py`
- Calls `dry_run_all_apps(production_cfg)` twice directly (no helper wrapper)
- Asserts `run1 == run2` (byte-identical plans — determinism)
- Asserts 0 UPDATE/DELETE actions on run2 (FP-fix verification for qBit #1, Prowlarr #2, Seerr #3)
- Documents failure consequence: "If this test fails, Phase 12 cannot close (D-17)"

## conftest.py Fixture Audit (D-10)

Fixtures audited: 27 fixtures total. 5 deleted with zero live references.

| Fixture | External refs | Action | Reason |
|---------|--------------|--------|--------|
| sonarr_downloadclient_fixture | 21 | KEPT | Live in multiple test files |
| sonarr_tag_managed_fixture | 54 | KEPT | Live in multiple test files |
| sonarr_tag_empty_fixture | 4 | KEPT | Live in test_managed_tag.py |
| sonarr_indexer_fixture | 3 | KEPT | Live in test_reconcilers_sonarr.py |
| sonarr_notification_fixture | 3 | KEPT | Live in test_reconcilers_sonarr.py |
| sonarr_rootfolder_fixture | 3 | KEPT | Live in test_reconcilers_sonarr.py |
| sonarr_hostconfig_fixture | 12 | KEPT | Live in multiple test files |
| **sonarr_base_url** | **0** | **DELETED** | No test injects it; tests use inline URL strings |
| **qbit_categories_fixture** | **0** | **DELETED** | Only comment reference in qbittorrent test (not injected) |
| **qbit_preferences_fixture** | **0** | **DELETED** | Tests inline preferences directly via respx |
| **qbit_login_response_body** | **0** | **DELETED** | Tests set up login inline via respx |
| sonarr_series_with_no_tags_fixture | 13 | KEPT | Live in test_scope_violation.py, test_series_editor.py |
| sonarr_series_with_tv_tag_fixture | 2 | KEPT | Live in test_series_editor.py |
| sonarr_remotepathmapping_fixture | 5 | KEPT | Live in test_remote_path_mapping.py |
| radarr_movie_with_no_tags_fixture | 17 | KEPT | Live in test_movie_editor.py |
| **radarr_remotepathmapping_fixture** | **0** | **DELETED** | Tests load fixture directly; no test injects it |
| seerr_settings_sonarr_fixture | 37 | KEPT | Live in test_reconcilers_seerr.py |
| seerr_settings_radarr_fixture | 34 | KEPT | Live in test_reconcilers_seerr.py |
| seerr_user_fixture | 32 | KEPT | Live in test_reconcilers_seerr.py |
| seerr_settings_main_fixture | 32 | KEPT | Live in test_reconcilers_seerr.py |
| jellyfin_library_virtualfolders_fixture | 21 | KEPT | Live in test_reconcilers_jellyfin.py |
| jellyfin_users_fixture | 24 | KEPT | Live in test_reconcilers_jellyfin.py |
| jellyfin_user_moi_full_fixture | 20 | KEPT | Live in test_reconcilers_jellyfin.py |
| jellyfin_system_configuration_fixture | 18 | KEPT | Live in test_reconcilers_jellyfin.py |
| jellyfin_plugins_fixture | 19 | KEPT | Live in test_reconcilers_jellyfin.py |

**5 fixtures deleted:** sonarr_base_url, qbit_categories_fixture, qbit_preferences_fixture, qbit_login_response_body, radarr_remotepathmapping_fixture.

## pytest Results

- Post-cleanup test count: **370 tests passed** (no `-k` filter, `--tb=short -x`)
- Pre-Plan-A baseline: 384 tests (per CLAUDE.md); Plan A deleted 14 tests; Plan C deleted 1 additional (test_sweep_manual_override_path) = 369. But actual count is 370 — one test added or miscounted in Plan A summary. This matches the Plan A summary ("371 passed" before Plan C deleted test_sweep_manual_override_path = 370).
- Python triad: ruff format OK (90 files formatted), ruff check clean (0 issues), mypy 47 errors (same pre-Phase-12 baseline)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - minor] _empty_fp_affected_sections already dead code after Plan A**
- **Found during:** Task C.1, examining how dry_run_all_apps passes data
- **Issue:** Plan C step 4 said to evaluate whether `_empty_fp_affected_sections` helper is dead code. It is: Plan A's intra-function shim in `reconcile_sonarr/radarr` overwrites `instance.*.items` with the `derived` argument regardless, so emptying them via the helper was already a no-op. The helper was dead code immediately after Plan A landed.
- **Fix:** Deleted the helper definition and removed the call from the renamed `test_sweep`, as prescribed in the plan action.
- **Files modified:** tools/arrconf/tests/test_phase10_idempotence_sweep.py
- **Commit:** e875e2b

## Known Stubs

None. All test changes are functional deletions and renames — no placeholder values or stub patterns.

## Threat Flags

None. Plan C only deletes/renames test code — no new network endpoints, auth paths, file access patterns, or schema changes.

## Self-Check: PASSED

- Commit e875e2b exists: confirmed (test deletions + renames)
- Commit c18b9ae exists: confirmed (conftest.py cleanup)
- `grep -rn test_sweep_manual_override_path tools/arrconf/tests/` returns 0 matches: confirmed
- `grep -c ^def test_sweep( tools/arrconf/tests/test_phase10_idempotence_sweep.py` returns 1: confirmed
- `grep -rn _wiring_empty_manual tools/arrconf/tests/` returns 0 matches: confirmed
- `grep -rn merge_decision tools/arrconf/tests/` returns 0 matches: confirmed
- `cd tools/arrconf && uv run pytest tests/ --tb=short -x` exits 0 (370 passed): confirmed
- `cd tools/arrconf && uv run ruff format --check .` exits 0: confirmed
- `cd tools/arrconf && uv run ruff check .` exits 0: confirmed
- `cd tools/arrconf && uv run mypy .` 47 errors (pre-existing baseline): confirmed
