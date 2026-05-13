---
gsd_state_version: 1.0
milestone: v0.2.0
milestone_name: forceSave fix
status: Phase 03 complete
stopped_at: Phase 4 context gathered
last_updated: "2026-05-13T02:10:55.240Z"
last_activity: 2026-05-13 -- Phase 4 planning complete
progress:
  total_phases: 11
  completed_phases: 6
  total_plans: 43
  completed_plans: 34
  percent: 79
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-07)

**Core value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.
**Current focus:** Phase 4 — umbrella-chart-migration-des-9-apps

## Current Position

Phase: 4 (umbrella-chart-migration-des-9-apps) — PLANNED (v5.0.0; 9 plans across 8 waves; Wave 0 Task 1.1 evidence already captured at commit 2a94257)
Plan: 0 of 9 (ready to execute — start with `/gsd-execute-phase 4`)
Phase 2.1 (interrupt) — INSERTED to fix field-merge before Phase 3 — DONE
Last activity: 2026-05-13 -- Phase 4 replanned against app-template 5.0.0 baseline after ADR-6 drift discovery

Progress: [██████████] 100%

### Blocker — D-02.2-AUTH-REGRESSION (HIGH severity)

Sonarr's "Test" button on the qBit downloadclient returns 401/403 after v0.1.4 reconcile. Forensic shows the v0.1.4 `?forceSave=true` PUT bypassed Sonarr's pre-save validation and stored the API mask `"********"` (preserved by Phase 2.1 `merge_fields_for_put` helper) as the literal password value. ADR-8 accepted-risk realized in production. CronJob `arrconf` SUSPENDED at 2026-05-09T06:48:11Z. Recovery artifacts:

- `snapshots/forensic-phase2.2-auth-regression-2026-05-09T0648/` (Sonarr 17 JSON + qBittorrent 8 files, redacted, anti-leak clean)
- `.planning/phases/02.2-v0-1-4-forcesave-fix/evidence/forensic-credentials-diff-2026-05-09T0651.txt` (DISPOSITIVE: GET-side diff is EMPTY — proves the GET cannot detect the regression)
- `.planning/phases/02.2-v0-1-4-forcesave-fix/evidence/forensic-cronjob-logs-2026-05-09T0652.log` (compiled smoke + drift logs showing `merge_field_preserved` + `put_force_save_used` + `apply_complete` chain)
- Plan 06 SUMMARY §"Operator Visual Gate FAILED" + `deferred-items.md` D-02.2-AUTH-REGRESSION

**Required next action:** route to `/gsd-plan-phase 02.2 --gaps` (or equivalent) to scope a hotfix plan that ships v0.1.5 with credential-aware merge (Option A omit / Option B mask-detect / Option C scope-forceSave), operator-driven Sonarr UI password re-entry, behavioral W-04 dispositive (Sonarr Test API HTTP 200), and re-run of Task 6.4.

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
- #4 download_client managed by arrconf ✅ SATISFIED (tag attached via Plan 02.1-03 PR3 + Plan 02.1-04 Task 4.1 snapshot — `tags: [1]` confirmed in post-phase2.1-2026-05-09/sonarr/downloadclient.json + Sonarr API)
- #5 drift detection ✅ SATISFIED (detection ✅ — Plan 02.1-04 Task 4.2 captured `plan_action action=update` event + W-04 dispositive `RESTORED_PRIORITY == ORIGINAL_PRIORITY` confirmed + W-01 forensic snapshot present; automated correction blocked by D-02.1-06 — fix shipping in v0.1.4 via `?forceSave=true`)

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

- Total plans completed: 16
- Average duration: — min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 0 | 3 | - | - |
| 02.2 | 13 | - | - |

**Recent Trend:**

- Last 5 plans: (none yet)
- Trend: —

*Updated after each plan completion*
| Phase 02.2 P01 | 6 | 1 tasks | 26 files |
| Phase 02.2 P02 | 4 | 2 tasks | 2 files |
| Phase 02.2 P03 | 1 | 1 tasks | 1 files |
| Phase 02.2 P04 | 5 | 2 tasks | 0 files |
| Phase 02.2 P05 | 130 | 2 tasks | 0 files (cross-repo: my-kluster PR #1371 +1/-1) |
| Phase 02.2 P06 | 13min | 3 tasks | 44 files |
| Phase 03 P06 | 20 | 4 tasks | 4 files |

## Accumulated Context

### Roadmap Evolution

- Phase 02.2 inserted after Phase 2.1: v0.1.4 forceSave fix — D-02.1-06 closure (URGENT)

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
- [Phase ?]: Phase 2.1 qBit auth workaround replayed cleanly for Phase 02.2
- [Phase ?]: Option (b) _ArrV3Client mixin chosen over class flag (a) and direct override (c) — explicit type hierarchy surfaces *arr v3 scope at the type level, qBit/Jellyfin inherit from ArrApiClient directly (D-02.2-02 implementation choice)
- [Phase ?]: URL-params assertion idiom (request.url.params[key]) introduced in test_reconcilers_sonarr.py — first in-tree usage; Phase 3 RadarrClient/ProwlarrClient regression contract follows this shape
- [Phase ?]: PUT URL respx regex must permit optional query string (regex \d+(?:\?.*)?\$) — Phase 02.2 GREEN required relaxing 2 existing UPDATE-test regexes; documented as future-proof pattern for any *arr v3 PUT route
- [Phase 02.2 P03]: ADR-8 added to spec.md §11 — "arrconf is a trusted controller — bypasses *arr UI-grade pre-save validation via ?forceSave=true on UPDATE PUTs" (D-02.2-04 closed); Conséquences explicitly scopes qBittorrent (Phase 5) + Jellyfin (Phase 7) OUT of forceSave; bidirectional traceability ADR ↔ `_ArrV3Client.put()` ↔ D-02.1-06 ↔ commit 4a24c5f (Plan 02 GREEN); ADRs 1-7 not renumbered (append-only convention)
- [Phase ?]: Plan 02.2-04: v0.1.4 annotated tag (object 7abc581 → commit 7e5770d) cut + pushed; CI run 25590328939 succeeded in 31s; ghcr.io/tom333/arr-stack-arrconf:0.1.4 (digest sha256:1e7e60c4...d6054a, ~146 MiB, USER 1000:1000) verified anonymously pullable; D-37 atomic-tag pattern observed; Plan 05 my-kluster chart bump unblocked
- [Phase ?]: Plan 02.2-04: GHCR anonymous manifest probe must include OCI index Accept type (application/vnd.oci.image.index.v1+json) — single-platform builds wrap in 1-entry index; legacy Docker manifest.v2-only Accept returns 404. Pattern updated for Phase 3 release verification.
- [Phase 02.2 P05]: my-kluster PR #1371 merged (merge commit bba9010636ec24c97e2419138e5974fe25a357d5, 2026-05-09T05:37:20Z) with atomic 1-line diff (charts/arrconf/values.yaml: tag "0.1.3"→"0.1.4"); ArgoCD selfHeal Synced+Healthy on revision matching merge commit SHA; live CronJob image=ghcr.io/tom333/arr-stack-arrconf:0.1.4 (DISPOSITIVE); CronJob unsuspended; hotfix-window discipline observed (suspend at 03:31:29Z → unsuspend at ~05:38Z, ~2h6m, 0 fires). Phase 2.1 PR4 hotfix decision honored (placeholders STAY — files/arrconf.yml NOT in PR file scope). Plan 06 unblocked.
- [Phase 02.2 P05]: argocd CLI may be unavailable on operator workstation — kubectl-on-Application equivalent path is dispositive (`kubectl get application arrconf -n argocd -o jsonpath='{.status.sync.status} {.status.health.status} rev={.status.sync.revision}'`). Pattern recorded for future hotfix plans.
- [Phase 02.2 P05]: PR merge style (squash vs merge-commit) is operator choice — both honored as non-deviation as long as +1/-1 file scope and PR title-in-commit-message audit anchor preserved.
- [Phase 02.2]: drift-demo runbook FULLY AUTOMATED dispositive captured (RESTORED_PRIORITY=1 == ORIGINAL_PRIORITY=1, no operator nudge); REQ-drift-detection correction half SATISFIED CLEANLY; D-02.1-06 architectural finding LOCKED SHUT — differential proof against Phase 2.1 closure recorded as 'manual_nudge_used: NO' in evidence/drift-demo-2026-05-09.log DISPOSITIVE COMPARISON block
- [Phase 02.2]: rtk token-saving CLI shim filters bare curl/jq/grep output (substitutes TypeScript-style schema or strips hex) — 'rtk proxy <cmd>' bypass is the documented escape hatch — pattern recorded for all future cluster-validation phases that capture raw API responses
- [Phase 02.2 P06 RECOVERY]: ADR-8's accepted bypass risk realized in production — v0.1.4 `?forceSave=true` PUT + Phase 2.1 `merge_fields_for_put` helper combine to silently overwrite `privacy=password` fields with the API mask `"********"`. Detection requires BEHAVIORAL test (Sonarr Test API HTTP 200), NOT snapshot diff (GET-side serialization makes the regression invisible). Pattern recorded for v0.1.5 hotfix planning + Phase 3 prerequisite update — every reconciler that touches credential-bearing fields MUST include a post-PUT behavioral assertion in its W-04 dispositive contract.
- [Phase 02.2 P06 RECOVERY]: `mv` is interactively-aliased on this workstation — rtk-proxied `jq | mv` patterns require explicit `mv -f` (or `\mv`) to bypass the prompt; without `-f` the .tmp output sits next to the original and the redaction silently fails the audit. Pattern recorded for all future per-snapshot redaction code paths.
- [Phase 03 P06]: v0.2.0 annotated tag cut + CI run 25660722478 triggered; ghcr.io/tom333/arr-stack-arrconf:0.2.0 build in progress; Task 6.5 operator checkpoint to verify anonymous pullability pending (D-37 atomic-tag pattern; OCI-index manifest probe per Plan 02.2-04 lesson); Phase 4 (umbrella chart) unblocked pending Task 6.5 approval.

### Pending Todos

None yet — projet vient d'être bootstrappé. Ouvertes mais non décidées : 10 open questions Q1-Q10 (cf PROJECT.md "Open Questions") routées vers les phases concernées :

- Q3 / Q4 / Q6-Q8 → Phase 1 ou 2 (arbitrage technique amont)
- Q2 → Phase 4 (multi-alias `bjw-s/app-template` syntaxe)
- Q1, Q10 → Phase 6 (compat Seerr, routing tags)
- Q9 → Phase 7 (Jellyfin auth header)
- Q5 → tranchée par ADR-5 (ne plus traiter comme open question)

### Blockers/Concerns

- **D-02.2-AUTH-REGRESSION (HIGH, 2026-05-09T06:48:11Z)** — Plan 02.2-06 visual gate failed: Sonarr "Test" on qBit downloadclient returns 401/403; v0.1.4 `?forceSave=true` PUT stored API mask `"********"` as literal password (ADR-8 accepted-risk realized). CronJob `arrconf` SUSPENDED. Phase 02.2 cannot close until v0.1.5 hotfix ships + operator-driven cluster recovery + behavioral W-04 dispositive re-run. See deferred-items.md D-02.2-AUTH-REGRESSION for full required-action checklist.

Risque suivi à anticiper :

- **Q1 bloquante Phase 6** : si Seerr v3.2.0 a divergé de l'API Overseerr/Jellyseerr sur les endpoints critiques, Phase 6 doit être réévaluée (test à faire dès qu'on commence la phase, pas au milieu).

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-12T06:05:18.818Z
Stopped at: Phase 4 context gathered
Resume file: .planning/phases/04-umbrella-chart-migration-des-9-apps/04-CONTEXT.md
Next plan: hotfix gap-closure plan (TBD) — v0.1.5 with credential-aware merge (Option A omit / B mask-detect / C scope-forceSave), operator-driven UI password re-entry, behavioral W-04 dispositive, re-run of Task 6.4. Phase 3 (Radarr/Prowlarr) BLOCKED until v0.1.5 closes the regression cleanly.

### Phase 2.1 plan summary

- Plan 02.1-01 ✅ Pre-fix snapshot baseline (snapshots/before-phase-2.1-2026-05-08/, 26 files, anti-leak audit clean) — commit 45e2f88
- Plan 02.1-02 ✅ Code change (merge_fields_for_put helper + sonarr UPDATE wiring + dump REDACTED filter, 60 tests green, 97.92% coverage)
- Plan 02.1-03 ✅ Release v0.1.3 + my-kluster PR3 + PR4 hotfix + post-PR4 smoke dispositive (merge_field_preserved fires for username + password)
- Plan 02.1-04 ✅ Closure: post-phase2.1 snapshot (tag attached) + drift demo (detection logged, correction via forceSave=true manual nudge) + UAT #3 closed

### Carry-forward to Phase 3

- D-02.1-06 (NEW): merge_fields_for_put preserves Sonarr API-mask `********` for password, blocking PUT pre-save validation when any real field changes. Fix: add `?forceSave=true` to client.put() in UPDATE branch (v0.1.4). See deferred-items.md.
- D-02.1-05 (carry-forward): merge_fields_for_put doesn't backfill cluster-only fields. Mitigated by retaining placeholders in arrconf.yml.
- D-02.1-01..D-02.1-04 (Wave 1 deferred): snapshot.sh redaction gaps + qBit cluster recovery + arrconf-env QBT credentials gap.

### NOTE TO ORCHESTRATOR

This worktree commits the STATE.md update for traceability, but the worktree-merge logic restores main's STATE.md on merge. The orchestrator MUST re-apply this STATE.md content (or selected diffs) to main after merging this worktree. The diff is captured in the Plan 02.1-04 SUMMARY for re-application.
