---
phase: 10-categories-6-app-propagation
plan: 10-E-radarr-wiring
subsystem: reconciler-wiring
tags: [python, radarr, categories, merge_with_manual, chart-pin, movies]

# Dependency graph
requires:
  - phase: 10-categories-6-app-propagation
    plan: 10-A-generators-categories
    provides: generate_radarr_resources() producing RadarrDerived with kind=movies filter
  - phase: 10-categories-6-app-propagation
    plan: 10-B-merge-with-manual
    provides: merge_with_manual() per-resource toggle mechanism
  - phase: 10-categories-6-app-propagation
    plan: 10-D-sonarr-wiring
    provides: Sonarr wiring pattern (byte-equivalent mirror)
provides:
  - Radarr apply branch pre-merges 4 resources from categories before reconcile_radarr call
  - Radarr diff branch pre-merges same 4 resources (Pitfall 5 fix — prevents false drift)
  - 6 wiring tests proving 5×4 mapping + per-resource override + no-movies edge case
  - movieCategory FieldKV (not tvCategory) confirmed in tests
  - arrconf.image.tag bumped to 0.6.2 in values.yaml
affects:
  - 10-F-seerr-wiring (next Wave 2 plan)
  - 10-G-jellyfin-wiring (downstream)
  - Charts deployment (0.6.2 tag triggers new Renovate bump in my-kluster)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Radarr wiring mirrors Sonarr wiring exactly: same 4 resources, same per-resource toggle, different kind filter (movies vs series)"
    - "D-05 co-bump: __main__.py code + values.yaml tag in single atomic commit"
    - "Pitfall 5: diff branch must have identical pre-merge as apply to prevent false drift"

key-files:
  created:
    - tools/arrconf/tests/test_radarr_categories.py
  modified:
    - tools/arrconf/arrconf/__main__.py
    - charts/arr-stack/values.yaml

key-decisions:
  - "movieCategory FieldKV (not tvCategory) is the Radarr-side field name for download client category routing"
  - "generate_radarr_resources import added alongside generate_sonarr_resources in same import block"
  - "Both apply AND diff branches wired (Pitfall 5) — diff must see same merged shape to avoid false drift report"

patterns-established:
  - "Pattern: Per-app pre-merge block placed AFTER instance extraction, BEFORE client construction"
  - "Pattern: radarr_derived / radarr_diff_derived variable naming mirrors sonarr_derived / sonarr_diff_derived"

requirements-completed:
  - REQ-categories-radarr-propagation

# Metrics
duration: 4min
completed: 2026-05-19
---

# Phase 10 Plan E: Radarr 4-Resource Wiring Summary

**Radarr pre-merge wired in apply + diff branches of __main__.py: tags/root_folders/download_clients/remote_path_mappings derive from kind=movies categories; chart-pin bumped 0.6.1→0.6.2 atomically**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-19T09:50:52Z
- **Completed:** 2026-05-19T09:54:51Z
- **Tasks:** 2 (bundled into 1 atomic commit per D-05)
- **Files modified:** 3

## Accomplishments

- `generate_radarr_resources` import added to `__main__.py` alongside existing generators
- Pre-merge block injected in `apply` branch: 4 `merge_with_manual` calls for tags, root_folders, download_clients, remote_path_mappings before `reconcile_radarr`
- Pre-merge block injected in `diff` branch (Pitfall 5): identical 4 calls to prevent false drift between `apply` and `diff` commands
- 6 wiring tests in `test_radarr_categories.py` cover: tags (empty manual), root_folders (empty manual), movieCategory FieldKV assertion, RPM trailing slashes, per-resource tag override, no-movies edge case
- `arrconf.image.tag` bumped from `"0.6.1"` to `"0.6.2"` in `charts/arr-stack/values.yaml` with Renovate annotation preserved
- Phase 9 no-regression test unchanged and passing

## Task Commits

Both tasks bundled in one atomic commit per D-05:

1. **Task 10-E-01 + 10-E-02: Radarr 4-resource wiring + chart-pin 0.6.1→0.6.2** - `23c6b43` (feat)

## Files Created/Modified

- `tools/arrconf/arrconf/__main__.py` - Added `generate_radarr_resources` import; pre-merge block in apply branch (lines ~186-211) and diff branch (lines ~504-529)
- `tools/arrconf/tests/test_radarr_categories.py` - New: 6 wiring tests, 186 lines
- `charts/arr-stack/values.yaml` - arrconf.image.tag `"0.6.1"` → `"0.6.2"`

## Decisions Made

- movieCategory FieldKV confirmed as Radarr-side field (not tvCategory which is Sonarr-side). Test explicitly asserts absence of tvCategory to prevent field-name regressions.
- dump branch NOT wired (Radarr dump deferred per Phase 3 CONTEXT.md — only Sonarr+Jellyfin dump implemented). No change needed there.
- Single atomic commit bundles code + chart-pin per D-05 requirement.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing test isolation issue discovered: `tests/test_merge_with_manual.py::test_log_event_manual_wins` fails intermittently in the full suite due to structlog/pytest-caplog interaction (structlog JSON renderer bypasses stdlib logging in certain test ordering contexts). The test passes in isolation and when run as part of `test_merge_with_manual.py` only. This failure exists on `main` before this plan's changes (verified via `git stash` + full suite run). Logged to deferred-items; out-of-scope for this plan.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. Pre-merge is pure in-memory data transformation before the existing reconcile_radarr call.

## Next Phase Readiness

- Radarr wiring complete. Wave 2 continues with Plan 10-F (Seerr — animeTags routing + FP fix #3).
- No blockers. Radarr categories will propagate on next `arrconf apply` after image 0.6.2 deploys.

## Self-Check: PASSED

- `tools/arrconf/arrconf/__main__.py` exists and contains `generate_radarr_resources` (3 occurrences): confirmed
- `tools/arrconf/tests/test_radarr_categories.py` exists with 6 test functions: confirmed
- `charts/arr-stack/values.yaml` contains `tag: "0.6.2"` and no `"0.6.1"` for arrconf: confirmed
- Commit `23c6b43` exists and includes all 3 files: confirmed

---
*Phase: 10-categories-6-app-propagation*
*Plan: 10-E-radarr-wiring*
*Completed: 2026-05-19*
