---
phase: 02-arrconf-cluster-validation
plan: 05
type: summary
wave: 4
status: partial
captured: 2026-05-08
my_kluster_pr2: 1368
arr_stack_commits:
  - 2144e2f  # evidence(02): PR2 apply-mode partial run + post-PR2 snapshot
roadmap_success_criteria:
  "1": satisfied  # snapshot baseline (Plan 02-01)
  "2": satisfied  # CronJob exists, secret bound via envFrom (Plan 02-04)
  "3": satisfied  # zero writes during dry-run (Plan 02-04)
  "4": partial    # arrconf-managed tag CREATED in Sonarr but NOT attached to qBit downloadclient (PUT 400)
  "5": untested   # drift demo blocked by same PUT failure (REQ-drift-detection deferred to Phase 3)
---

# Plan 02-05 Summary — PR2 Apply Mode (Partial) + Drift Demo (Deferred)

## Outcome

PR2 #1368 merged. ArgoCD self-healed `ARRCONF_DRY_RUN=false` into the live CronJob in ~10s (no hard refresh needed this time). First apply-mode smoke job emitted `managed_tag_created` (id=1) and `plan_action action=update`, then **failed at PUT /api/v3/downloadclient/1 with HTTP 400** due to a latent Phase 1 design issue: arrconf YAML overwrites Sonarr's qBittorrent credentials with empty strings, Sonarr's pre-save validation can't connect to qBit, returns 400.

`arrconf-managed` tag was successfully CREATED in Sonarr (orphan but harmless). `downloadclient.json[0].tags` is still `[]` — the tag was never attached. ROADMAP success criterion #4 is **PARTIAL**; #5 (drift detection) is **UNTESTED** because the drift demo runbook would hit the same PUT failure.

Defer fix to Phase 3 (or interrupt Phase 2.1). See §Recommended next step.

## What worked (Task 5.1a + 5.1b apply-mode triggering)

| Property | Value |
|---|---|
| PR number | 1368 |
| Title | feat(arrconf): Phase 2 PR2 — flip arrconfDryRun: false (apply mode) |
| Branch | phase-2-arrconf-pr2 |
| Diff | exactly 1 line: `arrconfDryRun: true → false` in `charts/arrconf/values.yaml` |
| Merged at | 2026-05-08 (PR #1368) |
| ArgoCD self-heal | first poll showed `false` after ~10s; no hard refresh needed (vs Wave 3's PR-fix #1367 that required one) |
| **B-03 dispositive** (single-acceptance flip) | `kubectl get cronjob ... | jq '...ARRCONF_DRY_RUN==\"false\"'` → `true` ✅ |
| Smoke job | arrconf-pr2-smoke-1778227220 |
| W-06 verified events emitted | `managed_tag_created` (id=1) + `plan_action` action=update diff_fields=[fields, tags] |
| W-06 dry-run markers absent | `would_create_managed_tag` =0, `dry_run_skip` =0 ✅ |
| Tag in Sonarr (verified via `curl /api/v3/tag`) | `[{id: 1, label: "arrconf-managed"}]` ✅ |

## What didn't work (PUT downloadclient failure)

Cited from `evidence/pr2-job-logs-2026-05-08.log` (lines 1-2 are the structlog events; the rest is a httpx HTTPStatusError stack trace):

```jsonl
{"id": 1, "event": "managed_tag_created", "level": "info", "timestamp": "2026-05-08T08:00:28.574644Z"}
{"action": "update", "name": "qBittorrent", "diff_fields": ["fields", "tags"], "event": "plan_action", "level": "info", "timestamp": "2026-05-08T08:00:28.593184Z"}
```

```
HTTPStatusError: Client error '400 Bad Request' for url
'http://sonarr.selfhost.svc.cluster.local:8989/api/v3/downloadclient/1'
```

Reproduced manually by PUTing the same body Sonarr received from arrconf — captured Sonarr's exact validation error:

```json
[{
  "isWarning": false,
  "detailedDescription": "Connection refused (qbittorrent.selfhost.svc.cluster.local:8080)",
  "propertyName": "Host",
  "errorMessage": "Impossible de se connecter à qBittorrent",
  "severity": "error"
}]
```

### Root cause

Phase 1 design issue: arrconf has no way to represent secrets in YAML, so `my-kluster/charts/arrconf/files/arrconf.yml` declares the qBit download_client `fields[]` with `username: ''` and `password: ''`. When the differ detects any field difference (here `tags` was being added), the entire `fields[]` array gets PUT to Sonarr. Sonarr persists the new empty username/password, then runs pre-save validation by attempting to authenticate to qBittorrent. qBit rejects the empty credentials, Sonarr returns 400, and the PUT fails atomically (Sonarr does NOT persist the partial change — verified by re-reading `/api/v3/downloadclient/1` post-failure: original credentials still present, `tags: []`).

The current cluster state is **consistent**:
- `arrconf-managed` tag exists (id=1) — orphan but harmless
- qBit download_client unchanged from pre-PR2 — still works for actual downloads
- No data loss, no corruption

### Why Phase 1 unit tests didn't catch this

Phase 1's 52 respx-mocked tests never invoked the **real Sonarr validation pipeline** for downloadclient PUT — respx replays mocked responses without honoring Sonarr's "validate qBit connection on save" semantics. The bug is invisible at unit-test layer; only an integration test against a real Sonarr (Phase 1 HUMAN-UAT #3 — which Phase 2 was meant to close) surfaces it.

This is exactly the value Phase 2 cluster validation was designed to provide.

## Snapshot delta (Task 5.1c partial)

`diff -rq snapshots/post-phase2-pr1-2026-05-08/sonarr/ snapshots/post-phase2-pr2-2026-05-08/sonarr/`:

```
Les fichiers .../sonarr/tag.json sont différents
```

Content diff:
```diff
- []
+ [{"id": 1, "label": "arrconf-managed"}]
```

`downloadclient.json` is identical to post-PR1 (PUT failed atomically). 16 other Sonarr files unchanged.

ROADMAP success criterion #4 jq check:
- `jq -e 'map(.label) | any(. == "arrconf-managed")' tag.json` → exits 0 ✅ (FILE proof)
- `jq -e '.[0].tags | length > 0' downloadclient.json` → exits 1 ❌ (tag NOT attached — PARTIAL)

## Task 5.2 (drift demo) — NOT EXECUTED

The drift demo runbook would induce a `priority` mutation on the qBit download_client and force a reconcile Job. The reconcile would then re-encounter the same PUT failure (the diff would still include the `fields` overwrite). Running it in this state would only generate another evidence log of the same failure. Skipped to avoid noise.

REQ-drift-detection is **DEFERRED to Phase 3** (or the Phase 2.1 interrupt that fixes the field-overwrite issue). After the fix lands, the drift demo runbook in this plan (Task 5.2 steps 1-10) can be re-executed in a future Plan 02-05.5 or Phase 3.X.

## Phase 1 HUMAN-UAT #3 status

NOT closed. Item #3 (live round-trip against a real Sonarr instance) is **partial**:
- `apply` triggered against real Sonarr — yes (tag created, PUT attempted)
- Round-trip 0-diff — no (PUT failed; the YAML cannot apply cleanly to a Sonarr instance with real qBit credentials)

Updating 01-HUMAN-UAT.md to reflect the partial status with deferral note.

## Cluster artifacts (post-Phase 2)

| Resource | State |
|---|---|
| Application/arrconf in argocd | Synced + Healthy |
| CronJob/arrconf in selfhost | active, ARRCONF_DRY_RUN=false, schedule `0 */4 * * *` |
| ConfigMap/arrconf in selfhost | active |
| Secret/arrconf-env in selfhost | active, no ArgoCD tracking-id (W-05) |
| Tag in Sonarr (id=1) | label="arrconf-managed" — orphan, no resources tagged with it |
| qBit download_client | unchanged — still in `tags: []` (Sonarr atomically rejected the failed PUT) |

**Recurring failure**: every 4h the cron fires, attempts the same PUT, fails with the same 400. Does NOT corrupt anything (Sonarr atomic), but pollutes logs and triggers Job failures (`failedJobsHistoryLimit: 2` is in effect — no unbounded growth).

**Mitigation until Phase 3 fix**: temporarily flip `arrconfDryRun: false → true` (revert PR2 effectively) OR suspend the CronJob:

```bash
# Option A: suspend cronjob (no PR needed, ArgoCD selfHeal will revert in ~3 min though)
kubectl patch cronjob arrconf -n selfhost -p '{"spec":{"suspend":true}}'

# Option B: re-flip arrconfDryRun via small PR — cleanest
```

## Deviations from plan

1. **Task 5.1c PARTIAL** — `tag.json` contains `arrconf-managed` (FILE proof passes), but `downloadclient.json[0].tags | length > 0` jq check FAILS. Snapshot committed anyway as the audit record of the partial state.

2. **Task 5.2 SKIPPED** — drift demo would re-trigger the same PUT failure. Not executed; runbook remains in 02-05-PLAN.md for re-execution post-fix. `snapshots/drift-test-2026-05-08/` (W-01 REQUIRED) NOT created. `evidence/drift-demo-2026-05-08.log` (W-04 dispositive comparison) NOT created.

3. **Phase 1 HUMAN-UAT #3 NOT closed** — partial completion only; will be revisited after Phase 3 / 2.1 fix.

4. **arrconf in cluster will fail every 4h** until Phase 3 fix lands. Recommend operator either suspend the CronJob OR re-flip arrconfDryRun=true via small PR3 in my-kluster.

## Recommended next step

**Open Phase 2.1 (interrupt) or Phase 3 prereq** with a single objective:

> Modify `tools/arrconf/arrconf/reconcilers/sonarr.py` (and possibly `differ.py`) so that the PUT body for `downloadclient` preserves cluster-stored field values for any field whose YAML value is empty string `""` OR matches a well-known-sensitive field name (`username`, `password`, `apiKey`, `token`, etc.). Test plan: replay Plan 02-05 Tasks 5.1b/c/2 — should land cleanly with tag attached and drift demo green.

Acceptance criteria for the fix:
- `tag.json` shows `arrconf-managed` (already done)
- `downloadclient.json[0].tags | length > 0` after PR2 apply
- Drift demo runbook completes with W-04 dispositive `RESTORED_PRIORITY == ORIGINAL_PRIORITY`
- W-01 forensic snapshot pair (`drift-test-<date>/`) committed
- Phase 1 HUMAN-UAT #3 closed

## Cross-repo file inventory (Phase 2 totals)

### my-kluster (committed)
- PR1 #1366: 8 files — chart + ArgoCD App
- PR-fix #1367: 1 file — cronjob.yaml args reorder
- PR2 #1368: 1 file — values.yaml dryRun flip

### my-kluster (on disk only — gitignored)
- secrets/arrconf-secret.yaml (158 bytes, kubectl apply target)

### arr-stack (committed)
- snapshots/before-phase-2-2026-05-08/ (86 files)
- snapshots/post-phase2-pr1-2026-05-08/ (75 files)
- snapshots/post-phase2-pr2-2026-05-08/ (17 files — sonarr only)
- snapshots/drift-test-2026-05-08/ — NOT CREATED (Task 5.2 skipped)
- .planning/phases/02-arrconf-cluster-validation/.cluster-services
- .planning/phases/02-arrconf-cluster-validation/evidence/pr1-job-logs-2026-05-08.log
- .planning/phases/02-arrconf-cluster-validation/evidence/pr2-job-logs-2026-05-08.log
- .planning/phases/02-arrconf-cluster-validation/evidence/drift-demo-2026-05-08.log — NOT CREATED
- .planning/phases/02-arrconf-cluster-validation/02-{01,02,03,04,05}-SUMMARY.md
- .planning/phases/01-arrconf-poc-json-schema/01-HUMAN-UAT.md (item #1 closed by 02-02)

### Image releases on GHCR
- ghcr.io/tom333/arr-stack-arrconf:0.1.0 — bootstrap (no image, first-push race)
- ghcr.io/tom333/arr-stack-arrconf:0.1.1 — bootstrap (no image, latent uv:0.11 Dockerfile bug)
- ghcr.io/tom333/arr-stack-arrconf:0.1.2 — LIVE (running in cluster, contains the field-overwrite design issue)
