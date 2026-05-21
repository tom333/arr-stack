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
    - "Pre-merge snapshot captured: `snapshots/before-phase-12-YYYY-MM-DD/` produced by `tools/snapshot/snapshot.sh` (D-14, ADR-6)"
    - "Snapshot is committed (lossless, redacted per snapshot.sh built-in redaction logic) — ADR-6 discipline preserved"
    - "NO arrconf code changes in this plan (code already shipped in Plan A)"
    - "NO additional values.yaml bump in this plan (co-bump already in Plan A's commit per CLAUDE.md `Release pin co-bump pattern`)"
  artifacts:
    - path: "CLAUDE.md"
      provides: "## v0.3.0 → v0.4.0 deprecation section"
      contains: "v0.3.0 → v0.4.0 deprecation"
    - path: "snapshots/before-phase-12-YYYY-MM-DD/"
      provides: "Pre-merge cluster API state for SC#5 diff against Plan E's after-snapshot"
  key_links:
    - from: "CLAUDE.md deprecation section"
      to: "ValidationError emitted by load_config when an operator keeps old-shape YAML"
      via: "extra='forbid' on Section models"
      pattern: "extra=\"forbid\"|Extra inputs are not permitted"
    - from: "snapshots/before-phase-12-*/"
      to: "snapshots/after-phase-12-* (Plan E)"
      via: "diff -r"
      pattern: "plan_action"
---

<objective>
Document the deprecation for the project's only operator (the user himself) via a new CLAUDE.md section, and capture the pre-merge baseline snapshot per ADR-6.

Purpose: The doc closes D-11 (operator migration guidance). The snapshot anchors SC#5 — Plan E will capture an `after-` snapshot post-merge against the live cluster and diff it against this baseline. The diff must show zero `plan_action` changes (Categories-derived was already in use during v0.3.0; deprecation removes dead code only).

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

<interfaces>
<!-- CLAUDE.md deprecation section template (D-11 contents 1-4) -->

The new section MUST land DIRECTLY AFTER the existing `### Release pin co-bump pattern` section in CLAUDE.md (which itself sits within the `## Conventions développement — arrconf` parent). Place it as a new H3 sibling: `### v0.3.0 → v0.4.0 deprecation` OR as a top-level H2 if the section warrants it — executor decides based on the existing heading hierarchy. (The CONTEXT D-11 wording "`## v0.3.0 → v0.4.0 deprecation`" suggests H2.)

The section body, in writing-with-codebase voice (FR/EN mix per existing CLAUDE.md style), MUST cover D-11's four points:

```markdown
## v0.3.0 → v0.4.0 deprecation

### Pourquoi ce changement

La couche de transition v0.2.0 (`merge_with_manual` + sections plates `*.items`)
est retirée. À partir de v0.4.0, les générateurs purs de
`arrconf/generators/categories.py` sont la **seule source** pour 12 ressources
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
`arrconf apply` exit code 2 avec une `ValidationError` pydantic du type :

```
arrconf.exceptions.ConfigError: Config validation error in
  /etc/arrconf/arrconf.yml:
  1 validation error for RootConfig
  sonarr.main.tags.items
    Extra inputs are not permitted [type=extra_forbidden, ...]
```

Le path `sonarr.main.tags.items` pointe la ligne à supprimer.

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

<!-- Snapshot capture command (D-14, ADR-6) -->

The pre-merge snapshot is OPERATOR action (no API key available in CI), captured BEFORE the PR merges to main:

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
    - .planning/phases/12-categories-deprecation/12-A-reconciler-refactor-SUMMARY.md (confirm the actual code state Plan A landed — the doc must reflect reality, not the plan)
    - .planning/phases/12-categories-deprecation/12-B-pydantic-yaml-schema-SUMMARY.md (confirm the exact YAML paths deleted — must match the doc verbatim)
  </read_first>
  <action>
    Insert the markdown section in `<interfaces>` block above into `CLAUDE.md`. Placement rule:

    1. Find the line in CLAUDE.md that closes the `### Release pin co-bump pattern` subsection (or the parent `## Conventions développement — arrconf` if structure suggests H2 placement). Use `grep -n "^###\|^##" CLAUDE.md | head -30` to map the heading structure first.

    2. The CONTEXT D-11 says `## v0.3.0 → v0.4.0 deprecation` (H2). Insert at H2 level immediately after the closing of `## Conventions développement — arrconf` (the parent section), OR at H3 level under it (executor decides based on which placement preserves the existing TOC flow better — both are acceptable as long as the heading reads `v0.3.0 → v0.4.0 deprecation`).

    3. Copy the markdown block from `<interfaces>` VERBATIM as the new section content. The verbatim list of 11 deleted paths MUST match Plan B's SUMMARY.

    4. Update the `**État actuel**` line at the very top of CLAUDE.md (if it currently references "milestone v0.3.0 — Categories first-class livré") to add a forward-reference: append `Phase 12 deprecation livré — flat sections retirées de arrconf.yml, generators sont la seule source.` to the existing sentence. Keep the rest of the line intact.
  </action>
  <verify>
    <automated>
      cd /data/projets/perso/arr-stack && \
      grep -q "## v0.3.0 → v0.4.0 deprecation\|### v0.3.0 → v0.4.0 deprecation" CLAUDE.md ; \
      grep -q "sonarr.main.tags.items" CLAUDE.md ; \
      grep -q "jellyfin.main.libraries.items" CLAUDE.md ; \
      grep -q "seerr.main.sonarr_service.animeTags" CLAUDE.md ; \
      grep -q "qbittorrent.main.categories.items" CLAUDE.md ; \
      grep -q "extra_forbidden\|Extra inputs are not permitted" CLAUDE.md ; \
      grep -q "merge_with_manual" CLAUDE.md ; \
      grep -q "arrconf/generators/categories.py" CLAUDE.md ; \
      echo "DOC OK"
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "v0.3.0 → v0.4.0 deprecation" CLAUDE.md` exits 0
    - `grep -q "sonarr.main.tags.items" CLAUDE.md` exits 0 (verbatim path #1 present)
    - `grep -q "jellyfin.main.libraries.items" CLAUDE.md` exits 0 (verbatim path #11 present)
    - `grep -q "seerr.main.sonarr_service.animeTags" CLAUDE.md` exits 0
    - `grep -q "qbittorrent.main.categories.items" CLAUDE.md` exits 0
    - `grep -qE "extra_forbidden|Extra inputs are not permitted" CLAUDE.md` exits 0 (sample ValidationError present)
    - `grep -q "merge_with_manual" CLAUDE.md` exits 0 (deprecation context mentions the removed function)
    - The new section sits AFTER the `### Release pin co-bump pattern` section (verify by `awk '/^###?\s+Release pin co-bump/,/^### v0\.3\.0|^## v0\.3\.0/' CLAUDE.md | wc -l` returns > 0 lines)
  </acceptance_criteria>
  <done>CLAUDE.md gains the deprecation section with all 4 D-11 contents; the verbatim path list matches Plan B's actual edits; placement respects existing heading hierarchy.</done>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task D.2 (HUMAN): Capture pre-merge cluster snapshot</name>
  <what-built>
    The CLAUDE.md deprecation section is committed in Task D.1. Plans A/B/C have landed code/YAML/schema/test changes. Before merging the phase PR, the operator must capture the live cluster's API state as the SC#5 baseline.
  </what-built>
  <how-to-verify>
    Operator runs the following from the arr-stack repo root. Each step is non-skippable.

    1. Confirm cluster connectivity:
       ```bash
       kubectl -n selfhost get pods | grep -E "sonarr|radarr|prowlarr|qbittorrent|jellyfin|seerr"
       ```
       All 6 pods MUST show `Running`.

    2. Export secrets from the operator's local secret stash (or copy from `kubectl get secret arrconf-env -n selfhost -o yaml | grep -A6 data` after `base64 -d`):
       ```bash
       export SONARR_API_KEY=<value>
       export RADARR_API_KEY=<value>
       export PROWLARR_API_KEY=<value>
       export JELLYFIN_API_KEY=<value>
       export SEERR_API_KEY=<value>
       export QBT_USER=<value>
       export QBT_PASS=<value>
       ```

    3. Set up port-forwards (one terminal per app, or use a multiplexer):
       ```bash
       kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
       kubectl -n selfhost port-forward svc/radarr 7878:7878 &
       kubectl -n selfhost port-forward svc/prowlarr 9696:9696 &
       kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
       kubectl -n selfhost port-forward svc/jellyfin 8096:8096 &
       kubectl -n selfhost port-forward svc/seerr 5055:5055 &
       ```

    4. Capture snapshot:
       ```bash
       DATE=$(date +%F)
       tools/snapshot/snapshot.sh --output snapshots/before-phase-12-${DATE}/
       ```

    5. Verify redaction (post-Phase-6 fix should be in effect; manual safety check):
       ```bash
       grep -rniE "(api[-_]?key|password|passkey|token).*:.*[a-z0-9]{16,}" snapshots/before-phase-12-${DATE}/ || echo "REDACTION CLEAN"
       ```
       Output MUST be `REDACTION CLEAN` (no real secrets found). If real secret-looking strings appear, manually redact before commit.

    6. Confirm `arrconf apply --dry-run` (run against port-forwarded URLs) produces a stable plan_action log (this is the pre-Phase-12 baseline behavior):
       ```bash
       cd tools/arrconf && uv run arrconf apply \
         --config ../../charts/arr-stack/files/arrconf.yml --dry-run \
         > ../../snapshots/before-phase-12-${DATE}/dry-run-plan-actions.log 2>&1
       ```
       (At this point the operator is on the new code — Plan A's signature refactor is already merged locally. The dry-run is the "what plan_action will the post-deprecation code emit AGAINST the current cluster state" measurement.)

    7. Stage + commit (NOT push — push happens with the full PR):
       ```bash
       git add snapshots/before-phase-12-${DATE}/
       git status
       git commit -m "snapshot(12): pre-merge cluster baseline for SC#5 (ADR-6, D-14)"
       ```

    8. Report back: paste the output of `ls snapshots/before-phase-12-${DATE}/` (file count) and `cat snapshots/before-phase-12-${DATE}/dry-run-plan-actions.log | tail -20` (the operator's confidence anchor before merging).
  </how-to-verify>
  <resume-signal>
    Reply `approved` after the snapshot is committed and the dry-run log captured. Reply `redaction-failure: <details>` if step 5 surfaces unredacted secrets — that blocks the PR until snapshot.sh is patched.
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator laptop ↔ cluster API | Port-forwarded HTTPS/HTTP; API keys flow as headers. |
| snapshot.sh stdout → committed JSON | Built-in redaction is the trust gate against secret leak (ADR-6). |
| CLAUDE.md → future-operator (future user, future fork) | Documentation accuracy = mitigation against repeating v0.3.0→v0.4.0 confusion. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-12D-01 | Information Disclosure | snapshot capture | mitigate | `tools/snapshot/snapshot.sh` already includes post-Phase-6 password+API-key redaction. Task D.2 step 5 enforces a re-grep audit before commit (operator gate). |
| T-12D-02 | Tampering | CLAUDE.md edit | mitigate | Doc lands as part of the PR; reviewer (= user, same person) cross-checks against actual code state via the SUMMARY references. |
| T-12D-03 | Repudiation | snapshot vs Plan E after-snapshot | mitigate | `snapshots/before-phase-12-DATE/` committed before merge; Plan E captures `snapshots/after-phase-12-DATE/` post-merge; `diff -r` between them is the dispositive SC#5 evidence. |
| T-12D-04 | Denial of Service | port-forward + snapshot | accept | Single-operator workflow; if a port-forward dies mid-snapshot, operator restarts. No production impact. |
| T-12D-05 | Spoofing | None applicable | n/a | Snapshot is read-only against cluster APIs; no PUT/POST issued. |
</threat_model>

<verification>
- `grep -q "v0.3.0 → v0.4.0 deprecation" CLAUDE.md` exits 0
- `ls snapshots/before-phase-12-*/` lists ≥ 6 subdirectories (one per app)
- `cat snapshots/before-phase-12-*/dry-run-plan-actions.log | grep -E "ValidationError|missing_api_key"` returns ZERO matches (the YAML loaded cleanly under the new shape)
- The snapshot diff vs `snapshots/post-phase2.2-hotfix-*` (most recent prior snapshot) shows ONLY expected drift (Phase 11+ Categories resources, no surprise mutations)
</verification>

<success_criteria>
- SC#4 (CLAUDE.md deprecation section) — SATISFIED by Task D.1.
- SC#5 prerequisite (before-snapshot for diff) — SATISFIED by Task D.2.
- D-11, D-12, D-13, D-14 closed in this plan.
</success_criteria>

<output>
After completion, create `.planning/phases/12-categories-deprecation/12-D-docs-snapshot-SUMMARY.md` documenting:
- Confirmation CLAUDE.md section landed at the chosen heading level
- Path to the committed `snapshots/before-phase-12-DATE/` directory
- File count of the snapshot directory
- Last 20 lines of the captured dry-run log
- Confirmation that redaction grep returned `REDACTION CLEAN`
</output>
