---
phase: "10"
plan: "J"
subsystem: arrconf-tests
tags: [idempotence, sc2, fp-fix, sweep, requirements, chart-pin]
dependency_graph:
  requires: [10-C, 10-F, 10-H]
  provides: [SC2-dispositive, phase10-baseline, prowlarr-fp2-complete]
  affects: [phase9-baseline, arrconf-schema]
tech_stack:
  added: []
  patterns: [dual-path-sweep, byte-equivalence-regression, allowlist-filter]
key_files:
  created:
    - tools/arrconf/tests/_arrconf_helpers.py
    - tools/arrconf/tests/test_phase10_idempotence_sweep.py
    - tools/arrconf/tests/fixtures/phase10-baseline-plans.json
  modified:
    - tools/arrconf/tests/test_idempotence_fp.py
    - tools/arrconf/tests/test_merge_with_manual.py
    - tools/arrconf/tests/fixtures/phase9-baseline-plans.json
    - tools/arrconf/arrconf/reconcilers/prowlarr.py
    - tools/arrconf/arrconf/resources/sonarr/download_client.py
    - schemas/arrconf-schema.json
    - .planning/REQUIREMENTS.md
    - charts/arr-stack/values.yaml
decisions:
  - "D-03a confirmed: qBit category names use bare <name>, not <kind>-<name>; REQUIREMENTS.md wording fixed"
  - "FieldKV.placeholder excluded from model_dump (same rationale as label/helpText/order)"
  - "Phase 9 baseline regenerated after placeholder fix (no UPDATE actions remain)"
  - "PROWLARR_APP_MANAGED_FIELD_NAMES allowlist (B2b) added as distinct constant"
metrics:
  duration: "~40 minutes active"
  completed: 2026-05-20
  tasks: 4
  files: 11
---

# Phase 10 Plan J: SC#2 Sweep + Requirements Wording + Chart-Pin 0.6.6 Summary

SC#2 dispositive sweep covering both Categories-derived and manual-override config paths; completed FP#2 fix for Prowlarr sub-field drift (FieldKV.placeholder + PROWLARR_APP_MANAGED_FIELD_NAMES); fixed REQUIREMENTS.md D-03a wording; bumped arrconf chart-pin to 0.6.6.

## Tasks Completed

| Task | Description | Status | Commit |
|------|-------------|--------|--------|
| 10-J-01 | Fork `_arrconf_helpers.py` from `_phase9_helpers.py` | Done | b0459db |
| 10-J-02 | SC#2 sweep test + phase10 baseline fixture | Done | b0459db |
| 10-J-03 | REQUIREMENTS.md `<kind>-<name>` → `<name>` (D-03a) | Done | b0459db |
| 10-J-04 | Bump arrconf chart-pin 0.6.5 → 0.6.6 | Done | b0459db |

All 4 tasks committed atomically in commit `b0459db`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] FieldKV.placeholder leaking into model_dump (root cause of Prowlarr FP#2)**

- **Found during:** Task 10-J-02 (sweep test revealed Prowlarr UPDATE on every run)
- **Issue:** Prowlarr's GET `/applications` response includes a `placeholder` key in each
  FieldKV dict (e.g., `placeholder: "http://localhost:9696"` on `prowlarrUrl` field).
  `FieldKV` uses `extra="allow"` and `placeholder` was NOT in the `exclude=True` list.
  It roundtripped into `__pydantic_extra__` and appeared in `model_dump()`, causing
  `diff_models` to flag `fields` as drifted on EVERY reconcile (current had `placeholder`,
  desired did not). This affected Sonarr and Radarr apps in Prowlarr.
- **Fix:** Added `placeholder: str | None = Field(default=None, exclude=True)` to `FieldKV`
  in `arrconf/resources/sonarr/download_client.py`.
- **Cascade:** Phase 9 baseline fixture had UPDATE actions for Prowlarr (the bug was
  pre-existing). After fix, baseline was regenerated — now 0 UPDATE/DELETE actions.
- **Cascade:** `schemas/arrconf-schema.json` regenerated (placeholder now declared).
- **Files modified:** `arrconf/resources/sonarr/download_client.py`, `schemas/arrconf-schema.json`,
  `tests/fixtures/phase9-baseline-plans.json`

**2. [Rule 2 - Missing] PROWLARR_APP_MANAGED_FIELD_NAMES sub-field allowlist (B2b)**

- **Found during:** Task 10-J-02 (after placeholder fix, verified remaining FP surface)
- **Issue:** Plan 10-H's FP#2 fix filtered top-level Application keys via
  `PROWLARR_APP_MANAGED_FIELDS`, but the cluster's `fields[]` list carries 10+ FieldKV
  entries (`syncCategories`, `importListSyncInterval`, `animeSyncCategories`, etc.) while
  desired only has 3 (prowlarrUrl, baseUrl, apiKey). Without filtering `fields[]` to managed
  names before `model_validate`, `diff_models` flags `fields` as drifted every run.
- **Fix:** Added `PROWLARR_APP_MANAGED_FIELD_NAMES = frozenset({"prowlarrUrl", "baseUrl", "apiKey"})`
  constant and applied filter in `reconcile_prowlarr` before `model_validate`.
- **Files modified:** `arrconf/reconcilers/prowlarr.py`, `tests/test_idempotence_fp.py`

**3. [Rule 1 - Bug] Pre-existing test failures in test_merge_with_manual.py**

- **Found during:** Task 10-J-01 (full test suite run revealed 2 failing tests)
- **Issue:** `configure_logging()` in `test_cli.py` calls `structlog.configure()` with
  `cache_logger_on_first_use=True` and JSON renderer, caching the bound logger in
  `_shared.py`'s module-level `log`. The autouse fixture in `test_merge_with_manual.py`
  reconfigured structlog but didn't restore it, leaving stdlib factory active after
  teardown. Downstream tests using `structlog.testing.capture_logs()` (jellyfin test)
  saw the wrong processor chain.
- **Fix:** Rewritten as yield fixture that saves/restores full `structlog._config._CONFIG`
  state AND `_shared_mod.log`, preventing state leakage across test files.
- **Files modified:** `tests/test_merge_with_manual.py`

## SC#2 Verification Results

Both sweep test paths pass with 0 UPDATE/DELETE actions on run 2:

**Categories-derived path (`test_sweep_categories_derived_path`):**
- Flat sections zeroed → `merge_with_manual` activates Categories-derived items
- Run 1 == Run 2 (byte-identical)
- Run 2 UPDATE/DELETE count: 0

**Manual-override path (`test_sweep_manual_override_path`):**
- Production config with flat sections populated → manual items win
- Run 1 == Run 2 (byte-identical)
- Run 2 UPDATE/DELETE count: 0

Expected actions on both paths: ADD (new resources not in v0.2.0 cluster fixtures) and
PRUNE-SKIP (extra cluster items preserved by prune=false). These are healthy — not FP bugs.

## Test Coverage

Final test suite: **381 tests pass** (up from 376 before this plan, due to 5 new tests).

New tests added:
- `test_prowlarr_app_managed_field_names_constant` — B2b allowlist constant verification
- `test_prowlarr_app_subfield_fp_fix_no_op_on_extra_fields` — B2b allowlist effectiveness
- `test_sweep_categories_derived_path` — SC#2 Categories path
- `test_sweep_manual_override_path` — SC#2 manual-override path (D-13 carry-forward)
- `test_phase10_baseline_fixture_exists_or_generate` — baseline freeze/regression

## Known Stubs

None. All tests use realistic fixtures; no placeholder/hardcoded data flows to production paths.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes at trust boundaries.

## Self-Check: PASSED

- [x] `tools/arrconf/tests/_arrconf_helpers.py` exists
- [x] `tools/arrconf/tests/test_phase10_idempotence_sweep.py` exists
- [x] `tools/arrconf/tests/fixtures/phase10-baseline-plans.json` exists
- [x] Commit `b0459db` exists: `git log --oneline | grep b0459db`
- [x] 381 tests pass
- [x] ruff: no issues
- [x] mypy: no issues in modified files
