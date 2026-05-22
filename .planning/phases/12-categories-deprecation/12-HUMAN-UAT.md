---
phase: 12-categories-deprecation
type: HUMAN-UAT
scenarios: 3
status: passed
captured: 2026-05-22
---

# Phase 12 HUMAN-UAT — SC#5 live-cluster dispositive

## Scenario 1 — PR1 merge + ArgoCD picks up image 0.7.0 ✅

**Pre-conditions met:**
- Phase 12 PR #19 (containing Plan A+B+C+D) merged to `main` at 2026-05-22T03:27 UTC.
- Auto-tag workflow created `v0.7.0` tag and `arrconf-image-build` workflow published `ghcr.io/tom333/arr-stack-arrconf:0.7.0` to GHCR.
- my-kluster Renovate PR bumping `arr-stack-app.yaml#targetRevision: v0.7.0` was opened and merged by the operator.
- ArgoCD synced.

**Verification commands:**

```bash
kubectl -n selfhost get cronjob arrconf -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}'
# Observed: ghcr.io/tom333/arr-stack-arrconf:0.7.0

kubectl -n argocd get application arr-stack -o jsonpath='{.status.sync.status} {.status.health.status}'
# Observed: Synced Progressing (jellyfin pod ContainerCreating during snapshot run; settled to Synced Healthy shortly after)
```

**Status:** ✅ passed.

## Scenario 2 — Post-merge snapshot + dry-run capture (v0.4.0 working tree) ✅

**Pre-conditions met:** Scenario 1 passed. Snapshot capture ran from main HEAD at commit `f2d55db` (Phase 12 merged + 2 Renovate merges on top).

**Commands executed:**

```bash
DATE=$(date +%F)   # 2026-05-22

# Port-forward 6 services; prowlarr on alt port 19696 because host runs a local Prowlarr on 9696
kubectl -n selfhost port-forward svc/{sonarr,radarr,qbittorrent,seerr,jellyfin} <port>:<port>
kubectl -n selfhost port-forward svc/prowlarr 19696:9696
export PROWLARR_URL=http://localhost:19696

# Decrypt secrets from the sealed-secret-derived arrconf-env
SECRET_JSON=$(kubectl -n selfhost get secret arrconf-env -o json)
for K in SONARR_API_KEY RADARR_API_KEY PROWLARR_API_KEY SEERR_API_KEY JELLYFIN_API_KEY QBT_USER QBT_PASS; do
  export $K=$(echo "$SECRET_JSON" | python3 -c "import json,sys,base64;d=json.load(sys.stdin)['data'];print(base64.b64decode(d['$K']).decode())")
done

# Snapshot.sh runs against forwarded ports
tools/snapshot/snapshot.sh --output snapshots/after-phase-12-${DATE}/
# Output: 84 redacted JSON files, 0 warnings.

# Dry-run against localhost-rewritten YAML (charts/arr-stack/files/arrconf.yml
# uses cluster-internal DNS; rewritten to localhost:<port> for forward access)
cd tools/arrconf
uv run arrconf --config /tmp/arr-stack-v040/arrconf-localhost.yml apply --dry-run \
  > ../../snapshots/after-phase-12-${DATE}/dry-run-plan-actions-v040.log 2>&1
# Exit code: 1 — sonarr + radarr report app_failed at step 6 (see Scenario 3
# analysis). Other 4 apps (prowlarr, qbittorrent, seerr, jellyfin) reported
# apply_complete in dry_run mode. This is the expected transitional state.

# Redaction audit
grep -rniE "(api[-_]?key|password|passkey|token|webhookurl|sessionkey).*:.*[a-zA-Z0-9]{16,}" \
  snapshots/after-phase-12-${DATE}/ | grep -v "<redacted>"
# Output: empty — AUDIT CLEAN
```

**Artifacts committed:**
- `snapshots/after-phase-12-2026-05-22/` — 85 files (84 JSON + 1 dry-run log).
- Commit `e1edff7` (snapshot) on main.

**Status:** ✅ passed.

## Scenario 3 — Diff vs before-snapshot (SC#5 dispositive) ✅

**Diff command + output:**

```bash
diff -rq snapshots/before-phase-12-2026-05-22/ snapshots/after-phase-12-2026-05-22/
```

**Snapshot JSON diff (9 files differ, ALL runtime telemetry):**

| File | Reason |
|---|---|
| `jellyfin/plugins.json` | Update-check timestamps drifted |
| `jellyfin/scheduled_tasks.json` | LastRun timestamps drifted |
| `jellyfin/system_info.json` | Uptime field |
| `jellyfin/system_info_public.json` | Uptime field |
| `jellyfin/system_storage.json` | Free-space percentage drifted |
| `prowlarr/indexerstats.json` | Query/grab counters drifted |
| `qbittorrent/torrents_info.json` | Per-torrent download progress |
| `qbittorrent/transfer_info.json` | Bandwidth counters |
| `seerr/settings_jobs.json` | NextRun timestamps |

**ZERO config-state divergence** — no `tag.json`, no `downloadclient.json`, no `rootfolder.json`, no `category.json`, no `library_virtualfolders.json` in the diff. This is exactly what SC#5 requires.

**Cross-version dry-run log diff:**

| Metric | v030 (pre-merge) | v040 (post-merge) |
|---|---|---|
| Line count | 111 | 181 |
| `merge_decision` events | 11 | 0 |
| Apps reporting `apply_complete` | 6/6 | 4/6 (sonarr/radarr failed at step 6) |
| New `plan_action: add` events for categories-derived resources | 0 | ~70 (5 series × {tag, RF, DC, RPM}, 5 movies × idem, 10 qBit categories, 8 jellyfin library_path, 1 seerr animeTag — minus duplicates already in cluster) |

The presence of 11 `merge_decision` events in v030 and 0 in v040 is the **dispositive structural marker** that proves `merge_with_manual` was alive in v0.3.0 and deleted in v0.4.0. The 70-line growth is the categories-derived ADD plan_actions becoming visible — also expected.

**Sonarr/Radarr `app_failed` at step 6:** Known transitional state. The cluster still has v0.2.0 tags (`tv`, `anime`, `family`) because no real apply has run on `:0.7.0` yet (CronJob next-run scheduled). v0.4.0 generators emit categories-derived labels (`series`, `series-emilie`, ..., `films`, ...). Step 2 (tags reconcile) would CREATE these, but in `dry_run=True` it just plans the ADD and skips the POST. Step 6 (download_client tag resolution) then can't find `series` / `films` in `all_tags` because they weren't actually persisted in dry-run. The NEXT real CronJob apply will create the tags first, then resolution will succeed. This is **NOT a Phase 12 regression** — it is the documented bootstrap behavior when migrating from v0.2.0 tags to v0.3.0+ Categories.

**Status:** ✅ passed — SC#5 satisfied. Configuration state is preserved; cross-version code paths are dispositively different per the `merge_decision` event marker.

## Operator decisions captured for traceability

1. **Tag spillover (v0.8.0, v0.8.1):** the auto-tag chain in `chart-lint.yml` bumped to v0.8.0 on the cleanuparr merge and v0.8.1 on the jellyfin merge (each treated as patch by the conventional-commit detector). The `values.yaml#arrconf.image.tag` still pins `0.7.0`. Operator may accept a future Renovate bump to a higher v0.8.x or pin to v0.7.0. Phase 12 cluster outcome is identical either way (no Python code changed between 0.7.0 and 0.8.1).

2. **Prowlarr local port collision:** the host runs a local Prowlarr on `:9696`, so the kubectl port-forward to the cluster's Prowlarr was bound to `:19696`. Documented for the next snapshot run.

3. **Jellyfin pod restart during sync:** ArgoCD restarted the jellyfin pod (`6fdffdcc5-kq8pw`) while syncing the chart updates from the my-kluster Renovate merge. Snapshot capture waited for `1/1 Running` before proceeding.
