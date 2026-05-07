# Context

Running notes captured from `CLAUDE.md` (project DOC, precedence 4) and the descriptive sections of `spec.md` that don't carry decisions, requirements, or hard constraints (background, motivation, references, glossary). Open questions from `spec.md` §10 are recorded here as well — they are explicitly NOT decisions.

---

## Vue d'ensemble du projet (background)

- source: /home/moi/projets/perso/arr-stack/spec.md (§1, §2)
- topic: project-overview

**arr-stack** est un projet de plateforme média **fully-as-code** déployée sur le cluster MicroK8s personnel (`my-kluster`). Il regroupe :
1. Un script Python custom `arrconf` qui réconcilie la config des applications *arr et apparentées (Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, Bazarr, …) depuis YAML déclaratif vers leurs APIs REST.
2. Un Helm umbrella chart qui empaquette toute la stack en un déploiement atomique versionné.
3. Une CI GitHub Actions qui build l'image arrconf et la pousse sur GHCR.
4. Une config Renovate dédiée qui suit les tags d'image dans `values.yaml`.

**Objectif final** : ne plus jamais ouvrir l'UI Sonarr/Radarr/qBit/Seerr pour configurer quoi que ce soit. Tout passe par PR.

**Auteur** : Thomas Guyader (tom333). **Date d'ingestion** : 2026-05-07. **Repo cible** : `github.com/tom333/arr-stack`.

---

## État actuel du cluster my-kluster (avant migration)

- source: /home/moi/projets/perso/arr-stack/spec.md (§2.1, §9.1, Annexe A)
- topic: existing-state

- Cluster MicroK8s single-node, GitOps via ArgoCD, domaine `*.tgu.ovh`
- 9 ArgoCD Applications dans `my-kluster/argocd/argocd-apps/` : sonarr (4.0.17), radarr (6.1.1), prowlarr (2.3.5), cleanuparr (latest — à pinner), configarr (1.16.0), qbittorrent (latest — à pinner), seerr (v3.2.0 `ghcr.io/seerr-team/seerr`), flaresolverr (latest — à pinner), jellyfin (10.11.8)
- Plus chart custom `charts/configarr/` dans my-kluster (sera migré dans arr-stack en Phase 4)
- Toutes via `bjw-s/app-template 4.6.2`
- Renovate auto-merge minor/patch sur ces fichiers
- ESO + Akeyless dispo dans le cluster mais pas encore branchés sur arr-stack (secret `configarr-env` manuel)
- hostPath partagé `/opt/media-stack/torrents` (qBit + Sonarr + Radarr)
- PVC NFS partagé `media-nas-pvc` (Sonarr + Radarr + Jellyfin)
- Jellyfin sans oauth2-proxy (auth interne)
- Recyclarr désactivé (`recyclarr-app.yaml.disable`)

---

## Pourquoi un nouveau projet séparé (rationale détaillé)

- source: /home/moi/projets/perso/arr-stack/spec.md (§2.2)
- topic: project-rationale

1. arrconf est du vrai code logiciel (Python, Docker, tests, CI) — mérite un repo distinct des manifestes K8s
2. Le pattern umbrella casse Renovate dans my-kluster qui scanne `argocd/argocd-apps/*.yaml` → repo dédié permet `customManagers` ciblés
3. Stack média = produit cohérent, distinct de l'infra/data/perso
4. Versionnement atomique : un release = `Sonarr@X + Radarr@Y + arrconf@Z + configarr@W`. Rollback en `git revert`.
5. Réutilisable : pattern packageable, exportable
6. Précédent : `tom333/cv` est déjà un repo séparé pulled par ArgoCD. Pattern connu et fonctionnel.

---

## Pourquoi PAS les alternatives (étude comparative)

- source: /home/moi/projets/perso/arr-stack/spec.md (§2.3)
- topic: alternatives-rejected

- **Buildarr** — maintenance en dérive, pas de plugin pour Seerr (remplaçant de Jellyseerr), incompatible avec la trajectoire des apps choisies
- **Terraform devopsarr** — couvre Sonarr/Radarr/Prowlarr mais qBit et Seerr n'ont pas de provider mature; gestion du state lourde dans un Job K8s; GitHub Actions ne peut pas atteindre le cluster privé
- **Recyclarr** — limité au scope quality profiles + CFs (déjà couvert par configarr, son successeur direct)
- **Flemmarr (tel quel)** — inspiration valide mais on veut maîtriser le code et étendre à qBit/Seerr/Bazarr
- **Ansible** — impératif, drift detection faiblarde, écosystème *arr peu actif
- **K8s operators *arr** — quelques tentatives mais aucun mature/maintenu

---

## Open questions (NON-décisions — à traiter en discuss-phase)

- source: /home/moi/projets/perso/arr-stack/spec.md (§10)
- topic: open-questions

Les Q1-Q10 sont **explicitement non décidées** dans la spec. Elles doivent être résolues en discuss-phase avant les Phases concernées. À NE PAS confondre avec les ADRs (qui sont LOCKED).

- **Q1 — Compatibilité API Seerr vs Overseerr/Jellyseerr** : Seerr identifié (`ghcr.io/seerr-team/seerr` v3.2.0, fork actif). Reste à vérifier que l'API REST est restée Overseerr-compatible (a priori oui, à valider sur 2-3 endpoints critiques : `/api/v1/settings/services`, `/api/v1/user`, `/api/v1/request`). Bloque Phase 6.
- **Q2 — Option Helm dependencies vs sub-charts** : ADR-2 a tranché pour Option A (dependencies). Cette Q est techniquement résolue par ADR-2 mais reste mentionnée pour l'arbitrage syntaxique en Phase 4 (multi-alias du même chart est connu pour être capricieux).
- **Q3 — Schedule arrconf** : 4h (comme configarr) ou plus fréquent ? Recommandation initiale 6h. À arbitrer en Phase 2.
- **Q4 — Mode de release** : tags manuels vs release-please vs semantic-release. À arbitrer en Phase 1/2.
- **Q5 — Cohabitation arrconf/configarr sur quality_profiles** : tranchée par ADR-5 (arrconf NE TOUCHE PAS aux quality_profiles ni custom_formats). À documenter dans le code (refus côté reconciler).
- **Q6 — Backup du state arrconf** : recommandation `oui, ajouter un tag arrconf-managed sur les ressources créées par le script` (cf REQ-managed-tag). À confirmer en Phase 1/3.
- **Q7 — Compatibilité multi-versions des APIs *arr** : recommandation tester sur Sonarr v4+ uniquement (déjà la version déployée), documenter comme prérequis. Pas de gestion v3.
- **Q8 — Stratégie `prune` par défaut** : recommandation `prune: false` par défaut, opt-in par section (cf REQ-prune-opt-in).
- **Q9 — Jellyfin auth header** : à choisir selon ce qui marche en 10.11.8 (probablement `?api_key=<key>` query param suffit). À valider en Phase 7. `client_base.py` doit pouvoir overrider la stratégie d'auth par app.
- **Q10 — Routing tags Seerr → Sonarr/Radarr** : avec single instance + tags (ADR-7), Seerr doit pouvoir indiquer le tag (`tv`/`anime`/`family`) à la requête. Question : Seerr expose-t-il `defaultTags` par service connecté ou par utilisateur ? À valider en Phase 6 avec test pratique. Fallback si non supporté : tag par défaut `tv` côté Sonarr + ré-tag manuel pour anime/family minoritaires.

---

## Stack technique (synthèse runbook)

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "Stack technique"
- topic: tech-stack

| Composant | Technologie | Pourquoi |
|---|---|---|
| Script | Python 3.13 | Cohérent avec choix data lab de l'auteur |
| HTTP | httpx | Sync + async, propre, retries faciles |
| Validation | pydantic v2 | Schémas YAML + réponses API |
| YAML | ruyaml | Round-trip, préservation commentaires |
| Logging | structlog ou stdlib + JSON formatter | Logs parsables côté observability |
| Tests | pytest + respx (mock httpx) | Standard Python |
| Lint/format | ruff | Rapide, suffisant |
| Type check | mypy | Strict sur signatures publiques ; CI bloque |
| Helm | Helm 3 + chart bjw-s/app-template en deps | Pattern déjà en place dans my-kluster |
| Image | ghcr.io/tom333/arr-stack-arrconf (public) | Cluster pull anonyme, Renovate suit |
| CI | GitHub Actions | Build image + lint + tests |
| Release | tags semver vX.Y.Z (manuel ou release-please — à arbitrer Q4) | |

---

## Structure cible du repo (vue runbook)

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "Structure cible"
- topic: repo-layout

```
arr-stack/
├── spec.md
├── CLAUDE.md
├── README.md
├── tools/arrconf/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── arrconf/{__main__,config,client_base,differ}.py
│   ├── arrconf/reconcilers/{sonarr,radarr,prowlarr,qbittorrent,seerr,jellyfin}.py
│   ├── arrconf/resources/{download_client,indexer,notification,root_folder,tag,…}.py
│   └── tests/{conftest.py, fixtures/}
├── tools/snapshot/
│   ├── snapshot.sh
│   └── README.md
├── charts/arr-stack/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values.schema.json
│   ├── files/{arrconf.yml,configarr.yml}
│   └── templates/{_helpers.tpl, arrconf-{cronjob,configmap}.yaml, configarr-{cronjob,configmap}.yaml}
├── examples/values-prod.yaml
├── schemas/arrconf-schema.json
├── snapshots/baseline-YYYY-MM-DD/<app>/<resource>.json
├── .github/workflows/{arrconf-image,chart-lint,tests}.yml
└── renovate.json
```

---

## Workflow snapshot (commandes)

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "Workflow snapshot"
- topic: workflow-snapshot

```bash
# Snapshot raw (Bash, dispo Phase 0)
tools/snapshot/snapshot.sh                              # output: snapshots/baseline-$(date +%F)/
tools/snapshot/snapshot.sh --apps sonarr                # une seule app
tools/snapshot/snapshot.sh --output snapshots/before-phase-N-$(date +%F)/

# Dump structuré (arrconf, dispo Phase 1+)
arrconf dump --apps sonarr > examples/baseline-sonarr.yml
arrconf dump --apps sonarr,radarr,prowlarr -o examples/baseline.yml

# Diff
arrconf diff --config examples/baseline-sonarr.yml --apps sonarr
diff -r snapshots/baseline-2026-05-07/ snapshots/before-phase-3-2026-05-15/
```

**Discipline** : snapshot AVANT toute Phase nouvelle, commit, et au moindre doute après un test : `tools/snapshot/snapshot.sh --output snapshots/forensic-$(date +%FT%H%M)/` puis diff.

---

## Workflow développement local

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "Workflow de développement"
- topic: workflow-local

```bash
# Python
cd tools/arrconf
uv sync                                          # ou pip install -e .
ruff check && ruff format --check
pytest -v --cov=arrconf

# Helm
helm dependency update charts/arr-stack/
helm lint charts/arr-stack/
helm template charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -

# Test arrconf contre vraie instance (port-forward)
export SONARR_API_KEY=<from secrets/configarr-secret.yaml>
kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
arrconf apply --config ../../examples/dev-config.yml --dry-run --log-level DEBUG
```

**Toujours `--dry-run` la première fois sur une nouvelle config**.

---

## CI triggers et déploiement

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "CI", §6.3, §5.2
- topic: ci-deploy

- PR sur `main` → `chart-lint.yml` + `tests.yml`
- Push sur `main` modifiant `tools/arrconf/**` → `arrconf-image.yml` build + push GHCR avec tag `:sha-<short>`
- Tag `v*` → image `:vX.Y.Z` + `:latest`
- Côté arr-stack : on bump le tag de release. Côté my-kluster : Renovate ouvre une PR sur `argocd/argocd-apps/arr-stack-app.yaml` pour bumper `targetRevision: vX.Y.Z`. Merge → ArgoCD sync.
- **Ne JAMAIS déployer depuis ce repo directement**. Toujours via my-kluster.

---

## Procédure d'ajout d'une nouvelle app à arrconf

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "Comment ajouter une nouvelle app"
- topic: extension-app

1. Créer un client dans `arrconf/reconcilers/<app>.py` héritant de `ArrApiClient`. Override `auth_headers()` si l'auth diffère.
2. Définir les schémas pydantic des resources gérées dans `arrconf/resources/<resource>.py`. Fields read-only marqués `Field(exclude=True)` pour le diff.
3. Implémenter `reconcile()` sur le client : appelle `differ.reconcile()` pour chaque resource type.
4. Tests : fixtures dans `tests/fixtures/<app>_<resource>.json`, tests unitaires `tests/test_<app>.py`.
5. Schéma YAML : ajouter la section dans pydantic config root.
6. Doc : ajouter une ligne dans README.md (apps couvertes) et dans le tableau frontière de CLAUDE.md.

---

## Procédure d'ajout d'un nouveau resource type

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "Comment ajouter un nouveau resource type"
- topic: extension-resource

1. Schéma pydantic dans `arrconf/resources/<resource>.py`.
2. Endpoint mapping dans le client : URL, méthode HTTP, identifiant de matching.
3. Implémentation `differ` : la méthode générique devrait suffire si pattern `GET list / POST / PUT by id / DELETE by id`. Sinon override.
4. Tests : add/update/delete/no-op + prune ON/OFF.
5. Régénérer le JSON Schema : `arrconf schema-gen --output schemas/arrconf-schema.json` puis commit. CI bloque si oublié.
6. Documenter dans le tableau frontière.

---

## GSD intégration

- source: /home/moi/projets/perso/arr-stack/CLAUDE.md "GSD intégration"
- topic: gsd-workflow

- `spec.md` est la source ingérée par `gsd-import` / `gsd-ingest-docs` au bootstrap.
- Après ingestion, `.planning/` contient les ADRs, PRDs, SPECs et la roadmap structurée.
- Chaque phase de la roadmap suit le cycle GSD : `discuss-phase` → `plan-phase` → `execute-phase` → `verify-work`.
- Pour les ambiguïtés : voir `spec.md` §10 (Q1-Q10). Résoudre en discuss-phase avant de coder.
- Pour les décisions structurantes : nouveaux ADRs dans `.planning/` après ingestion, OU mise à jour de `spec.md` §11 si pré-ingestion.

---

## Glossaire

- source: /home/moi/projets/perso/arr-stack/spec.md (Annexe B)
- topic: glossary

- **Reconciliation** : pattern où un script lit l'état désiré (YAML) et l'état actuel (API), puis applique les diffs pour faire converger.
- **Drift** : écart entre l'état déclaré et l'état réel (ex : modification UI hors-Git).
- **Idempotent** : ré-exécuter le script donne le même résultat (pas de doublons, pas de corruption).
- **App sync (Prowlarr)** : Prowlarr push automatiquement les indexers configurés vers les apps connectées (Sonarr, Radarr).
- **TRaSH-Guides** : guide communautaire de configuration Sonarr/Radarr (custom formats, quality profiles, naming).
- **Umbrella chart** : Helm chart parent qui embarque plusieurs sous-charts via dependencies.

---

## Références externes

- source: /home/moi/projets/perso/arr-stack/spec.md (§12), CLAUDE.md (Références)
- topic: references

- GSD : https://github.com/gsd-build/get-shit-done
- Configarr : https://configarr.de/docs/intro/
- Flemmarr (inspiration) : https://github.com/Flemmarr/Flemmarr
- TRaSH-Guides : https://trash-guides.info/
- bjw-s/app-template : https://github.com/bjw-s-labs/helm-charts/tree/main/charts/other/app-template
- Renovate customManagers : https://docs.renovatebot.com/configuration-options/#custommanagers
- Sonarr API : https://sonarr.tv/docs/api/
- Radarr API : https://radarr.video/docs/api/
- Prowlarr API : https://prowlarr.com/docs/api/
- qBittorrent Web API : https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
- FlareSolverr : https://github.com/FlareSolverr/FlareSolverr
- Jellyfin API : https://api.jellyfin.org/
- yaml-language-server : https://github.com/redhat-developer/yaml-language-server
- my-kluster CLAUDE.md : `/home/moi/projets/perso/my-kluster/CLAUDE.md`
