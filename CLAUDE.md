# CLAUDE.md — arr-stack

> Lis ce fichier en entier avant de modifier le projet.
> Pour le **quoi** et le **pourquoi**, voir [`spec.md`](./spec.md).
> Ce fichier décrit le **comment** : conventions, workflows, pièges.

---

## Vue d'ensemble

**arr-stack** est un projet à deux composants :

1. **`arrconf`** — script Python (CronJob in-cluster) qui réconcilie la config des apps *arr et apparentées (Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, Bazarr) depuis YAML vers leurs APIs REST.
2. **`charts/arr-stack/`** — Helm umbrella chart qui empaquette toute la stack média + arrconf + configarr en un déploiement atomique versionné.

Le projet est consommé par le cluster `my-kluster` (sister repo) via une seule ArgoCD Application qui pull ce repo.

**État actuel** : Phase 4 terminée — umbrella chart déployé, 1 ArgoCD Application, 9 apps en production. Voir [`spec.md`](./spec.md) §7 pour la roadmap.

---

## Structure actuelle (post-Phase 4)

```
arr-stack/
├── spec.md                          # WHAT + WHY
├── CLAUDE.md                        # ce fichier — HOW
├── README.md                        # entrée publique GitHub
│
├── tools/arrconf/                   # ★ script Python reconciler
│   ├── pyproject.toml
│   ├── Dockerfile                   # multi-stage, USER 1000:1000
│   ├── arrconf/
│   │   ├── __main__.py              # entrypoint CLI
│   │   ├── config.py
│   │   ├── client_base.py           # ArrApiClient + _ArrV3Client mixin (ADR-8)
│   │   ├── differ.py
│   │   ├── merge.py                 # field-merge helpers (Phase 2.1 + 2.2)
│   │   ├── reconcilers/{sonarr,radarr,prowlarr}.py
│   │   └── resources/               # pydantic schémas par resource type
│   └── tests/
│
├── tools/scripts/                   # helper scripts (Phase 4)
│   ├── check-renovate-annotations.sh
│   └── byte-equivalence-diff.sh
│
├── charts/arr-stack/                # ★ umbrella Helm chart
│   ├── Chart.yaml                   # 10 app-template@5.0.0 aliases
│   ├── Chart.lock
│   ├── values.yaml                  # ★ renovate annotations + tag pins
│   ├── values.schema.json
│   ├── files/
│   │   ├── arrconf.yml              # arrconf config (mounted ConfigMap)
│   │   └── configarr.yml            # configarr config (idem)
│   └── templates/
│       ├── _helpers.tpl
│       ├── arrconf-configmap.yaml
│       └── configarr-configmap.yaml
│
├── examples/
│   └── values-prod.yaml             # = charts/arr-stack/values.yaml (D-04-VALUES-03)
│
├── schemas/
│   └── arrconf-schema.json          # généré par `arrconf schema-gen`
│
├── snapshots/                       # baselines ADR-6 + forensics
│
└── .github/workflows/
    ├── arrconf-image.yml            # build + push GHCR
    ├── chart-lint.yml               # helm lint + kubeconform + guards + auto-tag
    └── tests.yml                    # ruff + mypy + pytest
```

Note historique : la section précédente ("Structure cible") était anticipative et listait des templates custom pour les CronJobs arrconf et configarr. D-04-CRON-01 a tranché pour des aliases `bjw-s/app-template` uniformes, ce qui a éliminé ces templates custom et déplacé toute la logique CronJob dans `charts/arr-stack/values.yaml`. Seuls `arrconf-configmap.yaml` et `configarr-configmap.yaml` subsistent dans `templates/` (ConfigMaps pour les fichiers de config).

---

## Stack technique

| Composant | Technologie | Pourquoi |
|---|---|---|
| Script | Python 3.13 | Cohérent avec les choix data lab de l'auteur |
| HTTP | `httpx` | Sync + async, propre, retries faciles |
| Validation | `pydantic` v2 | Schémas YAML + réponses API |
| YAML | `ruyaml` | Round-trip, préservation commentaires |
| Logging | `structlog` ou stdlib + JSON formatter | Logs parsables côté observability |
| Tests | `pytest` + `respx` (mock httpx) | Standard Python |
| Lint/format | `ruff` | Rapide, suffisant |
| Type check | `mypy` | Strict sur signatures publiques ; CI bloque |
| Helm | Helm 3 (≥ 3.18 requis par app-template 5.0.0) + chart `bjw-s/app-template@5.0.0` en deps | Pattern déjà en place dans my-kluster (Renovate-suivi via `helmv3` manager). Phase 4 = adoption umbrella. |
| Image | `ghcr.io/tom333/arr-stack-arrconf` (public) | Cluster pull anonyme, Renovate suit |
| CI | GitHub Actions | Build image + lint + tests |
| Release | tags semver `vX.Y.Z` (manuel ou release-please — à arbitrer Phase 0/1) | |

**Versions pinnées** : toujours via `pyproject.toml` (Python) ou `Chart.yaml` deps (Helm). Renovate suit.

---

## Conventions développement — arrconf

### Code style

- **`ruff check` et `ruff format`** doivent passer avant commit. CI bloque sinon.
- **`mypy`** doit passer sur les signatures publiques (mode strict configuré dans `pyproject.toml`). CI bloque sinon.
- **Type hints partout** sur les signatures publiques. Variables locales : optionnelles.
- **Docstrings** : sur `__main__`, classes publiques (clients, reconcilers), fonctions publiques. Pas sur les helpers privés évidents.
- **Pas de commentaires-narratifs** ("# fetch the data") — les noms parlent. Commentaire utile = explique le POURQUOI non-évident.

### Idempotence (RÈGLE D'OR)

Tout reconciler doit être **sûr à ré-exécuter**. Concrètement :

- `GET` la liste actuelle, matcher par `name` (ou un identifiant stable côté API) avec le YAML désiré
- Diff explicite avant `PUT` — ne PAS systématiquement PUT (génère du bruit dans les logs *arr)
- `prune: false` par défaut, opt-in par section. Si une ressource est en cluster mais pas dans le YAML, **logger sans supprimer** sauf si l'utilisateur a activé `prune: true` pour cette section.
- Marquer les ressources gérées via le champ `tags:` standard *arr (`arrconf-managed`) pour les distinguer des ressources manuelles. Voir spec §10 Q6.

### Tests

- **Couverture cible : ≥ 70 %** sur `differ.py` et `reconcilers/`. Pas d'objectif sur les fixtures et le main.
- **Mock l'API via respx** — pas de tests qui appellent vraiment Sonarr/Radarr en CI.
- **Fixtures réalistes** : capturer les vraies réponses API (sanitisées des secrets) dans `tests/fixtures/`. Préfixer par l'app : `sonarr_download_clients_v3.json`.
- **Une test par cas** : add, update, delete, no-op, prune-skip, prune-on. Pas de méga-test.

### CLI

```
python -m arrconf apply       [--config PATH] [--apps APP1,APP2] [--dry-run] [--log-level LEVEL]
python -m arrconf dump        [--apps APP1,APP2] [--output PATH]
python -m arrconf diff        [--config PATH] [--apps APP1,APP2]
python -m arrconf schema-gen  [--output PATH]
```

- `--dry-run` : log les actions sans appeler `POST/PUT/DELETE`. Comportement par défaut en CI/test.
- `--apps` : exécuter seulement certaines apps (debug, run partiel). Default : toutes celles déclarées dans le YAML.
- Exit code 0 si succès intégral. Code 1 si une app a échoué (mais les autres ont continué). Code 2 si erreur de config (parse, validation).

### Variables d'environnement

Une convention par app, MAJUSCULE :
- `SONARR_API_KEY`, `RADARR_API_KEY`, `PROWLARR_API_KEY`
- `QBT_USER`, `QBT_PASS`
- `SEERR_API_KEY`
- `ARRCONF_LOG_LEVEL` (default `INFO`)
- `ARRCONF_DRY_RUN` (default `false`)

**Aucune** lecture de fichier de secrets — uniquement env. Le wrapping K8s (`envFrom: secretRef`) injecte tout.

### Release pin co-bump pattern

**Règle :** lorsqu'un commit modifie des fichiers sous `tools/arrconf/**` (code Python, Dockerfile, pyproject.toml), il doit **également** bumper `charts/arr-stack/values.yaml#arrconf.image.tag` dans **le même commit**. Clôture D-07-CHART-PIN-LOOP (CF-07-1, STATE.md §"Phase 7 deviations").

**Pourquoi ?** Le workflow `chart-lint.yml` utilise `mathieudutour/github-tag-action` pour créer automatiquement un tag semver sur chaque push vers `main` — AVANT que les `values.yaml` ne soient réévalués. Sans co-bump, la chaîne de release devient :

1. Push → auto-tag `vX.Y.(Z+1)` créé
2. Renovate sur my-kluster ouvre une PR `targetRevision: vX.Y.(Z+1)`
3. ArgoCD sync → le pod arrconf démarre avec l'image `vX.Y.(Z+1)` **mais** `values.yaml#arrconf.image.tag` pointe encore sur `vX.Y.Z` → arrconf pod reste sur l'ancienne version
4. Un second commit sur arr-stack doit bumper `values.yaml`, déclenchant un deuxième auto-tag et une deuxième PR Renovate sur my-kluster

Avec le co-bump, le nouveau tag d'image est déjà inscrit dans `values.yaml` au moment où l'auto-tag se crée → **un seul cycle de release** (1 PR Renovate, 1 ArgoCD sync).

**Comment :**

```yaml
# charts/arr-stack/values.yaml
arrconf:
  image:
    # renovate: image=ghcr.io/tom333/arr-stack-arrconf
    repository: ghcr.io/tom333/arr-stack-arrconf
    tag: 0.6.6   # ← bumper ici dans le même commit que le code Python
```

- **Patch bump** (e.g. `0.6.5 → 0.6.6`) : correctif ou fix idempotence (FP fix)
- **Minor bump** (e.g. `0.6.x → 0.7.0`) : nouveau reconciler ou nouvelle feature
- **Major bump** (e.g. `0.x → 1.0`) : jalon majeur ou breaking change d'API

**Historique de référence :**

| Commit | Transition | Contexte |
|--------|-----------|----------|
| `de904c9` | `0.5.0 → 0.5.3` | Phase 9-D — pilote CF-07-1 (D-07-CHART-PIN-LOOP closure) |
| Phase 10-C | `0.5.3 → 0.6.0` | qBittorrent categories wiring |
| Phase 10-D | `0.6.0 → 0.6.1` | Sonarr categories wiring |
| Phase 10-E | `0.6.1 → 0.6.2` | Radarr categories wiring |
| Phase 10-F | `0.6.2 → 0.6.3` | Seerr anime tags FP fix |
| Phase 10-G | `0.6.3 → 0.6.4` | Jellyfin categories wiring |
| Phase 10-H | `0.6.4 → 0.6.5` | Prowlarr FP fix |

**Exception :** un commit qui ne modifie que des fichiers `.md`, `values.yaml` (hors arrconf), ou des fichiers hors `tools/arrconf/**` **ne doit PAS** bumper `arrconf.image.tag`. Le tag n'évolue pas si l'image n'évolue pas.

**Critique :** ne jamais supprimer ni déplacer l'annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` au-dessus de `repository:` — Renovate en a besoin pour suivre l'image. Voir § "Annotations Renovate" dans "Conventions Helm".

---

## Conventions Helm — umbrella chart

### Annotations Renovate (CRITIQUE)

Toute image dans `values.yaml` doit avoir l'annotation `# renovate: image=...` juste au-dessus :

```yaml
sonarr:
  image:
    # renovate: image=lscr.io/linuxserver/sonarr
    repository: lscr.io/linuxserver/sonarr
    tag: 4.0.17
```

Sans ça, Renovate ne suit pas et les bumps deviennent manuels.

### Dependencies

`Chart.yaml` utilise `dependencies:` sur `bjw-s/app-template` avec un alias par service :

```yaml
dependencies:
  - name: app-template
    alias: sonarr
    version: 5.0.0
    repository: https://bjw-s-labs.github.io/helm-charts
  - name: app-template
    alias: radarr
    version: 5.0.0
    repository: https://bjw-s-labs.github.io/helm-charts
  # ... (10 aliases au total dans Chart.yaml)
```

Renovate suit la version d'app-template via le manager `helmv3`.

**Workaround Helm 4 multi-alias (OBLIGATOIRE en local et en CI)** : Helm 4 ne duplique pas automatiquement le tgz pour les N aliases du même chart. Après `helm dependency build`, il faut unpacker :

```bash
tar -xzf charts/arr-stack/charts/app-template-5.0.0.tgz -C charts/arr-stack/charts/
for alias in sonarr radarr prowlarr qbittorrent cleanuparr seerr flaresolverr jellyfin arrconf configarr; do
  [ ! -d "charts/arr-stack/charts/$alias" ] && cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/$alias"
done
```

Ce step est codifié dans `chart-lint.yml` (CI) et dans le README "Vérification locale".

### Templates custom

Pour ce qui dépasse app-template (CronJobs arrconf et configarr, ConfigMaps avec `.Files.Get`), templates custom dans `templates/`. Pattern : `<app>-<resource>.yaml`.

### values.schema.json

À écrire dès qu'on ajoute des sections complexes. Permet à `helm template` de bloquer si values invalides. Génération initiale via `helm schema-gen` (plugin) puis maintenance manuelle.

---

## Workflow de développement

### En local, sans cluster

```bash
# Python
cd tools/arrconf
uv sync                                          # ou pip install -e .
ruff check && ruff format --check
mypy .
pytest -v --cov=arrconf

# Helm
cd ../..
helm dependency update charts/arr-stack/
helm lint charts/arr-stack/
helm template charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -
```

### Test arrconf contre une vraie instance (Sonarr/Radarr de my-kluster)

```bash
export SONARR_API_KEY=<from secrets/configarr-secret.yaml>
# Tunnel via kubectl port-forward si nécessaire
kubectl -n selfhost port-forward svc/sonarr 8989:8989 &

cd tools/arrconf
arrconf apply --config ../../examples/dev-config.yml --dry-run --log-level DEBUG
```

**Toujours `--dry-run` la première fois sur une nouvelle config**.

### Workflow snapshot (CRITIQUE — à respecter avant tout test risqué)

Le projet maintient des snapshots de l'état des APIs comme assurance. Voir spec §6.5 et ADR-6.

**Snapshot raw (Bash, dispo dès Phase 0, pas de dépendance Python)** :

```bash
# Capture complète de toutes les apps → JSON brut
tools/snapshot/snapshot.sh                              # output: snapshots/baseline-$(date +%F)/
tools/snapshot/snapshot.sh --apps sonarr                # une seule app
tools/snapshot/snapshot.sh --output snapshots/before-phase-N-$(date +%F)/
```

**Dump structuré (arrconf, dispo Phase 1+)** :

```bash
arrconf dump --apps sonarr > examples/baseline-sonarr.yml      # YAML format arrconf
arrconf dump --apps sonarr,radarr,prowlarr -o examples/baseline.yml
```

**Diff** :

```bash
arrconf diff --config examples/baseline-sonarr.yml --apps sonarr        # diff lisible
diff -r snapshots/baseline-2026-05-07/ snapshots/before-phase-3-2026-05-15/   # diff raw
```

**Discipline** :
- AVANT toute Phase qui touche un nouveau scope (nouvel app ou nouveau resource type), **re-snapshot raw d'abord**
- Tous les snapshots sont committés dans Git — ne pas les ignorer dans `.gitignore`
- Au moindre doute après un test cluster : `tools/snapshot/snapshot.sh --output snapshots/forensic-$(date +%FT%H%M)/` puis `diff` avec la baseline

### CI (déclenchée auto)

- PR sur `main` → `chart-lint.yml` + `tests.yml`
- Push sur `main` modifiant `tools/arrconf/**` → `arrconf-image.yml` build + push GHCR avec tag `:sha-<short>`
- Tag `v*` → image `:vX.Y.Z` + `:latest`

### Release

**Mécanisme actuel (Phase 4+)** : auto-tag via `mathieudutour/github-tag-action` dans `chart-lint.yml`. Sur chaque push vers `main`, le job `tag` crée automatiquement un tag patch `vX.Y.Z+1` basé sur le dernier tag. Tags manuels pour les sauts minor/major.

- Renovate côté `my-kluster` détecte le nouveau tag et propose un bump de `targetRevision: vX.Y.Z`.
- Merge → ArgoCD sync automatique (< 1 h).

### Déploiement (côté my-kluster)

Côté `arr-stack` : on bump le tag de release.
Côté `my-kluster` : Renovate ouvre une PR sur `argocd/argocd-apps/arr-stack-app.yaml` pour bumper `targetRevision: vX.Y.Z`. Merge → ArgoCD sync.

**On ne déploie JAMAIS** depuis ce repo directement. Toujours via my-kluster.

---

## Frontière arrconf / configarr (lire avant tout dev)

| Resource | configarr | arrconf | Notes |
|---|---|---|---|
| Quality profiles | ✅ | ❌ | TRaSH-Guides natif côté configarr |
| Custom formats | ✅ | ❌ | Idem |
| Quality definitions | ✅ | ❌ | Idem |
| Media naming | ✅ | ❌ | TRaSH naming standardisé |
| Indexers (Prowlarr → app sync) | ❌ | ✅ | |
| Indexers (Prowlarr lui-même) | ❌ | ✅ | |
| Download clients | ❌ | ✅ | |
| Notifications | ❌ | ✅ | |
| Root folders | ❌ | ✅ | |
| Tags | ❌ | ✅ | Y compris `arrconf-managed` |
| Host config (UI port, auth) | ❌ | ✅ | |
| qBittorrent settings | ❌ | ✅ | |
| Seerr settings | ❌ | ✅ | |
| App sync Prowlarr | ❌ | ✅ | |

**Les reconcilers arrconf doivent refuser explicitement** de toucher aux endpoints quality_profiles / custom_formats / quality_definitions / media_naming. Ajouter une garde dans le code (raise `ScopeViolationError` si configuré). Décision documentée : spec §10 Q5 et ADR-5.

---

## Pattern single-instance + tags (architecture Sonarr/Radarr)

Décision spec ADR-7 : **1 seule instance Sonarr et 1 seule Radarr**, différenciation TV / Anime / Family via tags.

**Implications pour arrconf** :
- Un seul bloc `sonarr.main` et `radarr.main` dans le YAML
- `download_clients` est une **liste** où chaque entrée a un champ `tags: [tv]` / `tags: [anime]` / `tags: [family]` — ce mécanisme est natif Sonarr/Radarr (le download client ne s'utilise que pour les séries taggées correspondamment)
- `root_folders` est aussi une liste (3 root folders par instance)
- `tags` est une liste à reconcilier comme les autres ressources (créer/garder les 3, supprimer les autres si `prune: true`)

**Implications pour configarr** :
- Plusieurs `quality_profiles` dans le même bloc d'instance (MULTi.VF, Anime, Family)
- `assign_scores_to` peut cibler plusieurs profils avec scores différents (ex: VOSTFR à -10000 sur MULTi.VF mais +50 sur Anime)

**Implications pour qBittorrent** :
- 6 catégories : `sonarr-{tv,anime,family}` + `radarr-{movies,anime,family}`
- Chaque catégorie a son `save_path` dans `/data/<type>` (relatif au mount qBit)
- Le hardlink final vers `/media/<type>` est géré par Sonarr/Radarr lors de l'import

**Implications pour Seerr** : Q10 ouverte (routing par tag à valider en Phase 6).

---

## Filesystem migration: v0.2.0 flat → v0.3.0 Categories

Procédure manuelle, opérateur-driven, à exécuter UNE FOIS après le merge du PR Phase 9 (qui crée les 10 nouveaux répertoires vides `/media/<name>`). arrconf n'orchestre PAS cette migration — il crée des répertoires vides et n'y touche jamais après.

**Discipline ADR-6** : snapshot AVANT et APRÈS. Lossless, versionné dans Git.

### Mapping v0.2.0 → v0.3.0 (validé contre arrconf.yml 2026-05-18)

| v0.2.0 dir | v0.3.0 dir(s) | Action opérateur |
|------------|---------------|-------------------|
| `/media/series` | `/media/series` (default) + `mv` sélectif vers `/media/series-emilie`, `/media/series-thomas`, `/media/series-garcons` | Déplacer manuellement les sous-dossiers d'Émilie, Thomas et des garçons dans leurs buckets nommés. Le reste reste dans `/media/series`. |
| `/media/anime` | `/media/series-zoe` (l'anime de Zoé est le bulk de ce dossier) | Déplacer le contenu en wholesale. Si du non-Zoé anime existe, opérateur juge (souvent retour à `/media/series`). |
| `/media/family` | `/media/series-garcons` (bucket family-rated kids' series) | `mv` wholesale vers le bucket des garçons. |
| `/media/films` | `/media/films` (default) + `mv` sélectif vers `/media/nouveaux-films` | Le bulk reste ; opérateur déplace les "nouveaux" selon sa propre définition de date. |
| `/media/films-anime` | `/media/films-zoe` (films de Zoé) + `/media/films-animation-enfants` | Split par jugement opérateur : Studio Ghibli → Zoé ; Disney/Pixar → enfants. |
| `/media/films-family` | `/media/films-enfants` | Rename, `mv` wholesale. |

### Étape 1 — Pre-check (snapshot baseline)

```bash
# Capture l'état API actuel des 6 apps (root_folders, library paths, etc.)
tools/snapshot/snapshot.sh --output snapshots/before-categories-migration-$(date +%F)/
git add snapshots/before-categories-migration-* && git commit -m "snapshot(pre-categories-migration): baseline"

# Vérifier que les 10 nouveaux /media/<name> dirs existent (créés par le Job Phase 9 au helm upgrade) :
kubectl exec -n selfhost deployment/jellyfin -- ls /media/ | sort | column
# Attendu : films, films-animation-enfants, films-enfants, films-zoe, nouveaux-films,
#           series, series-emilie, series-garcons, series-thomas, series-zoe
#           (+ éventuellement les legacy v0.2.0 : anime, family, films-anime, films-family)
```

### Étape 2 — Execution (kubectl exec dans Jellyfin)

Le pod Jellyfin monte déjà `media-nas-pvc` à `/media` en RW — pas besoin de pod de maintenance dédié.

```bash
kubectl exec -n selfhost -it deployment/jellyfin -- bash

# Dans le pod :
cd /media
mv anime/* series-zoe/ 2>/dev/null         # bulk anime → bucket Zoé
mv family/* series-garcons/                # bulk family series → bucket garçons
mv films-family/* films-enfants/           # bulk family films → bucket enfants

# films-anime nécessite jugement opérateur :
ls films-anime/ | head -20                 # eyeball le contenu
# Exemple (Studio Ghibli → Zoé) :
mv films-anime/Studio*Ghibli films-zoe/
# Exemple (Disney/Pixar → enfants) :
mv films-anime/Disney films-anime/Pixar films-animation-enfants/

# series : split manuel (Émilie/Thomas/Garçons selon le contenu réel)
# ex: mv series/<la-série-d-émilie> series-emilie/

# films : split manuel (nouveaux selon date)
# ex: mv films/<film-récent> nouveaux-films/

exit
```

### Étape 3 — Post-check (rescan + diff snapshot)

```bash
# 1. Déclencher un rescan Sonarr (sur les root_folders qui ont gagné/perdu du contenu) :
curl -X POST -H "X-Api-Key: $SONARR_API_KEY" "http://sonarr.selfhost.svc.cluster.local:8989/api/v3/command" \
  -d '{"name":"RescanSeries"}'

# 2. Idem Radarr :
curl -X POST -H "X-Api-Key: $RADARR_API_KEY" "http://radarr.selfhost.svc.cluster.local:7878/api/v3/command" \
  -d '{"name":"RescanMovie"}'

# 3. Snapshot après migration + diff :
tools/snapshot/snapshot.sh --output snapshots/after-categories-migration-$(date +%F)/
diff -r snapshots/before-categories-migration-*/ snapshots/after-categories-migration-*/
# Attendu : changements sur paths root_folder / library PathInfos uniquement ;
#          pas de drift sur tags, download_clients, ou notifications.
```

### Étape 4 — Rollback (si nécessaire)

Le rollback est l'inverse des `mv` de l'Étape 2 — opérateur reconstitue manuellement à partir du snapshot pre-migration s'il identifie un fichier déplacé par erreur. Pas de script fourni : v0.3.0 garde le runbook high-trust, low-automation.

### Notes

- arrconf est insensible à si la migration a été exécutée ou non. Il crée les 10 `/media/<name>` (vides) ; le contenu vient soit du `mv` opérateur, soit des futurs imports Sonarr/Radarr.
- Les anciens dirs (`/media/anime`, `/media/family`, `/media/films-anime`, `/media/films-family`) restent intacts tant que l'opérateur ne les supprime pas — Phase 9 n'a aucune logique `rmdir`.
- Pour supprimer un legacy dir une fois vidé : `rm -rf /media/anime` depuis le pod Jellyfin (opérateur, manuel).

---

## Intégration avec my-kluster (post-Phase 4)

- **Une seule** ArgoCD Application (`my-kluster/argocd/argocd-apps/arr-stack-app.yaml`) pointe vers ce repo, `path: charts/arr-stack/`, `valueFile: examples/values-prod.yaml`.
- **syncOptions** : `[CreateNamespace=true, ServerSideApply=true, Replace=true]`. `Replace=true` est REQUIS car la migration cutover change `app.kubernetes.io/instance` (immutable Deployment selector) — sans Replace, ArgoCD échoue avec `field is immutable`. Voir D-04-CUTOVER-05 dans la section "Decisions" de `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-RESEARCH.md`.
- **Suppression post-Phase-4** : 10 fichiers `argocd/argocd-apps/{sonarr,radarr,prowlarr,cleanuparr,qbittorrent,seerr,flaresolverr,jellyfin,arrconf,configarr}-app.yaml` + `charts/arrconf/` + `charts/configarr/` retirés de my-kluster dans la même PR atomique (D-04-CUTOVER-01).
- **Bootstrap secrets** restent dans `my-kluster/secrets/` (`arrconf-env`, `configarr-env` — manuels, `kubectl apply`). Migration ESO globale = Phase 8 (post-MVP).
- **Renovate côté my-kluster** suit `targetRevision: vX.Y.Z` dans `arr-stack-app.yaml` via le manager standard `argocd`. Bumps minor/patch automerge.

Tout changement de scope arr-stack passe par PR sur **ce** repo. Toute modif côté `my-kluster` est limitée au bump `targetRevision` (auto par Renovate) ou à la gestion des secrets bootstrap.

---

## Comment ajouter une nouvelle app à arrconf

1. **Créer un client** dans `arrconf/reconcilers/<app>.py` héritant de `ArrApiClient`. Override `auth_headers()` si l'auth diffère (qBit utilise login-based).
2. **Définir les schémas pydantic** des resources gérées dans `arrconf/resources/<resource>.py`. Fields read-only marqués `Field(exclude=True)` pour le diff.
3. **Implémenter `reconcile()`** sur le client : appelle `differ.reconcile()` pour chaque resource type.
4. **Tests** : fixtures dans `tests/fixtures/<app>_<resource>.json`, tests unitaires `tests/test_<app>.py`.
5. **Schéma YAML** : ajouter la section dans `pydantic` config root.
6. **Doc** : ajouter une ligne dans `README.md` (apps couvertes) et dans le tableau frontière de ce CLAUDE.md.

---

## Comment ajouter un nouveau resource type pour une app existante

1. **Schéma pydantic** dans `arrconf/resources/<resource>.py`.
2. **Endpoint mapping** dans le client : URL, méthode HTTP, identifiant de matching.
3. **Implémentation `differ`** : la méthode générique devrait suffire si le pattern est `GET list / POST / PUT by id / DELETE by id`. Sinon override.
4. **Tests** : add/update/delete/no-op + prune ON/OFF.
5. **Régénérer le JSON Schema** : `arrconf schema-gen --output schemas/arrconf-schema.json` puis commit. La CI bloque si oublié.
6. **Documenter dans le tableau frontière** ci-dessus.

---

## Ce que tu NE dois PAS faire

- ❌ **Ne pas committer de secrets** dans le repo. Aucun `*.yaml` avec API keys, passwords, ou tokens. Les seuls credentials sont injectés via env au runtime.
- ❌ **Ne pas hardcoder `:latest`** dans `values.yaml` ou Dockerfile (sauf le tag dev `localhost:32000` qui n'existe PAS dans ce projet de toute façon).
- ❌ **Ne pas écrire dans les endpoints quality_profiles / custom_formats / quality_definitions / media_naming depuis arrconf**. Configarr est seul propriétaire. Voir frontière.
- ❌ **Ne pas amender un tag de release publié** (`git tag -f`). Toujours créer un nouveau tag.
- ❌ **Ne pas dupliquer la config configarr** ailleurs. La source de vérité est `charts/arr-stack/files/configarr.yml`.
- ❌ **Ne pas appeler les vraies APIs depuis les tests CI**. Toujours mock via `respx`.
- ❌ **Ne pas ajouter de dépendance Python sans pinning** dans `pyproject.toml`. `pip install` libre = drift = casse en CI.
- ❌ **Ne pas changer le scope arrconf↔configarr sans ADR explicite** dans spec.md (§11).
- ❌ **Ne pas déployer directement** depuis ce repo (helm install, kubectl apply). Toujours via my-kluster + ArgoCD.
- ❌ **Ne pas merger une PR avec drift** : si Renovate propose un bump de Sonarr de 4.0 → 5.0 (major), valider le changelog upstream avant merge même si la CI passe.
- ❌ **Ne pas supprimer l'annotation `# renovate: image=...`** dans `values.yaml`. Sans elle, Renovate ne suit plus.
- ❌ **Ne pas activer `prune: true` par défaut** dans les reconcilers. Opt-in par section uniquement.
- ❌ **Ne pas tester un nouveau reconciler en cluster sans avoir snapshot la baseline d'abord.** `tools/snapshot/snapshot.sh` est le filet de sécurité — toujours l'exécuter avant un test risqué et committer le résultat. Voir spec ADR-6.
- ❌ **Ne pas ignorer `snapshots/` dans `.gitignore`.** Les snapshots sont versionnés volontairement (lossless, pas de secret, taille négligeable).

---

## GSD intégration

Ce projet utilise [get-shit-done](https://github.com/gsd-build/get-shit-done) pour le pilotage des phases.

- **`spec.md`** est la source ingérée par `gsd-import` / `gsd-ingest-docs` au bootstrap.
- Après ingestion, `.planning/` contient les ADRs, PRDs, SPECs, et la roadmap structurée.
- Chaque phase de la roadmap suit le cycle GSD : `discuss-phase` → `plan-phase` → `execute-phase` → `verify-work`.
- **Pour les ambiguïtés** : voir `spec.md` §10 (questions ouvertes). Résoudre en discuss-phase avant de coder.
- **Pour les décisions structurantes** : nouveaux ADRs dans `.planning/` après ingestion, OU mise à jour de `spec.md` §11 si pré-ingestion.

---

## Historical bootstrap (Phase 0-3)

> Note historique : cette section décrivait l'état du repo au moment du bootstrap (mai 2026, Phase 0). Conservée pour traçabilité ; la Phase 4 a opéré le cutover vers l'umbrella documenté ci-dessus dans "Structure actuelle". Pour l'état présent, lire les premières sections de ce fichier (Vue d'ensemble + Structure actuelle + Intégration avec my-kluster).

Au moment où ce CLAUDE.md a été initialement écrit, le repo contenait uniquement :
- `spec.md` (665 lignes — toute la spec)
- `CLAUDE.md` (ce fichier)

**Aucun code, aucun chart, aucune CI**. C'était l'état initial avant Phase 0.

Pour démarrer Phase 0 (historique — déjà fait) :
1. `gsd-import spec.md` (ou `gsd-ingest-docs`) → bootstrap `.planning/`
2. `gsd-new-project` si on veut un cycle complet (PROJECT.md, ROADMAP.md, etc.)
3. Premier `gsd-spec-phase` puis `gsd-plan-phase` sur la Phase 0 du spec
4. `gsd-execute-phase` pour mettre en place arrconf squelette + GitHub Actions GHCR

---

## Références

- **spec.md** (ce repo) — source de vérité pour le quoi/pourquoi
- **my-kluster CLAUDE.md** — `/home/moi/projets/perso/my-kluster/CLAUDE.md`
- **TRaSH-Guides** — https://trash-guides.info/
- **Configarr** — https://configarr.de/docs/intro/
- **Flemmarr** (inspiration) — https://github.com/Flemmarr/Flemmarr
- **bjw-s app-template** — https://github.com/bjw-s-labs/helm-charts/tree/main/charts/other/app-template
- **Renovate customManagers** — https://docs.renovatebot.com/configuration-options/#custommanagers
