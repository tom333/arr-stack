---
phase: 06
plan: 04
subsystem: arrconf/reconcilers
tags: [seerr, reconciler, python, wave-2]
dependency_graph:
  requires: [06-02, 06-03]
  provides: [reconcile_seerr, SeerrClient, seerr-cli-dispatch]
  affects: [06-06, 06-07]
tech_stack:
  added: []
  patterns: [isDefault-matching, manual-apiKey-preservation, POST-not-PUT-settings/main]
key_files:
  created:
    - tools/arrconf/arrconf/reconcilers/seerr.py
    - tools/arrconf/tests/test_reconcilers_seerr.py
  modified:
    - tools/arrconf/arrconf/client_base.py
    - tools/arrconf/arrconf/__main__.py
    - tools/arrconf/arrconf/settings.py
decisions:
  - "SeerrClient placed between ProwlarrClient and QbittorrentClient in client_base.py (logical grouping: /api/v1 apps together)"
  - "Defensive PUT mocks added to _mock_all_gets helper in tests — prevents AllMockedAssertionError when non-focus resources drift from defaults"
  - "_payloads_equivalent uses desired-subset-of-current semantics (not full equality) to ignore server-computed fields"
metrics:
  duration: ~8 minutes
  completed_date: "2026-05-16"
  tasks: 3
  files_created: 2
  files_modified: 3
---

# Phase 6 Plan 4: SeerrClient + reconcile_seerr Summary

**One-liner:** SeerrClient + 4-resource reconciler (settings/sonarr, settings/radarr, user, settings/main) with isDefault matching, manual apiKey preservation (D-06-CREDS-01), and 17 respx tests at 86% coverage.

## Completed Tasks

| Task | Description | Commit |
|------|-------------|--------|
| 4.1 | SeerrClient in client_base.py + seerr CLI dispatch in __main__.py | da932ef |
| 4.2 | reconcile_seerr implementation (4 resources, 320 LOC) | cf43b1d |
| 4.3 | 17 respx tests, 86% coverage on arrconf.reconcilers.seerr | 1b49d05 |

## Verification Results

- Tests: **17 passed** (target: ≥12) — `uv run pytest tests/test_reconcilers_seerr.py`
- Coverage: **86%** on `arrconf.reconcilers.seerr` (target: ≥80%)
- Full suite: **217 passed** (no regressions)
- ruff + mypy: clean on all 4 modified/created files

## Critical Invariants Tested

| Invariant | Test | Status |
|-----------|------|--------|
| Pitfall 1: id excluded from PUT body | test_settings_sonarr_put_body_excludes_id | PASS |
| Pitfall 2: settings/main uses POST | test_settings_main_uses_post_not_put | PASS |
| Pitfall 3: activeProfileName excluded | test_settings_sonarr_excludes_activeProfileName_from_put | PASS |
| D-06-CREDS-01: apiKey preserved | test_settings_sonarr_apikey_preserved_when_yaml_empty | PASS |
| ADR-5 frontiere | test_seerr_does_not_call_arr_v3_quality_endpoints | PASS |
| Idempotence (no-op) | test_settings_sonarr_no_op_when_cluster_matches, test_user_no_op_when_permissions_match | PASS |

## Implementation Notes

**User fixture shape:** The `/api/v1/user` fixture is dict-paginated: `{pageInfo: {...}, results: [user]}`. The reconciler defends both paginated-dict and bare-list shapes. Tests verify the paginated path.

**SEERR_API_KEY:** Added to `settings.py` as `seerr_api_key: SecretStr | None = None` — was NOT already present (Phase 6 is first to use it).

**LOC count:**
- `reconcilers/seerr.py`: 320 LOC (target ~250; extra comes from detailed docstrings and defensive comment blocks)
- `tests/test_reconcilers_seerr.py`: 730 LOC (17 tests)

**_payloads_equivalent semantics:** Compares only the keys present in `desired` against `current`. Server-computed fields (activeProfileName, timestamps) in `current` are ignored. This is the same pattern as D-05-MIG-01 idempotence.

**Defensive mocks in tests:** The `_mock_all_gets` helper registers defensive PUT/POST mocks for all 4 Seerr endpoints. This prevents `AllMockedAssertionError` when a test focuses on one resource but others detect drift. Tests that need to assert on specific routes register their own named route variable AFTER calling `_mock_all_gets`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Defensive PUT mocks in _mock_all_gets**
- **Found during:** Task 4.3 — first test run
- **Issue:** The radarr fixture has `tags=[]` and `tagRequests=false` but `_make_instance()` sets `tags=[2]` and `tagRequests=True`. When a test focused on sonarr, the radarr reconcile also fired a PUT, hitting an unmocked route and raising `AllMockedAssertionError`.
- **Fix:** Added defensive PUT/POST mocks to `_mock_all_gets` so all 4 write endpoints are pre-registered. Tests asserting on specific routes can still override the route variable.
- **Files modified:** `tests/test_reconcilers_seerr.py`
- **Impact:** Test isolation improved — all 17 tests pass correctly.

## Known Stubs

None — plan executed completely with working reconciler logic.

## Threat Surface Scan

No new network endpoints added beyond what the plan specified. The reconciler uses the existing `SeerrClient` which inherits from `ArrApiClient` and only calls `/api/v1/*` endpoints on the Seerr host. No new trust boundary crossings introduced.

## Self-Check: PASSED

- [x] `tools/arrconf/arrconf/reconcilers/seerr.py` exists
- [x] `tools/arrconf/tests/test_reconcilers_seerr.py` exists
- [x] Commits da932ef, cf43b1d, 1b49d05 exist in git log
- [x] 17 tests pass, 86% coverage, 217 total pass (no regressions)
- [x] ruff + mypy clean on all 4 files
