# arr-stack

## What This Is

arr-stack est un projet de plateforme média **fully-as-code** déployée sur le cluster MicroK8s personnel `my-kluster`. Il regroupe (1) un script Python custom `arrconf` qui réconcilie depuis YAML déclaratif vers les APIs REST de Sonarr / Radarr / Prowlarr / qBittorrent / Seerr / Jellyfin, et (2) un Helm umbrella chart qui empaquette toute la stack média (apps + arrconf + configarr) en un déploiement atomique versionné consommé par une seule ArgoCD Application dans `my-kluster`.

Cible utilisateur : Thomas (tom333), homelab single-tenant. Pattern transposable mais non multi-tenant.

## Current State

**Milestone complete: v0.9.0 configarr-in-UI + Jellyfin skip-intro** (2026-05-31, 4/4 phases, 13/13 plans). Deux features hétérogènes livrées : (1) **Jellyfin Intro Skipper** (Phase 24, arrconf `:0.17.0`) — reconciler étendu pour enregistrer le repo plugin, l'installer via le two-run model (Run N queue + restart opérateur unique, Run N+1 enable+config `MaxParallelism=1`) et activer `EnableChapterImageExtraction` sur les 10 libs ; ADR-9 inverse D-07-PLUGINS-01 en install-capable ; vérification opérateur live SC#1-4 PASS + spike Kodi `service.jellyskip` = ACCEPT. (2) **configarr-in-UI** (Phases 25-27) — `arrconf-ui` édite désormais `configarr.yml` via formulaire schema-driven (`ConfigarrRootConfig` pydantic, 4 endpoints, anti-leak `!env`/`!secret`), avec pickers TRaSH (CF par nom + QP append-only) et référence Recyclarr read-only, catalogue TRaSH baké au build (SHAs pinnés, zéro HTTP runtime). ADR-5 intact des deux côtés. Production cluster arrconf `:0.17.0`. **v0.9.0 archivé 2026-05-31** (pas de git tag GSD — `v0.9.0` collisionne avec un tag chart-release ; archive planning-only). 5 items deferred (Phase 27 UAT/verification operator-pending, etc. — voir STATE.md). **v0.10.0 en cadrage** (intention-layer design ébauché, commit `5bdd7f2`).

<details>
<summary>Previous state — v0.8.0 Categories cleanup — v0.2.0 legacy migration close-out (2026-05-27)</summary>

Migration v0.2.0→v0.3.0 Categories à moitié appliquée fermée côté config : audit (P20), filesystem+metadata migration (P21), arrconf prune reconciler `:0.15.0` + live cleanup (P22), UAT dispositive (P23). CAT-CLEANUP-04 fermé par UAT opérateur live. Archive: [`milestones/v0.8.0-ROADMAP.md`](milestones/v0.8.0-ROADMAP.md) (audit `tech_debt`, aucun blocker).

</details>

<details>
<summary>Previous state — v0.7.0 Media stack scope closure (2026-05-25)</summary>

Stack média déclarée **complète et fermée** à 9 apps + arrconf + configarr. Bazarr / Lidarr / Whisparr / Readarr explicitement hors scope. Doc-only zero-phase milestone. Archive: [`milestones/v0.7.0-ROADMAP.md`](milestones/v0.7.0-ROADMAP.md).

</details>

<details>
<summary>Earlier state — v0.6.0 arrconf observability 4xx body logging (2026-05-25)</summary>

`arrconf/client_base.py` `_request` emits `client_4xx` structlog warning with `response.text[:500]` body excerpt before raising `httpx.HTTPStatusError`. 5 respx tests (416 total). Closes v0.5.0 observability tech debt. Single-phase micro shipped via `/gsd-quick` (commit `9726d81`). Archive: [`milestones/v0.6.0-ROADMAP.md`](milestones/v0.6.0-ROADMAP.md).

</details>

<details>
<summary>Earlier state — v0.5.0 Jellyfin Categories-as-libs + CI/UX hardening (2026-05-24)</summary>

Jellyfin émet 10 `VirtualFolder` libs (1 par Category). arrconf-ui CI coverage. qBit POST credentials env-injected pour Sonarr+Radarr avec pre-flight gate. Archive: [`milestones/v0.5.0-ROADMAP.md`](milestones/v0.5.0-ROADMAP.md).

</details>

<details>
<summary>Even earlier — v0.4.0 Categories cleanup + content discovery + local config UI (2026-05-23)</summary>

v0.2.0 transition layer fully ripped out (generators are the only source); SuggestArr deployed as 11th umbrella alias with Categories-aware routing via `SEER_ANIME_PROFILE_CONFIG`; `arrconf-ui` ships as FastAPI + Svelte 5 SPA editing `arrconf.yml` from the LAN with pydantic validation + ruyaml round-trip + dark theme. Archive: [`milestones/v0.4.0-ROADMAP.md`](milestones/v0.4.0-ROADMAP.md).

</details>

## Current Milestone: v0.10.0 — Couche d'intention (méta-orchestrateur, tranche 1)

**Goal:** Généraliser le pattern `categories[]` en une couche d'intention : `intent.yml` (seul fichier hand-edited) → `arrconf generate` (fonction pure) → configs verbeuses générées + committées → `apply`/configarr reconcile (inchangé). Livré par tranches (approche P2 incrémentale, pas de big-bang sur un prod qui marche). Design validé : [`v0.10.0-intention-layer-DESIGN.md`](v0.10.0-intention-layer-DESIGN.md) (commit `5bdd7f2`).

**Target features (tranche 1):**

- **REQ-intent-layer** — `intent.yml` + `arrconf generate` : sous-commande CLI qui transforme l'intention en configs verbeuses (`arrconf.yml`, `configarr.yml`, `qbit_manage/config.yml`, `cross-seed/config.js`), réutilise les générateurs purs `generators/`, garde-fou CI idempotence (`generate && git diff --exit-code`). Modèle G1 : local + committé.
- **REQ-sagas** — bloc `sagas` dans `intent.yml` → nouveau reconciler Radarr Collections (GET-match-`tmdbId` / PUT idempotent) + plugin Jellyfin `tmdbboxsets`. Sagas séries = présentation Jellyfin only (tag arrconf + BoxSet curé ; Sonarr sans collections).
- **REQ-cross-seed** — bloc `tools.cross_seed` → `config.js` généré + alias Helm `app-template` (consolidation d'un cross-seed déjà hors-stack).
- **REQ-qbit-manage** — bloc `tools.qbit_manage` → `config.yml` généré + alias Helm (share_limits/ratio, recyclebin, tracker_tags, orphaned ; `cat_update: False` impératif — arrconf possède les catégories qBit).
- **REQ-intent-boundary-adr** — nouvel ADR : couche d'intention + frontière *absorber (générer la config) vs déployer seulement (DB/UI-only)*.

**Key context:**

- **ADR-1** (custom Python vs IaC) **tient** ; **ADR-5** (frontière configarr) **tient + étendu** : la couche intention se place *au-dessus* d'arrconf ET configarr ; configarr reste seul à apply TRaSH.
- **Génération G1** : `arrconf generate` en local, YAML/JS générés committés (read-only), CI vérifie l'idempotence. G2 (in-cluster, perd diff Git/ADR-6) et G3 (commits auto, bruit auto-tagger) rejetés.
- **Hors tranche 1 → v0.10.x / v0.11** : UI-sur-intention ; `configarr.yml` (CF/QP) généré depuis l'intention ; autobrr ; transcodage (Tdarr/FileFlows non-OSS, différés).
- **SEED-002** (évaluer autobrr / Tdarr / decluttarr) résolu par le design §4 : autobrr ⏸️ différé, Tdarr/FileFlows ⏸️ différés (non-OSS), decluttarr ❌ rejeté (cleanuparr = sur-ensemble). Pas de req dédiée.
- **Phase numbering** : continue depuis Phase 27 (v0.9.0) → v0.10.0 démarre **Phase 28**.
- **5 questions ouvertes** (design §6, à résoudre en discuss/spec) : schéma `intent.yml` ; sagas séries OK ? ; migration cross-seed + `linkDirs` ; politique ratio qbit_manage ; `arrconf generate` CLI (ordre vs apply, garde-fou CI).

## Last Milestone: v0.9.0 — configarr-in-UI + Jellyfin skip-intro (shipped 2026-05-31)

**Goal (achieved):** Étendre l'UX opérateur (édition de `configarr.yml` depuis `arrconf-ui`, profils + custom formats pré-mâchés depuis TRaSH-Guides + Recyclarr) et l'UX de visionnage (skip-intro / crédits + chapter markers sur Jellyfin). 4/4 phases, 13/13 plans, 13/13 requirements validés. Détail : [`MILESTONES.md`](MILESTONES.md) + [`milestones/v0.9.0-ROADMAP.md`](milestones/v0.9.0-ROADMAP.md). Next: `/gsd-new-milestone` (v0.10.0 intention-layer ébauché, commit `5bdd7f2`).

**Target features:**

- **REQ-config-ui-multi-config** — Formulaire schema-driven dans `arrconf-ui` pour éditer `configarr.yml`. Quality profiles + custom formats **sourcés depuis TRaSH-Guides + Recyclarr** (picker par nom, pas de `trash_ids` à la main). `arrconf-ui` apprend le modèle configarr (quality_profiles / custom_formats / includes / templates). ADR-5 intact : l'UI édite le *fichier*, configarr reste seul à apply.
- **REQ-jellyfin-skip-intro** — Plugin Intro Skipper (détection intro **+** crédits/outro) via le reconciler Jellyfin plugins arrconf (best-effort) + extraction des chapter markers Jellyfin. Clients cibles = web/app/Swiftfin (support natif Media Segments, Jellyfin 10.10+) **et** Kodi/JellyCon salon (best-effort, dégradé possible).

**Key context:**

- **`config-ui-multi-config` = gros morceau.** Sourcer les profils/CF depuis TRaSH-Guides + Recyclarr implique de connaître le modèle de templates configarr + d'aller chercher les métadonnées TRaSH/Recyclarr. Recherche recommandée avant requirements.
- **ADR-5 préservé des deux côtés** : `arrconf-ui` édite `configarr.yml` (fichier), configarr applique ; arrconf ne touche jamais quality_profiles/custom_formats via API.
- **skip-intro multi-client** : marche sur web/app/Swiftfin, dégradé/absent sur Kodi salon (faisabilité à confirmer — spike Kodi possible).
- **Phase numbering** : continue depuis Phase 23 (v0.8.0) → v0.9.0 démarre **Phase 24**.
- **2 features hétérogènes** (config UX vs playback UX) → probablement 2+ phases séparées.

**Last shipped:** v0.8.0 Categories cleanup (Phases 20-23, archivé 2026-05-27, audit `tech_debt`). Détail : [`MILESTONES.md`](MILESTONES.md) + [`milestones/v0.8.0-ROADMAP.md`](milestones/v0.8.0-ROADMAP.md) + [`milestones/v0.8.0-phases/`](milestones/v0.8.0-phases/).

## Backlog (post-v0.9.0)

- **REQ-suggestarr-ingress** — SuggestArr ingress + auto-submit (currently port-forward + manual approval)
- **REQ-auto-tag-rescue-automation** — Carry-forward from v0.6.0: standardize chart-pin co-bump rescue. v0.5.0 + v0.6.0 both required it.
- **REQ-arrconf-dry-run-pr-gate** — GHA job qui run `arrconf apply --dry-run` sur chaque PR et comment le diff. Réutilise les snapshots ADR-6 déjà commités. ~1 phase.
- **REQ-radarr-sonarr-lists** — TMDb/Trakt list auto-import. Native Radarr/Sonarr feature unconfigured.
- **REQ-radarr-sonarr-release-profiles** — preferred/required/ignored keywords per tag. Different from configarr custom formats. Native Radarr/Sonarr scope, arrconf non-géré.

**Carry-forward (non-blocking)**:

- REQ-jellyfin-collections — superseded by v0.5.0's 10-libs
- D-07-PLAYLIST-MGMT-NULL — re-verify on Jellyfin 11.x upgrade
- Phase 9 / Phase 10 HUMAN-UAT cluster scenarios (v0.3.0 carry-forward)

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

### Validated (v0.6.0)

<!-- Shipped 2026-05-25 in v0.6.0. -->

- [x] **REQ-client-base-4xx-logging** — v0.6.0 (Phase 19 via /gsd-quick 260525-bj5): `_request` in `arrconf/client_base.py` emits `client_4xx` structlog warning with `response.text[:500]` body excerpt before `raise_for_status()` raises `httpx.HTTPStatusError`. 5 respx tests (411 → 416). Closes v0.5.0 observability tech debt.

### Validated (v0.8.0)

<!-- Shipped 2026-05-27 in v0.8.0. Milestone audit: tech_debt (no blockers). -->

- [x] **CAT-CLEANUP-01** — v0.8.0 (Phase 20): `arrconf audit` + `audit-verify` read-only legacy-state inventory CLI (`audit.py`, 26 respx tests, `AUTO_PATH_MAPPING` verbatim from CLAUDE.md filesystem table, verify-gate rejects `?`/`TBD` cells). Operator live audit resolved 2026-05-26.
- [x] **CAT-CLEANUP-02** — v0.8.0 (Phase 21): one-shot `tools/scripts/migrate-categories.py` (filesystem `mv` + qBit `setLocation` + Radarr/Sonarr API PUT + Jellyfin refresh); 21 *arr PUTs + 37 torrents relocated live, ADR-6 pre/post snapshots. **Caveat:** file-on-disk sub-clause partial — pre-existing disk drift left 10 records missing-on-disk (DB Category-anchored; operator follow-up tracked).
- [x] **CAT-CLEANUP-03** — v0.8.0 (Phase 22): `differ.force_prune` path + pydantic legacy-path guard on Sonarr/Radarr root_folders/tags/download_clients; shipped `arrconf:0.15.0` (chart co-bump 0.14.1→0.15.0, 455 tests). Live cleanup of 4 legacy roots + catch-all DC id=1 + 3 orphan torrents. **Tech debt:** no 22-VERIFICATION.md (cross-verified by P23); `force_prune=true` DELETE path unexercised live (surgical deletes used) — re-verify before `prune:true` in `arrconf.yml`.
- [x] **CAT-CLEANUP-04** — v0.8.0 (Phase 23): live operator UAT on `:0.15.0` — SC#1-4 PASS (legacy roots absent, Seerr→per-Category DC routing not catch-all, idempotent apply ×2). SC#5 PARTIAL-deferred (3 Jellyfin libs empty pending media FS migration — operator-accepted, out of scope).

### Active

<!-- Scoped for v0.10.0 — tranche 1 of the intention layer. Full set + REQ-IDs in REQUIREMENTS.md. -->

- [ ] **REQ-intent-layer** — `intent.yml` + `arrconf generate` (fonction pure → configs verbeuses committées, CI idempotence guard).
- [ ] **REQ-sagas** — Radarr Collections reconciler (PUT par `tmdbId`) + Jellyfin `tmdbboxsets` depuis `sagas` dans `intent.yml`.
- [ ] **REQ-cross-seed** — `config.js` généré + alias Helm (consolidation hors-stack).
- [ ] **REQ-qbit-manage** — `config.yml` généré + alias Helm (`cat_update: False` impératif).
- [ ] **REQ-intent-boundary-adr** — ADR couche d'intention + frontière absorber vs déployer.

<details>
<summary>Carry-forward (pre-v0.10.0)</summary>

- [ ] **REQ-suggestarr-ingress** — SuggestArr ingress + auto-submit (currently port-forward + manual approval).
- [ ] **REQ-auto-tag-rescue-automation** — NEW: standardize chart-pin co-bump rescue as a post-push hook or phase-final step. v0.5.0 + v0.6.0 both required manual rescue; third recurrence would justify automation.
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
- **Bazarr (sous-titres)** — v0.7.0 decision: pas de besoin réel. Les médias téléchargés ont les sous-titres burned-in ou Jellyfin/Kodi cherche les subs en natif au moment du watch. Bazarr résoudrait un problème qui n'existe pas dans ce homelab. Ne pas ré-évaluer sans un cas d'usage concret nouveau (e.g., contenu sans subs récurrent dans une langue précise).
- **Lidarr (musique) / Whisparr (adulte) / Readarr (livres)** — v0.7.0 decision: stack média = vidéo (séries + films) uniquement. Audio, écrit, et adult content sortent du périmètre intentionnellement. La phrase "ajoutable sans repenser l'architecture" (pré-v0.7.0) reste techniquement vraie mais n'est pas une intention.
- **Media stack additions au-delà des 9 apps actuelles** — v0.7.0 decision: la stack est complète et fermée. Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin/FlareSolverr/Cleanuparr/SuggestArr couvrent l'usage. Toute proposition d'ajouter un *arr passe par revue de cette décision.
- **Déploiement direct depuis ce repo** — Toujours via my-kluster + ArgoCD ; jamais `helm install` ou `kubectl apply` depuis arr-stack
- **arrconf-ui git-integration + distribution** — v0.9.0 scoping decision (confirme v0.7.0): l'UI reste un outil local lancé via `uv run`. Pas d'auto-commit/push depuis l'UI, pas de packaging non-dev. Le commit/push des changements `arrconf.yml` reste manuel (workflow PR). N'exclut PAS `REQ-config-ui-multi-config` (édition configarr.yml dans l'UI), toujours actif.
- **Sous-titres Jellyfin natifs (plugin Open Subtitles)** — v0.9.0 scoping decision: pas de besoin réel. Subs burned-in OU recherche native Jellyfin/Kodi au moment du watch. Même rationale que Bazarr out (D-19-RATIONALE-01).

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
| **ADR-9 — Jellyfin plugin reconciler moves from activation-only (D-07-PLUGINS-01) to install-capable (Phase 24, JFSKIP-02)** | Reversal of D-07-PLUGINS-01. Mechanism: when `install_guid` + `install_version` + `install_repo_url` are set on a `PluginEntry` and the plugin is absent from GET /Plugins, arrconf POSTs `POST /Packages/Installed/{name}?assemblyGuid={guid}&version={version}&repositoryUrl={url}` and logs `plugin_install_queued` with a `kubectl rollout restart` hint. Absent fields = old activation-only behavior preserved (backward-compatible). Two-run model (D-02): Jellyfin loads plugins at boot only — install and enable/config NEVER happen in the same run; operator must restart the pod between Run N (install queued) and Run N+1 (enable + config). Install only — NO uninstall, NO prune (operator removes via UI). First use: Intro Skipper v1.10.11.19 GUID c83d86bb-a1e0-4c35-a113-e2101cf4ee6b. See Phase 24 / JFSKIP-02 and spec.md §11 ADR-9 cross-reference. | install-capable |
| **ADR-10 — Couche d'intention au-dessus d'arrconf + configarr (Phase 28, INTENT-04)** | Couche d'intention se place au-dessus d'arrconf ET configarr. Flux : `intent.yml` → `arrconf generate` (pure fn) → configs committées → `arrconf apply` / configarr (inchangés). Frontière absorber (générer la config : cross-seed, qbit_manage) vs déployer-seulement (DB/UI-only : autobrr, cleanuparr). Extension d'ADR-5 : configarr reste seul appliqueur TRaSH ; la couche d'intention ne touche jamais `quality_profiles` / `custom_formats` / `quality_definitions` / `media_naming`. Modèle G1 (local + committé) retenu ; G2 (in-cluster) et G3 (auto-commit) rejetés. Voir spec.md §11 ADR-10. | active |

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
*Last updated: 2026-05-31 — v0.10.0 milestone started (Couche d'intention, tranche 1). Scope from validated design `v0.10.0-intention-layer-DESIGN.md` (commit `5bdd7f2`): `intent.yml` + `arrconf generate` → sagas (Radarr Collections + Jellyfin tmdbboxsets), cross-seed, qbit_manage. ADR-1/ADR-5 hold; new intent-boundary ADR pending. SEED-002 resolved by design §4. Phase numbering continues → Phase 28. Research skipped (design §4/§7 covers it). Next: define REQUIREMENTS.md → roadmap.*

<details>
<summary>Previous footer — v0.9.0</summary>

*Last updated: 2026-05-31 — v0.9.0 in progress. Phase 27 (TRaSH CF picker + Recyclarr reference + QP picker) complete: build-time-baked TRaSH/Recyclarr catalog (pinned SHAs, no runtime GitHub HTTP), 3 read-only `/api/trash/*` endpoints, TRaSH CF picker (multi-id-safe, custom/unknown classification, verbatim-preserve), append-only QP picker (collision-blocked), read-only Recyclarr reference. CFGUI-05/06/08 validated; 2 code-review blockers (multi-id CF handling, QP min_format_score) fixed pre-completion. 2 HUMAN-UAT items pending (QP collision normalization, QP live-save mapping). **Phase 24 (Jellyfin Intro Skipper) now complete (3/3)** — 24-03 live operator verification closed 2026-05-31: gating SC#1-4 PASS (repo registered, plugin Active post-restart with single intro-skipper.org repo, web skip-intro/credits button, EnableChapterImageExtraction on all 10 libs), and non-gating Kodi SC#5 = **ACCEPT** (service.jellyskip works on the LibreELEC salon box + Jellyfin 10.11.8). JFSKIP-01..05 Complete. v0.9.0 milestone fully complete (4/4 phases, 13/13 plans).*

</details>
