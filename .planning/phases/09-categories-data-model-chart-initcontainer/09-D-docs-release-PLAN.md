---
phase: 09-categories-data-model-chart-initcontainer
plan: 09-D-docs-release
type: execute
wave: 2
depends_on:
  - 09-A-python-schema
  - 09-B-helm-job
  - 09-C-arrconf-yml-tests
files_modified:
  - CLAUDE.md
  - charts/arr-stack/values.yaml
autonomous: true
requirements:
  - REQ-filesystem-operator-migration
requirements_addressed:
  - REQ-filesystem-operator-migration
tags:
  - documentation
  - release
  - chart-pin

# NOTE (W-06 — informational, do NOT split this plan): Plan D could in principle
# split into Wave 1 (CLAUDE.md only) + Wave 2 (values.yaml + atomic close), but the
# 4-plan/2-wave shape is preferred for clarity. Re-evaluate in retro if the wave-2
# critical path becomes a bottleneck.

must_haves:
  truths:
    - "CLAUDE.md has a new section '## Filesystem migration: v0.2.0 flat → v0.3.0 Categories' placed AFTER '## Pattern single-instance + tags' and BEFORE '## Intégration avec my-kluster'."
    - "The new section contains the 6-row v0.2.0 dir → v0.3.0 dir(s) mapping table from 09-CONTEXT.md §D-17 (verified against actual arrconf.yml line refs by 09-RESEARCH.md §'Operator Migration Runbook')."
    - "The section documents the 5-step runbook: Pre-check (snapshot), Mapping table, Execution (kubectl exec deployment/jellyfin), Post-check (Sonarr/Radarr rescan POST + snapshot diff), Rollback (inverse mv)."
    - "charts/arr-stack/values.yaml#arrconf.image.tag is pre-bumped to v0.5.3 — the next patch tag computed from current latest tag v0.5.2 + chart-lint.yml default_bump: patch (CF-07-CHART-PIN-LOOP — reduces my-kluster targetRevision bumps from 2 to 1 per phase release)."
    - "Single-commit atomicity for the Phase 9 release is enforced by the execute-phase orchestrator's git workflow, NOT by Plan D tasks. Plan D's job is to leave the working tree in a state where the orchestrator can commit all Phase 9 artifacts together."
  artifacts:
    - path: "CLAUDE.md"
      provides: "Operator filesystem migration runbook"
      contains: "## Filesystem migration: v0.2.0 flat → v0.3.0 Categories"
    - path: "charts/arr-stack/values.yaml"
      provides: "Pre-bumped arrconf.image.tag for CF-07-CHART-PIN-LOOP closure"
      contains: "tag:"
  key_links:
    - from: "CLAUDE.md (new section)"
      to: "tools/snapshot/snapshot.sh"
      via: "Pre-check step invokes snapshot.sh --output snapshots/before-categories-migration-$(date +%F)/ (ADR-6 discipline)"
      pattern: "tools/snapshot/snapshot\\.sh"
    - from: "charts/arr-stack/values.yaml (arrconf.image.tag)"
      to: ".github/workflows/chart-lint.yml (mathieudutour/github-tag-action job)"
      via: "Pre-bumped tag matches the value the auto-tag action will create on merge — single my-kluster Renovate PR cycle (CF-07-CHART-PIN-LOOP closure)"
      pattern: "tag:"
---

<objective>
Close Phase 9 with two operator-facing deliverables: the filesystem migration runbook in CLAUDE.md (REQ-filesystem-operator-migration) and the pre-bumped `arrconf.image.tag` in `charts/arr-stack/values.yaml` (CF-07-CHART-PIN-LOOP closure pilot).

Purpose: Without Plan D, Phase 9 ships but operators have no documented path to migrate v0.2.0 flat dirs to v0.3.0 Categories, and the my-kluster Renovate cycle produces 2 PRs (one for the auto-tag, one for the image.tag bump). Plan D makes Phase 9 operationally complete and demonstrates the CF-07-CHART-PIN-LOOP fix that Phase 10's REQ-chart-pin-prebump will formalize.

Output:
- `CLAUDE.md` (MODIFIED — new `## Filesystem migration: v0.2.0 flat → v0.3.0 Categories` section)
- `charts/arr-stack/values.yaml` (MODIFIED — single-line `arrconf.image.tag` bump at line ~451)

D-NN coverage (locked decisions implemented):
- **D-17** — Operator runbook with the exact title, the 6-row mapping table, and the 5-step runbook structure (Pre-check + Mapping + Execution + Post-check + Rollback). NO bash helper script.

Carry-forward closure:
- **CF-07-1 (D-07-CHART-PIN-LOOP)** — Phase 9 is the pilot for the pre-bump pattern. Phase 10's REQ-chart-pin-prebump documents the pattern in the executor-agent prompt; Phase 9 ships the pattern in practice. After Phase 9 merges, the operator follows up with a SINGLE Renovate PR in my-kluster bumping `targetRevision` (not 2).

**Boundary (CRITICAL):** Plan D does NOT cut the release tag — that is the operator's manual step OR `mathieudutour/github-tag-action` running automatically on push to `main`. Plan D ALSO does NOT bump `my-kluster/argocd/argocd-apps/arr-stack-app.yaml#targetRevision` — that is the Renovate auto-PR or the operator's manual follow-up. Plan D's scope ends at the arr-stack PR merge (which contains all Phase 9 deltas atomically, with atomicity enforced by the execute-phase orchestrator's git workflow).

The MANDATORY ADR-6 snapshot (`tools/snapshot/snapshot.sh --output snapshots/before-phase-9-2026-05-18/`) is the operator's step BEFORE merging the Phase 9 release to my-kluster — it is documented in 09-VALIDATION.md "Manual-Only Verifications" row 4 and re-asserted in CLAUDE.md's new section's Pre-check step.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-CONTEXT.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-RESEARCH.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-PATTERNS.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-VALIDATION.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-A-python-schema-PLAN.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-B-helm-job-PLAN.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-C-arrconf-yml-tests-PLAN.md
@CLAUDE.md
@charts/arr-stack/values.yaml
@tools/snapshot/snapshot.sh

<interfaces>
<!-- Reference shape — CLAUDE.md new section follows existing section conventions; values.yaml change is a single-line tag bump. -->

From `CLAUDE.md` — the existing `## Pattern single-instance + tags` section anchor (where the new section is inserted AFTER):

```markdown
## Pattern single-instance + tags (architecture Sonarr/Radarr)

Décision spec ADR-7 : **1 seule instance Sonarr et 1 seule Radarr**, différenciation TV / Anime / Family via tags.

**Implications pour arrconf** :
- ...
```

And the existing `## Intégration avec my-kluster` section anchor (where the new section is inserted BEFORE):

```markdown
## Intégration avec my-kluster (post-Phase 4)

- **Une seule** ArgoCD Application (`my-kluster/argocd/argocd-apps/arr-stack-app.yaml`) pointe vers ce repo, ...
```

The new section MUST land between these two anchors.

From `charts/arr-stack/values.yaml` lines 446-452 (the current `arrconf.image.tag` pin — the line to bump):

```yaml
containers:
  main:
    image:
      # renovate: image=ghcr.io/tom333/arr-stack-arrconf
      repository: ghcr.io/tom333/arr-stack-arrconf
      tag: "0.5.0"
      pullPolicy: IfNotPresent
```

**IMPORTANT — pre-existing drift (B-01 finding):** The chart was pinned at `tag: "0.5.0"` but the cluster currently runs from v0.5.2 (verified at planning time via `git tag --sort=-version:refname | head -1` → `v0.5.2`). The Phase 9 release commit corrects this drift by pinning to **`tag: "0.5.3"`** — the value the auto-tag action will newly create. The 0.5.0 → 0.5.3 jump is intentional and documents the catch-up.

**Computing the next auto-tag (DEFINITIVE — per chart-lint.yml verification at planning time):**

- Latest git tag: `v0.5.2` (confirmed `git tag --sort=-version:refname | head -1`)
- `.github/workflows/chart-lint.yml` line 164: `default_bump: patch` for `mathieudutour/github-tag-action@v6.2`
- Therefore the next auto-tag will be **`v0.5.3`** (patch bump, NOT minor).
- The chart pin Phase 9 must write is therefore `tag: "0.5.3"` (without the `v` prefix per existing chart convention).

There is NO discretion here. The auto-tag action's `default_bump: patch` is unconditional regardless of commit-message prefix. Do NOT bump to 0.6.0 or any minor/major variant — the auto-tag action will create v0.5.3 and the chart MUST match that exactly to close CF-07-CHART-PIN-LOOP in a single commit.

From 09-CONTEXT.md §D-17 — the EXACT 6-row mapping table (verbatim from CONTEXT.md lines 211-217, refined in 09-RESEARCH.md §"Operator Migration Runbook" lines 758-767):

| v0.2.0 dir | v0.3.0 dir(s) | Operator action |
|------------|---------------|------------------|
| `/media/series` | `/media/series` (default) + selective `mv` to `/media/series-emilie`, `/media/series-thomas`, `/media/series-garcons` | Operator manually moves Émilie's, Thomas's, and the boys' series subdirs into their named buckets. The rest stays in `/media/series`. |
| `/media/anime` | `/media/series-zoe` (Zoé's anime is the bulk of this) | Move the contents wholesale. If any non-Zoé anime is in here, the operator decides where it goes (most likely back to `/media/series`). |
| `/media/family` | `/media/series-garcons` (the family-rated kids' series bucket) | Move wholesale to the boys' bucket. |
| `/media/films` | `/media/films` (default) + selective `mv` to `/media/nouveaux-films` | Bulk stays; operator moves "newly-added" films per their own definition. |
| `/media/films-anime` | `/media/films-zoe` (Zoé's films) + `/media/films-animation-enfants` | Split by operator judgment: Studio Ghibli → Zoé; Disney/Pixar → enfants. |
| `/media/films-family` | `/media/films-enfants` | Rename, wholesale move. |

From 09-RESEARCH.md §"Operator Migration Runbook" — the verified Pre-check + Execution + Post-check + Rollback commands. The Execution step uses `kubectl exec -n selfhost -it deployment/jellyfin -- bash` because Jellyfin's pod already mounts the PVC at `/media` RW.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task D1: Add the '## Filesystem migration: v0.2.0 flat → v0.3.0 Categories' section to CLAUDE.md</name>
  <files>CLAUDE.md</files>
  <read_first>
    - CLAUDE.md (full file, especially the existing `## Pattern single-instance + tags` and `## Intégration avec my-kluster` section boundaries — these are the insertion anchors)
    - CLAUDE.md "Workflow snapshot" subsection (under `## Workflow de développement` — bash-code-block style template)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-CONTEXT.md §D-17 (the locked runbook shape)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-RESEARCH.md §"Operator Migration Runbook" lines 741-808 (the refined mapping table + executable commands, cross-checked against arrconf.yml line refs)
    - tools/snapshot/snapshot.sh (the pre-check tool used in Step 1 of the runbook)
  </read_first>
  <action>
    Open `CLAUDE.md` and locate two anchors:
    1. The END of `## Pattern single-instance + tags (architecture Sonarr/Radarr)` section.
    2. The START of `## Intégration avec my-kluster (post-Phase 4)` section.

    Insert the new section between these two anchors. The new section MUST follow this EXACT structure (sourced from 09-CONTEXT.md §D-17 + 09-RESEARCH.md §"Operator Migration Runbook" — both verbatim, no paraphrasing):

    ```markdown
    ---

    ## Filesystem migration: v0.2.0 flat → v0.3.0 Categories

    Procédure manuelle, opérateur-driven, à exécuter UNE FOIS après le merge du PR Phase 9 (qui crée les 10 nouveaux répertoires vides `/media/<name>`). arrconf n'orchestre PAS cette migration — il crée des répertoires vides et n'y touche jamais après.

    **Discipline ADR-6** : snapshot AVANT et APRÈS. Lossless, versionné dans Git.

    ### Mapping v0.2.0 → v0.3.0 (validé contre arrconf.yml 2026-05-18)

    | v0.2.0 dir | v0.3.0 dir(s) | Action opérateur |
    |------------|---------------|-------------------|
    | `/media/series` | `/media/series` (default) + `mv` sélectif vers `/media/series-emilie`, `/media/series-thomas`, `/media/series-garcons` | Déplacer manuellement les sous-dossiers d'Émilie, Thomas et des garçons dans leurs buckets nommés. Le reste reste dans `/media/series`. |
    | `/media/anime` | `/media/series-zoe` (l'anime de Zoé est le bulk de ce dossier) | Déplacer le contenu en wholesale. Si du non-Zoé anime existe, opérateur juge (souvent retour à `/media/series`). |
    | `/media/family` | `/media/series-garcons` (bucket family-rated kids' series) | `mv` wholesale vers le bucket des garçons. |
    | `/media/films` | `/media/films` (default) + `mv` sélectif vers `/media/nouveaux-films` | Le bulk reste ; opérateur déplace les "nouveaux" selon sa propre définition de date. |
    | `/media/films-anime` | `/media/films-zoe` (films de Zoé) + `/media/films-animation-enfants` | Split par jugement opérateur : Studio Ghibli → Zoé ; Disney/Pixar → enfants. |
    | `/media/films-family` | `/media/films-enfants` | Rename, `mv` wholesale. |

    ### Étape 1 — Pre-check (snapshot baseline)

    ```bash
    # Capture l'état API actuel des 6 apps (root_folders, library paths, etc.)
    tools/snapshot/snapshot.sh --output snapshots/before-categories-migration-$(date +%F)/
    git add snapshots/before-categories-migration-* && git commit -m "snapshot(pre-categories-migration): baseline"

    # Vérifier que les 10 nouveaux /media/<name> dirs existent (créés par le Job Phase 9 au helm upgrade) :
    kubectl exec -n selfhost deployment/jellyfin -- ls /media/ | sort | column
    # Attendu : films, films-animation-enfants, films-enfants, films-zoe, nouveaux-films,
    #           series, series-emilie, series-garcons, series-thomas, series-zoe
    #           (+ éventuellement les legacy v0.2.0 : anime, family, films-anime, films-family)
    ```

    ### Étape 2 — Execution (kubectl exec dans Jellyfin)

    Le pod Jellyfin monte déjà `media-nas-pvc` à `/media` en RW — pas besoin de pod de maintenance dédié.

    ```bash
    kubectl exec -n selfhost -it deployment/jellyfin -- bash

    # Dans le pod :
    cd /media
    mv anime/* series-zoe/ 2>/dev/null         # bulk anime → bucket Zoé
    mv family/* series-garcons/                # bulk family series → bucket garçons
    mv films-family/* films-enfants/           # bulk family films → bucket enfants

    # films-anime nécessite jugement opérateur :
    ls films-anime/ | head -20                 # eyeball le contenu
    # Exemple (Studio Ghibli → Zoé) :
    mv films-anime/Studio*Ghibli films-zoe/
    # Exemple (Disney/Pixar → enfants) :
    mv films-anime/Disney films-anime/Pixar films-animation-enfants/

    # series : split manuel (Émilie/Thomas/Garçons selon le contenu réel)
    # ex: mv series/<la-série-d-émilie> series-emilie/

    # films : split manuel (nouveaux selon date)
    # ex: mv films/<film-récent> nouveaux-films/

    exit
    ```

    ### Étape 3 — Post-check (rescan + diff snapshot)

    ```bash
    # 1. Déclencher un rescan Sonarr (sur les root_folders qui ont gagné/perdu du contenu) :
    curl -X POST -H "X-Api-Key: $SONARR_API_KEY" "http://sonarr.selfhost.svc.cluster.local:8989/api/v3/command" \
      -d '{"name":"RescanSeries"}'

    # 2. Idem Radarr :
    curl -X POST -H "X-Api-Key: $RADARR_API_KEY" "http://radarr.selfhost.svc.cluster.local:7878/api/v3/command" \
      -d '{"name":"RescanMovie"}'

    # 3. Snapshot après migration + diff :
    tools/snapshot/snapshot.sh --output snapshots/after-categories-migration-$(date +%F)/
    diff -r snapshots/before-categories-migration-*/ snapshots/after-categories-migration-*/
    # Attendu : changements sur paths root_folder / library PathInfos uniquement ;
    #          pas de drift sur tags, download_clients, ou notifications.
    ```

    ### Étape 4 — Rollback (si nécessaire)

    Le rollback est l'inverse des `mv` de l'Étape 2 — opérateur reconstitue manuellement à partir du snapshot pre-migration s'il identifie un fichier déplacé par erreur. Pas de script fourni : v0.3.0 garde le runbook high-trust, low-automation.

    ### Notes

    - arrconf est insensible à si la migration a été exécutée ou non. Il crée les 10 `/media/<name>` (vides) ; le contenu vient soit du `mv` opérateur, soit des futurs imports Sonarr/Radarr.
    - Les anciens dirs (`/media/anime`, `/media/family`, `/media/films-anime`, `/media/films-family`) restent intacts tant que l'opérateur ne les supprime pas — Phase 9 n'a aucune logique `rmdir`.
    - Pour supprimer un legacy dir une fois vidé : `rm -rf /media/anime` depuis le pod Jellyfin (opérateur, manuel).

    ---
    ```

    Locked elements:
    - Section title EXACTLY: `## Filesystem migration: v0.2.0 flat → v0.3.0 Categories` (the verification grep checks for this literal — D-17 + 09-VALIDATION.md row 5).
    - Insertion position: AFTER `## Pattern single-instance + tags` END, BEFORE `## Intégration avec my-kluster` START.
    - The 6-row mapping table comes verbatim from 09-CONTEXT.md §D-17 (refined by 09-RESEARCH.md).
    - The Pre-check Étape 1 invokes `tools/snapshot/snapshot.sh` — ADR-6 discipline is reinforced (not duplicated; the existing `## Workflow snapshot` section under `## Workflow de développement` keeps full discipline; this section only references it).
    - The Étape 2 Execution uses `kubectl exec deployment/jellyfin` (the only pod that mounts `media-nas-pvc` RW in selfhost namespace).
    - The Étape 3 Post-check uses real Sonarr / Radarr `POST /command` endpoints.
    - The Étape 4 Rollback is intentionally brief — operator-judgement (D-17 explicit).
    - DO NOT include code that creates a `tools/scripts/migrate-to-categories.sh` script — explicitly deferred by 09-CONTEXT.md §Deferred lines 477-479.

    After editing, verify the section appears correctly with the exact title:

    ```bash
    grep -F '## Filesystem migration: v0.2.0 flat → v0.3.0 Categories' CLAUDE.md
    grep -c '^| ' CLAUDE.md  # should have increased by 7 (6 data rows + 1 header) compared to before
    ```

    Do NOT modify any other CLAUDE.md section (no rewriting "Conventions Helm", no editing "Workflow snapshot", etc.). Plan D scope is the addition of one new section only.
  </action>
  <verify>
    <automated>grep -F '## Filesystem migration: v0.2.0 flat → v0.3.0 Categories' CLAUDE.md && grep -F 'snapshots/before-categories-migration-' CLAUDE.md && grep -F 'kubectl exec -n selfhost -it deployment/jellyfin' CLAUDE.md && grep -F 'mv anime/* series-zoe/' CLAUDE.md && grep -F 'mv family/* series-garcons/' CLAUDE.md && grep -F 'mv films-family/* films-enfants/' CLAUDE.md && grep -F 'films-zoe' CLAUDE.md && grep -F 'films-animation-enfants' CLAUDE.md && awk '/## Filesystem migration/,/## Intégration avec my-kluster/' CLAUDE.md | grep -c '^| ' | awk '$1 >= 7 { exit 0 } { exit 1 }'</automated>
  </verify>
  <acceptance_criteria>
    - `grep -F '## Filesystem migration: v0.2.0 flat → v0.3.0 Categories' CLAUDE.md` exits 0
    - `awk '/^## Pattern single-instance/,/^## Filesystem migration/' CLAUDE.md | tail -1 | grep -F 'Filesystem migration'` exits 0 (new section comes after Pattern single-instance)
    - `awk '/^## Filesystem migration/,/^## Intégration avec my-kluster/' CLAUDE.md | tail -1 | grep -F 'Intégration avec my-kluster'` exits 0 (new section comes before Intégration avec my-kluster)
    - `awk '/^## Filesystem migration/,/^## Intégration/' CLAUDE.md | grep -c '^| ' ` returns at least 7 (1 header + 6 data rows)
    - `grep -F 'snapshots/before-categories-migration-' CLAUDE.md` exits 0
    - `grep -F 'kubectl exec -n selfhost -it deployment/jellyfin' CLAUDE.md` exits 0
    - `grep -F 'tools/snapshot/snapshot.sh' CLAUDE.md` exits 0
    - `grep -F 'series-zoe' CLAUDE.md` exits 0
    - `grep -F 'films-animation-enfants' CLAUDE.md` exits 0
    - `grep -F 'RescanSeries' CLAUDE.md` exits 0
    - `grep -F 'RescanMovie' CLAUDE.md` exits 0
    - `grep -F 'tools/scripts/migrate-to-categories.sh' CLAUDE.md` exits 1 (this script is explicitly NOT documented — 09-CONTEXT.md §Deferred lines 477-479)
  </acceptance_criteria>
  <done>
    `CLAUDE.md` has a new `## Filesystem migration: v0.2.0 flat → v0.3.0 Categories` section between the Pattern single-instance + tags section and the Intégration avec my-kluster section. The section contains all 6 mapping rows (D-17 verbatim), the 4-step runbook (Pre-check + Execution + Post-check + Rollback), and references to `tools/snapshot/snapshot.sh` and `kubectl exec deployment/jellyfin`. No bash helper script is mentioned (explicitly deferred to v0.4.0+).
  </done>
</task>

<task type="auto">
  <name>Task D2: Pre-bump charts/arr-stack/values.yaml#arrconf.image.tag from "0.5.0" to "0.5.3" (CF-07-CHART-PIN-LOOP closure pilot)</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    - charts/arr-stack/values.yaml (lines 446-452 — the `arrconf.controllers.main.containers.main.image` block to bump)
    - .github/workflows/chart-lint.yml (line ~164 — confirm `mathieudutour/github-tag-action@v6.2` with `default_bump: patch`)
    - .planning/STATE.md §"CF-07-1 (D-07-CHART-PIN-LOOP)" — the carry-forward context
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-PATTERNS.md §"charts/arr-stack/values.yaml (MODIFIED — single-line image tag bump)" — confirms current pin is `tag: "0.5.0"` at line 451
  </read_first>
  <action>
    Phase 9 pilots the CF-07-CHART-PIN-LOOP closure pattern that REQ-chart-pin-prebump (Phase 10) will formalize: bump `arrconf.image.tag` in the SAME commit as the rest of Phase 9 so the auto-tag action produces a chart whose pinned image matches the tag it just cut.

    **Sub-step 1 — Verify the tag-math inputs (DO NOT improvise; these are facts captured at planning time):**

    ```bash
    # Confirm latest existing tag is v0.5.2:
    git tag --sort=-version:refname | head -1
    # Expected: v0.5.2

    # Confirm auto-tag action's bump policy is patch:
    grep -A5 'mathieudutour/github-tag-action' .github/workflows/chart-lint.yml | grep default_bump
    # Expected: "default_bump: patch"
    ```

    If either assertion fails at execution time, STOP and surface the discrepancy — the precomputed target (`tag: "0.5.3"`) is only correct under both conditions.

    **Sub-step 2 — Compute next tag (DEFINITIVE).**

    - Current latest tag at planning time: **v0.5.2** (verified by `git tag --sort=-version:refname | head -1` on 2026-05-18).
    - `chart-lint.yml` `default_bump: patch` for `mathieudutour/github-tag-action@v6.2` (line ~164).
    - Therefore the next auto-tag the action will create on merge of the Phase 9 PR is **v0.5.3** (patch bump, NOT minor — the action's bump policy is unconditional regardless of commit-message prefix).
    - Phase 9 commit pins to **`tag: "0.5.3"`** (without the `v` prefix per existing chart convention).

    **Pre-existing drift (DOCUMENT IT, do NOT silently fix):** The chart was pinned at `tag: "0.5.0"` while the cluster runs from v0.5.2. The Phase 9 release commit corrects this drift by pinning to v0.5.3 — the value the auto-tag action will newly create. The 0.5.0 → 0.5.3 jump is intentional and the SUMMARY.md must call this out (latest existing tag, next auto-tag value, pre-existing drift, the catch-up nature of this bump).

    **Sub-step 3 — Edit the file.** Open `charts/arr-stack/values.yaml`, locate line 451:

    ```yaml
            image:
              # renovate: image=ghcr.io/tom333/arr-stack-arrconf
              repository: ghcr.io/tom333/arr-stack-arrconf
              tag: "0.5.0"
              pullPolicy: IfNotPresent
    ```

    Change `tag: "0.5.0"` to `tag: "0.5.3"`. Do NOT modify anything else (no other line, no comment, no quoting style).

    Final shape:

    ```yaml
            image:
              # renovate: image=ghcr.io/tom333/arr-stack-arrconf
              repository: ghcr.io/tom333/arr-stack-arrconf
              tag: "0.5.3"
              pullPolicy: IfNotPresent
    ```

    **Sub-step 4 — Verify chart still renders.** Run:

    ```bash
    helm lint charts/arr-stack/ -f examples/values-prod.yaml
    helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas
    # And confirm the new tag appears in the rendered arrconf CronJob:
    helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -F 'image: ghcr.io/tom333/arr-stack-arrconf:0.5.3'
    ```

    All three MUST exit 0 / produce a match. If the third command returns no match, the bump didn't propagate to the rendered manifest — re-verify the edit.

    **Sub-step 5 — Commit atomically.** Single-commit atomicity for the Phase 9 release is enforced by the **GSD execute-phase orchestrator's git workflow**, NOT by Plan D tasks. Plan D's responsibility is to leave the working tree staged correctly so the orchestrator can commit:
    - Plan A artifacts (`tools/arrconf/arrconf/resources/categories.py`, `arrconf/config.py`, `tests/test_categories.py`, `schemas/arrconf-schema.json`)
    - Plan B artifact (`charts/arr-stack/templates/categories-init-job.yaml`)
    - Plan C artifacts (`charts/arr-stack/files/arrconf.yml`, `tests/_phase9_helpers.py`, `tests/test_arrconf_yml_validates.py`, `tests/test_phase9_no_regression.py`, `tests/fixtures/phase9-baseline-plans.json`)
    - Plan D artifacts (`CLAUDE.md`, `charts/arr-stack/values.yaml`)
    - The 4 SUMMARY.md files

    Single-commit shape ensures the auto-tag action produces a tag whose chart already has the matching image pin (CF-07-CHART-PIN-LOOP closure).

    Note: this plan does NOT execute the actual `git commit` (that is the GSD execute-phase orchestrator's step). Plan D only ensures the values.yaml file is staged correctly.

    Operator FOLLOW-UP after this PR merges to main:
    1. Auto-tag action cuts the tag **v0.5.3** (patch bump from v0.5.2).
    2. arrconf-image.yml builds `ghcr.io/tom333/arr-stack-arrconf:0.5.3`.
    3. Renovate opens 1 PR on `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` bumping `targetRevision: v0.5.2 → v0.5.3`.
    4. Operator runs `tools/snapshot/snapshot.sh --output snapshots/before-phase-9-$(date +%F)/` BEFORE merging the Renovate PR (ADR-6 discipline + 09-VALIDATION.md row "Snapshot baseline taken BEFORE first Phase 9 cluster deploy").
    5. Operator merges Renovate PR; ArgoCD syncs; Job runs and emits 10 `media_dir_ensured` JSON lines.
  </action>
  <verify>
    <automated>grep -F 'repository: ghcr.io/tom333/arr-stack-arrconf' charts/arr-stack/values.yaml && grep -F 'tag: "0.5.3"' charts/arr-stack/values.yaml && helm lint charts/arr-stack/ -f examples/values-prod.yaml && helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas && helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -F 'image: ghcr.io/tom333/arr-stack-arrconf:0.5.3'</automated>
  </verify>
  <acceptance_criteria>
    - `grep -F 'tag: "0.5.3"' charts/arr-stack/values.yaml` exits 0 (exact-match assertion — B-01 fix)
    - `grep -B3 'tag: "0.5.3"' charts/arr-stack/values.yaml | grep -F 'ghcr.io/tom333/arr-stack-arrconf'` exits 0 (bumped tag is the one under arrconf image, not a different image)
    - `grep -B3 'tag: "0.5.3"' charts/arr-stack/values.yaml | grep -F '# renovate: image=ghcr.io/tom333/arr-stack-arrconf'` exits 0 (renovate annotation preserved — CLAUDE.md "Ne pas supprimer l'annotation # renovate: image=...")
    - `helm lint charts/arr-stack/ -f examples/values-prod.yaml` exits 0
    - `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas` exits 0
    - `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -F 'image: ghcr.io/tom333/arr-stack-arrconf:0.5.3'` exits 0
    - `git diff charts/arr-stack/values.yaml | grep -E '^\+\s*tag: "0\.5\.3"'` exits 0 (the diff is the tag bump line)
    - `git diff charts/arr-stack/values.yaml | grep -E '^\-\s*tag: "0\.5\.0"'` exits 0 (the diff removed the stale 0.5.0)
  </acceptance_criteria>
  <done>
    `charts/arr-stack/values.yaml#arrconf.image.tag` is pre-bumped from `"0.5.0"` to `"0.5.3"` — the value the next auto-tag action will produce (patch bump from latest tag v0.5.2 per chart-lint.yml `default_bump: patch`). Pre-existing drift (chart was at 0.5.0 while cluster runs v0.5.2) is caught up in the same edit. Chart lints + kubeconforms clean. The Renovate annotation remains untouched. The bump lands in the same commit as all other Phase 9 deliverables (atomicity enforced by the execute-phase orchestrator), demonstrating the CF-07-CHART-PIN-LOOP closure pattern and reducing the my-kluster follow-up to a single Renovate PR.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLAUDE.md (committed docs) → operator running runbook | Operator copies bash commands from CLAUDE.md and pastes into `kubectl exec`. Any malicious command in the doc could be executed without review. |
| `charts/arr-stack/values.yaml#arrconf.image.tag` → ArgoCD pull → kubelet image pull from GHCR | The pinned tag value must match a built image. A wrong tag means the CronJob fails to start. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09D-01 | Tampering | Malicious bash command added to the migration runbook (e.g. `rm -rf /media/*`) | mitigate | All bash commands in the new section are taken verbatim from 09-CONTEXT.md §D-17 + 09-RESEARCH.md §"Operator Migration Runbook". PR review catches any deviation. The runbook commands explicitly use `mv` (no `rm -rf`), preserve directories (no `--no-preserve-root`), and operate inside `/media` (no path escapes). |
| T-09D-02 | Information Disclosure | Runbook leaks API keys | N/A | The `curl` commands reference `$SONARR_API_KEY` and `$RADARR_API_KEY` env vars, not literal keys. Operator's shell environment holds the secrets (per CLAUDE.md "Variables d'environnement"). |
| T-09D-03 | Tampering | Operator pre-bumps the tag to a value that doesn't match what the auto-tag action will create | mitigate | Task D2 hardcodes `tag: "0.5.3"` derived from verified facts (latest tag = v0.5.2 + chart-lint.yml `default_bump: patch`). Sub-step 1 re-verifies both inputs at execution time; if either changed since planning, the executor stops and surfaces the discrepancy. The chart render check (Sub-step 4) provides a third guard: a wrong tag produces an ImagePullBackOff in the cluster, immediately visible. |
| T-09D-04 | Repudiation | Pre-bump tag is wrong but the PR merges anyway | mitigate | The PR review catches the discrepancy (the auto-tag value is computable from `git tag` + the action's config — both pinned in this plan). If it slips, the my-kluster Renovate PR will reference a non-existent image, ArgoCD shows `ImagePullBackOff`, operator rolls back via `git revert`. |
| T-09D-05 | Elevation of Privilege | Runbook tells operator to run a command that escalates | N/A | All commands run as the operator's normal user (no `sudo`, no `kubectl --as`, no privileged containers spawned). The `kubectl exec deployment/jellyfin` uses the existing pod's uid-1000 context. |
| T-09D-06 | Denial of Service | Migration `mv` commands take too long and stall Jellyfin | accept | `mv` on the same filesystem (NFS share is one filesystem) is metadata-only and near-instant. The operator runs the migration during a maintenance window. Even worst case: Jellyfin keeps serving its current library scan; rescan POST in Étape 3 picks up the changes. |
| T-09D-07 | Spoofing | Adversary forges a commit that looks like a tag bump but ships malicious image | mitigate | Git signature policy + branch protection rules on `main` (existing project posture). PR review catches image tag drift. |

**Zero HIGH-severity unmitigated threats.** The dominant Tampering vector (T-09D-01) is mitigated by the verbatim-copy discipline and PR review.
</threat_model>

<verification>
After both tasks complete:

```bash
# 1. CLAUDE.md section exists with correct shape
grep -F '## Filesystem migration: v0.2.0 flat → v0.3.0 Categories' CLAUDE.md
awk '/^## Filesystem migration/,/^## Intégration/' CLAUDE.md | grep -c '^| '   # >= 7
grep -F 'kubectl exec -n selfhost -it deployment/jellyfin' CLAUDE.md
grep -F 'tools/snapshot/snapshot.sh' CLAUDE.md

# 2. values.yaml tag was bumped to exactly 0.5.3
grep -F 'tag: "0.5.3"' charts/arr-stack/values.yaml

# 3. Chart still lints + kubeconforms
helm lint charts/arr-stack/ -f examples/values-prod.yaml
helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas

# 4. The bumped tag is rendered into the arrconf CronJob
helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -F 'image: ghcr.io/tom333/arr-stack-arrconf:0.5.3'
```

All four MUST succeed. If step 2 still shows `tag: "0.5.0"`, the bump didn't happen — re-run Task D2.
</verification>

<success_criteria>
- `CLAUDE.md` has a new `## Filesystem migration: v0.2.0 flat → v0.3.0 Categories` section with the 6-row mapping table, 4-step runbook, and ADR-6 snapshot discipline reinforced (REQ-filesystem-operator-migration).
- `charts/arr-stack/values.yaml#arrconf.image.tag` is pre-bumped to exactly `"0.5.3"` matching the next auto-tag the action will create on Phase 9 merge (CF-07-CHART-PIN-LOOP pilot closure).
- The bump lands in the SAME PR / commit as Plans A+B+C (atomicity enforced by the GSD execute-phase orchestrator's git workflow — Plan D does not itself commit).
- `helm lint` + `kubeconform` green; the rendered arrconf CronJob carries the new tag.
- After merge: 1 Renovate PR in my-kluster bumping `targetRevision` (not 2) — CF-07-CHART-PIN-LOOP closure pilot validated in production.
- Manual gate per 09-VALIDATION.md row "Snapshot baseline taken BEFORE first Phase 9 cluster deploy" is documented and re-asserted in the new CLAUDE.md section's Pre-check step.
</success_criteria>

<output>
After completion, create `.planning/phases/09-categories-data-model-chart-initcontainer/09-D-docs-release-SUMMARY.md` covering:
- Tasks executed (D1/D2)
- D-NN coverage table (D-17 fully implemented)
- CF-07-CHART-PIN-LOOP closure evidence: latest existing tag (v0.5.2), computed next tag (v0.5.3), bump type (patch — chart-lint.yml `default_bump: patch`), pre-existing drift caught up (chart was at 0.5.0 while cluster runs v0.5.2), the resulting `values.yaml` diff
- CLAUDE.md section diff (line count, exact title match)
- Manual cluster-time follow-up checklist for the operator:
  - [ ] Auto-tag action cut `v0.5.3`
  - [ ] arrconf-image.yml built `ghcr.io/tom333/arr-stack-arrconf:0.5.3`
  - [ ] Renovate PR in my-kluster bumping `targetRevision: v0.5.2 → v0.5.3`
  - [ ] `tools/snapshot/snapshot.sh --output snapshots/before-phase-9-$(date +%F)/` run + committed
  - [ ] Renovate PR merged; ArgoCD synced
  - [ ] Job emitted 10 `media_dir_ensured` JSON lines (`kubectl logs job/arr-stack-categories-init -n selfhost`)
  - [ ] All 10 `/media/<name>` dirs present (`kubectl exec -n selfhost deployment/jellyfin -- ls /media`)
- Phase 9 close-out: ROADMAP.md Phase 9 checklist tick + STATE.md update
</output>
