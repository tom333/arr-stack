---
phase: 33-configarr-yml-generation
plan: "01"
subsystem: generators
tags: [configarr, generator, intent, quality-profiles, custom-formats, adr-5]
dependency_graph:
  requires:
    - 32-01 (IntentConfig schema with categories[] — CATMIG-01)
    - 32-02 (generate_arrconf_yml + generate CLI — CATMIG-02)
  provides:
    - generate_configarr_yml pure function (generators/configarr.py)
    - ProfileDefinition + CustomFormatRef models (intent_config.py)
    - generate() unconditional 4th emitter for configarr.yml
    - 7 unit tests including ADR-5 no-API-call guard
  affects:
    - 33-02 (content migration — depends on this generator existing)
tech_stack:
  added: []
  patterns:
    - "D-33-04 Option B: profile enum (general/anime/family) mapped to configarr names (MULTi.VF/Anime/Family) at emit time"
    - "D-33-05: per-instance profile routing — only referenced profiles emitted (no dead profiles)"
    - "D-33-06 Option A: custom_formats grouped by trash_ids tuple across profiles"
    - "CFGARR-03 / T-33-01: !env tag reconstruction via regex post-processor"
    - "sort_dict renamed public (from _sort_dict) for cross-module reuse without duplication"
key_files:
  created:
    - tools/arrconf/arrconf/generators/configarr.py
    - tools/arrconf/tests/test_generate_configarr.py
  modified:
    - tools/arrconf/arrconf/intent_config.py (ProfileDefinition + CustomFormatRef + IntentConfig fields)
    - tools/arrconf/arrconf/generators/intent.py (_sort_dict → sort_dict public)
    - tools/arrconf/arrconf/generators/__init__.py (generate_configarr_yml exported)
    - tools/arrconf/arrconf/__main__.py (import + unconditional configarr.yml emitter + co-bump comment)
    - charts/arr-stack/values.yaml (co-bump 0.23.0 → 0.24.0)
decisions:
  - "D-33-04 Option B applied: Profile enum stays general/anime/family; _PROFILE_NAME_MAP translates at emit time"
  - "sort_dict renamed public in intent.py (was _sort_dict); configarr.py imports it directly — no duplication"
  - "ProfileDefinition.body is dict[str, Any] pass-through — configarr validates at apply time (ADR-5: no arrconf-ui models imported)"
  - "generate() configarr.yml emitter is unconditional (mirrors arrconf.yml, D-33-08)"
  - "co-bump 0.23.0 → 0.24.0 (minor: new generator feature)"
metrics:
  duration: "~25 minutes"
  completed_date: "2026-06-06"
  tasks_completed: 3
  files_created: 2
  files_modified: 5
---

# Phase 33 Plan 01: configarr.yml generator (CODE half) Summary

**One-liner:** Pure `generate_configarr_yml` function emitting quality_profiles/custom_formats per category kind with per-profile VOSTFR scores, !env tag reconstruction, and ADR-5 no-API-call guarantee.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | ProfileDefinition + CustomFormatRef models | 03d4931 | `intent_config.py` |
| 2 | generate_configarr_yml + rename sort_dict | 57f0f79 | `generators/configarr.py`, `generators/intent.py` |
| 3 | Wire emitter + export + unit tests + co-bump | 42543bf | `__main__.py`, `generators/__init__.py`, `tests/test_generate_configarr.py`, `values.yaml` |

## What Was Built

### Task 1 — IntentConfig schema extension

Added two new models to `tools/arrconf/arrconf/intent_config.py`:
- `CustomFormatRef(BaseModel, extra="forbid")`: `trash_ids: list[str]` + `score: int | None`
- `ProfileDefinition(BaseModel, extra="forbid")`: `body: dict[str, Any]` (QP pass-through) + `custom_formats: list[CustomFormatRef]`

Added two new fields to `IntentConfig`:
- `profile_definitions: dict[str, ProfileDefinition]` (keyed by configarr name: MULTi.VF/Anime/Family)
- `configarr: dict[str, Any]` (pass-through skeleton for trashGuideUrl, customFormatDefinitions, per-instance base_url/api_key/media_naming/quality_definition)

Both fields use `default_factory=dict` so existing intent.yml without these blocks continues to load during Plan 02 transition.

### Task 2 — Pure generator

Renamed `_sort_dict` → `sort_dict` (public) in `generators/intent.py` and updated its one caller.

Created `tools/arrconf/arrconf/generators/configarr.py` with `generate_configarr_yml(intent_cfg: IntentConfig) -> str`:
- Deep-copies `intent_cfg.configarr` skeleton (never mutates model)
- Routes profiles per instance by `category.kind` (series→sonarr, movies→radarr)
- D-33-04 Option B: `_PROFILE_NAME_MAP = {"general": "MULTi.VF", "anime": "Anime", "family": "Family"}`
- D-33-05: only referenced profiles emitted per instance (no dead profiles)
- D-33-06 Option A: custom_formats grouped by `tuple(sorted(trash_ids))` across profiles
- Serializes via `ruyaml.YAML(typ="safe")` + `sort_dict` (deterministic)
- Post-processes `api_key: '!env VAR'` → `api_key: !env VAR` (CFGARR-03 / T-33-01)
- Zero httpx/ArrApiClient/reconcile imports (ADR-5 / CFGARR-04)

### Task 3 — CLI wiring + export + tests + co-bump

Wired `generate_configarr_yml` into `__main__.py:generate()` as an unconditional 4th emitter (after arrconf.yml, before qbit_manage). Exported from `generators/__init__.py`. 

Created 7 unit tests in `tests/test_generate_configarr.py`:
1. `test_header_present` — GENERATED header present
2. `test_quality_profiles_routed_by_kind` — D-33-05 no dead profiles
3. `test_profile_name_mapping` — D-33-04 Option B mapping
4. `test_vostfr_scores_per_profile` — MULTi.VF=-10000, Anime=50, Family=-10000
5. `test_api_key_is_env_tag_not_secret` — CFGARR-03 / T-33-01 security
6. `test_deterministic` — byte-reproducible output
7. `test_no_api_calls_adr5` — source import guard + runtime monkeypatch (CFGARR-04)

Co-bumped `charts/arr-stack/values.yaml#arrconf.image.tag` from `0.23.0` → `0.24.0` (minor: new generator feature).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ADR-5 test assertion too broad (docstring mentions)**
- **Found during:** Task 3
- **Issue:** The plan specified `assert "httpx" not in src` and `assert "ArrApiClient" not in src` on `inspect.getsource(mod)`. The generator's docstring legitimately documents "No httpx, no ArrApiClient" as description of what is NOT there — this caused the assertion to trip on its own documentation.
- **Fix:** Changed assertions to use `re.search()` patterns targeting actual import statements (`^\s*import httpx\b`, `^\s*from arrconf\.client_base\b`, etc.) and instantiation patterns (`ArrApiClient\s*\(`) rather than substring presence in the full source string.
- **Files modified:** `tools/arrconf/tests/test_generate_configarr.py`
- **Commit:** 42543bf (part of Task 3 commit)

## Verification Results

- `uv run pytest tests/test_generate_configarr.py -q`: 7/7 passed
- Full suite (minus 2 pre-existing flaky order-dependent tests): 529 passed, 2 skipped
- Triade: `ruff format --check` + `ruff check` + `mypy arrconf` — all clean
- ADR-5 guard: `grep -c 'httpx\|ArrApiClient\|reconcile' generators/configarr.py` == 1 (docstring only, no actual import)

## Pre-existing Flaky Tests (not regressions)

Two tests fail intermittently when run in full-suite order due to respx state leakage (documented in project MEMORY.md as pre-existing):
- `tests/test_client_base_4xx_logging.py::test_4xx_emits_client_4xx_warning_with_body_excerpt`
- `tests/test_reconcilers_jellyfin.py::test_reconcile_jellyfin_step_order_invariant`

Both pass in isolation. Not caused by this plan.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced by this plan. The generator is a pure function (no I/O at all). The only security-relevant surface is the existing T-33-01 (`!env` handling) which is mitigated by the regex post-processor and tested by `test_api_key_is_env_tag_not_secret`.

## Self-Check: PASSED
