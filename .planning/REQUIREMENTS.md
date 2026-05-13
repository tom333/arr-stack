# Requirements: arr-stack

**Defined:** 2026-05-07
**Core Value:** Aucune intervention UI nécessaire pour configurer Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h.

## v1 Requirements

Requirements for initial release. Each maps to a roadmap phase. IDs preserved from `intel/requirements.md` (not renumbered) so that traceability with the source SPEC stays intact.

### Snapshot & baseline

- [x] **REQ-baseline-snapshot**: Baseline lossless de la config actuelle capturée avant toute écriture. `tools/snapshot/snapshot.sh` (Bash + curl + jq, indépendant d'arrconf) dispo dès Phase 0. `arrconf dump` produit un YAML round-trip avec `arrconf diff` = 0 action en Phase 1+. Snapshots versionnés Git, re-snapshot avant chaque phase touchant un nouveau scope (Phases 2, 3, 5, 6, 7).

### arrconf — script Python

- [ ] **REQ-cli-subcommands**: arrconf expose 4 sous-commandes — `apply` (reconcilie YAML → APIs), `dump` (read-only export YAML), `diff` (compare local vs cluster), `schema-gen` (exporte JSON Schema). Exit codes : 0 succès / 1 app failure / 2 erreur config / 3 drift (sur `diff`).
- [ ] **REQ-yaml-autocomplete**: Autocomplétion + validation à la frappe dans VS Code / code-server via yaml-language-server, alimentée par `schemas/arrconf-schema.json` régénéré à chaque ajout reconciler/resource (CI bloque si oublié). Directive `# yaml-language-server: $schema=…` en tête de chaque YAML arrconf.
- [ ] **REQ-idempotence**: Ré-exécuter arrconf N fois ne change rien si le YAML n'a pas bougé. `GET` puis diff explicite avant `PUT`. Round-trip prouvé : `arrconf dump → apply --dry-run` produit 0 action. Tests unitaires : add/update/delete/no-op.
- [ ] **REQ-prune-opt-in**: `prune: false` par défaut, opt-in explicite par section. Si une ressource cluster n'est pas dans le YAML : log sans supprimer (sauf `prune: true`). Seules les ressources taggées `arrconf-managed` peuvent être prune.
- [ ] **REQ-managed-tag**: Toute ressource créée/modifiée par arrconf reçoit le tag `arrconf-managed` (champ `tags:` standard *arr). Le tag `arrconf-managed` lui-même est réconcilié (créer/garder, protégé du prune).
- [ ] **REQ-test-coverage**: `pytest` couvre ≥ 70 % du code arrconf, focus sur `differ.py` et `reconcilers/`. Mock httpx via `respx` ; aucun test n'appelle les vraies APIs en CI. Fixtures sanitisées dans `tests/fixtures/<app>_<resource>.json`. CI bloque si coverage < 70 %, si `ruff` échoue, ou si `mypy` échoue.

### Drift & reconciliation cluster

- [ ] **REQ-config-as-code**: Toute la config visée par arrconf est exprimable dans `charts/arr-stack/files/arrconf.yml`. Aucune intervention UI après bootstrap (sauf bootstrap admin Jellyfin — REQ-bootstrap-exception). YAML validé contre `schemas/arrconf-schema.json` (CI bloque sinon).
- [x] **REQ-drift-detection**: Modification UI hors-Git détectée et corrigée au run suivant. Délai max = schedule du CronJob arrconf (Q3, recommandation initiale 6 h). Logs de drift visibles dans la sortie structurée JSON.
- [ ] **REQ-bootstrap-exception**: 1ère obtention d'API key toujours via UI (Sonarr / Radarr / Prowlarr / Seerr / Jellyfin). Compte admin Jellyfin créé manuellement avant Phase 7. Variables d'env attendues : `SONARR_API_KEY`, `RADARR_API_KEY`, `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY`. Aucune lecture de fichier de secrets (uniquement env, injection K8s `envFrom: secretRef`).
- [ ] **REQ-secret-management**: Tous les bootstrap secrets restent maîtrisés dans `my-kluster/secrets/` jusqu'à migration ESO globale. Aucun secret committé dans arr-stack. Migration ESO/Akeyless = Phase 8 (post-MVP, optionnelle).

### Frontière configarr / arrconf

- [x] **REQ-configarr-coexistence**: La config configarr (`charts/arr-stack/files/configarr.yml`) reste source de vérité unique pour quality_profiles / custom_formats / quality_definitions / media_naming. arrconf ne touche PAS à ces endpoints (refus codé en dur côté reconcilers — `ScopeViolationError`). Coexistence sans conflit, CronJobs séparés.

### Couverture des apps

- [x] **REQ-app-coverage**: Apps couvertes (cible MVP) — Helm umbrella + arrconf : Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, Jellyfin ; Helm umbrella seul (config UI/env) : FlareSolverr, Cleanuparr ; Helm umbrella + sa propre config dédiée : configarr (`files/configarr.yml`), arrconf (`files/arrconf.yml`).

### Helm umbrella & Renovate

- [ ] **REQ-umbrella-deployment**: Une seule ArgoCD Application `arr-stack` dans `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` déploie 9 apps via le chart umbrella. Suppression des 9 ArgoCD Application unitaires + `charts/configarr/` côté my-kluster après Phase 4. Sync `automated.selfHeal: true` + `automated.prune: true` + `ServerSideApply: true`.
- [ ] **REQ-renovate-image-tracking**: Annotation `# renovate: image=<repo>` au-dessus de chaque image dans `values.yaml`. `renovate.json` avec `customManagers` regex matchant `values.yaml`. Bumps minor/patch en automerge, majors en revue manuelle. Côté my-kluster, Renovate suit `targetRevision: vX.Y.Z` dans `arr-stack-app.yaml`.
- [ ] **REQ-helm-validation**: `helm lint charts/arr-stack/` et `helm template charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -` passent en CI. `values.yaml` parse contre `values.schema.json` (bloquant).
- [ ] **REQ-pr-to-cluster-latency**: PR mergée → tag de release → Renovate PR sur my-kluster → ArgoCD sync → CronJob run < 1 h. Possible run manuel `kubectl create job --from=cronjob/arrconf` pour accélérer.

### Documentation & roadmap

- [ ] **REQ-readme-onboarding**: README permet à un autre dev (ou toi-dans-3-mois) de comprendre et déployer en moins de 30 min. Vue d'ensemble + structure + commandes clés + bootstrap (API keys, secrets, 1er déploiement) + liens vers `spec.md` / `CLAUDE.md` / my-kluster.
- [x] **REQ-phase-roadmap**: Roadmap progressive de-risk en 9 phases (0 à 8), chaque phase livrable indépendamment. Méta-requirement validé quand la roadmap est instanciée et chaque phase respecte ses critères de fin (cf spec.md §7).

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Apps additionnelles

- **APPV2-01**: Bazarr (sous-titres) — ajoutable sans repenser l'architecture (nouveau reconciler + chart dep)
- **APPV2-02**: Lidarr (musique) — idem
- **APPV2-03**: Whisparr (adulte) — idem
- **APPV2-04**: Readarr (livres / audiobooks) — idem

### Operational maturity

- **OPSV2-01**: Migration ESO/Akeyless globale (cf REQ-secret-management Phase 8 — déjà inscrite mais explicitement optionnelle / post-MVP)
- **OPSV2-02**: Release automation (release-please ou semantic-release) — résolution Q4 ; v1 acceptable avec tags manuels
- **OPSV2-03**: cosign signing de l'image arrconf

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Migration data lab / infra / perso vers arr-stack | arr-stack se limite à la stack média ; les autres domaines restent dans `my-kluster` (NG1) |
| Outil générique multi-tenant | Dimensionné homelab single-user (NG2) |
| 100 % de couverture des APIs | On couvre uniquement ce que l'auteur utilise (NG3) |
| `quality_profiles` / `custom_formats` / `quality_definitions` / `media_naming` dans arrconf | Scope exclusif de configarr (ADR-5, NG4 ; arrconf lèvera `ScopeViolationError`) |
| Bootstrap automatique des API keys | 1ère API key toujours via UI, arrconf prend le relais (NG5, REQ-bootstrap-exception) |
| Multi-instance Sonarr/Radarr (sonarr-tv / sonarr-anime / sonarr-family + équivalents Radarr) | Single instance + tags retenu (ADR-7) |
| Buildarr / Terraform devopsarr / Recyclarr / Flemmarr-as-is / Ansible / operators K8s | Évalués et rejetés (cf intel/context.md alternatives-rejected) |
| Apply distant depuis GitHub Actions | Cluster privé inaccessible (C1) ; reconciliation in-cluster only (CronJob) |
| Tag `:latest` en production | Pinning obligatoire (C9) ; Phase 4 traite les `:latest` existants |
| Déploiement direct depuis arr-stack (`helm install` / `kubectl apply`) | Toujours via my-kluster + ArgoCD |
| Test cluster sans snapshot baseline préalable | Garde-fou ADR-6 — `tools/snapshot/snapshot.sh` est le filet de sécurité |
| Sonarr v3 (et plus généralement multi-versions des APIs *arr) | Recommandation Q7 : tester sur v4+ uniquement (déjà la version déployée), documenter comme prérequis |
| `prune: true` par défaut | Garde-fou Q8 / REQ-prune-opt-in : opt-in explicite par section uniquement |

## Traceability

Mapping `REQ-* → Phase`. Chaque requirement v1 mappé à exactement une phase (phase de réalisation principale). Les requirements transverses (idempotence, test coverage, schema-gen) sont rattachés à la phase où la pratique est instaurée pour la 1ère fois ; elles continuent d'être renforcées dans les phases suivantes (cf spec.md §7 critères de fin).

| Requirement | Phase | Status |
|-------------|-------|--------|
| REQ-baseline-snapshot | Phase 0 | Complete |
| REQ-phase-roadmap | Phase 0 | Complete |
| REQ-cli-subcommands | Phase 1 | Pending |
| REQ-yaml-autocomplete | Phase 1 | Pending |
| REQ-idempotence | Phase 1 | Pending |
| REQ-prune-opt-in | Phase 1 | Pending |
| REQ-managed-tag | Phase 1 | Pending |
| REQ-test-coverage | Phase 1 | Pending |
| REQ-drift-detection | Phase 2 | Complete |
| REQ-bootstrap-exception | Phase 2 | Pending |
| REQ-secret-management | Phase 2 | Pending |
| REQ-configarr-coexistence | Phase 3 | Complete |
| REQ-config-as-code | Phase 4 | Pending |
| REQ-umbrella-deployment | Phase 4 | Pending |
| REQ-renovate-image-tracking | Phase 4 | Pending |
| REQ-helm-validation | Phase 4 | Pending |
| REQ-pr-to-cluster-latency | Phase 4 | Pending |
| REQ-readme-onboarding | Phase 4 | Pending |
| REQ-app-coverage | Phases 1, 3, 5, 6, 7 | Complete |

**Notes traçabilité** :

- **REQ-app-coverage** est multi-phases parce que la couverture des apps s'étend incrémentalement : Phase 1 (Sonarr download_clients seul, POC), Phase 3 (Sonarr étendu + Radarr + Prowlarr full), Phase 5 (qBittorrent + split tags), Phase 6 (Seerr), Phase 7 (Jellyfin). Considérée "atteinte" à la fin de Phase 7.
- **REQ-secret-management** est rattaché à Phase 2 (pratique instaurée à la première écriture cluster — `arrconf-secret.yaml` manuel), avec rappel/migration optionnelle en Phase 8 (ESO).
- **REQ-readme-onboarding** est rattaché à Phase 4 (au moment où l'umbrella est déployable end-to-end ; le README final couvre toute la stack). Une version minimale est créée dès Phase 0/1.
- **REQ-phase-roadmap** est un méta-requirement : il est techniquement satisfait quand la ROADMAP.md existe (Phase 0 bootstrap), et son respect est vérifié à chaque transition de phase (`gsd-progress` / `gsd-transition`).

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-07*
*Last updated: 2026-05-07 after gsd-import / new-project-from-ingest bootstrap*
