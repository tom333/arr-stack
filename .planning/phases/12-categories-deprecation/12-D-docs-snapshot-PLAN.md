---
phase: 12-categories-deprecation
plan: D
type: execute
wave: 3
depends_on: [A, B, C]
files_modified:
  - CLAUDE.md
  - snapshots/before-phase-12-YYYY-MM-DD/
autonomous: false
requirements:
  - REQ-categories-deprecation
mode: standard

must_haves:
  truths:
    - "CLAUDE.md gains `## v0.3.0 → v0.4.0 deprecation` section after `## Release pin co-bump pattern` (D-11)"
    - "Section contents: rationale + verbatim list of deleted YAML paths + sample ValidationError text + operator one-shot fix instructions (D-11 + D-13)"
    - "The ValidationError text quoted in CLAUDE.md is the verbatim output of `tools/arrconf/tests/test_config_validation.py::test_load_config_rejects_legacy_items_field` (created in Plan B Task B.2) — copied from `12-B-pydantic-yaml-schema-SUMMARY.md`'s `## Captured D-13 ValidationError` section. NO hand-written prose error string."
    - "Pre-merge snapshot captured: `snapshots/before-phase-12-YYYY-MM-DD/` produced by `tools/snapshot/snapshot.sh` (D-14, ADR-6)"
    - "**The pre-merge snapshot is captured BEFORE Plan A's local changes are committed** — against the cluster currently running image `:0.6.7`, NOT against new local code. This makes the SC#5 diff a true v0.3.0-vs-v0.4.0 measurement, not a tautological self-diff (see Task D.2 step 1)."
    - "Snapshot is committed (lossless, redacted per snapshot.sh built-in redaction logic) — ADR-6 discipline preserved"
    - "NO arrconf code changes in this plan (code already shipped in Plan A)"
    - "NO additional values.yaml bump in this plan (co-bump already in Plan A's commit per CLAUDE.md `Release pin co-bump pattern`)"
  artifacts:
    - path: "CLAUDE.md"
      provides: "## v0.3.0 → v0.4.0 deprecation section"
      contains: "v0.3.0 → v0.4.0 deprecation"
    - path: "snapshots/before-phase-12-YYYY-MM-DD/"
      provides: "Pre-merge cluster API state for SC#5 diff against Plan E's after-snapshot. Captured against the v0.3.0 cluster (image :0.6.7), NOT against new local Plan-A code."
  key_links:
    - from: "CLAUDE.md deprecation section"
      to: "tools/arrconf/tests/test_config_validation.py::test_load_config_rejects_legacy_items_field (Plan B Task B.2)"
      via: "Plan D executor copies the captured pytest -v output from Plan B's SUMMARY verbatim into the CLAUDE.md doc block"
      pattern: "extra_forbidden|Extra inputs are not permitted"
    - from: "snapshots/before-phase-12-*/"
      to: "snapshots/after-phase-12-* (Plan E)"
      via: "diff -r"
      pattern: "plan_action"
---

<note>

**Autonomous contract:**

Plan-level `autonomous: false` denotes that the plan as a whole cannot complete without operator action — Task D.2's snapshot capture requires cluster port-forward and live API keys, which only the human operator can provide.

Task D.1 (CLAUDE.md edit) IS auto-driven by the executor: `type="auto"`, no checkpoint, no human input needed (the doc content is fully derived from Plan B's SUMMARY).

Task D.2 IS human-blocking: `type="checkpoint:human-action"`, gate="blocking".

**Execution order:** `/gsd-execute-phase` should drive D.1 first (purely automated), then pause at D.2 for operator confirmation. The two tasks are independent — D.1 does NOT depend on D.2's snapshot capture (the doc content depends on Plan B's already-committed SUMMARY, not on the snapshot).

**Wave-0 timing for D.2 step 1 (CRITICAL):** Although Plan D's `wave: 3` reflects the doc-writing dependency on Plan B's SUMMARY, the *snapshot capture* itself (Task D.2 step 1) MUST happen on a clean `main` BEFORE Plan A's code changes exist locally. This is enforced by Task D.2 step 1's explicit warning + the use of `git worktree` or `git stash` to obtain a pre-Plan-A working tree if changes have already started landing.

</note>

<objective>
Document the deprecation for the project's only operator (the user himself) via a new CLAUDE.md section, and capture the pre-merge baseline snapshot per ADR-6 — captured against the live v0.3.0 cluster running image `:0.6.7`, before any Plan-A local code changes are committed.

Purpose: The doc closes D-11 (operator migration guidance) using the canonical ValidationError text captured by Plan B's D-13 unit test. The snapshot anchors SC#5 — Plan E will capture an `after-` snapshot post-merge against the cluster running image `:0.7.0` and diff it against this baseline. The diff measures actual v0.3.0 → v0.4.0 cluster-API behaviour (NOT a same-code self-diff, which would be structurally trivial).

Output: 1 modified file (CLAUDE.md) + 1 new directory of redacted JSON snapshots.

Note: This plan does NOT touch arrconf code or values.yaml. The chart-pin co-bump (0.6.7 → 0.7.0) lives in Plan A's commit per CLAUDE.md "Release pin co-bump pattern" — it MUST NOT be duplicated here.
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
@tools/arrconf/tests/test_config_validation.py

<interfaces>
<!-- CLAUDE.md deprecation section template (D-11 contents 1-4) -->

The new section MUST land DIRECTLY AFTER the existing `### Release pin co-bump pattern` section in CLAUDE.md (which itself sits within the `## Conventions développement — arrconf` parent). Place it as a new H3 sibling: `### v0.3.0 → v0.4.0 deprecation` OR as a top-level H2 if the section warrants it — executor decides based on the existing heading hierarchy. (The CONTEXT D-11 wording "`## v0.3.0 → v0.4.0 deprecation`" suggests H2.)

The section body, in writing-with-codebase voice (FR/EN mix per existing CLAUDE.md style), MUST cover D-11's four points:

```markdown
## v0.3.0 → v0.4.0 deprecation

### Pourquoi ce changement

La couche de transition v0.2.0 (`merge_with_manual` + sections plates `*.items`)
est retirée. À partir de v0.4.0, les générateurs purs de
`arrconf/generators/categories.py` sont la **seule source** pour 11 ressources
(sonarr/radarr × {tags, root_folders, download_clients, remote_path_mappings},
qbittorrent.categories, jellyfin.libraries, seerr.sonarr_service.animeTags).
Le toggle par ressource n'existe plus — pas de fallback, pas de cycle de
warning. `extra="forbid"` sur les Section pydantic refuse les anciens champs.

### Sections supprimées de `charts/arr-stack/files/arrconf.yml`

Verbatim, les 11 paths supprimés en Phase 12 (anchors forensiques pour git
diff sur la branche `pre-v0.4.0`) :

- `sonarr.main.tags.items` (3 labels: tv, anime, family)
- `sonarr.main.root_folders.items` (3 paths)
- `sonarr.main.download_clients.items` (3 qBit DCs)
- `sonarr.main.remote_path_mappings.items` (3 RPMs)
- `radarr.main.tags.items` (3 labels: movies, anime, family)
- `radarr.main.root_folders.items` (3 paths)
- `radarr.main.download_clients.items` (3 qBit DCs)
- `radarr.main.remote_path_mappings.items` (3 RPMs)
- `qbittorrent.main.categories.items` (10 entrées dérivées de `categories[]`)
- `seerr.main.sonarr_service.animeTags` (`list[int]` — Sonarr tag IDs anime)
- `jellyfin.main.libraries.items` (Séries + Films super-libraries)

Les sections parentes (e.g. `sonarr.main.tags:`) survivent avec uniquement
`prune: false` — c'est le seul knob opérateur restant (D-02).

### Erreur attendue si l'ancien YAML survit après upgrade

Si un opérateur (homelab fork / Categories non-encore-réconciliées) garde
e.g. `sonarr.main.tags.items` dans son `arrconf.yml` post-upgrade, le prochain
`arrconf apply` exit code 2 avec une `ValidationError` pydantic. L'erreur
exacte est pinguée par le test unitaire
`tools/arrconf/tests/test_config_validation.py::test_load_config_rejects_legacy_items_field`
(introduit en Phase 12 Plan B) :

```
<PASTE-VERBATIM-FROM-12-B-SUMMARY.md-CAPTURED-D13-VALIDATION-ERROR-SECTION>
```

Le path `sonarr.main.tags.items` dans le message pointe la ligne à supprimer.

### Fix one-shot pour l'opérateur

1. Vérifier qu'on est sur la branche post-Phase-12 :
   `git log --oneline -1 charts/arr-stack/files/arrconf.yml`
2. Comparer son `arrconf.yml` local avec la version chart-shipped :
   `diff <local-arrconf.yml> charts/arr-stack/files/arrconf.yml`
3. Supprimer chaque `items:` listé dans `## Sections supprimées` ci-dessus.
   Les générateurs (re-)produisent les mêmes ressources à partir de
   `categories[]`. Garder `prune: false` sur les sections parentes.
4. Re-tester en dry-run :
   `arrconf apply --config arrconf.yml --dry-run`
5. Commit + push une fois la validation passée.

Pas de script de migration livré — l'opérateur est unique (le user), l'édition
se fait dans le PR qui ship le code v0.4.0 lui-même (D-12, D-15, D-18).
```

**Executor handoff:** the `<PASTE-VERBATIM-FROM-12-B-SUMMARY.md-CAPTURED-D13-VALIDATION-ERROR-SECTION>` placeholder MUST be replaced by the literal terminal output recorded in `12-B-pydantic-yaml-schema-SUMMARY.md` under the `## Captured D-13 ValidationError` heading. NO paraphrasing, NO hand-editing. If the SUMMARY does not contain that section, STOP and route back to Plan B for completion (Task B.2 acceptance criteria requires that section to exist).

<!-- Snapshot capture command (D-14, ADR-6) -->

The pre-merge snapshot is OPERATOR action (no API key available in CI), captured BEFORE Plan A's local code changes are committed, against the cluster currently running image `:0.6.7`. See Task D.2 step 1 for the git-worktree / git-stash escape hatch if Plan A has already been started locally.

```bash
# Pre-flight: ensure secrets are exported in the operator's shell
export SONARR_API_KEY=...
export RADARR_API_KEY=...
export PROWLARR_API_KEY=...
export JELLYFIN_API_KEY=...
export SEERR_API_KEY=...
export QBT_USER=...
export QBT_PASS=...

# kubectl port-forward each service (or use kube-resolved DNS if cluster-internal)
# (refer to CLAUDE.md §"Test arrconf contre une vraie instance" for the pattern)

# Then:
DATE=$(date +%F)
tools/snapshot/snapshot.sh --output snapshots/before-phase-12-${DATE}/

# Confirm no secrets leak past redaction
ls snapshots/before-phase-12-${DATE}/
git add snapshots/before-phase-12-${DATE}/
git status   # operator reviews; commit happens as part of PR
```

The snapshot.sh script already includes built-in password/API-key redaction (post-Phase-6 fix). Operator confirms the redaction by `grep -rni "password\|apikey\|api_key" snapshots/before-phase-12-*/` returning only redacted placeholders.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task D.1: Add `## v0.3.0 → v0.4.0 deprecation` section to CLAUDE.md</name>
  <files>CLAUDE.md</files>
  <read_first>
    - CLAUDE.md (full file — locate the existing `### Release pin co-bump pattern` section, around line 70-200 region. The new section goes IMMEDIATELY after the closing of the existing co-bump section and BEFORE the next H3 or H2 boundary)
    - tools/arrconf/tests/test_config_validation.py (the D-13 unit test introduced by Plan B Task B.2 — confirms the doc and test are coupled)
    - .planning/phases/12-categories-deprecation/12-A-reconciler-refactor-SUMMARY.md (confirm the actual code state Plan A landed — the doc must reflect reality, not the plan)
    - .planning/phases/12-categories-deprecation/12-B-pydantic-yaml-schema-SUMMARY.md (confirm the exact YAML paths deleted — must match the doc verbatim. **Most importantly**: read the `## Captured D-13 ValidationError` section — that block is the literal text the executor pastes into CLAUDE.md replacing the `<PASTE-VERBATIM…>` placeholder.)
  </read_first>
  <action>
    Insert the markdown section in `<interfaces>` block above into `CLAUDE.md`. Placement rule:

    1. Find the line in CLAUDE.md that closes the `### Release pin co-bump pattern` subsection (or the parent `## Conventions développement — arrconf` if structure suggests H2 placement). Use `grep -n "^###\|^##" CLAUDE.md | head -30` to map the heading structure first.

    2. The CONTEXT D-11 says `## v0.3.0 → v0.4.0 deprecation` (H2). Insert at H2 level immediately after the closing of `## Conventions développement — arrconf` (the parent section), OR at H3 level under it (executor decides based on which placement preserves the existing TOC flow better — both are acceptable as long as the heading reads `v0.3.0 → v0.4.0 deprecation`).

    3. Copy the markdown block from `<interfaces>` VERBATIM as the new section content. The verbatim list of 11 deleted paths MUST match Plan B's SUMMARY.

    4. **Replace `<PASTE-VERBATIM-FROM-12-B-SUMMARY.md-CAPTURED-D13-VALIDATION-ERROR-SECTION>`** with the literal block recorded in `.planning/phases/12-categories-deprecation/12-B-pydantic-yaml-schema-SUMMARY.md` under the `## Captured D-13 ValidationError` heading. The substitution is mechanical — read that section of the SUMMARY, copy its code-fenced block verbatim, and paste it into the CLAUDE.md placeholder. Do NOT paraphrase, do NOT trim, do NOT edit error line numbers. **If the SUMMARY does not contain that section, STOP** — Plan B Task B.2 did not complete fully, and Plan D cannot proceed until it does (the doc cross-reference is load-bearing per the must_haves.truths).

    5. Update the `**État actuel**` line at the very top of CLAUDE.md (if it currently references "milestone v0.3.0 — Categories first-class livré") to add a forward-reference: append `Phase 12 deprecation livré — flat sections retirées de arrconf.yml, generators sont la seule source.` to the existing sentence. Keep the rest of the line intact.
  </action>
  <verify>
    <automated>
      cd /data/projets/perso/arr-stack && \
      grep -q "## v0.3.0 → v0.4.0 deprecation\|### v0.3.0 → v0.4.0 deprecation" CLAUDE.md ; \
      grep -q "sonarr.main.tags.items" CLAUDE.md ; \
      grep -q "jellyfin.main.libraries.items" CLAUDE.md ; \
      grep -q "seerr.main.sonarr_service.animeTags" CLAUDE.md ; \
      grep -q "qbittorrent.main.categories.items" CLAUDE.md ; \
      grep -qE "extra_forbidden|Extra inputs are not permitted" CLAUDE.md ; \
      grep -q "test_load_config_rejects_legacy_items_field" CLAUDE.md ; \
      grep -q "merge_with_manual" CLAUDE.md ; \
      grep -q "arrconf/generators/categories.py" CLAUDE.md ; \
      ! grep -q "PASTE-VERBATIM-FROM-12-B-SUMMARY" CLAUDE.md ; \
      echo "DOC OK"
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "v0.3.0 → v0.4.0 deprecation" CLAUDE.md` exits 0
    - `grep -q "sonarr.main.tags.items" CLAUDE.md` exits 0 (verbatim path #1 present)
    - `grep -q "jellyfin.main.libraries.items" CLAUDE.md` exits 0 (verbatim path #11 present)
    - `grep -q "seerr.main.sonarr_service.animeTags" CLAUDE.md` exits 0
    - `grep -q "qbittorrent.main.categories.items" CLAUDE.md` exits 0
    - `grep -qE "extra_forbidden|Extra inputs are not permitted" CLAUDE.md` exits 0 (D-13 dispositive error string present)
    - `grep -q "test_load_config_rejects_legacy_items_field" CLAUDE.md` exits 0 (doc cross-references the Plan B test)
    - `grep -q "merge_with_manual" CLAUDE.md` exits 0 (deprecation context mentions the removed function)
    - `! grep -q "PASTE-VERBATIM-FROM-12-B-SUMMARY" CLAUDE.md` (placeholder was replaced — no template leakage)
    - The new section sits AFTER the `### Release pin co-bump pattern` section (verify by `awk '/^###?\s+Release pin co-bump/,/^### v0\.3\.0|^## v0\.3\.0/' CLAUDE.md | wc -l` returns > 0 lines)
  </acceptance_criteria>
  <done>CLAUDE.md gains the deprecation section with all 4 D-11 contents; the verbatim path list matches Plan B's actual edits; the ValidationError block is the literal pytest -v output from Plan B Task B.2 (no hand-written prose); placement respects existing heading hierarchy.</done>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task D.2 (HUMAN): Capture pre-merge cluster snapshot — against v0.3.0 cluster, BEFORE Plan A's local code lands</name>
  <what-built>
    The CLAUDE.md deprecation section is committed in Task D.1. Plans A/B/C have prepared local code/YAML/schema/test changes — possibly already committed locally. Before merging the phase PR, the operator must capture the live cluster's API state as the SC#5 baseline.

    **CRITICAL TIMING:** This snapshot MUST be captured against the cluster currently running image `:0.6.7` (v0.3.0 code path), NOT against new local Plan-A code. The capture is read-only (snapshot.sh is GET-only against the live API), so the cluster state IS the v0.3.0 baseline regardless of what local code looks like — but the operator's `arrconf apply --dry-run` (step 6 below) IS sensitive to local code and MUST be run from a pre-Plan-A working tree.
  </what-built>
  <how-to-verify>
    Operator runs the following from the arr-stack repo root. Each step is non-skippable.

    1. **Establish a pre-Plan-A working tree.**

       This is the critical timing step that avoids the SC#5 tautology (running the post-refactor code against the same cluster as the post-refactor code = trivially zero diff).

       Pick ONE of:
       - **Option 1A (cleanest):** create a separate worktree pinned to a pre-Plan-A commit.
         ```bash
         # Find the last commit BEFORE Plan A landed locally:
         git log --oneline -- tools/arrconf/arrconf/__main__.py | head -5
         # Pick the SHA immediately before the "phase 12 Plan A" or "feat(12):" commit.
         PRE_PLAN_A_SHA=<that SHA>
         git worktree add ../arr-stack-baseline ${PRE_PLAN_A_SHA}
         cd ../arr-stack-baseline
         ```
       - **Option 1B (if you have not yet started Plan A locally):** you are already on the pre-Plan-A working tree; just verify with `git log --oneline -3` showing no "Phase 12" commits yet.
       - **Option 1C (stash-based fallback):** if Plan A's changes are uncommitted local edits, `git stash push -u -m "phase-12-plan-a-wip"` then operate from clean main. Re-apply with `git stash pop` AFTER step 7.

       After this step the working tree MUST reflect v0.3.0 code (image `:0.6.7` Python path).

    2. Confirm cluster connectivity (one-time check, independent of local working tree):
       ```bash
       kubectl -n selfhost get pods | grep -E "sonarr|radarr|prowlarr|qbittorrent|jellyfin|seerr"
       ```
       All 6 pods MUST show `Running`.

       Also confirm the deployed image:
       ```bash
       kubectl -n selfhost get cronjob arrconf -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}'
       # Expected: ghcr.io/tom333/arr-stack-arrconf:0.6.7
       ```

    3. Export secrets from the operator's local secret stash (or copy from `kubectl get secret arrconf-env -n selfhost -o yaml | grep -A6 data` after `base64 -d`):
       ```bash
       export SONARR_API_KEY=<value>
       export RADARR_API_KEY=<value>
       export PROWLARR_API_KEY=<value>
       export JELLYFIN_API_KEY=<value>
       export SEERR_API_KEY=<value>
       export QBT_USER=<value>
       export QBT_PASS=<value>
       ```

    4. Set up port-forwards (one terminal per app, or use a multiplexer):
       ```bash
       kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
       kubectl -n selfhost port-forward svc/radarr 7878:7878 &
       kubectl -n selfhost port-forward svc/prowlarr 9696:9696 &
       kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
       kubectl -n selfhost port-forward svc/jellyfin 8096:8096 &
       kubectl -n selfhost port-forward svc/seerr 5055:5055 &
       ```

    5. Capture snapshot (snapshot.sh is GET-only; it walks the live cluster API and writes raw JSON files to the output directory):
       ```bash
       DATE=$(date +%F)
       tools/snapshot/snapshot.sh --output snapshots/before-phase-12-${DATE}/
       ```

       The output directory contains raw cluster-API JSON files (sonarr_*.json, radarr_*.json, etc.). These represent the **v0.3.0 cluster state** independent of local code. This is the true SC#5 baseline.

    6. Verify redaction (post-Phase-6 fix should be in effect; manual safety check):
       ```bash
       grep -rniE "(api[-_]?key|password|passkey|token).*:.*[a-z0-9]{16,}" snapshots/before-phase-12-${DATE}/ || echo "REDACTION CLEAN"
       ```
       Output MUST be `REDACTION CLEAN` (no real secrets found). If real secret-looking strings appear, manually redact before commit.

    7. Capture the v0.3.0 dry-run plan-action log (against the v0.3.0 working tree from step 1):
       ```bash
       cd tools/arrconf && uv run arrconf apply \
         --config ../../charts/arr-stack/files/arrconf.yml --dry-run \
         > ../../snapshots/before-phase-12-${DATE}/dry-run-plan-actions-v030.log 2>&1
       ```

       **Why this log matters:** Plan E's after-snapshot will capture the v0.4.0 equivalent (`dry-run-plan-actions-v040.log`) using the new code against the same cluster. Plan E's SC#5 dispositive diff compares these two logs. By capturing the v0.3.0 log here (from the v0.3.0 working tree, against the v0.3.0 cluster), we get a TRUE before/after measurement — not a same-code self-diff. The log file name is suffixed `-v030.log` to make the source-version explicit; Plan E mirrors with `-v040.log`.

    8. If you used Option 1A (worktree), commit/copy the snapshot back into the main working tree:
       ```bash
       cd /data/projets/perso/arr-stack   # back to main worktree
       mkdir -p snapshots/before-phase-12-${DATE}
       cp -r ../arr-stack-baseline/snapshots/before-phase-12-${DATE}/* \
             snapshots/before-phase-12-${DATE}/
       git worktree remove ../arr-stack-baseline   # cleanup
       ```

       If you used Option 1C (stash), just `git stash pop` to restore Plan A's WIP.

    9. Stage + commit (NOT push — push happens with the full PR):
       ```bash
       git add snapshots/before-phase-12-${DATE}/
       git status
       git commit -m "snapshot(12): pre-merge v0.3.0 cluster baseline for SC#5 (ADR-6, D-14)"
       ```

    10. Report back: paste the output of `ls snapshots/before-phase-12-${DATE}/` (file count) and `cat snapshots/before-phase-12-${DATE}/dry-run-plan-actions-v030.log | tail -20` (the operator's confidence anchor before merging).
  </how-to-verify>
  <resume-signal>
    Reply `approved` after the snapshot is committed and the v0.3.0 dry-run log captured. Reply `redaction-failure: <details>` if step 6 surfaces unredacted secrets — that blocks the PR until snapshot.sh is patched. Reply `working-tree-uncertain: <details>` if you cannot confirm step 1's pre-Plan-A working tree (Plan E's SC#5 diff will become tautological if Plan A's code influenced step 7's log).
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator laptop ↔ cluster API | Port-forwarded HTTPS/HTTP; API keys flow as headers. |
| snapshot.sh stdout → committed JSON | Built-in redaction is the trust gate against secret leak (ADR-6). |
| CLAUDE.md → future-operator (future user, future fork) | Documentation accuracy = mitigation against repeating v0.3.0→v0.4.0 confusion. The doc-test coupling (Plan B `test_load_config_rejects_legacy_items_field` ↔ CLAUDE.md error block) prevents stale doc drift. |
| Pre-Plan-A working tree ↔ v0.3.0 baseline log | If step 1 fails to establish a v0.3.0 tree, step 7's log is computed by v0.4.0 code and the SC#5 diff becomes a same-code self-diff (structurally zero by construction, dispositive of nothing). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-12D-01 | Information Disclosure | snapshot capture | mitigate | `tools/snapshot/snapshot.sh` already includes post-Phase-6 password+API-key redaction. Task D.2 step 6 enforces a re-grep audit before commit (operator gate). |
| T-12D-02 | Tampering | CLAUDE.md edit | mitigate | Doc lands as part of the PR; reviewer (= user, same person) cross-checks against actual code state via the SUMMARY references. The error block is mechanically copied from Plan B's pytest -v output (no hand-edited prose). |
| T-12D-03 | Repudiation | snapshot vs Plan E after-snapshot | mitigate | `snapshots/before-phase-12-DATE/` committed before merge with `dry-run-plan-actions-v030.log` produced from a pre-Plan-A working tree; Plan E captures `snapshots/after-phase-12-DATE/` with `dry-run-plan-actions-v040.log`; `diff` between them is the dispositive SC#5 evidence (true v030-vs-v040 measurement). |
| T-12D-04 | Denial of Service | port-forward + snapshot | accept | Single-operator workflow; if a port-forward dies mid-snapshot, operator restarts. No production impact. |
| T-12D-05 | Spoofing | None applicable | n/a | Snapshot is read-only against cluster APIs; no PUT/POST issued. |
| T-12D-06 | Repudiation | doc-test coupling drift | mitigate | The CLAUDE.md error block IS the test output. If Plan B's test is later edited without updating CLAUDE.md (or vice versa), a future Plan B re-run will produce a different captured output and the doc-vs-test drift will be visible. |
</threat_model>

<verification>
- `grep -q "v0.3.0 → v0.4.0 deprecation" CLAUDE.md` exits 0
- `grep -q "test_load_config_rejects_legacy_items_field" CLAUDE.md` exits 0
- `! grep -q "PASTE-VERBATIM-FROM-12-B-SUMMARY" CLAUDE.md` (placeholder substituted)
- `ls snapshots/before-phase-12-*/` lists ≥ 6 subdirectories (one per app)
- `cat snapshots/before-phase-12-*/dry-run-plan-actions-v030.log | grep -E "ValidationError|missing_api_key"` returns ZERO matches (the YAML loaded cleanly under the pre-Plan-B shape — note: from the pre-Plan-A working tree, arrconf.yml still has the flat items blocks)
- The snapshot diff vs `snapshots/post-phase2.2-hotfix-*` (most recent prior snapshot) shows ONLY expected drift (Phase 11+ Categories resources, no surprise mutations)
</verification>

<success_criteria>
- SC#4 (CLAUDE.md deprecation section, coupled to the D-13 unit test) — SATISFIED by Task D.1.
- SC#5 prerequisite (before-snapshot for diff, captured from v0.3.0 working tree against v0.3.0 cluster) — SATISFIED by Task D.2.
- D-11, D-12, D-13, D-14 closed in this plan.
</success_criteria>

<output>
After completion, create `.planning/phases/12-categories-deprecation/12-D-docs-snapshot-SUMMARY.md` documenting:
- Confirmation CLAUDE.md section landed at the chosen heading level
- Confirmation that the verbatim ValidationError block in CLAUDE.md matches Plan B Task B.2's captured pytest -v output (no drift)
- Path to the committed `snapshots/before-phase-12-DATE/` directory
- File count of the snapshot directory
- Which Option (1A worktree / 1B already-pre-PlanA / 1C stash) the operator used in step 1 and why
- Last 20 lines of the captured `dry-run-plan-actions-v030.log` (clearly labelled as "v0.3.0 working tree against v0.3.0 cluster")
- Confirmation that redaction grep returned `REDACTION CLEAN`
</output>
</content>
</invoke>