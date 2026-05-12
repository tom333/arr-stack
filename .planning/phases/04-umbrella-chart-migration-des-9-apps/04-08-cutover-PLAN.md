---
phase: 04-umbrella-chart-migration-des-9-apps
plan: 08
type: execute
wave: 6  # W1 — Plans 06 and 07 both occupy wave 5 (parallel); Plan 08 now depends on both. Wave 8 → 7 after the reshuffle (Plan 09).
depends_on: ["04-06", "04-07"]  # W1 — both feed the cutover (CI gate + docs) but can run in parallel within wave 5.
cross_repo: true  # B2 — informational custom key. This plan modifies files in BOTH /home/moi/projets/perso/arr-stack AND /home/moi/projets/perso/my-kluster. See "Cross-repo execution context" below.
files_modified:
  # B2 — Cross-repo files are listed as ACTIVE entries (no longer YAML comments) so plan-parsing tooling can audit them.
  # Plan-tree files (this repo):
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/byte-equivalence-*.diff
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/cutover-log-*.txt
  # Cross-repo files (my-kluster, separate git tree, separate branch + PR):
  - /home/moi/projets/perso/my-kluster/argocd/argocd-apps/arr-stack-app.yaml  # CROSS-REPO add
  - /home/moi/projets/perso/my-kluster/argocd/argocd-apps/sonarr-app.yaml  # CROSS-REPO delete
  - /home/moi/projets/perso/my-kluster/argocd/argocd-apps/radarr-app.yaml  # CROSS-REPO delete
  - /home/moi/projets/perso/my-kluster/argocd/argocd-apps/prowlarr-app.yaml  # CROSS-REPO delete
  - /home/moi/projets/perso/my-kluster/argocd/argocd-apps/cleanuparr-app.yaml  # CROSS-REPO delete
  - /home/moi/projets/perso/my-kluster/argocd/argocd-apps/qbittorrent-app.yaml  # CROSS-REPO delete
  - /home/moi/projets/perso/my-kluster/argocd/argocd-apps/seerr-app.yaml  # CROSS-REPO delete
  - /home/moi/projets/perso/my-kluster/argocd/argocd-apps/flaresolverr-app.yaml  # CROSS-REPO delete
  - /home/moi/projets/perso/my-kluster/argocd/argocd-apps/jellyfin-app.yaml  # CROSS-REPO delete
  - /home/moi/projets/perso/my-kluster/argocd/argocd-apps/configarr-app.yaml  # CROSS-REPO delete
  - /home/moi/projets/perso/my-kluster/argocd/argocd-apps/arrconf-app.yaml  # CROSS-REPO delete
  - /home/moi/projets/perso/my-kluster/charts/configarr/  # CROSS-REPO delete (whole dir)
  - /home/moi/projets/perso/my-kluster/charts/arrconf/  # CROSS-REPO delete (whole dir)
autonomous: false
requirements:
  - REQ-umbrella-deployment
  - REQ-pr-to-cluster-latency
tags: [cross-repo, cutover, argocd, byte-equivalence, my-kluster]
must_haves:
  truths:
    - "An arr-stack release tag (`v0.1.0`) exists on this repo and is reachable as `https://github.com/tom333/arr-stack.git` at `path: charts/arr-stack`"
    - "Local byte-equivalence diff against the Wave 0 baseline produces zero non-trivial differences (only excluded fields: argocd.argoproj.io/*, app.kubernetes.io/instance, helm.sh/chart) — diffs archived in evidence/"
    - "A single PR in my-kluster adds `argocd/argocd-apps/arr-stack-app.yaml` (NO `automated:` block — D-04-CUTOVER-02) AND deletes the 10 unit App YAMLs + `charts/configarr/` + `charts/arrconf/`"
    - "After PR merge, operator runs `argocd app diff arr-stack --server-side` and the diff matches the byte-equivalence expectation, then `argocd app sync arr-stack --server-side` succeeds and `argocd app wait arr-stack --health` returns Healthy"
    - "8 ingress hostnames respond post-cutover (sonarr/radarr/prowlarr/cleanuparr/qbittorrent/seerr/jellyfin all return 200/302/401; configarr-app.yaml was deleted but configarr CronJob remains via umbrella alias — configarr has no ingress)"
    - "arrconf smoke job runs successfully post-cutover with the umbrella-deployed CronJob (exit 0 + no resource churn vs idempotence)"
  artifacts:
    - path: ".planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/byte-equivalence-pre-merge.txt"
      provides: "Local diff result before merging the my-kluster PR — must be empty modulo exclusions"
    - path: ".planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/cutover-log-<date>.txt"
      provides: "Captured output of argocd app diff/sync/wait + smoke job logs"
  key_links:
    - from: "this repo's git tag v0.1.0"
      to: "my-kluster/argocd/argocd-apps/arr-stack-app.yaml targetRevision"
      via: "the PR in my-kluster sets targetRevision: v0.1.0"
      pattern: 'targetRevision: v0.1.0'
    - from: "tools/scripts/byte-equivalence-diff.sh"
      to: ".planning/phases/04-*/evidence/pre-cutover-argocd/"
      via: "diff vs Wave 0 baseline before merging"
      pattern: "byte-equivalence-diff.sh"
---

<objective>
Execute the actual atomic cutover from 10 unit ArgoCD Applications to 1 umbrella ArgoCD Application in `my-kluster`. The chart is content-complete (Plans 02-05), CI-gated (Plan 06), and documented (Plan 07).

Purpose: Closes SC#1 of REQ-umbrella-deployment (ArgoCD sync OK, 9 unit Apps gone, charts/configarr+charts/arrconf gone from my-kluster). Establishes SC#3 (no regression — ingresses respond, shared mounts intact, Jellyfin internal auth preserved). The PR ships WITHOUT `automated:` (D-04-CUTOVER-02) so the operator can manually diff + sync before ArgoCD garbage-collects from the deleted unit Apps.

Output: A merged my-kluster PR, a healthy `arr-stack` ArgoCD Application, archived byte-equivalence diffs in `evidence/`, and a post-cutover smoke job confirming arrconf still works.
</objective>

<cross_repo_execution>
**B2 — Cross-repo execution context.** This plan modifies files in TWO git repositories:

1. **This repo** (`/home/moi/projets/perso/arr-stack`) — commits the byte-equivalence evidence and cutover-log evidence to `.planning/phases/04-.../evidence/`. Normal `git commit && git push` on the current Phase 4 branch (or main, depending on branch strategy at execution time).

2. **my-kluster repo** (`/home/moi/projets/perso/my-kluster`) — adds `argocd/argocd-apps/arr-stack-app.yaml`, deletes 10 unit ArgoCD Application YAMLs + 2 chart directories (`charts/configarr/`, `charts/arrconf/`). The executor MUST `cd /home/moi/projets/perso/my-kluster` for these operations and create a SEPARATE branch + PR in that repository. Do NOT commingle my-kluster file changes with arr-stack commits — they are different git trees with different remotes (arr-stack → `https://github.com/tom333/arr-stack.git`, my-kluster → its own GitHub repo).

The 13 cross-repo paths are listed verbatim in `files_modified:` with absolute paths so plan-parsing tooling can audit them. The inline `# CROSS-REPO add|delete` annotations document the operation per file.

**Branch convention for the my-kluster PR**: `arr-stack-phase4-cutover` (single PR with 1 add + 10 deletions + 2 dir deletions, atomic per D-04-CUTOVER-01).
</cross_repo_execution>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-CONTEXT.md
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-VALIDATION.md
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-01-pre-cutover-baseline-SUMMARY.md
@spec.md
@CLAUDE.md
@/home/moi/projets/perso/my-kluster/CLAUDE.md
@/home/moi/projets/perso/my-kluster/argocd/argocd-apps/configarr-app.yaml
@charts/arr-stack/values.yaml
@examples/values-prod.yaml

<interfaces>
<!-- arr-stack-app.yaml target — verbatim from spec.md §9.2 + PATTERNS §"my-kluster/argocd/argocd-apps/arr-stack-app.yaml" -->

apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: arr-stack
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  destination:
    namespace: selfhost
    server: https://kubernetes.default.svc
  project: selfhost-project
  source:
    repoURL: https://github.com/tom333/arr-stack.git
    targetRevision: v0.1.0
    path: charts/arr-stack
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
      - ServerSideApply=true
    # automated: block OMITTED for first sync — D-04-CUTOVER-02
    # Re-enabled in Plan 09 follow-up PR:
    # automated:
    #   selfHeal: true
    #   prune: true

<!-- Files to delete in my-kluster (cross-repo) — D-04-CUTOVER-01 atomic -->
argocd/argocd-apps/sonarr-app.yaml
argocd/argocd-apps/radarr-app.yaml
argocd/argocd-apps/prowlarr-app.yaml
argocd/argocd-apps/cleanuparr-app.yaml
argocd/argocd-apps/qbittorrent-app.yaml
argocd/argocd-apps/seerr-app.yaml
argocd/argocd-apps/flaresolverr-app.yaml
argocd/argocd-apps/jellyfin-app.yaml
argocd/argocd-apps/configarr-app.yaml
argocd/argocd-apps/arrconf-app.yaml
charts/configarr/  (whole directory)
charts/arrconf/    (whole directory)

<!-- Sequence (D-04-CUTOVER-02) -->
1. Local byte-equivalence diff → must be empty modulo exclusions
2. Cut git tag v0.1.0 on this repo
3. Open my-kluster PR (NO automated: block)
4. ArgoCD app-of-apps auto-discovers arr-stack-app.yaml
5. Operator runs `argocd app diff arr-stack --server-side` (cross-check vs local diff from step 1)
6. Operator runs `argocd app sync arr-stack --server-side`
7. Operator runs `argocd app wait arr-stack --health`
8. Operator runs ingress smoke + arrconf smoke job
9. Plan 09 (next plan) re-enables automated: in a 1-line follow-up PR

<!-- Argocd CLI availability fallback (RESEARCH §Environment Availability + STATE.md Phase 02.2 P05) -->
If argocd CLI not available:
  - app diff fallback:  kubectl get application arr-stack -n argocd -o yaml + visual inspection of .status.sync
  - app sync fallback:  kubectl patch application arr-stack -n argocd --type merge -p '{"operation":{"sync":{"syncOptions":["ServerSideApply=true"]}}}'
  - app wait fallback:  kubectl get application arr-stack -n argocd -o jsonpath='{.status.sync.status} {.status.health.status}'  (loop until "Synced Healthy")
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 8.1: Run local byte-equivalence diff against Wave 0 baseline and archive the result</name>
  <files>.planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/byte-equivalence-pre-merge.txt, .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/byte-equivalence-*.diff</files>
  <read_first>
    tools/scripts/byte-equivalence-diff.sh (the helper script committed in Plan 01)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/pre-cutover-argocd/ (Wave 0 baseline)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md §Unknown #9 (exclusion list rationale)
    examples/values-prod.yaml (the values file to pass to helm template)
  </read_first>
  <action>
    Run the byte-equivalence diff helper:

    ```bash
    helm repo add bjw-s-labs https://bjw-s-labs.github.io/helm-charts 2>/dev/null || true
    helm dependency update charts/arr-stack/  # idempotent — Chart.lock unchanged

    tools/scripts/byte-equivalence-diff.sh \
      .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence \
      examples/values-prod.yaml \
      | tee .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/byte-equivalence-pre-merge.txt
    ```

    Expected output: 10 lines, each starting with `OK:` for each of the 10 apps (sonarr, radarr, prowlarr, cleanuparr, qbittorrent, seerr, flaresolverr, jellyfin, arrconf, configarr).

    If ANY app reports `DIFF:`, inspect the corresponding `evidence/byte-equivalence-<app>.diff` file:
    - **Acceptable diffs** (will be present in every run, NOT regressions — re-validate the exclusion regex in `byte-equivalence-diff.sh` catches them all):
      - `app.kubernetes.io/instance` change (unit App: `<app-name>`; umbrella: `arr-stack`).
      - `helm.sh/chart` change (`app-template-4.6.2` → `arr-stack-0.1.0`).
      - `argocd.argoproj.io/*` label/annotation changes.
      - `resourceVersion`, `uid`, `creationTimestamp` differences.
    - **Unacceptable diffs** (block cutover until reconciled):
      - Container image tag change (other than the intentional `:latest` → semver pin for qbit/flaresolverr/cleanuparr).
      - Removed/renamed env vars.
      - Different `securityContext`.
      - Missing `tty: true` on configarr.
      - Removed `checksum/config` annotation **is acceptable** (D-04-CRON-02 — intentional drop, document in SUMMARY).
      - Changed ingress hostnames, TLS secret names, or annotation set (except removed comments).
      - Changed mount paths / hostPath / existingClaim / storageClass.
      - Removed `concurrencyPolicy: Forbid`.
      - Changed PVC sizes or accessModes.

    If unacceptable diffs found:
    1. Document them in the SUMMARY.
    2. Fix `charts/arr-stack/values.yaml` in a new commit on this branch.
    3. Re-run the diff helper.
    4. Iterate until all diffs are acceptable.

    DO NOT proceed to Task 8.2 until byte-equivalence-pre-merge.txt shows 10 OK lines OR all diffs are documented as acceptable in the SUMMARY.

    Commit the evidence:
    ```bash
    git add .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/byte-equivalence-pre-merge.txt
    git add .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/byte-equivalence-*.diff 2>/dev/null || true
    git commit -m "docs(04): pre-cutover byte-equivalence diff archive"
    ```
  </action>
  <verify>
    <automated>
      test -f .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/byte-equivalence-pre-merge.txt && \
      [ "$(grep -c '^OK ' .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/byte-equivalence-pre-merge.txt)" -ge 10 -o \
        "$(grep -c '^DIFF: ' .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/byte-equivalence-pre-merge.txt)" -eq 0 ]
    </automated>
  </verify>
  <acceptance_criteria>
    - `evidence/byte-equivalence-pre-merge.txt` exists.
    - Either all 10 apps report `OK:` (zero diffs), OR every reported `DIFF:` is justified as acceptable in the Plan 08 SUMMARY (with explicit reference to the field type: ArgoCD labels, app-name instance label, helm.sh/chart relabel, etc.).
    - Evidence committed in this branch.
  </acceptance_criteria>
  <done>
    Local byte-equivalence verified. The chart renders an output that, modulo well-understood metadata differences, matches the current ArgoCD-managed state.
  </done>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 8.2: Cut git tag v0.1.0 on this repo (release for ArgoCD targetRevision)</name>
  <files>(git tag — no file changes in working tree)</files>
  <read_first>
    .planning/STATE.md `[Phase 02.2 P04]` (annotated tag + GHCR build pattern — though this is a chart-only release, no image to build)
    spec.md §11 ADR-3/D-37 (atomic single-tag pattern)
    Recent `git tag` output: previous tags include `v0.1.0`, `v0.1.1` (STATE.md notes these are "bootstrap artifacts only — see 02-02-SUMMARY.md deviations" and did NOT produce GHCR images)
  </read_first>
  <what-built>
    Nothing yet — operator must cut and push the tag.

    **CRITICAL prerequisite check**: Tag `v0.1.0` may ALREADY EXIST from Phase 0 bootstrap (STATE.md line 149: "v0.1.0 + v0.1.1 tags exist on origin but did NOT produce GHCR images — bootstrap artifacts only"). Run BEFORE cutting:
    ```bash
    git fetch --tags
    git tag -l 'v0.1.*'
    ```
    If `v0.1.0` already exists pointing to a Phase 0 commit, DO NOT force-overwrite. Use `v0.2.1` instead (next available patch tag after Phase 3's `v0.2.0` arrconf release) OR `v0.4.0` if a clean major boundary is preferred. The cutover does NOT depend on a specific tag name — only on the `targetRevision` value in arr-stack-app.yaml matching the tag.

    Reconcile the chosen tag name in the SUMMARY before Task 8.3 writes `targetRevision`.
  </what-built>
  <how-to-verify>
    OPERATOR steps:

    ```bash
    # 1. Verify all Phase 4 commits are on main (or the working branch ready to merge)
    git status
    git log --oneline -20

    # 2. Decide tag name (see prerequisite check above)
    TAG=v0.1.0   # or v0.2.1 / v0.4.0 if v0.1.0 is already taken
    git tag -l "$TAG"   # must return EMPTY for a fresh tag

    # 3. Cut annotated tag pointing at HEAD of the branch with all Phase 4 commits
    git tag -a "$TAG" -m "release: $TAG — umbrella chart Phase 4 cutover

    - charts/arr-stack/ umbrella chart with 10 app-template aliases (Plans 02-05)
    - chart-lint CI + Renovate customManagers (Plan 06)
    - README + CLAUDE.md refresh (Plan 07)
    - Cutover from 10 unit ArgoCD Applications to 1 (Plan 08)

    SC#1 of REQ-umbrella-deployment / D-04-CUTOVER-01."

    # 4. Push
    git push origin "$TAG"

    # 5. Verify the tag is fetchable from a fresh clone (or via `git ls-remote`)
    git ls-remote --tags origin "$TAG"
    ```

    Then type `tag-pushed v0.1.0` (or whichever tag name was used).
  </how-to-verify>
  <acceptance_criteria>
    - The chosen tag exists on origin: `git ls-remote --tags origin '<TAG>'` returns a non-empty line.
    - The tag is annotated: `git for-each-ref refs/tags/<TAG> --format='%(objecttype)'` returns `tag` (not `commit`).
    - The operator has noted the EXACT tag name in the resume signal so Task 8.3 can hardcode `targetRevision: <TAG>` correctly.
  </acceptance_criteria>
  <resume-signal>Type "tag-pushed &lt;TAG&gt;" (e.g. "tag-pushed v0.1.0").</resume-signal>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 8.3: Open the atomic my-kluster cutover PR + operator-driven sync</name>
  <files>(cross-repo: my-kluster — 1 new file + 12 deletions)</files>
  <read_first>
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-CONTEXT.md (D-04-CUTOVER-01..04 — atomic PR, no automated:, byte-equivalent, rollback = revert)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md §Unknown #5 (ArgoCD ServerSideApply adoption mechanics)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"my-kluster/argocd/argocd-apps/arr-stack-app.yaml (new)" (verbatim target)
    /home/moi/projets/perso/my-kluster/argocd/argocd-apps/configarr-app.yaml (analog with ServerSideApply already set)
    /home/moi/projets/perso/my-kluster/CLAUDE.md (sister repo conventions)
  </read_first>
  <what-built>
    Will be built BY THE OPERATOR (this is a cross-repo PR + a manual ArgoCD sync — not Claude-automatable as a single command flow).
  </what-built>
  <how-to-verify>
    OPERATOR runs the following sequence on the my-kluster repo (working tree). Substitute `<TAG>` with the tag pushed in Task 8.2.

    **Step 1 — branch and add the new Application file** (verbatim from PATTERNS §"my-kluster/argocd/argocd-apps/arr-stack-app.yaml" target, NO `automated:` block per D-04-CUTOVER-02):

    ```bash
    cd /home/moi/projets/perso/my-kluster
    git fetch origin
    git checkout -b arr-stack-phase4-cutover origin/main

    cat > argocd/argocd-apps/arr-stack-app.yaml <<'EOF'
    apiVersion: argoproj.io/v1alpha1
    kind: Application
    metadata:
      name: arr-stack
      namespace: argocd
      finalizers:
        - resources-finalizer.argocd.argoproj.io
    spec:
      destination:
        namespace: selfhost
        server: https://kubernetes.default.svc
      project: selfhost-project
      source:
        repoURL: https://github.com/tom333/arr-stack.git
        targetRevision: <TAG>
        path: charts/arr-stack
      syncPolicy:
        syncOptions:
          - CreateNamespace=false
          - ServerSideApply=true
        # automated: block intentionally OMITTED at first sync (D-04-CUTOVER-02).
        # Plan 09 re-enables in a follow-up 1-line PR after manual sync verification.
    EOF
    ```

    Edit the `targetRevision: <TAG>` line to the EXACT tag from Task 8.2 (e.g. `v0.1.0`).

    **Step 2 — delete the 10 unit Application files + 2 chart dirs** (verbatim list — atomic per D-04-CUTOVER-01):

    ```bash
    git rm \
      argocd/argocd-apps/sonarr-app.yaml \
      argocd/argocd-apps/radarr-app.yaml \
      argocd/argocd-apps/prowlarr-app.yaml \
      argocd/argocd-apps/cleanuparr-app.yaml \
      argocd/argocd-apps/qbittorrent-app.yaml \
      argocd/argocd-apps/seerr-app.yaml \
      argocd/argocd-apps/flaresolverr-app.yaml \
      argocd/argocd-apps/jellyfin-app.yaml \
      argocd/argocd-apps/configarr-app.yaml \
      argocd/argocd-apps/arrconf-app.yaml

    git rm -r charts/configarr/ charts/arrconf/
    ```

    **Step 3 — verify the AppProject `selfhost-project` whitelist includes the arr-stack repo** (RESEARCH Open Question 4):

    ```bash
    grep -A 10 'sourceRepos' argocd/argocd-appprojects/selfhost-project.yaml
    # If `https://github.com/tom333/arr-stack.git` is NOT listed, add it inline as an additional
    # commit in this same PR — otherwise ArgoCD will refuse to sync arr-stack-app.yaml with
    # error "application repo not permitted in project".
    ```

    If you need to add the repo, edit `argocd/argocd-appprojects/selfhost-project.yaml` to include `https://github.com/tom333/arr-stack.git` under `spec.sourceRepos:`.

    **Step 4 — stage + commit + push + open PR**:

    ```bash
    git add argocd/argocd-apps/arr-stack-app.yaml
    git status   # confirm: 1 added, 10 unit App files deleted, charts/{arrconf,configarr}/ dirs deleted, optional 1 modified (selfhost-project.yaml)

    git commit -m "feat(arr-stack): cutover to umbrella chart (Phase 4 atomic PR)

    D-04-CUTOVER-01 — atomic big-bang: add arr-stack-app.yaml pulling
    https://github.com/tom333/arr-stack.git@<TAG> at path charts/arr-stack;
    delete the 10 unit ArgoCD Applications + charts/configarr/ + charts/arrconf/.

    D-04-CUTOVER-02 — first sync is operator-driven: automated: block omitted.
    Plan 09 re-enables automated.{selfHeal,prune} in a 1-line follow-up PR after
    manual verification.

    D-04-CUTOVER-03 — byte-equivalent rendering verified locally on arr-stack:
    .planning/phases/04-*/evidence/byte-equivalence-pre-merge.txt — 10 OK.

    D-04-CUTOVER-04 — rollback = git revert this PR (PVCs survive prune:false during cutover)."

    git push origin arr-stack-phase4-cutover
    gh pr create --title "feat(arr-stack): cutover to umbrella chart (Phase 4)" --body "$(cat <<'EOF'
    ## Summary

    Phase 4 atomic cutover per D-04-CUTOVER-01:
    - Add `arr-stack-app.yaml` pulling `tom333/arr-stack@<TAG>` at `path: charts/arr-stack`
    - Delete 10 unit ArgoCD Applications (sonarr/radarr/prowlarr/cleanuparr/qbittorrent/seerr/flaresolverr/jellyfin/configarr/arrconf)
    - Delete `charts/configarr/` and `charts/arrconf/` directories
    - `automated:` block omitted on the new Application — operator drives first sync (D-04-CUTOVER-02)

    Local byte-equivalence diff against ArgoCD baseline is empty modulo expected exclusions (argocd labels, helm.sh/chart, app.kubernetes.io/instance) — see arr-stack repo `.planning/phases/04-*/evidence/byte-equivalence-pre-merge.txt`.

    ## Test plan
    - [ ] PR merged
    - [ ] argocd app diff arr-stack --server-side reviewed
    - [ ] argocd app sync arr-stack --server-side succeeds
    - [ ] argocd app wait arr-stack --health returns Healthy
    - [ ] 8 ingress hostnames respond
    - [ ] arrconf smoke job (kubectl create job --from=cronjob/arrconf arrconf-cutover-smoke) exits 0
    - [ ] Follow-up PR (Plan 09 in arr-stack) re-enables automated.{selfHeal,prune}
    EOF
    )"
    ```

    **Step 5 — operator merges the PR via the GitHub UI** (review the diff there for safety).

    **Step 6 — wait for the unit App finalizers to complete** (RESEARCH §Unknown #5 — typically 30-90 seconds):
    ```bash
    # Primary path:
    while argocd app list 2>/dev/null | grep -qE '^(sonarr|radarr|prowlarr|cleanuparr|qbittorrent|seerr|flaresolverr|jellyfin|configarr|arrconf)\s'; do
      echo "waiting for unit Apps to disappear..."
      sleep 5
    done
    # Fallback (no argocd CLI):
    # while kubectl get applications -n argocd -o name | grep -qE 'application.argoproj.io/(sonarr|radarr|prowlarr|cleanuparr|qbittorrent|seerr|flaresolverr|jellyfin|configarr|arrconf)$'; do
    #   sleep 5
    # done
    ```

    **Step 7 — verify arr-stack Application is created but OutOfSync** (because no `automated:`):
    ```bash
    argocd app get arr-stack  # OR: kubectl get application arr-stack -n argocd -o yaml
    # Expected: .status.sync.status == OutOfSync (manual sync gate per D-04-CUTOVER-02).
    ```

    **Step 8 — manual diff + sync + wait** (capture output for evidence):
    ```bash
    EVIDENCE_DIR=/home/moi/projets/perso/arr-stack/.planning/phases/04-umbrella-chart-migration-des-9-apps/evidence
    DATE=$(date +%FT%H%M%S)

    argocd app diff arr-stack --server-side 2>&1 \
      | tee "${EVIDENCE_DIR}/cutover-log-${DATE}-01-diff.txt"

    # Review the diff. It must contain ONLY:
    # - additions of resources (none expected — adoption via ServerSideApply)
    # - field-manager migrations
    # - excluded fields (argocd labels, helm.sh/chart, instance label)

    # If the diff is acceptable, sync:
    argocd app sync arr-stack --server-side 2>&1 \
      | tee "${EVIDENCE_DIR}/cutover-log-${DATE}-02-sync.txt"

    argocd app wait arr-stack --health --timeout 300 2>&1 \
      | tee "${EVIDENCE_DIR}/cutover-log-${DATE}-03-wait.txt"
    ```

    **Step 9 — ingress smoke (8 hostnames)**:
    ```bash
    for h in sonarr radarr prowlarr cleanuparr qbittorrent seerr jellyfin; do
      curl -I -s -o /dev/null -w "%{http_code} %{url_effective}\n" "https://${h}.tgu.ovh"
    done | tee "${EVIDENCE_DIR}/cutover-log-${DATE}-04-ingress.txt"
    # Expected: each line ends in 200, 302, or 401 (oauth2-proxy challenges count as healthy).
    # cleanuparr also has an ingress; configarr does NOT.
    ```

    **Step 10 — arrconf smoke job** (idempotence dispositive):
    ```bash
    kubectl -n selfhost create job --from=cronjob/arrconf arrconf-cutover-smoke-${DATE//[:T]/}
    sleep 30   # wait for pod to schedule + complete
    kubectl -n selfhost logs job/arrconf-cutover-smoke-${DATE//[:T]/} \
      | tee "${EVIDENCE_DIR}/cutover-log-${DATE}-05-arrconf-smoke.txt"
    # Expected: exit 0 (kubectl get job ... -o jsonpath='{.status.succeeded}' returns 1)
    # AND no resource mutations (idempotence — log shows plan_action no-op for all reconciled resources).
    ```

    **Step 11 — commit evidence back in arr-stack**:
    ```bash
    cd /home/moi/projets/perso/arr-stack
    git add .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/cutover-log-*.txt
    git commit -m "docs(04): cutover evidence — argocd sync + ingress smoke + arrconf smoke"
    git push
    ```

    Then type `cutover-complete` (or describe blockers).
  </how-to-verify>
  <acceptance_criteria>
    - my-kluster PR merged on `main` of `my-kluster` (one PR with 1 add + 10 deletions + 2 dir deletions).
    - **W2 — machine-verifiable `automated:` absence (D-04-CUTOVER-02 safety)**: `! grep -qE '^[[:space:]]*automated:' /home/moi/projets/perso/my-kluster/argocd/argocd-apps/arr-stack-app.yaml` (exit 0 = absent = correct; exit 1 = present = MUST be removed before merge). This guard replaces the prior prose-only check so the executor can `bash -c` it directly and a future CI lint in my-kluster could pick it up.
    - `argocd app get arr-stack` returns sync status `Synced` AND health `Healthy` (or kubectl fallback equivalent).
    - 8 ingress hostnames respond with 200/302/401: `grep -cE '^(200|302|401)' .../cutover-log-*-04-ingress.txt` >= 7 (sonarr/radarr/prowlarr/cleanuparr/qbittorrent/seerr/jellyfin — 7; configarr has no ingress; flaresolverr no ingress).
    - arrconf smoke job exits 0 with no resource mutations: `.../cutover-log-*-05-arrconf-smoke.txt` shows `apply_complete` (or equivalent Phase 3 success marker) and no `plan_action action=create|update|delete` events beyond what idempotence allows.
    - All cutover-log evidence files committed in arr-stack repo.
    - Unit Apps are gone from ArgoCD: `argocd app list | grep -cE '^(sonarr|radarr|prowlarr|cleanuparr|qbittorrent|seerr|flaresolverr|jellyfin|configarr|arrconf)\s'` returns 0.
  </acceptance_criteria>
  <resume-signal>Type "cutover-complete" once the my-kluster PR is merged, ArgoCD sync is Healthy, ingress smoke + arrconf smoke pass, and evidence is committed. Type "cutover-blocked: &lt;reason&gt;" otherwise.</resume-signal>
</task>

</tasks>

<verification>
- `evidence/byte-equivalence-pre-merge.txt` exists and shows 10 OK or every DIFF is documented as acceptable.
- Git tag (e.g. v0.1.0) pushed and reachable.
- my-kluster PR merged.
- `argocd app get arr-stack` shows Synced + Healthy.
- 8 ingress hostnames respond (sonarr/radarr/prowlarr/cleanuparr/qbittorrent/seerr/jellyfin; flaresolverr internal-only; configarr no ingress).
- arrconf smoke job exits 0.
- Cutover-log evidence committed in arr-stack repo.
</verification>

<success_criteria>
SC#1 of REQ-umbrella-deployment satisfied: 9 apps deployed via 1 chart (configarr CronJob is the 10th workload, no ingress); 9 unit Apps + charts/{configarr,arrconf}/ removed from my-kluster.

SC#3 satisfied: ingresses still respond; arrconf still works post-cutover.

SC#4 partially satisfied: `:latest` tags pinned (verified in Plans 03-05); annotations present (verified by `check-renovate-annotations.sh`); SC#4 fully closes when CI in Plan 06 PR went green.
</success_criteria>

<output>
After completion, create `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-08-cutover-SUMMARY.md` covering:
- The exact tag name used (was it `v0.1.0` or something else?).
- The my-kluster PR URL.
- ArgoCD app sync timeline (start, sync duration, health-ready time).
- Ingress smoke results (per-hostname status codes).
- arrconf smoke job verdict (exit code + idempotence summary).
- Any diffs that needed acceptance (vs the pre-merge expectation) and rationale.
- Any unit-App finalizer race observations (RESEARCH Assumption A3 was untested in staging).
</output>
