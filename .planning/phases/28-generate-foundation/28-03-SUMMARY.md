---
phase: 28-generate-foundation
plan: "03"
subsystem: arrconf-cli
tags: [generate, intent, cli, cross-seed, idempotence]
dependency_graph:
  requires: [28-01, 28-02]
  provides: [arrconf-generate-cmd, generate-cli-tests]
  affects: [arrconf/__main__.py, tests/test_generate_cmd.py, tests/test_cli.py]
tech_stack:
  added: []
  patterns: [typer-subcommand, ConfigError-exit2, check-mode-exit1]
key_files:
  created:
    - tools/arrconf/tests/test_generate_cmd.py
  modified:
    - tools/arrconf/arrconf/__main__.py
    - tools/arrconf/tests/test_cli.py
decisions:
  - "generate subcommand decoupled from apply per D-06 — apply code not modified"
  - "--check mode exits 1 on drift (absent file counts as drift), 0 on sync"
  - "ConfigError from load_intent maps to exit 2 matching all other config errors"
  - "help-list test renamed test_help_lists_subcommands (count changed) with generate added"
metrics:
  duration_minutes: 15
  completed: "2026-05-31"
  tasks_completed: 3
  files_changed: 3
---

# Phase 28 Plan 03: generate CLI subcommand + --check drift mode — Summary

Wire the `generate` CLI subcommand to `__main__.py`: bare `arrconf generate` writes `config.js` under `charts/arr-stack/files/cross-seed/`; `--check` exits 1 on drift for CI gate (INTENT-03, D-07); `ConfigError` → exit 2; decoupled from `apply` (D-06).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add generate @app.command to __main__.py | d2e543f | tools/arrconf/arrconf/__main__.py |
| 2 | CLI tests + update help-list test | 2f98f5b | tools/arrconf/tests/test_generate_cmd.py, tools/arrconf/tests/test_cli.py |
| 3 | Co-bump arrconf image tag | (no-op) | charts/arr-stack/values.yaml already at 0.18.0 from waves 1-2 |

## What Was Built

**Task 1 — generate subcommand (`__main__.py`):**
- Added `from arrconf.generators.intent import generate_cross_seed` and `from arrconf.intent_config import load_intent` imports (sorted per ruff I001)
- Added `@app.command() def generate(intent, output_dir, check)` after `intent_schema_gen_cmd`
- `load_intent(intent)` wrapped in `try/except ConfigError` → `typer.Exit(code=2)`
- Guard `if intent_cfg.tools.cross_seed is not None:` narrows `CrossSeedConfig | None` for mypy
- Write mode: `target.parent.mkdir(parents=True, exist_ok=True)` + `target.write_text()`
- Check mode: compare `target.read_text()` to `rendered`; `drift = True` if absent or different; `typer.Exit(code=1 if drift else 0)`
- `apply` command not modified — D-06 decoupling preserved

**Task 2 — CLI tests (`test_generate_cmd.py`) + updated help-list:**
- 6 test cases covering all behaviors: help flags, write exit 0, missing intent exit 2, --check in-sync exit 0, --check stale exit 1, --check absent exit 1
- `test_help_lists_four_subcommands` renamed `test_help_lists_subcommands` with `"generate"` added (PATTERNS gotcha #5)
- 30 tests pass: 6 new in test_generate_cmd.py + 24 in test_cli.py

**Task 3 — Co-bump:**
- `charts/arr-stack/values.yaml` tag `"0.18.0"` confirmed in-place from waves 1-2; Renovate annotation preserved

## Verification

```
cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf
# → All checks passed / Success: no issues in 58 source files

cd tools/arrconf && uv run pytest tests/test_generate_cmd.py tests/test_cli.py -q
# → 30 passed

grep 'tag: "0.18.0"' charts/arr-stack/values.yaml
# → match

grep 'renovate: image=ghcr.io/tom333/arr-stack-arrconf' charts/arr-stack/values.yaml
# → match
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff I001 import order violation**
- **Found during:** Task 1 triade run
- **Issue:** New `from arrconf.generators.intent` and `from arrconf.intent_config` imports placed after `from arrconf.reconcilers.*` — violated ruff's isort ordering
- **Fix:** Moved both new imports between `generators.categories` block and `from arrconf.logging` (alphabetical within third-party local group)
- **Files modified:** tools/arrconf/arrconf/__main__.py

**2. [Rule 1 - Bug] ruff E501 line too long in docstring**
- **Found during:** Task 1 triade run
- **Issue:** Single-line docstring `"Generate committed configs from intent.yml. Use --check in CI (INTENT-02/INTENT-03, D-06/D-07)."` exceeded 100-char limit
- **Fix:** Split into multi-line docstring (brief + detail paragraph)
- **Files modified:** tools/arrconf/arrconf/__main__.py

**3. [Scope] Task 3 co-bump was a no-op**
- **Found during:** Task 3 verification
- **Detail:** `charts/arr-stack/values.yaml` was already at `tag: "0.18.0"` from waves 1-2 (sibling plans 28-01, 28-02). No change committed; acceptance criteria satisfied by prior wave.

## Known Stubs

None — generate writes real config.js content derived from intent.yml via the pure generator from Plan 02.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes beyond those in the plan's threat model (T-28-06, T-28-07, T-28-08 all addressed).

## Self-Check: PASSED

- `tools/arrconf/arrconf/__main__.py` contains `def generate` and `generate_cross_seed` — confirmed
- `tools/arrconf/tests/test_generate_cmd.py` exists with 6 test functions — confirmed
- `tools/arrconf/tests/test_cli.py` contains `"generate"` in help-list test — confirmed
- Commits d2e543f and 2f98f5b exist in git log — confirmed
- `charts/arr-stack/values.yaml` tag `"0.18.0"` present — confirmed
- apply command not modified (D-06 preserved) — confirmed via grep: no `generate` call in apply function
