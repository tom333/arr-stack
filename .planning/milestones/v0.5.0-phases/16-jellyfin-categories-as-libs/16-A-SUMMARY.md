---
phase: 16-jellyfin-categories-as-libs
plan: A
subsystem: jellyfin-reconciler
tags: [jellyfin, reconciler, categories, generator, milestone-v0.5.0]
status: checkpoint-pending-operator
requires: [REQ-jellyfin-categories-as-libs]
provides:
  - 10-jellyfin-libraries-from-categories
  - jellyfin-library-lifecycle-create-delete
  - d-16-prune-01-opt-in-deletion
affects:
  - charts/arr-stack/values.yaml (arrconf.image.tag bump)
  - schemas/arrconf-schema.json
tech-stack:
  added: []
  patterns:
    - "Match-by-Name pre-check before POST (Pitfall 16-1 idempotence shim)"
    - "NotFoundError tolerance on DELETE Lib (Pitfall 16-2)"
    - "Single GET cluster snapshot + dispatch (Pitfall 16-3 discipline)"
key-files:
  created:
    - snapshots/before-phase-16-2026-05-24/jellyfin/* (10 files, ADR-6 baseline)
    - tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json
    - .planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md
  modified:
    - tools/arrconf/arrconf/generators/categories.py
    - tools/arrconf/arrconf/reconcilers/jellyfin.py
    - tools/arrconf/arrconf/config.py
    - tools/arrconf/tests/test_jellyfin_categories.py
    - tools/arrconf/tests/test_reconcilers_jellyfin.py
    - tools/arrconf/tests/test_generators_categories.py
    - tools/arrconf/tests/test_arrconf_yml_validates.py
    - schemas/arrconf-schema.json
    - charts/arr-stack/values.yaml
decisions:
  - "Combined Tasks 2-9 into one atomic commit (CLAUDE.md release-pin co-bump pattern requires `tools/arrconf/**` changes + `charts/arr-stack/values.yaml#arrconf.image.tag` bump in same commit)"
  - "Updated 4 sibling generator tests in test_generators_categories.py + 1 arrconf.yml validation test (Rule 1 deviation — tests asserted obsolete contract that Phase 16 explicitly reverses)"
metrics:
  duration: "~70m wall clock (1 task + 8 implementation tasks + checkpoint pending)"
  completed: 2026-05-24
  tasks-complete: 9-of-10
  tests-added: 14 (6 generator + 8 reconciler)
  tests-modified: 5 (4 sibling generator + 1 arrconf.yml validation)
  total-test-count: 395 passed (vs 384 Phase 12 baseline)
  coverage: "84.97% (cov-fail-under=70 satisfied)"
---

# Phase 16 Plan A: Jellyfin Categories-as-libs Summary

Phase 16 (v0.5.0 milestone anchor) refactors `generate_jellyfin_libraries()` to emit 10 VirtualFolder libs (one per `categories[]` entry) instead of 2 super-libs. Extends `_reconcile_libraries()` with full library lifecycle: CREATE missing libs, prune-gated DELETE PathInfo, prune-gated DELETE Lib (404-tolerant). D-07-LIB-01 hardcoded `prune:false` is reversed via D-16-PRUNE-01 (opt-in via YAML).

## Status

- **Tasks 1-9 complete and committed.**
- **Task 10 (checkpoint:human-verify, blocking) PENDING operator close-out.**

## Tasks completed (atomic commits)

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | ADR-6 pre-cutover snapshot baseline | `e66c996` | `snapshots/before-phase-16-2026-05-24/jellyfin/` (10 JSON files) |
| 2 | Refactor `generate_jellyfin_libraries()` to 10-lib emission | `2ef003b` | `tools/arrconf/arrconf/generators/categories.py` |
| 3 | Extend `_reconcile_libraries()` — CREATE + prune-gated DELETE Path + DELETE Lib | `2ef003b` | `tools/arrconf/arrconf/reconcilers/jellyfin.py` |
| 4 | Update `JellyfinLibrariesSection.prune` docstring + regen JSON schema | `2ef003b` | `tools/arrconf/arrconf/config.py`, `schemas/arrconf-schema.json` |
| 5 | Rewrite `test_jellyfin_categories.py` — 6 generator tests | `2ef003b` | `tools/arrconf/tests/test_jellyfin_categories.py` |
| 6 | Extend `test_reconcilers_jellyfin.py` — 8 reconciler tests + new fixture | `2ef003b` | `tools/arrconf/tests/test_reconcilers_jellyfin.py`, `tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json` |
| 7 | Triad gate — ruff format/check + mypy + pytest --cov=70 | `2ef003b` (verification) | (no file changes — gate) |
| 8 | Chart-pin co-bump `arrconf.image.tag: 0.7.0 → 0.8.0` | `2ef003b` | `charts/arr-stack/values.yaml` |
| 9 | Write `16-HUMAN-UAT.md` — 5 operator scenarios | `2ef003b` | `.planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md` |

## Code-side artifacts

### Generator (`arrconf/generators/categories.py`)
- New constant `_KIND_TO_COLLECTION_TYPE: Final[dict[str, str]] = {"series": "tvshows", "movies": "movies"}`.
- `generate_jellyfin_libraries` rewritten to a 10-line list comprehension over `cfg.categories`.
- Returns `JellyfinLibrary(name=c.display, collection_type=_KIND_TO_COLLECTION_TYPE[c.kind], paths=[c.base_path])` per Category.
- Empty `cfg.categories` → empty list (no implicit super-libs — Phase 16 reversal).
- Old hardcoded `"Séries"` / `"Films"` literals removed.

### Reconciler (`arrconf/reconcilers/jellyfin.py`)
- New helper `_create_library`: POST `/Library/VirtualFolders` with query params (`name`, `collectionType`, `paths`, `refreshLibrary=false`) + body `{}`.
- New helper `_add_missing_paths`: Phase 7 idempotence shim, extracted to function from old inline loop.
- New helper `_prune_library_paths`: DELETE excess PathInfos, prune-gated; sorted excess for determinism.
- New helper `_prune_libraries`: DELETE orphaned cluster libs, prune-gated, `try/except NotFoundError` → `log.info("library_already_absent")`.
- `_reconcile_libraries` rewritten: single GET, dispatch CREATE vs add+prune, then prune libs at end.
- `from arrconf.exceptions import NotFoundError` added.
- Module docstring updated to reflect Phase 16 ownership of CREATE + DELETE.
- Removed legacy `library_missing_skip` warning + "Operator must create the library via Jellyfin UI Dashboard" hint.

### Config (`arrconf/config.py`)
- `JellyfinLibrariesSection` class docstring + `prune` field description updated to D-16-PRUNE-01 semantics.
- Default `prune=False` UNCHANGED — operator opts in via YAML at cutover time.

### Tests
- 6 new generator tests (10-lib emission, kind→collection_type mapping, names match display, single PathInfo per lib, order follows cfg.categories, empty cfg).
- 8 new reconciler tests, including the two Pitfall 16-1 / 16-2 contract tests:
  - `test_library_create_skipped_when_name_already_exists` — Pitfall 16-1 (match-by-Name pre-check).
  - `test_library_prune_lib_tolerates_404` — Pitfall 16-2 (NotFoundError tolerance).
- New 10-lib post-cutover GET fixture `tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json`.
- 4 sibling generator tests in `test_generators_categories.py` updated to Phase 16 contract (deviation Rule 1 — see below).
- 1 arrconf.yml validation test updated to assert 10 libs (deviation Rule 1).

### Schema (`schemas/arrconf-schema.json`)
- Regenerated. Contains D-16-PRUNE-01 marker in `JellyfinLibrariesSection.description` and `prune.description`.
- Reproducibility: re-running `arrconf schema-gen` produces identical output → CI schema gate passes.

### Chart (`charts/arr-stack/values.yaml`)
- `arrconf.image.tag` co-bumped `"0.7.0"` → `"0.8.0"` (minor — new feature).
- Renovate annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` preserved verbatim above `repository:`.

## Pitfalls mitigated in code

| Pitfall | Mitigation | Test contract |
|---------|-----------|---------------|
| **16-1 (CRITIQUE)** — POST `/Library/VirtualFolders` not idempotent | Match-by-Name pre-check against pre-fetched cluster snapshot before POST. Single GET, dispatch in `_reconcile_libraries`. | `test_library_create_skipped_when_name_already_exists` |
| **16-2** — DELETE `/Library/VirtualFolders` 404 on missing lib | `try / except NotFoundError` in `_prune_libraries` → `log.info("library_already_absent")`, continues with remaining libs. | `test_library_prune_lib_tolerates_404` |
| **16-3** — Single GET discipline (no per-iteration GET) | `_reconcile_libraries` fetches `current_libraries` ONCE, then dispatches via `by_name` dict. Helpers receive the cluster slice they need, never re-GET. | (architecturally enforced — covered indirectly by all 8 reconciler tests) |
| **16-4** — Watched-state preservation depends on filesystem migration | Documented as HUMAN-UAT pre-merge gate G1; arrconf code is filesystem-migration-agnostic. | (operator gate, not code) |

## Triad + tests gate (Task 7)

| Gate | Result |
|------|--------|
| `uv run ruff format --check .` | 91 files already formatted (0 diff) |
| `uv run ruff check .` | All checks passed |
| `uv run mypy arrconf` (CI-equivalent) | Success: no issues found in 55 source files |
| `uv run pytest --cov=arrconf --cov-fail-under=70` | 395 passed, coverage 84.97% |
| `arrconf schema-gen` reproducibility | Re-run produces identical schema output |

Note: `uv run mypy .` (full repo incl. tests) shows 43 pre-existing baseline errors in 10 test files (unrelated to Phase 16 — confirmed by `git stash` comparison). CI gate uses `mypy arrconf` (package only), which is clean.

## Deviations from Plan

### Auto-fixed issues (Rule 1 — bug fix on tests asserting obsolete contract)

**1. [Rule 1 - Bug] Updated 4 sibling generator tests in `test_generators_categories.py`**
- **Found during:** Task 7 (triad gate) — pytest reported 5 failures.
- **Issue:** Pre-existing `test_generators_categories.py` tests asserted the old 2-super-libs contract that Phase 16 explicitly reverses (`test_generate_jellyfin_libraries_2_supers`, `test_generate_jellyfin_paths_match_base_paths`, `test_generate_jellyfin_all_series_no_movies`, `test_generate_jellyfin_libraries_empty`).
- **Fix:** Rewrote the 4 tests to assert the Phase 16 contract (10-lib emission, single PathInfo, empty cfg → empty list).
- **Files modified:** `tools/arrconf/tests/test_generators_categories.py`
- **Commit:** `2ef003b`

**2. [Rule 1 - Bug] Updated `test_arrconf_yml_validates_jellyfin` to Phase 16 contract**
- **Found during:** Task 7.
- **Issue:** Test asserted `len(jf_libraries) == 2` (old super-libs contract) against the production `arrconf.yml`.
- **Fix:** Updated to assert `len(jf_libraries) == 10`, plus first-Category assertion (Séries, tvshows, `/media/series`) and 5+5 collection-type split.
- **Files modified:** `tools/arrconf/tests/test_arrconf_yml_validates.py`
- **Commit:** `2ef003b`

### Discoveries (deferred, out of scope)

- **`tools/arrconf/tests/fixtures/phase10-baseline-plans.json` auto-regenerated by `test_phase10_idempotence_sweep.py`.** The file was deleted in Phase 12 commit `827e5cd` (sweep), but the test (`test_phase10_baseline_fixture_exists_or_generate`) still bootstraps it on every fresh run. Removed from staging before commit per scope-boundary rule. Out of scope for Phase 16 — Phase 10 test infrastructure leftover. Recommend follow-up: either re-commit the baseline (locking the contract) or remove the regeneration logic from the test.

### Authentication gates

None — kubectl + sealed-secret `JELLYFIN_API_KEY` worked out of the box for Task 1 snapshot (cluster reachable via `kubectl port-forward`).

## ADR-6 snapshot path

`snapshots/before-phase-16-2026-05-24/jellyfin/` — 10 JSON files captured BEFORE any code change. Confirms pre-cutover state: 2 super-libs (`Séries` with 3 paths, `Films` with 3 paths). Committed in `e66c996`.

## Open HUMAN-UAT scenarios + close criteria

Operator must close out via `.planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md`:

| # | Status | Type |
|---|--------|------|
| 1 — Web UI shows 10 libs | Pending | MANDATORY for close |
| 2 — Watched-state on 3 preserved series | Pending | MANDATORY for close |
| 3 — Prune flip to false (0 drift) | Pending | MANDATORY for close |
| 4 — JellyCon LibreELEC | Pending | CARRY-FORWARD per D-16-JELLYCON-UAT-01 |
| 5 — Legacy v0.2.0 paths zombie sweep | Pending | OPTIONAL |

## Carry-forward items into v0.5.x+ backlog

- **JellyCon LibreELEC scenario** (D-16-JELLYCON-UAT-01) — non-blocking, exercised by operator post-merge once JellyCon install lands.
- **Phase 10 baseline fixture infrastructure** — Phase 10 sweep test auto-regenerates a deleted-in-Phase-12 fixture. Recommend cleanup PR.

## Self-Check

### Created files exist
- `snapshots/before-phase-16-2026-05-24/jellyfin/library_virtualfolders.json` — FOUND
- `tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json` — FOUND
- `.planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md` — FOUND

### Commits exist
- `e66c996` snapshot(16-A): pre-cutover Jellyfin baseline — FOUND
- `2ef003b` feat(16-A): Jellyfin Categories-as-libs — FOUND

## Self-Check: PASSED
