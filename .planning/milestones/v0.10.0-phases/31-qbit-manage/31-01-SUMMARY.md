---
phase: 31-qbit-manage
plan: "01"
subsystem: arrconf-generator
tags: [qbit_manage, generator, intent, schema, tdd, co-bump]
dependency_graph:
  requires: []
  provides: [QbitManageConfig schema, generate_qbit_manage generator, qbit_manage/config.yml]
  affects: [intent_config.py, generators/intent.py, __main__.py, intent-schema.json]
tech_stack:
  added: [QbitManageConfig pydantic schema, generate_qbit_manage() pure function]
  patterns: [string-construction for !ENV YAML tags, TDD RED/GREEN cycle]
key_files:
  created:
    - tools/arrconf/tests/test_generate_qbit_manage.py
    - charts/arr-stack/files/qbit_manage/config.yml
  modified:
    - tools/arrconf/arrconf/intent_config.py
    - tools/arrconf/arrconf/generators/intent.py
    - tools/arrconf/arrconf/__main__.py
    - tools/arrconf/tests/test_generate_cmd.py
    - charts/arr-stack/files/intent.yml
    - schemas/intent-schema.json
    - charts/arr-stack/values.yaml
decisions:
  - "Used ruyaml(typ='safe') instead of pyyaml for test YAML parsing (pyyaml not in project deps)"
  - "!ENV tags built via string construction — ruyaml.dump() would quote them (Pitfall 1)"
  - "generate_qbit_manage() returns string without trailing newline: join('\n') produces content matching test expectations"
  - "Default catch-all share_limits group omits include_all_tags key (RESEARCH.md A1 — verify post-deploy)"
metrics:
  duration_minutes: 5
  tasks_completed: 2
  files_modified: 7
  files_created: 2
  completed_date: "2026-05-31"
---

# Phase 31 Plan 01: qbit_manage Generator Summary

QbitManageConfig pydantic schema + generate_qbit_manage() pure function + generate CLI dispatch + seed intent.yml + committed config.yml + regenerated intent-schema.json + arrconf image minor co-bump 0.19.1→0.20.0 (QBM-01/QBM-02).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for QbitManageConfig | `3639a4f` | tests/test_generate_qbit_manage.py |
| 1 (GREEN) | QbitManageConfig schema + generate_qbit_manage() | `8b05102` | intent_config.py, generators/intent.py, tests/test_generate_qbit_manage.py |
| 2 | CLI dispatch + seed + generated artifacts + co-bump | `fec3b5a` | __main__.py, test_generate_cmd.py, intent.yml, qbit_manage/config.yml, intent-schema.json, values.yaml |

## What Was Built

**QbitManageConfig schema** (`intent_config.py`):
- Three new pydantic models: `ShareLimitGroup`, `TrackerTagEntry`, `QbitManageConfig` — all with `extra="forbid"`
- `ToolsConfig.qbit_manage: QbitManageConfig | None = Field(default=None)` wired
- Fields: `qbt_host`, `tracker_tags`, `share_limits`, `recyclebin_days`, `rem_orphaned`, `rem_unregistered`

**generate_qbit_manage() generator** (`generators/intent.py`):
- Pure function: no I/O, no HTTP, deterministic output
- `cat_update: false` + `cat: {}` hardcoded unconditionally (QBM-02 — arrconf sole category owner)
- `!ENV QBT_USER` / `!ENV QBT_PASS` emitted as literal unquoted YAML strings via string construction
- `rem_orphaned` / `rem_unregistered` default false, opt-in via intent.yml (D-04)
- share_limits groups sorted ascending by priority
- Default catch-all group (priority: 999) with RESEARCH.md A1 verify-post-deploy comment

**generate CLI dispatch** (`__main__.py`):
- `generate_qbit_manage` imported + dispatched alongside cross_seed block
- Writes to `qbit_manage/config.yml` (underscore, per pydantic field name)

**Seed intent.yml** (`charts/arr-stack/files/intent.yml`):
- Added `tools.qbit_manage` block with beyond-hd tracker, one share_limits group, recyclebin 30d defaults

**Committed config.yml** (`charts/arr-stack/files/qbit_manage/config.yml`):
- Read-only generated artifact; `arrconf generate --check` exits 0 (idempotence confirmed)
- Contains `cat_update: false`, `cat: {}`, `user: !ENV QBT_USER`, `pass: !ENV QBT_PASS`

**Regenerated schema** (`schemas/intent-schema.json`):
- Updated to include `QbitManageConfig` (CI drift gate auto-covers this)

**Co-bump** (`charts/arr-stack/values.yaml`):
- `arrconf.image.tag`: `"0.19.1"` → `"0.20.0"` (minor: new feature per CLAUDE.md convention)
- Renovate annotation preserved

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] pyyaml not installed — used ruyaml for YAML test parsing**
- **Found during:** Task 1 RED phase (test collection error)
- **Issue:** Plan showed `import yaml; yaml.safe_load()` but `pyyaml` is not in the project's dependencies; project uses `ruyaml`
- **Fix:** Used `from ruyaml import YAML; YAML(typ='safe').load(io.StringIO(...))` instead — equivalent behavior
- **Files modified:** `tests/test_generate_qbit_manage.py`
- **Commit:** `3639a4f` (RED), `8b05102` (GREEN)

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit) | `3639a4f` | PASS — tests failed due to ImportError on missing `generate_qbit_manage` |
| GREEN (implementation commit) | `8b05102` | PASS — all 10 tests pass |
| REFACTOR | not needed | N/A — no cleanup required |

## Verification Results

- `uv run pytest tests/test_generate_qbit_manage.py -q`: 10 passed
- `uv run pytest tests/test_generate_cmd.py -q`: 7 passed (6 existing + 1 new)
- `uv run pytest -q` (full suite): 520 passed, 3 pre-existing flaky failures (phase10 sweep + jellyfin step-order per MEMORY — not regressions)
- `arrconf generate --check`: exits 0 (idempotence confirmed)
- Triade: `ruff format --check` + `ruff check` + `mypy arrconf`: all pass

## Known Stubs

None — all functionality is fully wired. The `default` catch-all share_limits group omits `include_all_tags` (per RESEARCH.md A1 guidance); this needs operator verification post-deploy that untagged torrents match this group.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: information_disclosure (mitigated) | charts/arr-stack/files/qbit_manage/config.yml | `user: !ENV QBT_USER` / `pass: !ENV QBT_PASS` — no real credentials in git; `!ENV` tag resolved at runtime by qbit_manage |
| threat_flag: tampering (mitigated) | charts/arr-stack/files/qbit_manage/config.yml | `cat_update: false` + `cat: {}` hardcoded unconditionally; CI `generate --check` blocks any drift |

## Self-Check: PASSED

Files verified:
- `tools/arrconf/tests/test_generate_qbit_manage.py`: FOUND
- `charts/arr-stack/files/qbit_manage/config.yml`: FOUND
- Commits `3639a4f`, `8b05102`, `fec3b5a`: FOUND
