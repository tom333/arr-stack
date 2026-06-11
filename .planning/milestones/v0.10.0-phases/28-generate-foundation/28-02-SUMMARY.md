---
phase: 28-generate-foundation
plan: "02"
subsystem: arrconf/generators
tags: [generator, cross-seed, js-literal, pure-function, tdd]
dependency_graph:
  requires: [28-01]
  provides: [generate_cross_seed, arrconf.generators.intent]
  affects: [arrconf.generators.__init__]
tech_stack:
  added: []
  patterns: [pure-function-generator, json-dumps-determinism, camelcase-key-mapping]
key_files:
  created:
    - tools/arrconf/arrconf/generators/intent.py
    - tools/arrconf/tests/test_generate_cross_seed.py
  modified:
    - tools/arrconf/arrconf/generators/__init__.py
decisions:
  - "json.dumps(sort_keys=True, indent=tab) for deterministic JS literal output (T-28-04/T-28-05 mitigations)"
  - "Empty list fields omitted from JS object; link_type/action always emitted"
  - "camelCase key mapping in generator layer (torrent_clients->torrentClients, link_dirs->linkDirs)"
  - "arrconf.image.tag left at 0.18.0 (already set by wave 1 plan 01 — idempotent co-bump)"
metrics:
  duration: "3m 16s"
  completed: "2026-05-31T03:03:28Z"
  tasks_completed: 3
  files_changed: 3
---

# Phase 28 Plan 02: generate_cross_seed Pure Function Summary

Pure-function JS literal generator for cross-seed config.js — the P28 D-03 proving slice demonstrating the generate framework emits non-YAML formats.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for generate_cross_seed | 4825716 | tests/test_generate_cross_seed.py |
| 1 (GREEN) | Implement generate_cross_seed pure function | 7e7fcdf | generators/intent.py + tests (fixed) |
| 2 | Export generate_cross_seed from generators/__init__.py | b0e9c49 | generators/__init__.py |
| 3 | Tests verified + co-bump confirmed | (included in Task 1 commit) | values.yaml confirmed at 0.18.0 |

## What Was Built

`arrconf/generators/intent.py` implements `generate_cross_seed(cfg: CrossSeedConfig) -> str`, a pure function (no I/O, no httpx, no file access) that renders a CommonJS `module.exports = {...};` literal with a read-only `// GENERATED` header.

Key behaviors:
- Deterministic output via `json.dumps(sort_keys=True)` — byte-identical across runs
- Empty list fields (`torznab`, `torrent_clients`, `link_dirs`) are omitted from the JS object
- `link_type` and `action` are always emitted (non-empty defaults)
- camelCase key mapping applied in the generator layer
- Security: `json.dumps` handles all escaping — no f-string interpolation of raw values (T-28-04/T-28-05)

## TDD Gate Compliance

- RED commit: `4825716` — 5 failing tests (ImportError — module not yet created)
- GREEN commit: `7e7fcdf` — implementation + 5 tests passing
- No REFACTOR needed (code was clean from the start)

## Tests

5 tests in `tests/test_generate_cross_seed.py`:
- `test_generate_cross_seed_minimal` — header + module.exports structure
- `test_generate_cross_seed_deterministic` — two calls produce identical bytes
- `test_generate_cross_seed_sort_keys` — JS object keys are alphabetically sorted
- `test_generate_cross_seed_omits_empty` — empty lists absent; linkType/action present
- `test_generate_cross_seed_camelcase` — torrent_clients → torrentClients, link_dirs → linkDirs

All pass. Python triade (ruff format, ruff check, mypy) clean.

## Co-bump

`charts/arr-stack/values.yaml#arrconf.image.tag` is `0.18.0` — already set by wave 1 plan 01. No change required (idempotent).

## Deviations from Plan

**[Rule 1 - Bug] Removed `open()` mention from module docstring to satisfy acceptance criterion**
- Found during: Task 1 verification
- Issue: Acceptance criterion `grep -c "open(" ... returns 0` matched the comment "no file access, no open()" in the module docstring
- Fix: Rephrased to "no file access, no httpx" — no behavioral change, purely cosmetic docstring update
- Files modified: `generators/intent.py`

**[Rule 1 - Bug] Fixed ruff lint errors in test file**
- Found during: Task 1 triade
- Issue: Import order (I001) and line-too-long (E501) in test file
- Fix: Sorted imports (generators.intent before intent_config alphabetically), shortened docstring
- Files modified: `tests/test_generate_cross_seed.py`

## Known Stubs

None — `generate_cross_seed` is a complete, wired pure function. No placeholders.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns introduced. The generator is a pure string transformation function.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `generators/intent.py` exists | FOUND |
| `tests/test_generate_cross_seed.py` exists | FOUND |
| commit 4825716 (RED) | FOUND |
| commit 7e7fcdf (GREEN) | FOUND |
| commit b0e9c49 (Task 2) | FOUND |
