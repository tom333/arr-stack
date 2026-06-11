---
phase: 30-cross-seed
plan: "01"
subsystem: arrconf-generator
tags: [cross-seed, intent, generator, token-emission, co-bump]
dependency_graph:
  requires: []
  provides: [XSEED-01, XSEED-02]
  affects: [charts/arr-stack/files/cross-seed/config.js, charts/arr-stack/values.yaml]
tech_stack:
  added: []
  patterns: [env-token-substitution, generator-regenerate, release-pin-co-bump]
key_files:
  created: []
  modified:
    - charts/arr-stack/files/intent.yml
    - charts/arr-stack/files/cross-seed/config.js
    - tools/arrconf/tests/test_generate_cross_seed.py
    - charts/arr-stack/values.yaml
decisions:
  - "Use ${QBT_USER} not hard-coded admin in torrent_clients URL (RESEARCH Open Question 2 resolved)"
  - "Patch bump 0.19.0 → 0.19.1 for token-emission correction (not a new feature)"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-31T05:37:11Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 4
---

# Phase 30 Plan 01: Distinct env tokens in cross-seed intent + generator test Summary

Replace shared `PLACEHOLDER` in intent.yml with distinct `${PROWLARR_API_KEY}` / `${QBT_USER}:${QBT_PASS}` tokens, regenerate config.js, update the generator test assertion, and co-bump arrconf image tag 0.19.0 → 0.19.1.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Swap PLACEHOLDER for distinct env tokens + regenerate config.js | `988f3a8` | intent.yml, cross-seed/config.js |
| 2 | Update generator test for new token + co-bump arrconf.image.tag | `f1ca773` | test_generate_cross_seed.py, values.yaml |

## Decisions Made

1. `${QBT_USER}` used in torrent_clients URL (not hard-coded `admin`): `QBT_USER` is already in `arrconf-env` sealed-secret, consistent with the rest of arrconf's env-injection pattern. Resolves RESEARCH Open Question 2.
2. Patch bump (0.19.0 → 0.19.1): token-emission correction is a fix, not a new feature; patch is the correct semver category per CLAUDE.md table.

## Verification

- `grep -r PLACEHOLDER charts/arr-stack/files/intent.yml charts/arr-stack/files/cross-seed/config.js` → returns nothing (PASS)
- `arrconf generate --check` → exit 0 (generate_ok, no drift)
- `uv run pytest tests/test_generate_cross_seed.py -q` → 5 passed
- `charts/arr-stack/values.yaml` arrconf image tag = `0.19.1` (PASS)
- Python triade: `ruff format --check` PASS, `ruff check` PASS, `mypy arrconf` PASS (0 issues in 60 files)

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. Both modified files (`intent.yml`, `config.js`) are version-controlled committed artifacts; neither carries resolved secret values — only literal `${...}` tokens, as required by T-30-01 (Information Disclosure mitigation).

## Self-Check: PASSED

- `charts/arr-stack/files/intent.yml` — FOUND
- `charts/arr-stack/files/cross-seed/config.js` — FOUND
- `tools/arrconf/tests/test_generate_cross_seed.py` — FOUND
- `charts/arr-stack/values.yaml` — FOUND (tag: 0.19.1)
- Commit `988f3a8` — FOUND
- Commit `f1ca773` — FOUND
