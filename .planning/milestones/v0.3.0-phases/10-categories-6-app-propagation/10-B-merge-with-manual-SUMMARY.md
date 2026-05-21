---
phase: 10-categories-6-app-propagation
plan: 10-B-merge-with-manual
subsystem: arrconf/reconcilers/_shared
tags:
  - python
  - shared-helper
  - merge
  - override-toggle
  - phase10
dependency_graph:
  requires:
    - 10-A-generators-categories (generators module — dead until Wave 2 wires it)
    - reconcilers/_shared.py (host file — pre-existing)
    - structlog (pre-existing import in _shared.py)
  provides:
    - arrconf.reconcilers._shared.merge_with_manual — public D-02 per-resource toggle
  affects:
    - 10-C (qBit reconciler wiring — consumes merge_with_manual)
    - 10-D (Sonarr reconciler wiring — consumes merge_with_manual)
    - 10-E (Radarr reconciler wiring — consumes merge_with_manual)
    - 10-F (Seerr animeTags routing — consumes merge_with_manual)
    - 10-G (Jellyfin PathInfos wiring — consumes merge_with_manual)
tech_stack:
  added: []
  patterns:
    - "keyword-only parameters (*, app, resource) enforcing explicit call sites"
    - "structlog merge_decision event with source/n/generated_skipped fields"
    - "D-02 per-resource boolean toggle: manual non-empty wins, else generated"
    - "pytest caplog + structlog.configure() fixture for structured log capture"
key_files:
  created:
    - tools/arrconf/tests/test_merge_with_manual.py
  modified:
    - tools/arrconf/arrconf/reconcilers/_shared.py
decisions:
  - "D-02 honored: merge is per-resource, binary (no item-level merge), transition layer for v0.4.0+ deprecation"
  - "structlog KeyValueRenderer quotes strings in output: assertions use source='manual' not source=manual"
  - "Chart-pin co-bump deferred to Plan 10-C per CONTEXT.md D-05 exception (code is dead until Wave 2 wires it)"
  - "Task 10-B-03 (ADR-6 snapshot) deferred — requires cluster API keys not available to executor"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-19"
  tasks_completed: 2
  tasks_deferred: 1
  files_created: 1
  files_modified: 1
  tests_added: 6
---

# Phase 10 Plan B: merge_with_manual() Summary

**One-liner:** D-02 per-resource override-toggle helper in `reconcilers/_shared.py` — manual non-empty wins; manual empty uses Categories-derived list; 6 unit tests covering all contract branches.

## Tasks Executed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 10-B-01 | Add merge_with_manual() helper to _shared.py | `b7cefb0` | reconcilers/_shared.py (+62 lines) |
| 10-B-02 | Unit tests for merge_with_manual() — 3 D-02 cases | `bf48e98` | tests/test_merge_with_manual.py (created, 85 lines, 6 tests) |
| 10-B-03 | ADR-6 baseline snapshot before Wave 2 | DEFERRED — operator action | snapshots/before-phase-10-YYYY-MM-DD/ |

## What Was Built

### `merge_with_manual()` in `tools/arrconf/arrconf/reconcilers/_shared.py` (lines 148–207)

Public function implementing the D-02 per-resource override toggle:

```python
def merge_with_manual(
    manual_items: list[Any],
    generated_items: list[Any],
    *,
    app: str,
    resource: str,
) -> list[Any]:
```

**Contract:**
- `manual_items` non-empty → returns `manual_items` unchanged; logs `merge_decision` with `source='manual'`, `n=len(manual_items)`, `generated_skipped=len(generated_items)`
- `manual_items` empty → returns `generated_items`; logs `merge_decision` with `source='categories'`, `n=len(generated_items)`
- Both empty → returns `[]`; logs `source='categories'`, `n=0`

Keyword-only `app` and `resource` parameters force explicit naming at all 6 Wave 2 call sites — prevents positional confusion between `manual_items` and `generated_items`.

No I/O, no imports added to `_shared.py` — `structlog` and `Any` were already present.

### `tools/arrconf/tests/test_merge_with_manual.py` (85 lines, 6 tests)

| Test | Behavioural case |
|------|-----------------|
| `test_manual_non_empty_wins` | D-02 Behaviour A: manual list returned unchanged |
| `test_manual_empty_uses_generated` | D-02 Behaviour B: generated list returned |
| `test_both_empty_returns_empty` | Edge case: both empty → `[]` |
| `test_log_event_manual_wins` | `merge_decision` has `source='manual'`, `n=2`, `generated_skipped=3` |
| `test_log_event_generated_wins` | `merge_decision` has `source='categories'`, `n=3` |
| `test_app_and_resource_are_keyword_only` | Positional call raises `TypeError` |

Log event capture uses `pytest.caplog` with a `structlog.configure()` autouse fixture routing structlog output through the stdlib logger. The `KeyValueRenderer` wraps string values in quotes (`source='manual'`), so assertions use quoted form.

## Deviations from Plan

### [Rule 1 - Bug] Fixed structlog string quoting in log event assertions

**Found during:** Task 10-B-02 test run
**Issue:** The plan's test template used `assert "source=manual" in msg`, but structlog's `KeyValueRenderer` wraps string values in single quotes, producing `source='manual'`. Three of the six tests would have failed with the plan's literal assertion strings.
**Fix:** Updated assertions to `assert "source='manual'" in msg` and `assert "source='categories'" in msg`. Added inline comments explaining the quoting behavior.
**Files modified:** `tools/arrconf/tests/test_merge_with_manual.py`
**Commit:** `bf48e98`

### [Rule 1 - Bug] Fixed ruff E501 line-too-long in assert messages

**Found during:** Task 10-B-02 ruff check
**Issue:** The `assert matching, f"..."` diagnostic messages exceeded the 100-char line limit (112 chars each).
**Fix:** Extracted `record_msgs = [r.getMessage() for r in caplog.records]` before the assertion line.
**Files modified:** `tools/arrconf/tests/test_merge_with_manual.py`
**Commit:** `bf48e98`

### D-05 Chart-pin co-bump exception (documented, not a deviation)

Per CONTEXT.md D-05 and the plan's output spec: this plan's commits do NOT touch `values.yaml`. `merge_with_manual()` is dead code until Wave 2 wires it. The first chart-pin bump (`0.5.3 → 0.6.0`) will be co-committed with Plan 10-C (qBit reconciler wiring).

## Deferred: Task 10-B-03 (ADR-6 snapshot)

**Status:** DEFERRED — operator action required

Task 10-B-03 is a `type="checkpoint:human-action"` task. The autonomous executor cannot run it because it requires:
- Cluster API keys (`SONARR_API_KEY`, `RADARR_API_KEY`, `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY`)
- Reachable cluster (port-forward or in-cluster)
- `tools/snapshot/snapshot.sh` to write files to `snapshots/before-phase-10-YYYY-MM-DD/`

**Required operator action before Wave 2 opens:**

```bash
tools/snapshot/snapshot.sh --output snapshots/before-phase-10-$(date +%F)/

git add snapshots/before-phase-10-*/
git commit -m "snapshot(pre-phase-10): baseline before Categories wiring"
```

**Why this matters (ADR-6):** Wave 2 plans (10-C..10-H) all wire Categories-derived resources into cluster-touching reconcilers. The snapshot is the project's safety net for detecting unintended side-effects from those first live writes.

**Verification command (after operator runs it):**
```bash
ls snapshots/before-phase-10-*/  # lists at least 1 directory
git log --oneline -10 | grep -F "snapshot(pre-phase-10): baseline before Categories wiring"
```

## Wave 2 Consumers

All 5 Wave 2 reconciler-wiring plans import and call `merge_with_manual`:

```python
from arrconf.reconcilers._shared import merge_with_manual
```

| Plan | Where called | Resources merged |
|------|-------------|-----------------|
| 10-C | `__main__.py` before `reconcile_qbittorrent` | `qbittorrent.categories.items` |
| 10-D | `__main__.py` before `reconcile_sonarr` | tags, root_folders, download_clients, RPMs |
| 10-E | `__main__.py` before `reconcile_radarr` | tags, root_folders, download_clients, RPMs |
| 10-F | `__main__.py` before `reconcile_seerr` | `seerr.sonarr_service.animeTags` |
| 10-G | `__main__.py` before `reconcile_jellyfin` | `jellyfin.libraries.items` |

None of Wave 2 plans need to modify `merge_with_manual` — the function is complete and stable.

## Note on chart-pin co-bump

This plan ships PURE PYTHON — no reconciler behavior changes, no cluster writes. The first chart-pin co-bump (`arrconf.image.tag: 0.5.3 → 0.6.0`) is bundled with Plan 10-C, the first Wave 2 plan to ship arrconf behavioral changes (per D-05 and the plan output spec).

## Known Stubs

None. `merge_with_manual()` is fully implemented and returns production-correct behavior.

## Threat Flags

None. The helper is pure Python with no network endpoints, no auth paths, no file access, and no schema changes at trust boundaries.

## Self-Check: PASSED

- `tools/arrconf/arrconf/reconcilers/_shared.py` — FOUND (contains `def merge_with_manual`)
- `tools/arrconf/tests/test_merge_with_manual.py` — FOUND (85 lines, 6 tests)
- Commit `b7cefb0` — FOUND (feat(10-B): add merge_with_manual() helper...)
- Commit `bf48e98` — FOUND (test(10-B): add 6 unit tests...)
- All 6 tests pass; ruff + ruff format + mypy strict all clean
- Wave 1 combined run (test_merge_with_manual + test_generators_categories): 30 passed
