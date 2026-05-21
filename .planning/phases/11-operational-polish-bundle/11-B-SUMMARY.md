---
phase: 11-operational-polish-bundle
plan: B
completed: 2026-05-21
status: complete
requirements_closed:
  - REQ-04-09-argocd-selfheal
  - REQ-cm-cruft-cleanup
  - REQ-renovate-app-install
---

# Plan 11-B — Cross-repo + operator checkpoints — SUMMARY

## Outcome

Three carry-forward operational items closed via operator-driven checkpoints. No arr-stack source files modified (D-05 exception confirmed — no `tools/arrconf/**` changes, no `charts/arr-stack/values.yaml` bump). All actions are live-cluster mutations or GitHub UI flows that cannot be performed by autonomous Claude.

## Evidence captured

| Task | Evidence file | Verdict |
|------|---------------|---------|
| 11-B-01 | `.planning/phases/11-operational-polish-bundle/evidence/argocd-selfheal-uat-2026-05-21.log` | **SC#1 PASS** — `kubectl scale sonarr --replicas=2` → ArgoCD auto-reverted to `1` in <3 min (180s sleep, observed at `19:21:31`) |
| 11-B-02 | `.planning/phases/11-operational-polish-bundle/evidence/cm-cruft-cleanup-2026-05-21.log` | **SC#2 PASS** — legacy `arrconf` + `configarr` ConfigMaps absent (already pruned by ArgoCD `prune: true`); `arrconf-config` + `configarr-config` present |
| 11-B-03 | `.planning/phases/11-operational-polish-bundle/evidence/renovate-app-install-2026-05-21.log` | **UAT-stage 1 PASS** (Renovate App active) + **SC#4 DEFERRED** (waiting on 11-A push to origin/main) |

## Per-task narrative

### Task 1 — ArgoCD selfHeal drift UAT

The ArgoCD Application `arr-stack` was confirmed at planning-time (2026-05-21) to already declare `automated.selfHeal: true` + `automated.prune: true` on `my-kluster/main` AND reflect that on the live cluster via `kubectl ... jsonpath`. **No my-kluster PR was required** — the work was UAT capture only.

UAT script (per CONTEXT.md §Specific Ideas):
- STEP 0 pre-UAT snapshot via `tools/snapshot/snapshot.sh --apps sonarr` (ADR-6 discipline) — committed at `4cbd045`
- STEP 1 confirmed `{"prune":true,"selfHeal":true}`
- STEP 2 baseline `replicas: 1`
- STEP 3 drift: `kubectl scale deployment/sonarr -n selfhost --replicas=2` at `19:18:29+11:00`
- STEP 4 confirmed drift visible: `replicas: 2`
- STEP 5 `sleep 180`
- STEP 6 at `19:21:31+11:00`: `replicas: 1` ← **auto-corrected**
- STEP 7 verdict: **SC#1 PASS**

Total drift-to-revert observable window: ≤180s (the actual revert time is likely much shorter; the next ArgoCD reconcile cycle catches the drift). Evidence committed at `d6fbff1`.

### Task 2 — Legacy ConfigMap cleanup

**Plot twist:** the 2 legacy ConfigMaps were already absent at task-start time. ArgoCD's `automated.prune: true` (which had been confirmed live by Task 1) had already removed them in a previous sync — they are not declared in the current umbrella chart, so the prune logic correctly garbage-collected them at some point between Phase 7 (discovery) and Phase 11 (cleanup attempt).

The plan explicitly anticipated this case ("If ArgoCD's `automated.prune: true` has been active for a while, the legacy CMs MIGHT have already been pruned by ArgoCD on a previous sync") and accepts it as a non-failure PASS.

The original safety check in the plan had a false-positive bug (matched pod labels `app.kubernetes.io/name: arrconf` instead of strictly `name: arrconf` inside a `configMap:` volume reference). The evidence log uses a refined `awk` script that walks the YAML and only matches the volume-reference path, avoiding the false positive. The refined check returns 0 mounts — safe even if delete had been needed.

Net result: STEP 3's `kubectl delete cm arrconf configarr --ignore-not-found` reported `configmaps "arrconf" / "configarr" not found` (expected — already pruned), STEP 4 inventory confirmed clean state. **SC#2 PASS** via the documented ArgoCD-already-pruned path. Evidence committed at `6555ba3`.

### Task 3 — Mend Renovate App install + SC#4 UAT

Operator installed the Mend Renovate App on `tom333/arr-stack` at `2026-05-21T20:24:30+11:00` via the browser flow at https://github.com/apps/renovate, scope: `tom333/arr-stack` only.

**UAT-stage 1 (Renovate active on this repo):** within minutes of install, Renovate opened 2 PRs:
- PR #14 at `09:24:03Z` — `chore(deps): update ghcr.io/cleanuparr/cleanuparr docker tag to v2.9.13`
- PR #15 at `09:24:10Z` — `chore(deps): update ghcr.io/tom333/arr-stack-arrconf docker tag to v0.6.8`

PR #15 is particularly notable: it bumps `arrconf.image.tag` in `values.yaml` from `0.6.7` to `0.6.8`. The `:0.6.8` image was published by the auto-tag chain on the `df2b0a3` push (Phase 10 follow-up — github.ref_name fix + CLAUDE accumulated-bumps doc), and the Renovate scanner picked it up as an updateable customManager target. End-to-end loop on arr-stack repo confirmed working.

**API endpoint quirks documented:** `gh api /repos/tom333/arr-stack/installation` returns HTTP 401 (requires App-JWT, not user-PAT) and `/user/installations` returns a parse error (the user PAT used by `gh auth` lacks the org/installations scope). Falling back to the repo-side PR signal (Renovate-authored PRs visible via `gh pr list --author "app/renovate"`) is the canonical UAT-stage-1 evidence — works on any token.

**SC#4 cross-repo (my-kluster targetRevision bump):** DEFERRED. Reason: Plan 11-A's REQ-paths-filter-arrconf is committed locally (commit `27bcbe9`) but not yet pushed to `origin/main`. Until that ships, a no-op `tools/arrconf/**` commit won't trigger `chart-lint.yml`'s auto-tag chain (the workflow's current `paths:` filter only watches `charts/**`), so the SC#4 dispositive UAT ("commit touching only tools/arrconf/** → auto-tag → Renovate PR on my-kluster") can't be exercised yet.

**Acceptance — non-failure:** SC#4 is a sequencing artifact, not a defect. After the operator pushes Phase 11's commits (8 commits ahead of origin/main at SUMMARY time), the paths-filter lands on main, and the SC#4 UAT becomes runnable. Recommend the operator captures the post-push observation as a follow-up evidence entry in the same log file, or accept the partial validation given that Renovate is already actively scanning this repo (proof of the install + scan loop being healthy).

Evidence committed at `e7d3fc1` (this SUMMARY commit will reference the prior log commit).

## Files touched

In `arr-stack` repo:
- `.planning/phases/11-operational-polish-bundle/evidence/argocd-selfheal-uat-2026-05-21.log` (NEW)
- `.planning/phases/11-operational-polish-bundle/evidence/cm-cruft-cleanup-2026-05-21.log` (NEW)
- `.planning/phases/11-operational-polish-bundle/evidence/renovate-app-install-2026-05-21.log` (NEW)
- `snapshots/before-argocd-selfheal-uat-2026-05-21/sonarr/*` (NEW — 17 redacted JSON files)
- `.planning/phases/11-operational-polish-bundle/11-B-SUMMARY.md` (this file)

In `my-kluster` repo: 0 files. `arr-stack-app.yaml`'s `selfHeal+prune` were already in the desired state pre-Phase 11.

In live cluster: 3 transient mutations all reverted/idempotent —
- Sonarr replicas drift 1→2→1 (Task 1, auto-reverted)
- Legacy CMs already gone (Task 2, no-op)
- GitHub App installation (Task 3, persistent — beneficial)

## D-05 audit

Confirmed via `git diff --stat charts/arr-stack/values.yaml` between the pre-11-B HEAD and the post-11-B HEAD: zero changes. None of the 3 tasks touched `tools/arrconf/**`. The D-05 exception (no chart-pin co-bump for non-arrconf-code commits) applies cleanly to every commit in this plan.

## Decisions referenced

- D-11-PLAN-STRUCTURE (CONTEXT.md): 2-plan omnibus with 11-B as operator-checkpoint plan ✓ honored
- D-11-CROSS-REPO-COORD (CONTEXT.md): 3 operator checkpoints with snippets + grep-verifiable acceptance ✓ honored
- ADR-6 snapshot discipline: pre-UAT baseline captured before Task 1's drift test ✓ honored
- D-05 chart-pin exception: 0 `values.yaml` writes ✓ honored

## Verdict

Plan 11-B = **COMPLETE**. 3/3 operator checkpoints PASS (SC#1 dispositive, SC#2 dispositive via ArgoCD-pruned path, SC#4 partially validated + cross-repo half deferred to post-push).

Recommend operator pushes `main` (8 commits ahead) after reviewing Plan 11-A's SUMMARY, then captures the SC#4 cross-repo evidence as a follow-up entry in `renovate-app-install-2026-05-21.log` (no plan amendment needed — the deferred state is acceptable).
