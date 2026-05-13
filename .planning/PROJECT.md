# arr-stack

## What This Is

arr-stack est un projet de plateforme média **fully-as-code** déployée sur le cluster MicroK8s personnel `my-kluster`. Il regroupe (1) un script Python custom `arrconf` qui réconcilie depuis YAML déclaratif vers les APIs REST de Sonarr / Radarr / Prowlarr / qBittorrent / Seerr / Jellyfin, et (2) un Helm umbrella chart qui empaquette toute la stack média (apps + arrconf + configarr) en un déploiement atomique versionné consommé par une seule ArgoCD Application dans `my-kluster`.

Cible utilisateur : Thomas (tom333), homelab single-tenant. Pattern transposable mais non multi-tenant.

## Core Value

Aucune intervention UI nécessaire pour configurer Sonarr / Radarr / Prowlarr / qBittorrent / Seerr / Jellyfin après bootstrap — tout changement passe par une PR sur `arr-stack` et se matérialise en cluster en moins d'1 h via ArgoCD + CronJob arrconf.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- [x] **REQ-drift-detection** — Drift UI détecté et corrigé au prochain run d'arrconf. Validated in Phase 02.2: fully-automated priority restore + credential survival (composite dispositive: `merge_field_omitted_credential ≥ 1`, `sonarr_qbit_test_http_status=200`, `manual_nudge_used=NO`). v0.1.6.

### Active

<!-- Current scope. Building toward these. -->

- [ ] **REQ-config-as-code** — Config Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin entièrement déclarative dans YAML versionné Git
- [ ] **REQ-drift-detection** — Drift UI détecté et corrigé au prochain run d'arrconf
- [ ] **REQ-idempotence** — Ré-exécution N fois = no-op si YAML inchangé
- [ ] **REQ-umbrella-deployment** — Une seule ArgoCD Application dans my-kluster pull `charts/arr-stack/`
- [ ] **REQ-renovate-image-tracking** — Renovate suit toutes les images dans `values.yaml` via `customManagers`
- [ ] **REQ-configarr-coexistence** — configarr et arrconf cohabitent avec scopes orthogonaux (frontière dure)
- [ ] **REQ-baseline-snapshot** — Baseline lossless capturée avant toute écriture, versionnée Git
- [ ] **REQ-bootstrap-exception** — API keys initiales hors scope (UI manuelle), arrconf prend le relais
- [ ] **REQ-pr-to-cluster-latency** — PR → cluster < 1 h
- [ ] **REQ-helm-validation** — `helm template … | kubeconform -` passe en CI
- [ ] **REQ-test-coverage** — Couverture pytest ≥ 70 % sur `differ.py` et `reconcilers/`
- [ ] **REQ-readme-onboarding** — README permet onboard < 30 min
- [ ] **REQ-secret-management** — Secrets bootstrap dans `my-kluster/secrets/` jusqu'à migration ESO (Phase 8)
- [ ] **REQ-cli-subcommands** — arrconf expose `apply` / `dump` / `diff` / `schema-gen`
- [ ] **REQ-yaml-autocomplete** — Autocomplétion VS Code via JSON Schema généré par `arrconf schema-gen`
- [ ] **REQ-prune-opt-in** — `prune: false` par défaut, opt-in par section
- [ ] **REQ-managed-tag** — Ressources créées par arrconf taggées `arrconf-managed`
- [ ] **REQ-phase-roadmap** — Livraison progressive en 9 phases (0 à 8), chaque phase livrable indépendamment
- [ ] **REQ-app-coverage** — Couvrir Sonarr / Radarr / Prowlarr / qBittorrent / Seerr / Jellyfin (FlareSolverr et Cleanuparr Helm-only)

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- **Migrer le reste de my-kluster (data lab, infra, perso)** — arr-stack se limite à la stack média ; data/infra/perso restent dans `my-kluster`
- **Outil générique multi-tenant** — Dimensionné pour 1 cluster, 1 utilisateur (homelab)
- **100 % de couverture des APIs** — On couvre uniquement ce que l'auteur utilise réellement
- **quality_profiles / custom_formats / quality_definitions / media_naming dans arrconf** — Scope exclusif de configarr (ADR-5, frontière dure ; arrconf lèvera `ScopeViolationError` si tenté)
- **Bootstrap automatique des API keys** — 1ère API key toujours via UI ; compte admin Jellyfin créé manuellement avant Phase 7
- **Multi-instance Sonarr/Radarr** — Single instance + tags retenu (ADR-7) ; reconsidérer uniquement si BDD sature ou si Q10 conclut Seerr ne peut pas router par tag
- **Buildarr / Terraform devopsarr / Recyclarr / Flemmarr / Ansible / operators K8s** — Évalués et rejetés (cf intel/context.md alternatives-rejected ; principal blocant : cluster privé inaccessible depuis GitHub Actions)
- **Apply distant depuis GitHub Actions** — Cluster privé, GHA ne peut pas atteindre les APIs *arr ; reconciliation in-cluster uniquement (CronJob)
- **Tag `:latest` en production** — Toutes les images doivent être pinnées (Phase 4 traite les `:latest` existants : qbittorrent, flaresolverr, cleanuparr)
- **Bazarr / Lidarr / Whisparr / Readarr** — v2 potentiel, ajoutables sans repenser l'architecture
- **Déploiement direct depuis ce repo** — Toujours via my-kluster + ArgoCD ; jamais `helm install` ou `kubectl apply` depuis arr-stack

## Context

**Environnement technique** :
- Cluster MicroK8s single-node, GitOps via ArgoCD, domaine `*.tgu.ovh`, namespace `selfhost`
- 9 ArgoCD Applications déjà déployées dans `my-kluster/argocd/argocd-apps/` (sonarr 4.0.17, radarr 6.1.1, prowlarr 2.3.5, cleanuparr `latest`, configarr 1.16.0, qbittorrent `latest`, seerr v3.2.0, flaresolverr `latest`, jellyfin 10.11.8) — toutes via `bjw-s/app-template 4.6.2`
- Chart custom `charts/configarr/` à migrer dans arr-stack (Phase 4)
- hostPath partagé `/opt/media-stack/torrents` (qBit + Sonarr + Radarr) ; PVC NFS `media-nas-pvc` (Sonarr + Radarr + Jellyfin)
- ESO + Akeyless dispo dans le cluster, pas encore branchés sur arr-stack (secret manuel jusqu'à Phase 8)
- Stack technique imposée : Python 3.13 + httpx + pydantic v2 + ruyaml ; Helm 3 ; pas de Terraform ; pas de Kustomize

**Existant pré-bootstrap** : repo arr-stack contient uniquement `spec.md`, `CLAUDE.md`, et `.planning/intel/*` au moment de l'ingestion (2026-05-07). Aucun code, aucun chart, aucune CI.

**Pattern réutilisé** : `tom333/cv` est déjà un repo séparé pull par ArgoCD — pattern connu et fonctionnel.

**GSD intégration** : `spec.md` est la source ingérée par `gsd-import`. Chaque phase suit le cycle `discuss-phase → plan-phase → execute-phase → verify-work`. Les ambiguïtés (Q1-Q10 ci-dessous) sont résolues en `discuss-phase` avant codage.

## Constraints

- **Réseau (NFR)** : Cluster privé — GitHub Actions ne peut PAS atteindre les APIs *arr ; apply in-cluster only (CronJob), pas de Terraform Cloud, pas d'apply distant
- **Image distribution (NFR)** : Image arrconf hébergée sur GHCR public `ghcr.io/tom333/arr-stack-arrconf` — pull anonyme, pas de imagePullSecret
- **APIs (api-contract)** : APIs *arr accessibles via Services K8s internes `http://<app>.selfhost.svc.cluster.local:<port>` — arrconf doit utiliser ces URLs, pas les ingress publics
- **Stack Python (NFR)** : Python 3.13 + httpx + pydantic v2 + ruyaml + structlog/stdlib + pytest + respx + ruff + mypy (strict sur signatures publiques)
- **Helm 3 (NFR)** : Helm 3 charts en première intention ; pas de Kustomize
- **Pas de Terraform (NFR)** : décision liée à C1 (cluster privé, providers immatures qBit/Seerr)
- **Cluster (NFR)** : MicroK8s single-node, `microk8s-hostpath` storageClass `WaitForFirstConsumer`, pas de StatefulSets HA
- **Conventions cluster (protocol)** : namespace `selfhost`, project ArgoCD `selfhost-project`, ingress NGINX + cert-manager `letsencrypt-prod`, oauth2-proxy pour UIs sensibles (sauf Jellyfin)
- **Renovate compat (protocol)** : Renovate global tom333 doit rester compatible ; toute config Renovate dans arr-stack respecte ce setup ; annotations `# renovate: image=…` obligatoires au-dessus de chaque image dans `values.yaml`
- **Pas de `:latest` en prod (protocol)** : pinner les tags `:latest` existants (qbittorrent, flaresolverr, cleanuparr) en Phase 4
- **Frontière arrconf/configarr (protocol — CRITIQUE)** : configarr est seul propriétaire de `quality_profiles` / `custom_formats` / `quality_definitions` / `media_naming` ; arrconf doit lever `ScopeViolationError` si tentative d'écriture sur ces endpoints (ADR-5)
- **Variables d'environnement (api-contract)** : arrconf lit UNIQUEMENT depuis env (jamais fichier de secrets) — `SONARR_API_KEY`, `RADARR_API_KEY`, `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY`, `ARRCONF_LOG_LEVEL`, `ARRCONF_DRY_RUN`
- **Image Docker arrconf (NFR)** : base `python:3.13-slim`, USER `1000:1000`, multi-stage build, ~80 MB cible, tagging `:vX.Y.Z` / `:sha-<short>` / `:latest`
- **Exit codes CLI (api-contract)** : 0 succès, 1 app failure, 2 erreur config, 3 (sur `diff`) drift détecté
- **Workflow snapshot (protocol)** : re-snapshot raw AVANT toute Phase qui touche un nouveau scope ; tous les snapshots committés (NE PAS ignorer dans `.gitignore`) ; toujours `--dry-run` la première fois
- **Pattern single-instance + tags (protocol)** : 1 Sonarr `main` + 1 Radarr `main`, 3 tags (`tv`/`anime`/`family`) + 3 root folders + 3 download clients par instance ; 6 catégories qBit
- **Tests (protocol)** : `respx` pour mocker httpx ; aucun test ne doit appeler les vraies APIs en CI ; fixtures sanitisées dans `tests/fixtures/<app>_<resource>.json`
- **CI workflows (protocol)** : `arrconf-image.yml`, `chart-lint.yml`, `tests.yml` obligatoires ; `release.yml` ultérieur (Q4)
- **Renovate config (schema)** : `renovate.json` avec `extends: ["config:recommended"]`, `customManagers` regex sur `values.yaml`, `packageRules` automerge minor/patch sur `custom.regex` / `helm-values` / `helmv3`
- **Garde-fous CLAUDE.md (protocol)** : pas de secrets committés, pas de `:latest` en prod, pas d'écriture sur endpoints frontière configarr, pas d'amend de tag, pas de duplication config configarr, pas d'API réelle dans tests CI, pas de dep Python non-pinnée, pas de changement scope sans ADR, pas de déploiement direct, pas de merge avec drift major non-validé, pas de suppression annotation Renovate, pas de `prune: true` par défaut, pas de test cluster sans snapshot préalable

## Key Decisions

<decisions>
<!-- LOCKED ADRs from spec.md §11. Out-of-scope for re-litigation. Full rationale: spec.md §11. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| **ADR-1 — Script Python custom (vs Buildarr / Terraform / Flemmarr)** | Buildarr en dérive (pas de plugin Seerr), Terraform providers immatures qBit/Seerr + cluster privé inaccessible depuis GHA, Flemmarr inspiration mais on veut maîtriser et étendre. Stack Python 3.13 + httpx + pydantic v2 + ruyaml. Voir spec.md §11 ADR-1. | — Pending |
| **ADR-2 — Helm dependencies sur app-template (Option A)** | `Chart.yaml` `dependencies:` sur `bjw-s/app-template` avec un alias par service. Pas de duplication, Renovate suit naturellement via `helmv3`. Risque : multi-alias capricieux (à valider Phase 4). Voir spec.md §11 ADR-2. | — Pending |
| **ADR-3 — Image arrconf sur GHCR public** | `ghcr.io/tom333/arr-stack-arrconf` visibilité publique. Cluster pull anonyme (pas de imagePullSecret), GitHub Actions push avec GITHUB_TOKEN, Renovate suit GHCR. Voir spec.md §11 ADR-3. | — Pending |
| **ADR-4 — Repo séparé (vs extension my-kluster)** | Repo dédié `github.com/tom333/arr-stack`, distinct de `my-kluster`. arrconf est du vrai code logiciel, umbrella casse Renovate dans my-kluster, versionnement atomique permis. Une seule ArgoCD Application dans my-kluster pull ce repo. Voir spec.md §11 ADR-4. | — Pending |
| **ADR-5 — configarr conservé pour son scope (frontière dure)** | configarr seul propriétaire de quality_profiles / custom_formats / quality_definitions / media_naming. arrconf NE TOUCHE PAS à ces endpoints (refus codé en dur, `ScopeViolationError`). Tout changement de scope nécessite un nouvel ADR. Voir spec.md §11 ADR-5. | — Pending |
| **ADR-6 — Snapshot baseline avant toute écriture** | Workflow snapshot obligatoire en 4 niveaux : Phase 0 Bash standalone (raw JSON), Phase 1 `arrconf dump` (YAML structuré), Phase 2 dry-run au 1er run cluster, Phases 3-7 re-snapshot à chaque phase qui touche un nouveau scope. Snapshots versionnés Git (lossless, pas de secret). Voir spec.md §11 ADR-6. | — Pending |
| **ADR-7 — Single instance Sonarr/Radarr + tags (vs multi-instance)** | 1 Sonarr `main` + 1 Radarr `main` ; différenciation tv/anime/family via 3 tags + 3 root folders + 3 download clients par instance + 6 catégories qBit + 3 quality profiles configarr. Volumétrie homelab modérée, BDD SQLite tient. Multi-instance rejeté (×3 ressources, complexité GitOps). Reconsidérer uniquement si BDD sature ou Q10 conclut Seerr ne peut pas router par tag. Voir spec.md §11 ADR-7. | — Pending |

</decisions>

## Open Questions

Questions non décidées dans la spec — à résoudre en `discuss-phase` avant les phases concernées. NE SONT PAS des décisions (à ne pas confondre avec les ADRs ci-dessus).

| ID | Question | Phase de résolution | Notes |
|----|----------|---------------------|-------|
| **Q1** | Compatibilité API Seerr (`ghcr.io/seerr-team/seerr` v3.2.0) vs Overseerr/Jellyseerr | **Phase 6** | Vérifier `/api/v1/settings/services`, `/api/v1/user`, `/api/v1/request` ; bloque la phase si incompatible |
| **Q2** | Helm dependencies vs sub-charts (multi-alias syntax) | **Phase 4** | Techniquement résolue par ADR-2 (Option A) ; reste arbitrage syntaxique multi-alias `bjw-s/app-template` |
| **Q3** | Schedule arrconf (4 h comme configarr ? plus fréquent ?) | **Phase 2** | Recommandation initiale : 6 h |
| **Q4** | Mode de release (tags manuels / release-please / semantic-release) | **Phase 1 ou 2** | À arbitrer avant le 1er release sémantique |
| **Q5** | Cohabitation arrconf/configarr sur quality_profiles | Tranchée par **ADR-5** | À documenter dans le code (refus côté reconciler — `ScopeViolationError`) |
| **Q6** | Backup du state arrconf | **Phase 1 ou 3** | Recommandation : tag `arrconf-managed` (cf REQ-managed-tag) ; à confirmer |
| **Q7** | Compatibilité multi-versions des APIs *arr | **Phase 1** | Recommandation : tester sur Sonarr v4+ uniquement, documenter comme prérequis (pas de v3) |
| **Q8** | Stratégie `prune` par défaut | **Phase 1** | Recommandation : `prune: false` par défaut, opt-in par section (cf REQ-prune-opt-in) |
| **Q9** | Jellyfin auth header (`X-Emby-Token` / `Authorization: MediaBrowser` / `?api_key=`) | **Phase 7** | À valider en pratique sur 10.11.8 ; `client_base.py` doit pouvoir overrider la stratégie d'auth par app |
| **Q10** | Routing tags Seerr → Sonarr/Radarr (single instance + tags ADR-7) | **Phase 6** | Seerr expose-t-il `defaultTags` par service ? Fallback documenté : tag par défaut `tv` + ré-tag manuel pour anime/family minoritaires |

## Frontière arrconf / configarr (CRITIQUE)

Frontière dure dérivée de **ADR-5**. Les ✅ sont obligatoires, les ❌ interdits par construction côté arrconf (lever `ScopeViolationError` si appelé).

| Resource | configarr | arrconf |
|---|:---:|:---:|
| Quality profiles | ✅ | ❌ |
| Custom formats | ✅ | ❌ |
| Quality definitions | ✅ | ❌ |
| Media naming | ✅ | ❌ |
| Indexers (Prowlarr → app sync) | ❌ | ✅ |
| Indexers (Prowlarr lui-même) | ❌ | ✅ |
| Download clients | ❌ | ✅ |
| Notifications | ❌ | ✅ |
| Root folders | ❌ | ✅ |
| Tags (y compris `arrconf-managed`) | ❌ | ✅ |
| Host config (UI port, auth, etc.) | ❌ | ✅ |
| qBittorrent settings | ❌ | ✅ |
| Seerr settings | ❌ | ✅ |
| Jellyfin libraries | ❌ | ✅ |
| Jellyfin users | ❌ | ✅ |
| Jellyfin server config (transcoding, networking) | ❌ | ✅ |
| Jellyfin plugins | ❌ | ✅ (best effort) |
| App sync Prowlarr | ❌ | ✅ |

---
*Last updated: 2026-05-10 after Phase 02.2 (v0.1.5/v0.1.6 hotfix — CR-01 gap closed, REQ-drift-detection validated)*
