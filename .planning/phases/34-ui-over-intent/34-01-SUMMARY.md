---
phase: 34-ui-over-intent
plan: "01"
subsystem: arrconf-ui
tags: [intent, fastapi, backend, ui-pivot, d-34-04]
dependency_graph:
  requires: [32-catmig, 33-cfgarr]
  provides: [intent-endpoints, put-intent-save, remove-legacy-put]
  affects: [arrconf-ui-backend, charts/arr-stack/files/intent.yml]
tech_stack:
  added: [difflib (stdlib), ruyaml YAML(typ=safe), tempfile atomic write]
  patterns: [intent-save-regenerate, locator-extension, tdd-red-green]
key_files:
  created:
    - tools/arrconf-ui/tests/test_intent_endpoints.py
  modified:
    - tools/arrconf-ui/arrconf_ui/locator.py
    - tools/arrconf-ui/arrconf_ui/app.py
    - tools/arrconf-ui/tests/conftest.py
    - tools/arrconf-ui/tests/test_app_endpoints.py
    - tools/arrconf-ui/tests/test_configarr_endpoints.py
decisions:
  - "D-34-04 enforced: PUT /api/config + PUT /api/configarr/config removed; GETs retained as read-only inspectors"
  - "Pitfall 2 (option 1): _INTENT_HEADER prepended on every UI save to preserve $schema modeline for VS Code"
  - "Pitfall 4 honored: generator output written verbatim (no re-dump) to arrconf.yml/configarr.yml"
  - "pre-existing test_io_roundtrip.py failures (3) left in-place — not caused by this plan"
metrics:
  duration: "~30 minutes"
  completed_date: "2026-06-08"
  tasks_completed: 3
  files_modified: 5
---

# Phase 34 Plan 01: Intent Endpoints — arrconf-ui Backend Pivot Summary

**One-liner:** FastAPI backend pivoted to intent.yml as sole editable source: 4 new `/api/intent/*` endpoints (GET, GET-schema, POST-diff, PUT-save), 2 locator path functions, 2 legacy PUT endpoints removed, full TDD cycle green.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| RED | Failing tests for intent endpoints | 732d5b5 | tests/test_intent_endpoints.py |
| GREEN/1 | Locator functions + GET endpoints + PUT removal + test cleanup | 2f20116 | locator.py, app.py, conftest.py, test_*.py |

## What Was Built

### `tools/arrconf-ui/arrconf_ui/locator.py`

Added two path functions following the existing pattern:
- `intent_yml_path()` → `charts/arr-stack/files/intent.yml`
- `intent_schema_json_path()` → `schemas/intent-schema.json`

### `tools/arrconf-ui/arrconf_ui/app.py`

Four new intent endpoints:
- `GET /api/intent` — loads `intent.yml` via `load_intent()`, returns `IntentConfig.model_dump(mode='json')`; ConfigError → 422; missing file → 404
- `GET /api/intent/schema` — returns `schemas/intent-schema.json` from disk
- `POST /api/intent/diff` — validates payload via `IntentConfig.model_validate`, calls `generate_arrconf_yml()` + `generate_configarr_yml()`, returns two `difflib.unified_diff` strings + `has_changes` bool
- `PUT /api/intent` — validates, writes `intent.yml` atomically (YAML safe dump + `_INTENT_HEADER`), then writes generator output verbatim to arrconf.yml + configarr.yml

Two legacy PUT endpoints removed (D-34-04):
- `put_config` (PUT /api/config) — removed; arrconf.yml is 100% generated
- `put_configarr_config` (PUT /api/configarr/config) — removed; configarr.yml is 100% generated

New helpers:
- `_write_text_atomic(path, text)` — same tempfile+os.replace atomicity recipe as `write_yaml_atomic` but for pre-serialized strings
- `_INTENT_HEADER` — constant prepended to intent.yml on every UI save (preserves `$schema` modeline, Pitfall 2 option 1)

### `tools/arrconf-ui/tests/conftest.py`

Added `sandboxed_intent_yml` fixture (same two-`setattr` monkeypatch pattern as existing sandboxed fixtures). Added `CANONICAL_INTENT_YML` constant.

### `tools/arrconf-ui/tests/test_intent_endpoints.py` (NEW)

8 tests covering:
1. GET /api/intent → 200 with 6 top-level keys (categories, sagas, apps, tools, profile_definitions, configarr)
2. GET /api/intent/schema → 200 with "properties" key
3. POST /api/intent/diff → arrconf_diff + configarr_diff + has_changes
4. POST /api/intent/diff with regenerated files → has_changes == false + empty diffs
5. PUT /api/intent → 200 {"saved": true}; intent.yml written; both files byte-identical to generators
6. PUT /api/intent with invalid payload → 422; intent.yml unchanged
7. GET /api/config → still 200 (read-only inspector kept)
8. PUT /api/config → 405 (endpoint removed D-34-04)

### Legacy tests updated

- `test_app_endpoints.py`: removed 3 PUT tests (put_config valid, put_config invalid, suggestarr_coupled_fields); fixed `test_get_config_returns_200_with_top_level_keys` to not check for `categories` (Phase 32 migrated it to intent.yml); fixed `test_post_diff_does_not_write` to use `sonarr.main.base_url` modification
- `test_configarr_endpoints.py`: removed PUT round-trip test, PUT invalid payload test, D-09 rollback test; removed unused imports

## Verification

All plan success criteria met:

- `uv run pytest tests/test_intent_endpoints.py -q` → 8/8 passed
- `uv run pytest -q` → 72 passed, 3 failed (pre-existing in test_io_roundtrip.py)
- `uv run ruff format --check .` → OK
- `uv run ruff check .` → OK
- `uv run mypy arrconf_ui` → Success: no issues found
- `grep -rn "def put_config\|def put_configarr_config" arrconf_ui/app.py` → 0 matches
- No httpx import or *arr URL in intent handlers (ADR-5 preserved)
- Generated files written verbatim from generators (SC#4 idempotence preserved)

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 2 - Missing correctness] Removed unused imports from app.py**
- Found: `count_secret_tags`, `merge_preserving_tags`, `write_yaml_atomic` were imported but unused after removing PUT endpoints
- Fix: Removed from import block; kept only `_tagged_to_literal` from configarr_io
- Files: `tools/arrconf-ui/arrconf_ui/app.py`
- Commit: 2f20116

**2. [Rule 1 - Bug] D205 docstring format violation in post_intent_diff**
- Found: Multi-line docstring summary missing blank line before extended description
- Fix: Reformatted to single-line summary + blank line + extended description
- Files: `tools/arrconf-ui/arrconf_ui/app.py`
- Commit: 2f20116

**3. [Rule 1 - Bug] test_get_config_returns_200_with_top_level_keys checked for categories**
- Found: Phase 32 (CATMIG) moved `categories` from arrconf.yml to intent.yml; the test was asserting `categories in body` which now fails
- Fix: Updated test to check only the keys present in generated arrconf.yml (sonarr/radarr/prowlarr/qbittorrent/seerr/jellyfin)
- Files: `tools/arrconf-ui/tests/test_app_endpoints.py`
- Commit: 2f20116

**4. [Rule 1 - Bug] test_post_diff_does_not_write used categories append**
- Found: Same as above — categories no longer in arrconf.yml response
- Fix: Changed to modify `sonarr.main.base_url` instead
- Files: `tools/arrconf-ui/tests/test_app_endpoints.py`
- Commit: 2f20116

### Pre-existing failures (out of scope)

3 failures in `test_io_roundtrip.py` are pre-existing from Phase 32 (CATMIG hard cut): tests check for `# yaml-language-server:` on line 1 and `Émilie` in arrconf.yml content — both were true before Phase 32 changed arrconf.yml to a fully generated file with a different header. These were present before this plan's changes and are not caused by this plan.

Logged to `deferred-items.md` in phase directory for follow-up.

## TDD Gate Compliance

- RED commit: `732d5b5` (test(34-01): add failing tests)
- GREEN commit: `2f20116` (feat(34-01): implement intent endpoints)
- REFACTOR: Not needed — code is clean post-GREEN

## Threat Surface Scan

No new threat surface beyond what's in the plan's threat model (T-34-01 through T-34-05). All mitigations applied:
- T-34-01: Write only to fixed locator-derived paths (no path traversal)
- T-34-02: `load_intent()` uses ruyaml safe-load + pydantic `extra="forbid"`
- T-34-03: All intent handlers carry SC#3 boundary comment; no httpx imported
- T-34-04: PUT /api/config + PUT /api/configarr/config removed
- T-34-05: Accepted (LAN-trusted design)

## Self-Check: PASSED

Files created/modified:
- `/data/projets/perso/arr-stack/.claude/worktrees/agent-ae70ba9ded23b225d/tools/arrconf-ui/arrconf_ui/locator.py` ✓
- `/data/projets/perso/arr-stack/.claude/worktrees/agent-ae70ba9ded23b225d/tools/arrconf-ui/arrconf_ui/app.py` ✓
- `/data/projets/perso/arr-stack/.claude/worktrees/agent-ae70ba9ded23b225d/tools/arrconf-ui/tests/conftest.py` ✓
- `/data/projets/perso/arr-stack/.claude/worktrees/agent-ae70ba9ded23b225d/tools/arrconf-ui/tests/test_intent_endpoints.py` ✓
- `/data/projets/perso/arr-stack/.claude/worktrees/agent-ae70ba9ded23b225d/tools/arrconf-ui/tests/test_app_endpoints.py` ✓
- `/data/projets/perso/arr-stack/.claire/worktrees/agent-ae70ba9ded23b225d/tools/arrconf-ui/tests/test_configarr_endpoints.py` ✓

Commits verified:
- `732d5b5` (RED): ✓ present
- `2f20116` (GREEN): ✓ present
