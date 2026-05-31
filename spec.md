# arr-stack — Spec

> Cible : `gsd-import` / `gsd-ingest-docs` (https://github.com/gsd-build/get-shit-done)
> Auteur : Thomas Guyader (tom333)
> Date : 2026-05-07
> Repo cible (à créer) : `github.com/tom333/arr-stack`

---

## 1. Vue d'ensemble

**arr-stack** est un projet de plateforme média **fully-as-code** déployée sur le cluster MicroK8s personnel (`my-kluster`). Il regroupe :

1. **Un script Python custom (`arrconf`)** qui réconcilie la config des applications *arr et apparentées (Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, Jellyfin) depuis un fichier YAML déclaratif vers leurs APIs REST.
2. **Un Helm umbrella chart** qui empaquette toute la stack (les apps elles-mêmes + configarr + arrconf + ressources transverses) en un déploiement atomique versionné.
3. **Une CI GitHub Actions** qui build l'image arrconf et la pousse sur GHCR.
4. **Une config Renovate dédiée** qui suit les tags d'image dans le `values.yaml` umbrella.

Objectif final : ne plus jamais ouvrir l'UI Sonarr/Radarr/qBit/Seerr pour configurer quoi que ce soit. Tout passe par PR.

---

## 2. Contexte & motivation

### 2.1 État actuel (dans `my-kluster`)

- Cluster : MicroK8s single-node, GitOps via ArgoCD, domaine `*.tgu.ovh`
- Stack média actuelle dans namespace `selfhost` :
  - `sonarr` 4.0.17 (lscr.io/linuxserver)
  - `radarr` 6.1.1
  - `prowlarr` 2.3.5
  - `cleanuparr`
  - `configarr` 1.16.0 (chart custom `charts/configarr/` — quality profiles + custom formats)
  - `qbittorrent` (lscr.io/linuxserver, tag `latest` — à pinner) — download client, hostPath `/opt/media-stack/torrents` partagé avec Sonarr/Radarr
  - `seerr` v3.2.0 (`ghcr.io/seerr-team/seerr`) — request manager (fork actif d'Overseerr/Jellyseerr)
  - `flaresolverr` (`ghcr.io/flaresolverr/flaresolverr`, tag `latest`) — proxy Cloudflare pour Prowlarr, accès interne uniquement
  - `jellyfin` 10.11.8 (`lscr.io/linuxserver/jellyfin`) — média serveur ; auth interne Jellyfin (PAS d'oauth2-proxy) ; PVC config 10Gi local + `media-nas-pvc` NFS partagé avec Sonarr/Radarr
- Toutes les apps déployées via le chart `bjw-s app-template 4.6.2`, fichiers individuels dans `argocd/argocd-apps/<service>-app.yaml`
- Renovate auto-merge minor/patch sur ces fichiers
- Bootstrap secrets gérés via Bitnami sealed-secrets côté my-kluster (`arrconf-env`, `configarr-env`) — baseline stable

### 2.2 Pourquoi un nouveau projet séparé

1. **arrconf est du vrai code logiciel** (Python, Docker, tests, CI). Il mérite un repo avec ses outils (lint, tests, build), distinct des manifestes Kubernetes de `my-kluster`.
2. **Le pattern umbrella casse Renovate dans `my-kluster`** (qui scanne `argocd/argocd-apps/*.yaml`). Dans un repo dédié, on configure Renovate sur mesure (`customManagers` sur les tags d'image dans `values.yaml`).
3. **Cohérence de domaine** : la stack média est un produit cohérent, distinct de l'infra/data/perso. Découpage légitime.
4. **Versionnement atomique** : un release = `Sonarr@X + Radarr@Y + arrconf@Z + configarr@W`. Rollback en un `git revert`.
5. **Réutilisable** : pattern packageable, exportable.
6. **Précédent** : `tom333/cv` est déjà un repo séparé pulled par ArgoCD. Pattern connu et fonctionnel.

### 2.3 Pourquoi PAS les alternatives

| Outil | Pourquoi rejeté |
|---|---|
| **Buildarr** | Maintenance en dérive, pas de plugin pour Seerr (remplaçant de Jellyseerr), incompatible avec la trajectoire des apps choisies |
| **Terraform devopsarr** | Couvre bien Sonarr/Radarr/Prowlarr mais qBittorrent et Seerr n'ont pas de provider mature ; gestion du state lourde dans un Job K8s ; GitHub Actions ne peut pas atteindre le cluster privé |
| **Recyclarr** | Limité au scope quality profiles + CFs (déjà couvert par configarr, son successeur direct) |
| **Flemmarr (tel quel)** | Inspiration valide, mais on veut maîtriser le code et étendre à qBit/Seerr/Jellyfin |
| **Ansible** | Impératif, drift detection faiblarde, écosystème *arr peu actif |
| **K8s operators *arr** | Quelques tentatives mais aucun mature/maintenu |

**Décision** : script Python maison, inspiré de Flemmarr (lecture de son source comme référence). Voir §11 ADR-1.

---

## 3. Objectifs & non-objectifs

### 3.1 Objectifs

- **O1** — La config de Sonarr/Radarr/Prowlarr/qBittorrent/Seerr (et autres apps de la stack) est entièrement déclarative dans un fichier YAML versionné Git.
- **O2** — Tout changement de config passe par PR sur le repo `arr-stack`. Aucune intervention UI requise après bootstrap.
- **O3** — Drift UI détectable : si quelqu'un (humain, autre tool) modifie l'app en UI, le prochain run d'arrconf restaure l'état désiré.
- **O4** — Idempotent : ré-exécuter arrconf 10 fois ne change rien si le YAML n'a pas bougé.
- **O5** — Le déploiement de la stack se fait via une seule ArgoCD Application dans `my-kluster` pointant vers le chart umbrella du repo arr-stack.
- **O6** — Renovate suit automatiquement les versions d'image (Sonarr, Radarr, ..., arrconf) déclarées dans `values.yaml` et propose les bumps.
- **O7** — La config configarr (quality profiles + custom formats + naming + quality definitions) est versionnée dans le repo arr-stack et continue de fonctionner exactement comme aujourd'hui.
- **O8** — Une **baseline lossless** de la config actuelle des apps est capturée AVANT toute écriture de test, et conservée dans le repo. Permet rollback forensic et seed du premier `files/arrconf.yml`.

### 3.2 Non-objectifs (explicitement OUT)

- **NG1** — Migrer le reste du cluster `my-kluster` vers ce repo. **arr-stack se limite à la stack média**. Restent dans `my-kluster` et n'ont pas vocation à venir ici :
  - Data lab : mlflow, jupyter, dagster, qdrant, postgresql
  - Infra : cert-manager, oauth2-proxy, kubetail, external-secrets, config (raw manifests)
  - Perso : cv, code-server, freshrss, komga
- **NG2** — Construire un outil générique multi-tenant. arr-stack est dimensionné pour 1 cluster, 1 utilisateur (homelab).
- **NG3** — Couvrir 100 % de toutes les options de chaque API. On couvre ce que l'auteur utilise réellement.
- **NG4** — Refaire ce que configarr fait bien (quality profiles, custom formats, naming, quality definitions). arrconf et configarr ont des scopes complémentaires.
- **NG5** — Bootstrap automatique des API keys initiales. La 1ère obtention d'API key se fait toujours via UI ; arrconf prend le relais ensuite.

---

## 4. Contraintes

### 4.1 Réseau & accès

- **C1** — Le cluster est privé. **GitHub Actions ne peut PAS atteindre les APIs *arr.** L'apply doit donc se faire **dans le cluster** (pattern CronJob, comme configarr).
- **C2** — Le cluster peut pull des images publiques sans credentials. → l'image arrconf doit être hébergée sur **GHCR public** (`ghcr.io/tom333/arr-stack-arrconf`).
- **C3** — Les APIs *arr sont accessibles en interne via leurs Services K8s : `http://<app>.selfhost.svc.cluster.local:<port>`. Pas besoin de passer par les ingress publics.

### 4.2 Compatibilité

- **C4** — Doit cohabiter sans conflit avec `configarr` actuel (scopes complémentaires, voir §6.2 boundaries).
- **C5** — Doit s'intégrer au pattern GitOps existant : ArgoCD Application dans `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` pointant vers `github.com/tom333/arr-stack`.
- **C6** — Doit respecter les conventions du cluster : namespace `selfhost`, project `selfhost-project`, ingress NGINX + cert-manager `letsencrypt-prod`, oauth2-proxy pour les UIs sensibles.

### 4.3 Opérationnel

- **C7** — Single-node MicroK8s. Pas de StatefulSets HA, `microk8s-hostpath` est la storageClass par défaut, `WaitForFirstConsumer`.
- **C8** — Renovate est en place sur les repos de tom333 ; toute config Renovate dans arr-stack doit être compatible avec son setup global.
- **C9** — Pas d'image `:latest` en production sauf pour les images locales `localhost:32000/*` (voir CLAUDE.md de my-kluster).

### 4.4 Stack technique imposée / préférée

- **C10** — Python 3.13 + httpx + pydantic + ruyaml pour arrconf (cohérent avec les choix data lab de l'auteur).
- **C11** — Helm 3 charts (pas Kustomize en première intention).
- **C12** — Pas de Terraform.

---

## 5. Architecture proposée

### 5.1 Vue d'ensemble (deux repos)

```
github.com/tom333/my-kluster                  github.com/tom333/arr-stack
├── argocd/argocd-apps/                       ├── tools/arrconf/             ← script Python
│   └── arr-stack-app.yaml         ─────►     │   ├── Dockerfile
│       (1 seule App ArgoCD)                  │   └── arrconf/...
└── ...                                       ├── charts/arr-stack/          ← umbrella Helm
                                              │   ├── Chart.yaml             ← deps app-template
                                              │   ├── values.yaml            ← versions, ingress
                                              │   ├── files/
                                              │   │   ├── arrconf.yml        ← config arrconf
                                              │   │   └── configarr.yml      ← config configarr
                                              │   └── templates/
                                              ├── .github/workflows/
                                              │   ├── arrconf-image.yml      ← build + push GHCR
                                              │   ├── chart-lint.yml         ← helm lint + values schema
                                              │   └── tests.yml              ← pytest arrconf
                                              ├── renovate.json              ← customManagers
                                              └── README.md
```

### 5.2 Flux de déploiement

1. PR sur `arr-stack` modifiant `values.yaml` ou `files/arrconf.yml` ou code Python
2. CI : lint, tests, build image arrconf si modifiée → push GHCR avec tag SHA
3. Merge → tag de release sémantique (manuel ou via release-please)
4. Renovate dans `my-kluster` détecte le nouveau tag → PR de bump sur `targetRevision: vX.Y.Z`
5. Merge sur `my-kluster` → ArgoCD sync l'umbrella → CronJob arrconf re-run au prochain schedule (ou manuel via `kubectl create job --from=cronjob/...`)

### 5.3 Apps couvertes (cible)

**Toutes déjà déployées dans `my-kluster`** (sauf arrconf, à créer) :

| App | Image | Géré par |
|---|---|---|
| Sonarr | `lscr.io/linuxserver/sonarr` | Helm umbrella + arrconf (download clients, indexers, notifications, root folders, tags, host config) |
| Radarr | `lscr.io/linuxserver/radarr` | Idem Sonarr |
| Prowlarr | `lscr.io/linuxserver/prowlarr` | Helm umbrella + arrconf (indexers, app sync vers Sonarr/Radarr, FlareSolverr proxy config) |
| qBittorrent | `lscr.io/linuxserver/qbittorrent` | Helm umbrella + arrconf (catégories, save paths, settings) |
| Seerr | `ghcr.io/seerr-team/seerr` v3.2.0 | Helm umbrella + arrconf (services Sonarr/Radarr connectés, users, requests config) |
| FlareSolverr | `ghcr.io/flaresolverr/flaresolverr` | Helm umbrella **seulement** (config par env vars, pas d'API à gérer) |
| Jellyfin | `lscr.io/linuxserver/jellyfin` 10.11.8 | Helm umbrella + arrconf (libraries, users, server config) — bootstrap admin via UI au 1er run (NG5) |
| Cleanuparr | `ghcr.io/cleanuparr/cleanuparr` | Helm umbrella seulement (config UI hors scope arrconf pour l'instant) |
| Configarr | `ghcr.io/raydak-labs/configarr` | Helm umbrella + sa propre config dans `files/configarr.yml` (scope quality profiles / custom formats) |
| arrconf | `ghcr.io/tom333/arr-stack-arrconf` (nouveau) | Helm umbrella + sa propre config dans `files/arrconf.yml` |

**Apps explicitement hors scope** (décidé v0.7.0 — voir [MILESTONES.md](.planning/MILESTONES.md)) :
- **Bazarr (sous-titres)** — Pas de besoin réel : les médias téléchargés ont les sous-titres burned-in ou Jellyfin/Kodi cherche les subs en natif au moment du watch. Bazarr résoudrait un problème qui n'existe pas dans ce homelab.
- **Lidarr (musique) / Whisparr (adulte) / Readarr (livres)** — Stack média est dimensionnée pour vidéo (séries + films) uniquement. Audio, écrit, et adult content sortent du périmètre intentionnellement.

La media stack est **complète et fermée** post-v0.7.0 : 9 apps (Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, Jellyfin, FlareSolverr, Cleanuparr, SuggestArr) + arrconf + configarr. Toute proposition d'ajouter un autre *arr passe par une revue de cette décision dans `.planning/PROJECT.md` "Out of Scope".

---

## 6. Composants

### 6.1 arrconf — script Python

**Rôle** : reconcile la config des apps *arr et apparentées depuis un YAML vers leurs APIs.

**Modèle de fonctionnement** :
1. Charge `arrconf.yml` (mounté en ConfigMap dans le pod)
2. Pour chaque app déclarée, instancie un client typé (Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, ...)
3. Pour chaque type de resource (download_clients, indexers, notifications, root_folders, tags, ...) :
   - `GET` la liste actuelle depuis l'API
   - Compare avec le YAML désiré (matching par `name` ou `id` selon ressource)
   - `POST` les nouvelles, `PUT` celles qui ont changé, `DELETE` celles qui ne sont plus dans le YAML (avec un flag `prune` configurable par section)
4. Log structured (JSON) des actions effectuées
5. Exit code != 0 si erreur sur l'une des apps (mais continue les autres)

**Stack** :
- Python 3.13
- `httpx` (client HTTP, support sync + async)
- `pydantic` v2 (validation des schémas YAML et des réponses API)
- `ruyaml` (YAML round-trip avec préservation des commentaires — utile pour debug)
- `structlog` ou stdlib logging avec JSON formatter
- `pytest` + `respx` (mock httpx) pour tests
- `ruff` lint + format
- `mypy` type-check (strict sur signatures publiques)

**Structure** :

```
tools/arrconf/
├── pyproject.toml
├── Dockerfile                     # python:3.13-slim, USER non-root
├── arrconf/
│   ├── __init__.py
│   ├── __main__.py                # entrypoint CLI (sous-commandes: apply, dump, diff)
│   ├── config.py                  # parsing + validation pydantic du YAML
│   ├── logging.py                 # setup structlog
│   ├── client_base.py             # ArrApiClient générique (auth, retry, pagination)
│   ├── differ.py                  # logique GET → diff → POST/PUT/DELETE générique
│   ├── schema_gen.py              # sérialise pydantic → JSON Schema (sous-commande schema-gen)
│   ├── reconcilers/
│   │   ├── __init__.py
│   │   ├── sonarr.py
│   │   ├── radarr.py
│   │   ├── prowlarr.py
│   │   ├── qbittorrent.py
│   │   ├── seerr.py
│   │   └── jellyfin.py
│   └── resources/                 # schémas pydantic par resource type
│       ├── download_client.py
│       ├── indexer.py
│       ├── notification.py
│       ├── root_folder.py
│       ├── tag.py
│       └── ...
└── tests/
    ├── conftest.py
    ├── test_differ.py
    ├── test_sonarr.py
    └── fixtures/
        └── sonarr_download_clients.json
```

**Image Docker** :
- Base `python:3.13-slim`
- `USER 1000:1000` (non-root)
- Health check optionnel (le CronJob est de toute façon one-shot)
- Multi-stage build pour minimiser la taille finale (~80 MB cible)
- Tagging : `:vX.Y.Z` pour les releases, `:sha-<short>` pour les commits, `:latest` mappé sur dernière release

**Variables d'environnement attendues** :
- `SONARR_API_KEY`, `RADARR_API_KEY`, `PROWLARR_API_KEY`
- `QBT_USER`, `QBT_PASS`
- `SEERR_API_KEY`
- `JELLYFIN_API_KEY` (généré dans Dashboard → API Keys après création du compte admin)
- `ARRCONF_LOG_LEVEL` (default INFO)
- `ARRCONF_DRY_RUN` (default false)

**CLI — sous-commandes** :

```
arrconf apply       [--config PATH] [--apps LIST] [--dry-run] [--log-level LEVEL]   # default: reconcilie
arrconf dump        [--apps LIST] [--output PATH]                                    # read-only, exporte YAML
arrconf diff        [--config PATH] [--apps LIST]                                    # diff lisible local vs cluster
arrconf schema-gen  [--output PATH]                                                  # exporte JSON Schema du config
```

- `apply` (default si aucune sous-commande) : reconcilie le YAML désiré vers les APIs.
- `dump` : **read-only**. Récupère l'état courant de chaque app via API et écrit un YAML conforme au schéma arrconf. Aucune écriture sur les APIs. Sert au seed initial et au diagnostic forensic.
- `diff` : compare YAML local vs APIs et affiche les actions qui seraient prises, en format lisible (par opposition à `--dry-run` qui log).
- `schema-gen` : **read-only, offline**. Sérialise les modèles pydantic du config en JSON Schema (Draft 2020-12). Output committé dans `schemas/arrconf-schema.json`. Permet l'autocomplétion + validation à la frappe dans VS Code / code-server via [yaml-language-server](https://github.com/redhat-developer/yaml-language-server). À régénérer après tout ajout de reconciler ou de resource type (CI peut vérifier l'idempotence).
- Exit codes : `0` succès, `1` une app a échoué (les autres ont continué), `2` erreur de config (parse/validation), `3` (sur `diff`) drift détecté.

### 6.2 Umbrella Helm chart

**Rôle** : empaqueter toute la stack en un déploiement atomique.

**Structure** :

```
charts/arr-stack/
├── Chart.yaml                     # deps: app-template ×N (ou subcharts inline)
├── values.yaml                    # tags d'image, ingress, schedules, ressources
├── values.schema.json             # JSON schema pour validation (généré ou écrit)
├── files/
│   ├── arrconf.yml                # config arrconf (mounté en ConfigMap par template)
│   └── configarr.yml              # config configarr (mounté en ConfigMap par template)
└── templates/
    ├── _helpers.tpl
    ├── arrconf-cronjob.yaml
    ├── arrconf-configmap.yaml
    ├── configarr-cronjob.yaml
    ├── configarr-configmap.yaml
    ├── configarr-pvc.yaml
    └── NOTES.txt
```

**Approche dependencies** : 2 options, à arbitrer en discuss-phase :

- **Option A — Helm dependencies sur app-template** : `Chart.yaml` liste app-template comme dependency × N (alias par service). Avantage : pas de duplication, hérite des évolutions upstream. Inconvénient : alias multiples du même chart, syntaxe dependency parfois capricieuse.
- **Option B — Sub-charts en local** : `charts/arr-stack/charts/sonarr/`, `radarr/`... contenant chacun un wrapper minimal. Avantage : maîtrise totale, pas de dépendance externe. Inconvénient : duplication potentielle.

Recommandation initiale : Option A (deps app-template). Voir §11 ADR-2.

**Frontières scope arrconf vs configarr** :

| Resource | configarr | arrconf |
|---|---|---|
| Quality profiles | ✅ | ❌ |
| Custom formats | ✅ | ❌ |
| Quality definitions | ✅ | ❌ |
| Media naming | ✅ | ❌ |
| Indexers (Prowlarr → app sync) | ❌ | ✅ |
| Indexers (Prowlarr lui-même) | ❌ | ✅ |
| Download clients | ❌ | ✅ |
| Notifications | ❌ | ✅ |
| Root folders | ❌ | ✅ |
| Tags | ❌ | ✅ |
| Host config (UI port, auth, etc.) | ❌ | ✅ |
| qBittorrent settings | ❌ | ✅ |
| Seerr settings | ❌ | ✅ |
| Jellyfin libraries | ❌ | ✅ |
| Jellyfin users | ❌ | ✅ |
| Jellyfin server config (transcoding, networking) | ❌ | ✅ |
| Jellyfin plugins | ❌ | ✅ (best effort) |
| App sync Prowlarr | ❌ | ✅ |

### 6.3 CI/CD (GitHub Actions)

**Workflows** :

1. **`arrconf-image.yml`** — Build + push GHCR
   - Trigger : push sur `main` modifiant `tools/arrconf/**`, ou tag `v*`
   - Steps : checkout → setup buildx → login GHCR (GITHUB_TOKEN) → docker build/push → cosign sign (optionnel)
   - Tags : `:sha-<short>`, `:branch-<name>`, et `:vX.Y.Z` + `:latest` sur tags

2. **`chart-lint.yml`** — Validation Helm
   - Trigger : PR modifiant `charts/**`
   - Steps : helm lint → kubeconform contre les schémas K8s → helm template (sanity) → vérification que `values.yaml` parse contre `values.schema.json`

3. **`tests.yml`** — Tests Python arrconf
   - Trigger : PR modifiant `tools/arrconf/**`
   - Steps : ruff check → ruff format --check → mypy → pytest avec couverture
   - Cible coverage : 70 % minimum sur `differ.py` et `reconcilers/`

4. **`release.yml`** (ultérieurement) — Release tagging
   - Via release-please ou conventional commits
   - Génère CHANGELOG.md, tag, GitHub Release, déclenche `arrconf-image.yml` avec tag de version

### 6.4 Renovate

**Config dans `renovate.json`** :

```jsonc
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "customManagers": [
    {
      "customType": "regex",
      "fileMatch": ["^charts/arr-stack/values\\.yaml$"],
      "matchStrings": [
        "# renovate: image=(?<depName>.+?)\\s+repository: \\S+\\s+tag: (?<currentValue>\\S+)"
      ],
      "datasourceTemplate": "docker"
    }
  ],
  "packageRules": [
    {
      "matchManagers": ["custom.regex", "helm-values", "helmv3"],
      "matchUpdateTypes": ["minor", "patch", "pin", "digest"],
      "automerge": true
    },
    {
      "matchPackagePatterns": ["arrconf"],
      "automerge": true,
      "automergeType": "branch"
    }
  ]
}
```

Annotations dans `values.yaml` :

```yaml
arrconf:
  image:
    # renovate: image=ghcr.io/tom333/arr-stack-arrconf
    repository: ghcr.io/tom333/arr-stack-arrconf
    tag: v0.1.0
sonarr:
  image:
    # renovate: image=lscr.io/linuxserver/sonarr
    repository: lscr.io/linuxserver/sonarr
    tag: 4.0.17
# ... idem pour radarr, prowlarr, qbittorrent, configarr
```

Côté `my-kluster`, Renovate suit `targetRevision: vX.Y.Z` dans `arr-stack-app.yaml`.

### 6.5 Snapshot tooling (capture forensic de l'existant)

**Rôle** : capturer la config actuelle de toutes les apps **AVANT** la moindre écriture de test, pour permettre rollback et diagnostic.

**Deux niveaux complémentaires** :

#### Niveau 1 — Snapshot raw API (Bash, standalone, indépendant d'arrconf)

```
tools/snapshot/
├── snapshot.sh                   # script Bash: curl + jq, GET /api/v3/<resource> par app
├── README.md
└── (pas de dépendance Python — utilisable AVANT que arrconf existe)
```

Outputs vers `snapshots/baseline-YYYY-MM-DD/<app>/<resource>.json` :
```
snapshots/baseline-2026-05-07/
├── sonarr/
│   ├── downloadclient.json
│   ├── indexer.json
│   ├── notification.json
│   ├── rootfolder.json
│   ├── tag.json
│   ├── qualityprofile.json
│   ├── customformat.json
│   └── ...
├── radarr/
│   └── ...
├── prowlarr/
│   └── ...
├── qbittorrent/
│   ├── preferences.json
│   ├── categories.json
│   └── ...
└── seerr/
    └── ...
```

**Propriétés** :
- 100 % read-only (que des `GET`)
- Lossless : capture tous les champs renvoyés par l'API, sans transformation
- Versionné dans Git (les snapshots ne contiennent pas de secret — uniquement la config)
- Datable : un dump par baseline + dumps ad-hoc avant chaque test risqué (`snapshots/before-phase-X/`)

#### Niveau 2 — `arrconf dump` (mode export YAML structuré)

Une fois arrconf bootstrappé en Phase 0, sa sous-commande `dump` produit un YAML au schéma arrconf — directement réutilisable comme seed pour `files/arrconf.yml`.

```bash
arrconf dump --apps sonarr,radarr > examples/baseline.yml
```

**Différence vs Niveau 1** :
- Format YAML structuré (pas JSON brut)
- Suit le schéma arrconf (champs read-only et metadata exclus)
- Utilisable comme input direct par `arrconf apply` (round-trip)
- Permet la traduction d'une config existante en config-as-code

**Discipline** :
- Re-snapshot raw avant chaque phase qui touche une app : `tools/snapshot/snapshot.sh > snapshots/before-phase-N/`
- Conserver tous les snapshots dans Git — ils sont petits (~quelques MB) et inestimables en cas de pépin
- Comparer avec `diff -r snapshots/baseline/ snapshots/after-phase-N/` pour vérifier que rien n'a bougé hors des intentions

---

## 7. Phases & roadmap

Approche progressive pour de-risker. Chaque phase est livrable indépendamment (peut s'arrêter sans casse).

### Phase 0 — Bootstrap repo + script snapshot raw

**Note** : avant tout code arrconf, on **capture l'existant**. Indépendant, standalone, n'écrit rien.

**Livrables** :
- Repo `arr-stack` créé sur GitHub, public
- `tools/snapshot/snapshot.sh` (Bash + curl + jq) qui dump TOUS les endpoints `GET` des 6 apps avec API REST (sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin) vers `snapshots/baseline-YYYY-MM-DD/<app>/<resource>.json`
- Premier dump committé : `snapshots/baseline-2026-05-07/` (date du jour à l'exécution)
- README expliquant comment relancer un snapshot avant tests risqués
- `renovate.json` initial

**Critères de fin** :
- `tools/snapshot/snapshot.sh` exécuté localement → produit JSON pour les 6 apps (snapshot Jellyfin nécessite création préalable du compte admin + génération API key, voir NG5)
- Tous les fichiers JSON committés dans `snapshots/baseline-<date>/`
- Aucune écriture observée (vérifier logs Sonarr/Radarr : que des reads, aucun write)
- Possibilité de comparer : `diff snapshots/baseline-<date>/sonarr/downloadclient.json $(arrconf dump apps=sonarr)` (à venir Phase 1)

**Estimation** : 0.5 journée

### Phase 1 — arrconf POC + snapshot YAML + JSON Schema

**Livrables** :
- Squelette `tools/arrconf/` (Python, Dockerfile, pyproject, tests)
- Workflow GitHub Actions `arrconf-image.yml` opérationnel → image `ghcr.io/tom333/arr-stack-arrconf:sha-<short>` poussée
- Workflow `tests.yml` opérationnel
- Sous-commandes `dump` et `diff` implémentées pour Sonarr (read-only, peuvent tourner immédiatement contre l'existant)
- Sous-commande `apply` implémentée pour UN type de ressource sur Sonarr : **download clients**
- Sous-commande `schema-gen` implémentée + `schemas/arrconf-schema.json` committé (JSON Schema des modèles pydantic du config)
- Directive `# yaml-language-server: $schema=...` ajoutée en tête de `examples/baseline-sonarr.yml` et `charts/arr-stack/files/arrconf.yml` (créés en Phase 4) pour que VS Code / code-server activent l'autocomplétion automatiquement
- `.vscode/settings.json` optionnel mappant `*arrconf*.yml` au schéma
- Workflow CI `tests.yml` ajoute un check : `arrconf schema-gen` doit produire un fichier identique à `schemas/arrconf-schema.json` (sinon CI fail → force la régénération à chaque ajout de reconciler/resource)
- Premier `arrconf dump --apps sonarr` exécuté → `examples/baseline-sonarr.yml` committé
- README minimal

**Critères de fin** :
- `pytest` vert
- Image buildée et publique
- `arrconf dump --apps sonarr` produit un YAML conforme au schéma arrconf, qui round-trip avec `arrconf diff --config examples/baseline-sonarr.yml --apps sonarr` → 0 diff (idempotence prouvée)
- Test manuel : `arrconf apply --config examples/baseline-sonarr.yml --apps sonarr --dry-run` → log "no-op" puisque YAML = état actuel
- **Autocomplétion VS Code fonctionnelle** : ouvrir `examples/baseline-sonarr.yml` dans code-server, taper sous `download_clients:` → propositions des champs valides (host, port, category, tags...) avec descriptions tirées des docstrings pydantic
- Pas encore de chart, pas encore d'umbrella, pas encore de déploiement K8s

**Estimation** : 1.5 journée (ajout schema-gen + intégration VS Code par rapport à 1 journée initial)

### Phase 2 — Validation cluster

**Pré-requis** : nouveau snapshot raw juste avant déploiement (`tools/snapshot/snapshot.sh > snapshots/before-phase-2-<date>/`) — capturer l'état exact avant que le CronJob ne tourne pour la première fois en mode `apply`.

**Livrables** :
- Mini chart `charts/arrconf-only/` (juste arrconf, pas l'umbrella) ou intégration ad-hoc dans `my-kluster`
- ArgoCD Application qui déploie arrconf en CronJob dans `selfhost`, avec **`ARRCONF_DRY_RUN=true` au premier déploiement**
- Secret manuel `arrconf-secret.yaml` dans `my-kluster/secrets/`
- Premier run réel en cluster en `--dry-run` réussi (logs only, aucune écriture)
- Bascule en mode apply (`ARRCONF_DRY_RUN=false`) après validation des logs

**Critères de fin** :
- CronJob arrconf existe dans `selfhost`
- Job manuel `kubectl create job --from=cronjob/arrconf` → exit 0
- Premier run en `--dry-run` : logs montrent les actions qui seraient prises, AUCUN écriture observée côté Sonarr (vérifier via re-snapshot après ce run)
- Après bascule en apply : Sonarr UI montre le download client géré par arrconf
- Drift detection validée : modification UI → écrasée au run suivant

**Estimation** : 0.5 journée

### Phase 3 — Étendre arrconf

**Pré-requis** : nouveau snapshot raw avant de commencer (`tools/snapshot/snapshot.sh > snapshots/before-phase-3-<date>/`).

**Livrables** :
- Reconcilers : indexers, notifications, root folders, tags, host config
- Apps : Radarr, Prowlarr (avec app sync vers Sonarr/Radarr)
- Pour chaque app, `arrconf dump --apps <app>` exécuté **avant** d'écrire un reconciler, output committé dans `examples/baseline-<app>.yml` — le YAML désiré démarre depuis l'existant
- Régénération de `schemas/arrconf-schema.json` après chaque ajout de resource type ou app (la CI bloque si oublié)
- Tests pour chaque reconciler

**Critères de fin** :
- Pour chaque nouveau reconciler : round-trip `dump → apply --dry-run` → 0 action (idempotence)
- Diff `snapshots/baseline-<date>/ vs snapshots/after-phase-3-<date>/` montre uniquement les changements intentionnels
- VS Code propose les nouveaux champs (indexers, notifications, etc.) dès qu'on ouvre un YAML avec la directive `$schema`

**Estimation** : 2 journées

### Phase 4 — Umbrella chart

**Livrables** :
- `charts/arr-stack/` umbrella avec deps app-template (alias par service)
- Migration des **9 apps déjà déployées** de `my-kluster` dans l'umbrella : sonarr, radarr, prowlarr, cleanuparr, configarr, qbittorrent, seerr, flaresolverr, jellyfin
- Suppression dans `my-kluster` : `argocd/argocd-apps/{sonarr,radarr,prowlarr,cleanuparr,configarr,qbittorrent,seerr,flaresolverr,jellyfin}-app.yaml` + `charts/configarr/`
- Création de `argocd/argocd-apps/arr-stack-app.yaml` dans `my-kluster`
- Renovate `customManagers` opérationnel et testé (un bump validé bout-en-bout)
- Pinning des tags `:latest` (qbittorrent, flaresolverr, cleanuparr) sur des tags semver explicites

**Critères de fin** :
- ArgoCD sync de l'umbrella OK (9 apps déployées via 1 chart)
- Renovate propose un bump d'image et le merge en auto-merge
- Aucune régression sur les 9 apps
- Ingress publics, hostPath partagés (`/opt/media-stack/torrents` entre qBit, Sonarr, Radarr), et PVC NFS partagés (`media-nas-pvc` entre Sonarr, Radarr, Jellyfin) restent fonctionnels
- Auth Jellyfin (interne, sans oauth2-proxy) reste fonctionnelle

**Estimation** : 1 journée

### Phase 5 — Reconciler qBittorrent + split tv/anime/family

**Note** : qBittorrent **déjà déployé**. Cette phase couvre le reconciler arrconf qBittorrent **ET** la mise en place du split tv/anime/family selon le pattern single-instance + tags (voir ADR-7). C'est le moment naturel parce que les catégories qBit sont au cœur du routing.

**Pré-requis** : snapshot raw qBittorrent + Sonarr + Radarr (`tools/snapshot/snapshot.sh --apps qbittorrent,sonarr,radarr`) + dump YAML AVANT toute écriture.

**Livrables côté qBittorrent** :
- Reconciler `qbittorrent.py` : settings clés (max connections, alternative speed limits, behavior)
- 6 catégories déclarées avec save_paths distincts :
  - `sonarr-tv` → `/data/series`
  - `sonarr-anime` → `/data/anime`
  - `sonarr-family` → `/data/family`
  - `radarr-movies` → `/data/movies`
  - `radarr-anime` → `/data/movies-anime`
  - `radarr-family` → `/data/movies-family`

**Livrables côté Sonarr (instance unique `main`)** :
- Tags : `tv`, `anime`, `family`
- Root folders : `/media/series`, `/media/anime`, `/media/family`
- 3 download clients qBittorrent déclarés, chacun avec son `tags:` ciblant un seul tag
- Cohabitation avec configarr : 3 quality profiles (MULTi.VF, Anime, Family) déclarés côté configarr, scores adaptés (ex: VOSTFR positif sur Anime)

**Livrables côté Radarr (instance unique `main`)** :
- Mêmes 3 tags + 3 root folders + 3 download clients par tag

**Critères de fin** :
- Création test : ajouter manuellement une série taggée `anime` dans Sonarr UI → vérifier que le download arrive dans `/data/anime` côté qBit puis hardlink dans `/media/anime`
- `arrconf diff` après le test = 0 action (idempotence sur tags/root folders/download clients)
- Configarr met à jour les 3 profils sans casser les existants

**Estimation** : 1.5 journée (ajout du split en plus du reconciler qBit)

### Phase 6 — Reconciler arrconf Seerr

**Note** : Seerr **déjà déployé** (`ghcr.io/seerr-team/seerr` v3.2.0 dans `argocd/argocd-apps/seerr-app.yaml`). Cette phase ne couvre que le reconciler arrconf.

**Pré-requis** : snapshot raw Seerr + dump YAML AVANT toute écriture.

**Livrables** :
- Vérification compatibilité API Seerr vs Overseerr/Jellyseerr (Seerr est un fork actif → API probablement compatible). Voir §10 Q1.
- **Vérification de la stratégie de routing tags depuis Seerr vers Sonarr** (§10 Q10) : Seerr expose-t-il un champ tag à la requête ? Si oui : router auto par genre. Si non : fallback "tag par défaut + ré-tag manuel dans Sonarr UI" pour les cas anime/family.
- Reconciler `seerr.py` : services Sonarr/Radarr connectés (single Sonarr `main`, single Radarr `main`), users (au minimum admin), requests config (auto-approve, request limits), default tags par type de contenu si supporté

**Estimation** : 1 journée (si l'API est bien Overseerr-compatible)

### Phase 7 — Reconciler arrconf Jellyfin

**Note** : Jellyfin **déjà déployé** (`lscr.io/linuxserver/jellyfin` 10.11.8 dans `argocd/argocd-apps/jellyfin-app.yaml`). API REST différente des *arr (auth par `X-Emby-Token` ou `?api_key=`, pas `X-Api-Key`). Cette phase ne couvre que le reconciler arrconf.

**Pré-requis** :
- Compte admin Jellyfin créé via UI (bootstrap manuel — voir NG5)
- API key générée dans Dashboard → API Keys
- Snapshot raw Jellyfin + dump YAML AVANT toute écriture

**Livrables** :
- Reconciler `jellyfin.py` couvrant en priorité :
  - **Libraries** (CRUD : Movies → `/media/movies`, TV Shows → `/media/series`, Music optionnel) — pointage sur les paths Sonarr/Radarr partagés via NFS
  - **Users** (admin + utilisateurs additionnels avec quotas / restrictions)
  - **Server config** (transcoding hardware, networking, schedules, scan automatique)
- Optionnel best-effort : plugins (auto-install + activation depuis le YAML)
- Tests + fixtures Jellyfin

**Critères de fin** :
- `arrconf dump --apps jellyfin` round-trip = 0 diff (idempotence prouvée)
- Bibliothèques pointant correctement sur le NFS partagé `/media/{movies,series}`
- Users gérés via YAML (au moins admin + 1 user de test)

**Estimation** : 1.5 journée (API plus exotique que les *arr — temps de découverte + tests)

### Phase 8 — RETIRÉE (2026-05-22)

Le projet de migration ESO/Akeyless a été retiré de la roadmap. Bitnami sealed-secrets côté `my-kluster` est la solution de production stable et long-terme pour les bootstrap secrets `arrconf-env` + `configarr-env`. Aucune migration externe-secret n'est planifiée.

---

## 8. Critères de succès (globaux)

- **CS1** — Aucune intervention UI pour la config Sonarr/Radarr/Prowlarr/qBittorrent/Seerr/Jellyfin après bootstrap initial (création compte admin Jellyfin exceptée — voir NG5).
- **CS2** — Une PR sur `arr-stack` modifiant un champ de config se matérialise en cluster en moins de 1h (sync ArgoCD + run CronJob arrconf).
- **CS3** — Un drift en UI est détecté et corrigé au run suivant (max 4h selon schedule).
- **CS4** — Renovate propose en auto-merge les bumps d'image minor/patch sans intervention.
- **CS5** — Tous les bootstrap secrets restent maîtrisés dans `my-kluster/secrets/` via Bitnami sealed-secrets (baseline stable long-terme — pas de migration externe-secret planifiée).
- **CS6** — `helm template charts/arr-stack/ -f examples/values-prod.yaml` rend des manifestes valides (kubeconform OK).
- **CS7** — `pytest` couvre ≥ 70 % du code arrconf, focus sur differ et reconcilers.
- **CS8** — README permet à un autre dev (ou toi-dans-3-mois) de comprendre et déployer en moins de 30 min.

---

## 9. Intégration avec my-kluster

### 9.1 Avant migration

État actuel — **9 ArgoCD Applications** dans `my-kluster/argocd/argocd-apps/` :
- `sonarr-app.yaml`
- `radarr-app.yaml`
- `prowlarr-app.yaml`
- `cleanuparr-app.yaml`
- `configarr-app.yaml`
- `qbittorrent-app.yaml`
- `seerr-app.yaml`
- `flaresolverr-app.yaml`
- `jellyfin-app.yaml`

Plus le chart custom `charts/configarr/` dans `my-kluster`.

### 9.2 Après migration (post-Phase 4)

État cible — 1 ArgoCD Application dans `my-kluster/argocd/argocd-apps/` :

```yaml
# my-kluster/argocd/argocd-apps/arr-stack-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: arr-stack
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  destination:
    namespace: selfhost
    server: https://kubernetes.default.svc
  project: selfhost-project
  source:
    repoURL: https://github.com/tom333/arr-stack.git
    targetRevision: v0.1.0
    path: charts/arr-stack
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
      - ServerSideApply=true
    automated:
      selfHeal: true
      prune: true
```

Suppression dans `my-kluster` :
- `argocd/argocd-apps/sonarr-app.yaml`
- `argocd/argocd-apps/radarr-app.yaml`
- `argocd/argocd-apps/prowlarr-app.yaml`
- `argocd/argocd-apps/cleanuparr-app.yaml`
- `argocd/argocd-apps/configarr-app.yaml`
- `argocd/argocd-apps/qbittorrent-app.yaml`
- `argocd/argocd-apps/seerr-app.yaml`
- `argocd/argocd-apps/flaresolverr-app.yaml`
- `argocd/argocd-apps/jellyfin-app.yaml`
- `charts/configarr/` (déplacé dans `arr-stack/charts/arr-stack/files/configarr.yml` + templates)

Conservation dans `my-kluster` :
- `secrets/arrconf-secret.yaml` + `secrets/configarr-secret.yaml` — bootstrap secrets gérés via Bitnami sealed-secrets (baseline stable long-terme)
- Mise à jour de `CLAUDE.md` pour documenter le découplage et pointer sur le repo arr-stack

### 9.3 Compatibilité ascendante

- Pendant la migration (Phase 4), prévoir une fenêtre de transition où l'umbrella ET les apps unitaires peuvent coexister (test sur un cluster de staging idéalement, sinon validation pas-à-pas en prod).
- Recyclarr a déjà été désactivé (`recyclarr-app.yaml.disable`). Cette suppression est définitive.

---

## 10. Questions ouvertes (ambiguïtés à résoudre en discuss-phase)

- **Q1** — **Compatibilité API Seerr vs Overseerr/Jellyseerr** : Seerr est identifié (`ghcr.io/seerr-team/seerr` v3.2.0, fork actif déjà déployé). Reste à vérifier que l'API REST est restée Overseerr-compatible (a priori oui, mais à valider sur 2-3 endpoints critiques : `/api/v1/settings/services`, `/api/v1/user`, `/api/v1/request`) avant d'écrire le reconciler. À résoudre AVANT Phase 6.
- **Q2** — **Option Helm dependencies vs sub-charts** (cf §6.2). À arbitrer avant Phase 4.
- **Q3** — **Schedule arrconf** : 4h (comme configarr) ou plus fréquent ? Plus fréquent = drift corrigé plus vite, mais plus de charge API. Recommandation initiale : 6h.
- **Q4** — **Mode de release** : tags manuels vs release-please vs semantic-release. À arbitrer en Phase 1/2.
- **Q5** — **Cohabitation arrconf/configarr sur quality_profiles** : si arrconf veut un jour gérer aussi les profils, comment éviter la guerre ? Décision : **arrconf NE TOUCHE PAS aux quality_profiles ni custom_formats.** À documenter explicitement dans le code (refus côté reconciler).
- **Q6** — **Backup du state arrconf** : le script est idempotent et stateless, mais les ressources créées (notifications, indexers) ont des IDs internes. Faut-il un mécanisme de marquage (tag arrconf-managed) pour distinguer ce qui est piloté de ce qui est manuel ? Recommandation : **oui, ajouter un tag `arrconf-managed` sur les ressources créées par le script** (champ `tags:` standard *arr).
- **Q7** — **Compatibilité multi-versions des APIs *arr** : Sonarr v4 vs v3 ont des breaking changes. Le script doit-il versionner ses appels ? Recommandation : tester sur Sonarr v4+ uniquement (déjà la version déployée), documenter comme prérequis.
- **Q8** — **Stratégie `prune` par défaut** : si une ressource est en cluster mais pas dans le YAML, on supprime ou on log et on garde ? Recommandation : `prune: false` par défaut, opt-in par section.
- **Q9** — **Jellyfin auth header** : l'API utilise `X-Emby-Token` (legacy) ou `Authorization: MediaBrowser Token=...`. À choisir selon ce qui marche en 10.11.8 — probablement `?api_key=<key>` query param suffit pour la plupart des endpoints. À valider en Phase 7 avant d'écrire le client. Conséquence : `client_base.py` doit pouvoir overrider la stratégie d'auth par app.
- **Q10** — **Routing tags Seerr → Sonarr/Radarr** : avec single instance + tags (ADR-7), Seerr doit pouvoir indiquer le tag (`tv`/`anime`/`family`) à la requête pour que Sonarr ajoute la série dans le bon root folder + bonne catégorie qBit. Question : Seerr expose-t-il ce mécanisme via `defaultTags` par service connecté ou par utilisateur ? À valider en Phase 6 avec un test pratique (créer un user "anime", configurer son default tag, requêter une série). Fallback si non supporté : tag par défaut côté Sonarr (`tv`) + ré-tag manuel post-import pour les minoritaires (anime, family).

---

## 11. Décisions clés (ADR-like)

### ADR-1 — Script Python custom plutôt que Buildarr/Terraform/Flemmarr

**Contexte** : besoin de gérer la config des apps *arr et apparentées comme code, dans un cluster privé, avec qBittorrent et Seerr inclus.

**Décision** : développer un script Python custom inspiré de Flemmarr.

**Raisons** :
- Buildarr en maintenance, pas de support Seerr
- Terraform : qBit/Seerr providers immatures, GitHub Actions ne peut pas atteindre le cluster privé, state lourd
- Flemmarr : utilisé comme référence (lecture du source) mais on veut maîtriser et étendre
- Python connu par l'auteur, écosystème mature pour HTTP + YAML + validation
- 200-500 LOC pour le cœur — coût acceptable pour la liberté

**Conséquences** :
- Maintenance par l'auteur (pas de communauté)
- Tests cruciaux pour éviter les régressions API
- Pattern reproductible si nouvelle app à intégrer

### ADR-2 — Helm dependencies sur app-template (Option A)

**Contexte** : structurer l'umbrella chart.

**Décision** : utiliser `dependencies:` dans `Chart.yaml` pointant sur `bjw-s/app-template`, avec alias par service.

**Raisons** :
- Pas de duplication de code Helm
- Hérite des évolutions upstream (déjà utilisé partout dans my-kluster)
- Renovate suit naturellement la version d'app-template

**Conséquences** :
- Multiples alias du même chart — syntax à valider en Phase 4
- Si bjw-s casse, impact transverse sur tous les services

### ADR-3 — Image arrconf hébergée sur GHCR public

**Contexte** : le cluster doit pouvoir pull l'image sans credentials, GitHub Actions doit pouvoir push.

**Décision** : `ghcr.io/tom333/arr-stack-arrconf` en visibilité publique.

**Raisons** :
- Cluster pull anonyme : ✅
- GitHub Actions push avec GITHUB_TOKEN : ✅
- Renovate suit GHCR : ✅
- Pas de coût : ✅
- Pas de risque sécurité (pas de secrets dans l'image)

**Alternative rejetée** : `localhost:32000` (build local manuel, pas de CI, pas reproductible).

### ADR-4 — Repo séparé plutôt qu'extension de my-kluster

**Contexte** : où vivre arr-stack ?

**Décision** : repo dédié `github.com/tom333/arr-stack`.

**Raisons** :
- arrconf est du code logiciel (Python, Docker, CI, tests) qui mérite son repo
- Renovate config customisable sur mesure pour le pattern umbrella
- Stack média = produit cohérent, distinct de l'infra cluster
- Versionnement atomique
- Précédent existant : `tom333/cv` est déjà séparé

**Conséquences** :
- 2 cycles de PR pour certains changements
- Effort de découpage initial (~1 journée)
- Documentation cross-repo nécessaire

### ADR-5 — configarr conservé pour son scope

**Contexte** : tentation de tout faire dans arrconf.

**Décision** : configarr reste responsable des quality profiles, custom formats, quality definitions, media naming. arrconf NE touche PAS à ces ressources.

**Raisons** :
- Configarr digère TRaSH-Guides upstream (templates, IDs, scores qui évoluent)
- Reproduire ça en arrconf = maintenance lourde inutile
- Séparation de responsabilités claire

**Conséquences** :
- Deux outils à maintenir, mais scopes orthogonaux
- Si configarr s'arrête un jour, l'auteur réabsorbera son scope dans arrconf

### ADR-6 — Snapshot baseline avant toute écriture

**Contexte** : la stack actuelle a accumulé de la config (manuel UI, Recyclarr passé, configarr actuel). Tester arrconf en cluster comporte un risque non-trivial de casser un état non-documenté.

**Décision** :
1. **Phase 0** est dédiée à un script Bash standalone (`tools/snapshot/snapshot.sh`) qui fait un dump raw JSON de toutes les APIs avant tout autre travail.
2. **Phase 1** ajoute `arrconf dump` qui exporte le même état au format YAML arrconf, seedé dans `examples/baseline-<app>.yml`.
3. **Phase 2** déploie arrconf en cluster avec `ARRCONF_DRY_RUN=true` au premier run, bascule en apply seulement après validation des logs.
4. **Phases 3-7** : chaque phase touchant une nouvelle app commence par un re-snapshot (`snapshots/before-phase-N-<date>/`).
5. Tous les snapshots restent dans Git (lossless, pas de secret, ~quelques MB).

**Raisons** :
- Insurance bon marché contre les casse silencieuses
- Permet `diff` forensic à n'importe quel moment
- Le `dump` arrconf de Phase 1 garantit que la config-as-code initiale = config réelle (pas de divergence cachée)
- Le `--dry-run` au premier run cluster prouve qu'arrconf ferait les bonnes actions avant de les faire

**Conséquences** :
- Phase 0 dédiée à du Bash standalone (peu de Python) — décalage de 0.5 journée du POC arrconf
- Discipline à tenir : re-snapshot AVANT chaque phase de scope nouveau
- Repo grossit légèrement (snapshots committés) mais c'est négligeable

### ADR-7 — Single instance Sonarr/Radarr + tags (pas multi-instance)

**Contexte** : pour différencier les contenus (tv, anime, family) il faut une stratégie de routing — chaque type ayant son root folder, sa catégorie qBit, ses préférences qualité. Deux options : multi-instance (TRaSH-Guides standard) ou single-instance + tags.

**Décision** : **single-instance par app** (1 sonarr, 1 radarr), différenciation via :
- 3 tags Sonarr/Radarr : `tv`, `anime`, `family`
- 3 root folders par instance (`/media/series`, `/media/anime`, `/media/family` côté Sonarr ; équivalents côté Radarr)
- 3 download clients qBittorrent par instance, chacun lié à un tag — Sonarr/Radarr router le download vers le bon client en fonction du tag de la série/film
- 6 catégories qBit avec save_path distincts
- 3 quality profiles par instance côté configarr (MULTi.VF / Anime / Family) avec scoring adapté par profil

**Raisons** :
- Volumétrie homelab modérée → la BDD SQLite Sonarr unique tient sans problème
- 1 pod / 1 PVC / 1 ingress / 1 API key par app vs 3-6 pods en multi-instance — coût ressource minimal
- Configarr et arrconf YAML restent simples (un seul bloc `sonarr.main` et `radarr.main`)
- Renovate suit 1 image par app au lieu de 3
- Si l'usage évolue, re-tagger sans recréer d'instance
- Le routing par tag est un mécanisme natif Sonarr/Radarr (champ `tags:` sur les download clients) — pas un workaround

**Conséquences / limitations acceptées** :
- Single point of failure : si la BDD Sonarr corrompt, tout le contenu (tv + anime + family) est touché. Atténué par les snapshots arrconf et les backups Sonarr natifs
- Routing Seerr → tag : à valider (Q10). Si Seerr ne supporte pas de tag par défaut par user/type, l'utilisateur Seerr ajoute toujours en `tv`, ré-tag manuel pour anime/family minoritaires
- Settings globaux de l'instance (release profiles, host config) partagés entre tous les types — acceptable car similaires
- Indexers Prowlarr poussés à l'instance unique, le ciblage anime-only se fait via tags côté Prowlarr (à vérifier en Phase 3)

**Alternatives rejetées** :
- **Multi-instance** (sonarr-tv, sonarr-anime, sonarr-family + radarr-movies, radarr-anime, radarr-family) : coût ressource × 3 et complexité GitOps significative pour un bénéfice d'isolation marginal en homelab. À reconsidérer uniquement si la BDD unique sature ou si Q10 conclut que Seerr ne peut pas router par tag.

### ADR-8 — arrconf is a trusted controller — bypasses *arr UI-grade pre-save validation

**Contexte** : Sonarr (et par extension Radarr/Prowlarr en *arr v3+) effectue une pré-validation côté serveur sur tout PUT modifiant une ressource avec credentials (download_client.password, indexer.apiKey, etc.). Cette pré-validation est conçue pour rattraper les misconfigs UI : elle re-authentifie contre le service externe (qBittorrent, indexer) en utilisant la valeur littérale du champ. Côté arrconf, le helper `merge_fields_for_put` (Phase 2.1, D-31) préserve le mask `********` pour les champs `privacy=password` parce que arrconf YAML ne porte jamais de vrai secret (CLAUDE.md "Variables d'environnement"). Résultat : le PUT atomique d'arrconf échoue en 400 dès qu'un champ top-level change vraiment, parce que Sonarr essaie d'auth qBit avec `********` comme mot de passe.

**Décision** : tout client *arr v3 d'arrconf (Sonarr, Radarr, Prowlarr) envoie systématiquement `?forceSave=true` sur les PUT UPDATE. Cela demande à Sonarr de skipper la pré-validation et d'écrire la ressource telle quelle. arrconf est un **trusted controller** — le scénario que la pré-validation protège (humain qui se trompe via UI) ne s'applique pas. L'implémentation vit au layer HTTP client (`_ArrV3Client.put()` dans `tools/arrconf/arrconf/client_base.py`) — Phase 3's `RadarrClient` et `ProwlarrClient` héritent par construction.

**Raisons** :
- arrconf a déjà décidé qu'un changement réel est nécessaire via son propre `diff` (idempotence golden rule, CLAUDE.md)
- Le body PUT est construit pour préserver les credentials du cluster par design (D-31/D-32 — value-based merge contract de Phase 2.1)
- Le pre-save validation Sonarr est une pré-validation UX pour utilisateurs humains ; arrconf n'est pas un humain
- Sans `forceSave=true`, la moitié correction de REQ-drift-detection est inatteignable sans intervention opérateur manuelle (constaté Phase 2.1 W-04 dispositive — D-02.1-06)
- Centraliser au layer HTTP client (D-02.2-02) plutôt qu'au layer reconciler évite le mode d'échec "j'ai oublié le kwarg" pour Phase 3+

**Conséquences** :
- Un nouveau log event `put_force_save_used` (event=info, payload `{path, id}`) est émis à chaque UPDATE PUT — auditable côté cluster JSON logs aux côtés de `merge_field_preserved` et `plan_action`
- Phase 3 Radarr/Prowlarr héritent par construction du comportement (intermediate class `_ArrV3Client`) — pas de discipline contributeur
- qBittorrent (Phase 5) et Jellyfin (Phase 7) ont des sémantiques PUT différentes ; ils restent **OUT OF SCOPE** de `forceSave` (leur classe parent reste `ArrApiClient` directement, pas `_ArrV3Client`)
- Si Sonarr introduit un jour un check pre-save vraiment utile, arrconf le skippera. Trade-off acceptable : les checks utiles seraient une régression upstream, pas une feature ; on les détectera par la perte d'idempotence (qui resterait visible dans les logs `plan_action`)
- Le trigger est l'action (UPDATE), pas le contenu du body — ADD (POST) et DELETE ne portent pas `forceSave`

**Alternatives rejetées** :
- **Trigger conditionnel sur mask dans body** (Option B de D-02.1-06) : ajoute un body scan + maintenance d'un alphabet de mask Sonarr (`********`, `***REDACTED***`, autres ?) — coût de maintenance inutile pour un gain de sécurité négligeable (la pré-validation étant inutile dans le contexte arrconf de toute façon)
- **Trigger conditionnel sur événements `merge_field_preserved` émis** : couple le layer HTTP au layer merge — inversion de responsabilité
- **Override au layer reconciler `_execute`** : crée une discipline par-reconciler ("n'oublie pas `params={"forceSave": "true"}`") — exactement le mode d'échec qu'on veut éviter pour Phase 3
- **Class flag `force_save_on_put: bool`** sur `ArrApiClient` (Option a) : plus court mais inverse le défaut — qBit/Jellyfin doivent se rappeler de remettre `False`. Le sous-typage explicite (`_ArrV3Client`) est plus auto-documenté pour Phase 5/7 contributeurs

#### ADR-8.1 — Refinement (v0.1.5) — omit-by-privacy-metadata for credential fields

**Contexte (réalisation du risque accepté ADR-8)** : la "Conséquences" d'ADR-8 anticipait *« si Sonarr introduit un jour un check pre-save vraiment utile, arrconf le skippera »*. Ce cas s'est produit en production le 2026-05-09 (Plan 02.2-06 visual UAT FAILED). Le pre-save check que Sonarr fait pour les champs `privacy=password|userName` EST utile : il re-authentifie contre le service externe (qBit, indexer) avec la valeur littérale du champ. v0.1.4 (`?forceSave=true`) bypassait ce check. Combiné avec le helper Phase 2.1 `merge_fields_for_put` qui préserve la valeur cluster (qui pour `privacy=password` EST le mask `"********"` côté GET Sonarr), résultat : la mask littérale `"********"` était écrite comme valeur réelle du champ password, écrasant le credential. Sonarr's GET continuait à sérialiser `"********"` (indissociable d'un mask normal), rendant la régression invisible aux snapshot diffs. Détection uniquement comportementale (bouton "Test" de l'UI Sonarr → 401/403 contre qBit).

Référence d'incident : `.planning/phases/02.2-v0-1-4-forcesave-fix/deferred-items.md` §D-02.2-AUTH-REGRESSION + `.planning/phases/02.2-v0-1-4-forcesave-fix/02.2-06-SUMMARY.md` §"Operator Visual Gate FAILED".

**Décision (raffinement, append-only — ADR-8 reste tel quel)** : ajouter une protection au layer **merge** (pas au layer HTTP — ADR-8 reste valide pour les champs non-credential). Dans `differ.py:merge_fields_for_put`, si le champ cluster a `privacy in ("password", "userName")`, **OMETTRE** l'entrée du body PUT entièrement. Sonarr préserve la valeur stockée quand un champ est absent du body — c'est le comportement sûr pour les credentials. Émettre un événement structuré `merge_field_omitted_credential` (payload `{name, privacy}` — métadonnées seulement, jamais de valeur) pour audit cluster. Implémentation Plan 02.2-08 (commit `fix(02.2-08): omit privacy=password|userName entries from merge_fields_for_put PUT body (GREEN)`).

Stratégie retenue : **Option A (omit-by-privacy-metadata)** parmi les trois envisagées dans `deferred-items.md` §D-02.2-AUTH-REGRESSION. Les deux autres ont été rejetées (voir §Alternatives rejetées 8.1 ci-dessous).

**Raisons** :
- **Cohésion** : le fix vit dans la même fonction (`merge_fields_for_put`) que le bug. Pas de nouveau module, pas de couplage HTTP↔merge.
- **Surface minimale** : ~10 lignes ajoutées dans `differ.py`. La logique force_save (D-02.2-02 / Plan 02 / `_ArrV3Client.put()`) reste inchangée.
- **Métadonnée fiable** : Sonarr's GET retourne `privacy: "password"` / `privacy: "userName"` pour chaque champ credential — contrat stable Sonarr v3 (vérifié dans `tools/arrconf/tests/fixtures/sonarr/downloadclient.json` L53/L63 + en cluster).
- **Sémantique Sonarr documentée** : un champ absent du body PUT préserve la valeur stockée. Mêmes garanties que `forceSave=true` exploite pour les champs non-credential, mais pour les credentials l'absence est l'opération correcte (pas le passthrough).
- **Auditable** : `merge_field_omitted_credential` apparaît dans les logs JSON du CronJob aux côtés de `merge_field_preserved` et `put_force_save_used`.

**Conséquences (stance à deux couches — defense-in-depth)** :
- **Couche HTTP (ADR-8 / `_ArrV3Client.put()` / Plan 02)** : `?forceSave=true` reste actif sur tous les UPDATE PUT *arr v3. Inchangé. Couvre la correction automatique des drifts non-credential (priority, host, port, urlBase, tvCategory, etc.).
- **Couche merge (ADR-8.1 / `merge_fields_for_put` / Plan 08)** : les champs `privacy=password|userName` sont absents du body PUT. Couvre le cas où le body ne peut pas être valide par construction (mask Sonarr non utilisable comme credential).
- Les deux couches sont **indépendantes et complémentaires** : retirer l'une ré-ouvre une classe de régression. ADR-8 sans ADR-8.1 → la régression D-02.2-AUTH-REGRESSION (production 2026-05-09, Plan 06 SUMMARY §"Operator Visual Gate FAILED"). ADR-8.1 sans ADR-8 → la régression D-02.1-06 (HTTP 400 sur tout UPDATE avec mask en body, Phase 2.1).
- **qBittorrent (Phase 5) et Jellyfin (Phase 7) restent OUT OF SCOPE des deux couches**. Leurs classes-clients n'héritent ni d'ADR-8 (`_ArrV3Client.put()` non applicable — sémantiques PUT différentes) ni d'ADR-8.1 (le helper `merge_fields_for_put` est utilisé uniquement par les reconcilers `*arr v3`, pas par les reconcilers `qBittorrent`/`Jellyfin` qui auront leurs propres patterns de body-construction quand ces phases atterriront).
- **`merge_field_preserved` (Phase 2.1, D-31/D-32) reste valide pour les champs non-credential** : si YAML est vide et cluster a une valeur non-mask (e.g. `tvCategory="sonarr"`), l'helper substitue. Le test `test_merge_fields_preserves_non_credential_empty_yaml_passthrough` (Plan 07) garde-foule cette invariant.
- Trade-off : la stratégie traite `privacy=userName` uniformément avec `privacy=password` — même quand la valeur cluster userName est une chaîne réelle (`"admin"`). Symétrie architecturale intentionnelle : le credential est la paire (username, password) ; l'omission de l'un sans l'autre serait incohérente. La discipline env-only-secret (CLAUDE.md "Variables d'environnement") garantit que YAML ne porte jamais ni l'un ni l'autre, donc la ré-saisie opérateur côté UI Sonarr couvre les deux d'un coup.

**Contrats de test (verrous régression)** :
- `tools/arrconf/tests/test_differ.py::test_merge_fields_omits_privacy_password_when_value_is_api_mask` — exerce le mask littéral production `"********"` (Plan 07 RED → Plan 08 GREEN)
- `tools/arrconf/tests/test_differ.py::test_merge_fields_omits_privacy_password_when_value_is_in_tree_redacted_mask` — exerce le mask de fixture `"***REDACTED***"` (Plan 07 RED → Plan 08 GREEN). Le test passant exclusivement par les **métadonnées privacy** (et pas un alphabet de mask) prouve que la stratégie n'est pas Option B (mask-token detect, rejetée).
- `tools/arrconf/tests/test_differ.py::test_merge_fields_preserves_non_credential_empty_yaml_passthrough` — garde-fou : Phase 2.1 D-31/D-32 reste valide pour les champs non-credential.
- `tools/arrconf/tests/test_differ.py::test_merge_field_omitted_credential_event_payload_excludes_value` — T-02.2-08-01 : aucune valeur credential dans les logs.
- `tools/arrconf/tests/test_reconcilers_sonarr.py::test_update_omits_privacy_credential_fields_from_put_body` — contrat intégration au layer reconciler (renommé depuis `test_update_preserves_redacted_credentials_in_put_body` qui asserrait l'ancien comportement Phase 2.1 maintenant intentionnellement inversé).
- Plan 02's `test_update_passes_forceSave_query_param` + ADD/DELETE négatifs — ADR-8 stance préservée, vérifiable indépendamment.

**Alternatives rejetées (8.1)** :
- **Option B (détection mask-token dans body)** : maintenir un alphabet de tokens (`"********"`, `null`, formes futures Sonarr ?). Générique mais fragile — le moindre changement Sonarr de mask invalide la protection. Rejetée pour la même raison qu'ADR-8 a rejeté Option B (D-02.1-06) : couplage à un littéral non-stable.
- **Option C (drop forceSave conditionnellement)** : garder le mask dans le body mais retirer `?forceSave=true` quand le body contient un mask connu. Sonarr's pre-save validation rejetterait alors avec HTTP 400 — ré-introduisant la régression D-02.1-06 que Plan 02 a fermée. Reverts à un modèle "manual nudge" pour les credentials → REQ-drift-detection redeviendrait opérateur-dépendante. Rejetée : perte d'acquis architectural pour un gain de detection-loud-failure marginal.
- **Override au layer reconciler `_execute`** : dupliquer la logique d'omission dans chaque reconciler (Sonarr, Phase 3 Radarr, Prowlarr). Mêmes raisons qu'ADR-8 D-02.2-02 : "discipline par-reconciler" est exactement le mode d'échec qu'on évite.
- **Suppression de `merge_field_preserved` entirely** : reverts D-31/D-32, casse les champs YAML vides non-credential. Hors-scope (régresse Phase 2.1 contracts).

---

### ADR-9 — Jellyfin plugin reconciler: install-capable (reversal of D-07-PLUGINS-01)

**Phase 24 / JFSKIP-02 — 2026-05-29**

arrconf's Jellyfin plugin reconciler moves from activation-only (D-07-PLUGINS-01) to install-capable. Full ADR in `.planning/PROJECT.md` decisions table (ADR-9). Summary:

- **Mechanism:** `POST /Packages/Installed/{name}?assemblyGuid&version&repositoryUrl` when plugin absent + install fields set on `PluginEntry`; logs `plugin_install_queued` with kubectl restart hint.
- **Two-run model (D-02):** install and enable/config never happen in the same run (Jellyfin loads plugins at boot only). Operator must restart the pod between Run N and Run N+1.
- **Backward-compatible:** absent install fields = old activation-only behavior unchanged.
- **No uninstall / no prune:** operator removes plugins via Jellyfin UI.
- **First use:** Intro Skipper v1.10.11.19, GUID `c83d86bb-a1e0-4c35-a113-e2101cf4ee6b`.

---

### ADR-10 — Couche d'intention : absorber vs déployer-seulement

**Phase 28 / INTENT-04 — 2026-05-31**

La v0.10.0 introduit une couche d'intention explicite au-dessus d'arrconf et de configarr, généralisant le pattern `categories[]` (1 ligne → N reconcilers) à l'ensemble de la stack.

- **Contexte / Couche :** La couche d'intention se place **au-dessus** d'arrconf ET de configarr. Flux : `intent.yml` (seul fichier hand-edited) → `arrconf generate` (fonction pure) → configs verbeuses **committées** (`arrconf.yml`, `configarr.yml`, `qbit_manage/config.yml`, `cross-seed/config.js`) → `arrconf apply` / configarr reconcilient (inchangés). Généralise le pattern `categories[]` en couche explicite et découplée.
- **Décision — frontière absorber vs déployer-seulement :** "Absorber" (générer la config) = tout outil exposant un fichier déclaratif ou une API de config propre (cross-seed, qbit_manage, arrconf existant) → sa config est **générée** par la couche d'intention depuis `intent.yml`. "Déployer-seulement" = outils config DB-only ou UI-only (autobrr, cleanuparr) → déployés comme aliases Helm uniquement, **aucune** config intention-générée.
- **Extension d'ADR-5 :** configarr reste le **seul appliqueur TRaSH**. La couche d'intention ne touche **jamais** `quality_profiles` / `custom_formats` / `quality_definitions` / `media_naming` — frontière dure ADR-5 inchangée. La couche d'intention se place au-dessus d'ADR-5 ; elle ne le contredit pas.
- **Conséquences :** G1 (générer en local + committer) préserve le diff Git et la discipline ADR-6 (review-in-PR). `generate` et `apply` restent découplés (D-06). Le drift est bloqué par la garde CI d'idempotence (`arrconf generate && git diff --exit-code`, INTENT-03). Le générateur réutilise `arrconf/generators/categories.py` — extension, pas réinvention.
- **Alternatives rejetées :** G2 (génération in-cluster — perd le diff Git et ADR-6), G3 (auto-commit — bruit Git + interaction auto-tagger), P1 (couche d'intention big-bang en une passe — réécriture brutale d'un prod qui marche, rejeté en favour de P2 incrémentale). Voir REQUIREMENTS.md Out of Scope.

---

## 12. Références

- **GSD** : https://github.com/gsd-build/get-shit-done
- **Configarr** : https://configarr.de/docs/intro/ (déjà déployé dans my-kluster)
- **Flemmarr** : https://github.com/Flemmarr/Flemmarr (inspiration)
- **TRaSH-Guides** : https://trash-guides.info/
- **bjw-s/app-template** : https://github.com/bjw-s-labs/helm-charts/tree/main/charts/other/app-template
- **Renovate customManagers** : https://docs.renovatebot.com/configuration-options/#custommanagers
- **Sonarr API** : https://sonarr.tv/docs/api/
- **Radarr API** : https://radarr.video/docs/api/
- **Prowlarr API** : https://prowlarr.com/docs/api/
- **qBittorrent Web API** : https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
- **Seerr** : `ghcr.io/seerr-team/seerr` (fork actif d'Overseerr/Jellyseerr) — API à valider Overseerr-compatible (Q1)
- **FlareSolverr** : https://github.com/FlareSolverr/FlareSolverr (proxy Cloudflare pour Prowlarr)
- **Jellyfin API** : https://api.jellyfin.org/ (OpenAPI complet)
- **yaml-language-server** : https://github.com/redhat-developer/yaml-language-server (autocomplétion YAML via JSON Schema dans VS Code / code-server)

---

## Annexe A — État actuel my-kluster (résumé)

Configuration actuelle au 2026-05-07 :

- `argocd/argocd-apps/sonarr-app.yaml` : Sonarr 4.0.17 via app-template 4.6.2, ingress oauth2-proxy, hostPath `/opt/media-stack/torrents`
- `argocd/argocd-apps/radarr-app.yaml` : Radarr 6.1.1, idem (hostPath partagé avec Sonarr et qBittorrent)
- `argocd/argocd-apps/prowlarr-app.yaml` : Prowlarr 2.3.5, ingress oauth2-proxy
- `argocd/argocd-apps/cleanuparr-app.yaml` : cleanuparr (latest tag — à pinner), oauth2-proxy
- `argocd/argocd-apps/configarr-app.yaml` : pointe sur `charts/configarr/` local
- `argocd/argocd-apps/qbittorrent-app.yaml` : qBittorrent (latest — à pinner), ingress oauth2-proxy, WEBUI_PORT 8080, hostPath `/opt/media-stack/torrents` partagé
- `argocd/argocd-apps/seerr-app.yaml` : Seerr v3.2.0 (`ghcr.io/seerr-team/seerr`), ingress oauth2-proxy, port 5055
- `argocd/argocd-apps/flaresolverr-app.yaml` : FlareSolverr (latest — à pinner), pas d'ingress (interne uniquement, port 8191)
- `argocd/argocd-apps/jellyfin-app.yaml` : Jellyfin 10.11.8 (`lscr.io/linuxserver/jellyfin`), ingress sans oauth2-proxy (auth interne Jellyfin), `proxy-body-size: 0`, PVC config 10Gi local + `media-nas-pvc` NFS partagé avec Sonarr/Radarr
- `charts/configarr/` : chart custom déployant configarr en CronJob 4h, ConfigMap depuis `files/config.yml` (TRaSH-Guides + customFormatDefinitions FR : VFF/VFI/VFQ/MULTi/VOSTFR/mHD/x265-HD), profil MULTi.VF complet HD-only, quality_definition resserré
- `secrets/configarr-secret.yaml` : Secret manuel `configarr-env` avec `SONARR_API_KEY` et `RADARR_API_KEY`
- Recyclarr désactivé (`recyclarr-app.yaml.disable`), à supprimer après validation Configarr

## Annexe B — Glossaire

- **Reconciliation** : pattern où un script lit l'état désiré (YAML) et l'état actuel (API), puis applique les diffs pour faire converger.
- **Drift** : écart entre l'état déclaré et l'état réel (ex : modification UI hors-Git).
- **Idempotent** : ré-exécuter le script donne le même résultat (pas de doublons, pas de corruption).
- **App sync (Prowlarr)** : Prowlarr push automatiquement les indexers configurés vers les apps connectées (Sonarr, Radarr).
- **TRaSH-Guides** : guide communautaire de configuration Sonarr/Radarr (custom formats, quality profiles, naming).
- **Umbrella chart** : Helm chart parent qui embarque plusieurs sous-charts via dependencies.
