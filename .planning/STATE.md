---
gsd_state_version: 1.0
milestone: v3.2.0
milestone_name: milestone
status: executing
stopped_at: Phase 02.1 context gathered
last_updated: "2026-05-08T09:20:23.770Z"
last_activity: 2026-05-08 -- Phase 02.1 planning complete
progress:
  total_phases: 10
  completed_phases: 3
  total_plans: 15
  completed_plans: 11
  percent: 73
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-07)

**Core value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.
**Current focus:** Phase 02 — arrconf-cluster-validation

## Current Position

Phase: 02 (arrconf-cluster-validation) — CLOSED (PARTIAL — see Carry-forward)
Phase 2.1 (interrupt) — INSERTED to fix field-merge before Phase 3
Last activity: 2026-05-08 -- Phase 02.1 planning complete

Progress: [██████████] 100% (5/5 plans executed; 1 plan partial — 02-05)

### Phase 2 final state

- Plan 02-01 ✅ Snapshot baseline
- Plan 02-02 ✅ v0.1.2 image released, GHCR public
- Plan 02-03 ✅ my-kluster chart authored
- Plan 02-04 ✅ PR1 dry-run, success criterion #3 satisfied (zero writes)
- Plan 02-05 ⚠️ PR2 apply PARTIAL — tag created in Sonarr but PUT downloadclient failed; drift demo deferred

### ROADMAP success criteria status

- #1 baseline snapshot ✅
- #2 CronJob exists with envFrom secret ✅
- #3 dry-run = zero writes ✅
- #4 download_client managed by arrconf ⚠️ PARTIAL (tag created, not attached)
- #5 drift detection ⏭️ UNTESTED (deferred to Phase 2.1)

### Wave 1 deliverables (committed in arr-stack)

- 02-01: snapshots/before-phase-2-2026-05-08/ + evidence/.gitkeep (38fa3ce + 6a1795e SUMMARY)
- 02-02: ghcr.io/tom333/arr-stack-arrconf:0.1.2 published, anon-pullable; HUMAN-UAT #1 passed (76e2c97 retarget, db0f163 Dockerfile fix, c6585dd SUMMARY)

### Wave 2 deliverables

- 02-03 (arr-stack committed):
  - .cluster-services capture file (f674f86)
  - 02-PATTERNS.md + 02-RESEARCH.md credential redactions (cf1a808 — 5 occurrences of API key literals)
  - 02-03-SUMMARY.md (13f0de0)
- 02-03 (my-kluster — committed via PR1 #1366, see Wave 3 below):
  - 8 chart files + ArgoCD App
  - secrets/arrconf-secret.yaml — gitignored, on disk only, manually `kubectl apply`'d in Wave 3

### Wave 3 deliverables

- 02-04 (arr-stack committed):
  - evidence/pr1-job-logs-2026-05-08.log (4e18965)
  - snapshots/post-phase2-pr1-2026-05-08/ (b9f72f0)
  - 02-04-SUMMARY.md (7a928a9)
- 02-04 (my-kluster committed via 2 PRs):
  - PR1 #1366 (merged 06:56:19Z): chart + ArgoCD App
  - PR-fix #1367 (merged): cronjob args reorder — `--config` BEFORE `apply` subcommand
- Cluster state (dry-run mode, ARRCONF_DRY_RUN=true):
  - Secret/arrconf-env in selfhost (manually applied — no ArgoCD tracking-id)
  - ConfigMap/arrconf in selfhost (rendered from files/arrconf.yml)
  - CronJob/arrconf in selfhost (schedule "0 */4 * * *", concurrencyPolicy Forbid, volumeMounts==1 named config)
  - Application/arrconf in argocd (Synced + Healthy)
- Smoke job arrconf-pr1-smoke-1778224797 completed in 12s; W-06 events verified:
  - would_create_managed_tag (1)
  - plan_action action=update diff_fields=[fields, tags] (1)
  - dry_run_skip (1)
  - managed_tag_created (0 — dispositive dry-run proof)
- Snapshot diff: only 2 noise files (rootfolder.json freeSpace, system_status.json startTime); critical files (downloadclient.json, tag.json) IDENTICAL to baseline.

### Pre-existing my-kluster state — STASHED

2 stashes pushed before Wave 2 to keep B-01/W-NEW-01 honest:

- `stash@{0}: pre-arrconf-Phase2-tracked-2026-05-08` (README.md, beszel/beszel.yml)
- `stash@{1}: pre-arrconf-Phase2-2026-05-08` (CLAUDE.md, TODO.md, config/sc-nfs.yaml, config/test-volume.yaml, openmetadata/, scripts/)

POP REMINDER: After Phase 2 closes (Plan 02-05 done), run twice in my-kluster:

```bash
git stash pop   # first pop -> stash@{0} restored
git stash pop   # second pop -> the other stash restored
```

### Resume entry point — Phase 2.1 (interrupt)

Run `/gsd-discuss-phase 2.1` then `/gsd-plan-phase 2.1` then `/gsd-execute-phase 2.1`. Single-plan phase with one objective:

**Modify `tools/arrconf/arrconf/reconcilers/sonarr.py` (and possibly `differ.py`) so the PUT body for `downloadclient` preserves cluster-stored field values for any field whose YAML value is empty `""` OR matches a well-known-sensitive field name (`username`, `password`, `apiKey`, `token`, `passkey`, etc.).**

Test plan (closes Phase 2 success criteria #4 and #5):

1. Modify reconciler + add unit tests for the merge logic
2. Bump to v0.1.3 (CI builds image)
3. Open PR3 in my-kluster bumping image.tag 0.1.2 → 0.1.3
4. Unsuspend CronJob (or merge a small revert PR if ArgoCD already auto-unsuspended)
5. Force smoke job → verify W-06 events + PUT 200
6. Re-snapshot Sonarr — `downloadclient.json[0].tags | length > 0` ✅
7. Run drift demo runbook (Plan 02-05 Task 5.2 steps 1-10) — capture evidence + W-01 forensic snapshot + W-04 dispositive
8. Close Phase 1 HUMAN-UAT #3

### What was Plan 02-05 Wave 4 (now superseded by Phase 2.1) — kept for reference

1. Author one-line PR2 in my-kluster: `charts/arrconf/values.yaml` `arrconfDryRun: true` → `false`. Push branch + open PR.
2. **OPERATOR**: review and merge PR2.
3. After ArgoCD sync (may need `kubectl annotate application arrconf -n argocd argocd.argoproj.io/refresh=hard --overwrite` based on Wave 3 experience), force smoke job: `kubectl create job --from=cronjob/arrconf arrconf-pr2-smoke -n selfhost`.
4. Verify W-06 apply-mode events: `managed_tag_created` ≥1, `would_create_managed_tag` ==0, `dry_run_skip` ==0. Persist logs to `evidence/pr2-job-logs-<date>.log`.
5. Post-PR2 snapshot Sonarr (port-forwards needed). `sonarr/tag.json` MUST gain `arrconf-managed` entry (success criterion #4).
6. Drift demo runbook (REQ-drift-detection):
   - W-01 forensic snapshot BEFORE: `tools/snapshot/snapshot.sh --apps sonarr --output snapshots/drift-test-<date>/`
   - Mutate qBittorrent download_client name in Sonarr UI (or via API curl) to `qBittorrent-DRIFT`
   - Force smoke job: `kubectl create job --from=cronjob/arrconf arrconf-drift-demo -n selfhost`
   - Capture logs to `evidence/drift-demo-<date>.log`
   - W-04 dispositive value-equality: log contains `plan_action action=update` AND post-snapshot `downloadclient.json` name field == "qBittorrent" (reverted to YAML value)
7. Close 01-HUMAN-UAT items #2 (VS Code autocomplete) + #3 (live round-trip — naturally satisfied by Phase 2 closure).
8. Plan 02-05 SUMMARY documenting all of the above.

After plan 02-05: phase verification (gsd-verifier on phase 02 OR manual ROADMAP success criteria check) + ROADMAP marking phase 02 complete + STATE.md update.

### Carry-forward / open items

- v0.1.0 + v0.1.1 tags exist on origin but did NOT produce GHCR images (bootstrap artifacts only — see 02-02-SUMMARY.md deviations).
- Phase 1 HUMAN-UAT items #2 (VS Code autocomplete demo) + #3 (live round-trip) still pending (see 01-HUMAN-UAT.md). #3 is targeted for Phase 2 closure.
- `gh` CLI account `tguyader` token lacks `read:packages` scope — workaround documented in 02-02-SUMMARY.md (substitute `gh api` package query with anonymous registry endpoint).
- Plan 02-03 <interfaces> block line 146 has the un-quoted `description: arrconf — ... (Phase 2 scope: ...)` that fails helm lint — already fixed in actual Chart.yaml; if 02-03 is re-executed the executor must quote it. Documented in 02-03-SUMMARY.md §Deviation 2.

## Performance Metrics

**Velocity:**

- Total plans completed: 3
- Average duration: — min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 0 | 3 | - | - |

**Recent Trend:**

- Last 5 plans: (none yet)
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

7 LOCKED ADRs already imported from `spec.md` §11 — see PROJECT.md `<decisions>` block for full list and rationale.

Quick reference:

- **ADR-1** Script Python custom (vs Buildarr/Terraform/Flemmarr)
- **ADR-2** Helm dependencies sur app-template (Option A)
- **ADR-3** Image arrconf sur GHCR public
- **ADR-4** Repo séparé (vs extension my-kluster)
- **ADR-5** configarr conservé (frontière dure quality_profiles/custom_formats/quality_definitions/media_naming)
- **ADR-6** Snapshot baseline avant toute écriture
- **ADR-7** Single instance Sonarr/Radarr + tags (pas multi-instance)

### Pending Todos

None yet — projet vient d'être bootstrappé. Ouvertes mais non décidées : 10 open questions Q1-Q10 (cf PROJECT.md "Open Questions") routées vers les phases concernées :

- Q3 / Q4 / Q6-Q8 → Phase 1 ou 2 (arbitrage technique amont)
- Q2 → Phase 4 (multi-alias `bjw-s/app-template` syntaxe)
- Q1, Q10 → Phase 6 (compat Seerr, routing tags)
- Q9 → Phase 7 (Jellyfin auth header)
- Q5 → tranchée par ADR-5 (ne plus traiter comme open question)

### Blockers/Concerns

None yet. Risque suivi à anticiper :

- **Q1 bloquante Phase 6** : si Seerr v3.2.0 a divergé de l'API Overseerr/Jellyseerr sur les endpoints critiques, Phase 6 doit être réévaluée (test à faire dès qu'on commence la phase, pas au milieu).

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-08T08:45:29.823Z
Stopped at: Phase 02.1 context gathered
Resume file: .planning/phases/02.1-field-merge-fix/02.1-CONTEXT.md
