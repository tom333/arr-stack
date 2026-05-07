# arr-stack — Spec

> Cible : `gsd-import` / `gsd-ingest-docs` (https://github.com/gsd-build/get-shit-done)
> Auteur : Thomas Guyader (tom333)
> Date : 2026-05-07
> Repo cible (à créer) : `github.com/tom333/arr-stack`

---

## 1. Vue d'ensemble

**arr-stack** est un projet de plateforme média **fully-as-code** déployée sur le cluster MicroK8s personnel (`my-kluster`). Il regroupe :

1. **Un script Python custom (`arrconf`)** qui réconcilie la config des applications *arr et apparentées (Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, Bazarr, ...) depuis un fichier YAML déclaratif vers leurs APIs REST.
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
- Toutes les apps déployées via le chart `bjw-s app-template 4.6.2`, fichiers individuels dans `argocd/argocd-apps/<service>-app.yaml`
- Renovate auto-merge minor/patch sur ces fichiers
- ESO + Akeyless dispo dans le cluster mais pas encore branché sur l'arr-stack (secret `configarr-env` manuel)

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
| **Flemmarr (tel quel)** | Inspiration valide, mais on veut maîtriser le code et étendre à qBit/Seerr/Bazarr |
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

### 3.2 Non-objectifs (explicitement OUT)

- **NG1** — Migrer le reste du cluster `my-kluster` (data lab, infra, perso) vers ce repo. arr-stack reste focalisé sur la stack média.
- **NG2** — Construire un outil générique multi-tenant. arr-stack est dimensionné pour 1 cluster, 1 utilisateur (homelab).
- **NG3** — Couvrir 100 % de toutes les options de chaque API. On couvre ce que l'auteur utilise réellement.
- **NG4** — Refaire ce que configarr fait bien (quality profiles, custom formats, naming, quality definitions). arrconf et configarr ont des scopes complémentaires.
- **NG5** — Bootstrap automatique des API keys initiales. La 1ère obtention d'API key se fait toujours via UI ; arrconf prend le relais ensuite.
- **NG6** — Migration vers ESO/Akeyless dans la première itération. Les secrets restent en `secrets/` manuel comme aujourd'hui (cohérent avec `my-kluster`). À traiter dans le chantier ESO global du cluster.

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

Phase initiale :
- Sonarr, Radarr, Prowlarr (déjà déployés)
- configarr (déjà déployé, intégré dans l'umbrella)
- cleanuparr (déjà déployé)
- arrconf (nouveau)
- qBittorrent (à déployer)

Phase ultérieure (dans arr-stack également) :
- Seerr (remplaçant de Jellyseerr — site officiel à confirmer)
- Bazarr
- Lidarr / Whisparr / Readarr selon besoin

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

**Structure** :

```
tools/arrconf/
├── pyproject.toml
├── Dockerfile                     # python:3.13-slim, USER non-root
├── arrconf/
│   ├── __init__.py
│   ├── __main__.py                # entrypoint CLI (argparse: --config, --dry-run, --apps)
│   ├── config.py                  # parsing + validation pydantic du YAML
│   ├── logging.py                 # setup structlog
│   ├── client_base.py             # ArrApiClient générique (auth, retry, pagination)
│   ├── differ.py                  # logique GET → diff → POST/PUT/DELETE générique
│   ├── reconcilers/
│   │   ├── __init__.py
│   │   ├── sonarr.py
│   │   ├── radarr.py
│   │   ├── prowlarr.py
│   │   ├── qbittorrent.py
│   │   └── seerr.py
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
- `ARRCONF_LOG_LEVEL` (default INFO)
- `ARRCONF_DRY_RUN` (default false)

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
   - Steps : ruff check → ruff format --check → mypy (optionnel) → pytest avec couverture
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

---

## 7. Phases & roadmap

Approche progressive pour de-risker. Chaque phase est livrable indépendamment (peut s'arrêter sans casse).

### Phase 0 — Bootstrap repo + arrconf POC

**Livrables** :
- Repo `arr-stack` créé sur GitHub, public
- Squelette `tools/arrconf/` (Python, Dockerfile, pyproject, tests)
- Workflow GitHub Actions `arrconf-image.yml` opérationnel → image `ghcr.io/tom333/arr-stack-arrconf:sha-<short>` poussée
- Workflow `tests.yml` opérationnel
- Capacité à reconcilier UN type de ressource sur UNE app : **download clients sur Sonarr**
- README minimal
- `renovate.json` initial

**Critères de fin** :
- `pytest` vert
- Image buildée et publique
- Test manuel : exécuter localement contre sonarr.tgu.ovh, vérifier qu'il ajoute/met à jour un download client de test
- Pas encore de chart, pas encore d'umbrella, pas encore de déploiement K8s

**Estimation** : 1 journée

### Phase 1 — Validation cluster

**Livrables** :
- Mini chart `charts/arrconf-only/` (juste arrconf, pas l'umbrella) ou intégration ad-hoc dans `my-kluster`
- ArgoCD Application qui déploie arrconf en CronJob dans `selfhost`
- Secret manuel `arrconf-secret.yaml` dans `my-kluster/secrets/`
- Premier run réel en cluster réussi (download client Sonarr matérialisé via API)

**Critères de fin** :
- CronJob arrconf existe dans `selfhost`
- Job manuel `kubectl create job --from=cronjob/arrconf` → exit 0
- Sonarr UI montre le download client géré par arrconf
- Drift detection validée : modification UI → écrasée au run suivant

**Estimation** : 0.5 journée

### Phase 2 — Étendre arrconf

**Livrables** :
- Reconcilers : indexers, notifications, root folders, tags, host config
- Apps : Radarr, Prowlarr (avec app sync vers Sonarr/Radarr)
- Tests pour chaque reconciler

**Estimation** : 2 journées

### Phase 3 — Umbrella chart

**Livrables** :
- `charts/arr-stack/` umbrella avec deps app-template
- Migration des 5 apps de `my-kluster` (sonarr, radarr, prowlarr, cleanuparr, configarr) dans l'umbrella
- Suppression de `argocd/argocd-apps/sonarr-app.yaml`, `radarr-app.yaml`, `prowlarr-app.yaml`, `cleanuparr-app.yaml`, `configarr-app.yaml` dans `my-kluster`
- Création de `argocd/argocd-apps/arr-stack-app.yaml` dans `my-kluster`
- Renovate `customManagers` opérationnel et testé (un bump validé bout-en-bout)

**Critères de fin** :
- ArgoCD sync de l'umbrella OK (5 apps déployées via 1 chart)
- Renovate propose un bump d'image et le merge en auto-merge
- Aucune régression sur Sonarr/Radarr/Prowlarr/cleanuparr/configarr

**Estimation** : 1 journée

### Phase 4 — qBittorrent

**Livrables** :
- App qBittorrent dans l'umbrella (déploiement)
- Reconciler arrconf qBittorrent (catégories, save paths, settings clés)
- Connectiques download clients dans Sonarr/Radarr pointant vers qBit

**Estimation** : 1 journée

### Phase 5 — Seerr

**Livrables** :
- App Seerr dans l'umbrella
- Reconciler arrconf Seerr (services Sonarr/Radarr connectés, users, requests config)

**Note** : "Seerr" doit être identifié précisément (URL repo, état du fork) avant cette phase. Voir §10 Q1.

**Estimation** : 1 journée (si Seerr est documenté)

### Phase 6 — Migration ESO/Akeyless (optionnelle, alignée sur chantier global cluster)

**Livrables** :
- ExternalSecret pour les API keys arr-stack pulled depuis Akeyless
- Suppression du secret manuel `arrconf-secret.yaml` dans `my-kluster/secrets/`

**Note** : à coordonner avec le chantier ESO global du cluster (TODO.md de my-kluster). Pas urgent.

**Estimation** : 0.5 journée

---

## 8. Critères de succès (globaux)

- **CS1** — Aucune intervention UI pour la config Sonarr/Radarr/Prowlarr/qBittorrent/Seerr après bootstrap initial.
- **CS2** — Une PR sur `arr-stack` modifiant un champ de config se matérialise en cluster en moins de 1h (sync ArgoCD + run CronJob arrconf).
- **CS3** — Un drift en UI est détecté et corrigé au run suivant (max 4h selon schedule).
- **CS4** — Renovate propose en auto-merge les bumps d'image minor/patch sans intervention.
- **CS5** — Tous les bootstrap secrets restent maîtrisés dans `my-kluster/secrets/` jusqu'à migration ESO globale.
- **CS6** — `helm template charts/arr-stack/ -f examples/values-prod.yaml` rend des manifestes valides (kubeconform OK).
- **CS7** — `pytest` couvre ≥ 70 % du code arrconf, focus sur differ et reconcilers.
- **CS8** — README permet à un autre dev (ou toi-dans-3-mois) de comprendre et déployer en moins de 30 min.

---

## 9. Intégration avec my-kluster

### 9.1 Avant migration

État actuel — 5 ArgoCD Applications dans `my-kluster/argocd/argocd-apps/` :
- `sonarr-app.yaml`
- `radarr-app.yaml`
- `prowlarr-app.yaml`
- `cleanuparr-app.yaml`
- `configarr-app.yaml`

Plus le chart custom `charts/configarr/` dans `my-kluster`.

### 9.2 Après migration (post-Phase 3)

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
- `charts/configarr/` (déplacé dans `arr-stack/charts/arr-stack/files/configarr.yml` + templates)

Conservation dans `my-kluster` :
- `secrets/configarr-secret.yaml` (renommé `arr-stack-secret.yaml` ?) — bootstrap secret manuel jusqu'à ESO global
- Mise à jour de `CLAUDE.md` pour documenter le découplage et pointer sur le repo arr-stack

### 9.3 Compatibilité ascendante

- Pendant la migration (Phase 3), prévoir une fenêtre de transition où l'umbrella ET les apps unitaires peuvent coexister (test sur un cluster de staging idéalement, sinon validation pas-à-pas en prod).
- Recyclarr a déjà été désactivé (`recyclarr-app.yaml.disable`). Cette suppression est définitive.

---

## 10. Questions ouvertes (ambiguïtés à résoudre en discuss-phase)

- **Q1** — **Identification précise de "Seerr"** : URL du repo officiel, statut maintenance, compatibilité API avec Jellyseerr/Overseerr (héritage ?). Sans ça, impossible d'écrire le reconciler. À résoudre AVANT Phase 5.
- **Q2** — **Option Helm dependencies vs sub-charts** (cf §6.2). À arbitrer avant Phase 3.
- **Q3** — **Schedule arrconf** : 4h (comme configarr) ou plus fréquent ? Plus fréquent = drift corrigé plus vite, mais plus de charge API. Recommandation initiale : 6h.
- **Q4** — **Mode de release** : tags manuels vs release-please vs semantic-release. À arbitrer en Phase 0/1.
- **Q5** — **Cohabitation arrconf/configarr sur quality_profiles** : si arrconf veut un jour gérer aussi les profils, comment éviter la guerre ? Décision : **arrconf NE TOUCHE PAS aux quality_profiles ni custom_formats.** À documenter explicitement dans le code (refus côté reconciler).
- **Q6** — **Backup du state arrconf** : le script est idempotent et stateless, mais les ressources créées (notifications, indexers) ont des IDs internes. Faut-il un mécanisme de marquage (tag arrconf-managed) pour distinguer ce qui est piloté de ce qui est manuel ? Recommandation : **oui, ajouter un tag `arrconf-managed` sur les ressources créées par le script** (champ `tags:` standard *arr).
- **Q7** — **Compatibilité multi-versions des APIs *arr** : Sonarr v4 vs v3 ont des breaking changes. Le script doit-il versionner ses appels ? Recommandation : tester sur Sonarr v4+ uniquement (déjà la version déployée), documenter comme prérequis.
- **Q8** — **Stratégie `prune` par défaut** : si une ressource est en cluster mais pas dans le YAML, on supprime ou on log et on garde ? Recommandation : `prune: false` par défaut, opt-in par section.

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
- Multiples alias du même chart — syntax à valider en Phase 3
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
- **Seerr** : à clarifier (Q1)

---

## Annexe A — État actuel my-kluster (résumé)

Configuration actuelle au 2026-05-07 :

- `argocd/argocd-apps/sonarr-app.yaml` : Sonarr 4.0.17 via app-template 4.6.2, ingress oauth2-proxy
- `argocd/argocd-apps/radarr-app.yaml` : Radarr 6.1.1, idem
- `argocd/argocd-apps/prowlarr-app.yaml` : Prowlarr 2.3.5, idem
- `argocd/argocd-apps/cleanuparr-app.yaml` : cleanuparr (latest tag — à pinner), oauth2-proxy
- `argocd/argocd-apps/configarr-app.yaml` : pointe sur `charts/configarr/` local
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
