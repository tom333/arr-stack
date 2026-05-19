---
phase: 10-categories-6-app-propagation
plan: 10-G-jellyfin-wiring
subsystem: arrconf
tags:
  - python
  - reconciler-wiring
  - jellyfin
  - chart-pin-cobump
dependency_graph:
  requires:
    - 10-A-generators-categories  # generate_jellyfin_libraries
    - 10-B-merge-with-manual       # merge_with_manual
  provides:
    - REQ-categories-jellyfin-paths (wiring side complete)
  affects:
    - tools/arrconf/arrconf/__main__.py
    - charts/arr-stack/values.yaml
tech_stack:
  added: []
  patterns:
    - pre-merge in apply + diff (Pitfall 5 compliance)
    - D-02 per-resource toggle (manual non-empty wins)
    - D-05 chart-pin co-bump in same commit
key_files:
  created:
    - tools/arrconf/tests/test_jellyfin_categories.py
  modified:
    - tools/arrconf/arrconf/__main__.py
    - charts/arr-stack/values.yaml
decisions:
  - "generate_jellyfin_libraries called in both apply and diff branches (Pitfall 5: apply/diff parity)"
  - "Chart-pin co-bump 0.6.3→0.6.4 in same commit as reconciler code (D-05 pattern)"
metrics:
  duration: "~18 min"
  completed_date: "2026-05-19"
---

# Phase 10 Plan G: Jellyfin Wiring Summary

**One-liner:** Jellyfin pre-merge wired in `__main__.py` — `generate_jellyfin_libraries` called in apply + diff branches; 2 super-libraries (`Séries` / `Films`) with 5 paths each auto-derived from Categories; 6 tests added; values.yaml tag bumped 0.6.3 → 0.6.4.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 10-G-01 | Pre-merge Jellyfin libraries in __main__.py (apply + diff) + 6 wiring tests | 23cac56 | Done |
| 10-G-02 | Chart-pin co-bump: values.yaml arrconf.image.tag 0.6.3 → 0.6.4 | 23cac56 | Done (same commit per D-05) |

## What Was Built

### `__main__.py` — Jellyfin pre-merge wiring

Added `generate_jellyfin_libraries` to the import block and inserted pre-merge blocks in two places:

1. **apply branch** (lines ~440-446): After `jellyfin_instance = root.jellyfin["main"]`, before client construction:
   ```python
   jellyfin_generated = generate_jellyfin_libraries(root)
   jellyfin_instance.libraries.items = merge_with_manual(
       jellyfin_instance.libraries.items,
       jellyfin_generated,
       app="jellyfin",
       resource="libraries",
   )
   ```

2. **diff branch** (lines ~739-745): Identical pre-merge block (Pitfall 5 — apply/diff parity).

The dump branch does not set `jellyfin_instance.libraries.items` (dump is read-only; it captures cluster state, not YAML desired state).

### `tests/test_jellyfin_categories.py` — 6 tests

| Test | What it verifies |
|------|-----------------|
| `test_jellyfin_libraries_wiring_empty_manual` | 5 series + 5 movies cats → 2 libs with 5 paths each, correct collection_type |
| `test_jellyfin_libraries_path_content` | Correct path-to-library routing, no cross-contamination |
| `test_jellyfin_manual_override_wins` | D-02: non-empty manual list blocks generated list entirely |
| `test_jellyfin_no_categories_returns_two_empty_libraries` | Generator always returns 2 libs (empty paths) when cfg.categories is empty |
| `test_jellyfin_only_series_no_movies` | Films lib has empty paths when no movies categories |
| `test_jellyfin_libraries_order` | Output order is [Séries, Films] (deterministic) |

### `charts/arr-stack/values.yaml` — tag bump

`arrconf.image.tag`: `"0.6.3"` → `"0.6.4"` (renovate annotation preserved).

## Verification

```
cd tools/arrconf && uv run pytest tests/test_jellyfin_categories.py tests/test_reconcilers_jellyfin.py tests/test_phase9_no_regression.py -x -v
```

Result: **23 passed** (6 new + 11 Jellyfin existing + 2 Phase 9 no-regression).

```
uv run ruff check arrconf/__main__.py tests/test_jellyfin_categories.py
uv run ruff format --check arrconf/__main__.py tests/test_jellyfin_categories.py
uv run mypy arrconf/__main__.py tests/test_jellyfin_categories.py
```

All clean.

## Deviations from Plan

None — plan executed exactly as written.

**Pre-existing test ordering issues (out of scope, not caused by this plan):**
Two tests fail when the full suite runs in the default pytest collection order due to structlog processor state leaking between tests:
- `tests/test_merge_with_manual.py::test_log_event_manual_wins` — passes in isolation, fails after tests that reconfigure structlog
- `tests/test_reconcilers_jellyfin.py::test_reconcile_jellyfin_step_order_invariant` — same root cause

Both failures confirmed pre-existing by running the full suite with `__main__.py` stashed back to pre-plan state. Logged to deferred-items scope (structlog test isolation gap).

## Next Plan

**Plan 10-H** — Prowlarr FP fix #2 (final Wave 2 plan).

## Self-Check

Files created/modified:
- `tools/arrconf/arrconf/__main__.py` — modified
- `tools/arrconf/tests/test_jellyfin_categories.py` — created
- `charts/arr-stack/values.yaml` — modified

Commit `23cac56` covers all three files (verified via `git show HEAD --stat`).
