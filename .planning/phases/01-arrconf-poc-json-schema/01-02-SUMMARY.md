---
phase: 01-arrconf-poc-json-schema
plan: 02
subsystem: infra
tags: [python, pydantic, httpx, respx, structlog, tdd, idempotence, threat-mitigation]

# Dependency graph
requires:
  - phase: 01-arrconf-poc-json-schema
    plan: 01
    provides: differ.Action enum + PlannedAction skeleton, SonarrClient, DownloadClient/Tag pydantic models, ScopeViolationError, conftest fixtures (downloadclient + tag empty + tag_with_arrconf_managed)
provides:
  - "arrconf.differ.diff_models() — D-21 read-only field exclusion (id, implementationName, infoLink, message, presets) on diff"
  - "arrconf.differ.reconcile() — 6-case classifier (ADD/UPDATE/DELETE/NO_OP/PRUNE_SKIP/PRUNE_PROTECTED) with managed-tag-gated DELETE (T-01-04 mitigation)"
  - "arrconf.reconcilers.sonarr._ensure_managed_tag() — idempotent get-or-create of arrconf-managed tag with dry-run sentinel id=-1"
  - "arrconf.reconcilers.sonarr._ensure_managed_tag_in_desired() — stamps managed tag id onto every desired DownloadClient before diff (D-02)"
  - "arrconf.reconcilers.sonarr.reconcile_sonarr() — 5-step orchestrator (tag → GET → stamp → diff → execute) with dry-run support"
  - "33 unit tests — 9 differ + 5 managed-tag + 7 reconciler + 12 scope-violation (parametrized 4×3)"
  - "T-01-04 (idempotence bypass via prune) — mitigated and tested with 3 differ + 1 reconciler test"
  - "T-01-05 (scope-guard bypass) — hardened with respx-asserted pre-network test on 4 frontière modules"
affects:
  - 01-03-PLAN.md (Wave 3 — wires reconcile_sonarr() into the typer apply/dump/diff CLI bodies and adds round-trip integration test)

# Tech tracking
tech-stack:
  added: []  # All deps were pinned in W1 — no new deps in W2
  patterns:
    - "TDD RED→GREEN cycle on each task: failing tests committed before the implementation that makes them pass"
    - "respx assert_all_called=False on tests that intentionally register guard routes to prove zero calls were made"
    - "respx url__regex pattern catches both /downloadclient and /downloadclient/{id} so an unintended PUT/DELETE surfaces as a route hit, not as an unhandled-route error"
    - "Frontière configarr modules tested as a parametrized matrix (4 modules × 3 assertions = 12 tests) so adding a new frontière module gets full coverage by appending one entry"
    - "Defensive default for managed_tag_id=None — the reconciler treats this as PRUNE_PROTECTED, not DELETE (T-01-04 belt-and-braces)"

key-files:
  created:
    - tools/arrconf/tests/test_differ.py
    - tools/arrconf/tests/test_reconcilers_sonarr.py
    - tools/arrconf/tests/test_managed_tag.py
    - tools/arrconf/tests/test_scope_violation.py
  modified:
    - tools/arrconf/arrconf/differ.py
    - tools/arrconf/arrconf/reconcilers/sonarr.py
    - tools/arrconf/arrconf/client_base.py  # Rule 1 — fix httpx.Timeout missing write/pool params

key-decisions:
  - "Use mutable set[str] for _READ_ONLY_FIELDS (not frozenset) — pydantic model_dump(exclude=...) types the param as IncEx which accepts set[str] natively; frozenset triggers a mypy strict error"
  - "respx assert_all_called=False on every reconciler test — the test pattern is to register routes that should NOT fire as call-count guards; respx default 'all routes were called' assertion is the wrong contract for that pattern"
  - "Cluster fixture stamped with tags=[1] for the round-trip NO_OP test — the reconciler adds the managed tag id to every desired DC before diffing, so the cluster fixture must already include it for diff_models() to return [] (otherwise the round-trip test would fire a spurious UPDATE on the tags field)"
  - "Defensive default — when managed_tag_id is None (e.g., dry-run sentinel never reached because of a bug), the reconciler treats as PRUNE_PROTECTED, never DELETE; locked in test_no_managed_tag_id_treats_as_protected"

# Metrics
duration: 30min
completed: 2026-05-07
---

# Phase 1 Plan 02: arrconf POC Wave 2 — Sonarr Reconciler Summary

**Sonarr download_clients reconciler with managed-tag-first ordering, 6-case Action classifier, and respx-hardened idempotence/scope-violation tests — 33 tests green at 99% coverage on the two scoped modules, mypy --strict + ruff clean.**

## Performance

- **Duration:** ~30 min
- **Tasks:** 3 (TDD on Tasks 1–2, plain on Task 3)
- **Files created:** 4 test modules
- **Files modified:** 3 source modules (differ.py, reconcilers/sonarr.py, client_base.py)
- **Commits:** 5 (3 TDD pairs + 1 hardening test)

## Accomplishments

- `arrconf.differ.diff_models()` and `arrconf.differ.reconcile()` are fully implemented with the 6-case Action classifier (ADD / UPDATE / DELETE / NO_OP / PRUNE_SKIP / PRUNE_PROTECTED) per D-04 / D-11 / D-20 / D-21. 100% line + branch coverage.
- `arrconf.reconcilers.sonarr.reconcile_sonarr()` orchestrates the 5-step Sonarr pipeline: ensure managed tag → GET cluster state → stamp managed tag onto desired → diff → execute (or log dry-run). 98% line + branch coverage; the 2 missed branches are conditional fall-through paths inside `_execute()` after the unreachable `Action.PRUNE_PROTECTED` early-return.
- `_ensure_managed_tag()` is idempotent: GET /tag matches by `label == "arrconf-managed"`. If found, returns it. If missing and `dry_run=False`, POST /tag with `{"label": "arrconf-managed"}`. If missing and `dry_run=True`, returns `Tag(id=-1, label="arrconf-managed")` — a sentinel that the rest of the pipeline tolerates without issuing real writes (Pitfall 3 + REQ-managed-tag).
- The managed tag is **always** stamped onto every desired DownloadClient before the diff runs (`_ensure_managed_tag_in_desired`), so any DC created via `arrconf apply` is automatically opt-into the prune-eligible cohort (D-02 / Pitfall 1: tag IDs not names).
- T-01-04 (idempotence bypass via prune) is mitigated by a **two-line defense**: (1) `prune: false` is the default in `DownloadClientsSection` (D-04, REQ-prune-opt-in); (2) even with `prune=True`, `reconcile()` returns `PRUNE_PROTECTED` (NOT `DELETE`) unless `managed_tag_id in cur.tags`. The defensive `managed_tag_id=None → PRUNE_PROTECTED` path is locked in `test_no_managed_tag_id_treats_as_protected`.
- T-01-05 (scope-guard bypass) is hardened by `test_scope_violation_raises_BEFORE_any_http_call` — uses respx with NO routes registered, then asserts `respx_mock.calls.call_count == 0` after the `ScopeViolationError` raises. If a future bug introduces httpx into any of the 4 frontière modules, the assertion fails loudly.
- 33 tests across 4 modules (9 differ + 5 managed-tag + 7 reconciler + 12 scope-violation = 33) all green via respx mocks. Zero live API calls. mypy --strict + ruff lint + ruff format all clean across the 23 source files + 4 test files.

## Task Commits

1. **Task 1 RED — failing tests for differ.reconcile()** — `3caab5e` (test)
2. **Task 1 GREEN — implement differ.reconcile() 6-case classifier** — `9dab8c5` (feat)
3. **Task 2 RED — failing tests for sonarr reconciler + managed tag** — `5b98992` (test)
4. **Task 2 GREEN — implement Sonarr reconciler with managed-tag-first ordering** — `86340d4` (feat)
5. **Task 3 — harden T-01-05 with respx-asserted scope-violation tests** — `10167e6` (test)

## Files Created/Modified

### Created

- `tools/arrconf/tests/test_differ.py` — 9 unit tests covering all 6 Action cases plus diff_models() read-only exclusion (D-21) and the T-01-04 defensive default.
- `tools/arrconf/tests/test_reconcilers_sonarr.py` — 7 tests: round-trip NO_OP, ADD with tag stamping, UPDATE diff, PRUNE_SKIP / PRUNE_PROTECTED / DELETE branches, dry-run.
- `tools/arrconf/tests/test_managed_tag.py` — 5 tests: tag creation when missing, reuse when present, dry-run sentinel, application onto download_clients, never-deleted invariant.
- `tools/arrconf/tests/test_scope_violation.py` — 3 parametrized tests over the 4 frontière modules (12 invocations) covering configarr.yml redirection message, pre-network raise (T-01-05 hardening with respx call-count assertion), and resource-name mention in the error message.

### Modified

- `tools/arrconf/arrconf/differ.py` — full implementation of `diff_models()` and `reconcile()` per RESEARCH.md Pattern 4. `_READ_ONLY_FIELDS = {"id", "implementationName", "infoLink", "message", "presets"}` per D-21.
- `tools/arrconf/arrconf/reconcilers/sonarr.py` — full implementation per RESEARCH.md Pattern 5: `_ensure_managed_tag`, `_ensure_managed_tag_in_desired`, `_execute`, `reconcile_sonarr`. Constants for paths and the dry-run sentinel id.
- `tools/arrconf/arrconf/client_base.py` — Rule 1 bug-fix: `httpx.Timeout(connect=5.0, read=30.0)` was missing the `write` and `pool` parameters that httpx>=0.28 requires. Added `write=10.0, pool=5.0`. The W1 skeleton compiled but blew up on the first real request — caught immediately by Wave 2's tests.

## Decisions Made

1. **`set[str]` for `_READ_ONLY_FIELDS` (not `frozenset[str]`).** mypy --strict rejects `frozenset[str]` for pydantic's `model_dump(exclude=…)` parameter (the `IncEx` type alias accepts `set[str]` directly). Functionally equivalent.
2. **`assert_all_called=False` on every reconciler test marker.** The test pattern registers routes that SHOULD NOT fire as call-count guards. respx's default "all routes were called" assertion is the inverse contract.
3. **Cluster fixture stamped with `tags=[1]` for the round-trip NO_OP test.** The reconciler adds the managed tag id to every desired DC before diffing, so the cluster fixture must already include it for `diff_models()` to return `[]`. Otherwise the round-trip test would fire a spurious UPDATE on `tags`.
4. **Defensive default — `managed_tag_id=None → PRUNE_PROTECTED`.** Even though Wave 2's `_ensure_managed_tag()` always returns a real Tag (or sentinel id=-1), the differ's protective branch covers a hypothetical future caller that might pass `managed_tag_id=None` directly. Locked in `test_no_managed_tag_id_treats_as_protected`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `client_base.py` httpx.Timeout missing write/pool parameters**

- **Found during:** Task 2 verification (first respx-mocked test invocation against `SonarrClient`).
- **Issue:** `httpx.Timeout(connect=5.0, read=30.0)` raises `ValueError: httpx.Timeout must either include a default, or set all four parameters explicitly.` httpx>=0.28 requires either a single positional default OR all four named params (connect, read, write, pool).
- **Fix:** Added `write=10.0, pool=5.0` to the constructor call in `client_base.py:48`.
- **Files modified:** `tools/arrconf/arrconf/client_base.py` (1 line).
- **Verification:** All 33 tests pass; mypy + ruff clean. The error originated from the W1 skeleton that was never actually exercised because W1's verification only checked `python -c 'import arrconf'` and not a real `SonarrClient(…)` constructor call.
- **Committed in:** `86340d4` (alongside the Task 2 GREEN implementation).

**2. [Rule 1 — Bug] `_READ_ONLY_FIELDS` typed as `set[str]`, not `frozenset[str]`**

- **Found during:** Task 1 GREEN — `mypy arrconf/differ.py` flagged `Argument "exclude" to "model_dump" of "BaseModel" has incompatible type "frozenset[str]"; expected "IncEx | None"`.
- **Issue:** The plan template suggested `frozenset[str]`. pydantic's `IncEx` type alias accepts `set[str]` but not `frozenset[str]` — strict mypy correctly rejects the broader type.
- **Fix:** Switched the literal from `frozenset({...})` to `{...}` (mutable set). The acceptance criterion `_READ_ONLY_FIELDS` "containing exactly {...}" is satisfied by either a set or frozenset; pick the one that types cleanly.
- **Files modified:** `tools/arrconf/arrconf/differ.py`.
- **Verification:** `mypy arrconf/differ.py` → 0 errors. Tests still pass at 100% coverage on the module.
- **Committed in:** `9dab8c5` (Task 1 GREEN).

---

**Total deviations:** 2 auto-fixed (1 W1 carry-over runtime bug, 1 mypy type-narrowing). No scope expansion, no architectural impact.

## Issues Encountered

- **respx default `assert_all_called=True`.** The first run of the Task 2 tests landed 12 PASSED but with 7 teardown errors because respx's pytest plugin treats unused routes as a failure. I had to opt out per-marker with `assert_all_called=False`. Captured as a pattern in `tech-stack.patterns` for Wave 3 to inherit.
- **The plan's verbatim grep `grep -c "FRONTIERE_MODULES = \[" tests/test_scope_violation.py` returns 0** because ruff format adds a type annotation: `FRONTIERE_MODULES: list[ModuleType] = [`. The semantic intent (4 frontière modules tested) is met — the parametrize marker iterates exactly the 4 modules required.

## Threat Model Mitigations Applied

| Threat ID | Severity | Status | Verification |
|-----------|----------|--------|--------------|
| T-01-04 (idempotence bypass via prune) | HIGH | mitigated | Two-line defense (default `prune: false` + managed-tag gate at delete time). Locked by 4 tests: `test_prune_skip_when_prune_false`, `test_prune_protected_when_no_managed_tag`, `test_no_managed_tag_id_treats_as_protected` (differ-level); `test_prune_protected_without_managed_tag` (reconciler-level). The "happy" pruning path is also tested (`test_prune_executes_with_managed_tag`) so we know the gate doesn't false-positive. |
| T-01-05 (scope-guard bypass) | HIGH | hardened | W1 raised ScopeViolationError before any HTTP import (static guarantee via grep). Wave 2 adds `test_scope_violation_raises_BEFORE_any_http_call` which uses respx as a network sniffer with no routes registered: any future bug introducing httpx into a frontière module would surface either as an unhandled-route error OR as a `respx_mock.calls.call_count > 0` assertion failure. |

## Decisions Surfaced for W3 Attention

1. **Wave 3 must NOT register catch-all respx routes in `apply` integration tests** — the per-test guard route pattern documented here scales to integration too.
2. **The dry-run tag sentinel id=-1** flows through `reconcile_sonarr` cleanly today because no real reconcile test exercises a dry-run-against-empty-tag-list. W3's CLI integration test should add an end-to-end dry-run case to lock the sentinel-propagation behavior at the CLI level.
3. **Coverage gate on `arrconf.config`** — `config.py` is currently uncovered (only used in tests via direct construction). When W3 fills `load_config()`, it should add fixture YAML files and unit tests; the existing `[tool.coverage.run] source = ["arrconf.differ", "arrconf.reconcilers.sonarr"]` scope keeps the gate green for now but should be widened in W3 to include `arrconf.config` and `arrconf.__main__`.
4. **The `_execute()` helper takes `path: str` as a parameter** — currently always `/downloadclient`. When W3 adds more reconcilable resources (Phase 3+), this signature stays stable, so adding indexers/notifications won't require a refactor.

## Next Phase Readiness

- **W3 (CLI wiring + tests.yml + round-trip integration)** can start immediately. The reconcile engine (`differ.reconcile`) and orchestrator (`reconcile_sonarr`) are both shipped, fully tested, and have a stable contract that W3 can call from `apply` / `dump` / `diff` typer commands.
- **The CLI bodies in `arrconf/__main__.py`** are W3 stubs — `apply` calls `reconcile_sonarr(client, instance, dry_run=True)` (or False), `dump` issues GET-only and serializes to YAML, `diff` is `apply --dry-run` formatted as a human-readable diff.
- **The round-trip integration test** (full pipeline: load YAML → apply dry-run → assert all NO_OP) belongs in W3 because it requires `load_config()` (W3 stub today). The engine-level round-trip is already proven by `test_dump_apply_no_op` (Task 2).

## Self-Check: PASSED

- All 4 created test files exist on disk (`test_differ.py`, `test_reconcilers_sonarr.py`, `test_managed_tag.py`, `test_scope_violation.py`).
- All 5 task commits exist on the worktree branch (verified by `git log --oneline 0427c6c3..HEAD` returning exactly the 5 commits listed above).
- Plan-level verification:
  1. `uv run pytest -x` → 33 passed.
  2. `uv run pytest --cov --cov-fail-under=70` → 99% on `arrconf.differ` (100%) + `arrconf.reconcilers.sonarr` (98%).
  3. `uv run mypy arrconf` → Success: no issues found in 23 source files.
  4. `uv run ruff check .` → All checks passed.
  5. `uv run ruff format --check .` → 29 files already formatted.
  6. T-01-04 tests pass (`test_prune_protected_when_no_managed_tag` + `test_no_managed_tag_id_treats_as_protected`).
  7. T-01-05 hardened test passes on all 4 frontière modules (`test_scope_violation_raises_BEFORE_any_http_call[*]`).
  8. No live API calls (`grep -rE 'httpx\.Client\(.*sonarr\.(?!test)' tests/` → 0 matches).

## TDD Gate Compliance

- Task 1: RED commit `3caab5e` (test) → GREEN commit `9dab8c5` (feat). Sequence verified.
- Task 2: RED commit `5b98992` (test) → GREEN commit `86340d4` (feat). Sequence verified.
- Task 3: not TDD (`tdd="false"` in plan); single test commit `10167e6`.

---
*Phase: 01-arrconf-poc-json-schema*
*Plan: 02 (Wave 2 — Sonarr Reconciler)*
*Completed: 2026-05-07*
