# Intro Skipper Operator Runbook

**Plugin:** Intro Skipper  
**GUID:** `c83d86bb-a1e0-4c35-a113-e2101cf4ee6b`  
**Version:** `1.10.11.19`  
**Manifest URL:** `https://intro-skipper.org/manifest.json`  
**Jellyfin target:** `10.11.8` (production cluster)  
**arrconf image:** `0.17.0` (ships this feature)  
**Phase:** 24 — Jellyfin Intro Skipper  
**Requirements:** JFSKIP-01..05

---

## Overview

This runbook covers the full operator procedure for activating the Intro Skipper plugin on the production Jellyfin instance. The install requires **two arrconf reconcile runs** with a **single manual Jellyfin restart** between them (D-02 two-run model). arrconf NEVER automates the restart — this is an explicit operator action.

Timeline summary:

```
Run N           : arrconf queues the plugin install (plugin_install_queued)
  ↓
Operator step   : kubectl rollout restart deployment/jellyfin -n selfhost
  ↓
Run N+1         : arrconf enables the plugin + applies config
  ↓
~hours later    : Intro Skipper fingerprint analysis completes
  ↓
Verification    : Skip button appears in Jellyfin web/app during playback
```

---

## Step 0 — Pre-phase ADR-6 Snapshot (MANDATORY before any live write)

Before any arrconf apply that touches the production cluster, capture a forensic baseline per ADR-6 (CLAUDE.md "Workflow snapshot").

```bash
# From the arr-stack repo root
tools/snapshot/snapshot.sh --apps jellyfin --output snapshots/before-phase-24-$(date +%F)/

# Commit immediately (snapshot is the rollback reference)
git add snapshots/before-phase-24-*/
git commit -m "snapshot(pre-phase-24): jellyfin baseline before intro-skipper install"
```

The snapshot captures: `/Plugins`, `/System/Configuration` (PluginRepositories), `/Library/VirtualFolders`, `/ScheduledTasks`. Keep this committed — it is your rollback reference if the plugin crashes Jellyfin.

---

## Step 1 — Deploy v0.17.0 via ArgoCD

Push (or wait for Renovate) to bump `targetRevision` in `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` to the tag that contains `arrconf.image.tag: 0.17.0` (the auto-generated tag from this phase's push to main).

ArgoCD sync completes when the arrconf CronJob pod and the arrconf ConfigMap are both updated. No Jellyfin restart is needed at this step.

---

## Step 2 — Run N: Plugin Install Queued (SC#1)

Trigger arrconf or wait for the next CronJob tick. On Run N, arrconf detects that "Intro Skipper" is absent from `GET /Plugins` and fires the install:

```
POST /Packages/Installed/Intro%20Skipper
  ?assemblyGuid=c83d86bb-a1e0-4c35-a113-e2101cf4ee6b
  &version=1.10.11.19
  &repositoryUrl=https://intro-skipper.org/manifest.json
```

arrconf logs a WARNING with the hint and adds the action `plugin_install_queued:Intro Skipper`.

**Manual trigger (skip the next CronJob tick):**

```bash
# Find the most recent arrconf pod or exec via kubectl
kubectl -n selfhost create job --from=cronjob/arrconf arrconf-manual-$(date +%s)
```

**Confirm SC#1 — install queued:**

```bash
kubectl -n selfhost logs job/<arrconf-job-name> | grep plugin_install_queued
# Expected output (JSON structlog):
# {"event": "plugin_install_queued", "plugin": "Intro Skipper", ...
#  "hint": "kubectl rollout restart deployment/jellyfin -n selfhost", ...}
```

If `plugin_install_queued` does not appear in logs, check:
- `arrconf.yml` has the correct `plugins.required` block with `install_guid: c83d86bb-a1e0-4c35-a113-e2101cf4ee6b`
- The plugin repository URL (`https://intro-skipper.org/manifest.json`) is already registered in `GET /System/Configuration` — Run N also ensures this via `_reconcile_server_config()`.

**Confirm no duplicate repository entries (idempotence pre-check):**

```bash
curl -s -H "Authorization: MediaBrowser Token=<JELLYFIN_API_KEY>" \
  http://jellyfin.selfhost.svc.cluster.local:8096/System/Configuration \
  | jq '[.PluginRepositories[] | select(.Url | contains("intro-skipper"))]'
# Expected: exactly ONE entry with Url "https://intro-skipper.org/manifest.json"
```

---

## Step 3 — PVC Persistence Check (ONCE, before restart)

Verify the Jellyfin `/config` directory is on a persistent PVC, not an ephemeral volume. If it is ephemeral, the plugin DLL is written into the pod and lost on every restart — making install perpetually stuck in `plugin_install_queued` (Pitfall B5).

```bash
# Check PVC mounts for the Jellyfin pod
kubectl -n selfhost get pod -l app.kubernetes.io/name=jellyfin \
  -o jsonpath='{.items[0].spec.volumes[*]}' | jq .

# Confirm /config is backed by a PVC (not emptyDir)
kubectl -n selfhost describe pod -l app.kubernetes.io/name=jellyfin | grep -A2 "Mounts:"
# Look for: /config → <pvc-name>
```

If `/config` is on a PVC: proceed to Step 4.  
If `/config` is on `emptyDir` or `hostPath` without persistence: STOP — the plugin state will be lost on restart. Fix the volume mount in `charts/arr-stack/values.yaml` before proceeding.

---

## Step 4 — Manual Restart (the single operator step)

This is the ONLY manual cluster action in the two-run model. arrconf NEVER automates this.

```bash
kubectl rollout restart deployment/jellyfin -n selfhost
kubectl rollout status deployment/jellyfin -n selfhost
# Wait until: "deployment 'jellyfin' successfully rolled out"
```

After restart, Jellyfin loads the plugin DLL from `/config/plugins/`. The plugin is now present but not yet enabled — that happens in Run N+1.

**Post-restart health check:**

```bash
# Jellyfin pod is Running + Ready
kubectl -n selfhost get pod -l app.kubernetes.io/name=jellyfin

# No CrashLoopBackOff (would indicate plugin incompatibility — see recovery section)
kubectl -n selfhost logs deployment/jellyfin --tail=50 | grep -i "error\|exception\|plugin"
```

---

## Step 5 — Run N+1: Plugin Enable + Config (SC#2)

Trigger arrconf again (next CronJob tick or manual job). On Run N+1:

1. `GET /Plugins` returns "Intro Skipper" with Status `NotInstalled` or `Disabled` (present in the list post-restart).
2. arrconf calls `POST /Plugins/c83d86bb-a1e0-4c35-a113-e2101cf4ee6b/1.10.11.19/Enable`.
3. arrconf calls `GET /Plugins/c83d86bb-a1e0-4c35-a113-e2101cf4ee6b/Configuration`, diffs against desired, and `POST`s the config block:
   - `MaxParallelism: 1` (fingerprint concurrency cap — D-05)
   - `AutoSkip: false` (show skip button, no forced skip — PROJECT.md Out of Scope)
   - `AutoSkipCredits: false` (same)
   - Intro + credits detection ON

**Confirm SC#2 — plugin active, no duplicate repository:**

```bash
# Plugin active
curl -s -H "Authorization: MediaBrowser Token=<JELLYFIN_API_KEY>" \
  http://jellyfin.selfhost.svc.cluster.local:8096/Plugins \
  | jq '.[] | select(.Name == "Intro Skipper") | {Name, Status, Version}'
# Expected: {"Name": "Intro Skipper", "Status": "Active", "Version": "1.10.11.19"}

# No duplicate repository entries
curl -s -H "Authorization: MediaBrowser Token=<JELLYFIN_API_KEY>" \
  http://jellyfin.selfhost.svc.cluster.local:8096/System/Configuration \
  | jq '[.PluginRepositories[] | select(.Url | contains("intro-skipper"))] | length'
# Expected: 1
```

If the plugin Status is `NotInstalled` (instead of `Active`) after Run N+1, the restart did not load the plugin. Re-check Step 3 (PVC persistence) and repeat Steps 4-5.

---

## Step 6 — Off-Peak Fingerprint Scheduling (W-01 — one-time operator action)

arrconf caps the fingerprint concurrency to `MaxParallelism: 1` via the plugin config (D-05). This governs *how many episodes are fingerprinted concurrently*. The **trigger time** of the analysis task is a separate Jellyfin built-in scheduled task setting that arrconf does NOT manage.

The first full library scan is a multi-hour CPU-intensive operation (Pitfall B4). To avoid daytime CPU contention on the single-node MicroK8s cluster:

**Set the analysis schedule in Jellyfin Dashboard:**

1. Navigate to: `Jellyfin web UI > Dashboard > Scheduled Tasks`
2. Locate the task named **"Analyze Episodes"** (or "Fingerprint Analysis" — may vary by plugin version).
3. Click the trigger edit (pencil icon).
4. Set the trigger to a **daily overnight window**, e.g. `02:00 local time`, duration 8 hours.
5. Save.

This is a one-time action. Subsequent runs are incremental (only new episodes) and are fast.

Note: you can also trigger the scan manually via **Dashboard > Scheduled Tasks > Run** if you want to start it immediately (e.g., on a weekend). The `MaxParallelism: 1` set by arrconf ensures it will not saturate the node.

---

## Step 7 — Chapter Extraction Verification (SC#4)

arrconf (via `generate_jellyfin()`) sets `EnableChapterImageExtraction: true` on all 10 Category libraries. Verify:

```bash
curl -s -H "Authorization: MediaBrowser Token=<JELLYFIN_API_KEY>" \
  http://jellyfin.selfhost.svc.cluster.local:8096/Library/VirtualFolders \
  | jq '[.[] | {Name, EnableChapterImageExtraction: .LibraryOptions.EnableChapterImageExtraction}]'
# Expected: all 10 libraries have EnableChapterImageExtraction: true
```

The 10 libraries are: `series`, `series-emilie`, `series-thomas`, `series-garcons`, `series-zoe`, `films`, `nouveaux-films`, `films-zoe`, `films-animation-enfants`, `films-enfants`.

If any library shows `false` or `null`: re-run `arrconf apply --apps jellyfin` and check that the generators are producing the correct library options.

**Seek-bar thumbnails:** after chapter extraction runs (Jellyfin scheduled task "Extract chapter images"), chapter thumbnails appear in the seek bar in web clients. Verify on at least one library episode.

---

## Step 8 — Skip Button Verification (SC#3 — dispositive)

This is the dispositive success criterion for Phase 24. The skip button must appear during playback on the Jellyfin web client (or Swiftfin/Jellyfin mobile app).

**Wait for analysis to complete first.** Monitor:

```bash
curl -s -H "Authorization: MediaBrowser Token=<JELLYFIN_API_KEY>" \
  http://jellyfin.selfhost.svc.cluster.local:8096/ScheduledTasks \
  | jq '.[] | select(.Name | test("Analyze|Fingerprint"; "i")) | {Name, State, LastExecutionResult}'
```

When `State: "Idle"` and `LastExecutionResult.Status: "Completed"`, analysis is done.

**Verify the skip button:**

1. Open the Jellyfin web client.
2. Play a series episode from a library with known intro (e.g., a TV series where every episode has the same opening sequence).
3. At the intro, confirm a **"Skip Intro"** button appears in the lower-left overlay.
4. At the credits/outro, confirm a **"Skip Credits"** button appears.
5. Click each button — confirm playback jumps forward.

This confirms SC#3 as PASS. Document here:

```
SC#3 verification:
  Date: 2026-05-31
  Episode tested: operator-confirmed (series episode, web client)
  Skip Intro button appeared: [x] YES  [ ] NO
  Skip Credits button appeared: [x] YES  [ ] NO
  Result: [x] PASS  [ ] FAIL
  Notes: SC#1-4 all confirmed PASS during live two-run verification (install queued → restart → plugin Active, single intro-skipper.org repo → web skip button → EnableChapterImageExtraction:true on all 10 libraries).
```

---

## Step 9 — Idempotence Verification (third run)

Run arrconf a third time in dry-run mode. Expect ZERO install/enable/config/library_options actions:

```bash
arrconf apply --apps jellyfin --dry-run --log-level DEBUG
# Expected: no plugin_install_queued, no plugin_enable, no plugin_config_applied,
#           no library_options_updated actions in the output.
```

Any non-zero action count on the third run indicates an idempotence bug — open an issue.

---

## Step 10 — Post-phase ADR-6 Snapshot

```bash
tools/snapshot/snapshot.sh --apps jellyfin --output snapshots/after-phase-24-$(date +%F)/

# Diff against baseline
diff -r snapshots/before-phase-24-*/  snapshots/after-phase-24-*/
# Expected changes: PluginRepositories (one new entry), Plugins list (Intro Skipper Active),
#                   LibraryOptions EnableChapterImageExtraction: true on all 10 libs.
# Expected stable: Tags, DownloadClients, Notifications, Users — no drift.

git add snapshots/after-phase-24-*/
git commit -m "snapshot(post-phase-24): jellyfin after intro-skipper activation"
```

---

## Step 11 — Kodi/JellyCon Salon Spike (SC#5 — non-gating)

**Background:** JellyCon (official Kodi addon) does NOT natively support Jellyfin Media Segments (issue #953). The skip button will NOT appear on LibreELEC with vanilla JellyCon. The only viable Kodi workaround is the `service.jellyskip` addon (SgtJalau/service.jellyskip), which calls the Jellyfin Media Segments API and presents a skip overlay.

This spike is **non-gating** — Phase 24 passes on web/app/Swiftfin alone. Run this at your convenience.

### Install service.jellyskip on LibreELEC (salon box)

`service.jellyskip` is not in the official Kodi addon repository. Install manually:

1. Download the latest release `.zip` from: https://github.com/SgtJalau/service.jellyskip/releases
2. Transfer the `.zip` to the LibreELEC device (USB, scp, or Samba share).
3. On the LibreELEC Kodi interface:
   - Go to **Settings > Add-ons > Install from ZIP file**
   - Navigate to the downloaded `.zip`
   - Install and enable the addon.
4. Configure `service.jellyskip`:
   - Server URL: `http://<jellyfin-ingress-host>` (or the LAN IP of the Jellyfin service)
   - API key: the Jellyfin API key (same as `JELLYFIN_API_KEY`)
   - Enable "Auto detect segments" (connects to the Jellyfin Media Segments API).
5. Restart Kodi or navigate to a series episode.
6. Play an episode with a known intro.
7. Verify: does a skip button / overlay appear during the intro?

### Accept/Reject Decision

```
SC#5 Kodi spike result:
  Date: 2026-05-31
  LibreELEC version: operator-confirmed (salon box)
  Jellyfin version: 10.11.8
  service.jellyskip version: operator-confirmed
  Skip overlay appeared on Kodi: [x] YES  [ ] NO
  
  DECISION: [x] ACCEPT — service.jellyskip works on this LibreELEC + Jellyfin 10.11.8 setup.
            [ ] REJECT — service.jellyskip did not work; Kodi salon has degraded skip-intro.
  
  Notes / failure mode (if REJECT): n/a — accepted.
```

**If REJECT:** The salon Kodi experience is documented as degraded. Skip-intro works on web/app/Swiftfin. No further action required for Phase 24.

**If ACCEPT:** `service.jellyskip` is the supported path for Kodi. Document in PROJECT.md under the Kodi client support table.

---

## Recovery Procedures

### Plugin caused Jellyfin CrashLoopBackOff after restart

```bash
# 1. Exec into a recovery pod with the same /config PVC mounted (or scale down Jellyfin temporarily)
kubectl scale deployment/jellyfin -n selfhost --replicas=0

# 2. Start a recovery pod mounting the jellyfin-config PVC
kubectl run jellyfin-recovery -n selfhost --rm -it \
  --image=busybox --restart=Never \
  --overrides='{"spec":{"volumes":[{"name":"config","persistentVolumeClaim":{"claimName":"jellyfin-config"}}],"containers":[{"name":"recovery","image":"busybox","command":["sh"],"volumeMounts":[{"name":"config","mountPath":"/config"}]}]}}'

# 3. Remove the plugin DLL (adjust path as needed)
ls /config/plugins/
rm -rf /config/plugins/intro-skipper*/
exit

# 4. Restart Jellyfin
kubectl scale deployment/jellyfin -n selfhost --replicas=1
kubectl rollout status deployment/jellyfin -n selfhost
```

### Duplicate plugin repository entries in Jellyfin

Remove via Jellyfin Dashboard > Repositories, or via API:

```bash
# Get current config
curl -s -H "Authorization: MediaBrowser Token=<JELLYFIN_API_KEY>" \
  http://jellyfin.selfhost.svc.cluster.local:8096/System/Configuration > /tmp/jf-config.json

# Edit: remove duplicate intro-skipper entries, keep exactly one
# Then POST the corrected config back
curl -X POST -H "Authorization: MediaBrowser Token=<JELLYFIN_API_KEY>" \
  -H "Content-Type: application/json" \
  -d @/tmp/jf-config.json \
  http://jellyfin.selfhost.svc.cluster.local:8096/System/Configuration
```

### Analysis data lost after pod restart (wrong PVC)

If fingerprint analysis resets to 0% after any pod restart:
1. Fix the Jellyfin volume mount (`charts/arr-stack/values.yaml`) to ensure `/config` is backed by a persistent PVC.
2. Deploy the fix via ArgoCD.
3. Re-trigger the "Analyze Episodes" scheduled task. One-time cost; subsequent runs are incremental.

---

## Client Support Matrix

| Client | Skip button | Notes |
|--------|-------------|-------|
| Jellyfin Web | YES | Native Media Segments API support |
| Jellyfin Android/iOS app | YES | Native support |
| Swiftfin (iOS) | YES | Native support |
| Kodi/JellyCon (LibreELEC) | BEST-EFFORT | Requires `service.jellyskip` addon (not native); result: see SC#5 spike above |
| Infuse | UNKNOWN | No Media Segments integration confirmed; not scoped |

---

*Runbook version: Phase 24 Plan 03*  
*Last updated: 2026-05-29*
