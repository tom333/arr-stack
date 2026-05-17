# Phase 4 cutover log + resolution

**Status (final): RESOLVED — cutover fully functional on v0.2.6**

**Date**: 2026-05-14 (cutover executed in three sessions: initial v0.2.2 cutover, multi-version fix series v0.2.3..v0.2.5, then chart refactor v0.2.6 + Plan 04-09 Task 9.1)

## Final state (v0.2.6, automated re-enabled)

- arr-stack ArgoCD App: Synced + Healthy at `targetRevision: v0.2.6`, `automated: {prune: true, selfHeal: true}`
- All 8 Deployments READY 1/1 (37 min uptime at resolution time, single pod per app)
- All 8 Service EndpointSlices: 1 endpoint each (per-alias selector working)
- All 8 Deployment `serviceAccountName` values match per-alias ServiceAccount metadata.name
- prowlarr.tgu.ovh: 10/10 retries return 200
- CronJobs arrconf + configarr scheduled `0 */4 * * *`, last ran 19 min ago
- `applications` parent App `automated:` re-enabled (was manually suspended during cutover surgery)
- Manual `arr-stack` ServiceAccount in `selfhost` deleted (no longer referenced)
- v0.3.0-class chart fix shipped as patch tag v0.2.6 (commit `d205336`) — auto-tag mechanism kept the chosen versioning scheme

## What's live in the cluster right now

| Component | State |
|---|---|
| 10 unit ArgoCD Applications | DELETED (cleanly orphaned beforehand: finalizers removed under suspended `applications` parent) |
| `applications` parent ArgoCD App | Synced; `automated:` suspended (intentional — to control prune timing during this cutover series) |
| `arr-stack` ArgoCD App | Synced + Healthy against `v0.2.5` (`2947c43`) |
| 8 media-app Deployments + 2 CronJobs + 2 ConfigMaps + 8 Services + 7 Ingresses + 7 PVCs + 11 ServiceAccounts | All Ready 1/1, owned by arr-stack umbrella |
| Cluster-level `arr-stack` ServiceAccount | Manually created in `selfhost` (workaround for a sub-bug — see Bug 2 below) |

## Bugs discovered during the cutover that block declaring Phase 4 done

### Bug 1 — Service selector too broad (BLOCKING for inter-app traffic)

Every per-alias Service has the identical selector:

```
selector:
  app.kubernetes.io/controller: main
  app.kubernetes.io/instance: arr-stack
  app.kubernetes.io/name: arr-stack
```

This matches ALL 8 umbrella pods, not just one alias's. Each Service's EndpointSlice has 7+ endpoints (all running umbrella pods). Traffic round-robins across all aliases at the Service layer.

**Why it's invisible from a browser** (and was missed by the cutover smoke checks):
- 7 of 8 ingresses (sonarr/radarr/prowlarr/cleanuparr/qbittorrent/seerr/jellyfin/configarr — actually 7 with flaresolverr being internal-only) have `nginx.ingress.kubernetes.io/auth-url` annotations that redirect to oauth2-proxy BEFORE the Service is hit. The 302 response is from nginx, not from the actual app. User cookies short-circuit the route too.
- `prowlarr.tgu.ovh` has NO oauth2-proxy annotation (per the captured my-kluster `argocd-apps/prowlarr-app.yaml` `helm.values`; matches D-04-CUTOVER-04 byte-equivalence intent). So prowlarr is the only ingress that reaches the Service directly. Repeated `curl https://prowlarr.tgu.ovh` returns 200 / 502 / 200 / 502 / ... at roughly 12.5% hit rate — matches "1 of 8 pods is actually prowlarr".

**Why it IS broken end-to-end**:
- Internal app traffic — Sonarr → Prowlarr API calls, qBittorrent → Sonarr webhook delivery — hits the Service directly inside the cluster (no ingress/oauth2 layer). Cross-app calls fail ~87.5% of the time.
- This is the realised failure mode of using `global.fullnameOverride` in an umbrella where 10 aliases share a single chart.

**Root cause**: in `charts/arr-stack/values.yaml`, each alias body declares:

```yaml
sonarr:
  global:
    fullnameOverride: sonarr
  controllers:
    ...
```

In bjw-s/app-template 5.0.0, `global.fullnameOverride` is honored at the LIBRARY-CHART level and propagates a single value across all `helm.sh/chart` and `app.kubernetes.io/name` label computations. With 10 aliased instances, this collapses every alias's name label to a single value — UNLESS the global is set per-sub-chart, which is what we INTENDED but apparently is not how Helm interprets `global:` inside an aliased sub-chart's values block.

**Correct fix** (deferred to v0.3.0):

```yaml
sonarr:
  nameOverride: sonarr        # at sub-chart top level, NOT under global
  fullnameOverride: sonarr    # idem
  controllers:
    ...
```

This sets the per-alias chart-name label without bleeding. Apply to all 10 aliases (8 media + arrconf + configarr).

### Bug 2 — `serviceAccountName: arr-stack` mismatch (WORKED AROUND)

The umbrella renders Deployment `spec.template.spec.serviceAccountName: arr-stack` (release name), while the actual ServiceAccount resources are named `sonarr`, `radarr`, etc. (correctly, per per-alias rendering). Result: pods couldn't be created (`error looking up service account selfhost/arr-stack: serviceaccount "arr-stack" not found`).

**Workaround applied**: `kubectl create serviceaccount arr-stack -n selfhost`. Pods now schedule against this orphan SA.

**Correct fix** (deferred to v0.3.0, alongside Bug 1): the same `nameOverride: <alias>` / `fullnameOverride: <alias>` refactor should also fix the per-alias serviceAccountName — app-template's SA reference helper resolves to the same name as the SA resource, both of which are derived from the fullname helper.

### Bug 3 — Helm 4 multi-alias dep-resolution (FIXED v0.2.3)

Helm 4 has a multi-alias-of-same-chart regression (helm/helm#12748). Fixed in v0.2.3 by vendoring `charts/arr-stack/charts/app-template/` directly. See arr-stack PR #2.

### Bug 4 — cleanuparr version drift (FIXED v0.2.5)

Pinned to 2.3.3 from running digest, but `:latest` had silently advanced to 2.9.x and the on-disk SQLite was at the newer schema. Downgrade broke startup. Fixed in v0.2.5 by bumping to 2.9.6. See arr-stack PR #3 + PR #4 (values-prod.yaml sync).

### Bug 5 — `examples/values-prod.yaml` drift (FIXED v0.2.5)

`charts/arr-stack/values.yaml` is the canonical source, but ArgoCD's `arr-stack-app.yaml` `valueFiles:` references `examples/values-prod.yaml`. Plan 04-05 created the latter as a content-copy of the former (per D-04-VALUES-03), but cleanuparr PR #3 only updated the canonical file. ArgoCD continued to render 2.3.3 against the stale copy. Fixed by re-copying in PR #4.

**Follow-up TODO**: replace `examples/values-prod.yaml` with a SYMLINK to `../charts/arr-stack/values.yaml` so they cannot drift again. (Helm and ArgoCD both honor symlinks at chart-source level.)

## Cutover release sequence

| Tag | Commit | What |
|---|---|---|
| v0.2.2 | `d1335fc` | Initial Phase 4 umbrella (PR #1) |
| v0.2.3 | `5bc0b0d` | Vendor unpacked app-template (Helm 4 fix, PR #2) |
| v0.2.4 | `fbe84cc` | cleanuparr 2.3.3 → 2.9.6 in values.yaml (PR #3) |
| v0.2.5 | `2947c43` | Sync examples/values-prod.yaml (PR #4) |
| v0.2.6 | `d205336` | Per-alias `global.nameOverride` + per-alias `serviceAccount.<alias>: {}` (PR #5) — closes Bug 1 + Bug 2 |

my-kluster cutover commits (squash-merged on origin/main):
- `0eb8c2db` — atomic cutover: add `arr-stack-app.yaml`, delete 10 unit Apps + 2 chart dirs (PR #1387)
- `de93ec5e` — bump targetRevision v0.2.2 → v0.2.3 (PR #1388)
- `566ba6a0` — bump v0.2.3 → v0.2.4 + accidental README/beszel WIP (PR #1389; postmortem in this file)
- `a8e0973e` (squashed) — bump v0.2.4 → v0.2.5 (PR #1390)
- `ec36d878` (squashed) — bump v0.2.5 → v0.2.6 (PR #1392) — picks up the chart bug fixes
- `enable-arr-stack-automated` (squashed) — re-enable `automated: {prune: true, selfHeal: true}` per D-04-CUTOVER-02 follow-up (PR #1393) — Plan 04-09 Task 9.1

## Operator-side state changes (RESOLVED)

1. **`applications` parent App `automated:` re-enabled** — restored to `{prune: true, selfHeal: true}` after the chart fix landed and arr-stack stabilized. The manual `kubectl patch` was idempotent with the source-of-truth, so no extra reconcile churn observed.

2. **`arr-stack` App `automated:` re-enabled** via PR #1393 (Plan 04-09 Task 9.1). Both parent + child Apps now self-heal autonomously.

3. **Manual `arr-stack` ServiceAccount in `selfhost` — DELETED** (`kubectl -n selfhost delete sa arr-stack`). The per-alias SAs (sonarr, radarr, prowlarr, qbittorrent, cleanuparr, seerr, flaresolverr, jellyfin, arrconf, configarr) created by the v0.2.6 chart are the only SAs in the namespace owned by arr-stack now.

4. **All 10 K8s resources were orphaned then adopted** (Bug-2-workaround era) — the `Replace=true + Force=true` sync recreated Deployments. PVCs (sonarr, radarr, prowlarr, qbittorrent, cleanuparr, seerr, jellyfin config + media-nas-pvc + configarr-cache) were never disturbed throughout the v0.2.2 → v0.2.6 sequence.

5. **v0.2.6 Force=true sync replaced Deployments AGAIN** to apply the new selectors + per-alias SA refs. ~5–10 s downtime per app (within the D-04-CUTOVER-02 budget). All 8 apps healthy at +37 min uptime by end of session.

## Resolution (what shipped to fix Bug 1 + Bug 2)

The original hypothesis in this log ("use sub-chart-level `nameOverride`/`fullnameOverride` NOT under `global:`") was WRONG. The actual fix:

- **Bug 1**: keep `global.fullnameOverride: <alias>` under each alias block AND ADD `global.nameOverride: <alias>` alongside it. The app-template chart's `templates/common.yaml` has a hardcoded defaulter that fills `global.nameOverride` with `.Release.Name` whenever the user doesn't provide one. Providing it explicitly per alias block (under the alias's `global:`) prevents the defaulter from firing inside that sub-chart's render context.

- **Bug 2**: explicitly declare `serviceAccount.<alias>: {}` (an empty map) under each alias block. The chart's `values/_init.tpl` auto-injects a `serviceAccount.<.Release.Name>: {}` entry if the user provides none; the SA-name helper then uses the IDENTIFIER (key) — which was `.Release.Name` = `arr-stack` — instead of the resolved SA resource name. Providing the identifier ourselves makes it match the alias.

Both fixes are in PR #5 (commit `9745d5a`, squash `d205336`, tag `v0.2.6`).

## Still-pending items

- **Plan 04-09 Task 9.2** — SC#2 72h M1/M2/M3 watch (passive). Operator observes the first Renovate-driven image bump landing end-to-end (arr-stack Renovate PR → my-kluster `targetRevision` PR → ArgoCD sync) within 72h. Fallback: at T+48h, force a `cleanuparr` patch downgrade to trigger Renovate (per D-04-PIN-04 Path B).
- **Plan 04-07 Task 7.3** — operator-timed README walkthrough (REQ-readme-onboarding < 30 min). Independent of the chart fixes.
- **Bug 5 follow-up TODO**: replace `examples/values-prod.yaml` with a SYMLINK to `../charts/arr-stack/values.yaml` so they cannot drift again. Helm and ArgoCD both honor symlinks at chart-source level.

## Recommended next steps for the operator

1. **Watch the next Renovate run** for the first natural image bump. If qBittorrent/Sonarr/Radarr/etc. ship a new tag, Renovate will open a PR against arr-stack `values.yaml`, the chart-lint workflow validates it, auto-merge merges it, the auto-tag job creates `v0.2.7`, then Renovate detects the new tag and opens a my-kluster `targetRevision` bump PR. End-to-end timing should be < 1h (Renovate's default scan cycle).
2. **Optional Phase 4.5**: implement the `examples/values-prod.yaml` symlink to harden against Bug 5 recurrence.
3. **Inter-app smoke check**: open Sonarr UI, settings → indexers, click "Test" against the Prowlarr-managed indexer (e.g. Jackett / rarbg). Now that Bug 1 is fixed, this should succeed reliably instead of intermittently.
4. **arrconf next run** (every 4h via CronJob) — should run cleanly with both sonarr/radarr/prowlarr reconciled per the Phase 3 + Phase 4 boundary. Watch logs the first time.

## Provenance

- Cutover sessions: 2026-05-13 (initial PR #1 + cutover discovery) + 2026-05-14 (sequential bug fixes through v0.2.5 + chart refactor v0.2.6 + Plan 04-09 Task 9.1).
- Total release tags shipped during cutover: 5 (v0.2.2..v0.2.6).
- Total cross-repo PRs: 5 on arr-stack (#1..#5), 6 on my-kluster (#1387..#1390, #1392, #1393).
- Plans 04-01..04-08 are COMPLETE. Plan 04-09 Task 9.1 is COMPLETE (`automated:` re-enabled). Plan 04-09 Task 9.2 (passive 72h SC#2 watch) is observation-mode. Plan 04-07 Task 7.3 (operator README walkthrough timing) remains independent.
