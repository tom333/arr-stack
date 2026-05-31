---
phase: 25-configarr-in-ui-backend
verified: 2026-05-29T00:00:00Z
status: passed
score: 13/13 must-haves verified
overrides_applied: 0
re_verification: null
gaps: []
deferred: []
human_verification: []
---

# Phase 25: configarr-in-UI backend Verification Report

**Phase Goal:** The arrconf-ui backend can read, validate, diff, and write `configarr.yml` with the same safety guarantees as `arrconf.yml`, including zero risk of secret leakage via `!env`/`!secret` tag drop.
**Verified:** 2026-05-29
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                         | Status     | Evidence                                                                                                                                                                                                  |
|----|---------------------------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | Round-trip test loads real configarr.yml, writes to temp, asserts both `!env` tags byte-present (SC#1)       | ✓ VERIFIED | `tests/test_configarr_leak.py` Tests 1-5 pass. Test 3 (`test_roundtrip_preserves_env_tags_byte_for_byte`) performs the exact round-trip byte assertion. 15 tests pass in the combined configarr test suite. |
| 2  | `GET /api/configarr/config` returns `api_key` as literal `!env SONARR_API_KEY`, never bare name (SC#2)       | ✓ VERIFIED | `app.py:176-203` — handler uses `_tagged_to_literal(read_yaml(path))`, explicitly NOT `_read_current`. Endpoint tests Test 1 and Test 2 assert the literal. 65 tests pass overall.                       |
| 3  | `PUT /api/configarr/config` D-09 anti-leak runtime guard: re-reads after write, rolls back on tag loss (SC#2/D-09) | ✓ VERIFIED | `app.py:222-253` — counts `!env` + `!secret` before write, re-reads after, calls `path.write_bytes(before_bytes)` on loss + raises HTTP 500. Endpoint test Test 5 asserts rollback works.                |
| 4  | `POST /api/configarr/diff` uses `_tagged_to_literal` path, never `_read_current` JSON-coercion (SC#4)        | ✓ VERIFIED | `app.py:268-271` — `before = _tagged_to_literal(read_yaml(path))`. `configarr_diff.py` never imports `_read_current`, has no `model_dump`, no `os.environ`. Test SC#4 in `test_configarr_diff.py`.       |
| 5  | `GET /api/configarr/schema` returns JSON Schema with `api_key readOnly: true` (SC#3)                         | ✓ VERIFIED | `schemas/configarr-schema.json` has `"readOnly": true` on `api_key`, `media_naming`, `quality_definition`. Endpoint test Test 7a asserts `$schema` presence. `configarr_schema_gen.py` generates reproducibly. |
| 6  | No `*arr` API URL constructed or dialed anywhere in arrconf-ui source (SC#3 / ADR-5 boundary)                 | ✓ VERIFIED | `grep -rn "httpx\|requests\|aiohttp"` over `arrconf_ui/` returns zero results. No `:8989`, `:7878`, or `sonarr.selfhost` patterns in any `arrconf_ui/*.py` file (only appears in test fixture assertion and in `diff.py` comments, not as live URLs). |
| 7  | `ConfigarrRootConfig` lives in `tools/arrconf-ui/` ONLY, never `tools/arrconf/` (ADR-5)                      | ✓ VERIFIED | `grep -rn "ConfigarrRootConfig" tools/arrconf/` returns zero results. The class is defined in `tools/arrconf-ui/arrconf_ui/configarr_config.py`.                                                          |
| 8  | `ConfigarrRootConfig.model_validate` against the real committed `configarr.yml` succeeds (CFGUI-02)          | ✓ VERIFIED | `test_configarr_ci_gate.py` Test 1 validates the real file (no monkeypatch). Test passes with 2/2. `extra="forbid"` model, 282-line implementation.                                                       |
| 9  | `_tagged_to_literal` reconstructs `!env X` literal from `TaggedScalar`, never drops the tag (SC#4 Pitfall 1)  | ✓ VERIFIED | `configarr_io.py` — 41-line implementation, no `json.dumps` in code (docstring only documents why to avoid it). Test 4 in `test_configarr_leak.py` proves the JSON-coercion shortcut would strip the tag. |
| 10 | Locator resolves `configarr_yml_path()` and `configarr_schema_json_path()` correctly                          | ✓ VERIFIED | `locator.py:37-44` — two functions resolving `repo_root() / "charts/arr-stack/files/configarr.yml"` and `repo_root() / "schemas/configarr-schema.json"`. Locator tests pass.                             |
| 11 | CI gate is pydantic-only (D-08 Option C): no `*arr` containers, no configarr invocation (CFGUI-07)           | ✓ VERIFIED | `tests.yml` arrconf-ui-backend job: `uv run pytest -q` runs `test_configarr_ci_gate.py` as part of the standard test run. `grep -c 'raydak-labs/configarr\|sonarrEnabled\|docker run' tests.yml` = 0.     |
| 12 | Schema-reproducibility CI step present in arrconf-ui-backend job (`git diff --exit-code -- schemas/configarr-schema.json`) | ✓ VERIFIED | `tests.yml:120-127` — "Verify configarr schema reproducibility (CFGUI-07)" step: `uv run python -m arrconf_ui.configarr_schema_gen` + `git diff --exit-code`.                                            |
| 13 | Co-bump exception honored: `charts/arr-stack/values.yaml#arrconf.image.tag` unchanged by phase 25            | ✓ VERIFIED | `git log -- charts/arr-stack/values.yaml` shows last modification was `cdaf7f6` (phase 24). None of the 8 phase-25 commits (`75d5da6`..`4680696`) touch `values.yaml`. Tag remains `0.17.0`.              |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact                                                      | Expected                                               | Status     | Details                                               |
|---------------------------------------------------------------|--------------------------------------------------------|------------|-------------------------------------------------------|
| `tools/arrconf-ui/arrconf_ui/configarr_io.py`                 | `_tagged_to_literal` tag-preserving read helper        | ✓ VERIFIED | 41 lines; `TaggedScalar` import; no `json.dumps` in code; reconstructs `f"{node.tag.value} {node.value}"` |
| `tools/arrconf-ui/arrconf_ui/locator.py`                      | `configarr_yml_path()` + `configarr_schema_json_path()` | ✓ VERIFIED | Both functions present at lines 37-44                 |
| `tools/arrconf-ui/tests/test_configarr_leak.py`               | Task-zero anti-leak round-trip test (5 tests)          | ✓ VERIFIED | 130 lines; 5 tests; contains `!env SONARR_API_KEY` assertion literal; all 5 pass |
| `tools/arrconf-ui/tests/conftest.py`                          | `sandboxed_configarr_yml` double-monkeypatch fixture   | ✓ VERIFIED | Lines 39-51; patches both `arrconf_ui.locator.configarr_yml_path` and `arrconf_ui.app.configarr_yml_path` |
| `tools/arrconf-ui/arrconf_ui/configarr_config.py`             | `ConfigarrRootConfig` with `extra="forbid"` on every model | ✓ VERIFIED | 282 lines; `ConfigarrRootConfig` + 9 sub-models; all have `model_config = ConfigDict(extra="forbid")`; `api_key = Field(json_schema_extra={"readOnly": True})` |
| `tools/arrconf-ui/arrconf_ui/configarr_schema_gen.py`         | `Draft202012Generator` + reproducible schema writer    | ✓ VERIFIED | `Draft202012Generator` class; `write_configarr_schema`; `sort_keys=True`; `__main__` entry |
| `schemas/configarr-schema.json`                               | Generated schema with `"readOnly": true` markers       | ✓ VERIFIED | `api_key`, `media_naming`, `quality_definition` all have `"readOnly": true`; `"$schema": "https://json-schema.org/draft/2020-12/schema"` |
| `tools/arrconf-ui/arrconf_ui/configarr_diff.py`               | Configarr-shape structured diff, tag-literal preserving | ✓ VERIFIED | 262 lines; `def configarr_diff`; no `arrconf_ui.diff` import; no `model_dump`; no `os.environ` |
| `tools/arrconf-ui/arrconf_ui/app.py`                          | 4 `/api/configarr/*` endpoints + D-09 guard            | ✓ VERIFIED | All 4 endpoints at lines 176/205/262/273; D-09 byte-count guard + `write_bytes` rollback at lines 222-253 |
| `tools/arrconf-ui/tests/test_configarr_endpoints.py`          | 8 endpoint tests including D-09 rollback test          | ✓ VERIFIED | Tests 1-7 (7b as separate) cover GET literal, PUT round-trip, 422, D-09 rollback, diff stateless, schema 404 |
| `tools/arrconf-ui/tests/test_configarr_ci_gate.py`            | Pydantic CI gate against real committed configarr.yml  | ✓ VERIFIED | 2 tests; validates real file via `configarr_yml_path()` (no monkeypatch); `model_validate` present; D-08 docstring |
| `.github/workflows/tests.yml`                                 | `Verify configarr schema reproducibility` step in arrconf-ui-backend job | ✓ VERIFIED | Lines 120-127; regenerates + `git diff --exit-code -- schemas/configarr-schema.json` |

### Key Link Verification

| From                                          | To                                      | Via                                        | Status     | Details                                                  |
|-----------------------------------------------|-----------------------------------------|--------------------------------------------|------------|----------------------------------------------------------|
| `configarr_io.py`                             | `ruyaml.comments.TaggedScalar`          | `isinstance` check + `f"{node.tag.value} {node.value}"` | ✓ WIRED    | Line 34-35; `from ruyaml.comments import TaggedScalar`   |
| `test_configarr_leak.py`                      | `arrconf_ui.io.read_yaml` + `write_yaml_atomic` | round-trip byte assertion          | ✓ WIRED    | Imports both; test 3 does the full cycle                 |
| `app.py GET /api/configarr/config`            | `configarr_io._tagged_to_literal`       | `read_yaml → _tagged_to_literal → ConfigarrRootConfig.model_validate` | ✓ WIRED | Lines 189-190; explicit comment "NOT _read_current" |
| `app.py PUT /api/configarr/config`            | D-09 byte-presence guard                | `before_bytes → write → re-read count → write_bytes rollback` | ✓ WIRED | Lines 223-253; both `expected_env`/`expected_secret` counts checked |
| `test_configarr_ci_gate.py`                   | real `charts/arr-stack/files/configarr.yml` | `_tagged_to_literal(read_yaml(configarr_yml_path())) → model_validate` | ✓ WIRED | No monkeypatch on path; validates the committed file     |
| `tests.yml arrconf-ui-backend job`            | `schemas/configarr-schema.json`         | `python -m arrconf_ui.configarr_schema_gen` + `git diff --exit-code` | ✓ WIRED | Lines 120-127                                           |
| `configarr_diff.py`                           | tag-literal before/after snapshots      | `configarr_diff(before_literal, payload)` — no `model_dump` | ✓ WIRED | `before` must be from `_tagged_to_literal`; `model_dump` prohibited in module docstring + implementation |

### Data-Flow Trace (Level 4)

| Artifact                         | Data Variable   | Source                                        | Produces Real Data | Status     |
|----------------------------------|-----------------|-----------------------------------------------|--------------------|------------|
| `app.py GET /api/configarr/config` | `literal`     | `_tagged_to_literal(read_yaml(configarr_yml_path()))` | Yes — reads `charts/arr-stack/files/configarr.yml` | ✓ FLOWING  |
| `app.py PUT /api/configarr/config` | `before_bytes` | `configarr_yml_path().read_bytes()`          | Yes — real file bytes | ✓ FLOWING  |
| `app.py POST /api/configarr/diff`  | `before`       | `_tagged_to_literal(read_yaml(path))`         | Yes — real file   | ✓ FLOWING  |
| `app.py GET /api/configarr/schema` | return value   | `configarr_schema_json_path().read_text()`   | Yes — committed schema | ✓ FLOWING  |

### Behavioral Spot-Checks

| Behavior                                          | Command                                                                                               | Result                  | Status  |
|---------------------------------------------------|-------------------------------------------------------------------------------------------------------|-------------------------|---------|
| 5 anti-leak tests pass                            | `cd tools/arrconf-ui && uv run pytest tests/test_configarr_leak.py -q`                               | 5 passed in 0.3s        | ✓ PASS  |
| 2 CI gate tests pass                              | `cd tools/arrconf-ui && uv run pytest tests/test_configarr_ci_gate.py -q`                            | 2 passed in 0.3s        | ✓ PASS  |
| 8 endpoint tests pass (incl. D-09 rollback)       | `cd tools/arrconf-ui && uv run pytest tests/test_configarr_endpoints.py -q`                          | 8 passed in 0.7s        | ✓ PASS  |
| All 65 arrconf-ui backend tests pass              | `cd tools/arrconf-ui && uv run pytest -q`                                                             | 65 passed in 2.15s      | ✓ PASS  |
| Triade clean (ruff format/check + mypy)           | `cd tools/arrconf-ui && uv run ruff format --check . && uv run ruff check . && uv run mypy .`        | All clean, 0 issues     | ✓ PASS  |
| Schema has readOnly on api_key/media_naming/quality_definition | python3 schema inspection                                                             | All 3 are `True`        | ✓ PASS  |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                          | Status       | Evidence                                                          |
|-------------|-------------|------------------------------------------------------------------------------------------------------|--------------|-------------------------------------------------------------------|
| CFGUI-01    | 25-01, 25-03 | Opérateur charge/édite/sauvegarde configarr.yml avec round-trip ruyaml préservant `!env`/`!secret` | ✓ SATISFIED  | Task-zero anti-leak test (Plan 01) + GET/PUT endpoints (Plan 03) + D-09 rollback guard |
| CFGUI-02    | 25-02       | `ConfigarrRootConfig` pydantic model (in arrconf-ui only) + JSON Schema with readOnly markers        | ✓ SATISFIED  | `configarr_config.py` (282 lines, all models `extra="forbid"`); `schemas/configarr-schema.json` with `readOnly: true` on api_key/media_naming/quality_definition |
| CFGUI-03    | 25-03       | Backend exposes GET/PUT config + GET schema + POST diff endpoints (symmetric to arrconf endpoints)   | ✓ SATISFIED  | All 4 endpoints registered in `app.py`; 8 endpoint tests pass    |
| CFGUI-07    | 25-04       | CI gate validates configarr.yml (D-08 RESOLVED → pydantic-only, Option C; no *arr containers, no configarr invocation) | ✓ SATISFIED | `test_configarr_ci_gate.py` runs in `uv run pytest -q`; schema-reproducibility step in `tests.yml:120-127`; no configarr/arr invocation confirmed |

**Note on CFGUI-07 requirement text:** The original `REQUIREMENTS.md` text for CFGUI-07 still states "via le dry-run/validation natif de configarr (validateur faisant autorité, pas la couche pydantic de l'UI)" — this predates the D-08 escalation (2026-05-29) where the user explicitly chose Option C (pydantic-only). The ROADMAP.md `Phase 25 Success Criteria #5` correctly reflects the resolved decision. The implementation is correct per the resolved decision; the REQUIREMENTS.md wording is a documentation artifact, not an implementation gap.

### Anti-Patterns Found

| File                  | Line | Pattern                              | Severity | Impact  |
|-----------------------|------|--------------------------------------|----------|---------|
| None found            | —    | —                                    | —        | —       |

No TODO/FIXME/placeholder comments found. No `return null` / `return []` stubs. No hardcoded empty data that flows to rendering. `json.dumps` in `configarr_io.py` appears only in a docstring (line 6) explaining why the pattern must NOT be used — not in executable code.

### Human Verification Required

None. All success criteria are verifiable programmatically and all tests pass.

### Gaps Summary

No gaps. All 13 must-haves verified. The phase goal is fully achieved:

- SC#1 (task-zero anti-leak): `test_configarr_leak.py` ships 5 tests; round-trip byte assertion passes.
- SC#2 (GET/PUT round-trip): 4 endpoints registered; PUT has D-09 runtime guard with `write_bytes` rollback.
- SC#3 (schema + ADR-5 boundary): `schemas/configarr-schema.json` has `readOnly: true` on `api_key`; zero HTTP client construction in `arrconf_ui/`; `ConfigarrRootConfig` lives exclusively in `tools/arrconf-ui/`.
- SC#4 (diff tag-literal): `POST /api/configarr/diff` uses `_tagged_to_literal`, never `_read_current`; `configarr_diff.py` has no `model_dump`, no `os.environ`.
- SC#5 (CI gate, D-08 Option C): `test_configarr_ci_gate.py` runs via `uv run pytest -q`; schema-reproducibility step in `tests.yml`; zero `*arr` container or configarr invocation.
- Co-bump exception: `charts/arr-stack/values.yaml` tag `0.17.0` untouched by all 8 phase-25 commits.

---

_Verified: 2026-05-29_
_Verifier: Claude (gsd-verifier)_
