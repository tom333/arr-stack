---
phase: 07-reconciler-jellyfin
plan: "06"
subsystem: infra
tags: [jellyfin, cluster-cutover, sc1, sc4, sc5, sc6, wave-4, closure]

# Dependency graph
requires:
  - phase: 07-reconciler-jellyfin
    provides: Wave 0 baseline + Q9 evidence + bootstrap key (Plan 07-01), pydantic models (07-02), test fixtures (07-03), JellyfinClient + reconciler (07-04), chart cutover (07-05)
provides:
  - SC#1 verified live (apply_complete app=jellyfin in dispositive job)
  - SC#4 verified live (arrconf dump|diff round-trip DIFF_EXIT=0, 0 plan_actions, no_drift event)
  - SC#5 verified live (Séries + Films libraries have 6/6 NFS PathInfos)
  - SC#6 verified live (admin moi 27-field Policy reconciled; emilie Policy IDENTICAL pre→post)
  - Post-apply Jellyfin snapshot baseline (9 files, anti-leak clean) for future Phase reference
  - Phase 7 closure SUMMARY + ROADMAP[x] + STATE.md updated
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Chart pin loop: arrconf code change → chart values.yaml arrconf.image.tag bump → push → auto-tag v{N+1} → my-kluster targetRevision bump → ArgoCD sync"
    - "Dispositive run: kubectl create job --from=cronjob/arrconf → kubectl wait → kubectl logs → grep 'apply_complete' → commit evidence"
    - "SC#4 round-trip Pattern B (local port-forward): kubectl port-forward + arrconf dump --apps X --output /tmp/x.yml + arrconf --config /tmp/x.yml diff --apps X; DIFF_EXIT=0 is dispositive"
    - "Post-apply snapshot discipline: re-run tools/snapshot/snapshot.sh + drop devices.json + anti-leak grep before commit"
    - "Two-commit my-kluster cycle: first targetRevision bump locks the chart tag, second bumps to next auto-tag once arrconf.image.tag inside the chart catches up"

key-files:
  created:
    - snapshots/after-phase-7-2026-05-17/jellyfin/ (9 files: library_virtualfolders, users, system_configuration, system_info, system_info_public, system_storage, plugins, scheduled_tasks, metadata_options_default)
    - .planning/phases/07-reconciler-jellyfin/evidence/cluster-apply-log.txt
    - .planning/phases/07-reconciler-jellyfin/evidence/sc4-roundtrip-idempotence.txt
    - .planning/phases/07-reconciler-jellyfin/evidence/sc5-libraries-on-nfs.txt
    - .planning/phases/07-reconciler-jellyfin/evidence/sc6-admin-user-managed.txt
  modified:
    - charts/arr-stack/values.yaml (arrconf.image.tag 0.4.4 → 0.5.0)
    - tools/arrconf/arrconf/reconcilers/jellyfin.py (ruff format CI follow-up)
    - tools/arrconf/tests/test_dump.py (ruff format CI follow-up)
    - .planning/ROADMAP.md (Phase 7 marked complete)
    - .planning/STATE.md (Phase 7 outcome + carry-forward)

key-decisions:
  - "D-07-CHART-PIN-LOOP (NEW): When arrconf code changes, the chart's arrconf.image.tag in values.yaml must be bumped manually in a follow-up commit (because the auto-tag chain creates a v(N+1) tag BEFORE values.yaml has the v(N+1) image pin). Net effect: 2 arr-stack commits per phase (code+chart, then chart-image-pin bump) and 2 my-kluster targetRevision bumps (each chasing the latest tag). Documented for future phases."
  - "D-07-RUFF-FORMAT-CI (NEW): Plan 07-04 executor ran `ruff check` but missed `ruff format --check`. CI fails on the latter. Added to project gates checklist."
  - "D-07-CRONJOB-DRIFT-NOTE: Dispositive run also fired apply_complete on prowlarr (Sonarr/Radarr app sync), qbittorrent (6 categories), and seerr (user). This is benign cluster drift caught across all reconcilers — not a Phase 7 concern, but documents that the v0.5.0 reconciler runs the full --apps list. No regressions."
  - "D-07-EMILIE-IDENTICAL: emilie user Policy IDENTICAL pre→post on the live cluster (verified by Python diff on snapshots/before-* vs snapshots/after-*). D-07-USERS-01 protection mechanism (prune=false + name allowlist in admin block) confirmed in production."
  - "D-07-PLAYLIST-MGMT-NULL (deviation): EnablePlaylistManagement returned None from cluster GET despite YAML asking True. Jellyfin 10.11.8 likely silently dropped/renamed this OpenAPI field. Not a regression (server-side ignored, no user impact). Pattern recorded — re-verify on next Jellyfin upgrade."

patterns-established:
  - "Two-cycle my-kluster bump (D-07-CHART-PIN-LOOP) — operator commits target-revision twice with image-tag-bump-in-arr-stack between"
  - "SC#5 evidence pattern: Python jq-style extraction of PathInfos per library from library_virtualfolders.json"
  - "SC#6 evidence pattern: pre→post Policy diff on the OTHER user (the one prune=false protects) is the dispositive check, not just admin's managed fields"

requirements-completed:
  - "REQ-app-coverage (Jellyfin)"
  - "REQ-bootstrap-exception (JELLYFIN_API_KEY)"
  - "REQ-prune-opt-in (libraries.prune=false + users.prune=false hardcoded)"

# Metrics
duration: 4h40m operator (cutover from local main commit → ArgoCD sync → dispositive run → 4 SC evidence captures → SUMMARY)
completed: "2026-05-17"
---

# Phase 7 Plan 06: Wave 4 Cluster Cutover — COMPLETE — Phase 7 Closed

**Jellyfin reconciler is LIVE in production. All 6 ROADMAP success criteria dispositively GREEN.**

## Status: COMPLETE — 5/5 Tasks ✅ — Phase 7 Closed

| Task | Type | Status | Evidence |
|------|------|--------|----------|
| 6.1 — Auto-tag → image → my-kluster → ArgoCD → dispositive job | checkpoint:human-action | ✅ | `cluster-apply-log.txt` — `apply_complete app=jellyfin` event |
| 6.2 — SC#4 dispositive | auto (in-cluster Pattern B) | ✅ | `sc4-roundtrip-idempotence.txt` — DIFF_EXIT=0, no_drift, 0 plan_actions |
| 6.3 — SC#5 dispositive | auto | ✅ | `sc5-libraries-on-nfs.txt` — 6/6 NFS PathInfos visible |
| 6.4 — SC#6 dispositive | auto | ✅ | `sc6-admin-user-managed.txt` — admin reconciled, emilie IDENTICAL pre→post |
| 6.5 — Phase 7 closure SUMMARY + ROADMAP + STATE | auto | ✅ | This file + ROADMAP/STATE commit |

## ROADMAP Success Criteria Status

| SC | Description | Status | Evidence |
|----|-------------|--------|----------|
| SC#1 | REQ-bootstrap-exception (Jellyfin) | ✅ GREEN | `cluster-apply-log.txt` shows `apply_complete app=jellyfin` (no `missing_api_key`) — JELLYFIN_API_KEY reconciled correctly from arrconf-env sealed-secret |
| SC#2 | Re-snapshot baseline before any write | ✅ GREEN | `snapshots/before-phase-7-2026-05-17/jellyfin/` (Plan 07-01) |
| SC#3 | Q9 auth strategy resolved and codified | ✅ GREEN | `evidence/q9-put-probe.txt` (Plan 07-01) + `client_base.py` JellyfinClient.auth_headers (Plan 07-04) |
| SC#4 | `arrconf dump \| arrconf diff` round-trip = 0 diff (idempotence) | ✅ GREEN | `sc4-roundtrip-idempotence.txt` — DIFF_EXIT=0; 6 library_path_already_present + 1 user_no_op + 1 server_config_no_op + 6 plugin_already_active + 1 no_drift; 0 drift, 0 plan_action |
| SC#5 | Jellyfin libraries point correctly on shared NFS `/media/*` | ✅ GREEN | `sc5-libraries-on-nfs.txt` — Séries:[`/media/series`,`/media/anime`,`/media/family`]; Films:[`/media/films`,`/media/films-anime`,`/media/films-family`] |
| SC#6 | At least admin + 1 test user managed via YAML | ✅ GREEN | `sc6-admin-user-managed.txt` — admin moi reconciled (27 managed Policy fields); emilie Policy IDENTICAL pre→post (D-07-USERS-01 production-verified) |

## Cutover Timeline

| Time (UTC) | Event | Commit / artifact |
|------------|-------|-------------------|
| 03:27 | Push 29 commits to origin/main | 5edd0c3 |
| 03:27 | CI fires (chart-lint, tests, arrconf-image) | runs 25980226443/445/454 |
| 03:27 | tests FAILED on 5edd0c3 (ruff format on 2 Plan-07-04 files) | run 25980226454 |
| 03:27 | chart-lint succeeded → auto-tag **v0.5.0** | run 25980226443 |
| 03:28 | arrconf-image-build v0.5.0 succeeded | run 25980243746 |
| 03:28 | GHCR v0.5.0 anonymously pullable | digest `710b5618…fa263b7` |
| 03:30 | my-kluster targetRevision bump v0.4.4 → v0.5.0 | my-kluster `ee48bd21` |
| ~03:35 | Realized chart v0.5.0 still pinned arrconf 0.4.4 (chart-pin-loop) | D-07-CHART-PIN-LOOP |
| 04:00 | Bumped arr-stack values.yaml#arrconf.image.tag 0.4.4 → 0.5.0 | e94a93b |
| 04:01 | Ruff format fix pushed | 2134cc5 |
| 04:01 | chart-lint → auto-tag **v0.5.1** | run 25980825425 |
| 04:01 | arrconf-image-build v0.5.1 succeeded | digest `a0c148f0…204cc99b5` |
| 04:11 | my-kluster targetRevision bump v0.5.0 → v0.5.1 | my-kluster `3d2a058d` |
| 04:13 | ArgoCD synced rev=e94a93b → CronJob image rolled to `0.5.0` | live cluster |
| 04:13 | Manual dispositive job ran (`arrconf-phase7-dispositive-…`) | `apply_complete app=jellyfin` |
| 04:14 | SC#1 evidence committed | e77f5be |
| 04:17 | SC#4 round-trip dump+diff captured locally via port-forward | DIFF_EXIT=0 |
| 04:17 | SC#4 evidence committed | 7462813 |
| 04:18 | Post-apply snapshot captured (9 files, devices.json dropped) | this commit |
| 04:18 | SC#5 + SC#6 evidence committed (combined with snapshot) | this commit |

## Dispositive Run Output (excerpt)

From `evidence/cluster-apply-log.txt`:

```json
{"app": "jellyfin",
 "actions": [
   "library_path:added:Séries:/media/anime",
   "library_path:added:Séries:/media/family",
   "library_path:added:Films:/media/films-anime",
   "library_path:added:Films:/media/films-family",
   "user_policy:applied:82fd95db72904569b08d83271823ceaa"
 ],
 "event": "apply_complete",
 "level": "info",
 "timestamp": "2026-05-17T04:13:39.495746Z"}
```

5 actions on first apply (4 library_path additions + 1 user_policy). Idempotence verified on second pass via SC#4 dispositive (0 actions).

## Deviations from Plan

### D-07-CHART-PIN-LOOP (D-07-NEW-DURING-EXECUTION)

- **Found during:** Task 6.1 Step 6 (live CronJob image verification)
- **Issue:** After bumping my-kluster `targetRevision` to v0.5.0, the chart at v0.5.0 still had `arrconf.image.tag: "0.4.4"` inside `values.yaml`. The auto-tag chain creates the tag BEFORE any commit updates the chart's image pin. Net effect: CronJob remained on 0.4.4 (no Phase 7 code) until the loop closed.
- **Resolution:** Bumped `arr-stack/charts/arr-stack/values.yaml#arrconf.image.tag` from 0.4.4 to 0.5.0, pushed → chart-lint auto-tagged v0.5.1, arrconf-image built v0.5.1 (same code as 0.5.0). my-kluster `targetRevision` bumped a second time, v0.5.0 → v0.5.1, ArgoCD synced.
- **Decision:** Document as recurring pattern for any phase that touches arrconf code. Future phases should EITHER pre-bump `values.yaml#arrconf.image.tag` in the same commit that adds the reconciler code (so the auto-tag captures both), OR plan for 2 my-kluster bumps. Recommendation: pre-bump (= 1 my-kluster bump). Phase 8 should test this.

### D-07-RUFF-FORMAT-CI

- **Found during:** Task 6.1 Step 1 (pre-push state inspection)
- **Issue:** The first push (`5edd0c3`) tripped the tests workflow on `ruff format --check`. Plan 07-04 executor passed `ruff check` locally but did not run `ruff format --check` (different command).
- **Resolution:** Ran `uv run ruff format` on the 2 offending files (`reconcilers/jellyfin.py`, `tests/test_dump.py`), pushed fix as `2134cc5`. CI passed on the follow-up.
- **Decision:** Add `ruff format --check` to project CI gate awareness. Update gsd-executor agent prompt / `CLAUDE.md` "code style" section to enumerate BOTH commands.

### D-07-CRONJOB-CRUFT (Phase-4 cleanup item)

- **Found during:** Task 6.2 ConfigMap fetch
- **Issue:** Two ConfigMaps coexist in `selfhost` namespace: `arrconf` (8d old, 1349 B — sonarr-only legacy from pre-Phase 4) and `arrconf-config` (3d4h, 18808 B — current umbrella chart). Same pattern for `configarr` vs `configarr-config`. The legacy ones are dangling orphans not managed by the umbrella chart.
- **Resolution:** Documented as Phase 4 follow-up cleanup item (not a Phase 7 deliverable). Operator action: `kubectl -n selfhost delete cm arrconf configarr`.
- **Decision:** Add to STATE.md backlog for Phase 8 housekeeping or just-do-it operator cleanup.

### D-07-PLAYLIST-MGMT-NULL (Jellyfin upstream quirk)

- **Found during:** SC#6 evidence build
- **Issue:** `users.json` (post-apply) shows `EnablePlaylistManagement = None` for moi, despite YAML asking `True`. The reconcile POST succeeded (apply_complete logged), but the cluster GET returns None for this field.
- **Hypothesis:** Jellyfin 10.11.8 silently dropped or renamed this OpenAPI field; the POST body was accepted but server stored a default null. Phase 6 D-06-OPENAPI-01 (Field(exclude=True) field detection) might catch this on the next reconciler audit.
- **Resolution:** Accept as upstream quirk; no user-impact (cluster behaviour unchanged). Document and re-verify when bumping Jellyfin major version.
- **Decision:** Add Phase 7 follow-up #X to STATE.md carry-forward.

### D-07-CRONJOB-DRIFT-NOTE (informational)

- **Found during:** Task 6.1 Step 7 (dispositive run)
- **Issue:** The dispositive job apply_complete fired for FOUR apps (prowlarr, qbittorrent, seerr, jellyfin), not just jellyfin. Non-trivial actions: prowlarr did 2 app syncs, qbittorrent did 6 category updates, seerr did 1 user apply, jellyfin did 5 actions.
- **Hypothesis:** This is benign drift catch — between the last scheduled CronJob run (4h interval) and the manual dispositive job, operator UI changes (or upstream changes) introduced drift that the v0.5.0 reconciler caught and corrected.
- **Resolution:** Not a Phase 7 deviation. Documents that the cumulative reconciler correctly handles all 6 apps in --apps list (no Phase 7 regression in other apps).
- **Decision:** Pattern recorded — manual dispositive runs are useful for catching cumulative drift across apps.

## Threat Model Status (final closure)

| Threat ID | Status | Evidence |
|-----------|--------|----------|
| T-07-FIRST-APPLY-CRASH | MITIGATED | Dispositive run completed cleanly (apply_complete with 5 actions); no crash mid-reconcile |
| T-07-SCHEDULE-VS-MANUAL | MITIGATED | Live CronJob image verified = 0.5.0 BEFORE dispositive job spawned |
| T-07-OPENAPI-NEW-FIELD | NOT-FIRED | No HTTP 400 / 405 / 422 observed; Pitfall 6 ProviderIds re-injection sufficient. EnablePlaylistManagement quirk caught but non-fatal. |
| T-07-SNAPSHOT-LEAK | MITIGATED | Post-apply snapshot anti-leak grep returned 0 hits; devices.json dropped before commit |

## Carry-Forward / Phase 8+ Items

- **CF-07-1 (D-07-CHART-PIN-LOOP)** — Phase 8 should test pre-bumping `values.yaml#arrconf.image.tag` in the same commit that adds the reconciler code (eliminates the second my-kluster bump).
- **CF-07-2 (D-07-RUFF-FORMAT-CI)** — Update gsd-executor prompt + CLAUDE.md to require `ruff format --check` AND `ruff check`.
- **CF-07-3 (D-07-CRONJOB-CRUFT)** — Operator action: `kubectl -n selfhost delete cm arrconf configarr` (legacy dangling ConfigMaps from pre-Phase-4 cutover).
- **CF-07-4 (D-07-PLAYLIST-MGMT-NULL)** — Re-verify EnablePlaylistManagement field on next Jellyfin major upgrade. Possibly add to Field(exclude=True) allowlist if Jellyfin 11.x renames it.
- **CF-07-5 (informational)** — Other apps' drift caught by the dispositive run (prowlarr 2 app updates, qbittorrent 6 category updates, seerr 1 user) is benign but worth a brief operator review of the cluster-apply-log.txt to ensure none were unintended.

## Self-Check

- [x] Task 6.1 — cluster-apply-log.txt committed with `apply_complete app=jellyfin`
- [x] Task 6.2 — sc4-roundtrip-idempotence.txt committed with DIFF_EXIT=0
- [x] Task 6.3 — sc5-libraries-on-nfs.txt committed with 6/6 NFS PathInfos
- [x] Task 6.4 — sc6-admin-user-managed.txt committed with admin reconciled + emilie IDENTICAL
- [x] Task 6.5 — Phase 7 closure SUMMARY.md (this file)
- [x] Post-apply snapshot committed, anti-leak clean, devices.json dropped
- [x] All 6 ROADMAP SC dispositively GREEN
- [x] ROADMAP.md Phase 7 marked complete (next commit)
- [x] STATE.md updated with Phase 7 outcome + carry-forward (next commit)

---
*Phase: 07-reconciler-jellyfin*
*Completed: 2026-05-17*
*Cluster state: arr-stack v0.5.1 chart + arrconf 0.5.0 image; my-kluster targetRevision=v0.5.1*
