---
phase: "07"
plan: "04"
subsystem: arrconf
tags: [jellyfin, reconciler, dump, diff, sc4, round-trip, pitfall-mitigations]
dependency_graph:
  requires: ["07-02", "07-03"]
  provides: ["07-05", "07-06"]
  affects: ["tools/arrconf/arrconf/reconcilers/jellyfin.py", "tools/arrconf/arrconf/dump.py", "tools/arrconf/arrconf/diff_cmd.py", "tools/arrconf/arrconf/__main__.py"]
tech_stack:
  added: []
  patterns: ["respx mock", "MediaBrowser Token auth", "dry-run exit-code 3 contract", "SC#4 round-trip idempotence"]
key_files:
  created:
    - tools/arrconf/arrconf/reconcilers/jellyfin.py
    - tools/arrconf/tests/test_reconcilers_jellyfin.py
    - tools/arrconf/tests/test_dump.py
    - tools/arrconf/tests/test_diff_cmd.py
  modified:
    - tools/arrconf/arrconf/client_base.py
    - tools/arrconf/arrconf/__main__.py
    - tools/arrconf/arrconf/dump.py
    - tools/arrconf/arrconf/diff_cmd.py
decisions:
  - "JellyfinClient inherits ArrApiClient NOT _ArrV3Client (ADR-8: Jellyfin has no /api/v3 prefix)"
  - "diff_jellyfin gates on :dry_run: string markers in actions_taken (not result.plan — jellyfin reconciler shape differs from sonarr)"
  - "9 Pitfall mitigations shipped: Pitfall 1 (POST full-replace), 2 (path set-membership), 3 (DELETE-never), 4 (POST not PUT Policy), 5 (version in Enable path), 6 (ProviderIds re-injected from cluster), 7 (PluginRepositories set-by-URL), 8 (PathInfos not Locations), 9 (Token in header not URL)"
  - "prune=False hardcoded for libraries (D-07-LIB-01) and users (D-07-USERS-01) — safety-critical, not opt-in"
  - "dump_jellyfin strips Pitfall 5 (no version) and Pitfall 6 (ProviderIds) to guarantee round-trip idempotence"
metrics:
  duration: "~5 hours (split across two context windows)"
  completed: "2026-05-17T03:00:46Z"
  tasks_completed: 6
  files_count: 8
---

# Phase 07 Plan 04: Jellyfin Reconciler + CLI Dispatch Summary

JellyfinClient + reconcile_jellyfin (9 Pitfall mitigations, 4 ordered steps) + dump_jellyfin + diff_jellyfin + 24 respx tests wired into arrconf CLI with SC#4 round-trip idempotence proven at unit test layer.

## Tasks Completed

| Task | Name | Commit | Files |
|---|---|---|---|
| 4.1 | JellyfinClient + apply dispatch | `6814635` | `client_base.py`, `__main__.py` |
| 4.2 | reconcile_jellyfin (4 steps, 9 Pitfalls) | `3496c26` | `reconcilers/jellyfin.py` |
| 4.3 | 15 respx tests for reconciler | `6d8c85a` | `tests/test_reconcilers_jellyfin.py` |
| 4.4 | dump_jellyfin | `93f4ec7` | `dump.py` |
| 4.5 | diff_jellyfin | `93f4ec7` | `diff_cmd.py` |
| 4.6 | CLI dispatch (dump + diff) + tests | `93f4ec7` | `__main__.py`, `test_dump.py`, `test_diff_cmd.py` |

## Verification Results

- **pytest:** 269 passed, 84% coverage (threshold 70%) — all tests pass
- **ruff check:** clean (no issues)
- **mypy (new/modified files):** clean — `arrconf/dump.py`, `arrconf/diff_cmd.py`, `arrconf/__main__.py`, `tests/test_dump.py`, `tests/test_diff_cmd.py` all pass
- **mypy (full):** 46 pre-existing errors in test files not touched by this plan — logged to `deferred-items.md`, out of scope per SCOPE BOUNDARY rule

## Success Criteria Verification

| Criterion | Status |
|---|---|
| JellyfinClient with api_path="", MediaBrowser Token auth | DONE |
| reconcile_jellyfin 4 steps in D-07-ORDER-01 order | DONE |
| 9 Pitfall mitigations implemented | DONE |
| ≥10 respx tests for reconciler | DONE (15 tests) |
| dump_jellyfin round-trippable YAML | DONE |
| diff_jellyfin exit 0 / exit 3 contract | DONE |
| SC#4 round-trip proven at unit layer | DONE (test_diff_jellyfin_round_trip_with_dump) |
| Coverage ≥70% | DONE (84%) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] respx assert_all_called teardown errors in test_reconcilers_jellyfin.py**
- **Found during:** Task 4.3 test execution
- **Issue:** `_mock_all_gets` helper registered defensive POST mocks (VirtualFolders/Paths, Users/Policy, System/Configuration, Plugins/Enable) for routes never called when steps were no-ops. respx default `assert_all_called=True` raised errors at teardown for uncalled routes.
- **Fix:** Removed all defensive POST mocks from `_mock_all_gets`. Added `assert_all_called=False` to all 12 `@pytest.mark.respx` markers.
- **Files modified:** `tests/test_reconcilers_jellyfin.py`
- **Commit:** `6d8c85a`

**2. [Rule 1 - Bug] respx route shadowing broke capture_body side_effect in Pitfall 4+1 tests**
- **Found during:** Task 4.3 test execution
- **Issue:** `_mock_all_gets` registered a second `POST /Users/{id}/Policy` (and `POST /System/Configuration`) AFTER the test's `capture_post` route. Respx route ordering caused the second registration to shadow the `side_effect` capture, so `captured_body` was always `{}`.
- **Fix:** Same fix as Deviation 1 — removing defensive POSTs from `_mock_all_gets` eliminated the duplicate registrations.
- **Files modified:** `tests/test_reconcilers_jellyfin.py`
- **Commit:** `6d8c85a`

**3. [Rule 1 - Bug] Users step was non-no-op in tests expecting no-op (EnablePublicSharing mismatch)**
- **Found during:** Task 4.3 test execution
- **Issue:** Production fixture `user_moi_full.json` has `EnablePublicSharing: true`. `_make_instance()` default admin policy omitted `EnablePublicSharing`, so it defaulted to `False`. This drift caused the users step to fire a POST in tests that expected a no-op.
- **Fix:** Added `EnablePublicSharing=True` to `_make_instance()` default admin policy. Updated `_user_moi_full_fixture()` local helper accordingly.
- **Files modified:** `tests/test_reconcilers_jellyfin.py`
- **Commit:** `6d8c85a`

**4. [Rule 1 - Bug] ruff D413 in dump.py (missing blank line after Notes section)**
- **Found during:** Task 4.4 ruff check
- **Issue:** `ruff check` flagged D413 on `dump_jellyfin` docstring Notes section.
- **Fix:** `uv run ruff check --fix` auto-corrected.
- **Files modified:** `arrconf/dump.py`
- **Commit:** `93f4ec7`

**5. [Rule 1 - Bug] ruff I001 in test_diff_cmd.py (unsorted imports inside test function)**
- **Found during:** Task 4.6 ruff check
- **Issue:** Two separate `from arrconf.config import` blocks inside test function body caused I001.
- **Fix:** `uv run ruff check --fix` auto-corrected (merged into one sorted block).
- **Files modified:** `tests/test_diff_cmd.py`
- **Commit:** `93f4ec7`

## Known Stubs

None — all 4 resources (libraries, users, server_config, plugins) are fully wired with live API fetch and YAML serialization. No placeholder text or empty data sources.

## Threat Flags

None — no new network endpoints introduced. JellyfinClient consumes existing `JELLYFIN_API_KEY` env var (already in arrconf-env secret, verified in Plan 07-01 evidence). API key is passed as `MediaBrowser Token` header (not URL query parameter — Pitfall 9 mitigated).

## Self-Check: PASSED

All 8 key files verified present on disk. All 4 task commits (`6814635`, `3496c26`, `6d8c85a`, `93f4ec7`) verified in git log.
