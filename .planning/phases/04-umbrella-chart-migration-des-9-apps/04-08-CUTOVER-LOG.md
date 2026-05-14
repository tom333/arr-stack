# Phase 4 cutover log + halt note

**Status: HALTED — internal traffic broken, browser-facing seemingly OK**

**Date**: 2026-05-14 (cutover executed in two sessions ending here)

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

my-kluster cutover commits (squash-merged on origin/main):
- `0eb8c2db` — atomic cutover: add `arr-stack-app.yaml`, delete 10 unit Apps + 2 chart dirs (PR #1387)
- `de93ec5e` — bump targetRevision v0.2.2 → v0.2.3 (PR #1388)
- `566ba6a0` — bump v0.2.3 → v0.2.4 + accidental README/beszel WIP (PR #1389; postmortem in this file)
- `a8e0973e` (squashed into `bump-arr-stack-v0.2.5` merge) — bump v0.2.4 → v0.2.5 (PR #1390)

## Operator-side state changes still in effect (need follow-up)

1. **`applications` parent App `automated:` suspended.** I manually removed `syncPolicy.automated` so that prune wouldn't cascade-delete K8s resources at cutover. Needs re-enabling (`kubectl patch application applications -n argocd --type merge -p '{"spec":{"syncPolicy":{"automated":{"prune":true,"selfHeal":true}}}}'`) once the chart bugs are fixed and we're confident steady-state is desired. This SHOULD be done by re-applying the my-kluster source-of-truth which still has `automated:` on `applications-app.yaml` — but ArgoCD selfHeal will then try to roll back our manual patch on `applications`. Specifically: `kubectl annotate application applications -n argocd argocd.argoproj.io/refresh=hard --overwrite` followed by trusting selfHeal to reconcile.

2. **`arr-stack` App `automated:` omitted by design** (D-04-CUTOVER-02). Plan 04-09 Task 9.1 re-adds it via a one-line my-kluster PR. NOT done yet — withheld until Bug 1 + Bug 2 are properly fixed.

3. **`arr-stack` ServiceAccount in `selfhost`** — manually created, no chart owns it. Will be a stray resource until either the chart fix lands (deletes the manual SA and replaces with per-alias ones) or the chart is rolled back.

4. **All 10 K8s resources were orphaned then adopted** — the `Replace=true + Force=true` sync recreated all Deployments cleanly. PVCs (sonarr, radarr, prowlarr, qbittorrent, cleanuparr, seerr, jellyfin config + media-nas-pvc + configarr-cache) were not disturbed.

## Recommended next steps

1. **Don't continue using inter-app features** (Sonarr's "Test" on the qBit/Prowlarr indexer download client, etc.) — they will misroute 87.5% of the time. Browse-only usage is OK.
2. **Plan a Phase 4.1 / v0.3.0 release** with:
   - Sub-chart-level `nameOverride: <alias>` + `fullnameOverride: <alias>` for all 10 aliases (NOT under `global:`)
   - Verify Service selectors match exactly one Deployment per alias
   - Verify rendered Deployment `spec.template.spec.serviceAccountName` matches the per-alias ServiceAccount metadata.name
   - Remove the manually-created `arr-stack` ServiceAccount once the chart starts emitting matching values
   - Smoke check: `kubectl exec deploy/sonarr -- curl -sS http://prowlarr:9696/api/v1/system/status` returns the right system info (proves the per-alias Service selector is correct)
3. **`examples/values-prod.yaml` → symlink** to prevent drift (Bug 5 follow-up).
4. **Plan 04-09 Tasks 9.1 + 9.2** stay PENDING until v0.3.0 lands.
5. **Plan 04-07 Task 7.3** (operator-timed README walkthrough) — independent of the chart bugs; still useful to verify REQ-readme-onboarding < 30 min budget.

## Provenance

- Cutover sessions: 2026-05-13 (initial PR #1 + cutover discovery) + 2026-05-14 (this session, sequential bug fixes through v0.2.5).
- Total release tags shipped during cutover: 4 (v0.2.2..v0.2.5).
- Total cross-repo PRs: 4 on arr-stack, 4 on my-kluster.
- Plans 04-01..04-07 + Plan 04-08 Tasks 8.1+8.2 are COMPLETE. Plan 04-08 Task 8.3 is **PARTIAL** — operator-driven sync executed, but discovered Bug 1 + Bug 2 above. Plans 04-09 PENDING.
