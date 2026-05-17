---
phase: "03"
plan: "02"
subsystem: arrconf
tags: [config, phase-3, scope-guard, caller-migration, radarr, prowlarr]
dependency_graph:
  requires: ["03-01"]
  provides: ["03-03", "03-04", "03-05"]
  affects: ["tools/arrconf/arrconf/config.py", "tools/arrconf/arrconf/__main__.py", "tools/arrconf/arrconf/diff_cmd.py", "tools/arrconf/arrconf/dump.py"]
tech_stack:
  added: []
  patterns: ["D-03-05 monolithic RootConfig", "D-03-03 AppEntry declarative YAML", "D-03-04 HostConfigSection opt-in", "ScopeViolationError guard for Radarr"]
key_files:
  created:
    - tools/arrconf/arrconf/resources/radarr/__init__.py
    - tools/arrconf/arrconf/resources/radarr/quality_profile.py
    - tools/arrconf/arrconf/resources/radarr/custom_format.py
    - tools/arrconf/arrconf/resources/radarr/quality_definition.py
    - tools/arrconf/arrconf/resources/radarr/media_naming.py
  modified:
    - tools/arrconf/arrconf/config.py
    - tools/arrconf/arrconf/__main__.py
    - tools/arrconf/arrconf/diff_cmd.py
    - tools/arrconf/arrconf/dump.py
    - tools/arrconf/tests/test_config.py
    - tools/arrconf/tests/test_scope_violation.py
    - tools/arrconf/tests/test_round_trip.py
    - tools/arrconf/tests/test_cli.py
    - tools/arrconf/pyproject.toml
    - examples/baseline-sonarr.yml
decisions:
  - "D-03-05 applied: RootConfig flat sonarr/radarr/prowlarr dicts at top level, apps: indirection removed"
  - "D-03-04 applied: HostConfigSection.enable defaults False — host_config opt-in safety"
  - "D-03-03 applied: AppEntry.type Literal['sonarr','radarr'], sync_level Literal['fullSync','addOnly','disabled']"
  - "D-03-01 applied: RadarrInstance full parity with SonarrInstance (5 section fields)"
  - "D-03-02 applied: ProwlarrInstance apps-only (no indexer definitions in YAML)"
  - "N815 suppressed for arrconf/config.py: camelCase API field names in HostConfigSection are intentional (mirror API)"
metrics:
  duration: "7m"
  completed: "2026-05-11"
  tasks_completed: 4
  files_modified: 10
  files_created: 5
---

# Phase 3 Plan 02: Config Restructure — Phase-3 Monolithic RootConfig Summary

Restructured `config.py` to the Phase-3 D-03-05 monolithic flat shape: flat
`sonarr` / `radarr` / `prowlarr` dict fields on `RootConfig`, new `RadarrInstance`
and `ProwlarrInstance` instance models, 5 new section models, `AppEntry` with
Literal-typed fields, 4 Radarr frontière modules, and full caller migration.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 2.1 | Replace config.py with Phase-3 monolithic structure | a786403 | arrconf/config.py |
| 2.2 | Migrate callers to root.sonarr["main"] | ae09a88 | __main__.py, diff_cmd.py, dump.py, test_round_trip.py |
| 2.3 | Create 4 Radarr frontière modules + update test_scope_violation.py | 37fdd97 | resources/radarr/*.py, test_scope_violation.py |
| 2.4 | Rewrite test_config.py + full regression gate | b49ba6c | test_config.py, test_cli.py, pyproject.toml, baseline-sonarr.yml |

## New config.py Shape

10 classes in Phase-3 monolithic `config.py`:

**Section models (6):**
- `DownloadClientsSection` — `prune: bool = False`, `items: list[DownloadClient]`
- `IndexersSection` — `prune: bool = False`, `items: list[Indexer]`
- `NotificationsSection` — `prune: bool = False`, `items: list[Notification]`
- `RootFoldersSection` — `prune: bool = False`, `items: list[RootFolder]`
- `HostConfigSection` — `enable: bool = False` (D-03-04 opt-in), camelCase API fields
- `AppsSection` — `prune: bool = False`, `items: list[AppEntry]`

**AppEntry (1):**
- `name: str`, `type: Literal["sonarr", "radarr"]`, `base_url: str`
- `api_key_env: str`, `sync_level: Literal["fullSync", "addOnly", "disabled"]`

**Instance models (3):**
- `SonarrInstance` — 5 section fields: download_clients, host_config, indexers, notifications, root_folders
- `RadarrInstance` — identical section list to SonarrInstance (D-03-01 full parity)
- `ProwlarrInstance` — apps section only (D-03-02 scope)

**Root (1):**
- `RootConfig` — `sonarr: dict[str, SonarrInstance]`, `radarr: dict[str, RadarrInstance]`, `prowlarr: dict[str, ProwlarrInstance]`

**Removed:** `AppsConfig`, `SonarrConfig` (Phase-1 indirection — D-03-05)

## Caller Migration Coverage

All `root.apps.sonarr.main` references replaced with `root.sonarr["main"]`:
- `arrconf/__main__.py`: 3 subcommand branches (apply, dump, diff)
- `arrconf/diff_cmd.py`: guard check + reconcile call
- `arrconf/dump.py`: `config_dict` no longer has `apps:` outer key
- `tests/test_round_trip.py`: 4 call sites (2 round-trip tests + 1 baseline load test)

## Radarr Frontière Modules

4 modules created under `arrconf/resources/radarr/`:
- `quality_profile.py` — raises `ScopeViolationError("radarr quality_profiles is owned by configarr (ADR-5)...")`
- `custom_format.py` — raises `ScopeViolationError("radarr custom_formats is owned by configarr (ADR-5)...")`
- `quality_definition.py` — raises `ScopeViolationError("radarr quality_definitions is owned by configarr (ADR-5)...")`
- `media_naming.py` — raises `ScopeViolationError("radarr media_naming is owned by configarr (ADR-5)...")`

All raise pre-network (T-01-05 mitigation), verified by `test_scope_violation_raises_BEFORE_any_http_call`.

## Test Suite Results

- `test_config.py`: 7 tests (new Phase-3 shape)
  - `test_load_config_happy_path_sonarr_only` — Phase-3 YAML + section defaults
  - `test_load_config_happy_path_all_three_apps` — sonarr + radarr + prowlarr + AppEntry
  - `test_load_config_validation_error_returns_exit_2` — extra="forbid" blocks bogus keys
  - `test_load_config_yaml_syntax_error_returns_exit_2` — malformed YAML
  - `test_load_config_missing_file_returns_exit_2` — absent file
  - `test_app_entry_rejects_invalid_type` — Literal type guard
  - `test_app_entry_rejects_invalid_sync_level` — Literal sync_level guard

- `test_scope_violation.py`: 24 tests (8 modules × 3 parametric cases)
  - 4 Sonarr + 4 Radarr frontière modules
  - `test_scope_violation_raised_with_configarr_message`
  - `test_scope_violation_raises_BEFORE_any_http_call` (T-01-05)
  - `test_scope_violation_message_names_resource`

- **Full suite**: 81 passed (test_schema_gen.py excluded — see Plan 06 dependency below)

## Regression Gate (Task 2.4 Part B)

- `pytest -q --no-cov --ignore=tests/test_schema_gen.py`: 81 passed
- `ruff check arrconf/ tests/`: All checks passed
- `mypy arrconf/config.py arrconf/__main__.py arrconf/diff_cmd.py arrconf/dump.py arrconf/resources/radarr/`: Success, no issues in 9 source files

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_cli.py YAML literals using old apps: format**
- **Found during:** Task 2.4 regression gate
- **Issue:** 5 tests in `test_cli.py` used old `apps:\n  sonarr:\n    main:` YAML format. With new `extra="forbid"` config, these would fail with ConfigError (exit 2) instead of reaching the intended test path. Tests expecting exit 2 for API key issues would still pass (same exit code, wrong reason), but `test_diff_returns_3_on_drift` expected exit 3 and got exit 2 from config parse failure.
- **Fix:** Updated all 5 YAML literals to `sonarr:\n  main:` flat format
- **Files modified:** `tools/arrconf/tests/test_cli.py`
- **Commit:** b49ba6c

**2. [Rule 1 - Bug] examples/baseline-sonarr.yml using old apps: format**
- **Found during:** Task 2.4 regression gate (`test_committed_baseline_yaml_loads` failed)
- **Issue:** `examples/baseline-sonarr.yml` had `apps:\n  sonarr:\n    main:` structure from Phase 1 dump. New `RootConfig` with `extra="forbid"` rejects the `apps:` key as an unknown field.
- **Fix:** Migrated to flat `sonarr:\n  main:` format, reduced indentation by one level throughout
- **Files modified:** `examples/baseline-sonarr.yml`
- **Commit:** b49ba6c

**3. [Rule 2 - Missing] N815 suppression for config.py camelCase fields**
- **Found during:** Task 2.4 ruff gate
- **Issue:** `HostConfigSection` in `config.py` uses camelCase field names (`authenticationMethod`, `authenticationRequired`, `urlBase`, `instanceName`) that mirror the Sonarr/Radarr API. ruff N815 flagged these. The existing suppression was only for `arrconf/resources/**`.
- **Fix:** Added `"arrconf/config.py" = ["N815"]` to `pyproject.toml` per-file-ignores with a comment explaining the rationale (camelCase API field names for YAML→API round-trip, same as resources/).
- **Files modified:** `tools/arrconf/pyproject.toml`
- **Commit:** b49ba6c

## Plan 06 Dependency (Schema Drift)

`test_schema_gen.py` is excluded from the full regression gate because the new `RootConfig` shape (10 classes, new AppEntry Literal fields, new instance models) produces a different JSON Schema than the committed `schemas/arrconf-schema.json`. This is expected — Plan 06 owns:
1. Running `arrconf schema-gen --output schemas/arrconf-schema.json`
2. Committing the updated schema
3. Re-enabling `test_schema_gen.py` in the full suite

## Known Stubs

None — all new models have proper field definitions and defaults. AppEntry fields are all required except `sync_level` which has a default of `"fullSync"`.

## Self-Check: PASSED

Files exist:
- tools/arrconf/arrconf/config.py ✓
- tools/arrconf/arrconf/resources/radarr/__init__.py ✓
- tools/arrconf/arrconf/resources/radarr/quality_profile.py ✓
- tools/arrconf/arrconf/resources/radarr/custom_format.py ✓
- tools/arrconf/arrconf/resources/radarr/quality_definition.py ✓
- tools/arrconf/arrconf/resources/radarr/media_naming.py ✓
- .planning/phases/03-extend-arrconf/03-02-SUMMARY.md ✓

Commits exist: a786403, ae09a88, 37fdd97, b49ba6c
