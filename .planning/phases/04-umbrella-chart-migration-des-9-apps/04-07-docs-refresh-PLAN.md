---
phase: 04-umbrella-chart-migration-des-9-apps
plan: 07
type: execute
wave: 5
depends_on: ["04-05"]  # W1 — Plan 07 produces no artifact Plan 06 needs; it can run in parallel with Plan 06 within wave 5 (Plan 06 also depends on 04-05). Plan 08 will depend on both 04-06 AND 04-07.
files_modified:
  - README.md
  - CLAUDE.md
autonomous: false
requirements:
  - REQ-readme-onboarding
tags: [docs, readme, claude-md, onboarding]
must_haves:
  truths:
    - "README.md is a full rewrite (no longer says `Statut: en cours de bootstrap (Phase 0)`) and contains sections: Vue d'ensemble, Stack overview, Prerequisites, Umbrella chart, Deploy, Operator runbook, Development, Liens"
    - "README.md walks a new operator from `git clone` to a first ArgoCD sync in under 30 minutes (REQ-readme-onboarding)"
    - "CLAUDE.md section `Structure cible` is renamed `Structure actuelle` and reflects the post-Phase-4 reality (no separate `templates/arrconf-cronjob.yaml` — app-template alias does the job; only `_helpers.tpl` + 2 ConfigMap templates in `templates/`)"
    - "CLAUDE.md section `Intégration avec my-kluster` is rewritten for the single ArgoCD App pull (`arr-stack-app.yaml` targetRevision points to this repo)"
    - "CLAUDE.md `Bootstrap (état actuel — 2026-05-07)` is archived/renamed `Historical bootstrap (Phase 0-3)` and kept for context"
    - "A human reviewer (the developer themselves) confirms onboarding flows in < 30 min via the checkpoint"
  artifacts:
    - path: "README.md"
      provides: "Onboarding-ready landing page (REQ-readme-onboarding)"
      min_lines: 80
    - path: "CLAUDE.md"
      provides: "Updated project conventions reflecting Phase 4 ground truth"
      min_lines: 380
  key_links:
    - from: "README.md Deploy section"
      to: "spec.md §9.2 (target arr-stack-app.yaml)"
      via: "Deploy section explains the my-kluster single-App pull pattern"
      pattern: "arr-stack-app.yaml"
    - from: "CLAUDE.md Structure actuelle"
      to: "charts/arr-stack/"
      via: "Section enumerates the actual on-disk layout produced by Plans 02-05"
      pattern: "templates/_helpers.tpl"
---

<objective>
Rewrite README.md (currently a 29-line bootstrap stub) and refresh the post-Phase-4-stale sections of CLAUDE.md (`Structure cible`, `Bootstrap (état actuel)`, `Intégration avec my-kluster`) to match the umbrella chart reality landing in Plans 02-06.

Purpose: D-04-DOCS-01 — full doc refresh, not targeted edits. REQ-readme-onboarding requires < 30 min onboarding which the current README cannot deliver. Anticipatory sections of CLAUDE.md were written before the chart existed and now contradict the actual layout (D-04-CRON-01 specifies the umbrella has only `_helpers.tpl` + 2 ConfigMap templates, NOT the four `arrconf-cronjob.yaml` / `arrconf-configmap.yaml` / `configarr-cronjob.yaml` / `configarr-configmap.yaml` files the old CLAUDE.md listed).

Output: A rewritten README.md and a refactored CLAUDE.md, both reviewed by the operator.
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
@.planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md
@README.md
@CLAUDE.md
@spec.md

<interfaces>
<!-- README target outline (PATTERNS.md §"README.md (rewritten)" + REQ-readme-onboarding) -->

# arr-stack

1. Vue d'ensemble (1 paragraph: what it is + what it deploys + how it works)
2. Stack overview table (apps + versions + ports)
3. Prerequisites (kubectl, helm, argocd CLI or fallback, my-kluster repo access)
4. Umbrella chart usage (helm lint, helm template, helm template | kubeconform — local dev loop)
5. Déploiement (how a release reaches the cluster: git tag → Renovate PR my-kluster → ArgoCD sync)
6. Operator runbook (snapshot.sh discipline, cutover history pointer, rollback = git revert)
7. Développement (arrconf Python dev loop — pytest/ruff/uv; chart dev loop)
8. Snapshot rapide (preserved from current README — still relevant)
9. Liens (spec.md, CLAUDE.md, .planning/, my-kluster)

<!-- CLAUDE.md sections to rewrite (PATTERNS.md §"CLAUDE.md (rewritten)") -->

| Section                                   | Action                                      |
| Vue d'ensemble                             | Update "État actuel: phase spec/bootstrap"  → "État actuel: Phase 4 closed, umbrella chart en place"  |
| Structure cible                            | Rename → Structure actuelle. Replace anticipatory tree with ACTUAL post-Phase-4 layout (no separate cronjob templates) |
| Conventions Helm — umbrella chart          | KEEP. Renovate annotation rules + dependencies pattern still authoritative. |
| Intégration avec my-kluster                | Rewrite: one ArgoCD App `arr-stack` pulling this repo (cite Plan 08 cutover); remove the "5 fichiers ... à supprimer" futurology |
| Comment ajouter une nouvelle app à arrconf | Add note: "+ alias dans Chart.yaml + values.yaml" |
| Ce que tu NE dois PAS faire                | Add: "Ne pas oublier l'alias dans Chart.yaml + values.yaml + Renovate annotation" |
| Bootstrap (état actuel — 2026-05-07)       | Rename → Historical bootstrap (Phase 0-3). Keep as archive section. |

KEEP UNCHANGED: Stack technique, Conventions développement — arrconf, Workflow snapshot, Frontière arrconf / configarr, Pattern single-instance + tags, GSD intégration, Références.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 7.1: Rewrite README.md for post-Phase-4 onboarding (REQ-readme-onboarding)</name>
  <files>README.md</files>
  <read_first>
    README.md (current stub — keep the "Snapshot rapide" section, replace the rest)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"README.md (rewritten)" (target structure outline)
    spec.md §9.2 (target arr-stack-app.yaml example to reference from Deploy section)
    CLAUDE.md (project conventions to cross-reference)
  </read_first>
  <action>
    Replace the contents of `README.md` with a new file matching the outline in `<interfaces>` above. Keep the "Snapshot rapide" section verbatim from the current README (still relevant for the runbook).

    Key content requirements:
    - **Vue d'ensemble**: One paragraph: arr-stack = umbrella Helm chart packaging Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/FlareSolverr/Cleanuparr/Jellyfin/arrconf/configarr; deployed by one ArgoCD Application in `my-kluster`; arrconf is a Python CronJob reconciling REST APIs from YAML; configarr handles TRaSH-Guides.
    - **Stack overview**: Markdown table with 10 rows (alias name, image repo, current pinned tag, port). Source the tags from `charts/arr-stack/values.yaml` to keep them in sync.
    - **Prerequisites**: list `kubectl >= 1.28`, `helm >= 3.x` (Helm v4.x binary = Helm 3 CLI per RESEARCH §Standard Stack), `argocd` CLI (optional — fallback to `kubectl get application ...` documented), Python 3.13 + `uv` for arrconf dev.
    - **Umbrella chart usage**: 4 commands operator can run locally to validate:
      ```bash
      helm repo add bjw-s-labs https://bjw-s-labs.github.io/helm-charts
      helm dependency update charts/arr-stack/
      helm lint charts/arr-stack/ -f examples/values-prod.yaml
      helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas -kubernetes-version 1.33.0
      ```
    - **Déploiement**: Diagram-or-list of the 3-hop chain — (a) PR in arr-stack merges → tag git release `vX.Y.Z`; (b) Renovate opens a PR in `my-kluster` bumping `arr-stack-app.yaml` `targetRevision`; (c) operator merges → ArgoCD auto-syncs. Explicitly say **deployment is never done from this repo** (CLAUDE.md rule). Cite REQ-pr-to-cluster-latency < 1h target.
    - **Operator runbook**:
      - Before risky changes → `tools/snapshot/snapshot.sh` (ADR-6).
      - Cutover history (Phase 4) → pointer to `.planning/phases/04-*/04-08-cutover-SUMMARY.md`.
      - Rollback → `git revert` the my-kluster PR (D-04-CUTOVER-04).
    - **Développement**:
      - arrconf Python loop: `cd tools/arrconf; uv sync; pytest -v --cov=arrconf; ruff check; mypy .`.
      - Chart loop: same 4 helm commands as above + `tools/scripts/check-renovate-annotations.sh charts/arr-stack/values.yaml`.
    - **Snapshot rapide**: Preserve the existing block from the current README.md verbatim (it documents the port-forward + env workflow correctly).
    - **Liens**: `spec.md`, `CLAUDE.md`, `.planning/`, my-kluster repo URL.

    Target file size: at least 80 non-empty lines (more is fine — REQ-readme-onboarding cares about quality of content, not length, but the current 29-line stub is demonstrably insufficient).

    After writing, do a self-walkthrough: pretend you have just cloned the repo with no prior context. Can you reach `helm lint` exiting 0 by following the README only? If not, fix the missing step.

    Do NOT delete the Snapshot rapide section — it remains the canonical pointer to the cluster-side snapshot workflow.
  </action>
  <verify>
    <automated>
      [ "$(wc -l < README.md)" -ge 80 ] && \
      grep -q '^# arr-stack' README.md && \
      grep -qE '^## (Vue d.ensemble|Stack)' README.md && \
      grep -q 'helm lint charts/arr-stack/' README.md && \
      grep -q 'kubeconform' README.md && \
      grep -q 'arr-stack-app.yaml' README.md && \
      grep -q 'snapshot.sh' README.md && \
      grep -q 'spec.md' README.md && \
      grep -q 'CLAUDE.md' README.md && \
      ! grep -q 'en cours de bootstrap (Phase 0)' README.md
    </automated>
  </verify>
  <acceptance_criteria>
    - README.md has at least 80 lines.
    - Contains required sections: "Vue d'ensemble", "Stack" (overview table), helm/kubeconform usage, "arr-stack-app.yaml" (Deploy explanation), "snapshot.sh" (runbook), "spec.md", "CLAUDE.md" links.
    - Does NOT carry the stale "en cours de bootstrap (Phase 0)" status from the current README.
    - All 4 helm commands from `<interfaces>` are present and copy-pasteable.
    - The Snapshot rapide section from the current README is preserved verbatim or with only cosmetic edits.
  </acceptance_criteria>
  <done>
    README is rewritten for the post-Phase-4 reality. Onboarding walkthrough is feasible without other docs — the next checkpoint task validates this with a human pass.
  </done>
</task>

<task type="auto">
  <name>Task 7.2: Refresh CLAUDE.md sections rendered stale by Phase 4 (D-04-DOCS-01)</name>
  <files>CLAUDE.md</files>
  <read_first>
    CLAUDE.md (entire file — 590 lines)
    .planning/phases/04-umbrella-chart-migration-des-9-apps/04-PATTERNS.md §"CLAUDE.md (rewritten)" (section-by-section action table)
    charts/arr-stack/ (the actual on-disk layout post-Plans 02-05 — this is what `Structure actuelle` must mirror)
  </read_first>
  <action>
    Open `CLAUDE.md` and apply the following targeted edits. DO NOT rewrite untouched sections — D-04-DOCS-01 is a refresh, not a full rewrite of CLAUDE.md (the README gets the full rewrite). Preserve:
    - Stack technique (table)
    - Conventions développement — arrconf
    - Workflow snapshot
    - Frontière arrconf / configarr
    - Pattern single-instance + tags
    - GSD intégration
    - Références

    **Section: "Vue d'ensemble" (lines 4-15)**

    Replace `**État actuel** : phase spec/bootstrap. Le code et le chart n'existent pas encore — voir [\`spec.md\`](./spec.md) §7 pour la roadmap par phases.` with:

    ```
    **État actuel** : Phase 4 terminée — chart umbrella `charts/arr-stack/` opérationnel avec ses 10 alias bjw-s/app-template, 1 ArgoCD App `arr-stack` côté my-kluster, Renovate `customManagers` actif. Phases 5-8 à venir. Voir [`spec.md`](./spec.md) §7 et [`.planning/ROADMAP.md`](./.planning/ROADMAP.md).
    ```

    **Section: "Structure cible" → "Structure actuelle"**

    Replace the entire `## Structure cible` block (its tree diagram) with `## Structure actuelle` and the FOLLOWING tree (matches Plans 02-06 ground truth):

    ```
    ## Structure actuelle (post-Phase 4)

    ```
    arr-stack/
    ├── spec.md                          # WHAT + WHY
    ├── CLAUDE.md                        # ce fichier — HOW
    ├── README.md                        # entrée publique GitHub
    │
    ├── tools/arrconf/                   # script Python (Phases 1-3)
    │   ├── pyproject.toml
    │   ├── Dockerfile
    │   ├── arrconf/                     # source
    │   └── tests/
    │
    ├── tools/snapshot/                  # snapshot Bash (Phase 0)
    ├── tools/scripts/                   # helpers Phase 4 (check-renovate-annotations.sh + byte-equivalence-diff.sh)
    │
    ├── charts/arr-stack/                # umbrella Helm chart (Phase 4)
    │   ├── Chart.yaml                   # 10 dépendances app-template (alias par service)
    │   ├── Chart.lock                   # committé pour ArgoCD path-source
    │   ├── charts/                      # sub-chart tarballs committés
    │   │   └── app-template-4.6.2.tgz
    │   ├── values.yaml                  # ★ annotations Renovate ici, 10 alias
    │   ├── values.schema.json           # validation values.yaml (Helm 3 auto)
    │   ├── files/                       # config files mountés en ConfigMap
    │   │   ├── arrconf.yml
    │   │   └── configarr.yml
    │   └── templates/                   # minimaliste (D-04-CRON-01 → tout passe par alias)
    │       ├── _helpers.tpl             # arr-stack.labels + 2 annotation fragments
    │       ├── arrconf-configmap.yaml   # .Files.Get "files/arrconf.yml"
    │       └── configarr-configmap.yaml # .Files.Get "files/configarr.yml"
    │
    ├── examples/
    │   └── values-prod.yaml             # copie de charts/arr-stack/values.yaml (D-04-VALUES-03)
    │
    ├── schemas/                         # JSON Schema arrconf (Phase 1)
    │
    ├── snapshots/                       # ADR-6 baselines
    │
    └── .github/workflows/
        ├── arrconf-image.yml            # build + push GHCR (Phase 1)
        ├── tests.yml                    # ruff + mypy + pytest (Phase 1)
        └── chart-lint.yml               # helm lint + kubeconform + Renovate + schema (Phase 4)
    ```
    ```

    **Section: "Intégration avec my-kluster" (find heading "Intégration avec my-kluster")**

    Replace its content with:

    ```
    - **Une seule** ArgoCD Application (`my-kluster/argocd/argocd-apps/arr-stack-app.yaml`) pointe vers ce repo, path `charts/arr-stack/`, `targetRevision: vX.Y.Z` (semver pinné par Renovate côté my-kluster). Cf [`spec.md`](./spec.md) §9.2 et [`.planning/phases/04-umbrella-chart-migration-des-9-apps/04-08-cutover-SUMMARY.md`](./.planning/phases/04-umbrella-chart-migration-des-9-apps/) (cutover Phase 4).
    - **Bootstrap secrets** restent dans `my-kluster/secrets/{arrconf,configarr}-secret.yaml` (manuels, `kubectl apply`) jusqu'à migration ESO globale (Phase 8). Référencés via `envFrom: secretRef: name: {arrconf,configarr}-env` dans les alias correspondants.
    - **9 anciennes ArgoCD Applications unitaires** (sonarr/radarr/prowlarr/cleanuparr/configarr/qbittorrent/seerr/flaresolverr/jellyfin) + `arrconf-app.yaml` + `charts/configarr/` + `charts/arrconf/` ont été SUPPRIMÉES côté my-kluster lors de la Phase 4 (D-04-CUTOVER-01 — atomic big-bang single PR).

    Tout ce qui change dans le périmètre arr-stack se fait via PR sur **ce** repo. Toute modif côté my-kluster est limitée au bump `targetRevision` (auto par Renovate) ou à la gestion des secrets bootstrap.
    ```

    **Section: "Comment ajouter une nouvelle app à arrconf"**

    At the end of the existing numbered list, add a new step:

    ```
    6. **Ajouter l'alias dans le chart umbrella** : `charts/arr-stack/Chart.yaml` (nouvelle entrée `dependencies:`, alias = nom de l'app) + `charts/arr-stack/values.yaml` (nouveau bloc top-level avec annotation `# renovate: image=...`). Lancer `helm dependency update charts/arr-stack/` pour rafraîchir le Chart.lock.
    7. **Doc** : ajouter une ligne dans `README.md` (apps couvertes) et dans le tableau frontière de ce CLAUDE.md.
    ```
    (Renumber the existing step 6 to 8 — the previous "Doc" step.)

    **Section: "Ce que tu NE dois PAS faire"**

    Add at the end of the existing bulleted list:

    ```
    - ❌ **Ne pas ajouter une app dans `values.yaml` sans alias correspondant dans `Chart.yaml`.** L'alias est requis pour que Helm propage les valeurs vers le sub-chart `app-template` (D-04-VALUES-01).
    - ❌ **Ne pas oublier l'annotation `# renovate: image=<repo>` au-dessus de chaque `repository:`.** `tools/scripts/check-renovate-annotations.sh` + le job `chart-lint.yml` bloquent un merge sinon.
    - ❌ **Ne pas modifier `charts/arr-stack/charts/app-template-*.tgz`.** Sub-chart tarball committé pour ArgoCD path-source (RESEARCH §Unknown #7). Régénérer avec `helm dependency update`.
    ```

    **Section: "Bootstrap (état actuel — 2026-05-07)" → "Historical bootstrap (Phase 0-3)"**

    Rename the heading. At the top of the section add a one-line note:

    ```
    > Section archivée — Phase 4 est terminée. Pour l'état actuel, voir "Vue d'ensemble" et "Structure actuelle" ci-dessus.
    ```

    Then leave the rest of the historical content unchanged.

    Final smoke checks:
    ```bash
    [ "$(wc -l < CLAUDE.md)" -ge 380 ]
    grep -q 'Structure actuelle' CLAUDE.md
    grep -q 'Historical bootstrap (Phase 0-3)' CLAUDE.md
    grep -q 'arr-stack-app.yaml' CLAUDE.md
    grep -q 'check-renovate-annotations.sh' CLAUDE.md
    ! grep -q 'Structure cible$' CLAUDE.md   # heading renamed
    ! grep -q 'phase spec/bootstrap' CLAUDE.md   # stale status removed
    ```
  </action>
  <verify>
    <automated>
      [ "$(wc -l < CLAUDE.md)" -ge 380 ] && \
      grep -q '## Structure actuelle' CLAUDE.md && \
      grep -q 'Historical bootstrap (Phase 0-3)' CLAUDE.md && \
      grep -q 'arr-stack-app.yaml' CLAUDE.md && \
      grep -q 'check-renovate-annotations.sh' CLAUDE.md && \
      grep -q 'app-template-4.6.2.tgz' CLAUDE.md && \
      ! grep -q '^## Structure cible$' CLAUDE.md && \
      ! grep -q 'phase spec/bootstrap' CLAUDE.md
    </automated>
  </verify>
  <acceptance_criteria>
    - `## Structure cible` heading is gone (renamed to `## Structure actuelle`).
    - `Historical bootstrap (Phase 0-3)` heading is present.
    - Stale "phase spec/bootstrap. Le code et le chart n'existent pas encore" text is removed.
    - `arr-stack-app.yaml` is referenced in the Intégration section.
    - The `Comment ajouter` and `Ce que tu NE dois PAS faire` sections each mention `Chart.yaml`/`values.yaml` alias requirement.
    - Sub-chart tarball mention (`app-template-4.6.2.tgz`) present.
    - File still has at least 380 lines (preserves untouched sections).
  </acceptance_criteria>
  <done>
    CLAUDE.md is up to date with Phase 4 reality. The README rewrite + CLAUDE.md refresh together deliver D-04-DOCS-01.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 7.3: Operator walkthrough — onboarding < 30 min from README</name>
  <files>README.md, CLAUDE.md</files>
  <read_first>
    README.md (newly rewritten)
    CLAUDE.md (newly refreshed)
  </read_first>
  <what-built>
    A rewritten README.md (Task 7.1) and a refreshed CLAUDE.md (Task 7.2) that together aim to enable a new operator (or you-in-3-months) to clone, understand, and chart-lint the project in under 30 minutes.
  </what-built>
  <how-to-verify>
    OPERATOR walkthrough — open a fresh shell and a stopwatch.

    Without consulting other docs (no spec.md, no .planning/, no STATE.md):

    1. Open README.md from the current branch.
    2. Identify what arr-stack does. (≤ 3 min)
    3. Inventory the prerequisites and confirm they are satisfied (or note what is missing). (≤ 5 min)
    4. Run the 4 helm commands from the "Umbrella chart usage" section in the README. They must all exit 0. (≤ 10 min including `helm repo add`)
    5. Open CLAUDE.md "Structure actuelle" and confirm the tree matches what is actually on disk (`ls -la charts/arr-stack/templates/` should match the 3 files listed). (≤ 5 min)
    6. Read CLAUDE.md "Intégration avec my-kluster" and confirm the description of the single-App pull pattern. (≤ 3 min)
    7. Read README.md "Operator runbook" and the snapshot section. (≤ 4 min)

    Total target: ≤ 30 min wall-clock.

    Then:
    - Type "approved" (with the measured wall-clock time) to resume.
    - OR type a description of gaps/confusion points so Tasks 7.1/7.2 can be revised.
  </how-to-verify>
  <acceptance_criteria>
    - Operator confirms the walkthrough completes in ≤ 30 minutes.
    - 4 helm commands from README all exited 0 during the walkthrough.
    - CLAUDE.md `Structure actuelle` tree matches the actual files in `charts/arr-stack/`.
    - No critical confusion points raised by operator (small typo fixes acceptable, structural gaps blocking).
  </acceptance_criteria>
  <resume-signal>Type "approved &lt;duration&gt;" (e.g. "approved 22min") OR describe gaps for revision.</resume-signal>
</task>

</tasks>

<verification>
- README.md has ≥ 80 lines, contains required sections, no stale Phase 0 status.
- CLAUDE.md has `Structure actuelle` (renamed from `Structure cible`), `Historical bootstrap (Phase 0-3)` (renamed from `Bootstrap (état actuel)`), mentions `arr-stack-app.yaml` + `check-renovate-annotations.sh`.
- Operator confirmed onboarding < 30 min.
</verification>

<success_criteria>
REQ-readme-onboarding satisfied with a human-confirmed onboarding walkthrough. D-04-DOCS-01 closed.
</success_criteria>

<output>
After completion, create `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-07-docs-refresh-SUMMARY.md`. Record the wall-clock time the operator measured during the walkthrough.
</output>
