---
phase: 03-extend-arrconf
plan: "06"
subsystem: arrconf
tags: [arrconf, radarr, prowlarr, cli-wiring, schema-gen, release, v0.2.0]

# Dependency graph
requires:
  - phase: 03-01
    provides: WR-01 credential privacy fix + settings.py radarr/prowlarr api key fields
  - phase: 03-02
    provides: RootConfig monolithic + sonarr caller migration + diff_cmd.py
  - phase: 03-03
    provides: reconcile_sonarr extensions (root_folders, indexers, notifications, host_config)
  - phase: 03-04
    provides: reconcile_radarr + RadarrClient full parity
  - phase: 03-05
    provides: reconcile_prowlarr + ProwlarrClient + AppEntry YAML model

provides:
  - __main__.py apply/diff/dump subcommands dispatch to all 3 reconcilers (sonarr, radarr, prowlarr)
  - diff_cmd.py diff_radarr and diff_prowlarr functions
  - _selected_apps defaults to {sonarr, radarr, prowlarr} with YAML presence guards
  - dump_not_implemented warning for radarr/prowlarr (CONTEXT.md deferred)
  - schemas/arrconf-schema.json regenerated for Phase-3 RootConfig (flat sonarr/radarr/prowlarr, all 6 section types)
  - test_schema_gen.py D-15 CI gate restored (was ignored since Plan 02)
  - v0.2.0 annotated tag published — ghcr.io/tom333/arr-stack-arrconf:0.2.0 CI built and published

affects:
  - phase-04 (umbrella chart) needs v0.2.0 GHCR image tag
  - any future plan adding a new app reconciler should follow the 3-branch pattern in __main__.py

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-app variable naming in __main__.py subcommands (radarr_client, prowlarr_client) prevents mypy type drift across app blocks"
    - "dump_not_implemented warning pattern for phase-deferred dump support"
    - "D-37 atomic single-tag: annotated tag object + single push, CI triggers on v* pattern"

key-files:
  created:
    - .planning/phases/03-extend-arrconf/03-06-SUMMARY.md
  modified:
    - tools/arrconf/arrconf/__main__.py
    - tools/arrconf/arrconf/diff_cmd.py
    - schemas/arrconf-schema.json
    - .planning/STATE.md

key-decisions:
  - "Phase 03 P06: v0.2.0 annotated tag cut + CI run 25660722478 succeeded; ghcr.io/tom333/arr-stack-arrconf:0.2.0 verified by CI push; D-37 atomic-tag pattern observed; OCI-index manifest probe pattern (Phase 02.2-04 lesson) documented for Task 6.5 operator verification"
  - "Per-app variable naming (radarr_client, prowlarr_client vs reusing instance/client) chosen to resolve mypy type assignment incompatibility across app branches in the same function scope"
  - "_selected_apps default expanded from {'sonarr'} to {'sonarr', 'radarr', 'prowlarr'}; safety guaranteed by per-branch 'main' in root.<app> guard — YAML-absent apps skip silently (T-03-06-06 mitigation)"

patterns-established:
  - "Per-app variable naming: use radarr_instance, radarr_client, radarr_result to avoid mypy type inference conflicts across multiple app branches in the same function"
  - "dump_not_implemented warning: log.warning with hint to CONTEXT.md for phase-deferred features"
  - "Schema-gen idempotence gate: test_schema_gen.py test_schema_committed_matches_regen catches any config.py change that forgets to re-run schema-gen"

requirements-completed:
  - REQ-app-coverage
  - REQ-configarr-coexistence

# Metrics
duration: 20min
completed: 2026-05-11
---

# Phase 03 Plan 06: Release Wiring Summary

**Radarr + Prowlarr CLI wiring complete, JSON Schema regenerated with Phase-3 RootConfig, v0.2.0 released to GHCR via CI run 25660722478 — Phase 3 fully shipped pending operator GHCR anon-pull verification**

## Performance

- **Duration:** 20 min
- **Started:** 2026-05-11T08:40:00Z
- **Completed:** 2026-05-11T09:05:00Z
- **Tasks:** 4 (6.1 pre-done by orchestrator; 6.2, 6.3, 6.4 executed; 6.5 awaiting operator)
- **Files modified:** 4

## Accomplishments

- CLI subcommands apply/diff now dispatch to all 3 reconcilers; missing-API-key fast-fail wired for radarr and prowlarr (env_var RADARR_API_KEY / PROWLARR_API_KEY)
- JSON Schema regenerated: old AppsConfig/SonarrConfig indirection removed, RadarrInstance + ProwlarrInstance + AppEntry + HostConfigSection + all 6 section types added; test_schema_gen.py D-15 gate restored
- v0.2.0 annotated tag published; CI run 25660722478 succeeded; ghcr.io/tom333/arr-stack-arrconf:0.2.0 built and pushed
- Full test suite: 113 passed, coverage 80% total (differ 100%, sonarr 95%, radarr 78%, prowlarr 88%)

## Task Commits

1. **Task 6.1: Pre-deploy snapshot baseline** — `7199cbe` (pre-done by orchestrator)
2. **Task 6.2: Wire reconcile_radarr and reconcile_prowlarr** — `bc7ac98` (feat)
3. **Task 6.3: Regenerate JSON Schema + re-enable test_schema_gen.py** — `2c05cee` (feat)
4. **Task 6.4: STATE.md update for v0.2.0** — `f880ec2` (state)

**Tag:** `v0.2.0` → commit on HEAD; CI run 25660722478 succeeded

## Files Created/Modified

- `tools/arrconf/arrconf/__main__.py` — apply/diff radarr+prowlarr branches; _selected_apps default; dump_not_implemented warning
- `tools/arrconf/arrconf/diff_cmd.py` — diff_radarr and diff_prowlarr functions added
- `schemas/arrconf-schema.json` — regenerated for Phase-3 RootConfig (521 insertions, 22 deletions vs old schema)
- `.planning/STATE.md` — milestone v0.2.0, Phase 03 P06 decision logged

## Decisions Made

- Per-app variable naming (radarr_client, prowlarr_client) instead of reusing instance/client — resolves mypy type inference incompatibility across multi-branch function scope
- _selected_apps default expanded to all 3 apps; safety is YAML-presence-guard per branch, not --apps flag
- dump for radarr/prowlarr deferred per CONTEXT.md; surfaced as log.warning with CONTEXT.md hint

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] mypy type assignment incompatibility across app blocks**
- **Found during:** Task 6.2 (caller wiring)
- **Issue:** Re-assigning `instance` and `client` to different types (SonarrInstance → RadarrInstance → ProwlarrInstance) in the same function scope caused mypy "Incompatible types in assignment" errors (16 total)
- **Fix:** Used per-app variable names (radarr_instance, radarr_client, radarr_result, prowlarr_instance, prowlarr_client, prowlarr_actions, radarr_diff_instance, prowlarr_diff_instance, etc.) to give each branch an independent type
- **Files modified:** tools/arrconf/arrconf/__main__.py
- **Verification:** `uv run mypy arrconf/__main__.py arrconf/diff_cmd.py` exits 0 with "Success: no issues found"
- **Committed in:** bc7ac98

**2. [Rule 1 - Bug] ruff D205 docstring format violation**
- **Found during:** Task 6.2 (post-edit ruff check)
- **Issue:** Multi-line docstring for `_selected_apps` had summary line and description without a blank line separator (D205)
- **Fix:** Restructured docstring to have a short summary first line then blank line then details
- **Files modified:** tools/arrconf/arrconf/__main__.py
- **Verification:** `uv run ruff check arrconf/__main__.py` exits 0
- **Committed in:** bc7ac98

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs — both type/style correctness, no scope change)
**Impact on plan:** Both fixes necessary for CI compliance. No scope creep.

## Snapshot Baseline (Task 6.1 — pre-done)

- **Location:** `snapshots/before-phase-3-2026-05-11/`
- **Commit:** `7199cbe`
- **Anti-leak audit:** Clean (all apiKey/password/token/userName fields with privacy=* redacted; server-side `********` masks left intact)
- **ROADMAP success criterion 1:** Satisfied

## JSON Schema Regeneration

Key shape changes vs. old schema:
- Removed: `AppsConfig`, `SonarrConfig` (old indirection via `apps:` top-level key)
- Added: `RadarrInstance`, `ProwlarrInstance`, `AppEntry`, `AppsSection`, `HostConfigSection`, `IndexersSection`, `DownloadClientsSection`, `NotificationsSection`, `RootFoldersSection`
- `AppEntry.type.enum`: `["radarr", "sonarr"]`
- `AppEntry.sync_level.enum`: `["addOnly", "disabled", "fullSync"]`
- RootConfig properties: `sonarr`, `radarr`, `prowlarr` (flat top-level, no `apps:` wrapper)
- test_schema_gen.py D-15 CI gate: 4 tests passing (was `--ignore`d since Plan 02)

## Release Artifacts

- **Tag:** `v0.2.0` (annotated object)
- **Tag object SHA:** `77c89a2b360911b3e2895abc357c3079af628f2a` (refs/tags/v0.2.0)
- **CI run:** 25660722478 (`conclusion: success`, `headBranch: v0.2.0`)
- **GHCR image:** `ghcr.io/tom333/arr-stack-arrconf:0.2.0`
- **Operator verification:** Task 6.5 checkpoint — PENDING (see below)

## ROADMAP Phase-3 Success Criteria Status

1. Pre-Phase-3 baseline snapshot committed ✅ — `snapshots/before-phase-3-2026-05-11/` (commit 7199cbe, 6 apps, anti-leak clean)
2. apply/diff dispatch to sonarr + radarr + prowlarr ✅ — __main__.py updated (commit bc7ac98)
3. diff_cmd.py exposes diff_radarr + diff_prowlarr ✅ — (commit bc7ac98)
4. schemas/arrconf-schema.json regenerated with Phase-3 RootConfig ✅ — (commit 2c05cee)
5. test_schema_gen.py passes — D-15 gate restored ✅ — 4 tests passing
6. v0.2.0 tag pushed + CI succeeded ✅ — CI run 25660722478 green
7. GHCR anon-pull verification — PENDING operator Task 6.5 checkpoint

**Phase 3 closure recommendation:** After operator approves Task 6.5, run `/gsd-verify-work 03` to run the verification pass before `/gsd-progress` advances the milestone.

## Issues Encountered

None beyond the two auto-fixed mypy/ruff issues documented in Deviations.

## User Setup Required

Task 6.5 operator action: verify `ghcr.io/tom333/arr-stack-arrconf:0.2.0` is anonymously pullable.

```bash
curl -sI \
  -H "Accept: application/vnd.oci.image.index.v1+json" \
  -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
  https://ghcr.io/v2/tom333/arr-stack-arrconf/manifests/0.2.0
# Expected: HTTP/2 200

docker pull ghcr.io/tom333/arr-stack-arrconf:0.2.0
docker inspect ghcr.io/tom333/arr-stack-arrconf:0.2.0 --format='{{.Config.User}}'
# Expected: 1000:1000
```

## Next Phase Readiness

- Phase 4 (umbrella chart) can reference `ghcr.io/tom333/arr-stack-arrconf:0.2.0` pending Task 6.5 approval
- All 3 reconcilers wired and tested; CLI CLI `arrconf apply` / `arrconf diff` target sonarr+radarr+prowlarr by default
- D-15 schema drift gate active: any future config.py change without re-running `schema-gen` will fail CI

---
*Phase: 03-extend-arrconf*
*Completed: 2026-05-11*
