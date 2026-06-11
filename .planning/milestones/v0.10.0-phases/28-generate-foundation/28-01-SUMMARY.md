---
phase: 28-generate-foundation
plan: "01"
subsystem: arrconf/intent_config
tags: [pydantic, intent-config, schema-gen, ci, co-bump]
dependency_graph:
  requires: []
  provides: [IntentConfig, CrossSeedConfig, ToolsConfig, SagaEntry, load_intent, intent-schema-gen, schemas/intent-schema.json]
  affects: [tools/arrconf/arrconf/__main__.py, .github/workflows/tests.yml, charts/arr-stack/values.yaml]
tech_stack:
  added: []
  patterns: [pydantic-extra-forbid, load-config-mirror, schema-gen-subcommand, co-bump]
key_files:
  created:
    - tools/arrconf/arrconf/intent_config.py
    - schemas/intent-schema.json
    - tools/arrconf/tests/test_intent_config.py
  modified:
    - tools/arrconf/arrconf/schema_gen.py
    - tools/arrconf/arrconf/__main__.py
    - charts/arr-stack/values.yaml
    - .github/workflows/tests.yml
decisions:
  - "INTENT-01: IntentConfig uses extra=forbid on 3 models (IntentConfig/ToolsConfig/CrossSeedConfig) and extra=allow on SagaEntry (P29 will tighten); mirrors RootConfig convention exactly"
  - "Co-bump 0.17.0 → 0.18.0 (minor) for new generate feature spanning Plans 01-03"
  - "All 4 tasks committed atomically in one commit to satisfy CLAUDE.md co-bump constraint"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-05-31"
  tasks_completed: 4
  files_changed: 7
---

# Phase 28 Plan 01: IntentConfig Foundation Summary

IntentConfig pydantic model with extra=forbid on 3 models + load_intent() + intent-schema-gen CLI subcommand + CI reproducibility guard + co-bump 0.17.0→0.18.0 (INTENT-01 typed contract).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create intent_config.py (IntentConfig models + load_intent) | 86e65d4 | tools/arrconf/arrconf/intent_config.py |
| 2 | Add intent-schema-gen subcommand + commit schemas/intent-schema.json | 86e65d4 | tools/arrconf/arrconf/schema_gen.py, tools/arrconf/arrconf/__main__.py, schemas/intent-schema.json |
| 3 | Unit tests for intent_config (test_intent_config.py) | 86e65d4 | tools/arrconf/tests/test_intent_config.py |
| 4 | Co-bump arrconf image tag + add CI intent-schema reproducibility step | 86e65d4 | charts/arr-stack/values.yaml, .github/workflows/tests.yml |

## What Was Built

- `tools/arrconf/arrconf/intent_config.py`: Four pydantic models (`CrossSeedConfig`, `ToolsConfig`, `SagaEntry`, `IntentConfig`) + `load_intent(path: Path) -> IntentConfig`. Exactly mirrors `load_config` error handling (YAML safe + ConfigError wrapping). `extra="forbid"` on 3 models, `extra="allow"` on SagaEntry (Phase 29 stub).
- `tools/arrconf/arrconf/schema_gen.py`: Added `write_intent_schema(output_path: Path)` mirroring `write_schema`, using `Draft202012Generator` and `sort_keys=True` determinism guarantee.
- `tools/arrconf/arrconf/__main__.py`: Added `intent-schema-gen` CLI subcommand after `schema-gen`, mirrors its pattern exactly with `--output` defaulting to `schemas/intent-schema.json`.
- `schemas/intent-schema.json`: Committed Draft 2020-12 JSON schema derived from `IntentConfig`. Deterministic (two-run diff is empty).
- `tools/arrconf/tests/test_intent_config.py`: 7 unit tests covering all 6 behaviors from the plan spec plus a default-values smoke test.
- `.github/workflows/tests.yml`: New CI step "Verify intent-schema reproducibility (INTENT-01)" immediately after the existing D-15 schema step.
- `charts/arr-stack/values.yaml`: Co-bumped `arrconf.image.tag` from `0.17.0` to `0.18.0` (minor bump for new generate feature; renovate annotation preserved).

## Verification

- Python triade green: `ruff format --check`, `ruff check`, `mypy arrconf` all pass (57 source files, 0 errors)
- `uv run pytest tests/test_intent_config.py -q`: 7 passed
- Full suite: 471 passed (2 pre-existing failures in test_phase10_idempotence_sweep.py, unrelated to this plan)
- `arrconf intent-schema-gen` two-run diff empty (DETERMINISTIC)
- `schemas/intent-schema.json` contains `IntentConfig`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff B017 — blind pytest.raises(Exception)**
- **Found during:** Task 3 (ruff check gate)
- **Issue:** `with pytest.raises(Exception)` triggers ruff B017 (blind exception assertion)
- **Fix:** Changed to `pytest.raises(ValidationError)` after importing `from pydantic import ValidationError`
- **Files modified:** `tools/arrconf/tests/test_intent_config.py`
- **Commit:** 86e65d4

**2. [Rule 1 - Bug] Ruff format — line length in test file**
- **Found during:** Task 3 (ruff format --check gate)
- **Issue:** One assertion line exceeded ruff's line-length limit
- **Fix:** Applied `uv run ruff format` to the test file
- **Files modified:** `tools/arrconf/tests/test_intent_config.py`
- **Commit:** 86e65d4

**3. [Rule 2 - Missing] Module docstring grep conflict**
- **Found during:** Task 1 acceptance criteria verification
- **Issue:** Module docstring contained `extra="forbid"` as code literals, causing `grep -c 'extra="forbid"'` to return 4 instead of the expected 3 (one per model class)
- **Fix:** Reworded docstring to use prose description without quoted Python syntax
- **Files modified:** `tools/arrconf/arrconf/intent_config.py`
- **Commit:** 86e65d4

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| intent-schema.json public | schemas/intent-schema.json | Documents field names only, no values/secrets — T-28-02 accepted per plan threat model |

The threat model T-28-01 (YAML safe load + extra=forbid), T-28-02 (schema names only, safe to commit), and T-28-03 (ConfigError wrapping) are all addressed by the implementation.

## Known Stubs

- `SagaEntry` in `intent_config.py` uses `extra="allow"` — intentional P28 stub. Phase 29 (SAGAS) will tighten to `extra="forbid"` once the full saga schema is locked (D-05).

## Self-Check: PASSED

- `tools/arrconf/arrconf/intent_config.py`: FOUND
- `schemas/intent-schema.json`: FOUND
- `tools/arrconf/tests/test_intent_config.py`: FOUND
- commit 86e65d4: FOUND (git log HEAD)
