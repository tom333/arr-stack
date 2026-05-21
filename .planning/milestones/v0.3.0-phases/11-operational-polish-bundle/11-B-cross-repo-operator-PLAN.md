---
phase: 11-operational-polish-bundle
plan: B
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: false
requirements:
  - REQ-04-09-argocd-selfheal
  - REQ-cm-cruft-cleanup
  - REQ-renovate-app-install

must_haves:
  truths:
    - "ArgoCD Application `arr-stack` in namespace `argocd` has both `automated.selfHeal: true` and `automated.prune: true` ACTIVE on the live cluster — verified via `kubectl ... -o jsonpath='{.spec.syncPolicy.automated}'` returning `{\"prune\":true,\"selfHeal\":true}`."
    - "A manual drift (kubectl scale on a deployment managed by arr-stack chart) is auto-reverted by ArgoCD within 3 minutes — SC#1 dispositive UAT evidence captured."
    - "Namespace `selfhost` no longer contains the legacy ConfigMaps `arrconf` (1349 B, sonarr-only) nor `configarr` (9271 B); the current `arrconf-config` and `configarr-config` remain."
    - "Mend Renovate App is installed on `github.com/tom333/arr-stack` (or on the user/org with arr-stack in scope); a new arr-stack tag opens a Renovate PR on `my-kluster/argocd/argocd-apps/arr-stack-app.yaml#targetRevision` within one scan cycle."
  artifacts:
    - path: ".planning/phases/11-operational-polish-bundle/evidence/argocd-selfheal-uat-<date>.log"
      provides: "SC#1 dispositive evidence — kubectl scale → auto-revert"
    - path: ".planning/phases/11-operational-polish-bundle/evidence/cm-cruft-cleanup-<date>.log"
      provides: "SC#2 dispositive evidence — kubectl get cm before+after"
    - path: ".planning/phases/11-operational-polish-bundle/evidence/renovate-app-install-<date>.log"
      provides: "SC#4 dispositive evidence — Renovate PR opened on my-kluster"
    - path: ".planning/phases/11-operational-polish-bundle/11-B-SUMMARY.md"
      provides: "Plan summary with operator timestamps + PR/cleanup numbers"
  key_links:
    - from: "my-kluster/argocd/argocd-apps/arr-stack-app.yaml (LIVE STATE — already configured as of 2026-05-21)"
      to: "ArgoCD Application arr-stack — automated.selfHeal/prune"
      via: "GitOps sync"
      pattern: "selfHeal: true\\s+prune: true"
    - from: "kubectl -n selfhost delete cm arrconf configarr"
      to: "namespace selfhost ConfigMap inventory"
      via: "kubectl apply (operator action)"
      pattern: "^arrconf-config\\s|^configarr-config\\s"
    - from: "https://github.com/apps/renovate Install flow"
      to: "github.com/tom333/arr-stack repo permissions"
      via: "GitHub Apps install (browser UI, operator action)"
      pattern: "renovate"
---

<objective>
Close the three cross-repo / cluster-live / GitHub-UI carry-forward operational items from v0.2.0 — each requires operator action that arrconf code cannot perform.

1. **REQ-04-09-argocd-selfheal** — capture dispositive UAT evidence that `automated.selfHeal: true` + `automated.prune: true` are LIVE on the cluster and auto-correct a manual drift within 3 min. (NB: the YAML config in `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` is ALREADY in the desired state as of 2026-05-21 — see Task 1 — so this task is verify + drift-UAT, not edit-and-PR.)
2. **REQ-cm-cruft-cleanup** — operator runs `kubectl -n selfhost delete cm arrconf configarr` to remove the two legacy ConfigMaps left over from the Phase 4 cutover.
3. **REQ-renovate-app-install** — operator installs the Mend Renovate App on `github.com/tom333/arr-stack` via the GitHub Apps install flow (browser UI).

Purpose: clear the 3 cross-repo / live-cluster items in the v0.3.0 closeout bundle. None of these are doable from autonomous Claude — all three need either cluster credentials, live-cluster mutation auth, or a browser-based GitHub App install flow with org approval.

Output: 3 operator-actioned changes + 3 evidence files + 1 SUMMARY.md.

**Sequencing note:** Plan 11-B-03 (Renovate App install UAT for SC#4) DEPENDS on Plan 11-A Task 2 (REQ-paths-filter-arrconf) being merged FIRST — without the `tools/arrconf/**` paths filter, a no-chart arrconf-only commit will NOT auto-tag, and SC#4's "new tag → Renovate PR on my-kluster" chain cannot be exercised. Document this explicitly in Task 3's `<action>`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/11-operational-polish-bundle/11-CONTEXT.md
@CLAUDE.md
@/home/moi/projets/perso/my-kluster/argocd/argocd-apps/arr-stack-app.yaml

<interfaces>
<!-- Existing live cluster + sister-repo state. Captured 2026-05-21. -->

From `/home/moi/projets/perso/my-kluster/argocd/argocd-apps/arr-stack-app.yaml` lines 22-26 (CURRENT STATE on `main`):
```yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=true
    - ServerSideApply=true
    # Replace=true was REMOVED in Phase 10 PR #1403 (PVC immutability conflict)
  automated:
    prune: true
    selfHeal: true
```

From `kubectl -n argocd get application arr-stack -o jsonpath='{.spec.syncPolicy.automated}'` (LIVE state captured 2026-05-21):
```
{"prune":true,"selfHeal":true}
```

**IMPLICATION:** REQ-04-09-argocd-selfheal's CONFIG step is ALREADY DONE (the my-kluster repo already declares it; the live cluster already reflects it). What is MISSING is the SC#1 dispositive UAT evidence — "a manual `kubectl edit` drift auto-corrects within 3 min". Task 1 captures that evidence; it does NOT need a my-kluster PR.

From STATE.md "Phase 7 deviations + follow-ups" item #14 (CF-07-3 D-07-CRONJOB-CRUFT):
> Two ConfigMaps coexist in `selfhost`: legacy `arrconf` (8d, sonarr-only, 1349B) and current `arrconf-config` (umbrella, 18.8KB). Same for `configarr` vs `configarr-config`. Operator action: `kubectl -n selfhost delete cm arrconf configarr` (Phase 4 cleanup leftover).

From `.planning/phases/11-operational-polish-bundle/11-CONTEXT.md` § Specific Ideas:
- ArgoCD selfHeal UAT snippet: `kubectl scale deployment/sonarr -n selfhost --replicas=2; sleep 180; kubectl -n selfhost get deployment/sonarr -o jsonpath='{.spec.replicas}'` → expected `1` (auto-corrected).
- CM cleanup safety check: `kubectl -n selfhost get pod -o yaml | grep -A2 'configMap:.*arrconf"$'` must be empty (no pod uses the legacy CMs).
- Renovate App install: browser flow at `https://github.com/apps/renovate` → choose `tom333/arr-stack`.

From CLAUDE.md § "Release pin co-bump pattern" (D-05 exception):
> Un commit qui ne modifie que des fichiers `.md`, `values.yaml` (hors arrconf), ou des fichiers hors `tools/arrconf/**` ne doit PAS bumper `arrconf.image.tag`.

This plan's evidence files + SUMMARY.md are under `.planning/phases/.../evidence/` and `.planning/phases/.../11-B-SUMMARY.md` — both docs-only, both confirm the D-05 exception (no `charts/arr-stack/values.yaml` modification).
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: Verify + capture SC#1 dispositive UAT — ArgoCD selfHeal drift auto-revert</name>
  <files>.planning/phases/11-operational-polish-bundle/evidence/argocd-selfheal-uat-&lt;date&gt;.log, snapshots/before-argocd-selfheal-uat-&lt;date&gt;/</files>
  <action>
    The ArgoCD Application `arr-stack` ALREADY has `automated.selfHeal: true` + `automated.prune: true` declared in `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` (confirmed at planning time on 2026-05-21). The live cluster reflects this via `kubectl ... -o jsonpath='{.spec.syncPolicy.automated}'` returning `{"prune":true,"selfHeal":true}`. **No my-kluster PR is required.**

    This task captures dispositive UAT evidence for SC#1 ("a manual `kubectl edit` drift on the live arr-stack chart auto-corrects on next ArgoCD sync") by intentionally drifting a managed deployment and observing auto-correction.

    **STEP 0 — ADR-6 pre-action snapshot** (CLAUDE.md "Workflow snapshot"): before any cluster mutation that could surprise you, capture a baseline.
    ```bash
    tools/snapshot/snapshot.sh --apps sonarr --output snapshots/before-argocd-selfheal-uat-$(date +%F)/
    git add snapshots/before-argocd-selfheal-uat-* && git commit -m "snapshot(11-B-01): pre-UAT baseline before ArgoCD selfHeal drift test"
    ```

    **STEP 1-7 — Drift test, logged to `evidence/argocd-selfheal-uat-$(date +%F).log`:**

    ```bash
    EVIDENCE=".planning/phases/11-operational-polish-bundle/evidence/argocd-selfheal-uat-$(date +%F).log"
    mkdir -p "$(dirname "$EVIDENCE")"

    # 1. Confirm syncPolicy.automated state (should be selfHeal:true + prune:true)
    echo "=== STEP 1: pre-drift syncPolicy.automated ===" | tee -a "$EVIDENCE"
    kubectl -n argocd get application arr-stack -o jsonpath='{.spec.syncPolicy.automated}{"\n"}' | tee -a "$EVIDENCE"

    # 2. Capture pre-drift deployment replicas (should be 1)
    echo "=== STEP 2: pre-drift sonarr replicas ===" | tee -a "$EVIDENCE"
    kubectl -n selfhost get deployment/sonarr -o jsonpath='{.spec.replicas}{"\n"}' | tee -a "$EVIDENCE"

    # 3. Drift: scale sonarr to 2 replicas (manual `kubectl scale` simulates an out-of-band edit)
    echo "=== STEP 3: introducing drift (sonarr scale 1 -> 2) at $(date -Is) ===" | tee -a "$EVIDENCE"
    kubectl scale deployment/sonarr -n selfhost --replicas=2 | tee -a "$EVIDENCE"

    # 4. Confirm drift is observable (immediate read after scale)
    echo "=== STEP 4: drift confirmed ===" | tee -a "$EVIDENCE"
    kubectl -n selfhost get deployment/sonarr -o jsonpath='{.spec.replicas}{"\n"}' | tee -a "$EVIDENCE"  # expected: 2

    # 5. Wait for ArgoCD selfHeal to re-converge (default sync interval ~3min ; selfHeal triggers on drift detection)
    echo "=== STEP 5: waiting 180s for ArgoCD selfHeal ===" | tee -a "$EVIDENCE"
    sleep 180

    # 6. Verify auto-revert
    echo "=== STEP 6: post-wait sonarr replicas at $(date -Is) ===" | tee -a "$EVIDENCE"
    REPLICAS=$(kubectl -n selfhost get deployment/sonarr -o jsonpath='{.spec.replicas}')
    echo "$REPLICAS" | tee -a "$EVIDENCE"

    # 7. Dispositive check
    if [ "$REPLICAS" = "1" ]; then
      echo "=== SC#1 PASS: ArgoCD auto-reverted drift within 3 min ===" | tee -a "$EVIDENCE"
    else
      echo "=== SC#1 FAIL: replicas=$REPLICAS (expected 1) — investigate ArgoCD sync status ===" | tee -a "$EVIDENCE"
      kubectl -n argocd get application arr-stack -o jsonpath='{.status.sync.status}{" "}{.status.health.status}{"\n"}' | tee -a "$EVIDENCE"
    fi

    git add "$EVIDENCE"
    git commit -m "evidence(11-B-01): SC#1 dispositive UAT — ArgoCD selfHeal auto-revert"
    ```

    **If SC#1 FAILS** (replicas still 2 after 180s): do NOT proceed. Investigate ArgoCD sync status and report. Possible causes: ArgoCD application paused / refresh interval misconfigured / cluster auth issue. Re-do the test after diagnosis.

    **No bump to `charts/arr-stack/values.yaml`** — this task does NOT touch `tools/arrconf/**` (D-05 exception per CLAUDE.md).

    **Resume signal:** Operator reports: "SC#1 PASS, evidence committed at &lt;commit-sha&gt;" — OR "SC#1 FAIL with reason ..." (in which case the orchestrator routes to a hotfix scope).
  </action>
  <verify>
    <automated>test -f .planning/phases/11-operational-polish-bundle/evidence/argocd-selfheal-uat-$(date +%F).log && grep -c 'SC#1 PASS' .planning/phases/11-operational-polish-bundle/evidence/argocd-selfheal-uat-$(date +%F).log | grep -q '^[1-9]'</automated>
  </verify>
  <done>
    - Pre-UAT snapshot committed under `snapshots/before-argocd-selfheal-uat-<date>/` (ADR-6 discipline).
    - Evidence file `.planning/phases/11-operational-polish-bundle/evidence/argocd-selfheal-uat-<date>.log` exists and contains the literal string `SC#1 PASS`.
    - Evidence file shows STEP 1 returned `{"prune":true,"selfHeal":true}`, STEP 4 returned `2`, STEP 6 returned `1`.
    - Evidence committed to git.
    - No change to `charts/arr-stack/values.yaml`.
  </done>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 2: Delete legacy ConfigMaps arrconf + configarr from namespace selfhost</name>
  <files>.planning/phases/11-operational-polish-bundle/evidence/cm-cruft-cleanup-&lt;date&gt;.log</files>
  <action>
    Two legacy ConfigMaps remain in `selfhost` namespace as Phase 4 cutover leftovers:
    - `arrconf` (1349 B, sonarr-only, 8 days old at Phase 7 discovery) — pre-umbrella era.
    - `configarr` (9271 B) — pre-umbrella era.

    The current managed CMs are `arrconf-config` (umbrella, 18.8 KB) and `configarr-config`. The legacy pair is NOT mounted by any pod (Phase 4 cutover moved all mounts to the `-config`-suffixed pair) but lingers in the namespace cluttering audits.

    **Operator action:** `kubectl delete` after a safety check confirms no pod references the legacy CMs.

    Capture full evidence to `evidence/cm-cruft-cleanup-$(date +%F).log`:

    ```bash
    EVIDENCE=".planning/phases/11-operational-polish-bundle/evidence/cm-cruft-cleanup-$(date +%F).log"
    mkdir -p "$(dirname "$EVIDENCE")"

    # 1. Pre-cleanup CM inventory in selfhost
    echo "=== STEP 1: pre-cleanup CM inventory ===" | tee -a "$EVIDENCE"
    kubectl -n selfhost get cm | tee -a "$EVIDENCE"

    # 2. Safety check: no pod must reference the legacy CMs (`arrconf` or `configarr` — NOT the -config suffix)
    echo "=== STEP 2: safety check — pod mounts referencing legacy CMs ===" | tee -a "$EVIDENCE"
    MOUNTS=$(kubectl -n selfhost get pod -o yaml | grep -E 'configMap:|name: arrconf$|name: configarr$' | grep -B1 -E 'name: arrconf$|name: configarr$' || true)
    echo "$MOUNTS" | tee -a "$EVIDENCE"
    if [ -n "$MOUNTS" ]; then
      echo "=== SAFETY CHECK FAIL: a pod still mounts legacy arrconf or configarr ConfigMap ===" | tee -a "$EVIDENCE"
      echo "ABORTING delete — investigate which deployment still references the legacy CM and migrate to the -config suffix first." | tee -a "$EVIDENCE"
      exit 1
    fi
    echo "OK: no pod mounts the legacy CMs — safe to delete" | tee -a "$EVIDENCE"

    # 3. Delete the 2 legacy CMs
    echo "=== STEP 3: deleting legacy CMs ===" | tee -a "$EVIDENCE"
    kubectl -n selfhost delete cm arrconf configarr 2>&1 | tee -a "$EVIDENCE"

    # 4. Post-delete CM inventory
    echo "=== STEP 4: post-cleanup CM inventory ===" | tee -a "$EVIDENCE"
    kubectl -n selfhost get cm | tee -a "$EVIDENCE"

    # 5. Dispositive checks
    ABSENT_COUNT=$(kubectl -n selfhost get cm 2>/dev/null | awk '$1 == "arrconf" || $1 == "configarr"' | wc -l)
    PRESENT_COUNT=$(kubectl -n selfhost get cm 2>/dev/null | awk '$1 == "arrconf-config" || $1 == "configarr-config"' | wc -l)
    echo "=== DISPOSITIVE: legacy CM count=$ABSENT_COUNT (expect 0), current CM count=$PRESENT_COUNT (expect 2) ===" | tee -a "$EVIDENCE"

    if [ "$ABSENT_COUNT" = "0" ] && [ "$PRESENT_COUNT" = "2" ]; then
      echo "SC#2 PASS" | tee -a "$EVIDENCE"
    else
      echo "SC#2 FAIL" | tee -a "$EVIDENCE"
    fi

    git add "$EVIDENCE"
    git commit -m "evidence(11-B-02): SC#2 dispositive — legacy CM cleanup (arrconf + configarr)"
    ```

    **Special considerations:**
    - If ArgoCD's `automated.prune: true` (Task 1) has been active for a while, the legacy CMs MIGHT have already been pruned by ArgoCD on a previous sync (they're not declared in the current chart). In that case, STEP 1 will already show them absent and STEP 3's delete will report `NotFound`. That's a non-failure — the SC#2 dispositive (`ABSENT_COUNT=0`) still passes. Document this case in the evidence log with the literal kubectl output.
    - Do NOT delete `arrconf-config` or `configarr-config` (the current umbrella-chart-rendered CMs).

    No bump to `charts/arr-stack/values.yaml` (no `tools/arrconf/**` touched).

    **Resume signal:** Operator reports: "SC#2 PASS, evidence committed at &lt;commit-sha&gt;" — OR notes the "already pruned by ArgoCD" case (still a PASS).
  </action>
  <verify>
    <automated>test -f .planning/phases/11-operational-polish-bundle/evidence/cm-cruft-cleanup-$(date +%F).log && grep -c 'SC#2 PASS' .planning/phases/11-operational-polish-bundle/evidence/cm-cruft-cleanup-$(date +%F).log | grep -q '^[1-9]'</automated>
  </verify>
  <done>
    - Safety check (STEP 2) returned empty mounts (no pod referenced the legacy CMs).
    - STEP 3 reported either successful delete OR "NotFound" (ArgoCD-already-pruned case).
    - STEP 4 inventory shows `arrconf-config` + `configarr-config` present, NO `arrconf` standalone or `configarr` standalone.
    - Evidence file contains `SC#2 PASS`.
    - Evidence committed to git.
    - No change to `charts/arr-stack/values.yaml`.
  </done>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 3: Install Mend Renovate App on github.com/tom333/arr-stack + SC#4 UAT</name>
  <files>.planning/phases/11-operational-polish-bundle/evidence/renovate-app-install-&lt;date&gt;.log</files>
  <action>
    The Mend Renovate App (https://github.com/apps/renovate) provides automated dependency bump PRs. It is currently NOT installed on `tom333/arr-stack` (Renovate has historically run via a self-hosted instance from `my-kluster`'s side per STATE.md "Pre-existing my-kluster state").

    **Operator action:** browse to https://github.com/apps/renovate, click Install, select `tom333/arr-stack` (or "All repositories"), approve the requested permissions.

    **CRITICAL SEQUENCING:** This task's SC#4 UAT ("commit touching only `tools/arrconf/**` triggers auto-tag → Renovate PR on my-kluster") REQUIRES Plan 11-A Task 2 (REQ-paths-filter-arrconf) to be merged on `main` FIRST. Without that paths-filter expansion, a tools/arrconf-only commit will NOT trigger chart-lint.yml's auto-tag chain, breaking the UAT. STEP 4 includes a guard that aborts (with a "deferred" status, not a failure) if 11-A Task 2 is not yet on `origin/main`.

    Capture full evidence to `evidence/renovate-app-install-$(date +%F).log`:

    ```bash
    EVIDENCE=".planning/phases/11-operational-polish-bundle/evidence/renovate-app-install-$(date +%F).log"
    mkdir -p "$(dirname "$EVIDENCE")"

    # STEP 1 — Pre-install check (Renovate should NOT yet be installed on the repo)
    echo "=== STEP 1: pre-install — Renovate app installation status ===" | tee -a "$EVIDENCE"
    # GitHub returns 404 for /repos/.../installation if the Renovate App is not installed; 200 + JSON if it is.
    # The endpoint requires a user token (gh auth) with at least public_repo scope.
    gh api /repos/tom333/arr-stack/installation 2>&1 | tee -a "$EVIDENCE" || true
    echo "(expecting HTTP 404 or 'Not Found' pre-install)" | tee -a "$EVIDENCE"
    ```

    **STEP 2 — Operator browser action (manual, the only truly unavoidable manual step in this plan):**
    1. Open https://github.com/apps/renovate in a browser.
    2. Click **Install** (top-right green button).
    3. On the next page, choose the GitHub account/org that owns `tom333/arr-stack`.
    4. Choose "Only select repositories" → check `tom333/arr-stack` (alternative: "All repositories" if the operator is OK with org-wide Renovate). For SC#4 scope, only `arr-stack` is required.
    5. Review the permissions Renovate requests:
       - Contents: Read & write (open PRs)
       - Issues: Read & write (Dependency Dashboard)
       - Metadata: Read (mandatory)
       - Pull requests: Read & write
       - Workflows: Read & write (update CI YAML)
    6. Click **Install** to confirm.

    Document the install timestamp and the account/org name in the evidence log:
    ```bash
    echo "=== STEP 2: operator install action ===" | tee -a "$EVIDENCE"
    echo "Installed at: $(date -Is)" | tee -a "$EVIDENCE"
    echo "Account/org: <operator-fills-in>" | tee -a "$EVIDENCE"
    echo "Scope: <only-arr-stack OR all-repos>" | tee -a "$EVIDENCE"
    ```

    **STEP 3 — Post-install verification:**
    ```bash
    echo "=== STEP 3: post-install verification ===" | tee -a "$EVIDENCE"
    INSTALL_INFO=$(gh api /repos/tom333/arr-stack/installation 2>&1)
    echo "$INSTALL_INFO" | tee -a "$EVIDENCE"
    APP_SLUG=$(echo "$INSTALL_INFO" | jq -r .app_slug 2>/dev/null || echo "PARSE_ERROR")
    echo "Detected app_slug: $APP_SLUG" | tee -a "$EVIDENCE"
    if [ "$APP_SLUG" = "renovate" ]; then
      echo "Renovate install detected — UAT-stage 1 PASS" | tee -a "$EVIDENCE"
    else
      echo "Renovate install NOT detected — investigate (check gh auth scope, re-run after 60s for cache)" | tee -a "$EVIDENCE"
    fi
    ```

    **STEP 4 — SC#4 dispositive UAT (end-to-end test, depends on 11-A Task 2 being merged):**
    ```bash
    echo "=== STEP 4: SC#4 prereq check — paths-filter merged? ===" | tee -a "$EVIDENCE"
    git fetch origin main
    PATHS_FILTER_PRESENT=$(git show origin/main:.github/workflows/chart-lint.yml 2>/dev/null | grep -c 'tools/arrconf/\*\*' || true)
    echo "paths filter contains tools/arrconf/**: $PATHS_FILTER_PRESENT occurrences (expect >= 2)" | tee -a "$EVIDENCE"
    if [ "$PATHS_FILTER_PRESENT" -lt 2 ]; then
      echo "DEFERRED: Plan 11-A Task 2 not yet merged on origin/main — SC#4 cannot be tested now" | tee -a "$EVIDENCE"
      echo "Re-run STEP 4 after 11-A Task 2 is merged on origin/main." | tee -a "$EVIDENCE"
      echo "SC#4 DEFERRED (not a failure)" | tee -a "$EVIDENCE"
      # Stop STEP 4 here; the SUMMARY documents the deferred state.
    else
      echo "=== STEP 4b: trigger a no-op tools/arrconf/** commit ===" | tee -a "$EVIDENCE"
      # Smallest possible arrconf-only change: bump a docstring or add a comment in __main__.py.
      # (e.g., edit a trailing comment in tools/arrconf/arrconf/__main__.py)
      # IMPORTANT: this WILL trigger D-05 chart-pin co-bump per CLAUDE.md → bump charts/arr-stack/values.yaml#arrconf.image.tag in the SAME commit.
      # Operator picks the next patch tag (e.g., 0.6.6 → 0.6.7).
      echo "Operator triggers arrconf-only commit at $(date -Is) (co-bumped chart-pin per D-05)" | tee -a "$EVIDENCE"
      sleep 60
      LATEST_TAG=$(git ls-remote --tags origin | grep -v '\^{}' | awk '{print $2}' | sort -V | tail -1)
      echo "Latest tag after no-op arrconf commit: $LATEST_TAG" | tee -a "$EVIDENCE"

      echo "=== STEP 4c: wait for Renovate PR on my-kluster (up to 1h) ===" | tee -a "$EVIDENCE"
      # Operator polls https://github.com/tom333/my-kluster/pulls?q=is:pr+author:app/renovate
      # until a PR appears bumping argocd/argocd-apps/arr-stack-app.yaml#targetRevision to $LATEST_TAG.
      echo "Expected: Renovate PR opens within ~1h bumping arr-stack-app.yaml#targetRevision to $LATEST_TAG" | tee -a "$EVIDENCE"
      echo "Captured PR URL: <operator-fills-in once observed>" | tee -a "$EVIDENCE"
      echo "Captured PR open timestamp: <operator-fills-in>" | tee -a "$EVIDENCE"

      echo "=== SC#4 STATUS ===" | tee -a "$EVIDENCE"
      echo "PASS if Renovate PR observed AND PR file = argocd/argocd-apps/arr-stack-app.yaml AND PR bumps targetRevision to $LATEST_TAG" | tee -a "$EVIDENCE"
    fi

    git add "$EVIDENCE"
    git commit -m "evidence(11-B-03): Renovate App install + SC#4 UAT"
    ```

    **Fallback for `gh api` endpoint quirks:** Different GitHub API versions return slightly different shapes. If `jq .app_slug` errors, the operator can fall back to:
    ```bash
    gh api /repos/tom333/arr-stack/installations 2>&1 | grep -c '"slug": "renovate"'  # >=1 = installed
    ```
    Document the fallback used in the evidence log.

    Note: STEP 4b's no-op arrconf commit is a SEPARATE commit from this plan's evidence commit, AND it co-bumps `charts/arr-stack/values.yaml` per D-05 (because it DOES touch `tools/arrconf/**`). That co-bump is documented in the SUMMARY (Task 4) but is NOT counted in THIS plan's "files_modified" frontmatter (which is `[]` for evidence-only).

    **Resume signal:** Operator reports: "Renovate App installed at &lt;timestamp&gt;, evidence committed at &lt;commit-sha&gt;, SC#4 UAT PASS — Renovate PR &lt;PR-URL&gt; opened on my-kluster" — OR notes that SC#4 was deferred because 11-A Task 2 was not yet merged at install time (re-run STEP 4 later, not a failure).
  </action>
  <verify>
    <automated>test -f .planning/phases/11-operational-polish-bundle/evidence/renovate-app-install-$(date +%F).log && grep -cE 'Renovate install detected|SC#4 (PASS|DEFERRED)' .planning/phases/11-operational-polish-bundle/evidence/renovate-app-install-$(date +%F).log | grep -q '^[1-9]'</automated>
  </verify>
  <done>
    - Pre-install STEP 1 returned 404 or "Not Found" for `/installation` endpoint.
    - STEP 2 install action timestamp + account/org + scope recorded in the evidence log.
    - STEP 3 post-install detection returned `app_slug: renovate` (or the fallback check found `"slug": "renovate"`).
    - STEP 4 either: (a) recorded `SC#4 PASS` with a Renovate PR URL on my-kluster bumping targetRevision, OR (b) recorded `SC#4 DEFERRED` because 11-A Task 2 was not yet merged — both states acceptable.
    - Evidence committed to git.
    - No change to `charts/arr-stack/values.yaml` in THIS plan's commits (STEP 4b's arrconf-only commit is a SEPARATE commit with its own co-bump, documented in the SUMMARY).
  </done>
</task>

<task type="auto">
  <name>Task 4: Plan 11-B SUMMARY</name>
  <files>.planning/phases/11-operational-polish-bundle/11-B-SUMMARY.md</files>
  <action>
    Write `.planning/phases/11-operational-polish-bundle/11-B-SUMMARY.md` following the standard summary template (read `$HOME/.claude/get-shit-done/templates/summary.md` first ; reference `.planning/phases/10-categories-6-app-propagation/10-J-SUMMARY.md` for format). Capture:

    - **Requirements closed** (3): REQ-04-09-argocd-selfheal, REQ-cm-cruft-cleanup, REQ-renovate-app-install
    - **Files modified in arr-stack repo** (0 source files): only 3 evidence `.log` files under `.planning/phases/11-operational-polish-bundle/evidence/` + this SUMMARY. NO `charts/`, NO `tools/`, NO `.github/`.
    - **Files modified in my-kluster repo** (0): the `arr-stack-app.yaml` was ALREADY in the desired state (`selfHeal: true` + `prune: true` declared since pre-Phase 11 — confirmed against `main` on 2026-05-21). No PR needed for REQ-04-09; the work was UAT capture only.
    - **Live cluster mutations** (operator actions, not committed to repo):
      - `kubectl scale deployment/sonarr --replicas=2` → auto-reverted by ArgoCD (Task 1 evidence)
      - `kubectl -n selfhost delete cm arrconf configarr` → 2 legacy CMs removed (Task 2 evidence) — OR documented as "already pruned by ArgoCD" if applicable
      - GitHub App install (Renovate) → applied to `tom333/arr-stack` via browser UI (Task 3 evidence)
    - **Operator action timestamps** (extract from evidence logs):
      - Task 1 SC#1 PASS timestamp + sonarr replicas at T0 + T180s
      - Task 2 delete timestamp + pre/post CM inventory
      - Task 3 Renovate install timestamp + my-kluster PR URL (if SC#4 not DEFERRED)
    - **Acceptance criteria status** per task (3 checkmarks; SC#4 may be DEFERRED — that's not a failure).
    - **Deviations**:
      - REQ-04-09-argocd-selfheal: planner expected a my-kluster PR; YAML was already correct. Task pivoted to UAT-only.
      - Task 3 SC#4 may be marked DEFERRED if 11-A Task 2 was not yet on main at install time.
    - **Chart-pin co-bump audit**: explicit `git diff --stat charts/arr-stack/values.yaml` against pre-plan tree — must be empty for THIS plan's commits. Task 3 STEP 4b's separate arrconf-only commit (if executed) IS allowed to co-bump the chart-pin per D-05; that commit is documented HERE but is a SEPARATE git commit from this plan's evidence commits, AND it has its own tag (e.g., 0.6.7).
    - **Carry-forward**: nothing new.

    ALWAYS use the Write tool to create the file (never `cat << EOF`).
  </action>
  <verify>
    <automated>test -f .planning/phases/11-operational-polish-bundle/11-B-SUMMARY.md && grep -cE 'REQ-04-09-argocd-selfheal|REQ-cm-cruft-cleanup|REQ-renovate-app-install' .planning/phases/11-operational-polish-bundle/11-B-SUMMARY.md | grep -q '^[3-9]$\|^[1-9][0-9]'</automated>
  </verify>
  <done>
    - `11-B-SUMMARY.md` exists.
    - All 3 REQ IDs mentioned at least once.
    - Each task's evidence file path is referenced.
    - Operator-action timestamps recorded (filled in by the executor from the evidence logs).
    - D-05 chart-pin co-bump audit explicit: no `values.yaml` change in THIS plan's commits; if Task 3 STEP 4b executed an arrconf-only commit, that's a separate commit with its own co-bump (documented but not part of this plan's files_modified).
    - Pivot deviation documented (REQ-04-09 was config-already-applied → UAT-only).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| operator workstation → live cluster | `kubectl scale` and `kubectl delete cm` mutate live cluster state; auth via kubeconfig |
| operator browser → GitHub App install flow | Renovate App receives Contents/Issues/PR/Workflows write permission on `tom333/arr-stack` |
| Renovate App → my-kluster repo | post-install, Renovate opens PRs that mutate ArgoCD-tracked YAMLs in my-kluster |
| ArgoCD auto-prune → cluster resources | with `prune: true`, ArgoCD will delete resources not declared in the chart (potential blast radius if a chart edit accidentally drops a resource) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-11-B-01 | Tampering | ArgoCD `automated.selfHeal` reverts manual emergency fixes | accept | Documented in ArgoCD ops practice — emergency `kubectl edit` during an outage will be reverted on next sync (default ~3 min). For true emergencies, suspend ArgoCD app first (`argocd app set arr-stack --sync-policy none`) before mutating. CLAUDE.md should note this but does not currently — defer to v0.4.0+ doc update. |
| T-11-B-02 | Denial of Service | `automated.prune: true` deletes resources not in chart | mitigate | The Phase 10 closeout verified all 80+ chart resources match the cluster inventory (see 10-VERIFICATION.md). Future chart edits that accidentally drop a resource will trigger a delete on next sync; mitigated by the chart-lint.yml `helm template` step that flags resource count regressions. Operator-side mitigation: monitor ArgoCD UI's "Resources" tab for unexpected delete-pending states. |
| T-11-B-03 | Elevation of Privilege | Renovate App requests Contents:write + Workflows:write | mitigate | Permissions match standard Renovate scope; Mend is a well-known SaaS with SOC2 attestations. Repo scope is narrowed to `tom333/arr-stack` only (not org-wide). Risk acceptance documented in evidence log STEP 2. |
| T-11-B-04 | Information Disclosure | `gh api /installation` requires a user token with `public_repo` scope | accept | The operator's `gh auth login` token is local to their workstation; evidence logs do NOT contain the token (the gh CLI reads it from `~/.config/gh/`). Token rotation is operator's normal hygiene. |
| T-11-B-05 | Tampering | `kubectl delete cm arrconf configarr` — irrecoverable if mis-targeted | mitigate | Safety check in Task 2 STEP 2 (`grep` for legacy CM names exactly, not the `-config` suffix) prevents accidental delete of the live CMs. If a mis-delete happens, ArgoCD selfHeal (Task 1) will re-create the umbrella `-config` CMs from chart sources within 3 min. The legacy CMs themselves cannot be re-created (they are not in any chart) — but they're cruft, so loss is acceptable. |
| T-11-B-06 | Repudiation | Operator-action timestamps in evidence logs | mitigate | All 3 evidence logs include `$(date -Is)` timestamps captured by the script. Logs are committed to git, providing a tamper-evident audit trail. |
</threat_model>

<verification>
- All 3 operator-action evidence files exist under `.planning/phases/11-operational-polish-bundle/evidence/` and are committed.
- `kubectl -n argocd get application arr-stack -o jsonpath='{.spec.syncPolicy.automated}'` returns `{"prune":true,"selfHeal":true}`.
- `kubectl -n selfhost get cm` lists `arrconf-config` and `configarr-config` but NOT standalone `arrconf` nor `configarr`.
- `gh api /repos/tom333/arr-stack/installation` returns a JSON object with `app_slug: renovate` (post-install state).
- `git diff --stat charts/arr-stack/values.yaml` against the pre-plan tree returns empty for THIS plan's commits.
</verification>

<success_criteria>
1. **SC#1** (REQ-04-09-argocd-selfheal): `kubectl scale deployment/sonarr -n selfhost --replicas=2` → wait 180s → `kubectl -n selfhost get deployment/sonarr -o jsonpath='{.spec.replicas}'` returns `1` (auto-reverted). Evidence in `evidence/argocd-selfheal-uat-<date>.log`.
2. **SC#2** (REQ-cm-cruft-cleanup): `kubectl -n selfhost get cm 2>&1 | awk '$1 == "arrconf" || $1 == "configarr"' | wc -l` returns `0`. Evidence in `evidence/cm-cruft-cleanup-<date>.log`.
3. **SC#4** (REQ-renovate-app-install): `gh api /repos/tom333/arr-stack/installation | jq -r .app_slug` returns `"renovate"`. SC#4 end-to-end UAT may be PASS (Renovate PR observed on my-kluster) OR DEFERRED (11-A Task 2 not yet merged) — both acceptable. Evidence in `evidence/renovate-app-install-<date>.log`.
4. `11-B-SUMMARY.md` exists and references all 3 REQ IDs + 3 evidence files.
5. No `charts/arr-stack/values.yaml` modification in THIS plan's commits (D-05 audit).
</success_criteria>

<output>
After completion, create `.planning/phases/11-operational-polish-bundle/11-B-SUMMARY.md` (Task 4 produces this).
</output>
