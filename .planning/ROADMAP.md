# Roadmap: arr-stack

## Overview

arr-stack se construit en 9 phases de-risk progressives (0 à 8), chacune livrable indépendamment. La structure est dictée par la spec source (`spec.md` §7) qui a déjà ordonnancé le travail selon une logique « capture l'existant → POC code → valider en cluster → étendre → packager → split tv/anime/family → couvrir les apps spécifiques (Seerr, Jellyfin) → durcir les secrets ». Les phases 0-7 forment le MVP. La phase 8 (migration ESO/Akeyless) est explicitement post-MVP et optionnelle, alignée sur un chantier global du cluster.

Chaque phase commence par une discipline obligatoire de **snapshot baseline** (ADR-6) avant toute écriture sur un nouveau scope, et chaque reconciler doit prouver son idempotence (round-trip `dump → apply --dry-run` = 0 action) avant d'être considéré complet.

## Phases

**Phase Numbering:**
- Integer phases (0-8): Planned milestone work (preserved from spec.md §7)
- Decimal phases (e.g., 2.1): Reserved for urgent insertions (none yet)

- [x] **Phase 0: Bootstrap repo + snapshot raw** - Capture lossless de l'existant (Bash) + scaffolding repo + Renovate initial (completed 2026-05-07)
- [x] **Phase 1: arrconf POC + JSON Schema** - Squelette Python, CI image GHCR, sous-commandes `dump`/`diff`/`apply`/`schema-gen`, 1 reconciler bout-en-bout (Sonarr download_clients) avec autocomplétion VS Code (completed 2026-05-08, 3 human-UAT items pending in 01-HUMAN-UAT.md)
- [x] **Phase 2: Validation cluster** - Premier déploiement arrconf en CronJob `selfhost` (`ARRCONF_DRY_RUN=true` au 1er run), bascule en apply après validation des logs, drift detection prouvée — completed 2026-05-08 with **partial success criteria** (success #1-#3 ✅; #4 PARTIAL — arrconf-managed tag created in Sonarr but PUT downloadclient blocked by Phase 1 design issue: empty username/password in YAML overwrites real qBit credentials, Sonarr 400; #5 UNTESTED — drift demo deferred). CronJob currently suspended in cluster pending Phase 2.1/3 fix. See `.planning/phases/02-arrconf-cluster-validation/02-05-SUMMARY.md`.
- [x] **Phase 2.1: Field-merge fix for sensitive YAML values** - Modify `tools/arrconf/arrconf/reconcilers/sonarr.py` (and possibly `differ.py`) so PUT body preserves cluster-stored field values when YAML value is `""` or for well-known sensitive field names. Re-run Plan 02-05 Tasks 5.1c + 5.2 (drift demo) for closure. Closes Phase 1 HUMAN-UAT #3. (completed 2026-05-09)
- [ ] **Phase 2.2: v0.1.4 forceSave fix (INSERTED)** - Add `?forceSave=true` query param to arrconf's UPDATE-branch PUT in `client_base.py` / `reconcilers/sonarr.py` so Sonarr does not re-validate the API-mask `"********"` against qBit on every real field change. Closes D-02.1-06 architectural finding from Phase 2.1 — required prerequisite before Phase 3 (Radarr/Prowlarr) automated drift correction.
- [ ] **Phase 3: Étendre arrconf (indexers, notifications, root_folders, tags, host_config + Radarr + Prowlarr)** - Couverture complète Sonarr/Radarr/Prowlarr avec app sync Prowlarr → *arr (depends on Phase 2.1 + 2.2 fix)
- [ ] **Phase 4: Umbrella chart + migration des 9 apps** - `charts/arr-stack/` umbrella avec deps `bjw-s/app-template`, migration des 9 ArgoCD Apps de my-kluster vers 1 seule App, Renovate `customManagers` validé bout-en-bout
- [ ] **Phase 5: Reconciler qBittorrent + split tv/anime/family** - 6 catégories qBit + 3 tags + 3 root folders + 3 download clients par instance Sonarr/Radarr (ADR-7), 3 quality profiles configarr correspondants
- [ ] **Phase 6: Reconciler Seerr** - Validation Q1 (compat API Seerr vs Overseerr/Jellyseerr) + Q10 (routing tags), reconciler `seerr.py` (services connectés, users, requests config)
- [ ] **Phase 7: Reconciler Jellyfin** - Bootstrap admin manuel préalable, validation Q9 (auth header), reconciler libraries / users / server config / plugins (best effort)
- [ ] **Phase 8: Migration ESO/Akeyless (optionnelle, post-MVP)** - ExternalSecret pour les API keys, suppression du secret manuel, alignement avec chantier ESO global du cluster

## Phase Details

### Phase 0: Bootstrap repo + snapshot raw
**Goal**: Capturer lossless l'état actuel des 6 apps avec API REST AVANT toute écriture, et scaffolder le repo `arr-stack` (Renovate initial, README minimal). Aucune dépendance Python — Bash + curl + jq uniquement.
**Depends on**: Nothing (first phase)
**Requirements**: REQ-baseline-snapshot, REQ-phase-roadmap
**Success Criteria** (what must be TRUE):
  1. `tools/snapshot/snapshot.sh` exécuté localement produit du JSON pour les 6 apps (sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin) dans `snapshots/baseline-2026-05-07/<app>/<resource>.json`
  2. Tous les fichiers JSON snapshot sont committés dans Git (NE PAS dans `.gitignore`)
  3. Aucune écriture observée pendant le snapshot (vérification : logs Sonarr/Radarr ne montrent que des reads)
  4. `renovate.json` initial committé (suivi GitHub Releases côté my-kluster `targetRevision`)
  5. README minimal présent expliquant comment relancer un snapshot avant un test risqué
**Plans**: 3 plans
- [x] 00-01-PLAN.md — Scaffolding repo (README.md racine + renovate.json + .gitignore + tools/snapshot/.gitkeep)
- [x] 00-02-PLAN.md — Implémentation tools/snapshot/snapshot.sh + tools/snapshot/README.md (6 apps, 3 patterns auth)
- [x] 00-03-PLAN.md — Exécution baseline snapshot + audit anti-leak + commit (5 success criteria ROADMAP)
**Open questions to resolve**: (none for Phase 0 — Q5 déjà tranchée par ADR-5, autres questions hors scope)

### Phase 1: arrconf POC + JSON Schema
**Goal**: Livrer un squelette Python `arrconf` avec ses 4 sous-commandes (`apply`, `dump`, `diff`, `schema-gen`), CI build d'image GHCR, et UN reconciler bout-en-bout (Sonarr `download_clients`) prouvant le round-trip `dump → apply --dry-run` = 0 action. JSON Schema généré et autocomplétion VS Code fonctionnelle.
**Depends on**: Phase 0
**Requirements**: REQ-cli-subcommands, REQ-yaml-autocomplete, REQ-idempotence, REQ-prune-opt-in, REQ-managed-tag, REQ-test-coverage, REQ-app-coverage (Sonarr download_clients seul)
**Success Criteria** (what must be TRUE):
  1. `pytest` vert avec couverture ≥ 70 % sur `differ.py` et `reconcilers/sonarr.py` (CI bloque sinon, tous mocks via `respx`)
  2. Image `ghcr.io/tom333/arr-stack-arrconf:sha-<short>` buildée par GitHub Actions et publique
  3. `arrconf dump --apps sonarr` produit `examples/baseline-sonarr.yml` qui round-trip avec `arrconf diff --config examples/baseline-sonarr.yml --apps sonarr` → 0 diff
  4. `arrconf apply --config examples/baseline-sonarr.yml --apps sonarr --dry-run` log "no-op" puisque YAML = état actuel
  5. Autocomplétion VS Code / code-server fonctionnelle : ouvrir `examples/baseline-sonarr.yml`, taper sous `download_clients:` → propositions des champs valides avec descriptions docstrings pydantic
  6. CI `tests.yml` vérifie que `arrconf schema-gen` produit un fichier identique à `schemas/arrconf-schema.json` committé (force la régénération à chaque ajout)
**Plans**: 3 plans
- [x] 01-01-PLAN.md — Wave 1: Plumbing (pyproject + uv.lock + Dockerfile multi-stage USER 1000:1000 + 12 module skeletons + 4 frontière configarr stubs raising ScopeViolationError + GHCR build workflow + fixture seeds from Phase 0 baseline)
- [x] 01-02-PLAN.md — Wave 2: Sonarr reconciler + tests (differ.py full impl with 6-case Action enum + reconcilers/sonarr.py with managed-tag-first ordering + Pitfall 1 tag-IDs-not-names + 4 test modules covering 33+ tests, coverage >= 70 %)
- [x] 01-03-PLAN.md — Wave 3: E2E + JSON Schema + CLI cement (full apply/dump/diff/schema-gen + JSON Schema Draft 2020-12 committed + examples/baseline-sonarr.yml with modeline + tests.yml with schema-gen idempotence gate + README documenting GHCR public toggle + VS Code autocomplete demo)
**Open questions to resolve**: Q4 (mode de release — tags manuels v1 confirme via D-01), Q6 (managed tag — confirme via D-02), Q7 (multi-version *arr — v4+ only confirme via D-03), Q8 (`prune: false` default — confirme via D-04)

### Phase 2: Validation cluster
**Goal**: Déployer arrconf en CronJob dans le namespace `selfhost` du cluster `my-kluster` (mini-chart ad-hoc avant umbrella), prouver la drift detection, et basculer en mode apply après dry-run sécurisé.
**Depends on**: Phase 1
**Requirements**: REQ-drift-detection, REQ-bootstrap-exception, REQ-secret-management
**Success Criteria** (what must be TRUE):
  1. Re-snapshot `snapshots/before-phase-2-<date>/` exécuté et committé avant tout déploiement (discipline ADR-6)
  2. CronJob `arrconf` existe dans le namespace `selfhost` avec secret manuel `arrconf-secret.yaml` dans `my-kluster/secrets/` (env-only, jamais de fichier de secrets) ; injection K8s via `envFrom: secretRef`
  3. Premier run en `ARRCONF_DRY_RUN=true` réussi : logs montrent les actions qui seraient prises, AUCUNE écriture observée côté Sonarr (vérification par re-snapshot post-run)
  4. Après bascule en `ARRCONF_DRY_RUN=false` : Sonarr UI montre le download client géré par arrconf
  5. Drift detection prouvée : modification UI hors-Git → écrasée au run suivant (logs JSON visibles)
**Plans**: 5 plans
- [ ] 02-01-PLAN.md — Wave 1: Pre-deploy snapshot baseline (re-snapshot all 6 apps + evidence/ dir for Wave 3/4 logs)
- [ ] 02-02-PLAN.md — Wave 1: v0.1.2 image release + GHCR public toggle (v0.1.0 first-push race; closes Phase 1 HUMAN-UAT #1; records image_tag_verified for 02-03)
- [ ] 02-03-PLAN.md — Wave 2: my-kluster chart authoring (capture verified hostnames, 9 files in my-kluster working tree, helm lint, secret-leak audit, end-of-plan cross-repo working-tree checkpoint per B-01)
- [ ] 02-04-PLAN.md — Wave 3: PR1 dry-run deployment (manual secret apply with W-05 tracking-id check, ArgoCD sync, B-02 volumeMount inspection, forced smoke job with W-06 verified event names, post-PR1 snapshot diff = 0)
- [ ] 02-05-PLAN.md — Wave 4: PR2 apply mode (B-03 split into 5.1a/b/c) + drift detection runbook (W-04 dispositive value-equality, W-01 REQUIRED forensic snapshot, W-06 verified plan_action event)
**Open questions to resolve**: Q3 (resolved D-23 — schedule `0 */4 * * *`), Q4 (resolved by Phase 1 D-01 — manual tag releases)

### Phase 2.1: Field-merge fix for sensitive YAML values
**Goal**: Implémenter dans arrconf un merge cluster→PUT pour les `fields[]` dont la valeur YAML est vide (`''`/`null`), releaser l'image `v0.1.3`, déployer via PR3 dans my-kluster (bump tag + nettoyage `username/password` du YAML), puis re-exécuter Plan 02-05 Tasks 5.1c (post-PR2 snapshot + Sonarr API tag verification) + 5.2 (drift demo runbook avec W-01 forensic snapshot + W-04 dispositive value-equality) pour clore les success criteria #4 et #5 de Phase 2 et l'item HUMAN-UAT #3 de Phase 1.
**Depends on**: Phase 2 (PARTIAL — success #1-#3 OK ; #4 PARTIAL ; #5 UNTESTED)
**Requirements**: REQ-drift-detection (closure via re-run drift demo), REQ-secret-management (formalisation du contrat "valeur vide en YAML = preserve cluster"), REQ-idempotence (round-trip `dump → apply --dry-run` = 0 action préservé après le merge)
**Success Criteria** (what must be TRUE):
  1. Helper de merge partagé livré (D-33) — `differ.py` ou `arrconf/merge.py` — généralisable aux reconcilers Phase 3 (Radarr/Prowlarr)
  2. Sémantique D-31/D-32 implémentée et testée : pour chaque entrée de `fields[]`, si `value` YAML est `''` ou `None`, le PUT body porte la valeur du cluster ; sinon, la valeur YAML l'emporte. Règle exclusivement value-based (pas d'allowlist par nom de champ)
  3. Tests respx unitaires couvrant les scénarios merge (vide préservé, non-vide override, mixte, edges) + un test round-trip `dump → merge → PUT body` qui asserte la préservation des credentials cluster face à un YAML aux champs vides (D-35)
  4. `arrconf dump` n'émet plus les entrées `fields[]` dont la valeur côté Sonarr est REDACTED (D-36) — round-trip `dump → diff` reste à 0 action
  5. Tag `v0.1.3` poussé, image GHCR `ghcr.io/tom333/arr-stack-arrconf:0.1.3` publique et anonymously pullable (D-37)
  6. PR3 dans my-kluster mergée : `image.tag: 0.1.2 → 0.1.3` ET suppression des entrées `username: ''`/`password: ''` dans `charts/arrconf/files/arrconf.yml` (D-36) ; ArgoCD sync OK et CronJob non-suspendu après sync
  7. Smoke job forcé après deploy : log JSON montre `managed_tag_found` (id=1, déjà créé par le run partiel Phase 2) + `plan_action action=update` sur le download client + `PUT 200` (plus de 400 « must have valid Username and Password »)
  8. Plan 02-05 Task 5.1c re-exécutée : post-PR2 snapshot capturé sous `evidence/`, vérification Sonarr API confirme le tag `arrconf-managed` attaché au download client (closure success #4 de Phase 2)
  9. Plan 02-05 Task 5.2 re-exécutée : drift demo runbook complet avec W-01 forensic snapshot et W-04 dispositive value-equality sur `priority` (closure success #5 de Phase 2 et HUMAN-UAT #3 de Phase 1)
**Plans**: 4 plans
- [x] 02.1-01-PLAN.md — Wave 1: Pre-fix snapshot (sonarr+qbittorrent baseline before code change, ADR-6)
- [x] 02.1-02-PLAN.md — Wave 2: Implement merge_fields_for_put + dump REDACTED filter + tests (D-31/D-32/D-33/D-35/D-36)
- [x] 02.1-03-PLAN.md — Wave 3: Release v0.1.3 + PR3 in my-kluster + post-deploy smoke job (D-36/D-37)
- [x] 02.1-04-PLAN.md — Wave 4: Re-execute Plan 02-05 Tasks 5.1c + 5.2 + close HUMAN-UAT #3 + STATE.md update (D-34)
**Open questions to resolve**: (none — D-31..D-37 tranchés en discuss-phase 2026-05-08)

### Phase 02.2: v0.1.4 forceSave fix (INSERTED)

**Goal:** Ship `v0.1.4` of arrconf adding `?forceSave=true` to every UPDATE PUT for *arr v3 clients (Sonarr/Radarr/Prowlarr) via a new `_ArrV3Client(ArrApiClient)` intermediate class in `tools/arrconf/arrconf/client_base.py`. Closes the architectural finding D-02.1-06 from Phase 2.1: Sonarr's `merge_fields_for_put` faithfully preserves the API mask `********` for `privacy=password` fields; without `forceSave=true`, Sonarr's pre-save validation re-authenticates against the literal `********` and rejects the PUT with HTTP 400 on any real-change PUT. Add ADR-8 to `spec.md` §11 documenting the trusted-controller stance. Cut `v0.1.4` annotated tag → CI builds GHCR image → atomic single-line PR in my-kluster bumping `image.tag: 0.1.3 → 0.1.4`. Re-execute Phase 2.1's drift demo runbook FULLY AUTOMATED (no operator manual `?forceSave=true` curl nudge) — the differential against Phase 2.1's closure is the dispositive proof that v0.1.4 closes the correction half of REQ-drift-detection cleanly. Required prerequisite before Phase 3 (Radarr/Prowlarr automated drift correction would face the identical 400 failure mode).

**Requirements**: REQ-drift-detection (correction half — closes cleanly here via fully-automated reconcile, replacing Phase 2.1's manual-nudge closure)

**Depends on:** Phase 2.1

**Plans:** 5/6 plans complete — Plan 06 INCOMPLETE; Phase 02.2 BLOCKED on D-02.2-AUTH-REGRESSION

> **BLOCKER (2026-05-09T06:48:11Z):** Plan 02.2-06 visual gate FAILED. Sonarr "Test" on qBit downloadclient returns 401/403 after v0.1.4 deploy. The `?forceSave=true` PUT bypassed Sonarr's pre-save validation and stored the API mask `"********"` (preserved by Phase 2.1 helper) as the literal qBit password. ADR-8 accepted-risk realized in production. CronJob `arrconf` SUSPENDED. Phase 02.2 closure REJECTED until v0.1.5 hotfix ships. See `.planning/phases/02.2-v0-1-4-forcesave-fix/deferred-items.md` D-02.2-AUTH-REGRESSION + Plan 06 SUMMARY §"Operator Visual Gate FAILED". Recommended next: `/gsd-plan-phase 02.2 --gaps`.

Plans:
- [x] 02.2-01-PLAN.md — Wave 1: Pre-deploy snapshot baseline (sonarr + qbittorrent, ADR-6 discipline; redaction workaround for D-02.1-01/-02)
- [x] 02.2-02-PLAN.md — Wave 2: TDD RED+GREEN — _ArrV3Client mixin + put_force_save_used event + 3 tests (UPDATE positive + ADD/DELETE defensive negative)
- [x] 02.2-03-PLAN.md — Wave 2: ADR-8 in spec.md §11 — trusted-controller stance documenting forceSave bypass (parallel to Plan 02)
- [x] 02.2-04-PLAN.md — Wave 3: Release v0.1.4 — annotated tag + CI build + GHCR public anon-pull verify (D-37 atomic single-tag pattern)
- [x] 02.2-05-PLAN.md — Wave 4: my-kluster PR — image.tag bump 0.1.3 → 0.1.4 (suspend CronJob during merge window; placeholders STAY per Phase 2.1 PR4)
- [ ] 02.2-06-PLAN.md — Wave 5: Cluster smoke + drift demo FULLY AUTOMATED — **INCOMPLETE / FAILED at Task 6.4 visual gate (operator UAT)**. Tasks 6.1–6.3 automated dispositives PASSED (priority restored, `put_force_save_used` emitted, no HTTP 400, `manual_nudge_used: NO`); Task 6.4 detected the credential-side regression that priority-only checks could not surface. CronJob suspended; D-02.2-AUTH-REGRESSION opened.

### Phase 3: Étendre arrconf
**Goal**: Étendre arrconf pour couvrir tous les types de ressources transverses des *arr (indexers, notifications, root_folders, tags, host_config) et ajouter les apps Radarr et Prowlarr (avec app sync Prowlarr → Sonarr/Radarr). Frontière configarr respectée.
**Depends on**: Phase 2
**Requirements**: REQ-configarr-coexistence, REQ-app-coverage (Sonarr extension + Radarr + Prowlarr full)
**Success Criteria** (what must be TRUE):
  1. Re-snapshot `snapshots/before-phase-3-<date>/` exécuté et committé avant écriture sur Radarr / Prowlarr (discipline ADR-6)
  2. Pour chaque nouveau reconciler / resource type : round-trip `dump → apply --dry-run` produit 0 action (idempotence prouvée)
  3. `diff -r snapshots/baseline-<date>/ snapshots/after-phase-3-<date>/` montre uniquement les changements intentionnels — aucun drift inattendu
  4. arrconf lève `ScopeViolationError` si un test ou config tente d'écrire sur `quality_profiles` / `custom_formats` / `quality_definitions` / `media_naming` (frontière ADR-5 codée en dur)
  5. App sync Prowlarr → Sonarr/Radarr fonctionnel et réconciliable depuis le YAML
  6. VS Code propose les nouveaux champs (indexers, notifications, etc.) automatiquement après régénération du JSON Schema (CI bloque si oublié)
**Plans**: TBD
**Open questions to resolve**: (Q6 finalisée si pas tranchée Phase 1)

### Phase 4: Umbrella chart + migration des 9 apps
**Goal**: Construire le chart umbrella `charts/arr-stack/` avec dependencies `bjw-s/app-template` (alias par service — ADR-2), migrer les 9 ArgoCD Applications de my-kluster vers une seule App pull arr-stack, valider Renovate `customManagers` bout-en-bout, et pinner les tags `:latest` résiduels.
**Depends on**: Phase 3
**Requirements**: REQ-config-as-code, REQ-umbrella-deployment, REQ-renovate-image-tracking, REQ-helm-validation, REQ-pr-to-cluster-latency, REQ-readme-onboarding
**Success Criteria** (what must be TRUE):
  1. ArgoCD sync de l'umbrella OK : 9 apps déployées via 1 chart unique (`arr-stack-app.yaml` dans my-kluster) ; les 9 ArgoCD Applications unitaires + `charts/configarr/` côté my-kluster sont supprimés
  2. Renovate propose un bump d'image (Sonarr ou Radarr minor/patch) et l'auto-merge passe sur le repo arr-stack ; côté my-kluster, Renovate ouvre une PR de bump `targetRevision` qui sync ArgoCD < 1 h après merge (REQ-pr-to-cluster-latency démontré bout-en-bout)
  3. Aucune régression sur les 9 apps : ingress publics restent fonctionnels, hostPath partagé `/opt/media-stack/torrents` (qBit + Sonarr + Radarr) intact, PVC NFS `media-nas-pvc` (Sonarr + Radarr + Jellyfin) intact, auth Jellyfin interne (sans oauth2-proxy) toujours OK
  4. Tags `:latest` pinnés sur des semver explicites pour qbittorrent, flaresolverr, cleanuparr ; toutes les images dans `values.yaml` ont leur annotation `# renovate: image=…`
  5. CI `chart-lint.yml` verte : `helm lint` + `helm template … | kubeconform -` + `values.yaml` parse contre `values.schema.json` (bloquant)
  6. README final permet onboard (clone → bootstrap secrets → premier deploy) en moins de 30 min, avec liens vers `spec.md` / `CLAUDE.md` / my-kluster
**Plans**: TBD
**UI hint**: yes
**Open questions to resolve**: Q2 (multi-alias `bjw-s/app-template` syntaxe — arbitrage syntaxique uniquement ; ADR-2 a déjà tranché Option A)

### Phase 5: Reconciler qBittorrent + split tv/anime/family
**Goal**: Implémenter le reconciler `qbittorrent.py` (settings + 6 catégories avec save_paths distincts) ET mettre en place le split tv/anime/family selon ADR-7 (3 tags + 3 root folders + 3 download clients par instance Sonarr/Radarr, 3 quality profiles configarr correspondants).
**Depends on**: Phase 4
**Requirements**: REQ-app-coverage (qBittorrent + split)
**Success Criteria** (what must be TRUE):
  1. Re-snapshot `snapshots/before-phase-5-<date>/` (qbittorrent + sonarr + radarr) exécuté et committé avant toute écriture
  2. 6 catégories qBittorrent déclarées avec save_paths distincts : `sonarr-tv → /data/series`, `sonarr-anime → /data/anime`, `sonarr-family → /data/family`, `radarr-movies → /data/movies`, `radarr-anime → /data/movies-anime`, `radarr-family → /data/movies-family`
  3. Sonarr `main` et Radarr `main` ont chacun 3 tags (`tv`, `anime`, `family`), 3 root folders, 3 download clients tagués correspondamment
  4. Test bout-en-bout : ajouter manuellement une série taggée `anime` dans Sonarr UI → le download arrive dans `/data/anime` côté qBit puis hardlink vers `/media/anime` (NFS partagé)
  5. `arrconf diff` après le test ≡ 0 action (idempotence sur tags / root folders / download clients)
  6. Configarr met à jour les 3 quality profiles (MULTi.VF, Anime, Family) avec scoring adapté (ex: VOSTFR à -10000 sur MULTi.VF, +50 sur Anime) sans casser l'existant
**Plans**: TBD
**UI hint**: yes
**Open questions to resolve**: (none — ADR-7 a tranché le pattern single-instance + tags)

### Phase 6: Reconciler Seerr
**Goal**: Implémenter le reconciler `seerr.py` (services Sonarr/Radarr connectés, users, requests config, default tags par type de contenu si supporté) après validation préalable de Q1 (compat API Seerr v3.2.0 vs Overseerr/Jellyseerr) et Q10 (stratégie de routing tags Seerr → Sonarr).
**Depends on**: Phase 5
**Requirements**: REQ-app-coverage (Seerr)
**Success Criteria** (what must be TRUE):
  1. Re-snapshot `snapshots/before-phase-6-<date>/` (seerr) exécuté et committé avant toute écriture
  2. Q1 résolue : `/api/v1/settings/services`, `/api/v1/user`, `/api/v1/request` testés sur Seerr v3.2.0 — compat Overseerr confirmée (ou divergences documentées dans le code)
  3. Q10 résolue : soit Seerr expose `defaultTags` par service connecté → routing auto par genre, soit fallback documenté `tag par défaut tv + ré-tag manuel pour anime/family minoritaires`
  4. Reconciler `seerr.py` réconcilie services Sonarr/Radarr connectés (single instance `main`), au minimum 1 user admin, requests config (auto-approve, request limits) ; round-trip `dump → apply --dry-run` = 0 action
  5. Test pratique : créer une demande Seerr → la requête arrive bien dans Sonarr ou Radarr taggée correctement (ou taggée `tv` + ré-tag manuel selon résolution Q10)
**Plans**: TBD
**UI hint**: yes
**Open questions to resolve**: Q1 (bloque la phase si incompatible), Q10 (avec fallback documenté)

### Phase 7: Reconciler Jellyfin
**Goal**: Implémenter le reconciler `jellyfin.py` (libraries, users, server config, plugins best effort) avec bootstrap admin manuel préalable et validation de Q9 (auth header — `X-Emby-Token` / `Authorization: MediaBrowser` / `?api_key=` query param). `client_base.py` doit pouvoir overrider la stratégie d'auth par app (les *arr utilisent `X-Api-Key`, qBit utilise login-based, Jellyfin diverge).
**Depends on**: Phase 6
**Requirements**: REQ-app-coverage (Jellyfin)
**Success Criteria** (what must be TRUE):
  1. Bootstrap admin Jellyfin manuel effectué via UI ; API key générée dans Dashboard → API Keys ; secret K8s mis à jour avec `JELLYFIN_API_KEY`
  2. Re-snapshot `snapshots/before-phase-7-<date>/` (jellyfin) exécuté et committé avant toute écriture
  3. Q9 résolue : stratégie d'auth Jellyfin retenue documentée et codée dans `client_base.py` (override par app supporté)
  4. `arrconf dump --apps jellyfin` round-trip avec `arrconf diff --apps jellyfin` = 0 diff (idempotence prouvée)
  5. Bibliothèques Jellyfin pointent correctement sur le NFS partagé `/media/{movies,series}` (et `/media/family` / `/media/anime` selon split Phase 5) ; au moins 1 library Movies + 1 library TV Shows
  6. Au moins admin + 1 user de test gérés via YAML (création / mise à jour quotas)
**Plans**: TBD
**UI hint**: yes
**Open questions to resolve**: Q9 (à valider par test pratique sur Jellyfin 10.11.8)

### Phase 8: Migration ESO/Akeyless (optionnelle, post-MVP)
**Goal**: Migrer les bootstrap secrets de `my-kluster/secrets/` vers ExternalSecrets pull depuis Akeyless, en alignement avec le chantier ESO global du cluster. Phase explicitement optionnelle et hors MVP.
**Depends on**: Phase 7 ; aligné sur le chantier ESO global du cluster (TODO de my-kluster, hors scope arr-stack)
**Requirements**: REQ-secret-management (closure)
**Success Criteria** (what must be TRUE):
  1. ExternalSecret(s) déclarés dans `charts/arr-stack/templates/` pour les API keys et credentials (sonarr / radarr / prowlarr / qbt / seerr / jellyfin / arrconf-runtime)
  2. Akeyless contient les secrets et le pull fonctionne dans le cluster
  3. Le secret manuel `arrconf-secret.yaml` (et autres bootstrap secrets concernés) est supprimé de `my-kluster/secrets/` après vérification que les pods récupèrent bien les valeurs via ExternalSecret
  4. Aucune régression : les CronJobs arrconf et configarr continuent de tourner avec des exit codes 0
**Plans**: TBD
**Open questions to resolve**: (none — phase d'exécution une fois le chantier ESO global mature)

## Progress

**Execution Order:**
Phases execute in numeric order: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Bootstrap repo + snapshot raw | 3/3 | Complete    | 2026-05-07 |
| 1. arrconf POC + JSON Schema | 0/TBD | Not started | - |
| 2. Validation cluster | 0/TBD | Not started | - |
| 2.1. Field-merge fix for sensitive YAML values | 4/4 | Complete   | 2026-05-09 |
| 2.2. v0.1.4 forceSave fix (INSERTED) | 5/6 | In progress | - |
| 3. Étendre arrconf | 0/TBD | Not started | - |
| 4. Umbrella chart + migration des 9 apps | 0/TBD | Not started | - |
| 5. Reconciler qBittorrent + split tv/anime/family | 0/TBD | Not started | - |
| 6. Reconciler Seerr | 0/TBD | Not started | - |
| 7. Reconciler Jellyfin | 0/TBD | Not started | - |
| 8. Migration ESO/Akeyless (optionnelle) | 0/TBD | Not started | - |
