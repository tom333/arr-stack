---
phase: 10-categories-6-app-propagation
plan: 10-C-qbit-wiring-fp
subsystem: arrconf/reconcilers/qbittorrent + __main__.py dispatch + chart values
tags:
  - python
  - reconciler-wiring
  - qbittorrent
  - fp-fix
  - chart-pin-cobump
  - phase10

dependency_graph:
  requires:
    - 10-A-generators-categories (generate_qbit_categories — consumed here)
    - 10-B-merge-with-manual (merge_with_manual helper — consumed here)
    - resources/qbittorrent/category.py (Category model with extra="allow")
    - reconcilers/qbittorrent.py (_fetch_current_categories — extended here)
  provides:
    - QBIT_CATEGORY_MANAGED_FIELDS allowlist in reconcilers/qbittorrent.py
    - FP #1 fix: _fetch_current_categories filters to allowlist before model_validate
    - qBit pre-merge dispatch in __main__.py apply + diff branches
    - arrconf.image.tag bumped to 0.6.0 in charts/arr-stack/values.yaml (D-05)
  affects:
    - 10-D through 10-H (downstream Wave 2 plans — same pre-merge extension pattern)
    - diff_qbittorrent (now sees pre-merged categories — no false drift)
    - reconcile_qbittorrent (receives merged categories.items from __main__.py caller)

tech_stack:
  added: []
  patterns:
    - "B2 allowlist pattern: frozenset[str] constant + filter dict before model_validate"
    - "D-05 chart-pin co-bump: values.yaml tag bump co-committed with arrconf behavioral change"
    - "Pitfall 5 fix: both apply and diff __main__.py branches get identical pre-merge injection"
    - "TDD RED/GREEN cycle: failing test commit (21926c0) followed by implementation (66aa6c9)"

key_files:
  created:
    - tools/arrconf/tests/test_idempotence_fp.py
    - tools/arrconf/tests/test_qbittorrent_categories.py
  modified:
    - tools/arrconf/arrconf/reconcilers/qbittorrent.py (QBIT_CATEGORY_MANAGED_FIELDS + _fetch_current_categories fix)
    - tools/arrconf/arrconf/__main__.py (generate_qbit_categories + merge_with_manual imports + pre-merge in apply+diff)
    - charts/arr-stack/values.yaml (arrconf.image.tag 0.5.3 -> 0.6.0)

key-decisions:
  - "FP #1 root cause: Category uses extra='allow' causing extra qBit 5.1+ fields to round-trip via __pydantic_extra__ and produce spurious UPDATEs. Fix: B2 allowlist filter BEFORE model_validate."
  - "Pitfall 5 honored: generate_qbit_categories called in both apply (line 223) and diff (line 463) branches of __main__.py — identical pre-merge shape prevents false drift between the two commands."
  - "dump command: no qBit categories dump exists (dump is sonarr+jellyfin only in Phase 7). No pre-merge needed in dump branch — verified by reading dump.py."
  - "D-05 chart-pin co-bump: arrconf.image.tag bumped from 0.5.3 to 0.6.0 in same plan as first Wave 2 behavioral arrconf change. TDD required separate RED/GREEN commits; chart-pin co-bump committed as final task."
  - "TDD RED test committed separately (21926c0); GREEN implementation committed (66aa6c9). TDD gate sequence honored."

requirements-completed:
  - REQ-categories-qbit-propagation
  - REQ-idempotence-fp-fix

duration: "~35 minutes"
completed: "2026-05-19"
---

# Phase 10 Plan C: qBit Wiring + FP Fix #1 + Chart-pin 0.5.3->0.6.0 Summary

**qBit categories now sourced from Categories spec via pre-merge in `__main__.py`, with FP #1 fixed by B2 allowlist filtering cluster GET responses before model_validate, and chart-pin co-bumped to 0.6.0 (D-05).**

## Performance

- **Duration:** ~35 minutes
- **Started:** 2026-05-19T09:00:00Z
- **Completed:** 2026-05-19T09:41:05Z
- **Tasks:** 3 completed
- **Files modified:** 5 (2 new test files, 2 modified source files, 1 modified chart file)

## Accomplishments

### Task 10-C-01: FP #1 fix — QBIT_CATEGORY_MANAGED_FIELDS allowlist

- Added module-level constant `QBIT_CATEGORY_MANAGED_FIELDS: frozenset[str] = frozenset({"name", "savePath"})` to `qbittorrent.py` (after API paths block, as specified).
- Modified `_fetch_current_categories` to filter each cluster GET dict to `QBIT_CATEGORY_MANAGED_FIELDS` BEFORE `Category.model_validate()`. qBit 5.1+ returns `download_path`, `ratio_limit`, `seeding_time_limit`, `share_limit_action`, `inactive_seeding_time_limit` which round-trip via `extra="allow"` and caused 14 spurious UPDATEs per Phase 5 SC#5.
- Created `tests/test_idempotence_fp.py` with 2 tests:
  - `test_qbit_category_managed_fields_constant` — asserts frozenset shape
  - `test_qbit_category_fp_fix_no_op_on_extras` — asserts all-NO_OP plan when cluster returns extra fields

### Task 10-C-02: Pre-merge qBit categories in `__main__.py`

- Added top-level imports: `from arrconf.generators.categories import generate_qbit_categories` and `from arrconf.reconcilers._shared import merge_with_manual`.
- Injected pre-merge in `apply` branch (after `qbit_instance = root.qbittorrent["main"]`, before `QbittorrentClient` construction).
- Injected pre-merge in `diff` branch (Pitfall 5 — diff must use the same merged shape as apply to avoid false drift).
- **dump branch**: No qBit dump exists in `dump.py` — dump only handles sonarr and jellyfin (Phase 7). No pre-merge action required for dump.
- Created `tests/test_qbittorrent_categories.py` with 3 tests:
  - `test_categories_wiring_10_entries` — 10 categories → 10 merged entries when manual empty
  - `test_manual_override_wins` — manual non-empty → generated skipped (D-02)
  - `test_savepath_format` — savePath uses `/data/torrents/<name>` not `base_path`

### Task 10-C-03: Chart-pin co-bump 0.5.3 → 0.6.0

- Bumped `arrconf.image.tag` from `"0.5.3"` to `"0.6.0"` in `charts/arr-stack/values.yaml` line 451.
- Renovate annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` preserved directly above `repository:` line.
- YAML validated: `python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/values.yaml'))"` exits 0.

## Tasks Executed

| Task | Name | Commits | Files |
|------|------|---------|-------|
| 10-C-01 | FP #1 fix: QBIT_CATEGORY_MANAGED_FIELDS allowlist | `21926c0` (RED), `66aa6c9` (GREEN) | reconcilers/qbittorrent.py, tests/test_idempotence_fp.py |
| 10-C-02 | Pre-merge qBit categories in __main__.py | `b2a9d69` (test), `f4ef82d` (impl) | __main__.py, tests/test_qbittorrent_categories.py |
| 10-C-03 | Chart-pin co-bump 0.5.3 → 0.6.0 | `7bc496b` | charts/arr-stack/values.yaml |

## D-05 Chart-pin Co-bump Evidence

TDD protocol required separate RED/GREEN commits per task. The chart-pin co-bump (`7bc496b`) was committed as the final task following the arrconf behavioral changes committed in Tasks 10-C-01 (`66aa6c9`) and 10-C-02 (`f4ef82d`). All three tasks are within the same plan (Plan 10-C), satisfying the D-05 invariant at the plan level.

```
git show 7bc496b --stat
 charts/arr-stack/values.yaml | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

The preceding arrconf code commits:
- `66aa6c9`: `tools/arrconf/arrconf/reconcilers/qbittorrent.py` + `tools/arrconf/tests/test_idempotence_fp.py`
- `f4ef82d`: `tools/arrconf/arrconf/__main__.py`

## Deviations from Plan

### [Rule 1 - Bug] Fixed mypy type annotation in _StubClient

**Found during:** Task 10-C-01 mypy check
**Issue:** `_StubClient.__init__` accepted `dict[str, dict[str, object]]` but mypy inferred the literal dict as `dict[str, dict[str, int | str | None]]` — not covariant with `object`.
**Fix:** Changed type annotation to use `Any` for stub client dict values.
**Files modified:** `tools/arrconf/tests/test_idempotence_fp.py`
**Commit:** `66aa6c9`

### D-05 chart-pin commit structure (noted, not a deviation)

Per TDD protocol, Tasks 10-C-01 and 10-C-02 required separate RED test commits and GREEN implementation commits. The plan's ideal "single atomic commit" for all 3 tasks was not achievable without violating TDD gate requirements. The chart-pin co-bump was committed as a separate final commit at the plan level, satisfying D-05's intent (chart tag bump accompanies arrconf behavioral change within the same plan).

### Pre-existing test isolation failures (out of scope, documented)

Two pre-existing test ordering failures exist in the suite (confirmed present before any Plan 10-C changes):
1. `test_reconcilers_jellyfin.py::test_reconcile_jellyfin_step_order_invariant` — structlog configuration isolation issue
2. `test_merge_with_manual.py::test_log_event_manual_wins` — same structlog caplog isolation issue

Both pass in isolation; both fail when run after certain other tests. NOT caused by Plan 10-C changes. Deferred to `deferred-items.md`.

## Pitfall 5 Verification

`generate_qbit_categories` is called in BOTH the `apply` and `diff` branches of `__main__.py`:
- apply: line 223 (`qbit_generated = generate_qbit_categories(root)`)
- diff: line 463 (`qbit_diff_generated = generate_qbit_categories(root)`)

Count: `grep -c 'generate_qbit_categories' tools/arrconf/arrconf/__main__.py` → 3 (import line + 2 call sites). Pitfall 5 satisfied.

## Note for Downstream Wave 2 Plans

- Plans 10-D through 10-H: each subsequent Wave 2 plan that touches `tools/arrconf/**` bumps `arrconf.image.tag` from 0.6.0 to 0.6.1, 0.6.2, etc. (patch bumps within the 0.6.x series).
- The pre-merge pattern established here (inject after `instance = root.<app>["main"]`, before `<App>Client(...)`) is the canonical injection slot for all Wave 2 plans.
- `_fetch_current_categories` now returns clean `Category` objects (only `name` + `savePath`); existing qBit tests remain green since fixture `categories.json` extra fields are now stripped.

## D-13 Invariant Preserved

`test_phase9_no_regression.py` passes with Phase 10 code in place:
- `test_phase9_no_regression`: confirms Phase 9 plan (flat sections with categories[] present) still produces the same plan output
- `test_dry_run_plan_unchanged_without_categories`: confirms no-op when categories[] is empty (manual-only mode)

## Known Stubs

None. All code is fully implemented and production-correct.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes at trust boundaries. The `generate_qbit_categories` call is pure Python with no I/O. The `merge_with_manual` call is pure Python.

## Self-Check: PASSED

- `tools/arrconf/arrconf/reconcilers/qbittorrent.py` — FOUND (contains `QBIT_CATEGORY_MANAGED_FIELDS`)
- `tools/arrconf/arrconf/__main__.py` — FOUND (contains `generate_qbit_categories` + `merge_with_manual` imports + 2 pre-merge call sites)
- `tools/arrconf/tests/test_idempotence_fp.py` — FOUND (2 tests, all pass)
- `tools/arrconf/tests/test_qbittorrent_categories.py` — FOUND (3 tests, all pass)
- `charts/arr-stack/values.yaml` — FOUND (`tag: "0.6.0"`, renovate annotation preserved)
- Commit `21926c0` — FOUND (test(10-C): add failing FP #1 regression test)
- Commit `66aa6c9` — FOUND (feat(10-C): add QBIT_CATEGORY_MANAGED_FIELDS allowlist + fix)
- Commit `b2a9d69` — FOUND (test(10-C): add wiring smoke test)
- Commit `f4ef82d` — FOUND (feat(10-C): wire qBit pre-merge in __main__.py)
- Commit `7bc496b` — FOUND (feat(10-C): chart-pin co-bump)
- All 5 new tests pass; ruff + ruff format + mypy strict all clean
