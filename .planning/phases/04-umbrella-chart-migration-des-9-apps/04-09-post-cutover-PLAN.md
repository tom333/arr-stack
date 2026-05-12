---
phase: 04-umbrella-chart-migration-des-9-apps
plan: 09
type: execute
wave: 7  # W1 ripple — Plan 08 moved from wave 7 → 6 (parallel-merge of 06 + 07 at wave 5).
depends_on: ["04-08"]
cross_repo: true  # B2-consistent — same pattern as Plan 08.
files_modified:
  - .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/renovate-sc2-evidence.md
  - /home/moi/projets/perso/my-kluster/argocd/argocd-apps/arr-stack-app.yaml  # CROSS-REPO modify (re-enable automated:)
autonomous: false
requirements:
  - REQ-umbrella-deployment
  - REQ-pr-to-cluster-latency
  - REQ-renovate-image-tracking
tags: [post-cutover, argocd, renovate, follow-up]
must_haves:
  truths:
    - "A follow-up 1-line PR in my-kluster re-enables `automated.{selfHeal,prune}` on `arr-stack-app.yaml`"
    - "After the follow-up PR merge, `argocd app get arr-stack` reports `Synced + Healthy` AND `.spec.syncPolicy.automated.selfHeal: true`"
    - "REQ-pr-to-cluster-latency / SC#2 is satisfied within 72 hours of cutover: either by a natural Renovate bump observed within 48 h (auto-merges per packageRules → CI auto-tag → my-kluster Renovate scan) OR by D-04-PIN-04 Path B forced downgrade executed IMMEDIATELY at T+48 h post-cutover."
    - "SC#2 evidence captured in evidence/renovate-sc2-evidence.md: PR URL + arr-stack tag (CI auto-tag URL per B3 Path A) → my-kluster targetRevision PR URL → ArgoCD sync timestamp → cluster reconcile delta < 1 h"
    - "Phase 4 reaches a definitive SC#2 verdict (PASS or documented FAIL) within 72 hours of cutover, regardless of natural Renovate cadence (B4 hard decision gate)."
  artifacts:
    - path: ".planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/renovate-sc2-evidence.md"
      provides: "End-to-end timeline proving REQ-pr-to-cluster-latency (Renovate → arr-stack release → my-kluster bump PR → ArgoCD sync < 1h)"
  key_links:
    - from: "my-kluster/argocd/argocd-apps/arr-stack-app.yaml"
      to: "ArgoCD controller"
      via: "automated.selfHeal: true reactivates drift correction"
      pattern: "automated:"
    - from: "Renovate PR on arr-stack repo"
      to: "Renovate PR on my-kluster (targetRevision bump)"
      via: "End-to-end chain documented in evidence/renovate-sc2-evidence.md"
      pattern: "targetRevision"
---

<objective>
Close Phase 4: re-enable ArgoCD automation on `arr-stack-app.yaml` (D-04-CUTOVER-02 follow-up) and capture SC#2 E2E evidence (REQ-pr-to-cluster-latency / D-04-PIN-04).

Purpose: Until automation is re-enabled, the cluster cannot self-heal drift. SC#2 (`PR → release tag → Renovate PR my-kluster → ArgoCD sync < 1h`) is the dispositive E2E test for both REQ-pr-to-cluster-latency AND REQ-renovate-image-tracking — it proves the customManagers regex actually works against the live Renovate bot.

Output: A merged follow-up PR in my-kluster + an evidence file documenting the SC#2 timeline.
</objective>

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
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-VALIDATION.md
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-08-cutover-SUMMARY.md

<interfaces>
<!-- 1-line follow-up PR — add this block back into arr-stack-app.yaml -->

  syncPolicy:
    syncOptions:
      - CreateNamespace=false
      - ServerSideApply=true
    automated:                     # <-- re-add this block (D-04-CUTOVER-02 follow-up)
      selfHeal: true               # <--
      prune: true                  # <--

<!-- SC#2 evidence shape — REQ-pr-to-cluster-latency timeline -->
Tn — n event
T0  — A Renovate PR on arr-stack repo opens (or operator forces one per D-04-PIN-04)
T1  — chart-lint CI passes; Renovate auto-merges (minor/patch packageRule)
T2  — operator (or Renovate) cuts a release tag (or Renovate detects the merge and proposes a my-kluster bump)
T3  — Renovate PR on my-kluster opens for targetRevision: <new tag>
T4  — my-kluster PR auto-merges (or operator merges)
T5  — ArgoCD detects new revision and syncs arr-stack
T6  — arr-stack app reports Synced + Healthy with the new tag

REQ-pr-to-cluster-latency target: T6 - T0 < 1 hour.
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 9.1: Open follow-up PR in my-kluster re-enabling automated.{selfHeal,prune}</name>
  <files>(cross-repo: my-kluster — 1-line edit to arr-stack-app.yaml)</files>
  <read_first>
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-08-cutover-SUMMARY.md (confirm arr-stack is Synced + Healthy at the end of Plan 08 before re-enabling automation)
    /home/moi/projets/perso/my-kluster/argocd/argocd-apps/arr-stack-app.yaml (the file created in Plan 08 — confirm it currently has NO `automated:` block)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-CONTEXT.md (D-04-CUTOVER-02 — "Re-enables `automated.{selfHeal,prune}` in a follow-up one-line PR")
  </read_first>
  <what-built>
    Nothing yet — operator opens a 1-line follow-up PR.
  </what-built>
  <how-to-verify>
    OPERATOR steps in my-kluster:

    ```bash
    cd /home/moi/projets/perso/my-kluster
    git fetch origin
    git checkout -b arr-stack-enable-automated origin/main

    # Verify the current state: arr-stack-app.yaml MUST NOT have automated: yet.
    grep -c '^    automated:' argocd/argocd-apps/arr-stack-app.yaml   # must be 0

    # Append the automated: block at the end of syncPolicy.
    # The exact YAML insertion (preserving spec.syncPolicy.syncOptions intact):
    ```

    Use an editor (or a precise `sed`) to insert these 3 lines AT THE END of the `syncPolicy:` block (under `- ServerSideApply=true`):
    ```yaml
        automated:
          selfHeal: true
          prune: true
    ```

    The full `syncPolicy:` block must end up like:
    ```yaml
      syncPolicy:
        syncOptions:
          - CreateNamespace=false
          - ServerSideApply=true
        automated:
          selfHeal: true
          prune: true
    ```

    Sanity check the YAML still parses:
    ```bash
    python3 -c "import yaml; print(yaml.safe_load(open('argocd/argocd-apps/arr-stack-app.yaml'))['spec']['syncPolicy'])"
    # Expected output should include {'automated': {'prune': True, 'selfHeal': True}, ...}
    ```

    Commit + push + open PR:
    ```bash
    git add argocd/argocd-apps/arr-stack-app.yaml
    git commit -m "feat(arr-stack): re-enable automated.{selfHeal,prune} (D-04-CUTOVER-02 follow-up)

    Phase 4 cutover (D-04-CUTOVER-02) shipped the arr-stack Application without
    automated: so the operator could drive the first sync manually. Manual sync
    succeeded (.planning/phases/04-*/04-08-cutover-SUMMARY.md in arr-stack repo).
    Re-enabling automation now."

    git push origin arr-stack-enable-automated
    gh pr create --title "feat(arr-stack): re-enable automated.{selfHeal,prune}" --body "1-line follow-up per D-04-CUTOVER-02. arr-stack app is currently Synced+Healthy from manual sync."
    ```

    Merge the PR. Then verify ArgoCD picks up the change (no resource changes expected — only the Application spec):
    ```bash
    # Wait ~30s, then:
    argocd app get arr-stack -o yaml | grep -A 3 syncPolicy
    # Expected: automated: { selfHeal: true, prune: true } block present.

    # Fallback (no argocd CLI):
    kubectl get application arr-stack -n argocd -o jsonpath='{.spec.syncPolicy.automated}'
    # Expected: {"prune":true,"selfHeal":true}
    ```

    Then type `automated-reenabled <PR-URL>`.
  </how-to-verify>
  <acceptance_criteria>
    - my-kluster PR merged: 1-line addition of `automated: { selfHeal: true, prune: true }` to `arr-stack-app.yaml`.
    - ArgoCD picks up the change: `kubectl get application arr-stack -n argocd -o jsonpath='{.spec.syncPolicy.automated.selfHeal}'` returns `true`.
    - `kubectl get application arr-stack -n argocd -o jsonpath='{.spec.syncPolicy.automated.prune}'` returns `true`.
    - `arr-stack` app remains Synced + Healthy.
  </acceptance_criteria>
  <resume-signal>Type "automated-reenabled &lt;PR-URL&gt;".</resume-signal>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 9.2: Wait for OR force a Renovate-driven E2E bump and record the SC#2 timeline</name>
  <files>.planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/renovate-sc2-evidence.md</files>
  <read_first>
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-CONTEXT.md §D-04-PIN-04 (1-week wait OR force a downgrade)
    .planning/REQUIREMENTS.md §REQ-pr-to-cluster-latency
    renovate.json (customManagers + packageRules — verify against the merged file)
  </read_first>
  <what-built>
    A wait-and-observe pattern: Renovate runs on a schedule (default: at least hourly for cloud-hosted; check Renovate Dashboard). The bot scans the merged renovate.json, walks values.yaml, and proposes bump PRs.
  </what-built>
  <how-to-verify>
    **BOUNDED 72-HOUR DECISION GATE (B4).** This task does NOT wait open-endedly for Renovate. It has THREE hard milestones:

    | Milestone | T+ post-cutover | Action |
    |---|---|---|
    | M1 | 0–48 h | Watch for natural Renovate bump |
    | M2 | T+48 h sharp | If no natural Renovate PR on arr-stack: EXECUTE Path B (forced downgrade) IMMEDIATELY — do NOT extend the wait |
    | M3 | T+72 h sharp | SC#2 verdict MUST be captured in evidence/renovate-sc2-evidence.md (PASS or documented FAIL). Phase 4 cannot remain open past M3. |

    **B3 Path A timeline (collapsed T1→T2)**: thanks to the `auto-tag` job added to `.github/workflows/chart-lint.yml` in Plan 06, the previous manual T2 step (operator cuts release tag) collapses to near-zero. After Renovate auto-merges the arr-stack PR (T1), CI's `auto-tag` job runs on the post-merge push to `main` and immediately publishes a patch tag matching `^v[0-9]+\.[0-9]+\.[0-9]+$`. T2 ≈ T1 + CI duration (≈ 2–5 min). The bottleneck now shifts to my-kluster's Renovate scan cycle (default ≈ 1 h for cloud-hosted Renovate).

    **Path A — wait for a natural bump (M1: 0–48 h window).**

    Monitor the arr-stack PR feed. Look for an open PR with title matching the Renovate convention `Update <image> to <version>` (e.g. "Update lscr.io/linuxserver/sonarr to 4.0.18"). When one arrives:

    ```bash
    # Capture T0 timestamp (PR open time):
    gh -R tom333/arr-stack pr list --search 'author:app/renovate' --json number,title,createdAt
    ```

    Timeline (with B3 Path A auto-tag):
    1. T0 — arr-stack Renovate PR opens.
    2. T1 — `chart-lint.yml` lint job green → Renovate auto-merges per packageRules (minor/patch).
    3. T2 — CI `auto-tag` job runs on push-to-main, publishes vX.Y.Z+1 tag (T2 ≈ T1 + 2-5 min — NO operator action).
    4. T3 — my-kluster Renovate scan detects new tag, opens PR bumping `arr-stack-app.yaml` targetRevision (≤ 1 h after T2 with default scan cadence).
    5. T4 — my-kluster PR merged (auto-merge if configured on my-kluster side; verify with /home/moi/projets/perso/my-kluster/CLAUDE.md).
    6. T5 — ArgoCD detects new revision and starts sync (selfHeal: true is on after Task 9.1).
    7. T6 — `argocd app get arr-stack` reports Synced + Healthy at the new revision.

    Target: T6 - T0 < 1 h.

    **Path B — force the bump (HARD GATE at T+48 h, NOT a 1-week soft wait).**

    At exactly T+48 h post-cutover, run this check:

    ```bash
    # Hard gate decision script
    CUTOVER_TS=$(date -d "$(grep '^cutover:' .planning/phases/04-*/04-08-cutover-SUMMARY.md | head -1 | awk '{print $2}')" +%s 2>/dev/null || echo 0)
    NOW=$(date +%s)
    HOURS=$(( (NOW - CUTOVER_TS) / 3600 ))
    NATURAL_PR=$(gh -R tom333/arr-stack pr list --search 'author:app/renovate' --state all --json number --jq 'length')
    echo "Hours since cutover: $HOURS"
    echo "Renovate PRs opened so far: $NATURAL_PR"
    if [[ $HOURS -ge 48 && $NATURAL_PR -eq 0 ]]; then
      echo "GATE TRIPPED — execute Path B forced downgrade NOW. Do not wait further."
    fi
    ```

    If the gate trips, IMMEDIATELY execute Path B (no further delay):

    ```bash
    cd /home/moi/projets/perso/arr-stack
    git checkout -b force-renovate-trigger
    # Edit charts/arr-stack/values.yaml: cleanuparr tag "2.3.3" → "2.3.2" (or whatever the current pinned value is — downgrade by one patch)
    git commit -am "chore(04): force Renovate E2E test — downgrade cleanuparr by one patch (D-04-PIN-04 Path B at T+48h)"
    git push origin force-renovate-trigger
    gh pr create --title "chore(04): force Renovate E2E test (B4 hard gate)" --body "B4 — 48h hard decision gate tripped (no natural bump). Downgrade cleanuparr by one patch to verify Renovate detects + auto-bumps within 1 h. SC#2 evidence MUST be captured by T+72h regardless of outcome."
    # Merge.
    # Then capture T0 from Renovate's reactive bump PR (usually opens within 1-2 scan cycles).
    ```

    Renovate cloud-hosted typically scans within ≤ 1 h. T0 (reactive Renovate PR) should arrive between T+48h and T+50h. From there, the rest of the Path A timeline applies.

    **M3 hard deadline at T+72 h**: by 72 hours post-cutover, the evidence file MUST exist with either:
    - A complete PASS timeline (natural or forced), OR
    - A complete FAIL timeline with explicit bottleneck analysis. Bottleneck candidates to evaluate: my-kluster Renovate scan cadence > 1 h, ArgoCD polling interval, manual merge friction on the my-kluster PR, or a regex/customManagers configuration defect (cross-check with the W4 regex test result captured in Plan 06 SUMMARY).

    The phase CANNOT remain open past M3. If FAIL is captured, the SUMMARY proceeds with the FAIL verdict — fixing the underlying gap is a follow-up phase, NOT a blocker for Phase 4 closure.

    **Step — write evidence file** (regardless of path A or B):

    Create `.planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/renovate-sc2-evidence.md` with this structure:

    ```markdown
    # Renovate SC#2 E2E evidence

    **Captured:** <YYYY-MM-DD>
    **Path:** A (natural bump) | B (forced via D-04-PIN-04 fallback)

    | Stage | Timestamp (UTC) | Reference |
    |---|---|---|
    | T0 — arr-stack Renovate PR opens | <ISO8601> | <PR URL> |
    | T1 — chart-lint CI green + Renovate auto-merges | <ISO8601> | <CI run URL> + <merge commit SHA> |
    | T2 — release tag cut on arr-stack | <ISO8601> | <tag name + git URL> |
    | T3 — my-kluster Renovate PR opens (targetRevision bump) | <ISO8601> | <PR URL> |
    | T4 — my-kluster PR merged | <ISO8601> | <merge commit SHA> |
    | T5 — ArgoCD detects new revision and starts sync | <ISO8601> | argocd app history arr-stack |
    | T6 — arr-stack reports Synced + Healthy at new revision | <ISO8601> | argocd app get arr-stack |

    **Total: T6 - T0 = <duration>**

    **REQ-pr-to-cluster-latency target: < 1 h**
    **Result: PASS | FAIL**

    ## Notes
    - <any anomalies, e.g. CI flake, manual merge instead of auto-merge, ArgoCD sync delay>
    ```

    Commit:
    ```bash
    cd /home/moi/projets/perso/arr-stack
    git add .planning/phases/04-umbrella-chart-migration-des-9-apps/evidence/renovate-sc2-evidence.md
    git commit -m "docs(04): SC#2 REQ-pr-to-cluster-latency E2E evidence"
    git push
    ```

    Then type `sc2-evidence-captured <result>` where result is PASS or FAIL.
  </how-to-verify>
  <acceptance_criteria>
    - `evidence/renovate-sc2-evidence.md` exists and is committed.
    - All 7 timeline rows (T0-T6) are populated with timestamps and references (URLs or SHAs).
    - The duration `T6 - T0` is computed and the PASS/FAIL verdict against the < 1h target is stated.
    - **B4 hard-gate compliance**: the evidence file contains EITHER (a) a captured natural-bump timeline (Path A) where T0 happened within 0–48 h post-cutover, OR (b) a captured forced-bump timeline (Path B) where T0 happened between 48 h and 72 h post-cutover. ZERO open-ended waits beyond M3 (T+72h).
    - **B3 ripple**: T2 (release tag) reference points at a CI `auto-tag` job run URL (per Plan 06 B3 Path A), not at an operator-cut tag. If the operator cut the tag manually for any reason (CI failure, force-tag, etc.), the SUMMARY documents WHY auto-tag did not fire.
    - If FAIL: the SUMMARY analyzes the bottleneck. Candidates: my-kluster Renovate scan cadence > 1 h (verify in my-kluster Renovate Dashboard); ArgoCD polling interval; customManagers regex defect (cross-check Plan 06 W4 test result); manual merge friction on my-kluster PR.
  </acceptance_criteria>
  <resume-signal>Type "sc2-evidence-captured PASS" or "sc2-evidence-captured FAIL: &lt;duration&gt; — &lt;analysis&gt;".</resume-signal>
</task>

</tasks>

<verification>
- my-kluster PR re-enabling automated merged; ArgoCD reports `automated.selfHeal: true` AND `automated.prune: true`.
- `evidence/renovate-sc2-evidence.md` exists with all 7 timeline rows.
- arr-stack app stays Synced + Healthy.
</verification>

<success_criteria>
SC#2 of REQ-pr-to-cluster-latency demonstrated end-to-end (PASS or FAIL with documented analysis). REQ-renovate-image-tracking proven via the Renovate bot's actual bump PR. Phase 4 is complete — ROADMAP can mark it `[x]`.
</success_criteria>

<output>
After completion, create `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-09-post-cutover-SUMMARY.md` AND update STATE.md (`progress.completed_phases`, `current_focus`, last_activity) + ROADMAP.md (mark Phase 4 `[x]`).
</output>
