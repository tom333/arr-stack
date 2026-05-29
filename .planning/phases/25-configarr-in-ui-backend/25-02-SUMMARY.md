---
phase: 25-configarr-in-ui-backend
plan: "02"
subsystem: arrconf-ui
tags: [pydantic, schema, configarr, tdd, arrconf-ui]
dependency_graph:
  requires: []
  provides: [ConfigarrRootConfig, configarr_schema_gen, schemas/configarr-schema.json]
  affects: [tools/arrconf-ui/arrconf_ui, schemas]
tech_stack:
  added: []
  patterns:
    - "extra=forbid on every pydantic model class (mirrors arrconf config.py pattern)"
    - "Field(json_schema_extra={'readOnly': True}) for read-only schema markers"
    - "@model_validator(mode='after') for conditional-required (upgrade block)"
    - "Draft202012Generator clone from arrconf/schema_gen.py (local sibling, ADR-5)"
    - "sort_keys=True reproducible JSON Schema write for CI diff gate"
key_files:
  created:
    - tools/arrconf-ui/arrconf_ui/configarr_config.py
    - tools/arrconf-ui/arrconf_ui/configarr_schema_gen.py
    - schemas/configarr-schema.json
    - tools/arrconf-ui/tests/test_configarr_model.py
  modified: []
decisions:
  - "N815 noqa: camelCase field names (trashGuideUrl, recyclarrConfigUrl, customFormatDefinitions, includeCustomFormatWhenRenaming) preserved verbatim from configarr.yml schema; noqa suppresses ruff N815 warning — API contract trumps Python naming convention"
  - "MediaNaming is ONE type with all sonarr+radarr keys Optional (Pitfall 5) — mirrors configarr's single MediaNamingType"
  - "_tagged_to_literal defined locally in test file (not imported from configarr_io.py) — Plan 01 runs in parallel wave 1; self-contained test avoids cross-plan import dependency during parallel execution"
  - "duplicate model_config removed in ResetUnmatchedScores — ruff auto-fixed; populate_by_name=True added to support 'except' alias"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-29"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 0
  tests_added: 8
  tests_passed: 40
---

# Phase 25 Plan 02: ConfigarrRootConfig model + JSON Schema Summary

**One-liner:** Fully-typed `ConfigarrRootConfig` pydantic model with `extra="forbid"`, `readOnly` markers on `api_key`/`media_naming`/`quality_definition`, plus reproducible Draft 2020-12 JSON Schema with 3 `readOnly: true` markers — all in `tools/arrconf-ui/` only (ADR-5).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for ConfigarrRootConfig | `483df3f` | tests/test_configarr_model.py |
| 1 (GREEN) | ConfigarrRootConfig model implementation | `5419223` | arrconf_ui/configarr_config.py + tests/test_configarr_model.py |
| 2 | Local schema generator + committed schema | `be498d1` | arrconf_ui/configarr_schema_gen.py + schemas/configarr-schema.json |

## What Was Built

### `tools/arrconf-ui/arrconf_ui/configarr_config.py` (NEW, 282 lines)

10 model classes, all with `model_config = ConfigDict(extra="forbid")`:

- `EpisodesNaming` / `MovieNaming` — sub-models for `MediaNaming`
- `MediaNaming` — ONE type covering both sonarr (series/season/episodes) and radarr (folder/movie) keys; all fields Optional (Pitfall 5)
- `QualityDefQuality` / `QualityDefinition` — readOnly, fully typed per D-03
- `ResetUnmatchedScores` / `Upgrade` — quality profile sub-models; `Upgrade` carries `@model_validator(mode="after")` enforcing `until_quality`+`until_score` when `allowed=True` (Pitfall 3)
- `QualityGroup` / `QualityProfile` — editable
- `AssignScoresTo` / `CustomFormat` — editable; deprecated `quality_profiles` key intentionally NOT modeled
- `Specification` / `CustomFormatDefinition` — `fields: dict[str, Any]` accepts str and int values (Pitfall 4)
- `ArrInstance` — `base_url` stored/echoed verbatim NEVER dialed (SC#3); `api_key`, `media_naming`, `quality_definition` marked `Field(json_schema_extra={"readOnly": True})`
- `ConfigarrRootConfig` — 5 real-file top-level keys only (Assumption A1)

### `tools/arrconf-ui/arrconf_ui/configarr_schema_gen.py` (NEW, 62 lines)

- `Draft202012Generator` — clones `arrconf/schema_gen.py` pattern locally (ADR-5: does NOT import from arrconf)
- `write_configarr_schema(output_path)` — reproducible `json.dumps(..., sort_keys=True) + "\n"`
- `if __name__ == "__main__":` guard for CLI regen (`python -m arrconf_ui.configarr_schema_gen`)

### `schemas/configarr-schema.json` (NEW, generated)

- 3x `"readOnly": true` (api_key, media_naming, quality_definition in ArrInstance)
- `"$schema": "https://json-schema.org/draft/2020-12/schema"` dialect
- Reproducible: byte-identical on regeneration (`git diff --exit-code` exits 0)

### `tools/arrconf-ui/tests/test_configarr_model.py` (NEW, 8 tests)

All 8 pass (6 required by plan + 2 extra for upgrade allowed=true/false cases):
1. Real-file validation against `charts/arr-stack/files/configarr.yml`
2. extra=forbid rejects `whisparr: {}` top key
3. extra=forbid rejects `delete_unmanaged_custom_formats` per-instance key
4. upgrade allowed=true WITHOUT until_quality/until_score → ValidationError
5. upgrade allowed=false without until fields → validates OK
6. specifications polymorphism: str and int fields.value both validate
7. MediaNaming sonarr keys (series/season/episodes) validates
8. MediaNaming radarr keys (folder/movie) validates

## Verification Results

- `uv run pytest tests/test_configarr_model.py -q`: 8 passed
- `uv run pytest -q` (full suite): 40 passed (32 original + 8 new)
- `uv run ruff format --check .`: PASS
- `uv run ruff check .`: PASS (4 N815 noqa suppressed for camelCase API keys)
- `uv run mypy .`: PASS (no new errors)
- `git diff --exit-code -- schemas/configarr-schema.json`: PASS (reproducible)
- `git diff --exit-code -- tools/arrconf/arrconf/schema_gen.py`: PASS (ADR-5 untouched)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Duplicate `model_config` in `ResetUnmatchedScores`**
- **Found during:** Task 1 GREEN implementation
- **Issue:** `model_config` was defined twice; second definition with `populate_by_name=True` overwrote the first, but ruff auto-fixed the import ordering
- **Fix:** Collapsed to single `model_config = ConfigDict(extra="forbid", populate_by_name=True)` with alias on `except_` field
- **Files modified:** `configarr_config.py`

**2. [Rule 2 - Convention] N815 noqa inline suppression for camelCase field names**
- **Found during:** Task 1 triade check
- **Issue:** ruff N815 warns on camelCase class-scope variables (`trashGuideUrl`, `recyclarrConfigUrl`, `customFormatDefinitions`, `includeCustomFormatWhenRenaming`)
- **Fix:** Added `# noqa: N815` inline — these names are the external API contract (configarr.yml keys) and must NOT be renamed
- **Files modified:** `configarr_config.py`

**3. [Wave-1 parallel execution] `_tagged_to_literal` defined locally in test**
- **Context:** Plan 01 (parallel wave 1) ships `configarr_io.py` with `_tagged_to_literal`. Plan 02 tests reference it.
- **Decision:** Defined a local copy in `test_configarr_model.py` rather than importing from `arrconf_ui.configarr_io` — makes the test file self-contained and avoids a cross-plan import failure if Plan 01 hasn't merged yet.
- **Impact:** After merge, Plan 01 will provide the canonical module; tests can optionally be updated to import from there in Plan 03/04 review.

## Known Stubs

None. The model validates the real `configarr.yml` without errors. No placeholder data or mock responses.

## Threat Flags

None found. The model file contains no httpx/requests imports, no URL construction, and no network calls. `base_url` is stored as a plain `str` field with an inline `# NEVER dialed` comment satisfying T-25-04.

## Self-Check: PASSED

- `configarr_config.py`: FOUND
- `configarr_schema_gen.py`: FOUND
- `schemas/configarr-schema.json`: FOUND
- `test_configarr_model.py`: FOUND
- commit `483df3f`: FOUND (RED gate)
- commit `5419223`: FOUND (GREEN gate)
- commit `be498d1`: FOUND (schema task)
