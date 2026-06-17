# arr-stack

> Plateforme média fully-as-code (Sonarr / Radarr / Prowlarr / qBittorrent / Seerr / Jellyfin + arrconf + configarr + SuggestArr) déployée sur le cluster MicroK8s personnel `my-kluster`.

**Statut** : milestone **v0.7.0 — Media stack scope closure** livré 2026-05-25. Stack média **complète et fermée** à 9 apps + arrconf + configarr. Cluster prod tourne sur arr-stack tag `v0.14.0` / arrconf image `:0.14.0`. Une seule entrée `categories[]` dans `arrconf.yml` propage sur 6 reconcilers (qBit, Sonarr, Radarr, Seerr, Jellyfin, SuggestArr routing) ; Jellyfin expose 10 libs natives (une par Category) depuis v0.5.0 ; qBit POST credentials env-injection + pre-flight gate depuis v0.5.0 ; observability 4xx body logging depuis v0.6.0. Roadmap complète : voir [`.planning/ROADMAP.md`](./.planning/ROADMAP.md) et [`.planning/MILESTONES.md`](./.planning/MILESTONES.md).

> 📚 Documentation complète : site GitHub Pages (à venir). Ce README est l'entrée rapide.

## Vue d'ensemble

arr-stack est structuré autour de deux composants :

1. **`tools/arrconf/`** — script Python (CronJob in-cluster, toutes les 4 h) qui réconcilie la configuration de 6 apps depuis `arrconf.yml` vers leurs APIs REST. Idempotent, diff-before-PUT, `prune: false` par défaut, pre-flight gate sur les credentials qBit (échec rapide avec `ConfigError` si env vars manquantes), structlog avec body excerpt sur 4xx/5xx pour observability. Couverture actuelle (post-v0.7.0) : qBit (categories), Sonarr (tags/root_folders/download_clients env-injected/RPMs/series_tags + content_routing), Radarr (idem côté movies), Prowlarr (app-sync/indexers/download clients/notifications), Seerr (settings/animeTags routing), Jellyfin (**10 VirtualFolder libs**, une par Category — refactor v0.5.0 reverse de D-07-LIB-01). Pattern central : générateurs purs `categories → resources` (depuis v0.3.0, single-source post-v0.4.0 — la couche de transition `merge_with_manual` a été retirée en Phase 12).

2. **`charts/arr-stack/`** — chart Helm umbrella qui empaquette toute la stack (9 apps médias + arrconf + configarr = **11 aliases** `bjw-s/app-template@5.0.0`) en un déploiement atomique versionné, consommé par une seule ArgoCD Application côté `my-kluster`. SuggestArr (auto-content discovery via Jellyfin watch history) ajouté en v0.4.0.

La séparation de responsabilités avec **configarr** est stricte : configarr gère quality profiles / custom formats / quality definitions / media naming (TRaSH-Guides), arrconf gère tout le reste. Voir [`CLAUDE.md`](./CLAUDE.md) "Frontière arrconf / configarr".

## Local config UI

Phase 15 (v0.4.0) shipped a local web UI for editing `charts/arr-stack/files/arrconf.yml` from a browser. Homelab tool — **bound to `0.0.0.0:8765` by default (LAN-accessible)**, no auth scheme. Same trust model as the existing Sonarr/Radarr/Jellyfin UIs already exposed on your home network (everyone on the LAN is trusted; `arrconf.yml` itself contains no secrets). Phase 17 (v0.5.0) added CI coverage (`arrconf-ui-backend` triad + `arrconf-ui-frontend` quad) so backend (FastAPI) and frontend (Svelte 5) regressions are caught at PR time.

### Launch

From the repo root:

```bash
cd tools/arrconf-ui
uv sync                            # one-time: installs FastAPI + uvicorn + arrconf (editable)
uv run arrconf-ui                  # default: bind 0.0.0.0:8765, auto-opens browser
uv run arrconf-ui --port 9000      # alternate port
uv run arrconf-ui --no-browser     # headless (URLs still printed to stdout)
uv run arrconf-ui --host 127.0.0.1 # restrict to loopback only — no LAN access
```

Env-var overrides: `ARRCONF_UI_HOST=127.0.0.1 ARRCONF_UI_PORT=9000 uv run arrconf-ui`.

On startup, both URLs are printed:

```
INFO: Local config UI ready at http://localhost:8765
INFO: LAN-accessible at http://192.168.1.42:8765
INFO: Editing /path/to/arrconf.yml
```

The LAN URL is auto-detected via the host's outbound interface. Open it from another device on the same network (phone, tablet, another laptop) to edit `arrconf.yml` remotely.

The UI loads `charts/arr-stack/files/arrconf.yml`, renders a schema-driven typed form (Categories table + per-app collapsible sections for sonarr/radarr/prowlarr/qbittorrent/seerr/jellyfin), shows a semantic diff preview on Save, validates via pydantic on Save (422 errors highlighted in-form), and writes the file back via ruyaml round-trip (comments + blank lines + key ordering preserved). No git automation — Save shows a toast "Saved — run `git diff` to review, then push."

### Workflow

1. `uv run arrconf-ui` from `tools/arrconf-ui/`.
2. Edit Categories / per-app fields in the browser.
3. Click **Save config** → review the diff preview → **Confirm & Save**.
4. In the terminal: `git diff charts/arr-stack/files/arrconf.yml` to review.
5. `git add` / `git commit` / `git push` manually.

### Dev mode (frontend hot reload)

If you're modifying the frontend (`tools/arrconf-ui/web/src/`), run the FastAPI backend AND Vite dev server in parallel:

```bash
# Terminal A — backend on 127.0.0.1:8765
cd tools/arrconf-ui
uv run arrconf-ui --no-browser

# Terminal B — Vite dev server on 127.0.0.1:5173 (proxies /api/* → 8765)
cd tools/arrconf-ui/web
npm install
npm run dev
```

Open `http://localhost:5173/` for the hot-reloading dev UI.

### Building the static bundle

```bash
cd tools/arrconf-ui/web
npm install
npm run build       # produces tools/arrconf-ui/web/dist/
```

After build, `arrconf-ui` auto-serves the bundle from FastAPI's `StaticFiles` mount at `/`.

### CI coverage

Depuis Phase 17 (v0.5.0), tout PR touchant `tools/arrconf-ui/**` déclenche `tests.yml` avec 2 jobs dédiés :

| Job | Working dir | Steps |
|-----|-------------|-------|
| `arrconf-ui-backend` | `tools/arrconf-ui` | `uv sync --frozen` → `ruff format --check` → `ruff check` → `mypy .` → `pytest -q` |
| `arrconf-ui-frontend` | `tools/arrconf-ui/web` | `npm ci` → `npm run check` (svelte-check) → `npm run typecheck` (tsc --noEmit) → `npm run build` (Vite) |

Le 3ème job `test` (arrconf reconciler) est inchangé. **`chart-lint.yml` ignore intentionnellement `tools/arrconf-ui/**`** — un PR touchant seulement la UI ne déclenche PAS l'auto-tag chain, donc pas de release semver/GHCR rebuild inutile pour une feature CI-only.

### What's NOT in scope

- `configarr.yml` editor (deferred — REQ-config-ui-multi-config carry-forward to v0.7.0+).
- Auto-commit / auto-push (deferred — REQ-config-ui-git-integration carry-forward to v0.7.0+, post-v0.6.0 close).
- Packaging arrconf-ui for non-dev install (deferred — REQ-arrconf-ui-distribution v0.7.0+).
- Remote exposure / Ingress / Tailscale (single-tenant homelab; LAN-only by design).
- Auth (single-operator LAN-trusted).

## Architecture

```
┌─────────────────────────────────────────┐
│              ce repo (arr-stack)        │
│                                         │
│  charts/arr-stack/                      │
│    Chart.yaml  ← 11 app-template 5.0.0 │
│    values.yaml ← renovate annotations  │
│    files/arrconf.yml + configarr.yml   │
└────────────────┬────────────────────────┘
                 │ git pull
                 ▼
┌─────────────────────────────────────────┐
│  my-kluster / ArgoCD                    │
│                                         │
│  argocd-apps/arr-stack-app.yaml         │
│    path: charts/arr-stack/              │
│    targetRevision: vX.Y.Z              │
│    syncOptions: [ServerSideApply=true,  │
│                  Replace=true]          │
└────────────────┬────────────────────────┘
                 │ sync
                 ▼
┌─────────────────────────────────────────┐
│  cluster MicroK8s — namespace selfhost  │
│                                         │
│  9 Deployments (sonarr radarr prowlarr  │
│    qbittorrent cleanuparr seerr         │
│    flaresolverr jellyfin suggestarr)    │
│  2 CronJobs (arrconf configarr)        │
│  2 ConfigMaps + 11 ServiceAccounts     │
└─────────────────────────────────────────┘
```

**Flux Renovate** : bump image dans `values.yaml` → CI `chart-lint.yml` (lint + kubeconform + guards) → auto-merge minor/patch → auto-tag `vX.Y.Z` → Renovate côté `my-kluster` propose un bump de `targetRevision` → merge → ArgoCD sync (< 1 h end-to-end).

**Note `Replace=true`** : requis car la migration cutover change `app.kubernetes.io/instance` (selector Deployment immuable). Kubernetes rejette un patch sur ce label ; Replace supprime et recrée. Résultat : bref redémarrage de pod au cutover uniquement. Voir [`CLAUDE.md`](./CLAUDE.md) "Intégration avec my-kluster".

## Stack technique

| Composant | Technologie | Version | Rôle |
|-----------|-------------|---------|------|
| Umbrella chart | [bjw-s/app-template](https://github.com/bjw-s-labs/helm-charts) | 5.0.0 | 11 aliases (9 médias + arrconf + configarr) |
| Reconciler Python | arrconf (ce repo) | `:0.14.0` (post-v0.6.0 OBS-01) | qBit / Sonarr / Radarr / Prowlarr / Seerr / Jellyfin (6 apps) ; pre-flight gate qBit creds (v0.5.0) ; 4xx body logging (v0.6.0) |
| Local config UI | `tools/arrconf-ui/` (FastAPI + Svelte 5) | v0.4.0+ | éditeur browser de `arrconf.yml` ; LAN-trusted ; CI coverage backend triad + frontend quad |
| Content discovery | [SuggestArr](https://github.com/giuseppe99barchetta/SuggestArr) (v0.4.0) | — | auto-content discovery via Jellyfin watch history → Seerr requests, Categories-aware routing via `SEER_ANIME_PROFILE_CONFIG` |
| Quality profiles | [configarr](https://configarr.de/docs/intro/) | 1.28.x | TRaSH-Guides custom formats |
| CI | GitHub Actions | — | `chart-lint.yml` (charts + arrconf — triggers auto-tag) + `arrconf-image.yml` (GHCR build on tag push) + `tests.yml` (3 jobs : `test` arrconf, `arrconf-ui-backend`, `arrconf-ui-frontend`) |
| Image arrconf | GHCR public | `ghcr.io/tom333/arr-stack-arrconf:0.14.0` | anonymous-pullable |
| Renovate | self-hosted via my-kluster | — | suit `customManagers` regex sur `values.yaml` |
| ArgoCD | côté my-kluster | — | une seule App `arr-stack` |
| Cluster | MicroK8s | 1.33.x | namespace `selfhost` |
| Helm | Helm 4.x (≥ 3.18 requis par app-template 5.0.0) | 4.1.4 | umbrella packaging |
| Python | Python 3.13 + httpx + pydantic v2 + ruyaml + structlog | 3.13 | arrconf reconciler |
| Tests | pytest + respx (no real API calls) + structlog.testing | — | 416 tests, ≥70% coverage (95%+ on differ + reconcilers) |

## Déploiement

### Pré-requis

- Cluster `my-kluster` opérationnel avec ArgoCD installé et `selfhost-project` créé
- Secrets `arrconf-env` + `configarr-env` appliqués dans le namespace `selfhost` (cf `my-kluster/secrets/`)
- PVCs existants pour les 9 apps + `configarr-cache` (provisionnés au premier sync ArgoCD ; persistent storage `Retain` policy assure leur survie cross-cutover)

### Vérification locale du chart

```bash
# Cloner ce repo
git clone https://github.com/tom333/arr-stack.git
cd arr-stack

# Ajouter le repo Helm bjw-s-labs
helm repo add bjw-s-labs https://bjw-s-labs.github.io/helm-charts

# Télécharger les dépendances
helm dependency build charts/arr-stack/

# Workaround Helm 4 multi-alias (nécessaire car 13 aliases du même chart)
tar -xzf charts/arr-stack/charts/app-template-5.0.0.tgz -C charts/arr-stack/charts/
for alias in sonarr radarr prowlarr qbittorrent cleanuparr seerr flaresolverr jellyfin suggestarr arrconf configarr cross-seed qbit-manage arrconf-mcp arr-dashboard; do
  [ ! -d "charts/arr-stack/charts/$alias" ] && cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/$alias"
done

# Linter
helm lint charts/arr-stack/ -f examples/values-prod.yaml

# Template de vérification
helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | head -50
```

### Premier déploiement (via my-kluster)

1. Appliquer les secrets bootstrap dans le cluster :
   ```bash
   kubectl apply -f my-kluster/secrets/arrconf-secret.yaml
   kubectl apply -f my-kluster/secrets/configarr-secret.yaml
   ```
   Ces fichiers sont gitignorés dans `my-kluster` — les copier localement depuis le coffre-fort avant `kubectl apply`.

2. Merger la PR qui ajoute `argocd/argocd-apps/arr-stack-app.yaml` dans `my-kluster`. ArgoCD synchronise automatiquement.

3. **AUCUN `helm install` direct depuis ce repo** — toujours via my-kluster + ArgoCD. Voir [`CLAUDE.md`](./CLAUDE.md) "Ce que tu NE dois PAS faire".

### Mise à jour d'image (flux Renovate normal)

1. Renovate ouvre une PR sur ce repo (`values.yaml` : `tag: X.Y.Z` → `X.Y.Z+1`)
2. CI `chart-lint.yml` : helm lint + kubeconform + 5 guards + renovate-config-validator
3. Auto-merge si minor/patch (gate manuel sur majors)
4. Auto-tag patch sur push-to-main (`mathieudutour/github-tag-action`)
5. Renovate côté `my-kluster` détecte le nouveau tag, propose un bump de `targetRevision: vX.Y.Z`
6. Merge côté `my-kluster` → ArgoCD sync (< 1 h)
7. CronJob arrconf/configarr run dans le créneau suivant (max 4 h)

## Operator runbook

### Snapshot avant un test risqué (toujours en premier)

```bash
# 1. Lancer les port-forwards dans un terminal séparé (voir tools/snapshot/README.md)
# 2. Exporter les API keys dans l'env
# 3. Lancer le snapshot
./tools/snapshot/snapshot.sh
# Ou pour une seule app :
./tools/snapshot/snapshot.sh --apps sonarr
```

Output : `snapshots/baseline-YYYY-MM-DD/<app>/<resource>.json`. Tous les snapshots sont versionnés Git (lossless, pas de secret, taille négligeable). Voir [ADR-6](./spec.md#adr-6).

### Forcer un run arrconf

```bash
# Créer un job manuel depuis le CronJob (utile pour valider une nouvelle config)
kubectl -n selfhost create job --from=cronjob/arrconf arrconf-manual-$(date +%s)
kubectl -n selfhost logs -f job/arrconf-manual-<timestamp>
```

### Diagnostiquer un drift de config

```bash
# Diff via arrconf (format lisible)
arrconf diff --apps sonarr,radarr,prowlarr

# Diff raw (JSON) entre deux snapshots
./tools/snapshot/snapshot.sh --output snapshots/forensic-$(date +%FT%H%M)/
diff -r snapshots/baseline-<date>/ snapshots/forensic-<date>/
```

### Rollback umbrella → ArgoCD Apps individuelles (si regression majeure)

```bash
# Côté my-kluster : git revert la PR qui ajoutait arr-stack-app.yaml
# ArgoCD restore les Applications individuelles
# Les PVCs survivent (Retain policy + existingClaim discipline)
# Voir spec.md D-04-CUTOVER-04 pour le détail
```

## Onboarding (< 30 min)

Pour un autre dev (ou toi-dans-3-mois) qui découvre le projet :

1. **Lire ce fichier** (5 min) — aperçu architecture + flux Renovate
2. **Lire [`spec.md`](./spec.md) §§1-6** (10 min) — quoi/pourquoi, ADRs, frontières
3. **Lire [`CLAUDE.md`](./CLAUDE.md)** sections "Vue d'ensemble", "Conventions Helm", "Ce que tu NE dois PAS faire" (10 min)
4. **Cloner + lint** : étapes "Vérification locale du chart" ci-dessus (5 min)
5. Optionnel : `arrconf dump --apps sonarr` contre une instance Sonarr en port-forward (format YAML arrconf)

Total cible : 25-30 min sans toucher au cluster.

## Documentation

- 📚 **GitHub Pages** (à venir) — site complet (architecture, ADRs, runbooks, API)
- [`spec.md`](./spec.md) — quoi et pourquoi (architecture, ADRs 1-8, frontières)
- [`CLAUDE.md`](./CLAUDE.md) — comment (conventions, workflows, garde-fous, release co-bump pattern)
- [`.planning/`](./.planning/) — pilotage GSD (PROJECT.md, ROADMAP.md, REQUIREMENTS.md, phases/)
- [`tools/snapshot/README.md`](./tools/snapshot/README.md) — snapshot raw avant un test risqué (ADR-6)
- [`tools/arrconf/`](./tools/arrconf/) — code Python du reconciler (incl. `arrconf/generators/categories.py` single-source post-v0.4.0 + pre-flight gate `__main__.py` v0.5.0 + 4xx logging `client_base.py` v0.6.0)
- [`tools/arrconf-ui/`](./tools/arrconf-ui/) — local config UI (FastAPI backend + Svelte 5 frontend, v0.4.0+) avec CI coverage backend triad + frontend quad (v0.5.0+)
- [`charts/arr-stack/`](./charts/arr-stack/) — chart Helm umbrella (11 aliases app-template 5.0.0)
- [`.planning/MILESTONES.md`](./.planning/MILESTONES.md) — historique des milestones (v0.2.0 → v0.7.0) avec décisions et tech debt observée
- [`.planning/RETROSPECTIVE.md`](./.planning/RETROSPECTIVE.md) — leçons par milestone et tendances cross-milestone
- [`my-kluster`](https://github.com/tom333/my-kluster) — repo cluster (`argocd/argocd-apps/arr-stack-app.yaml` pointe ici)

## Licence

Personnel — tom333 (homelab single-tenant). Pas de licence open-source à ce stade.
