# Phase 4 execution halted — app-template 4.6.2 → 5.0.0 drift

**Date:** 2026-05-13
**Detected during:** Plan 04-01 Task 1.1 (ADR-6 pre-cutover snapshot)
**Detected by:** orchestrator (gsd-execute-phase)

## What the baseline revealed

`kubectl -n argocd get application <app>` for the 8 media-app ArgoCD Applications (sonarr, radarr, prowlarr, cleanuparr, qbittorrent, seerr, flaresolverr, jellyfin) shows:

- `spec.source.chart: app-template`
- `spec.source.targetRevision: 5.0.0`
- `helm.sh/chart: app-template-5.0.0` (label on rendered K8s objects)
- `status.sync.status: Synced`

…but the **arr-stack Phase 4 plans + RESEARCH.md** assume `app-template 4.6.2` based on the my-kluster *local* checkout that was used during planning.

## Why the plan assumed 4.6.2

The local my-kluster checkout (`/home/moi/projets/perso/my-kluster`) on branch `phase-2.2-arrconf-v0.1.4` was stale by **one commit** — missing `fe6fbfcd chore(deps): update helm release app-template to v5 (#1381)` dated 2026-05-11. That Renovate PR bumped all 8 media-app `argocd-apps/*-app.yaml` files from 4.6.2 → 5.0.0 on `origin/main`, one day before Phase 4 context was gathered (2026-05-12).

`origin/main` has the bump; the working checkout did not, and Phase 4 planning pipeline (CONTEXT.md → RESEARCH.md → PATTERNS.md → 9 PLAN.md files) cascaded the 4.6.2 assumption end-to-end. RESEARCH.md even mentioned that v5.0.0 exists in the chart registry but explicitly chose 4.6.2 "to match byte-equivalence".

## Why this is a blocker

D-04-CUTOVER-03 (byte-equivalent rendering) is the cutover safety gate. With the plans as written:

- Plan 04-02 Chart.yaml hardcodes `version: 4.6.2` × 8 media-app dependencies.
- The umbrella cutover would render `app-template-4.6.2`-labeled manifests.
- ArgoCD live state runs `app-template-5.0.0`-labeled manifests.
- The diff would be non-trivial: any chart-version-sensitive defaults (label sets, `helm.sh/chart` value, possibly default ports / probes / strategy) would change.
- The cutover would effectively be a **silent downgrade** of all 8 media apps.

This is exactly the kind of regression ADR-6 baseline capture is designed to surface before cutover — the discovery is on schedule, but the remediation is a replan, not a continuation.

## What was actually captured (kept; still useful)

Committed to phase dir:

- `evidence/current-image-tags.txt` (3 :latest digest pairs — qbittorrent 5.2.0 / flaresolverr v3.4.6 / cleanuparr 2.3.3, all matching RESEARCH §"Running Image Digests")
- `evidence/pre-cutover-argocd/*.yaml` (10 files; ArgoCD Application CR + live K8s objects per `app.kubernetes.io/instance` selector — kubectl-only fallback because `argocd` CLI is not installed on this workstation; STATE.md Phase 02.2 P05 lesson)

These are valid **5.0.0** baselines — they become the byte-equivalence target for the replan.

## What was skipped

- **Task 1.2** (helper scripts `tools/scripts/check-renovate-annotations.sh` + `byte-equivalence-diff.sh`) — deferred. The scripts are version-agnostic and PATTERNS.md still contains their verbatim source, but they're written by the executor as part of Plan 01 — best to let the replan re-emit Plan 04-01 in case acceptance criteria evolve.
- **Waves 1–7** — not started.

## Operator notes for the replan

1. **my-kluster local sync needed.** Current working checkout is on `phase-2.2-arrconf-v0.1.4` (no upstream). `origin/main` has the bump. Before replanning, the operator should fast-forward the `main` branch locally:
   ```bash
   cd /home/moi/projets/perso/my-kluster
   git checkout main && git pull --ff-only origin main
   # then return to the working branch:
   git checkout phase-2.2-arrconf-v0.1.4
   ```
   This makes `git log main -- argocd/argocd-apps/<app>.yaml` show the 5.0.0 line.

2. **argocd CLI not installed.** Task 1.1 fallback path was used: `kubectl get application <name> -n argocd -o yaml` + `kubectl get all,ingress,configmap,pvc,secret -l app.kubernetes.io/instance=<name>`. Phase 4 Wave 6 cutover tasks (`argocd app diff` / `argocd app sync --server-side`) need either argocd CLI install OR documented kubectl equivalents. The replan should explicitly cover both paths (already partially in Plan 04-08 per the W2 fix from plan-checker iteration 1).

3. **arrconf + configarr were NOT bumped.** PR #1381 touched only the 8 media apps. `arrconf-app.yaml` + `configarr-app.yaml` still use `targetRevision: HEAD` against custom local charts in `my-kluster/charts/{arrconf,configarr}/`. The umbrella plan's CronJob aliases (Plan 04-05) are unaffected by the 5.0.0 bump — they translate from custom-chart YAML, not from app-template version. But the planner should re-confirm whether the CronJob aliases should use app-template **5.0.0** (consistency) or 4.6.2 (no behavioral change). Recommend 5.0.0 across the board.

4. **Helm version OK.** `helm v4.1.4` is well above the 5.0.0 minimum (>= 3.18). No tooling upgrade needed.

5. **Renovate annotation strategy unchanged.** D-04-PIN-03 (`# renovate: image=...` above every `repository:` line) is independent of the app-template version pin. The annotations + customManagers regex from RESEARCH §"Renovate customManagers exact JSON — VERIFIED" still apply.

## Recommended next steps

```bash
# 1. Refresh my-kluster local main
cd /home/moi/projets/perso/my-kluster
git checkout main && git pull --ff-only origin main
git checkout phase-2.2-arrconf-v0.1.4

# 2. Refresh research against current state — keeps CONTEXT.md, regenerates RESEARCH
cd /home/moi/projets/perso/arr-stack
/gsd-plan-phase 4 --research

# 3. Re-spawn planner once research is current
# (The --research flag re-spawns the planner after refreshing RESEARCH.md;
# no manual re-invocation needed.)

# 4. Inspect the regenerated Plan 04-02 Chart.yaml task to confirm
#    `version: 5.0.0` × 8 media-app dependencies (or whatever the latest
#    stable v5 patch is at replan time).

# 5. Re-run /gsd-execute-phase 4 once the new plans are committed.
```

## Affected plans (replan scope)

The replan should regenerate or revise:

- **04-02-chart-skeleton-PLAN.md** — Chart.yaml `version:` field × 8 deps (4.6.2 → 5.0.0 or latest v5 patch).
- **04-03-media-aliases-arr-PLAN.md** + **04-04-media-aliases-misc-PLAN.md** — values.yaml alias bodies may need shape adjustments if v5.0.0 changed any default keys vs 4.6.2. RESEARCH should verify.
- **04-05-cronjob-aliases-schema-PLAN.md** — CronJob aliases also under app-template; the `cronjob:` key location (per RESEARCH Pitfall 1) may have shifted between 4.x and 5.x. Verify.
- **04-06-ci-renovate-PLAN.md** — chart-lint.yml: kubeconform schemas should still target K8s 1.33.0 (cluster version unchanged); no change expected. Renovate customManagers stays the same.
- **04-07-docs-refresh-PLAN.md** — README/CLAUDE.md "Stack technique" should reference app-template 5.x not 4.x.
- **04-08-cutover-PLAN.md** + **04-09-post-cutover-PLAN.md** — byte-equivalence target is now 5.0.0, the captured baseline is correct.

`evidence/current-image-tags.txt` and `evidence/pre-cutover-argocd/*.yaml` remain valid baselines (they snapshot the **actual** production state — that's what cutover must match).

## Plan 04-01 status after this halt

- Task 1.1 (image-digest capture + ADR-6 baseline): ✅ COMPLETE (evidence committed)
- Task 1.2 (helper scripts): ⏸ DEFERRED — re-emitted by replan
- Plan-level status: PARTIAL — pending replan to set Wave 0 acceptance criteria against the corrected plan scope
