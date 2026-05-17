---
phase: 05-reconciler-qbittorrent-split-tv-anime-family
plan: 03
subsystem: testing
tags: [pytest, fixtures, conftest, qbittorrent, sonarr, radarr, scaffolding]

requires:
  - phase: 05-reconciler-qbittorrent-split-tv-anime-family
    provides: Wave 0 baseline snapshot (snapshots/before-phase-5-2026-05-14/) — fixture payloads derived from this
provides:
  - 8 fixture JSON/TXT files in tools/arrconf/tests/fixtures/{qbittorrent,sonarr,radarr}/
  - 8 @pytest.fixture functions in tools/arrconf/tests/conftest.py
  - Test scaffolding for Plans 05-04, 05-05, 05-06
affects: [05-04, 05-05, 05-06]

tech-stack:
  added: []
  patterns:
    - "WR-07 fixture routing (baseline vs edge_cases) extended to qBit + Sonarr/Radarr Phase 5 surface"
    - "qBittorrent cookie-auth login body fixture (plain-text 'Ok.', no JSON)"

key-files:
  created:
    - tools/arrconf/tests/fixtures/qbittorrent/categories.json
    - tools/arrconf/tests/fixtures/qbittorrent/preferences.json
    - tools/arrconf/tests/fixtures/qbittorrent/auth_login_ok.txt
    - tools/arrconf/tests/fixtures/sonarr/series_with_no_tags.json
    - tools/arrconf/tests/fixtures/sonarr/edge_cases/series_with_tv_tag.json
    - tools/arrconf/tests/fixtures/sonarr/remotepathmapping.json
    - tools/arrconf/tests/fixtures/radarr/movie_with_no_tags.json
    - tools/arrconf/tests/fixtures/radarr/remotepathmapping.json
  modified:
    - tools/arrconf/tests/conftest.py

key-decisions:
  - "Salvaged work from a failed parallel subagent run (Bash permission denied silently in background). Subagent had created files via Write but couldn't commit; orchestrator committed atomically + ran CI gates + wrote SUMMARY."
  - "qBit preferences fixture trimmed to Q2 allowlist (5 keys) + peripheral keys; web_ui_password explicitly omitted to keep fixture audit-clean."
  - "sonarr edge_cases/series_with_tv_tag.json carries tags=[2] for the future idempotence-proof test in Plan 05-05."

patterns-established:
  - "Worktree-isolated subagent permission failure mode: agent's Write tool changes leaked into the parent working tree, allowing salvage by parent orchestrator."
  - "Two minor ruff E501 errors auto-fixed in salvage (Path wrap + docstring split) — no semantic change."

requirements-completed: [REQ-app-coverage]

duration: ~15 min (incl. salvage from failed parallel run)
completed: 2026-05-14
---

# Plan 05-03: Test Scaffolding for Phase 5 Reconcilers

**8 fixture files + 8 @pytest.fixture functions added to unblock Plans 05-04/05/06 reconciler tests**

## Performance

- **Duration:** ~15 min (including ~3 min recovering from failed parallel subagent)
- **Tasks:** 2/2 complete (3.1 fixture files, 3.2 conftest extension)

## Accomplishments

- 8 fixture payloads landed under `tools/arrconf/tests/fixtures/{qbittorrent,sonarr,radarr}/`, derived directly from the Wave 0 baseline snapshot at `snapshots/before-phase-5-2026-05-14/`.
- conftest.py extended with 8 `@pytest.fixture` functions following WR-07 routing (baseline vs `edge_cases/`).
- All 128 pre-existing tests still pass; ruff + mypy(arrconf) CI gates clean.
- qBittorrent allowlist applied to `preferences.json` (Q2 resolution): only 5 reconciled keys + peripheral keys; sensitive `web_ui_password` etc. explicitly omitted.

## Task Commits

1. **Task 3.1: 8 fixture files** — `9c4b2dd` (test)
2. **Task 3.2: conftest.py extension** — `64f797f` (test)

## Files Created/Modified

- `tools/arrconf/tests/fixtures/qbittorrent/categories.json` — 3 baseline categories (cleanuparr-unlinked, radarr, sonarr)
- `tools/arrconf/tests/fixtures/qbittorrent/preferences.json` — trimmed allowlist + peripheral keys
- `tools/arrconf/tests/fixtures/qbittorrent/auth_login_ok.txt` — `Ok.` login response body
- `tools/arrconf/tests/fixtures/sonarr/series_with_no_tags.json` — 8 series, tags=[]
- `tools/arrconf/tests/fixtures/sonarr/edge_cases/series_with_tv_tag.json` — 8 series, tags=[2] (idempotence)
- `tools/arrconf/tests/fixtures/sonarr/remotepathmapping.json` — 1 baseline mapping
- `tools/arrconf/tests/fixtures/radarr/movie_with_no_tags.json` — 11 movies, tags=[]
- `tools/arrconf/tests/fixtures/radarr/remotepathmapping.json` — 1 baseline mapping
- `tools/arrconf/tests/conftest.py` — 8 new `@pytest.fixture` functions following the existing `_load_fixture` pattern

## Decisions Made

- **Salvaged the failed-subagent's Write-tool output.** The parallel executor agent for this plan was denied Bash mid-run (subagent permission isolation in this Claude Code environment). All 8 fixture files + the conftest.py edit had already landed in the parent working tree by the time the agent gave up. The orchestrator validated, committed, and CI-gated them.
- **Followed WR-07 baseline/edge_cases routing.** `series_with_tv_tag.json` placed in `edge_cases/` (scenario fixture for idempotence), `series_with_no_tags.json` at the baseline root (starting state).
- **Patched two ruff E501 in salvage.** Line 138 wrapped via intermediate `path` var; line 164 docstring split. No semantic change.

## Deviations from Plan

### Auto-fixed Issues

**1. [Process — failed parallel run] Bash permission denied for worktree subagent**
- **Found during:** Initial Wave 1 parallel dispatch (Plan 05-03's executor)
- **Issue:** Subagent had `Write` but not `Bash`; could create fixtures but couldn't commit, validate, or run CI gates. Worktree was auto-removed (no commits = no preservation).
- **Fix:** Orchestrator added `Bash(*)` to `.claude/settings.local.json` (user-approved), but the fixture work had also leaked into the parent tree's gitignored-and-untracked state. Salvaged inline; committed atomically per task; ran full CI gates.
- **Verification:** 128 tests pass, ruff clean, mypy(arrconf) clean. SUMMARY.md atomic commit.
- **Committed in:** 9c4b2dd, 64f797f, this SUMMARY commit.

**2. [Ruff E501] Two line-too-long errors in new conftest code**
- **Found during:** CI gate validation post-salvage
- **Issue:** `path.read_text().rstrip(...)` single-line and the remotepathmapping docstring exceeded 100 cols
- **Fix:** Extracted `path` to a local; split the docstring across two lines
- **Verification:** `uv run ruff check tests/conftest.py` → All checks passed

---

**Total deviations:** 2 auto-fixed (1 process-level recovery, 1 lint)
**Impact on plan:** Salvage path delivered the planned outcome with a 3-minute delay. No scope change.

## Issues Encountered

- Subagent permission isolation in background Claude Code worktrees — subagents cannot reliably invoke Bash without an explicit broad allow-rule. Resolved at the orchestrator level by adding `Bash(*)` to settings.local.json.

## User Setup Required

None.

## Next Phase Readiness

- Plans 05-04 (qBit reconciler tests), 05-05 (Sonarr split reconciler tests), 05-06 (Radarr mirror tests) can now reference the 8 new fixtures by name.
- Wave 1 still has 05-02 outstanding; orchestrator will re-spawn that plan as a parallel agent now that Bash permissions are configured.

---
*Phase: 05-reconciler-qbittorrent-split-tv-anime-family*
*Completed: 2026-05-14*
