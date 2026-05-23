---
phase: 12-categories-deprecation
plan: E
type: execute
wave: 4
depends_on: [A, B, C, D]
files_modified:
  - snapshots/after-phase-12-YYYY-MM-DD/
  - .planning/phases/12-categories-deprecation/12-HUMAN-UAT.md
  - .planning/phases/12-categories-deprecation/12-VERIFICATION.md
autonomous: false
requirements:
  - REQ-categories-deprecation
mode: standard

must_haves:
  truths:
    - "Post-merge snapshot captured against live cluster: `snapshots/after-phase-12-YYYY-MM-DD/` (D-14, D-16, ADR-6)"
    - "Plan E's `dry-run-plan-actions-v040.log` is captured against image `:0.7.0` (post-merge); Plan D's `dry-run-plan-actions-v030.log` was captured against image `:0.6.7` (pre-merge) — the two logs are a true v030-vs-v040 measurement, not a same-code self-diff"
    - "`diff -r snapshots/before-phase-12-* snapshots/after-phase-12-*` shows ONLY structural diffs (e.g. removed merge_decision log lines)"
    - "ZERO `plan_action` differences between before and after snapshots (SC#5 dispositive)"
    - "PR2 is evidence-only: no code, no chart, no values changes; image stays on 0.7.0 (D-16, D-18)"
    - "12-VERIFICATION.md status = PASSED (D-17 requires both SC#3 and SC#5; SC#3 is Plan C, SC#5 is this plan)"
  artifacts:
    - path: "snapshots/after-phase-12-YYYY-MM-DD/"
      provides: "Post-merge cluster API state baseline + `dry-run-plan-actions-v040.log` captured from new code path"
    - path: ".planning/phases/12-categories-deprecation/12-HUMAN-UAT.md"
      provides: "SC#5 operator-driven UAT record"
    - path: ".planning/phases/12-categories-deprecation/12-VERIFICATION.md"
      provides: "Phase 12 final verification status"
  key_links:
    - from: "snapshots/before-phase-12-*/dry-run-plan-actions-v030.log (Plan D)"
      to: "snapshots/after-phase-12-*/dry-run-plan-actions-v040.log (this plan)"
      via: "diff"
      pattern: "plan_action"
    - from: "12-VERIFICATION.md"
      to: "ROADMAP.md Phase 12 checkbox"
      via: "manual status update"
      pattern: "Phase 12.*\\[x\\]"
---

<note>

**Autonomous contract:**

Plan-level `autonomous: false` denotes that the plan as a whole cannot complete without operator action — Task E.1's snapshot capture, diff inspection, and PR2 opening all require live cluster access + human judgment on what constitutes "acceptable noise" in the diff.

Task E.1 is `type="checkpoint:human-action"`, gate="blocking". There are no `type="auto"` tasks in this plan; the executor pauses immediately at E.1 and waits for the operator.

</note>

<objective>
SC#5 dispositive — the live-cluster confirmation that Plan A+B's refactor produced ZERO behavioral drift. After the phase PR merges and ArgoCD picks up image `:0.7.0`, the operator runs `arrconf apply --dry-run` against the production cluster from the post-merge working tree, captures the post-merge snapshot, and diffs it against Plan D's before-snapshot (captured pre-merge from the v0.3.0 working tree against the v0.3.0 cluster). The diff must show only structural noise (removed `merge_decision` log events) and zero `plan_action` differences. Because the two logs come from different code versions running against the cluster at different image states, the diff is a TRUE v030-vs-v040 measurement, not a tautological same-code self-diff.

Purpose: SC#3 (Plan C's `test_sweep`) is the cheap in-CI dispositive. SC#5 is the dispositive against real cluster state with cross-version comparison. D-17 requires BOTH for VERIFICATION PASSED.

Output: 1 new snapshot directory + 1 HUMAN-UAT.md + 1 VERIFICATION.md. Per D-16, this work lands as evidence-only PR2 (no code, no chart, no values changes).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/12-categories-deprecation/12-CONTEXT.md
@CLAUDE.md
@tools/snapshot/snapshot.sh
@.planning/phases/12-categories-deprecation/12-A-reconciler-refactor-SUMMARY.md
@.planning/phases/12-categories-deprecation/12-B-pydantic-yaml-schema-SUMMARY.md
@.planning/phases/12-categories-deprecation/12-C-test-cleanup-SUMMARY.md
@.planning/phases/12-categories-deprecation/12-D-docs-snapshot-SUMMARY.md

<interfaces>
<!-- 12-HUMAN-UAT.md template -->

```markdown
---
phase: 12-categories-deprecation
type: HUMAN-UAT
scenarios: 3
status: <pending|in_progress|passed|failed>
captured: YYYY-MM-DD
---

# Phase 12 HUMAN-UAT — SC#5 live-cluster dispositive

## Scenario 1 — PR1 merge + ArgoCD picks up image 0.7.0

**Pre-conditions:**
- Phase 12 PR (containing Plan A+B+C+D) is merged to main
- Auto-tag workflow created `v0.7.0` tag (or operator pushed it manually per CLAUDE.md "Accumulated-bumps escape hatch")
- GHCR image `ghcr.io/tom333/arr-stack-arrconf:0.7.0` is anonymously pullable
- my-kluster Renovate has opened the `targetRevision: v0.7.0` PR
- Operator has merged the my-kluster Renovate PR
- ArgoCD has synced and is `Synced + Healthy`

**Verification commands:**
```bash
kubectl -n selfhost get cronjob arrconf -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}'
# Expected: ghcr.io/tom333/arr-stack-arrconf:0.7.0

kubectl -n argocd get application arr-stack -o jsonpath='{.status.sync.status} {.status.health.status}'
# Expected: Synced Healthy
```

**Status:** [ ] passed / [ ] failed: <details>

## Scenario 2 — Post-merge snapshot + dry-run capture (v0.4.0 working tree)

**Pre-conditions:** Scenario 1 passed. Operator is on the post-merge `main` working tree (image-tag `:0.7.0`, arrconf code = v0.4.0).

**Commands:**
```bash
# Set up port-forwards + secrets (mirror Plan D Task D.2 steps 3-4)
DATE=$(date +%F)
tools/snapshot/snapshot.sh --output snapshots/after-phase-12-${DATE}/

# Confirm redaction
grep -rniE "(api[-_]?key|password|passkey|token).*:.*[a-z0-9]{16,}" snapshots/after-phase-12-${DATE}/ || echo "REDACTION CLEAN"

# Capture dry-run log against new code (note the -v040 suffix — paired with Plan D's -v030 log)
cd tools/arrconf && uv run arrconf apply \
  --config ../../charts/arr-stack/files/arrconf.yml --dry-run \
  > ../../snapshots/after-phase-12-${DATE}/dry-run-plan-actions-v040.log 2>&1

# Force the in-cluster CronJob to do a dry-run too (extra confidence)
kubectl -n selfhost create job --from=cronjob/arrconf arrconf-phase12-uat-${DATE}
kubectl -n selfhost logs job/arrconf-phase12-uat-${DATE} > snapshots/after-phase-12-${DATE}/cluster-cronjob-log.txt
```

**Status:** [ ] passed / [ ] failed: <details>

## Scenario 3 — SC#5 DISPOSITIVE diff (v030 vs v040)

**Pre-conditions:** Scenarios 1-2 passed; `snapshots/before-phase-12-*` (from Plan D, captured against v0.3.0 cluster from v0.3.0 working tree) and `snapshots/after-phase-12-*` (from Scenario 2, captured against v0.4.0 cluster from v0.4.0 working tree) both committed locally.

**Commands:**
```bash
BEFORE=$(ls -d snapshots/before-phase-12-* | tail -1)
AFTER=$(ls -d snapshots/after-phase-12-* | tail -1)

# Full diff of the raw cluster-API JSON files (the dispositive proof
# that the cluster state under v0.4.0 matches v0.3.0 — these JSON files
# are produced by snapshot.sh which is GET-only and version-independent):
diff -r "$BEFORE" "$AFTER" --exclude='dry-run-plan-actions-*.log' --exclude='cluster-cronjob-log.txt' \
  > snapshots/phase-12-cluster-api-diff.diff 2>&1 || true

# Cross-version dry-run plan-action log comparison (the v030 vs v040 measurement):
diff "$BEFORE/dry-run-plan-actions-v030.log" "$AFTER/dry-run-plan-actions-v040.log" \
  > snapshots/phase-12-cross-version-plan-actions.diff 2>&1 || true

# Filter to plan_action lines only
grep -E "^[<>].*plan_action" snapshots/phase-12-cross-version-plan-actions.diff || \
  echo "ZERO plan_action diffs — SC#5 PASSED"
```

**Acceptance:**
- `snapshots/phase-12-cluster-api-diff.diff` (raw cluster-API JSON state) MUST show only benign drift — timestamps, `freeSpace`, `startTime`, request IDs. No new/disappeared `name=` entries on the generator-derived resources (tags, root_folders, download_clients, remote_path_mappings, qbit categories, jellyfin libraries, animeTags). This file is the PRIMARY dispositive — the cluster-API JSON is the same regardless of which local code version reads it.
- `snapshots/phase-12-cross-version-plan-actions.diff` (v030 log vs v040 log) MUST show only:
  - Removed `merge_decision` structlog events (expected — function deleted in Plan A)
  - Removed log-keyword fragments referencing `merge_with_manual`
  - NO line where a previously-emitted `plan_action` is now absent or has a different `action=` value for the same `resource`

**Status:** [ ] passed / [ ] failed: <details>

## Summary

| Scenario | Status | Evidence path |
|---|---|---|
| 1 (image 0.7.0 pulled) | [ ] / [ ] | kubectl get cronjob output |
| 2 (after-snapshot) | [ ] / [ ] | snapshots/after-phase-12-DATE/ |
| 3 (SC#5 dispositive diff) | [ ] / [ ] | snapshots/phase-12-cluster-api-diff.diff + phase-12-cross-version-plan-actions.diff |

Phase 12 closure verdict: [ ] PASSED / [ ] FAILED
```

<!-- 12-VERIFICATION.md template -->

```markdown
---
phase: 12-categories-deprecation
status: <draft|verified|failed>
verified_by: human-operator
verified_at: YYYY-MM-DD
sc_status:
  sc1: <passed|failed>   # merge_with_manual removed + callsites simplified — Plan A
  sc2: <passed|failed>   # flat sections deleted + schema regen — Plan B
  sc3: <passed|failed>   # test_sweep is sole sweep — Plan C
  sc4: <passed|failed>   # CLAUDE.md deprecation section — Plan D
  sc5: <passed|failed>   # live cluster v030-vs-v040 diff dispositive — Plan E
---

# Phase 12 Verification

## SC#1 (`merge_with_manual` removed)
- `grep -cE "merge_with_manual\(" tools/arrconf/arrconf/__main__.py` = 0 ✅ (was 22 pre-deletion)
- `_resolve_anime_tag_labels` survives in `_shared.py` ✅
- Plan A SUMMARY: <link>

## SC#2 (Flat sections deleted + schema regen)
- `yq` on 11 deleted paths returns null ✅
- `arrconf schema-gen` reproducible (CI test green) ✅
- D-13 unit test `test_load_config_rejects_legacy_items_field` green ✅
- Plan B SUMMARY: <link>

## SC#3 (`test_sweep` is sole SC#3 dispositive)
- `pytest tests/test_phase10_idempotence_sweep.py::test_sweep -v` exits 0 ✅
- `grep -c "^def test_sweep" tools/arrconf/tests/test_phase10_idempotence_sweep.py` = 1 ✅
- Plan C SUMMARY: <link>

## SC#4 (CLAUDE.md deprecation section)
- `grep -q "v0.3.0 → v0.4.0 deprecation" CLAUDE.md` exits 0 ✅
- ValidationError block in CLAUDE.md matches Plan B's captured pytest -v output verbatim ✅
- Plan D SUMMARY: <link>

## SC#5 (Live cluster v030-vs-v040 dry-run diff)
- 12-HUMAN-UAT.md Scenario 3 marked PASSED ✅
- `snapshots/phase-12-cluster-api-diff.diff` reviewed: only benign timestamp/freeSpace drift ✅
- `snapshots/phase-12-cross-version-plan-actions.diff` reviewed: only `merge_decision` event removal + benign log-keyword cleanup ✅
- Plan E SUMMARY: <link>

## Outcome

Verdict: <PASSED|FAILED>

D-17 requires BOTH SC#3 and SC#5 to pass for closure. <Both pass / SC#X failed because Y>.
```
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task E.1 (HUMAN): Post-merge dispositive snapshot + cross-version diff + UAT capture</name>
  <what-built>
    Plans A-D are merged. PR1 image `0.7.0` is running in the cluster. The operator must now capture the after-snapshot (from the v0.4.0 working tree against the v0.4.0 cluster), perform the cross-version diff against Plan D's before-snapshot (v0.3.0 vs v0.3.0), and write up the SC#5 verdict. This work lands as evidence-only PR2 per D-16.
  </what-built>
  <how-to-verify>
    Operator runs the three scenarios documented in the 12-HUMAN-UAT.md template (see `<interfaces>` above):

    1. **Scenario 1 — Image 0.7.0 picked up by cluster:** run the two `kubectl` commands; both must show the expected output. If `kubectl -n argocd get application arr-stack` does NOT show Synced+Healthy, STOP and diagnose before continuing.

    2. **Scenario 2 — After-snapshot capture (v0.4.0 working tree):** mirror Plan D Task D.2 steps 3-4 to re-establish port-forwards + secrets, then run `tools/snapshot/snapshot.sh --output snapshots/after-phase-12-${DATE}/` and the in-cluster CronJob dry-run. The dry-run log is named `dry-run-plan-actions-v040.log` to pair with Plan D's `dry-run-plan-actions-v030.log`.

    3. **Scenario 3 — SC#5 dispositive diff (cross-version):**
       - `diff -r snapshots/before-phase-12-*/ snapshots/after-phase-12-*/ --exclude='dry-run-plan-actions-*.log' --exclude='cluster-cronjob-log.txt' > snapshots/phase-12-cluster-api-diff.diff` (don't fail on diff exit code)
       - `diff snapshots/before-phase-12-*/dry-run-plan-actions-v030.log snapshots/after-phase-12-*/dry-run-plan-actions-v040.log > snapshots/phase-12-cross-version-plan-actions.diff` (don't fail on diff exit code)
       - Inspect both diffs.

       **Acceptable noise in `phase-12-cluster-api-diff.diff`** (the raw cluster-API JSON):
       - Timestamps (`startTime`, `lastWriteTime`)
       - `freeSpace` byte counts on root folders
       - Request IDs in qBit responses
       - Sonarr/Radarr "last poll" fields

       **Acceptable noise in `phase-12-cross-version-plan-actions.diff`** (v030 vs v040 dry-run logs):
       - Removed `merge_decision` structlog events (expected — function deleted)
       - Removed log-keyword fragments (`merge_with_manual`)
       - Timestamps in log lines

       **Unacceptable diffs (block phase closure):**
       - Any `plan_action action=update` or `action=delete` line that appears in after but not in before, OR vice versa, for the same `resource`
       - Any reconcile-time error (`api_error`, `app_failed`, `ReconcileError`) absent in before but present in after
       - Schema validation errors (`ValidationError`, `extra_forbidden`) in the v040 log — this would mean some operator-side YAML still has dead fields, which is a Plan B regression
       - Any name=value change on a generator-derived resource (tag label, root folder path, download client name, etc.) — these MUST be identical because the generators produce the same output from the same `categories[]`

    4. Create `12-HUMAN-UAT.md` by copying the template from `<interfaces>` and filling in each Scenario's status (passed/failed) + evidence path.

    5. Create `12-VERIFICATION.md` by copying the template from `<interfaces>` and filling SC#1-SC#5 statuses based on:
       - SC#1: confirm with `grep -cE "merge_with_manual\(" tools/arrconf/arrconf/__main__.py` returning 0
       - SC#2: confirm with `cd tools/arrconf && uv run arrconf schema-gen --output /tmp/check.json && diff schemas/arrconf-schema.json /tmp/check.json` exit 0 AND `cd tools/arrconf && uv run pytest tests/test_config_validation.py::test_load_config_rejects_legacy_items_field -v` exit 0
       - SC#3: confirm with `cd tools/arrconf && uv run pytest tests/test_phase10_idempotence_sweep.py::test_sweep -v` exit 0
       - SC#4: confirm with `grep -q "v0.3.0 → v0.4.0 deprecation" CLAUDE.md` exit 0
       - SC#5: take the verdict from 12-HUMAN-UAT.md Scenario 3

    6. Commit and open PR2 (evidence-only) per D-16:
       ```bash
       git add snapshots/after-phase-12-*/ snapshots/phase-12-cluster-api-diff.diff snapshots/phase-12-cross-version-plan-actions.diff \
         .planning/phases/12-categories-deprecation/12-HUMAN-UAT.md \
         .planning/phases/12-categories-deprecation/12-VERIFICATION.md
       git commit -m "verify(12): SC#5 dispositive — live cluster v030-vs-v040 diff captured (ADR-6, D-16, D-17)"
       git push -u origin main   # or open PR2 if branch-protection requires
       ```

    7. If SC#5 PASSES, update `.planning/ROADMAP.md` line `[ ] **Phase 12: Categories deprecation**` to `[x] **Phase 12: Categories deprecation** — closed YYYY-MM-DD`. If SC#5 FAILS, route to `/gsd-plan-phase 12 --gaps` for hotfix scoping.
  </how-to-verify>
  <resume-signal>
    Reply `approved` after PR2 is opened and 12-VERIFICATION.md shows all 5 SC as PASSED. Reply `sc5-failed: <details>` if Scenario 3's diff shows unacceptable plan_action drift — that triggers the gap-closure flow.
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Live cluster API ↔ operator workstation | API keys flow as headers over port-forwarded HTTPS. |
| snapshot.sh stdout → committed JSON | Built-in redaction; operator verifies. |
| Post-merge code path (image 0.7.0) ↔ cluster | Genuinely new code-paths exercise the cluster for the first time as ConfigMap+Image. |
| v0.3.0 working tree (Plan D) ↔ v0.4.0 working tree (this plan) | The cross-version log naming (`-v030.log` / `-v040.log`) enforces explicit version provenance; if a log is captured from the wrong tree, the file name lies — operator self-audit catches via Scenario 1 prerequisite checks. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-12E-01 | Information Disclosure | after-snapshot capture | mitigate | snapshot.sh redaction + operator re-grep audit (same control as Plan D Task D.2 step 6). |
| T-12E-02 | Tampering | live cluster dry-run | mitigate | `--dry-run` (and `ARRCONF_DRY_RUN=true` env on CronJob) guarantees no PUT/POST. The in-cluster CronJob invocation in Scenario 2 is also dry-run. |
| T-12E-03 | Denial of Service | image 0.7.0 unavailable | mitigate | Operator confirms anonymous pullability (`docker pull ghcr.io/tom333/arr-stack-arrconf:0.7.0`) BEFORE merging the my-kluster Renovate PR; if missing, the manual-tag escape hatch (CLAUDE.md "Accumulated-bumps escape hatch") applies. |
| T-12E-04 | Repudiation | SC#5 verdict | mitigate | All three scenarios produce committable evidence files (`snapshots/`, `12-HUMAN-UAT.md`, `12-VERIFICATION.md`); the verdict is reproducible from the artifacts. The two diff files separate "raw cluster API drift" from "log-shape drift" so a future investigator can distinguish substance (block) from noise (waive). |
| T-12E-05 | Elevation of Privilege | PR2 evidence commits | accept | PR2 is evidence-only per D-16 — no code, no chart, no values changes. Branch-protection rules on main apply unchanged. |
| T-12E-06 | Tampering | log version provenance | mitigate | File names `-v030.log` / `-v040.log` encode the source-version; operator confirms in Scenario 1 that image is 0.7.0 before generating the v040 log. Mismatched provenance triggers `working-tree-uncertain` resume signal in Plan D. |
</threat_model>

<verification>
- `snapshots/after-phase-12-*/dry-run-plan-actions-v040.log` exists and contains apply_complete or no-op entries for sonarr/radarr/qbittorrent/jellyfin/seerr (5 successful app branches; prowlarr may not have applicable plan_action under dry-run depending on cluster state)
- `snapshots/phase-12-cluster-api-diff.diff` shows ONLY benign drift (timestamps/freeSpace) on raw cluster-API JSON
- `snapshots/phase-12-cross-version-plan-actions.diff` shows ONLY removed `merge_decision` lines + benign timestamp/log-key changes
- `12-VERIFICATION.md` shows all 5 SC statuses
- `12-HUMAN-UAT.md` Scenario 3 status = passed
- `kubectl -n selfhost get cronjob arrconf -o jsonpath='...image}'` returns `ghcr.io/tom333/arr-stack-arrconf:0.7.0`
</verification>

<success_criteria>
- SC#5 (live cluster v030-vs-v040 plan_action shape unchanged) — SATISFIED by Scenario 3 cross-version diff.
- D-14, D-16, D-17 closed in this plan.
- Phase 12 closure: ROADMAP.md line marked `[x]` after this plan's PR2 lands.
</success_criteria>

<output>
After completion, create `.planning/phases/12-categories-deprecation/12-E-live-cluster-dispositive-SUMMARY.md` documenting:
- Path to the `after-phase-12-*` snapshot directory
- Path to BOTH diff files: `phase-12-cluster-api-diff.diff` (raw cluster JSON) and `phase-12-cross-version-plan-actions.diff` (v030 log vs v040 log)
- Verbatim list of "acceptable noise" diff lines observed in each file (so future investigators see what was waived, and which file the waiver applies to)
- Final SC verdicts from 12-VERIFICATION.md
- The PR2 URL once opened
</output>
</content>
</invoke>