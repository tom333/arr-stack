---
phase: 10-categories-6-app-propagation
plan: 10-H-prowlarr-fp
subsystem: arrconf/reconcilers
tags:
  - python
  - fp-fix
  - prowlarr
  - chart-pin-cobump
dependency_graph:
  requires:
    - 10-C-qbit-wiring-fp  # established B2 allowlist pattern
  provides:
    - PROWLARR_APP_MANAGED_FIELDS frozenset (reconcilers/prowlarr.py)
    - FP #2 regression test (tests/test_idempotence_fp.py)
    - arrconf image.tag 0.6.5 (charts/arr-stack/values.yaml)
  affects:
    - reconcile_prowlarr callsite (filter before model_validate)
tech_stack:
  added: []
  patterns:
    - "B2 allowlist: frozenset filter on cluster GET dict before pydantic model_validate"
key_files:
  created: []
  modified:
    - tools/arrconf/arrconf/reconcilers/prowlarr.py
    - tools/arrconf/tests/test_idempotence_fp.py
    - charts/arr-stack/values.yaml
decisions:
  - "Pass id through filter alongside PROWLARR_APP_MANAGED_FIELDS: id is exclude=True (not a diff field) but _execute needs p.current.id for PUT routing. Kept id out of PROWLARR_APP_MANAGED_FIELDS (plan specifies 7 managed write fields) and used _app_keep = PROWLARR_APP_MANAGED_FIELDS | {'id'} at the callsite."
metrics:
  duration: "~15 min"
  completed: "2026-05-19T20:32:11Z"
  tasks: 2
  files_modified: 3
---

# Phase 10 Plan 10-H: Prowlarr FP Fix #2 + chart-pin 0.6.5 Summary

**One-liner:** Prowlarr Application `extra="allow"` FP fixed via `PROWLARR_APP_MANAGED_FIELDS` B2 allowlist filter before `model_validate`; arrconf tag bumped 0.6.4 → 0.6.5.

## What Was Built

### Task 10-H-01: PROWLARR_APP_MANAGED_FIELDS allowlist + FP regression tests

Added `PROWLARR_APP_MANAGED_FIELDS: frozenset[str]` to `tools/arrconf/arrconf/reconcilers/prowlarr.py` with 7 managed top-level fields: `name`, `enable`, `implementation`, `configContract`, `syncLevel`, `fields`, `tags`.

Modified the `reconcile_prowlarr` callsite to filter cluster GET dicts before `Application.model_validate`:

```python
_app_keep = PROWLARR_APP_MANAGED_FIELDS | {"id"}
current_apps = [
    Application.model_validate({k: v for k, v in x.items() if k in _app_keep})
    for x in raw_current
]
```

The `id` field is passed through via `_app_keep` (not in `PROWLARR_APP_MANAGED_FIELDS`) because it is `exclude=True` on the model (not a diff key) but `_execute` needs `p.current.id` for PUT routing.

Appended 3 regression tests to `tools/arrconf/tests/test_idempotence_fp.py`:
- `test_prowlarr_app_managed_fields_constant` — constant shape assertion
- `test_prowlarr_app_fp_fix_no_op_on_extras` — cluster GET with `presets`, `message`, `implementationName`, `infoLink`, `id` extras → NO_OP (FP eliminated)
- `test_prowlarr_app_real_change_still_detected` — managed field drift (`syncLevel: fullSync → disabled`) still fires UPDATE (sanity check)

**A1 assumption verified inline:** `grep model_config tools/arrconf/arrconf/resources/prowlarr/application.py` → `model_config = ConfigDict(extra="allow")` at line 36. FP root cause confirmed at top-level Application (not inside FieldKV sub-objects).

### Task 10-H-02: Chart-pin co-bump 0.6.4 → 0.6.5

`charts/arr-stack/values.yaml` arrconf `image.tag` bumped from `"0.6.4"` to `"0.6.5"`. Renovate annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` preserved. Committed atomically with Task 10-H-01 per D-05.

## Commit

| Commit | Files | Description |
|--------|-------|-------------|
| `5028de8` | prowlarr.py, test_idempotence_fp.py, values.yaml | FP fix #2 + chart-pin 0.6.5 (atomic per D-05) |

## Test Results

All 7 tests in `tests/test_idempotence_fp.py` pass:
- FP #1 qBit (Plan 10-C): `test_qbit_category_managed_fields_constant`, `test_qbit_category_fp_fix_no_op_on_extras`
- FP #3 Seerr (Plan 10-F): `test_seerr_user_managed_fields_constant`, `test_seerr_user_fp_fix_no_op_on_extras`
- FP #2 Prowlarr (this plan): `test_prowlarr_app_managed_fields_constant`, `test_prowlarr_app_fp_fix_no_op_on_extras`, `test_prowlarr_app_real_change_still_detected`

All 18 existing Prowlarr tests in `tests/test_reconcilers_prowlarr.py` pass.

Full suite (excluding pre-existing isolation failure in `test_merge_with_manual`): 370 tests pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] id passthrough needed alongside PROWLARR_APP_MANAGED_FIELDS**

- **Found during:** Task 10-H-01 GREEN phase (test_update_application_uses_forceSave_and_omits_apiKey failed)
- **Issue:** Filtering cluster dict strictly to `PROWLARR_APP_MANAGED_FIELDS` dropped the `id` key. The `id` field is `exclude=True` on the `Application` model (not a diff key, so correctly absent from `PROWLARR_APP_MANAGED_FIELDS`) but `_execute` requires `p.current.id is not None` for PUT routing.
- **Fix:** Used `_app_keep = PROWLARR_APP_MANAGED_FIELDS | {"id"}` at the callsite, keeping `id` separate from the 7-field constant (constant shape matches plan spec exactly).
- **Files modified:** `tools/arrconf/arrconf/reconcilers/prowlarr.py`
- **Commit:** `5028de8`

### Pre-existing Issue (Out of Scope)

`test_merge_with_manual::test_log_event_manual_wins` fails with structlog caplog isolation issue when running the full suite in deterministic order. Confirmed pre-existing: fails without my changes in the same test order. This is tracked as a pre-existing test isolation bug; it passes in isolation. Not caused by Plan 10-H changes.

## Wave 2 Closure Note

All 5 propagation reconcilers wired across Plans 10-C through 10-H:
- 10-C: qBittorrent categories (FP fix #1 + wiring)
- 10-D: Sonarr categories wiring
- 10-E: Radarr categories wiring
- 10-F: Seerr user management (FP fix #3)
- 10-G: Jellyfin host config wiring
- 10-H: Prowlarr FP fix #2 (this plan)

All 3 idempotence FPs now have regression tests in `tests/test_idempotence_fp.py`. Wave 3 (10-I docs + 10-J sweep) opens.

## Known Stubs

None — this plan is a pure bug fix with no new user-facing data flows.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

- prowlarr.py: FOUND
- test_idempotence_fp.py: FOUND
- values.yaml: FOUND
- SUMMARY.md: FOUND
- commit 5028de8: FOUND
