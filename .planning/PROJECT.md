# arr-stack

## What This Is

arr-stack est un projet de plateforme média **fully-as-code** déployée sur le cluster MicroK8s personnel `my-kluster`. Il regroupe (1) un script Python custom `arrconf` qui réconcilie depuis YAML déclaratif vers les APIs REST de Sonarr / Radarr / Prowlarr / qBittorrent / Seerr / Jellyfin, et (2) un Helm umbrella chart qui empaquette toute la stack média (apps + arrconf + configarr) en un déploiement atomique versionné consommé par une seule ArgoCD Application dans `my-kluster`.

Cible utilisateur : Thomas (tom333), homelab single-tenant. Pattern transposable mais non multi-tenant.

## Current State

**Shipped: v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening** (2026-05-24). Jellyfin emits 10 `VirtualFolder` libs (1 per Category) — reverses D-07-LIB-01, makes Categories visible structurally in JellyCon/Kodi (LibreELEC salon) and every other Jellyfin client. `tools/arrconf-ui/**` covered by CI (`arrconf-ui-backend` triad + `arrconf-ui-frontend` quad) while staying architecturally isolated from `chart-lint.yml` (UI-only PRs do NOT trigger auto-tag). qBit POST credentials env-injected for Sonarr+Radarr with pre-flight gate + fail-fast `ConfigError`; UAT dispositive 9/9 + 9/9 qBit DCs HTTP 200 + 0 plan_actions on 2nd run (idempotence proven). Production cluster running arr-stack tag `v0.13.0` (with rescue tag `v0.12.1`) / arrconf image `:0.12.1`. Full archive: [`milestones/v0.5.0-ROADMAP.md`](milestones/v0.5.0-ROADMAP.md).

<details>
<summary>Previous state — v0.4.0 Categories cleanup + content discovery + local config UI (2026-05-23)</summary>

v0.2.0 transition layer fully ripped out (generators are the only source); SuggestArr deployed as 11th umbrella alias with Categories-aware routing via `SEER_ANIME_PROFILE_CONFIG`; `arrconf-ui` ships as FastAPI + Svelte 5 SPA editing `arrconf.yml` from the LAN with pydantic validation + ruyaml round-trip + dark theme. Production cluster ran chart `v0.8.2` / image `:0.7.0` at close. Archive: [`milestones/v0.4.0-ROADMAP.md`](milestones/v0.4.0-ROADMAP.md).

</details>

<details>
<summary>Earlier state — v0.3.0 Categories first-class (2026-05-22)</summary>

1 declarative `categories[]` entry in `arrconf.yml` propagates to all 6 apps + chart initContainer + dispositive idempotence on live cluster. Production cluster ran chart `v0.7.0` / image `:0.6.7`. Archive: [`milestones/v0.3.0-ROADMAP.md`](milestones/v0.3.0-ROADMAP.md) + [audit](v0.3.0-MILESTONE-AUDIT.md) `passed_with_caveats`.

</details>

## Current Milestone: v0.6.0 arrconf observability — 4xx body logging

**Goal:** Plug the observability gap surfaced by the v0.5.0 Sonarr `PathExistsValidator` 400 incident — `arrconf/client_base.py` 4xx `HTTPStatusError` raises with no `response.text` excerpt, so client-side reconcile crashes lose the server's actual error message. Add `response.text[:500]` to the 4xx path symmetric with the existing 5xx logging, so future API regressions are debuggable on first occurrence instead of waiting 3 image versions.

**Target features:**

- **REQ-client-base-4xx-logging** — `_request` in `tools/arrconf/arrconf/client_base.py:80` logs `response.text[:500]` for 4xx responses (parallel to existing 5xx logging at line 80). New respx test verifies the body excerpt is included in the raised exception's structured log payload.

**Key context:**

- **Single-phase, single-requirement micro-milestone.** This is intentional — closes a specific v0.5.0 tech debt item without scope creep. Phase 19 continues numbering from v0.5.0's Phase 18.
- **2-line code change + 1 respx test + co-bump.** Smallest milestone in the project's history. Expected execution time: ~1-2 hours from plan to ship.
- **Driver = v0.5.0 incident.** Sonarr's `PathExistsValidator` 400 went unsurfaced for 3 image versions because `client_base.py` only logs `response.text[:200]` for 5xx (`if 500 <= response.status_code < 600:` at line 79). 4xx raises raw `HTTPStatusError` from `response.raise_for_status()` at line 81 — the actual JSON error array is invisible to `arrconf` logs. The Phase 18 UAT debug session captured the body via manual curl reproduction, but that was after the bug had blocked Phase 17's CronJob for weeks.

**Explicitly OUT of v0.6.0 scope:**

- **REQ-bazarr-addition** (Bazarr subtitles) — operator decision deferred
- **REQ-config-ui-git-integration** (auto-commit/push from arrconf-ui) — operator decision deferred
- **REQ-arrconf-ui-distribution** (packaging non-dev install) — deferred
- **REQ-config-ui-multi-config** (configarr.yml in same UI) — deferred, requires ADR-5 frontière re-check
- **REQ-suggestarr-ingress** (auto-submit) — deferred
- **HUMAN-UAT frontmatter standardization** — deferred, audit-open parser warning is minor
- **Phase 9 / Phase 10 HUMAN-UAT cluster scenarios** — v0.3.0 carry-forward maintenu
- **D-07-PLAYLIST-MGMT-NULL** — re-verify on Jellyfin 11.x upgrade (carry-forward inchangé)
- **REQ-jellyfin-collections** — superseded by v0.5.0's 10-libs (only re-surface if Kodi/JellyCon UAT shows a gap)

**Projected phases:** Phase 19 (single phase, single plan).

## Core Value

Aucune intervention UI nécessaire pour configurer Sonarr / Radarr / Prowlarr / qBittorrent / Seerr / Jellyfin après bootstrap — tout changement passe par une PR sur `arr-stack` et se matérialise en cluster en moins d'1 h via ArgoCD + CronJob arrconf.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- [x] **REQ-drift-detection** — v0.1.6 (Phase 02.2): fully-automated priority restore + credential survival (composite dispositive: `merge_field_omitted_credential ≥ 1`, `sonarr_qbit_test_http_status=200`, `manual_nudge_used=NO`).
- [x] **REQ-baseline-snapshot** — v0.2.0 (Phase 0 + per-phase before/after pairs). 11 snapshot dirs committed under `snapshots/`, ADR-6 discipline + anti-leak grep on every commit.
- [x] **REQ-cli-subcommands** — v0.2.0 (Phase 1+3). `arrconf apply / dump / diff / schema-gen` operational across all 6 apps; exit codes 0/1/2/3 per spec.
- [x] **REQ-yaml-autocomplete** — v0.2.0 (Phase 1, regen on every reconciler phase). `schemas/arrconf-schema.json` generated by `arrconf schema-gen`, modeline `# yaml-language-server: $schema=…` at top of every YAML; CI test gates regen.
- [x] **REQ-config-as-code** — v0.2.0 (Phase 4+). Full config for 6 apps in `charts/arr-stack/files/arrconf.yml` (540 lines). No UI intervention post-bootstrap.
- [x] **REQ-idempotence** — v0.2.0 (every reconciler phase). `arrconf dump | arrconf diff = 0 drift` proven dispositively for Sonarr (Phase 02.1), Radarr+Prowlarr (Phase 3), qBittorrent (Phase 5), Seerr (Phase 6), Jellyfin (Phase 7 SC#4 DIFF_EXIT=0).
- [x] **REQ-prune-opt-in** — v0.2.0 (Phase 1+). `prune: false` default everywhere; opt-in per section; Jellyfin libraries + users hardcoded `prune: false` regardless of YAML (D-07-LIB-01 + D-07-USERS-01 protection).
- [x] **REQ-managed-tag** — v0.2.0 (Phase 2.1+). `arrconf-managed` tag reconciled on Sonarr/Radarr/Prowlarr; Jellyfin has no tags concept (documented N/A in spec.md §11).
- [x] **REQ-test-coverage** — v0.2.0. pytest coverage 94.94% on `differ.py` + `reconcilers/` (Phase 7 verifier confirmed); ruff + mypy clean; respx-mocked, no real API calls in CI.
- [x] **REQ-configarr-coexistence** — v0.2.0 (Phase 3+). Hard scope frontier coded as `ScopeViolationError`; quality_profiles / custom_formats / quality_definitions / media_naming refused at reconciler entry.
- [x] **REQ-umbrella-deployment** — v0.2.0 (Phase 4). Single `arr-stack-app.yaml` ArgoCD Application; 9 unit Applications deleted; chart v0.5.2 in production.
- [x] **REQ-renovate-image-tracking** — v0.2.0 (Phase 4). `# renovate: image=…` annotations on all 10 images in `values.yaml`; `customManagers` regex matches.
- [x] **REQ-helm-validation** — v0.2.0 (Phase 4+5.1). `helm lint + kubeconform 1.33.0 + 5 guards` block on every PR via `chart-lint.yml`; `values.schema.json` parses cleanly.
- [x] **REQ-pr-to-cluster-latency** — v0.2.0 (Phase 7 cutover end-to-end). PR → auto-tag → image build → my-kluster bump → ArgoCD sync → CronJob run measured at < 1 h (Phase 7 dispositive completed in ~45 min including 2 chart-pin-loop iterations).
- [x] **REQ-bootstrap-exception** — v0.2.0 (Phase 7). 7 API keys sealed in `arrconf-env` SealedSecret; sealed-secrets controller pattern validated for JELLYFIN_API_KEY hot-add (~30s reconcile).
- [x] **REQ-app-coverage** — v0.2.0 (Phases 1, 3, 5, 6, 7). 6 *arr-stack apps managed declaratively: Sonarr (Phase 1+3), Radarr (Phase 3), Prowlarr (Phase 3), qBittorrent (Phase 5), Seerr (Phase 6), Jellyfin (Phase 7). FlareSolverr + Cleanuparr deployed via Helm only (env config).
- [x] **REQ-phase-roadmap** — v0.2.0 meta-req. Roadmap instantiated 2026-05-07, 11/12 phases shipped, each independently deliverable + verifiable.

### Validated (v0.5.0)

<!-- Shipped 2026-05-24 in v0.5.0. -->

- [x] **REQ-jellyfin-categories-as-libs** — v0.5.0 (Phase 16): `generate_jellyfin()` emits 10 `VirtualFolder` libs (1 per Category) instead of 2 super-libs. D-07-LIB-01 reversed by D-16-PRUNE-01. `_reconcile_libraries()` extended with CREATE + prune-gated DELETE. SC#1-2-3 validated live on cluster (10 libs in Jellyfin web UI ✓, 12 paths pruned from legacy super-libs ✓, prune re-locked false ✓). JellyCon LibreELEC UAT (SC#4) carry-forward non-blocking per D-16-JELLYCON-UAT-01.
- [x] **REQ-arrconf-ui-ci** — v0.5.0 (Phase 17): `tests.yml` path-filter extended to include `tools/arrconf-ui/**`; 2 new jobs (`arrconf-ui-backend` triad + `arrconf-ui-frontend` quad) green on closure commit `c53c9a3`. `chart-lint.yml` intentionally UNCHANGED — UI-only PRs do NOT trigger auto-tag (architectural SC#3 dispositive per D-17-WORKFLOW-01).
- [x] **REQ-qbit-post-credentials** — v0.5.0 (Phase 18): `_resolve_qbit_credentials_from_env()` helper in `_shared.py` + pre-flight gate in `__main__.py` (CR-02 auto-fix). 12 respx tests covering 5 SC + asymmetric env + idempotence. Cluster UAT dispositive: 9/9 Sonarr + 9/9 Radarr qBit DCs HTTP 200 on `/test`, 0 plan_actions on 2nd run.

### Active

<!-- Scoped for v0.6.0. -->

- [ ] **REQ-client-base-4xx-logging** — `tools/arrconf/arrconf/client_base.py:80` `_request` logs `response.text[:500]` for 4xx responses, symmetric with existing 5xx logging. New respx test verifies the body excerpt appears in the raised `HTTPStatusError` context. Driver: v0.5.0 Sonarr `PathExistsValidator` 400 incident (bug went unsurfaced for 3 image versions because 4xx response bodies were never logged).

<details>
<summary>Carry-forward to v0.7.0+ (not in v0.6.0 scope)</summary>

- [ ] **REQ-bazarr-addition** — Bazarr (subtitles) as 8th *arr-stack app. Operator decision.
- [ ] **REQ-config-ui-git-integration** — auto-commit/push from arrconf-ui. Operator decision.
- [ ] **REQ-arrconf-ui-distribution** — packaging arrconf-ui for non-dev install.
- [ ] **REQ-config-ui-multi-config** — configarr.yml editing in same UI (ADR-5 frontière re-check needed).
- [ ] **REQ-suggestarr-ingress** — SuggestArr ingress + auto-submit (currently port-forward + manual approval).
- [ ] **HUMAN-UAT frontmatter standardization** — convert all Phase HUMAN-UAT.md to YAML frontmatter for `audit-open` parser compatibility.

</details>

<details>
<summary>Carry-forward from v0.3.0 (UAT operator-exercise opt-in)</summary>

- [ ] **REQ-readme-onboarding** — README exists but not yet operator-validated against the < 30-min onboarding metric. Will be revisited when an operator other than the author tries to bootstrap.
- [x] **REQ-secret-management** — sealed-secrets baseline is stable. No external-secret migration planned (REQ-eso-akeyless-migration retired 2026-05-22). Considered closed.

</details>

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
- sealed-secrets baseline en place côté my-kluster (bootstrap secrets `arrconf-env` + `configarr-env` gérés via Bitnami sealed-secrets — pas de plan de migration externe-secret)
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

<details>
<summary>Archived milestone scopes (v0.2.0 + v0.3.0 + v0.4.0)</summary>

- v0.2.0 forceSave fix — see [`MILESTONES.md`](MILESTONES.md) + [`milestones/v0.2.0-ROADMAP.md`](milestones/v0.2.0-ROADMAP.md)
- v0.3.0 Categories first-class — see [`milestones/v0.3.0-ROADMAP.md`](milestones/v0.3.0-ROADMAP.md) + [`v0.3.0-MILESTONE-AUDIT.md`](v0.3.0-MILESTONE-AUDIT.md)
- v0.4.0 Categories cleanup + content discovery + local config UI — see [`milestones/v0.4.0-ROADMAP.md`](milestones/v0.4.0-ROADMAP.md)

</details>

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
| **Q1** | ~~Compatibilité API Seerr (`ghcr.io/seerr-team/seerr` v3.2.0) vs Overseerr/Jellyseerr~~ | **RESOLVED Phase 6** | All 4 endpoints PUT-probed live (06-01 evidence `q1-put-probe.txt` HTTP 200); Pitfall 3 wrong on `activeProfileName` excludability — D-06-OPENAPI-01 hotfix shipped in `:0.4.4`. Seerr v3.2.0 API confirmed compatible. |
| **Q2** | Helm dependencies vs sub-charts (multi-alias syntax) | **Phase 4** | Techniquement résolue par ADR-2 (Option A) ; reste arbitrage syntaxique multi-alias `bjw-s/app-template` |
| **Q3** | Schedule arrconf (4 h comme configarr ? plus fréquent ?) | **Phase 2** | Recommandation initiale : 6 h |
| **Q4** | Mode de release (tags manuels / release-please / semantic-release) | **Phase 1 ou 2** | À arbitrer avant le 1er release sémantique |
| **Q5** | Cohabitation arrconf/configarr sur quality_profiles | Tranchée par **ADR-5** | À documenter dans le code (refus côté reconciler — `ScopeViolationError`) |
| **Q6** | Backup du state arrconf | **Phase 1 ou 3** | Recommandation : tag `arrconf-managed` (cf REQ-managed-tag) ; à confirmer |
| **Q7** | Compatibilité multi-versions des APIs *arr | **Phase 1** | Recommandation : tester sur Sonarr v4+ uniquement, documenter comme prérequis (pas de v3) |
| **Q8** | Stratégie `prune` par défaut | **Phase 1** | Recommandation : `prune: false` par défaut, opt-in par section (cf REQ-prune-opt-in) |
| **Q9** | Jellyfin auth header (`X-Emby-Token` / `Authorization: MediaBrowser` / `?api_key=`) | **Phase 7** | À valider en pratique sur 10.11.8 ; `client_base.py` doit pouvoir overrider la stratégie d'auth par app |
| **Q10** | ~~Routing tags Seerr → Sonarr/Radarr (single instance + tags ADR-7)~~ | **RESOLVED Phase 6** | Native: `animeTags` + `activeAnimeDirectory` + `activeAnimeProfileId` exposed per service (D-06-Q10-01); fallback: arrconf `content_tags` step (D-06-RETAG-01) on Sonarr (family+anime) + Radarr (family only, Pitfall 5 enforced). Native production validation deferred — `06-HUMAN-UAT.md` tracks the TVDB-anime-classified series test. |

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

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-24 — v0.6.0 milestone scoped (single-phase observability micro-milestone — client_base.py 4xx body logging).*
