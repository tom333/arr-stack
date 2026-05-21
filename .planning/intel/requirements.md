# Requirements

Extracted from `spec.md` §3 (Objectifs / Non-objectifs) and §8 (Critères de succès). The source is a SPEC (no PRDs in the ingest set), but goals + success criteria + scope statements function as PRD-style requirements for the roadmapper. Each requirement carries an ID, source pointer, description, acceptance criteria, and scope.

---

## REQ-config-as-code

- source: /home/moi/projets/perso/arr-stack/spec.md (§3.1 O1, §3.1 O2)
- description: La config de Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin (et autres apps de la stack) est entièrement déclarative dans un fichier YAML versionné Git. Tout changement de config passe par PR sur le repo `arr-stack`. Aucune intervention UI requise après bootstrap.
- acceptance:
  - Toute la config visée par arrconf est exprimable dans `files/arrconf.yml`
  - Aucune intervention UI nécessaire après bootstrap initial (sauf bootstrap admin Jellyfin — voir REQ-bootstrap-exception)
  - Le YAML est validé contre `schemas/arrconf-schema.json` (échec CI sinon)
- scope: arrconf, charts/arr-stack/files/arrconf.yml

---

## REQ-drift-detection

- source: /home/moi/projets/perso/arr-stack/spec.md (§3.1 O3, §8 CS3)
- description: Drift UI détectable. Si quelqu'un (humain, autre tool) modifie l'app en UI, le prochain run d'arrconf restaure l'état désiré.
- acceptance:
  - Modification UI hors-Git détectée et corrigée au run suivant
  - Délai max de correction = schedule du CronJob arrconf (recommandation initiale 6h, à arbitrer Q3)
  - Logs de drift visibles dans la sortie structurée JSON
- scope: arrconf reconcilers

---

## REQ-idempotence

- source: /home/moi/projets/perso/arr-stack/spec.md (§3.1 O4, CLAUDE.md "Idempotence (RÈGLE D'OR)")
- description: Idempotent. Ré-exécuter arrconf 10 fois ne change rien si le YAML n'a pas bougé.
- acceptance:
  - `GET` la liste actuelle, matcher par `name` ou identifiant stable côté API
  - Diff explicite avant `PUT` (pas de PUT systématique → pas de bruit dans les logs *arr)
  - Round-trip prouvé : `arrconf dump → apply --dry-run` produit 0 action
  - Tests unitaires : add / update / delete / no-op (un test par cas)
- scope: arrconf differ.py, reconcilers/

---

## REQ-umbrella-deployment

- source: /home/moi/projets/perso/arr-stack/spec.md (§3.1 O5, §9.2)
- description: Le déploiement de la stack se fait via une seule ArgoCD Application dans `my-kluster` pointant vers le chart umbrella du repo arr-stack.
- acceptance:
  - Une seule Application `arr-stack` dans `my-kluster/argocd/argocd-apps/arr-stack-app.yaml`
  - 9 apps déployées via ce chart unique : sonarr, radarr, prowlarr, cleanuparr, configarr, qbittorrent, seerr, flaresolverr, jellyfin
  - Suppression des 9 ArgoCD Application unitaires + `charts/configarr/` côté `my-kluster` après Phase 4
  - Sync automatique selfHeal + prune + ServerSideApply
- scope: charts/arr-stack/, integration my-kluster

---

## REQ-renovate-image-tracking

- source: /home/moi/projets/perso/arr-stack/spec.md (§3.1 O6, §6.4, §8 CS4)
- description: Renovate suit automatiquement les versions d'image (Sonarr, Radarr, ..., arrconf) déclarées dans `values.yaml` et propose les bumps.
- acceptance:
  - Annotation `# renovate: image=<repo>` au-dessus de chaque image dans `values.yaml`
  - `renovate.json` avec `customManagers` regex matchant `values.yaml`
  - Bumps minor/patch en automerge, majors en revue manuelle
  - Renovate suit aussi GHCR pour `arrconf` et le tag de release dans `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` (`targetRevision`)
- scope: renovate.json, charts/arr-stack/values.yaml

---

## REQ-configarr-coexistence

- source: /home/moi/projets/perso/arr-stack/spec.md (§3.1 O7, §3.2 NG4, §6.2 frontière, ADR-5)
- description: La config configarr (quality profiles + custom formats + naming + quality definitions) est versionnée dans le repo arr-stack et continue de fonctionner exactement comme aujourd'hui. arrconf et configarr ont des scopes complémentaires non-recouvrants.
- acceptance:
  - `charts/arr-stack/files/configarr.yml` est la source de vérité unique pour ces ressources
  - arrconf NE TOUCHE PAS aux endpoints quality_profiles / custom_formats / quality_definitions / media_naming (refus codé en dur dans les reconcilers)
  - Coexistence sans conflit : configarr et arrconf tournent en CronJobs séparés sans collision
- scope: arrconf reconcilers, charts/arr-stack/files/configarr.yml

---

## REQ-baseline-snapshot

- source: /home/moi/projets/perso/arr-stack/spec.md (§3.1 O8, §6.5, ADR-6)
- description: Une baseline lossless de la config actuelle des apps est capturée AVANT toute écriture de test, et conservée dans le repo. Permet rollback forensic et seed du premier `files/arrconf.yml`.
- acceptance:
  - `tools/snapshot/snapshot.sh` (Bash + curl + jq, indépendant d'arrconf) dispo dès Phase 0
  - Premier dump committé : `snapshots/baseline-2026-05-07/` (date du jour à l'exécution Phase 0)
  - Re-snapshot avant chaque phase touchant un nouveau scope (Phase 2, 3, 5, 6, 7)
  - Snapshots versionnés dans Git (NE PAS ignorer dans `.gitignore`)
  - `arrconf dump` (Phase 1+) produit un YAML arrconf round-trip avec `arrconf diff` = 0 action
- scope: tools/snapshot/, arrconf dump, snapshots/

---

## REQ-bootstrap-exception

- source: /home/moi/projets/perso/arr-stack/spec.md (§3.2 NG5, §8 CS1)
- description: Bootstrap automatique des API keys initiales explicitement hors scope. La 1ère obtention d'API key se fait toujours via UI; arrconf prend le relais ensuite. Compte admin Jellyfin créé manuellement avant Phase 7.
- acceptance:
  - Documentation runbook claire pour le bootstrap manuel (Sonarr / Radarr / Prowlarr / Seerr / Jellyfin)
  - Variables d'environnement attendues : `SONARR_API_KEY`, `RADARR_API_KEY`, `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY`
  - Aucune lecture de fichier de secrets : uniquement env (le wrapping K8s `envFrom: secretRef` injecte tout)
- scope: arrconf, runbook

---

## REQ-pr-to-cluster-latency

- source: /home/moi/projets/perso/arr-stack/spec.md (§8 CS2)
- description: Une PR sur `arr-stack` modifiant un champ de config se matérialise en cluster en moins de 1h (sync ArgoCD + run CronJob arrconf).
- acceptance:
  - PR mergée → tag de release → Renovate PR sur my-kluster → ArgoCD sync → CronJob run < 1h
  - Possible run manuel `kubectl create job --from=cronjob/arrconf` pour accélérer
- scope: workflow, CI/CD

---

## REQ-helm-validation

- source: /home/moi/projets/perso/arr-stack/spec.md (§8 CS6, §6.3 chart-lint.yml)
- description: `helm template charts/arr-stack/ -f examples/values-prod.yaml` rend des manifestes valides (kubeconform OK).
- acceptance:
  - `helm lint charts/arr-stack/` passe en CI
  - `helm template ... | kubeconform -` passe en CI
  - `values.yaml` parse contre `values.schema.json` en CI (bloquant)
- scope: charts/arr-stack/, .github/workflows/chart-lint.yml

---

## REQ-test-coverage

- source: /home/moi/projets/perso/arr-stack/spec.md (§8 CS7, §6.3 tests.yml, CLAUDE.md "Tests")
- description: `pytest` couvre ≥ 70 % du code arrconf, focus sur differ et reconcilers. Mock l'API via respx; pas de tests qui appellent vraiment Sonarr/Radarr en CI.
- acceptance:
  - Coverage ≥ 70 % sur `differ.py` et `reconcilers/`
  - Toutes les fixtures sont des JSON capturés depuis vraies APIs (sanitisés des secrets) dans `tests/fixtures/`
  - CI bloque si coverage < 70 %, si `ruff check` / `ruff format --check` échoue, ou si `mypy` échoue
- scope: tools/arrconf/tests/, .github/workflows/tests.yml

---

## REQ-readme-onboarding

- source: /home/moi/projets/perso/arr-stack/spec.md (§8 CS8)
- description: README permet à un autre dev (ou toi-dans-3-mois) de comprendre et déployer en moins de 30 min.
- acceptance:
  - Vue d'ensemble du projet, structure, commandes clés
  - Procédure de bootstrap claire (création API keys, secrets, premier déploiement)
  - Liens vers spec.md, CLAUDE.md, my-kluster
- scope: README.md

---

## REQ-secret-management

- source: /home/moi/projets/perso/arr-stack/spec.md (§8 CS5)
- description: Tous les bootstrap secrets sont maîtrisés côté my-kluster via Bitnami sealed-secrets. Aucune migration externe-secret planifiée — la baseline sealed-secrets est considérée stable et long-terme.
- acceptance:
  - Aucun secret committé en clair dans le repo arr-stack
  - Le wrapping K8s injecte les secrets via `envFrom: secretRef`
  - sealed-secrets reste la solution de production
- scope: my-kluster/secrets/, charts/arr-stack/templates/

---

## REQ-cli-subcommands

- source: /home/moi/projets/perso/arr-stack/spec.md (§6.1 CLI, CLAUDE.md "CLI")
- description: arrconf expose 4 sous-commandes : `apply`, `dump`, `diff`, `schema-gen`.
- acceptance:
  - `arrconf apply [--config PATH] [--apps LIST] [--dry-run] [--log-level LEVEL]` — reconcilie YAML → APIs
  - `arrconf dump [--apps LIST] [--output PATH]` — read-only, exporte YAML conforme schéma
  - `arrconf diff [--config PATH] [--apps LIST]` — compare local vs cluster, format lisible
  - `arrconf schema-gen [--output PATH]` — exporte JSON Schema pydantic vers `schemas/arrconf-schema.json`
  - Exit codes : 0 succès, 1 une app a échoué, 2 erreur de config (parse/validation), 3 (sur diff) drift détecté
  - `--dry-run` log les actions sans appeler `POST/PUT/DELETE`
- scope: tools/arrconf/arrconf/__main__.py

---

## REQ-yaml-autocomplete

- source: /home/moi/projets/perso/arr-stack/spec.md (§6.1 schema-gen, Phase 1)
- description: Autocomplétion + validation à la frappe dans VS Code / code-server via yaml-language-server, alimentée par le JSON Schema généré par `arrconf schema-gen`.
- acceptance:
  - `schemas/arrconf-schema.json` committé et regénéré à chaque ajout reconciler/resource (CI bloque si oublié)
  - Directive `# yaml-language-server: $schema=...` en tête de `examples/baseline-*.yml` et `charts/arr-stack/files/arrconf.yml`
  - `.vscode/settings.json` optionnel mappant `*arrconf*.yml` au schéma
  - Test manuel Phase 1 : ouvrir un YAML dans code-server, taper sous `download_clients:` → propositions des champs valides avec descriptions docstrings pydantic
- scope: tools/arrconf/arrconf/schema_gen.py, schemas/, examples/

---

## REQ-prune-opt-in

- source: /home/moi/projets/perso/arr-stack/spec.md (§10 Q8, CLAUDE.md "Idempotence")
- description: Stratégie `prune: false` par défaut, opt-in par section. Si une ressource est en cluster mais pas dans le YAML, logger sans supprimer sauf si l'utilisateur a activé `prune: true` pour cette section.
- acceptance:
  - Default `prune: false` au niveau de chaque section de ressource
  - Opt-in explicite par utilisateur dans `arrconf.yml`
  - Log clair quand une ressource cluster est ignorée (mode prune off)
  - Tag `arrconf-managed` (cf REQ-managed-tag) interagit avec prune : seules les ressources taggées `arrconf-managed` peuvent être prune (proposition à valider)
- scope: arrconf differ.py, reconcilers/

---

## REQ-managed-tag

- source: /home/moi/projets/perso/arr-stack/spec.md (§10 Q6)
- description: Marquer les ressources gérées via le champ `tags:` standard *arr (`arrconf-managed`) pour les distinguer des ressources manuelles.
- acceptance:
  - Toute ressource créée/modifiée par arrconf reçoit le tag `arrconf-managed`
  - Le reconciler tag est lui-même réconcilié (créer/garder le tag `arrconf-managed`, le tag est protégé du prune)
  - Documenté dans le runbook (CLAUDE.md mentionne déjà la décision Q6)
- scope: arrconf reconcilers/, tags resource

---

## REQ-phase-roadmap

- source: /home/moi/projets/perso/arr-stack/spec.md (§7)
- description: Roadmap progressive de-risk en 9 phases (0 à 8), chaque phase livrable indépendamment.
- acceptance:
  - Phase 0 (0.5j) — Bootstrap repo + script snapshot raw
  - Phase 1 (1.5j) — arrconf POC + snapshot YAML + JSON Schema (Sonarr download_clients)
  - Phase 2 (0.5j) — Validation cluster (CronJob avec dry-run au 1er run)
  - Phase 3 (2j) — Étendre arrconf : indexers, notifications, root_folders, tags, host_config + Radarr + Prowlarr
  - Phase 4 (1j) — Umbrella chart + migration des 9 apps de my-kluster
  - Phase 5 (1.5j) — Reconciler qBittorrent + split tv/anime/family (selon ADR-7)
  - Phase 6 (1j) — Reconciler Seerr (avec validation Q1 + Q10 préalable)
  - Phase 7 (1.5j) — Reconciler Jellyfin (avec bootstrap admin manuel + validation Q9)
  - Critères de fin de chaque phase = ceux listés en §7
- scope: roadmap globale

---

## REQ-app-coverage

- source: /home/moi/projets/perso/arr-stack/spec.md (§5.3, §6.2 frontière)
- description: Apps couvertes par le projet (cible MVP, déjà déployées dans my-kluster sauf arrconf).
- acceptance:
  - **Helm umbrella + arrconf** : Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, Jellyfin
  - **Helm umbrella seul** : FlareSolverr (config par env vars, pas d'API), Cleanuparr (config UI hors scope arrconf)
  - **Helm umbrella + sa propre config** : configarr (`files/configarr.yml`), arrconf (`files/arrconf.yml`)
  - Apps potentielles ultérieures hors scope MVP : Bazarr, Lidarr, Whisparr, Readarr (ajoutables sans repenser l'architecture)
- scope: charts/arr-stack/, tools/arrconf/reconcilers/
