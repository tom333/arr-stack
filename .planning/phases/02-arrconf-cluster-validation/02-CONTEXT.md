# Phase 2: Validation cluster - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning
**Source:** /gsd-discuss-phase 2 (interactif, mode default — 4 zones grises sélectionnées)

<domain>
## Phase Boundary

Premier déploiement réel d'arrconf dans le cluster `my-kluster` :

- **Mini-chart Helm ad-hoc** dans `my-kluster/charts/arrconf/` (mirror exact de `charts/configarr/`) — sera supprimé en Phase 4 quand l'umbrella le remplace.
- **CronJob `arrconf`** dans namespace `selfhost`, schedule 4h, secret manuel `arrconf-env` injecté via `envFrom: secretRef`.
- **Bascule progressive** : PR1 déploie en `arrconfDryRun: true` → 1 cycle d'observation → PR2 flippe en `false`.
- **Drift detection** prouvée : modification UI hors-Git → écrasée au run suivant, log JSON visible.
- **Re-snapshot ADR-6 obligatoire** avant PR1 et après le premier run dry-run pour prouver l'absence d'écriture (success criterion #3).

**Reconciler couvert :** uniquement Sonarr `download_clients` (le seul livré en Phase 1).

**OUT of scope Phase 2 :**
- Umbrella chart → Phase 4
- Autres reconcilers Sonarr (indexers, notifications, root_folders, tags, host_config) → Phase 3
- Radarr / Prowlarr / qBittorrent / Seerr / Jellyfin → Phases 3, 5, 6, 7
- Migration ESO/Akeyless → Phase 8
- Suppression du chart configarr de my-kluster → Phase 4

</domain>

<decisions>
## Implementation Decisions

### Open questions résolues

- **D-23 (Q3 schedule arrconf)** : `0 */4 * * *` (toutes les 4 h, sync avec configarr). `concurrencyPolicy: Forbid`, `startingDeadlineSeconds: 600` (tolérance 10 min de retard), `successfulJobsHistoryLimit: 1`, `failedJobsHistoryLimit: 2`. *Source : choix utilisateur ; spec recommandait 6h initialement, mais 4h aligné configarr facilite la mémorisation et accélère la fenêtre de drift detection.*

### Emplacement & shape

- **D-24 (Mini-chart location)** : Le chart Phase 2 vit dans **`my-kluster/charts/arrconf/`**, pas dans ce repo. Mirror exact de `my-kluster/charts/configarr/`. PRs Phase 2-3 atterrissent côté my-kluster. Phase 4 supprimera ce chart + l'ArgoCD App dédiée quand l'umbrella prendra le relais — exactement la même migration que pour configarr. *Source : choix utilisateur ; cohérent avec ADR-2 (deps app-template) reportée à Phase 4 et avec la séparation des responsabilités déjà établie pour configarr.*

- **D-25 (`arrconf.yml` shape Phase 2)** : Minimal Sonarr-only. Un seul bloc `sonarr.main` avec 1 download_client (qBittorrent existant), pas de stubs vides ni de sections commentées pour Phase 3+. Le JSON Schema généré en Phase 1 valide déjà cette shape. Phase 3 ajoutera les sections au fur et à mesure que les reconcilers atterrissent. *Source : choix utilisateur ; principe « pas de noise sans valeur immédiate » + pas besoin de modifier le schéma maintenant pour autoriser des sections vides.*

- **D-26 (ArgoCD App)** : `my-kluster/argocd/argocd-apps/arrconf-app.yaml` créée — `kind: Application`, `metadata.name: arrconf`, `spec.destination.namespace: selfhost`, `spec.project: selfhost-project`, `spec.source.repoURL: https://github.com/tom333/my-kluster.git`, `spec.source.path: charts/arrconf`, `targetRevision: HEAD`, `syncOptions: [CreateNamespace=false, ServerSideApply=true]`, `automated: { selfHeal: true, prune: true }`. Mirror exact de `configarr-app.yaml`. *Source : pattern établi.*

- **D-27 (ConfigMap mount)** : `arrconf.yml` est dans `charts/arrconf/files/arrconf.yml` côté my-kluster, injecté en ConfigMap via `.Files.Get` dans `templates/configmap.yaml`, monté en lecture seule à `/app/config/arrconf.yml` dans le container. Annotation `checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}` sur le pod template pour rolling reload (mirror configarr). *Source : pattern configarr ; aucune raison de diverger.*

### Bascule dry-run → apply

- **D-28 (Protocole 2-PR)** : Helm value `arrconfDryRun: bool` dans `values.yaml`, mappée au CronJob template via `env: [{ name: ARRCONF_DRY_RUN, value: {{ .Values.arrconfDryRun | quote }} }]`.
  - **PR1** : ajoute le chart, ArgoCD App, ConfigMap, `arrconfDryRun: true`. Après merge → ArgoCD sync → attendre 1 cycle (4 h) → vérifier les logs JSON ("would ADD/UPDATE/DELETE …, dry_run=true") → re-snapshot post-run dans `snapshots/post-phase2-pr1-<date>/` → `diff -r` avec baseline = identique (success criterion #3 vérifié programmatiquement, pas juste à l'œil).
  - **PR2** : flippe `arrconfDryRun: false`. Le commit message documente l'observation des logs PR1 et la date du re-snapshot. Revert facile (`git revert`) en cas de pépin.
  *Source : choix utilisateur ; respecte le principe GitOps (zéro drift cluster vs Git pendant la validation), traçabilité dans l'historique Git, revert atomique possible.*

### Bootstrap secret

- **D-29 (Scope `arrconf-env`)** : Secret manuel `my-kluster/secrets/arrconf-secret.yaml` ne contient **que** `SONARR_API_KEY` en Phase 2 (principe de moindre privilège, REQ-bootstrap-exception). Bump du secret par PR à chaque phase suivante :
  - Phase 3 → ajoute `RADARR_API_KEY`, `PROWLARR_API_KEY`
  - Phase 5 → ajoute `QBT_USER`, `QBT_PASS`
  - Phase 6 → ajoute `SEERR_API_KEY`
  - Phase 7 → ajoute `JELLYFIN_API_KEY`

  Le YAML attendu côté my-kluster :
  ```yaml
  apiVersion: v1
  kind: Secret
  metadata:
    name: arrconf-env
    namespace: selfhost
  type: Opaque
  stringData:
    SONARR_API_KEY: "<api key Sonarr récupérée via UI bootstrap>"
  ```
  *Source : choix utilisateur ; cohérent CLAUDE.md « Aucune lecture de fichier de secrets — uniquement env » + REQ-secret-management.*

### Re-snapshot discipline (ADR-6)

- **D-30 (Snapshots Phase 2)** : Trois snapshots minimum sont committés dans `snapshots/` au cours de Phase 2 :
  1. **`before-phase-2-<date>/`** — re-snapshot avant tout déploiement (success criterion #1, peut être identique au baseline Phase 0 si aucun changement UI entre-temps — dans ce cas un README.md note « identique à baseline »).
  2. **`post-phase2-pr1-<date>/`** — capture post-1er-run en dry-run, sert à prouver `diff = 0` vs `before-phase-2` (success criterion #3).
  3. **`post-phase2-pr2-<date>/`** — capture après bascule en apply, montre que la ressource managée porte bien le tag `arrconf-managed` et matche le YAML (success criterion #4).
  4. **`drift-test-<date>/`** (optionnel mais recommandé) — capture après modification UI manuelle d'un download_client (test #5), preuve écrite que le drift a été corrigé au run suivant.
  *Source : ADR-6 + CLAUDE.md « Discipline snapshot ».*

### Carry-forward de Phase 1 (locked, ne pas re-débattre)

| Décision | Pertinence Phase 2 |
|---|---|
| **D-01** (release manuelle, image GHCR `:vX.Y.Z`) | Le chart pin l'image sur un tag concret (`v0.1.0` typiquement, créé après Phase 1 verify) — jamais `:latest` |
| **D-02** (tag `arrconf-managed`) | Visible dans la vérif drift detection : la ressource recréée doit porter le tag |
| **D-04** (`prune: false` default) | `arrconf.yml` Phase 2 N'AJOUTE PAS `prune: true` — Phase 2 ne supprime rien, juste add+update |
| **D-07** (structlog JSON cluster, pretty TTY local) | Activation auto via détection TTY ; logs CronJob = JSON pour parsing observability |
| **D-12** (ScopeViolationError) | Codé en dur dans le binaire ; pas de configuration Phase 2 |
| **ADR-5** (frontière configarr) | Confirme que arrconf ne touche PAS les endpoints quality_profiles / etc. |
| **ADR-6** (snapshot baseline) | Operationalisé en D-30 |

### Claude's Discretion

Détails opérationnels laissés au planner / executor (mirror configarr sauf raison contraire) :

- **Cluster service URL** : `http://sonarr.selfhost.svc.cluster.local:8989` — vérifier le service name exact dans `my-kluster/argocd/argocd-apps/sonarr-app.yaml` ; idem pour qBit dans `arrconf.yml`.
- **Pod securityContext** : `runAsNonRoot: true`, `runAsUser: 1000`, `runAsGroup: 1000` (déjà appliqués dans l'image Phase 1, redondant mais defense-in-depth) ; `readOnlyRootFilesystem: false` (httpx + tenacity peuvent vouloir écrire dans `/tmp` — à confirmer en exécution).
- **Resources requests/limits** : copie configarr (50m/128Mi req, 500m/512Mi limit). À ajuster après observation des premiers runs si besoin.
- **TZ env var** : `Europe/Paris` (mirror configarr).
- **`imagePullPolicy: IfNotPresent`** + `image.tag` pinned (Phase 1 release tag).
- **Helm values.schema.json** : optionnel Phase 2 ; seulement 4-5 valeurs à valider, pas critique. Phase 4 (umbrella) en aura besoin.
- **Validation programmatique post-run** : un petit script Bash dans `tools/snapshot/` qui prend deux dossiers de snapshots et fait `diff -r` filtré sur les champs read-only (id, etc.) — peut être utile pour automatiser le success criterion #3. Si le planner juge que c'est trop, le faire à la main.
- **Drift detection demo** : modifier un download_client via `kubectl exec -it deployment/sonarr -n selfhost -- curl -X PUT …` ou via l'UI Sonarr (web port-forward). Documenter dans le README arrconf une fois validé. Le commit Phase 2 final doit linker une capture des logs JSON montrant l'override.
- **Documentation** : ajouter une section "Phase 2 deployment" au `tools/arrconf/README.md` ou (mieux) un nouveau `my-kluster/charts/arrconf/README.md` court documentant la procédure 2-PR et le runbook de drift detection.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spec source + conventions
- `spec.md §6.4` — Pattern de déploiement (CronJob, ConfigMap, secret manuel)
- `spec.md §7 Phase 2` — Narrative de la phase (validation cluster, dry-run protocol)
- `spec.md §10 Q3` — Schedule arrconf (résolu D-23)
- `spec.md §11 ADR-6` — Discipline snapshot baseline (operationalisé D-30)
- `CLAUDE.md` "Workflow snapshot (CRITIQUE)" — Procédure ADR-6 détaillée
- `CLAUDE.md` "Variables d'environnement" — Naming convention API keys (SONARR_API_KEY etc.)
- `CLAUDE.md` "Intégration avec my-kluster" — Bootstrap secrets restent côté my-kluster
- `.planning/REQUIREMENTS.md` — REQ-drift-detection, REQ-bootstrap-exception, REQ-secret-management

### Phase 1 outputs (carry-forward)
- `.planning/phases/01-arrconf-poc-json-schema/01-CONTEXT.md` — D-01 à D-22 (locked decisions)
- `.planning/phases/01-arrconf-poc-json-schema/01-VERIFICATION.md` — État des success criteria Phase 1
- `.planning/phases/01-arrconf-poc-json-schema/01-HUMAN-UAT.md` — 3 items humains pending (item #3 = live round-trip Sonarr, naturellement résolu par Phase 2 PR1)
- `tools/arrconf/README.md` — CLI reference, déjà rédigé Phase 1
- `schemas/arrconf-schema.json` — JSON Schema utilisé pour valider `arrconf.yml`
- `examples/baseline-sonarr.yml` — Template de référence pour `charts/arrconf/files/arrconf.yml`

### Phase 0 outputs
- `snapshots/baseline-2026-05-07/sonarr/downloadclient.json` — Baseline pour `diff` post-dry-run
- `tools/snapshot/snapshot.sh` — Outil de re-snapshot (ADR-6, D-30)
- `tools/snapshot/README.md` — Doc port-forward / env vars

### Sister repo my-kluster (templates de référence — LIRE AVANT DE COPIER)
- `/home/moi/projets/perso/my-kluster/CLAUDE.md` — Conventions ArgoCD App, charts/, secrets/, syncPolicy
- `/home/moi/projets/perso/my-kluster/charts/configarr/Chart.yaml` — Chart.yaml minimal pattern
- `/home/moi/projets/perso/my-kluster/charts/configarr/values.yaml` — schedule, resources, apiKeysSecret pattern
- `/home/moi/projets/perso/my-kluster/charts/configarr/templates/_helpers.tpl` — fullname, labels, selectorLabels helpers
- `/home/moi/projets/perso/my-kluster/charts/configarr/templates/cronjob.yaml` — CronJob template, concurrencyPolicy Forbid, envFrom, checksum/config
- `/home/moi/projets/perso/my-kluster/charts/configarr/templates/configmap.yaml` — ConfigMap pattern (lit `files/config.yml` via .Files.Get)
- `/home/moi/projets/perso/my-kluster/argocd/argocd-apps/configarr-app.yaml` — ArgoCD App template
- `/home/moi/projets/perso/my-kluster/secrets/configarr-secret.yaml` — secret manuel pattern (stringData, Opaque)
- `/home/moi/projets/perso/my-kluster/argocd/argocd-apps/sonarr-app.yaml` — pour identifier le service name exact à mettre dans `arrconf.yml` (`base_url`)

### Image (livrée Phase 1, à pin Phase 2)
- `ghcr.io/tom333/arr-stack-arrconf:v0.1.0` — premier tag à créer après Phase 1 verify (`git tag v0.1.0 && git push --tags` sur arr-stack ; image construite par `arrconf-image.yml` workflow). Phase 2 PR1 pin ce tag exact.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`my-kluster/charts/configarr/` template entier** : Chart.yaml + values.yaml + templates/ tous transposables. Substitutions : `configarr` → `arrconf`, image, schedule (déjà identique 4h), config mount path (`/app/config/config.yml` → `/app/config/arrconf.yml`), apiKeysSecret (`configarr-env` → `arrconf-env`). PVC cache de configarr **n'est PAS** reproduit pour arrconf — il sert au cache TRaSH-Guides Git, arrconf n'a pas de cache local nécessaire (idempotent par nature).
- **`tools/snapshot/snapshot.sh`** (Phase 0) : utilisé tel quel pour les re-snapshots D-30. Possiblement étendu avec un mode `--diff <baseline_dir>` qui prend deux dossiers et compare — à arbitrer en planning.
- **`examples/baseline-sonarr.yml`** (Phase 1) : déjà au bon format avec modeline `# yaml-language-server`, sert de base directe pour `charts/arrconf/files/arrconf.yml` (suffit d'ajuster le chemin relatif du `$schema` puisque le fichier vit côté my-kluster maintenant — le modeline pointera vers `https://raw.githubusercontent.com/tom333/arr-stack/main/schemas/arrconf-schema.json` ou un chemin relatif si on garde une copie du schéma côté my-kluster).
- **`arrconf` CLI** (Phase 1) : tous les sous-commandes (`apply`, `dump`, `diff`, `schema-gen`) marchent ; `apply` respecte `ARRCONF_DRY_RUN` env. La pile est complète, Phase 2 ne fait QUE l'empaqueter K8s.

### Established Patterns

- **GitOps strict** (CLAUDE.md, my-kluster) : zéro `kubectl apply` direct ; tout passe par PR + ArgoCD sync. D-28 respecte ce principe (deux PRs trackés en Git plutôt que `kubectl patch` qui drift).
- **Secret manuel + envFrom** (configarr existant) : les bootstrap secrets vivent dans `my-kluster/secrets/`, appliqués manuellement (`kubectl apply -f`), jamais via Helm chart. ArgoCD ne les touche pas. Migration ESO = Phase 8.
- **CronJob + concurrencyPolicy Forbid** (configarr) : un seul run à la fois, jamais de race. Adopté tel quel.
- **`checksum/config` annotation** (configarr cronjob.yaml) : roule le pod template quand le ConfigMap change ; même si CronJob ne crée pas un Deployment, l'annotation reste utile pour les futurs runs.

### Integration Points

- **ArgoCD project `selfhost-project`** : nouvelle App `arrconf` rattachée à ce project (mirror configarr).
- **Namespace `selfhost`** : already exists (créé par les autres apps : sonarr, radarr, qbittorrent, configarr). `CreateNamespace=false`.
- **Service Sonarr in-cluster** : `sonarr.selfhost.svc.cluster.local:8989` (à confirmer dans my-kluster sonarr-app values). Plus de port-forward nécessaire — le pod arrconf y accède directement.
- **Secret application** : opérateur fait `kubectl apply -f my-kluster/secrets/arrconf-secret.yaml` AVANT le sync ArgoCD de la PR1 (sinon le pod crash sur `SONARR_API_KEY` vide). À documenter dans le README my-kluster ou la PR description.

</code_context>

<specifics>
## Specific Ideas

- **Image tag à créer avant PR1** : `git tag v0.1.0 && git push --tags` côté `arr-stack` pour déclencher `arrconf-image.yml` qui produit `ghcr.io/tom333/arr-stack-arrconf:v0.1.0`. PR1 my-kluster pin ce tag exact. À tracer dans le plan Phase 2.
- **Pitfall 7 (GHCR public toggle)** : item #1 du `01-HUMAN-UAT.md` Phase 1 — le tag `v0.1.0` produira la première image publiée ; aller dans GHCR settings et toggle `package visibility: public`. Si oublié, le pod arrconf en cluster fail sur `ImagePullBackOff` (pas de pull secret configuré dans le chart — délibéré, on veut public). Documenter dans la PR1 description.
- **Drift demo concret** : modifier `category` du download_client qBittorrent dans l'UI Sonarr (champ neutre, pas de risque) → attendre 4 h ou forcer `kubectl create job --from=cronjob/arrconf arrconf-drift-test` → vérifier dans logs JSON la ligne `event=update_planned action=UPDATE diff={category: …}` puis dans Sonarr UI que la valeur est revenue.

</specifics>

<deferred>
## Deferred Ideas

- **`tools/snapshot/diff.sh`** — script de diff structuré entre deux dossiers de snapshots (filtrage des champs read-only `id`, etc.). Utile pour Phase 2 mais peut rester du `diff -r` brut si pas critique. **Pour la roadmap Phase 3 ou tools utilities**.
- **NetworkPolicy `selfhost`** restrictive pour arrconf (autorise sortie vers Sonarr/Radarr/Prowlarr/qBit/Seerr/Jellyfin uniquement). Sécurité défense-en-profondeur. **Pour Phase 8 (durcissement secrets/réseau).**
- **Notification Sonarr quand arrconf rétablit un drift** (Slack / email via Sonarr.Notification config). Suppose que Phase 3 a déjà landé `notifications` reconciler. **Pour Phase 3+ ou nice-to-have.**
- **Helm `values.schema.json`** pour le mini-chart Phase 2 — mineur, déféré à Phase 4 où l'umbrella en aura besoin de toute façon.
- **`arrconf` SDK metrics endpoint** (Prometheus exposing reconcile counts) — observabilité avancée. **Hors-scope MVP.**

</deferred>
