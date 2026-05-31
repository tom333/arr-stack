---
phase: 25-configarr-in-ui-backend
plan: "01"
subsystem: arrconf-ui
tags: [configarr, tag-preservation, anti-leak, tdd, sc1]
dependency_graph:
  requires: []
  provides: [configarr_io._tagged_to_literal, locator.configarr_yml_path, locator.configarr_schema_json_path, tests.sandboxed_configarr_yml]
  affects: [tools/arrconf-ui]
tech_stack:
  added: []
  patterns: [TaggedScalar literal reconstruction, double-monkeypatch sandbox fixture]
key_files:
  created:
    - tools/arrconf-ui/arrconf_ui/configarr_io.py
    - tools/arrconf-ui/tests/test_configarr_leak.py
  modified:
    - tools/arrconf-ui/arrconf_ui/locator.py
    - tools/arrconf-ui/tests/conftest.py
decisions:
  - "raising=False on arrconf_ui.app.configarr_yml_path monkeypatch in sandboxed_configarr_yml fixture — app.py does not yet re-export the symbol (Plan 03 adds it); raising=False makes the fixture forwards-compatible without modification"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-29"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 4
---

# Phase 25 Plan 01: Anti-Leak Foundation (configarr_io + locators + task-zero test) Summary

Task-zero SC#1 anti-leak foundation: `_tagged_to_literal` reconstructs `!env`/`!secret` TaggedScalar nodes as literal strings, configarr path resolvers added to locator.py, sandboxed fixture in conftest.py, and 5-test round-trip anti-leak suite passes against real configarr.yml.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 0 | Task-zero anti-leak round-trip test + tag-literal helper + configarr locators | 17ddb22 | configarr_io.py (new), locator.py (+2 funcs), conftest.py (+1 fixture), test_configarr_leak.py (new, 5 tests) |

## What Was Built

### `tools/arrconf-ui/arrconf_ui/configarr_io.py` (new)

Provides `_tagged_to_literal(node)` — a recursive tree-walker that converts `ruyaml` `TaggedScalar` objects to their full literal string representation (`"!env SONARR_API_KEY"`), leaving all other scalars, dicts, and lists unchanged. The docstring explicitly documents the forbidden `json.dumps(default=str)` shortcut (Pitfall 1 from RESEARCH) and why it must not be used.

### `tools/arrconf-ui/arrconf_ui/locator.py` (extended)

Two new resolvers added:
- `configarr_yml_path()` → `repo_root() / "charts" / "arr-stack" / "files" / "configarr.yml"`
- `configarr_schema_json_path()` → `repo_root() / "schemas" / "configarr-schema.json"`

### `tools/arrconf-ui/tests/conftest.py` (extended)

New `sandboxed_configarr_yml` fixture: copies real `configarr.yml` to `tmp_path`, double-monkeypatches `arrconf_ui.locator.configarr_yml_path` (strict) and `arrconf_ui.app.configarr_yml_path` (`raising=False`, forwards-compatible with Plan 03).

### `tools/arrconf-ui/tests/test_configarr_leak.py` (new, 5 tests)

| Test | Description | Threat |
|------|-------------|--------|
| `test_tagged_to_literal_sonarr_api_key` | `_tagged_to_literal` yields `"!env SONARR_API_KEY"` | T-25-01 |
| `test_tagged_to_literal_radarr_api_key` | `_tagged_to_literal` yields `"!env RADARR_API_KEY"` | T-25-01 |
| `test_roundtrip_preserves_env_tags_byte_for_byte` | read→write→re-read contains both `!env` tags verbatim | T-25-02 (SC#1) |
| `test_json_coercion_would_drop_env_tag` | proves `json.dumps(default=str)` produces bare `"SONARR_API_KEY"` — documents Pitfall 1 | T-25-01 regression guard |
| `test_tagged_to_literal_leaves_plain_scalars_unchanged` | `base_url`, plain strings, ints pass through unchanged | correctness |

All 5 pass. Triade (ruff format + ruff check + mypy) clean.

## Deviations from Plan

None — plan executed exactly as written.

The `raising=False` on `arrconf_ui.app.configarr_yml_path` was explicitly specified in the plan's `<action>` section.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All new code is pure in-process utility (no I/O beyond reading the real `configarr.yml` in tests). Threat mitigations T-25-01 and T-25-02 are now enforced by the test suite.

## Known Stubs

None. No UI-facing data flow, no placeholder values.

## Self-Check: PASSED

- `tools/arrconf-ui/arrconf_ui/configarr_io.py` exists and contains `_tagged_to_literal` and `TaggedScalar`
- `tools/arrconf-ui/arrconf_ui/locator.py` contains `configarr_yml_path` and `configarr_schema_json_path`
- `tools/arrconf-ui/tests/conftest.py` contains `sandboxed_configarr_yml`
- `tools/arrconf-ui/tests/test_configarr_leak.py` contains `!env SONARR_API_KEY`
- Commit `17ddb22` exists in git log
- 5/5 tests pass, triade clean
