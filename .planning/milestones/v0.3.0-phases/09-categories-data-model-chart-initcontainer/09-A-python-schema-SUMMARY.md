---
phase: 09-categories-data-model-chart-initcontainer
plan: 09-A-python-schema
subsystem: arrconf-python
tags:
  - pydantic
  - schema
  - categories
  - python
dependency_graph:
  requires: []
  provides:
    - arrconf.resources.categories.Category
    - arrconf.resources.categories.Kind
    - arrconf.resources.categories.Profile
    - RootConfig.categories field
    - schemas/arrconf-schema.json (with Category type)
  affects:
    - tools/arrconf/arrconf/config.py
    - schemas/arrconf-schema.json
tech_stack:
  added:
    - arrconf.resources.categories module (new cross-cutting resource)
  patterns:
    - pydantic BaseModel with extra='forbid' + model_validator(mode='after')
    - Literal type aliases as module-level symbols for downstream re-import
    - Category as MediaCategory import alias (Option A — zero blast radius)
key_files:
  created:
    - tools/arrconf/arrconf/resources/categories.py
    - tools/arrconf/tests/test_categories.py
  modified:
    - tools/arrconf/arrconf/config.py
    - schemas/arrconf-schema.json
decisions:
  - "D-04 enforced via model_validator(mode='after'): base_path must equal /media/{name}"
  - "Import alias Category as MediaCategory used in config.py to avoid collision with existing qBit Category (Option A per 09-PATTERNS.md)"
  - "categories field placed FIRST in RootConfig to mirror YAML top-of-file placement (Plan C)"
  - "D-16 CI gate (test_schema_committed_matches_regen) passes — no new gate code needed"
metrics:
  duration: "6 minutes"
  completed: "2026-05-18"
  tasks_completed: 3
  files_changed: 4
---

# Phase 09 Plan A: Python Schema Summary

**One-liner:** Pydantic `Category` model with kebab-case regex + base_path invariant + `RootConfig.categories` field wired via import alias + 37 parametric tests + regenerated JSON Schema (2357 lines, Category type present).

## Tasks Executed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| A1 | Category pydantic model + Kind/Profile enums | 437dfcd | tools/arrconf/arrconf/resources/categories.py (NEW) |
| A2 | Wire RootConfig.categories field | 08d24d0 | tools/arrconf/arrconf/config.py (MODIFIED) |
| A3 | Parametric tests + schema regen | 245d3ed | tools/arrconf/tests/test_categories.py (NEW), schemas/arrconf-schema.json (REGENERATED) |

## D-NN Coverage

| Decision | Status | Evidence |
|----------|--------|----------|
| D-01 (Profile mapping — series) | Implemented | `Profile = Literal["general", "anime", "family"]`; 5 series categories in PRODUCTION_CATEGORIES |
| D-02 (Profile mapping — movies) | Implemented | Same Profile literal; 5 movie categories in PRODUCTION_CATEGORIES |
| D-04 (base_path STRICT invariant) | Implemented | `model_validator(mode='after')` enforces `/media/{name}`; 4 invariant violation tests pass |
| D-05 (schema optionality) | Implemented | `categories: list[MediaCategory] = Field(default_factory=list)` — defaults to `[]` |
| D-13 (no reconciler changes) | Preserved | Only config.py and resources/ modified; zero reconciler files touched |
| D-16 (schema regen CI gate) | Passing | `test_schema_committed_matches_regen` green; schema regenerated and committed byte-exact |

## Test Results

```
37 tests in test_categories.py — all PASSED
  - 10 production category happy-path tests (parametrized by name)
  - 8 kebab-case name violation tests
  - 5 kind enum violation tests
  - 4 profile enum violation tests
  - 4 base_path invariant violation tests
  - 1 extra='forbid' test
  - 5 missing required field tests

Full suite: 308 passed in 10.02s — coverage 94.94% (threshold 70%)
```

## Schema Regen Evidence

```
uv run arrconf schema-gen --output schemas/arrconf-schema.json
diff -q schemas/arrconf-schema.json /tmp/regen.json -> exit 0 (byte-equal)
schemas/arrconf-schema.json: 2357 lines (was ~2294 before — +63 lines for Category definition)
grep '"Category"' schemas/arrconf-schema.json -> found (Category type present)
grep '"categories"' schemas/arrconf-schema.json -> found (RootConfig.categories field present)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ruff I001: import block sort order in categories.py**
- **Found during:** Task A1 first lint run
- **Issue:** The plan's verbatim code had a blank line inside the import block and quoted return type annotation (ruff UP037)
- **Fix:** Removed extra blank line; changed `-> "Category":` to `-> Category:` (using `from __future__ import annotations` already present)
- **Files modified:** tools/arrconf/arrconf/resources/categories.py
- **Commit:** 437dfcd (inline fix before commit)

**2. [Rule 1 - Bug] ruff I001: import block sort order in config.py**
- **Found during:** Task A2 first lint run
- **Issue:** New `categories` import placed after `jellyfin` import — ruff isort requires alphabetical order
- **Fix:** Moved `from arrconf.resources.categories import Category as MediaCategory` to before the jellyfin import block
- **Files modified:** tools/arrconf/arrconf/config.py
- **Commit:** 08d24d0 (inline fix before commit)

**3. [Rule 1 - Bug] ruff E501: line too long in test_categories.py**
- **Found during:** Task A3 first lint run
- **Issue:** Plan's verbatim test code had PRODUCTION_CATEGORIES as single-line dicts, all exceeding the 100-char line limit
- **Fix:** Expanded each dict to multi-line format; also split long pytest.raises lines
- **Files modified:** tools/arrconf/tests/test_categories.py
- **Commit:** 245d3ed (inline fix before commit)

**4. [Rule 1 - Bug] mypy unused-ignore comments in test_categories.py**
- **Found during:** Task A3 first mypy run
- **Issue:** `type: ignore[arg-type]` placed on the opening `Category(` line instead of the argument line with the actual type mismatch
- **Fix:** Moved comments to the specific argument line (`kind=bad_kind, # type: ignore[arg-type]`)
- **Files modified:** tools/arrconf/tests/test_categories.py
- **Commit:** 245d3ed (inline fix before commit)

## Known Stubs

None — all fields are typed and validated; no placeholder values or TODO markers.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond what is documented in the plan's threat model. T-09A-01 through T-09A-07 dispositions all honored:
- T-09A-01 (Tampering via name field): mitigated — kebab-case regex blocks all path-traversal payloads
- T-09A-02 (Tampering via kind/profile): mitigated — Literal type closure enforced at load

## Pointer to Downstream Plans

Plan C (`09-C-arrconf-yml`) depends on `arrconf.resources.categories.Category` being importable from `arrconf.config.RootConfig`. This plan fulfills that dependency. Plan C can now add the 10-entry `categories:` block to `charts/arr-stack/files/arrconf.yml` and have it validate against `RootConfig` correctly.

## Self-Check: PASSED
