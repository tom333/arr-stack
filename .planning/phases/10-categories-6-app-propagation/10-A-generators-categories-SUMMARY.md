---
phase: 10-categories-6-app-propagation
plan: 10-A-generators-categories
subsystem: arrconf/generators
tags:
  - python
  - generator
  - categories
  - pure-function
  - phase10
dependency_graph:
  requires:
    - 09-A-python-schema (Category model — read-only in Phase 10)
    - config.py TagItem + RootConfig (pre-existing)
    - resources/qbittorrent/category.py (pre-existing)
    - resources/sonarr/{tag,root_folder,download_client,remote_path_mapping}.py (pre-existing)
    - resources/jellyfin/library.py (pre-existing)
  provides:
    - arrconf.generators.categories — 5 pure generator functions
    - arrconf.generators.__init__ — re-exports public API
    - arrconf.generators.SonarrDerived + RadarrDerived dataclasses
  affects:
    - 10-C (qBit reconciler wiring — consumes generate_qbit_categories)
    - 10-D (Sonarr reconciler wiring — consumes generate_sonarr_resources)
    - 10-E (Radarr reconciler wiring — consumes generate_radarr_resources)
    - 10-F (Seerr animeTags routing — consumes generate_anime_tag_labels)
    - 10-G (Jellyfin PathInfos wiring — consumes generate_jellyfin_libraries)
tech_stack:
  added: []
  patterns:
    - pure-function generator module (no I/O, no httpx, no client calls)
    - "@dataclass containers SonarrDerived/RadarrDerived for multi-resource output"
    - "from __future__ import annotations + Final[] for private constants"
    - "module-level private constants _QBIT_HOST/_QBIT_PORT/_QBIT_IMPLEMENTATION/_QBIT_CONFIG_CONTRACT"
key_files:
  created:
    - tools/arrconf/arrconf/generators/__init__.py
    - tools/arrconf/arrconf/generators/categories.py
    - tools/arrconf/tests/test_generators_categories.py
  modified: []
decisions:
  - "D-01 honored: generators live in dedicated generators/ module as pure functions (no I/O)"
  - "D-03a: qBit category names are bare slugs (not <kind>-<name>); savePath=/data/torrents/<name>"
  - "D-03b-e: Sonarr/Radarr each get 5 DCs/tags/root_folders/RPMs from 5 categories per kind"
  - "Chart-pin co-bump deferred to Plan 10-C per CONTEXT.md D-05 exception (code is dead until Wave 2 wires it)"
  - "Task 10-A-01 and 10-A-02 merged into one commit (implementation included with package creation)"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-19"
  tasks_completed: 3
  files_created: 3
  tests_added: 24
  coverage: "100% on arrconf.generators"
---

# Phase 10 Plan A: generators/categories.py Summary

**One-liner:** Pure-function generator module expanding `RootConfig.categories` into per-app resource lists for qBit, Sonarr, Radarr, Jellyfin and Seerr (D-01).

## Tasks Executed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 10-A-01 | Create generators/ package + dataclass containers | `1a9198d` | generators/__init__.py, generators/categories.py |
| 10-A-02 | Implement 5 generator functions | (included in 1a9198d) | generators/categories.py |
| 10-A-03 | Unit tests for all 5 generators | `6fea29d` | tests/test_generators_categories.py |

## What Was Built

### `tools/arrconf/arrconf/generators/categories.py` (229 lines)

Five pure generator functions:

| Function | Output | Input filter |
|----------|--------|--------------|
| `generate_qbit_categories(cfg)` | `list[QbitCategory]` (10 entries) | all categories |
| `generate_sonarr_resources(cfg)` | `SonarrDerived` (5×4 resources) | `kind=series` |
| `generate_radarr_resources(cfg)` | `RadarrDerived` (5×4 resources) | `kind=movies` |
| `generate_jellyfin_libraries(cfg)` | `list[JellyfinLibrary]` (2 items) | kind-partitioned |
| `generate_anime_tag_labels(cfg)` | `list[str]` | `profile=anime` |

Key design choices:
- `SonarrDerived` / `RadarrDerived` `@dataclass` containers hold tags + root_folders + download_clients + remote_path_mappings (D-03b–e)
- Module-level private constants `_QBIT_HOST`, `_QBIT_PORT`, `_QBIT_IMPLEMENTATION`, `_QBIT_CONFIG_CONTRACT` match production `arrconf.yml`
- Private helpers `_qbit_dc_fields_sonarr(name)` / `_qbit_dc_fields_radarr(name)` build the 14-field `FieldKV` list without duplication
- D-03a: qBit category `name = c.name` (bare slug), `savePath = /data/torrents/<name>` (NOT `c.base_path`)
- Pitfall 6: RPM `remotePath = /data/<name>/`, `localPath = /data/torrents/<name>/` — both end with `/`
- `TagItem(label=c.name)` not `Tag` (which carries server-assigned id)

### `tools/arrconf/arrconf/generators/__init__.py` (24 lines)

Package marker re-exporting all 5 generators + 2 dataclasses via `__all__`.

### `tools/arrconf/tests/test_generators_categories.py` (388 lines, 24 tests)

Coverage: 100% on `arrconf.generators` module (exceeds 70% gate).

Test groups:
- qBit (4 tests): count, bare names, savePath format, empty config
- Sonarr (8 tests): 5-each count, tag labels, root_folders, DC tag_labels, tvCategory field, RPM trailing slashes, empty config, connection constants
- Radarr (4 tests): 5-each count, movieCategory field, RPM trailing slashes, empty config
- Jellyfin (4 tests): 2-supers count, paths match base_paths, all-series-no-movies, empty config
- animeTags (2 tests): production fixture (2 anime categories: films-zoe + series-zoe), empty config
- Cross-cases (2 tests): qBit order preservation, Sonarr order preservation

## Deviations from Plan

### Minor: Tasks 10-A-01 and 10-A-02 merged into one commit

**Found during:** Task 10-A-01 implementation
**Issue:** The plan specified Task 10-A-01 for dataclass containers only, and Task 10-A-02 for the 5 generator functions. Because the generators are tightly coupled to the dataclasses (they return `SonarrDerived`/`RadarrDerived`), implementing them in the same writing session avoids a non-compiling intermediate state.
**Fix:** Included all 5 generator functions in the Task 10-A-01 commit (`1a9198d`). Task 10-A-02 verification (ruff + mypy) was run and passed against this commit, but no separate commit was created.
**Impact:** No behavioral difference. All acceptance criteria for both tasks were met. The commit message references `10-A` plan.

### D-05 Chart-pin co-bump exception (documented)

Per CONTEXT.md D-05 and the plan's output spec: this plan's commits do NOT touch `values.yaml`. The new generators code is dead until Wave 2 wires it. The first chart-pin bump (`0.5.3 → 0.6.0`) will be co-committed with Plan 10-C (qBit reconciler wiring — first Wave 2 plan to ship arrconf behavioral changes).

**This is NOT a D-05 violation.** D-05 requires the co-bump when a reconciler behavior changes. Adding a dead generators module does not change reconciler output.

## Wave 2 Consumers

Plans 10-C through 10-G (all Wave 2, parallel execution) consume this module:

| Plan | Function consumed | How |
|------|-------------------|-----|
| 10-C | `generate_qbit_categories` | pre-merge in `__main__.py` before `reconcile_qbittorrent` |
| 10-D | `generate_sonarr_resources` | pre-merge in `__main__.py` before `reconcile_sonarr` |
| 10-E | `generate_radarr_resources` | pre-merge in `__main__.py` before `reconcile_radarr` |
| 10-F | `generate_anime_tag_labels` | label→ID resolution after `reconcile_sonarr`, before `reconcile_seerr` |
| 10-G | `generate_jellyfin_libraries` | pre-merge in `__main__.py` before `reconcile_jellyfin` |

None of Wave 2 plans need to modify `generators/categories.py` — the module is complete and stable.

## Known Stubs

None. All 5 functions are fully implemented and return production-correct shapes.

## Threat Flags

None. The generators module is pure Python with no network endpoints, no auth paths, no file access, and no schema changes at trust boundaries.

## Self-Check: PASSED

- `tools/arrconf/arrconf/generators/__init__.py` — FOUND
- `tools/arrconf/arrconf/generators/categories.py` — FOUND
- `tools/arrconf/tests/test_generators_categories.py` — FOUND
- Commit `1a9198d` — FOUND (feat(10-A): create generators/ package...)
- Commit `6fea29d` — FOUND (test(10-A): add 24 unit tests...)
- All 24 tests pass; 100% coverage on arrconf.generators
- ruff + ruff format + mypy strict all clean
