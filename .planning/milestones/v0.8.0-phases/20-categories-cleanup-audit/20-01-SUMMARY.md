---
phase: 20-categories-cleanup-audit
plan: 01
subsystem: arrconf
tags: [arrconf, audit, legacy-detection, categories, python, typer, respx]

requires:
  - phase: 16-jellyfin-categories-as-libs
    provides: "10-lib Jellyfin virtual-folder reconciler (baseline for audit_jellyfin)"
  - phase: 10-categories-wiring
    provides: "Categories generator + 6-app wiring (defines category paths audit compares against)"

provides:
  - "arrconf/audit.py — read-only legacy state inventory module (5 per-app audit functions + run_audit + verify_audit)"
  - "arrconf audit + audit-verify Typer subcommands wired into __main__.py"
  - "26 respx-mocked tests covering all RESEARCH.md Pitfalls 1-8"
  - "10 JSON fixtures under tests/fixtures/audit/ for per-app scenarios"
  - "20-AUDIT.md scaffold (operator must run `arrconf audit` then fill ? cells)"
  - "arrconf.image.tag patch-bumped 0.14.0 → 0.14.1 (co-bump rule)"

affects: [21-categories-cleanup-migration, 22-categories-cleanup-dc-rename, 23-categories-cleanup-verify]

tech-stack:
  added: []
  patterns:
    - "Audit-only GET invariant: audit.py contains zero .post/.put/.delete/.post_form calls"
    - "Pitfall 2 disambiguation: AUTO_TAG_MAPPING_SERIES vs AUTO_TAG_MAPPING_MOVIES split to handle Sonarr family→series-garcons vs Radarr family→films-enfants"
    - "Verify gate pattern: verify_audit() returns 0/1; gates checked sequentially (no ?, YAML parses, paths valid, tags live)"
    - "conftest.py cast() pattern: new fixtures use cast(list[dict[str,Any]], _load_fixture(...)) to keep mypy error count at pre-existing baseline (43)"

key-files:
  created:
    - tools/arrconf/arrconf/audit.py
    - tools/arrconf/tests/test_audit.py
    - tools/arrconf/tests/fixtures/audit/radarr_movies_mixed.json
    - tools/arrconf/tests/fixtures/audit/radarr_tags_mixed.json
    - tools/arrconf/tests/fixtures/audit/radarr_downloadclient_with_catchall.json
    - tools/arrconf/tests/fixtures/audit/sonarr_series_mixed.json
    - tools/arrconf/tests/fixtures/audit/sonarr_tags_mixed.json
    - tools/arrconf/tests/fixtures/audit/sonarr_downloadclient_with_catchall.json
    - tools/arrconf/tests/fixtures/audit/qbit_torrents_mixed.json
    - tools/arrconf/tests/fixtures/audit/qbit_categories_aligned.json
    - tools/arrconf/tests/fixtures/audit/seerr_settings_sonarr_legacy_anime.json
    - tools/arrconf/tests/fixtures/audit/jellyfin_virtualfolders_post_phase16.json
    - .planning/phases/20-categories-cleanup-audit/20-AUDIT.md
  modified:
    - tools/arrconf/arrconf/__main__.py
    - tools/arrconf/tests/conftest.py
    - charts/arr-stack/values.yaml

key-decisions:
  - "Read-only invariant enforced by convention (no code guard): audit.py uses only client.get() — audited via grep in review"
  - "AUTO_TAG_MAPPING split (Pitfall 2): separate SERIES vs MOVIES dicts because 'family' tag maps differently per Sonarr vs Radarr context"
  - "conftest.py cast() pattern: use cast() in new Phase 20 fixtures to keep mypy at pre-existing baseline (43 errors, not increasing)"
  - "20-AUDIT.md is a scaffold until operator runs `arrconf audit` against live cluster; Phase 21 consumes the YAML appendix"

requirements-completed: [CAT-CLEANUP-01]

duration: 45min
completed: 2026-05-26
---

# Phase 20 Plan 01: Categories Cleanup Audit Summary

**arrconf audit + audit-verify commands with read-only legacy state inventory (LEGACY_PATHS_HARD/AUTO_PATH_MAPPING constants, 5-app GET-only audit functions, verify gate rejecting ? cells)**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-05-26T06:20:00Z
- **Completed:** 2026-05-26T07:09:00Z
- **Tasks:** 5 code tasks complete + 1 checkpoint reached (Task 6 — cluster access)
- **Files modified:** 15

## Accomplishments

- Created `arrconf/audit.py` (997 LOC) implementing `LEGACY_PATHS_HARD`, `AUTO_PATH_MAPPING`, `AUTO_TAG_MAPPING_SERIES/MOVIES`, `OPERATOR_DECISION_PATHS` as `Final` constants matching CLAUDE.md §"Filesystem migration v0.2.0 → v0.3.0" verbatim; 5 per-app audit functions + `run_audit()` + `verify_audit()` gate
- Wired `audit` and `audit-verify` Typer subcommands into `__main__.py` with env-var pre-flight validation
- Added 26 respx-mocked tests (test_audit.py, 937 LOC) covering all 8 Pitfalls from RESEARCH.md plus security/rendering edge cases; full suite passes (442 tests, 83.47% coverage)
- Chart co-bump: `arrconf.image.tag` 0.14.0 → 0.14.1 in same commit per CLAUDE.md release pin rule

## Task Commits

1. **Tasks 1-5: audit.py + __main__.py + tests + fixtures + chart co-bump** — `ee5ac19` (feat)

**Plan metadata:** (pending — final docs commit)

## Files Created/Modified

- `tools/arrconf/arrconf/audit.py` — Read-only audit module: 5 per-app GET-only functions, run_audit() Markdown+YAML emitter, verify_audit() gate (4 checks)
- `tools/arrconf/arrconf/__main__.py` — Added `audit` + `audit-verify` Typer commands with Settings pre-flight
- `tools/arrconf/tests/test_audit.py` — 26 tests: predicates (is_legacy_path, is_legacy_tag), per-app audits (radarr/sonarr/qbittorrent/seerr/jellyfin), run_audit integration, verify gates, security/rendering
- `tools/arrconf/tests/conftest.py` — 10 new Phase 20 fixture registrations with cast() for mypy compliance
- `tools/arrconf/tests/fixtures/audit/*.json` — 10 JSON fixtures (7 GET endpoints + categories dict)
- `charts/arr-stack/values.yaml` — Patch-bumped `arrconf.image.tag` 0.14.0 → 0.14.1
- `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md` — Scaffold (operator generates with `arrconf audit` against live cluster)

## Decisions Made

- **AUTO_TAG_MAPPING split (Pitfall 2):** Two separate dicts (`AUTO_TAG_MAPPING_SERIES` vs `AUTO_TAG_MAPPING_MOVIES`) because `family` tag maps to `series-garcons` in Sonarr context but `films-enfants` in Radarr context. Single dict would silently mis-route.
- **cast() in conftest.py:** New Phase 20 fixtures use `cast(list[dict[str,Any]], _load_fixture(...))` instead of bare return, keeping mypy error count at pre-existing 43 (no regression introduced by this plan).
- **lstrip('...') → slicing (B005):** Replaced `media_path.lstrip('/data/')` with `media_path[len('/data/'):]` to avoid ruff B005 (multi-char lstrip is misleading).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ruff format, ruff check, and mypy issues before committing**
- **Found during:** Task 4 (triade gate)
- **Issue:** 3 ruff issues (unsorted imports in __main__.py, unused `_fetch_current_categories` import in audit.py, `B005` lstrip with multi-char string, `UP017` timezone alias, `E501` line too long) + 1 mypy unused-ignore
- **Fix:** Auto-fixed with `ruff check --fix`; manual fixes for B005 (slicing), E501 (comment truncation), unused type: ignore removed
- **Files modified:** `arrconf/audit.py`, `arrconf/__main__.py`, `tests/test_audit.py`
- **Committed in:** ee5ac19

**2. [Rule 1 - Bug] Fixed _build_root_with_10_categories() helper in test_audit.py**
- **Found during:** Task 4 (pytest run, 23 test failures)
- **Issue:** The seerr section used `{"enable": True, "prune": False}` for `sonarr_service` and `radarr_service` — but `SeerrSonarrServiceSection` requires `hostname`, `activeProfileId`, `activeDirectory` fields (pydantic ValidationError)
- **Fix:** Replaced with correct minimal valid shape: `{"hostname": "sonarr.svc", "activeProfileId": 6, "activeDirectory": "/media/series"}`
- **Files modified:** `tests/test_audit.py`
- **Committed in:** ee5ac19

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs caught at triade gate)
**Impact on plan:** All fixes necessary for CI compliance. No scope creep.

## Issues Encountered

- mypy pre-existing error count: 43 errors in 10 files (pre-existing before this plan). New conftest.py fixtures introduced 10 additional `no-any-return` errors (same pattern as all existing fixtures using `_load_fixture() -> Any`). Fixed by adding `cast()` calls, restoring count to 43.

## Known Stubs

- `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md` — Scaffold placeholder. The actual inventory is generated by running `arrconf audit` against the live cluster. Phase 21 requires the operator to complete this file (fill `?` cells, run `audit-verify`) before proceeding.

## Threat Flags

None. `audit.py` issues only GET requests — zero new write surfaces introduced. No new network endpoints exposed. All cluster credentials flow via env vars (pre-existing pattern).

## Next Phase Readiness

- Phase 20 Task 6 (human-action checkpoint): Operator must run `arrconf audit` against live cluster, fill `?` cells in `20-AUDIT.md`, run `arrconf audit-verify`, and commit the populated file
- Phase 21 (Categories cleanup migration) can proceed once `20-AUDIT.md` has no `?` cells and `audit-verify` exits 0

## Self-Check: PASSED

- `tools/arrconf/arrconf/audit.py` — FOUND
- `tools/arrconf/arrconf/__main__.py` — FOUND (modified)
- `tools/arrconf/tests/test_audit.py` — FOUND
- `tools/arrconf/tests/fixtures/audit/` (10 files) — FOUND
- `charts/arr-stack/values.yaml` tag: "0.14.1" — FOUND
- `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md` — FOUND
- Commit `ee5ac19` — FOUND

---
*Phase: 20-categories-cleanup-audit*
*Completed: 2026-05-26*
