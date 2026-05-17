---
phase: 02-arrconf-cluster-validation
plan: 04
type: summary
wave: 3
status: complete
captured: 2026-05-08
my_kluster_pr1: 1366
my_kluster_pr_fix: 1367
arr_stack_commits:
  - 4e18965  # evidence(02): capture PR1 dry-run smoke job logs
  - b9f72f0  # snapshot(02): post-phase2-pr1 dry-run capture
---

# Plan 02-04 Summary — PR1 Dry-Run Deployment

## Outcome

PR1 (#1366) deployed in `tom333/my-kluster`. Bootstrap secret applied manually before sync (W-05 — no ArgoCD tracking-id). After PR-fix #1367 (cronjob args reorder), forced smoke job completed in 12s with all 3 W-06 dispositive event names present and apply-mode marker absent. Post-PR1 snapshot of Sonarr shows the critical files (`downloadclient.json`, `tag.json`) IDENTICAL to baseline — only time-varying noise differs (free space, uptime).

ROADMAP success criteria #2 (CronJob exists) — **SATISFIED**.
ROADMAP success criterion #3 (zero writes during dry-run) — **SATISFIED functionally** (strict `wc -l == 0` failed on 2 noise files; see Deviations §3).

## PR1 details

| Property | Value |
|---|---|
| PR number | 1366 |
| Title | feat(arrconf): Phase 2 PR1 — mini-chart with arrconfDryRun=true |
| Branch | phase-2-arrconf-pr1 |
| Merged at | 2026-05-08T06:56:19Z |
| Files | 8 staged (NOT 9 — `secrets/arrconf-secret.yaml` gitignored per 02-03 SUMMARY §Deviation 1) |
| ArgoCD sync after merge | first poll showed Synced + Healthy (~10 min after merge with manual hard-refresh) |

## Smoke job

| Property | Value |
|---|---|
| Job name | arrconf-pr1-smoke-1778224797 |
| Trigger | `kubectl create job --from=cronjob/arrconf` |
| Duration | 12s |
| Complete condition | True |
| Exit | 0 |
| Logs persisted | `.planning/phases/02-arrconf-cluster-validation/evidence/pr1-job-logs-2026-05-08.log` (4 lines, valid JSON Lines) |

## W-06 verified events (cited from evidence log)

```jsonl
{"event": "would_create_managed_tag", "level": "info", "timestamp": "2026-05-08T07:20:05.845607Z"}
{"action": "update", "name": "qBittorrent", "diff_fields": ["fields", "tags"], "event": "plan_action", "level": "info", "timestamp": "2026-05-08T07:20:05.861321Z"}
{"action": "update", "name": "qBittorrent", "event": "dry_run_skip", "level": "info", "timestamp": "2026-05-08T07:20:05.861386Z"}
{"app": "sonarr", "actions": [], "event": "apply_complete", "level": "info", "timestamp": "2026-05-08T07:20:05.861426Z"}
```

| W-06 dispositive check | Expected | Observed | Result |
|---|---|---|---|
| `managed_tag_found` OR `would_create_managed_tag` ≥ 1 | yes | 1 (`would_create_managed_tag`) | ✅ |
| `plan_action` ≥ 1 | yes | 1 (action=update, diff_fields=[fields, tags]) | ✅ |
| `managed_tag_created` == 0 (apply-mode marker MUST be absent) | yes | 0 | ✅ |
| `dry_run_skip` (additional dry-run signal) | yes | 1 | ✅ bonus |

## Cluster verifications

| Check | Expected | Observed | Result |
|---|---|---|---|
| Secret `arrconf-env` in selfhost | DATA=1, age recent | DATA=1, AGE=23m at check, key length=32 bytes | ✅ |
| **W-05** Secret has NO ArgoCD tracking-id | empty | empty | ✅ |
| ArgoCD App `arrconf` synced | Synced+Healthy | Synced+Healthy (first poll) | ✅ |
| CronJob `arrconf` in selfhost | exists, schedule `0 */4 * * *` | exists, AGE=10m | ✅ |
| ConfigMap `arrconf` in selfhost | exists | exists, AGE=10m | ✅ |
| envFrom secretRef name | `arrconf-env` | `arrconf-env` | ✅ |
| `ARRCONF_DRY_RUN` env value | `true` | `true` | ✅ |
| **B-02** volumeMounts | length==1, name=config | `[{config, /app/config/arrconf.yml, subPath: arrconf.yml}]` | ✅ |
| arr-stack secret-leak audit (W-02 POSIX) | 0 matches | 0 | ✅ |

## Snapshot diff (success criterion #3)

```
diff -rq snapshots/before-phase-2-2026-05-08/sonarr/ snapshots/post-phase2-pr1-2026-05-08/sonarr/
> rootfolder.json (différent)
> system_status.json (différent)
```

Strict count: 2 (vs spec ==0). **But content-level inspection shows both are time-varying Sonarr-internal noise**, not arrconf writes:

- `rootfolder.json`: ONLY `freeSpace` field changed (421523095552 → 457214001152 — ~33 GB disk usage drift over the snapshot interval).
- `system_status.json`: ONLY `startTime` changed (`2026-05-07T03:05:49Z` → `2026-05-08T03:00:08Z` — Sonarr was restarted overnight, possibly a routine pod restart).

The CRITICAL files (those arrconf would touch) are IDENTICAL:

- `downloadclient.json` — IDENTICAL ✅
- `tag.json` — IDENTICAL `[]` (no `arrconf-managed` tag created — dispositive proof of dry-run) ✅

This matches the same noise pattern documented in Plan 02-01 SUMMARY (8 noise diffs vs Phase 0 baseline including `system_status.json`, `rootfolder.json`).

## Deviations from plan

1. **Stage count 8 instead of 9** — `my-kluster/.gitignore` excludes `secrets/`, so `secrets/arrconf-secret.yaml` cannot be git-staged. Already documented in Plan 02-03 SUMMARY §Deviation 1; Plan 02-04 Task 4.1 step 2 line 187's assertion `STAGED_COUNT -eq 9` was overridden to `-eq 8`. The bootstrap secret stays on disk + `kubectl apply -f` (operational pattern from 02-VALIDATION.md "Manual-Only Verifications" row 2).

2. **PR-fix #1367 needed before smoke job could run** — first smoke attempt CrashLooped:
   ```
   Usage: arrconf apply [OPTIONS]
   Error: No such option: --config
   ```
   Root cause: `--config` is a top-level `arrconf` option (default `/etc/arrconf/arrconf.yml`), not an `apply` subcommand option. Plan 02-03 specified `args: ["apply", "--config", ..., "--apps", "sonarr"]` (broken) — the correct order is `args: ["--config", ..., "apply", "--apps", "sonarr"]`. Caught at first smoke job. PR-fix #1367 merged; ArgoCD required a hard refresh annotation (`argocd.argoproj.io/refresh=hard`) to pick up the new args (auto-sync didn't propagate within the polling window — possibly because annotated objects skip the deep-equal short-circuit on initial polls). After hard refresh, args correct, smoke job completed in 12s.

3. **Strict diff -rq count is 2, not 0** — see Snapshot diff section. Functional zero-writes proven by `downloadclient.json` + `tag.json` identical content. The 2 noise files are time-varying (Sonarr-internal `freeSpace` + `startTime`), not arrconf writes. Same pattern as Plan 02-01 SUMMARY noise diffs vs Phase 0 baseline. Recommend Plan 02-05 / future runs use a content-aware diff (e.g., `jq -S 'del(.. | objects | .freeSpace?, .startTime?, .uptime?, .buildTime?, .runtimeSeconds?)'`-piped) instead of the byte-level `diff -rq`.

4. **Anti-leak redaction needed on post-PR1 snapshot** — `tools/snapshot/snapshot.sh` produces raw API output; same Phase 0 jq pattern applied (18 redactions). Plan 02-04 Task 4.3 didn't explicitly call out the redaction step but it's part of the snapshot workflow per `tools/snapshot/README.md` "Audit anti-leak". Recommend hoisting redaction into `snapshot.sh` itself (or a follow-up Phase) so it's not a manual step at every snapshot point.

## What this unblocks

- Plan 02-05 (Wave 4) can flip `arrconfDryRun: true → false` in PR2.
  Expected delta after PR2 + 1 cron cycle:
  - `sonarr/tag.json` gains an `arrconf-managed` entry (success criterion #4)
  - `sonarr/downloadclient.json` may gain the `arrconf-managed` tag id on the qBittorrent download_client entry (the smoke log already showed `diff_fields: ["fields", "tags"]` would have been the apply target)
- Drift demo runbook (Plan 02-05 Task 5.2) can be exercised once apply mode is verified.

## Reminder for Phase 2 close

After Wave 4 (Plan 02-05) completes, run twice in `my-kluster`:

```bash
git stash pop   # first pop -> stash@{0}
git stash pop   # second pop
```
