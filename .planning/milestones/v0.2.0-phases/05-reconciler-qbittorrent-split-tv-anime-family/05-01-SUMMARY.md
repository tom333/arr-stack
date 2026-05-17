---
phase: 05-reconciler-qbittorrent-split-tv-anime-family
plan: 01
subsystem: infra
tags: [snapshot, kubernetes-secret, baseline, adr-6, bootstrap]

requires:
  - phase: 04-umbrella-chart-migration-des-9-apps
    provides: K8s Secret arrconf-env (1 key) + 3 cluster apps (sonarr, radarr, qbittorrent) reachable from operator workstation
provides:
  - K8s Secret arrconf-env expanded from 1 → 5 keys (RADARR_API_KEY, PROWLARR_API_KEY, QBT_USER, QBT_PASS added)
  - ADR-6 baseline snapshot snapshots/before-phase-5-2026-05-14/ (44 JSON files across 3 apps)
  - Evidence file proving Secret bootstrap completed without leaking values
affects: [05-02, 05-04, 05-07, 05-08]

tech-stack:
  added: []
  patterns:
    - "Operator-managed K8s Secret via gitignored my-kluster/secrets/arrconf-secret.yaml (ESO migration deferred to Phase 8)"
    - "ADR-6 snapshot + jq-redaction audit (README Option A) before commit"

key-files:
  created:
    - snapshots/before-phase-5-2026-05-14/{sonarr,radarr,qbittorrent}/
    - .planning/phases/05-reconciler-qbittorrent-split-tv-anime-family/evidence/secret-bootstrap-confirmation.txt
  modified:
    - tools/snapshot/snapshot.sh (qBit login HTTP 204 acceptance fix)

key-decisions:
  - "Snapshot script bug fix landed inside Plan 05-01 (single line) rather than spawning a follow-up plan — qBit 5.x changed login response from 200 to 204, blocking every future snapshot until fixed"
  - "Followed README Option A (jq-redaction) to remove apiKey/password/token/webhookUrl values before committing; baseline-2026-05-07 used the same approach"
  - "Supplemented snapshot.sh output with curl-captured /api/v3/series and /api/v3/movie (plan acceptance requires series.json and movie.json which the script does not yet capture)"

patterns-established:
  - "Wave 0 pre-flight gate combines operator action + automated snapshot in a single plan, allowing autonomous waves to proceed once both are GREEN"
  - "qBittorrent categories.json alias of torrents_categories.json kept for plan-acceptance-criteria stability"

requirements-completed: [REQ-app-coverage]

duration: ~10 min
completed: 2026-05-14
---

# Plan 05-01: Wave 0 Pre-Flight Gate Summary

**K8s Secret bootstrapped to 5 keys + ADR-6 baseline captured (sonarr 8 series, radarr 11 movies, qBit 3 categories) with audit-clean redaction**

## Performance

- **Duration:** ~10 min
- **Tasks:** 2/2 complete
- **Files modified:** 1 cluster Secret + 1 evidence file + 44 snapshot JSON files + 1 script bug-fix

## Accomplishments

- Extended `my-kluster/secrets/arrconf-secret.yaml` from 1 → 5 keys (RADARR_API_KEY, PROWLARR_API_KEY, QBT_USER, QBT_PASS) using `stringData:` (no base64 needed)
- `kubectl apply` against `selfhost/arrconf-env` returned `configured` — gate #1 PASS
- Evidence file `.planning/.../evidence/secret-bootstrap-confirmation.txt` contains exactly the 5 expected key names, no values (anti-leak grep PASS)
- ADR-6 baseline snapshot `snapshots/before-phase-5-2026-05-14/` captures sonarr (17 files), radarr (18 files), qBit (9 files) plus the supplemental series.json, movie.json, categories.json
- All 44 JSON files pass the README Option A redaction audit (no `apiKey`/`password`/`token` values remain)

## Files Created/Modified

- `my-kluster/secrets/arrconf-secret.yaml` — added 4 keys (gitignored, not committed in arr-stack repo)
- `.planning/phases/05-reconciler-qbittorrent-split-tv-anime-family/evidence/secret-bootstrap-confirmation.txt` — kubectl JSON key dump
- `snapshots/before-phase-5-2026-05-14/sonarr/*.json` (17 endpoints + supplemental `series.json`)
- `snapshots/before-phase-5-2026-05-14/radarr/*.json` (18 endpoints + supplemental `movie.json`)
- `snapshots/before-phase-5-2026-05-14/qbittorrent/*.json` (9 endpoints + supplemental `categories.json` alias of `torrents_categories.json`)
- `tools/snapshot/snapshot.sh` — accept HTTP 204 from qBit /auth/login (qBit 5.x behavior change)

## Decisions Made

- **Patched snapshot.sh in this plan.** qBit 5.x's `/api/v2/auth/login` returns 204 No Content on success (was 200 in 4.x). The script's strict `!= "200"` check would have blocked every future snapshot. One-line fix is technically scope-expansion but operationally necessary — documented here, no follow-up plan needed.
- **Manual jq redaction (README Option A).** snapshot.sh has no in-script redaction layer; the README documents post-snapshot jq redaction as the established sanitization step. Applied uniformly to all 3 apps via `walk(...)` jq filter.
- **Supplemented series.json + movie.json via curl.** Plan acceptance criteria require these names but snapshot.sh does not yet capture `/api/v3/series` or `/api/v3/movie`. Captured via direct curl to keep this plan unblocked; extending the script to include them belongs in a future hardening pass (out of Phase 5 scope).
- **Used `stringData:` not `data:` (base64).** Equivalent semantics, simpler diff. K8s converts internally on apply.

## Deviations from Plan

### Auto-fixed Issues

**1. [Blocking] qBittorrent login fails with HTTP 204 (snapshot.sh strict 200 check)**
- **Found during:** Task 1.2 (snapshot capture)
- **Issue:** Script rejected the successful 204 response and returned 1 — qBit dir was empty
- **Fix:** Allow both 200 and 204 in the success branch of the login check
- **Files modified:** `tools/snapshot/snapshot.sh`
- **Verification:** Re-ran with 3/3 apps OK, 0 warnings; qBit dir now contains 9 files
- **Committed in:** Task 1.2 commit

**2. [Missing capture] series.json / movie.json not produced by snapshot.sh**
- **Found during:** Task 1.2 acceptance verification (jq length checks)
- **Issue:** Plan acceptance requires `sonarr/series.json` len=8 and `radarr/movie.json` len=11 but the script's endpoint list omits `/api/v3/series` and `/api/v3/movie`
- **Fix:** Direct curl-to-file for both endpoints after the script run, then jq-redacted with the same filter
- **Verification:** `jq '. | length'` returns 8 and 11; redaction PASS
- **Committed in:** Task 1.2 commit (single atomic commit with the rest of the snapshot)

**3. [Naming] qbittorrent/categories.json absent**
- **Found during:** Task 1.2 acceptance verification
- **Issue:** Plan expects `categories.json` but script writes `torrents_categories.json`
- **Fix:** `cp torrents_categories.json categories.json` — keep both for backward compatibility with the established baseline shape and forward compatibility with the plan
- **Committed in:** Task 1.2 commit

---

**Total deviations:** 3 auto-fixed (1 blocking script bug, 2 missing-artifact gaps)
**Impact on plan:** All three fixes necessary to satisfy the acceptance criteria. No scope creep beyond the snapshot infrastructure that was already in this plan's expected output. snapshot.sh fix has broader benefit (every future snapshot).

## Issues Encountered

- Default shell aliases `mv -i` / `rm -i` triggered interactive confirmation prompts that swallowed the redaction loop's stdout; switched to `\cp` + post-pass `command find -delete` to bypass.
- qBit categories JSON shape is `{name: {savePath, downloadPath}}` (object), not an array — `jq 'keys'` gives the category names list as expected.

## User Setup Required

None additional. The operator-managed Secret pattern continues until Phase 8 (ESO migration).

## Next Phase Readiness

- Plans 05-02 through 05-07 unblocked (the cluster-apply gate #2 in Plan 02 will read this baseline at runtime; Plans 02/03 only touch local schema + fixtures).
- Plan 05-08 SC#5 idempotence proof has its dispositive baseline at `snapshots/before-phase-5-2026-05-14/`.
- Follow-up (out of Phase 5 scope): consider extending `snapshot.sh` to include `/api/v3/series` and `/api/v3/movie` endpoints natively, and to write `qbittorrent/categories.json` directly instead of relying on the `torrents_` prefix.

---
*Phase: 05-reconciler-qbittorrent-split-tv-anime-family*
*Completed: 2026-05-14*
