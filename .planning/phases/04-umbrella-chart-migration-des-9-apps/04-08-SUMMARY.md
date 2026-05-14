# Plan 04-08 SUMMARY — cutover (Wave 6)

**Status**: COMPLETE
**Date**: 2026-05-13 → 2026-05-14 (multi-session)

## What this plan delivered

The atomic cross-repo cutover from 10 unit ArgoCD Applications + 2 custom charts in `my-kluster` to a single ArgoCD Application pulling tom333/arr-stack@vX.Y.Z. Final operating tag at end of cutover: **v0.2.6**.

## Tasks

| Task | Type | Status | Evidence |
|------|------|--------|----------|
| 8.1 | auto — render umbrella + byte-equivalence diff vs Wave 0 baseline | DONE | `evidence/umbrella-render.yaml` (1672 lines) + `evidence/byte-equivalence-diff.txt` (VERDICT: PROCEED) |
| 8.2 | checkpoint:human-action — open atomic my-kluster PR | DONE | my-kluster PR #1387 (squash `0eb8c2db`) |
| 8.3 | checkpoint:human-action — operator merges + drives kubectl sync | DONE (with iterative bug-fix loop) | 5 cluster-driven sync rounds via `kubectl patch application … operation/sync …` |

## Acceptance criteria (per the plan)

- [x] `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml` produces 8 Deployments, 8 Services, 7 Ingresses, 7 PVCs, 2 CronJobs, 2 ConfigMaps, 10 ServiceAccounts.
- [x] `helm lint charts/arr-stack/ -f examples/values-prod.yaml` exits 0.
- [x] my-kluster cutover PR opened with 1 add (`arr-stack-app.yaml`) + 10 deletes (unit Apps) + 2 chart-dir deletes.
- [x] `arr-stack-app.yaml` ships with `syncOptions: [CreateNamespace=true, ServerSideApply=true, Replace=true]` and NO `automated:` block (D-04-CUTOVER-02).
- [x] `Replace=true` machine-verifiable (W2 from prior iteration).
- [x] Operator-driven kubectl sync sequence executed (kubectl-only fallback per Phase 02.2 P05 lesson — argocd CLI absent on workstation).
- [x] 8/8 Deployments healthy 1/1 after final sync.
- [x] Ingress smoke: 7/7 hostnames respond (`*.tgu.ovh`); prowlarr 10/10 retries return 200 (Bug 1 fix verified end-to-end).
- [x] Per-alias Service EndpointSlices have 1 endpoint each (Bug 1 fix verified).
- [x] Per-alias Deployment `serviceAccountName` matches per-alias `ServiceAccount.metadata.name` (Bug 2 fix verified).
- [x] arrconf + configarr CronJobs scheduled `0 */4 * * *`, both ran cleanly post-cutover.
- [x] `arr-stack` ArgoCD App: Synced + Healthy.
- [x] `applications` parent App: `automated: {prune: true, selfHeal: true}` restored after Bug 1+2 fixed.

## Bugs surfaced + resolved during cutover

5 bugs discovered, all resolved before close. Full diagnosis in `04-08-CUTOVER-LOG.md`. Summary:

| # | Bug | Fix |
|---|-----|-----|
| 1 | Service selector too broad — `app.kubernetes.io/name=arr-stack` matched all 8 pods | v0.2.6: add `global.nameOverride: <alias>` per alias |
| 2 | Pod `serviceAccountName: arr-stack` (release name) vs SA resources named per-alias | v0.2.6: add explicit `serviceAccount.<alias>: {}` per alias |
| 3 | Helm 4 multi-alias-of-same-chart regression (helm/helm#12748) | v0.2.3: vendor unpacked `app-template/` chart directory |
| 4 | cleanuparr 2.3.3 binary vs 2.9.x SQLite schema drift (`:latest` had advanced) | v0.2.5: bump pin to 2.9.6 |
| 5 | `examples/values-prod.yaml` drift vs canonical `values.yaml` (PR #3 only updated canonical) | v0.2.5: re-sync via `cp` (follow-up TODO: symlink) |

## must_haves verification

| Truth (from PLAN.md) | Verified |
|---|---|
| Single `arr-stack-app.yaml` replaces 10 unit ArgoCD Applications | ✓ (my-kluster PR #1387 squash `0eb8c2db`) |
| `charts/arrconf/` + `charts/configarr/` deleted from my-kluster | ✓ (same commit) |
| 8 media-app ingresses respond `*.tgu.ovh` healthy | ✓ (5/7 return 302 = oauth2 redirect, 1 returns 200 (prowlarr), 1 internal-only (flaresolverr)) |
| hostPath `/opt/media-stack/torrents` + NFS `media-nas-pvc` intact | ✓ (PVCs not disturbed across 5 release iterations) |
| Per-alias Service selector matches exactly 1 Deployment | ✓ (EndpointSlice count = 1 for all 8) |
| arr-stack ArgoCD App Synced + Healthy with `automated:` | ✓ (PR #1393 merged, both `automated.{prune,selfHeal}: true`) |
| arrconf + configarr CronJobs scheduled + running on adopted ConfigMaps | ✓ (last ran 19 min ago, schedule `0 */4 * * *`) |

## Key links

- arr-stack PRs: #1 (cutover), #2 (Helm 4 vendor), #3 (cleanuparr bump), #4 (values-prod sync), #5 (nameOverride + SA fix)
- arr-stack tags: v0.2.2..v0.2.6 (5 releases)
- my-kluster PRs: #1387 (cutover), #1388..#1390 (bumps), #1392 (v0.2.6 bump), #1393 (re-enable automated)
- Diagnosis: `04-08-CUTOVER-LOG.md`
- Render snapshot: `evidence/umbrella-render.yaml` (1672 lines from final v0.2.6 render is the byte-equivalence anchor for any future verification work)

## Phase 4 wrap-up state

Plans 04-01..04-08 are all COMPLETE. Plan 04-09 Task 9.1 (re-enable arr-stack `automated:`) is COMPLETE — merged into this cutover sequence as PR #1393. Plan 04-09 Task 9.2 (passive 72h SC#2 watch for first Renovate-driven bump) is observation-mode; operator monitors over the next 72h. Plan 04-07 Task 7.3 (operator-timed README walkthrough) is independent and can be done any time.

Phase 4 is functionally complete; only the 72h passive watch remains as a "wait-state" gate.
