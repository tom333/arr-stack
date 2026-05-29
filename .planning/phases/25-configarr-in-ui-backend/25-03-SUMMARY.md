---
phase: 25-configarr-in-ui-backend
plan: "03"
subsystem: arrconf-ui
tags: [configarr, fastapi, endpoints, tdd, sc2, sc3, sc4, d09, anti-leak]
dependency_graph:
  requires: [25-01, 25-02]
  provides:
    - arrconf_ui.configarr_diff.configarr_diff
    - arrconf_ui.configarr_diff.has_changes
    - GET /api/configarr/config
    - PUT /api/configarr/config
    - POST /api/configarr/diff
    - GET /api/configarr/schema
  affects: [tools/arrconf-ui/arrconf_ui/app.py, tools/arrconf-ui/arrconf_ui/configarr_diff.py]
tech_stack:
  added: []
  patterns:
    - "configarr-shape structured diff (per-quality-profile by name, per-custom-format by trash_ids[0])"
    - "_cf_stable_key helper extracts stable diff key from trash_ids list vs trash_id scalar"
    - "D-09 byte-presence guard: capture before_bytes + !env/!secret counts, rollback write_bytes + 500 on loss"
    - "_tagged_to_literal for GET/diff (NOT _read_current which JSON-coerces and drops tags)"
    - "Strict double-monkeypatch in conftest.py (raising=True now that Plan 03 ships)"
key_files:
  created:
    - tools/arrconf-ui/arrconf_ui/configarr_diff.py
    - tools/arrconf-ui/tests/test_configarr_diff.py
    - tools/arrconf-ui/tests/test_configarr_endpoints.py
  modified:
    - tools/arrconf-ui/arrconf_ui/app.py
    - tools/arrconf-ui/tests/conftest.py
decisions:
  - "_cf_stable_key: custom_formats[] entries use trash_ids (list) not trash_id (scalar); derive stable diff key from trash_ids[0] as first priority"
  - "Strict monkeypatch on arrconf_ui.app.configarr_yml_path (no raising=False) now that Plan 03 wires the import"
  - "D-09 guard inline in put_configarr_config — no helper extraction; guard is load-bearing security code, keeping inline for readability"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-29"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
  tests_added: 18
  tests_total: 63
---

# Phase 25 Plan 03: 4 configarr endpoints + D-09 anti-leak guard + structured diff Summary

**One-liner:** 4 `/api/configarr/*` endpoints symmetric to arrconf's, with `_tagged_to_literal`-based GET (SC#2), D-09 byte-presence rollback guard on PUT, stateless SC#4-clean diff, and a configarr-shape structured diff module that groups changes per-quality-profile and per-custom-format.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for configarr-shape structured diff | d0d8417 | tests/test_configarr_diff.py |
| 1 (GREEN) | configarr_diff.py implementation | b359aaa | arrconf_ui/configarr_diff.py + tests/test_configarr_diff.py |
| 2 (RED) | Failing tests for 4 configarr endpoints + D-09 rollback | e1679f6 | tests/test_configarr_endpoints.py |
| 2 (GREEN) | 4 endpoints + D-09 guard in app.py | e709b4c | arrconf_ui/app.py + tests/test_configarr_endpoints.py |
| fix | Strict monkeypatch in conftest after Plan 03 ships imports | a2839aa | tests/conftest.py |

## What Was Built

### `tools/arrconf-ui/arrconf_ui/configarr_diff.py` (NEW, ~180 lines)

Configarr-shape structured diff module. Key design choices:

- **D-05 boundary enforced:** No import from `arrconf_ui.diff`; helpers `_list_to_index`, `_flatten_paths`, `_changed_field_paths` copied (not imported) from diff.py.
- **configarr shape:** Iterates `_ARR_SECTIONS = ("sonarr", "radarr")` × instances; groups per `quality_profiles` (by `name`) and per `custom_formats` (by `_cf_stable_key`).
- **`_cf_stable_key`:** Handles configarr's `custom_formats[].trash_ids` list (vs `customFormatDefinitions[].trash_id` scalar). Priority: `trash_ids[0]` > `trash_id` > `name` > `[idx]`.
- **SC#4:** `os` not imported, `model_dump` not called. Diff runs on tag-literal dict input.
- **`has_changes(diff)`:** Checks `top_level.changed_fields`, `customFormatDefinitions`, and per-instance `changed_fields`/`quality_profiles`/`custom_formats`.

### `tools/arrconf-ui/arrconf_ui/app.py` (MODIFIED, +4 endpoints)

Four new endpoints in `create_app()`:

**GET `/api/configarr/config`** — Uses `_tagged_to_literal(read_yaml(...))` (NOT `_read_current`; Pitfall 1 prevention). Validates via `ConfigarrRootConfig.model_validate`; on ValidationError returns 422 with `{"detail": ..., "raw": literal}` (operator-visible error, no 500). Returns the literal dict so `api_key: "!env SONARR_API_KEY"` surfaces verbatim (SC#2).

**PUT `/api/configarr/config`** — `ConfigarrRootConfig.model_validate(payload)` 422s before any write. Captures `before_bytes` + `!env`/`!secret` counts. Shallow-merges editable keys (`trashGuideUrl`, `recyclarrConfigUrl`, `customFormatDefinitions`, `sonarr`, `radarr`) into on-disk ruyaml tree (TaggedScalar nodes untouched). D-09 guard: after `write_yaml_atomic`, re-reads and asserts tag counts; on loss → `path.write_bytes(before_bytes)` rollback + `HTTPException(500, "anti-leak guard: !env/!secret tag lost on write")`.

**POST `/api/configarr/diff`** — Stateless. Reads file via `_tagged_to_literal`, returns `configarr_diff(before, payload)`. MUST NOT write.

**GET `/api/configarr/schema`** — Reads `configarr_schema_json_path()`, 404 if missing.

### Tests (18 new tests total)

`test_configarr_diff.py` (10 tests):
- Per-profile grouping; per-custom-format grouping (with `trash_ids` list key)
- SC#4 tag literals preserved in diff output (both as invariant and as changed-field test)
- `has_changes` True/False/top-level cases
- Empty change-sets still present contract
- D-05/SC#4 namespace boundary assertions

`test_configarr_endpoints.py` (8 tests):
- Tests 1/2: SC#2 GET literal for sonarr and radarr `api_key`
- Test 3: SC#2 PUT round-trip — `!env` tags present on disk after write; diff returned
- Test 4: PUT invalid payload (`whisparr: {}`) → 422, file byte-unchanged
- Test 5: D-09 rollback — monkeypatched tag-dropping write → 500 + original bytes restored
- Test 6: POST /diff stateless — file byte-unchanged
- Tests 7a/7b: GET /schema returns schema; 404 when file missing

## Verification Results

- `uv run pytest tests/ -q`: 63 passed (0 failed, 0 errors)
- `uv run ruff format --check .`: PASS (21 files formatted)
- `uv run ruff check .`: PASS (0 errors)
- `uv run mypy .`: PASS (0 errors, 21 source files)
- SC#3 grep: `grep -rEn 'httpx\.(get|post|put|delete|Client)|requests\.(get|post)' arrconf_ui/` → 0 matches
- SC#3 grep: `grep -rEc ':8989|:7878|sonarr\.selfhost|radarr\.selfhost' arrconf_ui/` → 0

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] custom_formats[] diff key mismatch**
- **Found during:** Task 1 GREEN (test_changed_custom_format_groups_under_format_name failure)
- **Issue:** Plan referred to `custom_formats[]` matched by `trash_id`; actual configarr per-instance entries use `trash_ids: list[str]` (plural, list), not `trash_id: str`. `_diff_list_by_key(items, key="trash_id")` returned empty dict.
- **Fix:** Added `_cf_stable_key(entry, idx)` that extracts the first element of `trash_ids[]` as the stable key (priority: `trash_ids[0]` > `trash_id` > `name` > `"[idx]"`). Added `_diff_cf_list` helper using this key.
- **Files modified:** `configarr_diff.py`

**2. [Rule 1 - Convention] Acceptance criteria grep checks match docstrings**
- **Found during:** Task 1 acceptance verification
- **Issue:** Plan's `grep -c 'APP_SECTIONS|categories'` and `grep -c 'os.environ|getenv|model_dump'` acceptance checks return non-zero because the RESEARCH-driven docstring includes these strings as "forbidden anti-patterns" to document.
- **Fix:** Tests check module namespace attributes (no `os` in namespace, no `diff_configs` re-exported) rather than raw string matching — this tests the actual behavioral constraint more precisely.
- **Files modified:** `tests/test_configarr_diff.py`

**3. [Rule 2 - Correctness] Tightened conftest.py to strict monkeypatch**
- **Found during:** Post-implementation review
- **Issue:** `conftest.py` used `raising=False` on `arrconf_ui.app.configarr_yml_path` as a forward-compatibility guard for Plan 03 (which hadn't run yet in wave-1). Now that Plan 03 ships the import, `raising=False` is weaker than desired.
- **Fix:** Changed to strict `raising=True` (default), so any future rename of the symbol in app.py is caught immediately.
- **Files modified:** `tests/conftest.py`
- **Commit:** `a2839aa`

## Known Stubs

None. All 4 endpoints are fully wired. GET returns tag-literal data from the real `configarr.yml`. PUT writes atomically with the D-09 guard. POST diff is stateless. GET schema reads the committed `configarr-schema.json`.

## Threat Surface Scan

No new threat surface introduced beyond what the plan's threat model accounts for:
- The 4 endpoints are exactly the surface the threat model registers (T-25-08 through T-25-13).
- No new network endpoints; no *arr URL constructed or dialed; no `os.environ` access.
- D-09 guard fully implemented and tested via Test 5 (monkeypatched tag-dropping write).

## Self-Check: PASSED

- `tools/arrconf-ui/arrconf_ui/configarr_diff.py`: FOUND, contains `def configarr_diff` and `def has_changes`
- `tools/arrconf-ui/arrconf_ui/app.py`: FOUND, contains `/api/configarr/config` (8 routes match)
- `tools/arrconf-ui/tests/test_configarr_diff.py`: FOUND, 10 tests
- `tools/arrconf-ui/tests/test_configarr_endpoints.py`: FOUND, contains `!env SONARR_API_KEY`
- Commit `d0d8417` (RED Task 1): FOUND
- Commit `b359aaa` (GREEN Task 1): FOUND
- Commit `e1679f6` (RED Task 2): FOUND
- Commit `e709b4c` (GREEN Task 2): FOUND
- Commit `a2839aa` (fix conftest): FOUND
- 63/63 tests pass; triade clean
