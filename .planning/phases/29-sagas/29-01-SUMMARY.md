---
phase: 29-sagas
plan: "01"
subsystem: arrconf
tags: [sagas, intent-config, schema, generators, cli-wiring, co-bump]
dependency_graph:
  requires: []
  provides:
    - SagaEntry locked schema (extra=forbid, kind Literal, movies validator)
    - generate_sagas_desired pure generator (SagasDesiredState)
    - apply --intent option + optional intent.yml load guard
    - schemas/intent-schema.json regenerated
    - arrconf.image.tag co-bumped 0.19.0
  affects:
    - tools/arrconf/arrconf/intent_config.py
    - tools/arrconf/arrconf/generators/sagas.py
    - tools/arrconf/arrconf/generators/__init__.py
    - tools/arrconf/arrconf/__main__.py
    - schemas/intent-schema.json
    - charts/arr-stack/values.yaml
tech_stack:
  added: []
  patterns:
    - Pydantic v2 model_validator(mode="after") for kind-specific field constraints
    - Dataclass container + pure generator function (mirrors categories.py pattern)
    - Typer callback option stash via ctx.obj for optional path passing to subcommands
key_files:
  created:
    - tools/arrconf/arrconf/generators/sagas.py
    - tools/arrconf/tests/test_intent_config_saga_entry.py
    - tools/arrconf/tests/test_generators_sagas.py
  modified:
    - tools/arrconf/arrconf/intent_config.py (SagaEntry locked schema)
    - tools/arrconf/arrconf/generators/__init__.py (new exports)
    - tools/arrconf/arrconf/__main__.py (--intent option + apply load guard)
    - schemas/intent-schema.json (regenerated)
    - charts/arr-stack/values.yaml (co-bump 0.18.0 → 0.19.0)
decisions:
  - "D-02: SagaEntry fields locked: name/kind(Literal)/tmdb_collection/profile/root/items(list[str]|None)"
  - "D-01: generate_sagas_desired is pure (no I/O), mirrors categories.py pattern"
  - "T-29-01: intent_path.exists() guard — absent intent.yml leaves intent_cfg=None, apply proceeds normally"
  - "T-29-02: ConfigError from malformed intent.yml → structured log + exit 2 (no partial apply)"
metrics:
  duration: "296s (~5m)"
  completed: "2026-05-31"
  tasks_completed: 3
  tasks_total: 3
  files_created: 3
  files_modified: 5
---

# Phase 29 Plan 01: SagaEntry Schema Lock + generators/sagas.py + apply --intent wiring Summary

**One-liner:** Locked SagaEntry schema (extra=forbid, kind Literal, movies model_validator) + pure SagasDesiredState generator + optional intent.yml load guarded by `intent_path.exists()` in apply.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Lock SagaEntry schema + regenerate intent-schema.json | 84839bc | intent_config.py, test_intent_config_saga_entry.py, schemas/intent-schema.json |
| 2 | Build pure generators/sagas.py + export | 939619b | generators/sagas.py, generators/__init__.py, test_generators_sagas.py |
| 3 | Wire --intent option + optional intent.yml load in apply + co-bump | 3f052e0 | __main__.py, charts/arr-stack/values.yaml |

## What Was Built

### Task 1: SagaEntry Schema Lock (TDD)

Replaced the P28 `extra="allow"` / `name`-only stub in `intent_config.py` with the full locked schema (D-02):

- `model_config = ConfigDict(extra="forbid")` — unknown keys fail loudly (exit 2)
- `kind: Literal["movies", "series"]` — discriminator field
- `tmdb_collection: int | None` — required when `kind=="movies"` (enforced by validator)
- `profile: str` — required when `kind=="movies"` (enforced by validator)
- `root: str` — required when `kind=="movies"` (enforced by validator)
- `items: list[str] | None` — series BoxSet member titles (optional, `kind=="series"` only)
- `@model_validator(mode="after")` enforcing all three movies constraints
- `schemas/intent-schema.json` regenerated via `arrconf intent-schema-gen`

7 tests pass covering: valid movies saga, missing tmdb_collection, missing profile, missing root, valid series saga, extra-key forbidden, invalid kind.

### Task 2: Pure generators/sagas.py (TDD)

New module `generators/sagas.py` mirroring `categories.py` pattern:

- `SagasDesiredState` dataclass: `radarr_collections: list[dict]`, `series_boxsets: list[SagaEntry]`, `series_tag_titles: list[str]`
- `generate_sagas_desired(sagas: list[SagaEntry]) -> SagasDesiredState` — pure, no I/O, no httpx
- Re-exported from `generators/__init__.py` alongside existing generators

5 tests pass covering: empty, movies-only, series-only, mixed, purity.

### Task 3: apply --intent wiring + co-bump

- `--intent` / `-i` global option added to `app.callback()` (default `/etc/arrconf/intent.yml`)
- `intent_path` stored in `ctx.obj` alongside `config_path`
- In `apply()`: `intent_path.exists()` guard (T-29-01: absent file = no crash, intent_cfg stays None)
- `ConfigError` from malformed intent.yml → structured `intent_config_error` log + exit 2 (T-29-02)
- `log.debug("intent_loaded", sagas=...)` avoids unused-variable lint
- `charts/arr-stack/values.yaml#arrconf.image.tag` co-bumped `0.18.0 → 0.19.0` (minor — new reconciler feature across this phase)

## Verification Results

```
cd tools/arrconf && uv run pytest tests/test_intent_config_saga_entry.py tests/test_generators_sagas.py -q
# 12 passed

cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf
# All checks passed! Success: no issues found in 59 source files

grep -q 'tag: "0.19.0"' charts/arr-stack/values.yaml
# PASS
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Quoted return type annotation in model_validator**
- **Found during:** Task 1 triade check
- **Issue:** `ruff check` flagged `UP037` — quoted `"SagaEntry"` return type is unnecessary with `from __future__ import annotations`
- **Fix:** Changed `-> "SagaEntry":` to `-> SagaEntry:` in `check_kind_constraints`
- **Files modified:** `tools/arrconf/arrconf/intent_config.py`
- **Commit:** 84839bc (same task)

**2. [Rule 1 - Style] Missing blank line after docstring Returns section**
- **Found during:** Task 2 triade check
- **Issue:** `ruff check` flagged `D413` — missing blank line after `Returns` section in `generate_sagas_desired` docstring
- **Fix:** Added trailing blank line inside the `Returns` section
- **Files modified:** `tools/arrconf/arrconf/generators/sagas.py`
- **Commit:** 939619b (same task)

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes at trust boundaries beyond the plan's `<threat_model>`:

| Flag | File | Description |
|------|------|-------------|
| T-29-01 mitigated | `__main__.py` | intent_path.exists() guard — absent file skipped silently |
| T-29-02 mitigated | `__main__.py` | ConfigError from malformed intent.yml → exit 2, no partial apply |

## Known Stubs

None — all fields are properly wired. `intent_cfg` is available in `apply()` for 29-02 (Radarr Collections) and 29-03 (Jellyfin BoxSets) to consume.

## Self-Check: PASSED

All created files exist. All 3 task commits verified in git log.
