---
phase: 25-configarr-in-ui-backend
plan: "04"
subsystem: arrconf-ui
tags: [ci, pydantic, configarr, cfgui-07, tdd, tests.yml]
dependency_graph:
  requires: [25-01, 25-02, 25-03]
  provides: [CFGUI-07-gate, configarr-schema-reproducibility-ci-step]
  affects: [tools/arrconf-ui/tests, .github/workflows/tests.yml]
tech_stack:
  added: []
  patterns:
    - "pytest gate against the REAL committed file (no monkeypatch) — validates infrastructure rather than building new code"
    - "schema-reproducibility step mirrors arrconf D-15 pattern: regenerate + git diff --exit-code"
    - "D-08 Option C: pydantic-only CI gate; no configarr/container invocation"
key_files:
  created:
    - tools/arrconf-ui/tests/test_configarr_ci_gate.py
  modified:
    - .github/workflows/tests.yml
decisions:
  - "D-08 Option C honored: configarr v1.28.0 has no offline validate mode; ConfigarrRootConfig.model_validate IS the CI authority — no configarr or *arr container invoked"
  - "No TDD RED/GREEN split needed: test file IS the deliverable (the gate); infrastructure (configarr_config, configarr_io, locator, io) already shipped in Plans 01-03; tests pass immediately"
  - "configarr_schema_gen step placed AFTER 'Run tests' in arrconf-ui-backend job — pydantic gate (Task 1) runs in the existing pytest step, schema drift check is a separate CI gate (Task 2)"
  - "No chart co-bump: plan touches only tools/arrconf-ui/tests/ + .github/workflows/ — CLAUDE.md exception rule applies"
metrics:
  duration: "~3 minutes"
  completed: "2026-05-29"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
  tests_added: 2
  tests_passed: 65
---

# Phase 25 Plan 04: CFGUI-07 CI Gate Summary

**One-liner:** Pydantic-only CI gate (`ConfigarrRootConfig.model_validate` against the REAL committed `configarr.yml`) plus configarr schema-reproducibility step in the `arrconf-ui-backend` job — D-08 Option C, no configarr/container invocation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (CFGUI-07 gate) | Pydantic CI gate test against the REAL configarr.yml | `2ce48ff` | tools/arrconf-ui/tests/test_configarr_ci_gate.py |
| 2 (schema reproducibility) | Schema-reproducibility step in tests.yml arrconf-ui-backend job | `75d5da6` | .github/workflows/tests.yml |

## What Was Built

### `tools/arrconf-ui/tests/test_configarr_ci_gate.py` (NEW, 84 lines)

2 tests forming the CFGUI-07 CI gate:

1. `test_real_configarr_yml_validates`: `ConfigarrRootConfig.model_validate(_tagged_to_literal(read_yaml(configarr_yml_path())))` against the REAL committed `charts/arr-stack/files/configarr.yml` (no monkeypatch). Asserts both `sonarr.main` and `radarr.main` are present with quality profiles. If a hand-edit introduces an unmodeled key or shape error, `extra="forbid"` causes this test to fail in CI before the bad config reaches the cluster.

2. `test_env_tags_survive_into_gate`: asserts `!env SONARR_API_KEY` and `!env RADARR_API_KEY` are literal strings in the input dict after `_tagged_to_literal`. Guards against SC#4 regressions where tag markers are silently dropped (would cause the gate to validate a corrupt input where secret variable names were lost as plain strings).

Module docstring explicitly documents D-08 RESOLVED Option C and forbids future addition of configarr/*arr-container invocation.

### `.github/workflows/tests.yml` (MODIFIED, +9 lines)

New step added to the `arrconf-ui-backend` job, placed after `Run tests`:

```yaml
- name: Verify configarr schema reproducibility (CFGUI-07)
  working-directory: ${{ github.workspace }}
  run: |
    cd tools/arrconf-ui
    uv run python -m arrconf_ui.configarr_schema_gen
    cd ../..
    git diff --exit-code -- schemas/configarr-schema.json \
      || (echo "::error::schemas/configarr-schema.json drift — ..."; exit 1)
```

Mirrors the arrconf D-15 step pattern exactly. The pydantic gate itself runs via the existing `uv run pytest -q` step (Task 1 ships the test). This step guards only against schema drift.

## Verification Results

- `uv run pytest tests/test_configarr_ci_gate.py -q`: 2 passed
- `uv run pytest -q` (full suite): 65 passed (63 prior + 2 new)
- `uv run ruff format --check .`: PASS
- `uv run ruff check .`: PASS
- `uv run mypy .`: PASS (no new errors)
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/tests.yml'))"`: PASS (valid YAML)
- `uv run python -m arrconf_ui.configarr_schema_gen && git diff --exit-code -- schemas/configarr-schema.json`: PASS (reproducible)
- No `charts/arr-stack/values.yaml` drift: PASS (co-bump rule exception applies)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Convention] ruff I001 — import block sorting**
- **Found during:** Task 1 triade check
- **Issue:** ruff I001 flagged unsorted import block in `test_configarr_ci_gate.py` (all `arrconf_ui.*` imports need to be sorted alphabetically)
- **Fix:** `uv run ruff check --fix tests/test_configarr_ci_gate.py` — auto-fixed by ruff
- **Files modified:** `tools/arrconf-ui/tests/test_configarr_ci_gate.py`
- **Commit:** included in `2ce48ff`

### TDD Note

Task 1 is marked `tdd="true"` but no RED/GREEN split was needed: the test file IS the deliverable. All required modules (`configarr_config`, `configarr_io`, `locator`, `io`) were already implemented in Plans 01-03. The tests passed immediately on first run. This is expected — the plan is writing a test-as-gate against existing infrastructure, not building new implementation.

## Known Stubs

None. The gate validates the real file (no hardcoded empty values). No placeholder data.

## Threat Flags

None found. The test file contains no httpx/requests imports, no URL construction, no network calls. The CI step runs only `uv run python -m arrconf_ui.configarr_schema_gen` (local, no network) and `git diff`.

## Self-Check: PASSED

- `tools/arrconf-ui/tests/test_configarr_ci_gate.py`: FOUND
- `.github/workflows/tests.yml` has `Verify configarr schema reproducibility` step: FOUND
- commit `2ce48ff`: FOUND (Task 1)
- commit `75d5da6`: FOUND (Task 2)
- `grep -q 'configarr_yml_path' tools/arrconf-ui/tests/test_configarr_ci_gate.py`: PASS
- `grep -q 'model_validate' tools/arrconf-ui/tests/test_configarr_ci_gate.py`: PASS
- `grep -q 'git diff --exit-code -- schemas/configarr-schema.json' .github/workflows/tests.yml`: PASS
- D-08 Option C — no configarr/*arr invocation: PASS
