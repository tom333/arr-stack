# Constraints

Extracted from `spec.md` (§4 Contraintes, §6 Composants — schémas et contrats techniques) and `CLAUDE.md` (conventions de code, garde-fous opérationnels). Constraints classified by type:

- **api-contract** — contrats avec APIs externes (Sonarr, Radarr, ..., Helm, GHCR, GitHub Actions)
- **schema** — schémas de fichiers (YAML config, JSON Schema, Helm values.schema.json)
- **nfr** — non-functional requirements (perf, sécurité, déploiement)
- **protocol** — protocoles internes (workflow, naming, conventions)

---

## C1 — Cluster privé : reconciliation in-cluster only

- source: /home/moi/projets/perso/arr-stack/spec.md (§4.1 C1)
- type: nfr
- content: Le cluster est privé. GitHub Actions ne peut PAS atteindre les APIs *arr. L'apply doit donc se faire dans le cluster (pattern CronJob, comme configarr). Implication directe : pas de Terraform Cloud, pas d'apply distant; tout passe par un Job/CronJob in-cluster pull-based.

---

## C2 — Image arrconf sur GHCR public

- source: /home/moi/projets/perso/arr-stack/spec.md (§4.1 C2, ADR-3)
- type: nfr
- content: Le cluster peut pull des images publiques sans credentials. L'image arrconf doit être hébergée sur GHCR public (`ghcr.io/tom333/arr-stack-arrconf`). Pas de imagePullSecret, pas de coût.

---

## C3 — APIs *arr accessibles via Service interne

- source: /home/moi/projets/perso/arr-stack/spec.md (§4.1 C3)
- type: api-contract
- content: Les APIs *arr sont accessibles en interne via leurs Services K8s : `http://<app>.selfhost.svc.cluster.local:<port>`. Pas besoin de passer par les ingress publics. arrconf doit utiliser ces URLs internes.

---

## C4 — Cohabitation configarr (frontière dure)

- source: /home/moi/projets/perso/arr-stack/spec.md (§4.2 C4, §6.2, ADR-5)
- type: protocol
- content: arrconf et configarr ont des scopes COMPLÉMENTAIRES NON-RECOUVRANTS. Le code arrconf doit refuser explicitement (lever une exception type `ScopeViolationError`) toute tentative d'écriture sur les endpoints quality_profiles / custom_formats / quality_definitions / media_naming.

---

## C5 — Intégration GitOps ArgoCD

- source: /home/moi/projets/perso/arr-stack/spec.md (§4.2 C5, §9)
- type: api-contract
- content: Une seule ArgoCD Application dans `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` pointe vers `github.com/tom333/arr-stack`, path `charts/arr-stack/`, valueFile `examples/values-prod.yaml`. Sync options : `CreateNamespace=false`, `ServerSideApply=true`, `automated.selfHeal=true`, `automated.prune=true`.

---

## C6 — Conventions cluster

- source: /home/moi/projets/perso/arr-stack/spec.md (§4.2 C6)
- type: protocol
- content: namespace `selfhost`, project ArgoCD `selfhost-project`, ingress NGINX + cert-manager `letsencrypt-prod`, oauth2-proxy pour les UIs sensibles (sauf Jellyfin qui a son auth interne).

---

## C7 — Single-node MicroK8s

- source: /home/moi/projets/perso/arr-stack/spec.md (§4.3 C7)
- type: nfr
- content: Cluster MicroK8s single-node. Pas de StatefulSets HA. `microk8s-hostpath` est la storageClass par défaut, mode `WaitForFirstConsumer`.

---

## C8 — Compatibilité Renovate global tom333

- source: /home/moi/projets/perso/arr-stack/spec.md (§4.3 C8)
- type: protocol
- content: Renovate est en place sur les repos de tom333. Toute config Renovate dans arr-stack doit être compatible avec son setup global.

---

## C9 — Pas de tag :latest en production

- source: /home/moi/projets/perso/arr-stack/spec.md (§4.3 C9), CLAUDE.md "Ce que tu NE dois PAS faire"
- type: protocol
- content: Pas d'image `:latest` en production sauf pour les images locales `localhost:32000/*` (qui n'existent PAS dans ce projet). Phase 4 inclut le pinning des tags `:latest` actuels (qbittorrent, flaresolverr, cleanuparr) sur des tags semver explicites.

---

## C10 — Stack Python imposée

- source: /home/moi/projets/perso/arr-stack/spec.md (§4.4 C10, §6.1, ADR-1)
- type: nfr
- content: Python 3.13 + httpx + pydantic v2 + ruyaml pour arrconf (cohérent avec les choix data lab de l'auteur). Logging via `structlog` ou stdlib + JSON formatter. Tests via `pytest` + `respx`. Lint/format via `ruff`. Type-check via `mypy` (strict sur signatures publiques, CI bloque).

---

## C11 — Helm 3 charts (pas Kustomize)

- source: /home/moi/projets/perso/arr-stack/spec.md (§4.4 C11)
- type: nfr
- content: Helm 3 charts en première intention. Pas de Kustomize.

---

## C12 — Pas de Terraform

- source: /home/moi/projets/perso/arr-stack/spec.md (§4.4 C12, ADR-1)
- type: nfr
- content: Pas de Terraform dans la stack. Décision liée à C1 (cluster privé, state lourd, providers immatures qBit/Seerr).

---

## Frontière arrconf/configarr (boundary table)

- source: /home/moi/projets/perso/arr-stack/spec.md (§6.2), CLAUDE.md "Frontière arrconf / configarr"
- type: protocol
- content: Frontière dure (les ✅ sont obligatoires, les ❌ sont interdits par construction côté arrconf):

```
Resource                                          configarr  arrconf
Quality profiles                                  ✅          ❌
Custom formats                                    ✅          ❌
Quality definitions                               ✅          ❌
Media naming                                      ✅          ❌
Indexers (Prowlarr → app sync)                    ❌          ✅
Indexers (Prowlarr lui-même)                      ❌          ✅
Download clients                                  ❌          ✅
Notifications                                     ❌          ✅
Root folders                                      ❌          ✅
Tags (y compris arrconf-managed)                  ❌          ✅
Host config (UI port, auth, etc.)                 ❌          ✅
qBittorrent settings                              ❌          ✅
Seerr settings                                    ❌          ✅
Jellyfin libraries                                ❌          ✅
Jellyfin users                                    ❌          ✅
Jellyfin server config (transcoding, networking)  ❌          ✅
Jellyfin plugins                                  ❌          ✅ (best effort)
App sync Prowlarr                                 ❌          ✅
```

Note d'écart : la table CLAUDE.md ne liste PAS les 4 lignes Jellyfin (libraries, users, server config, plugins). spec.md §6.2 (précédence supérieure) les inclut. La table autoritaire est celle ci-dessus, alignée sur spec.md.

---

## Variables d'environnement attendues par arrconf

- source: /home/moi/projets/perso/arr-stack/spec.md (§6.1), CLAUDE.md "Variables d'environnement"
- type: api-contract
- content: arrconf lit UNIQUEMENT depuis l'environnement (jamais depuis fichier de secrets) :
  - `SONARR_API_KEY`, `RADARR_API_KEY`, `PROWLARR_API_KEY`
  - `QBT_USER`, `QBT_PASS`
  - `SEERR_API_KEY`
  - `JELLYFIN_API_KEY` (généré dans Dashboard → API Keys après création du compte admin)
  - `ARRCONF_LOG_LEVEL` (default `INFO`)
  - `ARRCONF_DRY_RUN` (default `false`)

Le wrapping K8s (`envFrom: secretRef`) injecte tout. Aucune lecture de fichier.

---

## Image Docker arrconf

- source: /home/moi/projets/perso/arr-stack/spec.md (§6.1)
- type: nfr
- content:
  - Base `python:3.13-slim`
  - `USER 1000:1000` (non-root)
  - Multi-stage build pour minimiser la taille finale (~80 MB cible)
  - Tagging : `:vX.Y.Z` pour les releases, `:sha-<short>` pour les commits, `:latest` mappé sur dernière release
  - Health check optionnel (le CronJob est de toute façon one-shot)

---

## Exit codes arrconf CLI

- source: /home/moi/projets/perso/arr-stack/spec.md (§6.1), CLAUDE.md "CLI"
- type: api-contract
- content:
  - `0` succès intégral
  - `1` une app a échoué (mais les autres ont continué)
  - `2` erreur de config (parse, validation)
  - `3` (sur `diff` uniquement) drift détecté

---

## Renovate configuration (renovate.json)

- source: /home/moi/projets/perso/arr-stack/spec.md (§6.4)
- type: schema
- content: `renovate.json` doit déclarer :
  - `extends: ["config:recommended"]`
  - `customManagers` regex matchant `^charts/arr-stack/values\.yaml$` avec pattern `# renovate: image=(?<depName>.+?)\s+repository: \S+\s+tag: (?<currentValue>\S+)`, `datasourceTemplate: docker`
  - `packageRules` : automerge minor/patch/pin/digest pour `custom.regex`, `helm-values`, `helmv3`; automerge branch pour packages matching `arrconf`
- annotations dans `values.yaml` : `# renovate: image=<repo>` au-dessus de chaque image. SUPPRIMER l'annotation = casser le tracking Renovate.

---

## Snapshot tooling — formats

- source: /home/moi/projets/perso/arr-stack/spec.md (§6.5)
- type: schema
- content: Deux niveaux complémentaires :
  - **Niveau 1 — Snapshot raw API** (Bash, dispo Phase 0) : `tools/snapshot/snapshot.sh` (curl + jq). Output : `snapshots/baseline-YYYY-MM-DD/<app>/<resource>.json`. 100% read-only, lossless, versionné Git. Pas de dépendance Python.
  - **Niveau 2 — `arrconf dump`** (Python, dispo Phase 1+) : YAML structuré au schéma arrconf, exclut champs read-only, utilisable round-trip avec `arrconf apply`.

---

## CI workflows requis

- source: /home/moi/projets/perso/arr-stack/spec.md (§6.3)
- type: protocol
- content: 3 workflows GitHub Actions obligatoires + 1 ultérieur :
  1. `arrconf-image.yml` — push sur main modifiant `tools/arrconf/**` ou tag `v*` → build + push GHCR
  2. `chart-lint.yml` — PR modifiant `charts/**` → helm lint + kubeconform + helm template + values schema check
  3. `tests.yml` — PR modifiant `tools/arrconf/**` → ruff check + ruff format --check + mypy + pytest avec couverture ≥ 70 %
  4. `release.yml` (ultérieurement) — release-please ou conventional commits → CHANGELOG, tag, GitHub Release

---

## Conventions code style (arrconf)

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "Code style"
- type: protocol
- content:
  - `ruff check` et `ruff format` doivent passer avant commit (CI bloque)
  - `mypy` doit passer (strict sur signatures publiques, CI bloque)
  - Type hints partout sur signatures publiques. Locales : optionnelles.
  - Docstrings sur `__main__`, classes publiques (clients, reconcilers), fonctions publiques. Pas sur helpers privés évidents.
  - Pas de commentaires-narratifs ; commentaire utile = explique le POURQUOI non-évident.
  - Pinning strict via `pyproject.toml`. Pas de dépendance non-pinnée.

---

## Conventions Helm (annotations Renovate critiques)

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "Conventions Helm"
- type: protocol
- content:
  - Toute image dans `values.yaml` DOIT avoir l'annotation `# renovate: image=...` juste au-dessus (sans, Renovate ne suit pas)
  - `Chart.yaml` `dependencies:` sur `bjw-s/app-template` avec un alias par service (cf ADR-2)
  - Templates custom dans `templates/` pour ce qui dépasse app-template (CronJobs arrconf et configarr, ConfigMaps avec `.Files.Get`)
  - Pattern de nommage : `<app>-<resource>.yaml`
  - `values.schema.json` à écrire dès qu'on ajoute des sections complexes (génération initiale via `helm schema-gen`, maintenance manuelle)

---

## Workflow snapshot (discipline opérationnelle)

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "Workflow snapshot", spec.md ADR-6
- type: protocol
- content:
  - AVANT toute Phase qui touche un nouveau scope, re-snapshot raw d'abord
  - Tous les snapshots committés dans Git — NE PAS les ignorer dans `.gitignore`
  - Au moindre doute après un test cluster : `tools/snapshot/snapshot.sh --output snapshots/forensic-$(date +%FT%H%M)/` puis `diff` avec la baseline
  - Toujours `--dry-run` la première fois sur une nouvelle config

---

## Pattern single-instance + tags (implications techniques)

- source: /home/moi/projets/perso/arr-stack/spec.md (ADR-7), CLAUDE.md "Pattern single-instance + tags"
- type: protocol
- content:
  - **arrconf YAML** : un seul bloc `sonarr.main` et `radarr.main`. `download_clients` est une liste où chaque entrée a un champ `tags: [tv|anime|family]`. `root_folders` est aussi une liste (3 par instance). `tags` réconcilié comme les autres ressources.
  - **configarr** : plusieurs `quality_profiles` dans le même bloc d'instance. `assign_scores_to` peut cibler plusieurs profils avec scores différents (ex: VOSTFR à -10000 sur MULTi.VF mais +50 sur Anime).
  - **qBittorrent** : 6 catégories `sonarr-{tv,anime,family}` + `radarr-{movies,anime,family}`. Chaque catégorie a son `save_path` dans `/data/<type>` (relatif au mount qBit). Le hardlink final vers `/media/<type>` est géré par Sonarr/Radarr lors de l'import.

---

## Test conventions (arrconf)

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "Tests"
- type: protocol
- content:
  - Couverture cible ≥ 70 % sur `differ.py` et `reconcilers/`. Pas d'objectif sur fixtures et main.
  - Mock l'API via `respx`. Pas de tests qui appellent vraiment Sonarr/Radarr en CI.
  - Fixtures réalistes : capturer les vraies réponses API (sanitisées des secrets) dans `tests/fixtures/`. Préfixer par l'app : `sonarr_download_clients_v3.json`.
  - Une test par cas : add, update, delete, no-op, prune-skip, prune-on. Pas de méga-test.

---

## API multi-versions des *arr

- source: /home/moi/projets/perso/arr-stack/spec.md (§10 Q7)
- type: api-contract
- content: Recommandation initiale (à confirmer en discuss-phase) : tester arrconf sur Sonarr v4+ uniquement (déjà la version déployée), documenter comme prérequis. Sonarr v3 vs v4 ont des breaking changes API que le script ne couvrira pas.

---

## Jellyfin auth header

- source: /home/moi/projets/perso/arr-stack/spec.md (§10 Q9, §6.1)
- type: api-contract
- content: L'API Jellyfin utilise `X-Emby-Token` (legacy) ou `Authorization: MediaBrowser Token=...`. Stratégie : probablement `?api_key=<key>` query param suffit pour la plupart des endpoints. À valider en Phase 7. Conséquence pour le code : `client_base.py` doit pouvoir overrider la stratégie d'auth par app (Sonarr/Radarr utilisent `X-Api-Key`, qBit utilise login-based, Jellyfin diverge).

---

## Bootstrap flow (état actuel — 2026-05-07)

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "Bootstrap"
- type: protocol
- content: Au moment de l'ingestion, le repo contient uniquement `spec.md` et `CLAUDE.md`. Aucun code, aucun chart, aucune CI. C'est l'état initial avant Phase 0. Démarrage Phase 0 :
  1. `gsd-import spec.md` (ou `gsd-ingest-docs`) → bootstrap `.planning/`
  2. `gsd-new-project` (optionnel) pour cycle complet (PROJECT.md, ROADMAP.md, etc.)
  3. Premier `gsd-spec-phase` puis `gsd-plan-phase` sur Phase 0
  4. `gsd-execute-phase` pour mettre en place arrconf squelette + GitHub Actions GHCR

---

## Apps déjà déployées (état initial my-kluster)

- source: /home/moi/projets/perso/arr-stack/spec.md (§2.1, Annexe A)
- type: protocol
- content: 9 ArgoCD Applications existantes dans `my-kluster/argocd/argocd-apps/` :
  - sonarr 4.0.17, radarr 6.1.1, prowlarr 2.3.5, cleanuparr (latest — à pinner), configarr 1.16.0, qbittorrent (latest — à pinner), seerr v3.2.0 (`ghcr.io/seerr-team/seerr`), flaresolverr (latest — à pinner), jellyfin 10.11.8
  - Plus chart custom `charts/configarr/`
  - Toutes via `bjw-s/app-template 4.6.2`
  - hostPath partagé `/opt/media-stack/torrents` (qBit + Sonarr + Radarr)
  - PVC NFS partagé `media-nas-pvc` (Sonarr + Radarr + Jellyfin)
  - Jellyfin sans oauth2-proxy (auth interne)
  - Recyclarr désactivé (`recyclarr-app.yaml.disable`), à supprimer après validation Configarr

---

## Garde-fous "ne pas faire" (CLAUDE.md)

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "Ce que tu NE dois PAS faire"
- type: protocol
- content: Liste explicite d'interdictions, tirée du runbook (chacune est un constraint codé ou un check CI) :
  - Ne pas committer de secrets (aucun `.yaml` avec API keys, passwords, tokens)
  - Ne pas hardcoder `:latest` dans `values.yaml` ou Dockerfile
  - Ne pas écrire dans les endpoints quality_profiles / custom_formats / quality_definitions / media_naming depuis arrconf (cf ADR-5)
  - Ne pas amender un tag de release publié (`git tag -f`); toujours créer un nouveau tag
  - Ne pas dupliquer la config configarr ailleurs (source de vérité = `charts/arr-stack/files/configarr.yml`)
  - Ne pas appeler les vraies APIs depuis les tests CI (toujours mock via respx)
  - Ne pas ajouter de dépendance Python sans pinning dans `pyproject.toml`
  - Ne pas changer le scope arrconf↔configarr sans ADR explicite (mise à jour `.planning/` ADR + spec.md §11)
  - Ne pas déployer directement depuis ce repo (helm install, kubectl apply); toujours via my-kluster + ArgoCD
  - Ne pas merger une PR avec drift Renovate major sans valider le changelog upstream
  - Ne pas supprimer l'annotation `# renovate: image=...` dans `values.yaml`
  - Ne pas activer `prune: true` par défaut dans les reconcilers
  - Ne pas tester un nouveau reconciler en cluster sans avoir snapshot la baseline d'abord (cf ADR-6)
  - Ne pas ignorer `snapshots/` dans `.gitignore`

---

## API references (apps externes)

- source: /home/moi/projets/perso/arr-stack/spec.md (§12 Références)
- type: api-contract
- content: APIs ciblées par arrconf et leurs docs canoniques :
  - Sonarr API : https://sonarr.tv/docs/api/
  - Radarr API : https://radarr.video/docs/api/
  - Prowlarr API : https://prowlarr.com/docs/api/
  - qBittorrent Web API : https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
  - Seerr (fork actif Overseerr/Jellyseerr — compat à valider Q1) : `ghcr.io/seerr-team/seerr`
  - Jellyfin API : https://api.jellyfin.org/ (OpenAPI complet)
  - FlareSolverr (no API à reconcilier) : https://github.com/FlareSolverr/FlareSolverr
  - yaml-language-server : https://github.com/redhat-developer/yaml-language-server
