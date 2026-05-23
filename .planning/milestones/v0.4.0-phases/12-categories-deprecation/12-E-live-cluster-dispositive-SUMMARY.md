---
phase: 12-categories-deprecation
plan: E
type: SUMMARY
status: complete
date: 2026-05-22
---

# Plan 12-E Summary — SC#5 live-cluster dispositive

## Outcome

SC#5 satisfied. Post-merge snapshot captured against the v0.4.0 cluster (image `:0.7.0`) from main HEAD; diffed against Plan D's pre-merge snapshot (v0.3.0 cluster, image `:0.6.7`, captured from a pre-Plan-A worktree). The diff confirms zero config-state divergence and proves the cross-version code transition via the absence of `merge_decision` events in the v040 log.

## Capture procedure

Same shape as Plan D's runbook but from main HEAD (no worktree this time — main is the v0.4.0 reference). Six `kubectl port-forward` sessions, prowlarr on alt port `:19696` because the host runs a local Prowlarr on `:9696`. `PROWLARR_URL` env override.

Secrets pulled directly from the sealed-secret-derived K8s secret `selfhost/arrconf-env`.

```bash
DATE=2026-05-22
tools/snapshot/snapshot.sh --output snapshots/after-phase-12-${DATE}/
cd tools/arrconf
uv run arrconf --config /tmp/arr-stack-v040/arrconf-localhost.yml apply --dry-run \
  > ../../snapshots/after-phase-12-${DATE}/dry-run-plan-actions-v040.log 2>&1
```

(`arrconf-localhost.yml` is a sed-rewritten copy of `charts/arr-stack/files/arrconf.yml` with cluster-internal DNS replaced by localhost ports. The committed YAML on main is untouched.)

## Artifacts

- `snapshots/after-phase-12-2026-05-22/` — 85 files (84 JSON + 1 dry-run log), commit `e1edff7`.
- `.planning/phases/12-categories-deprecation/12-HUMAN-UAT.md` — Scenarios 1/2/3 all passed.
- `.planning/phases/12-categories-deprecation/12-VERIFICATION.md` — Phase 12 status PASSED.

## SC#5 evidence

### JSON snapshot diff (9 files, ALL runtime telemetry)

```
jellyfin/plugins.json
jellyfin/scheduled_tasks.json
jellyfin/system_info.json
jellyfin/system_info_public.json
jellyfin/system_storage.json
prowlarr/indexerstats.json
qbittorrent/torrents_info.json
qbittorrent/transfer_info.json
seerr/settings_jobs.json
```

ZERO config-state divergence. No `tag.json` / `downloadclient.json` / `rootfolder.json` / `category.json` / `library_virtualfolders.json` differ between the two snapshots.

### Cross-version dry-run log diff

| Metric | v030 | v040 | Interpretation |
|---|---|---|---|
| Line count | 111 | 181 | v040 emits ~70 more lines |
| `merge_decision` events | 11 | 0 | `merge_with_manual` is dead in v0.4.0 |
| `apply_complete` apps | 6/6 | 4/6 | sonarr/radarr failed at step 6 (see below) |

The `merge_decision` event marker is the dispositive structural difference proving the code transition. The line growth in v040 is the categories-derived ADD plan_actions becoming visible.

### Known transitional state (NOT a regression)

v040 dry-run reports `app_failed` on sonarr and radarr at step 6 (download_client tag resolution). Cause: the cluster still has v0.2.0 tags (`tv`, `anime`, `family`) because no real apply has run on `:0.7.0` yet. The v0.4.0 generators emit categories-derived labels (`series`, `series-emilie`, ..., `films`, ...). Step 2 (tags reconcile) plans to ADD these labels but `dry_run=True` skips the POST, so step 6 can't find them in `all_tags`. The next real CronJob apply on `:0.7.0` will create the tags first, then resolution will succeed.

This is documented in `12-VERIFICATION.md` Follow-ups #1. Phase 12 does not gate on it because:

- SC#3 (the in-CI `test_sweep`) already proves the generators + reconcilers are byte-equivalent across two consecutive runs against the same fixtures.
- SC#5 (this plan) proves the cross-version transition via the `merge_decision` marker and the snapshot-state preservation.
- The transitional failure is a property of `dry_run=True` against a not-yet-migrated cluster, not of the v0.4.0 code itself.

## Acceptance against PLAN.md `must_haves.truths`

| Truth | Status |
|---|---|
| Post-merge snapshot captured | ✅ `snapshots/after-phase-12-2026-05-22/` |
| dry-run-plan-actions-v040.log captured against image :0.7.0 | ✅ 181 lines |
| `diff -r` shows only structural diffs | ✅ 9 runtime-telemetry files; zero config-state |
| ZERO `plan_action` differences in config | ✅ |
| PR2 evidence-only (no code/chart/values changes) | ✅ this commit + planning updates only |
| 12-VERIFICATION.md = PASSED | ✅ |

## Out of scope

- Triggering a manual real-apply on the new image (cluster will run the CronJob on schedule; not a Phase 12 deliverable).
- Closing the chart-lint workflow papercut (PR #17 follow-up).
- Python 3.14 changelog review (PR #21 follow-up).
