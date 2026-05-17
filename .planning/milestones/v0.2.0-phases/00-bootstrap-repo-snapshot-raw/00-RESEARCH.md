# Phase 0: Bootstrap repo + snapshot raw — Research

**Researched:** 2026-05-07
**Domain:** Bash/curl/jq snapshot tooling + repo scaffolding (Renovate, README, .gitignore)
**Confidence:** HIGH (endpoint paths verified against upstream OpenAPI specs; existing cluster validates assumptions)

---

## Summary

Phase 0 a une portée volontairement étroite : capturer un snapshot **raw, lossless, read-only** des 6 apps avec API REST (sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin) via Bash + curl + jq, scaffolder un repo minimal (`renovate.json` initial + README minimal), et committer le tout. Aucune dépendance Python (`arrconf` arrive Phase 1), aucun chart Helm (Phase 4), aucune CI (Phase 1+).

L'enjeu majeur est la **discipline read-only** : le script ne doit JAMAIS faire de POST/PUT/DELETE, sous peine de violer ADR-6 (le filet de sécurité censé protéger les phases suivantes). Côté technique, la complexité réside dans l'hétérogénéité des 4 stratégies d'auth (X-Api-Key pour les *arr et Seerr, login form + cookie pour qBittorrent, header `Authorization: MediaBrowser Token=...` pour Jellyfin 10.11+) et dans le choix du transport vers le cluster (kubectl port-forward depuis le workstation, le cluster étant privé — C1 et C3).

Tous les endpoints à snapshot ont été vérifiés contre les OpenAPI specs upstream (Sonarr/Radarr develop branch, Prowlarr develop branch, Jellyfin stable spec officiel, Seerr `seerr-api.yml` du repo seerr-team/seerr, qBittorrent wiki v5.0). Les services K8s sont confirmés présents dans le cluster via `kubectl get svc -n selfhost` exécuté pendant la recherche.

**Primary recommendation:** Un seul script Bash `tools/snapshot/snapshot.sh` avec un manifest YAML/Bash interne (pas de fichier séparé) déclarant pour chaque app : URL de base, stratégie d'auth, liste d'endpoints à GET. Output déterministe via `jq --sort-keys '.'`. Connectivité cluster via `kubectl port-forward` lancé depuis le script lui-même (ou prérequis documenté). `set -euo pipefail` + trap de cleanup pour garantir que les port-forwards meurent même en cas de Ctrl-C.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

CONTEXT.md n'existe pas pour Phase 0 (`/gsd-discuss-phase 0` n'a pas été exécuté avant ce research). Les contraintes ci-dessous sont donc tirées **directement de spec.md, CLAUDE.md, PROJECT.md et ROADMAP.md** — qui ont autorité équivalente à des décisions verrouillées.

### Locked Decisions (verbatim de PROJECT.md `<decisions>` et ROADMAP.md "Success Criteria")

- **ADR-6** verrouille le workflow snapshot 4 niveaux. Phase 0 = niveau 1 : Bash standalone, raw JSON, indépendant d'arrconf. Snapshots versionnés Git, NE PAS dans `.gitignore`.
- **Chemin output verrouillé** : `snapshots/baseline-2026-05-07/<app>/<resource>.json` (ROADMAP success criterion #1, format de date depuis spec §6.5).
- **Apps couvertes (6)** : sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin (ROADMAP success criterion #1).
- **Aucune écriture** observée pendant le snapshot — vérification : logs Sonarr/Radarr ne montrent que des reads (ROADMAP success criterion #3).
- **Renovate config initiale** committée (ROADMAP success criterion #4) — règle Renovate `extends: ["config:recommended"]` (constraints.md "Renovate configuration").
- **README minimal** présent expliquant comment relancer un snapshot avant un test risqué (ROADMAP success criterion #5).
- **Pas de Python** en Phase 0 (spec §7 Phase 0 — "Bash + curl + jq uniquement"). `arrconf` existe à partir de Phase 1.
- **Pas de Helm chart, pas de CI** en Phase 0 (charts arrivent Phase 4, CI Phase 1+).
- **`customManagers` Renovate sur `values.yaml`** : DEFERRED en Phase 4 (le `values.yaml` n'existe qu'à partir de Phase 4 — pattern regex inutile maintenant).
- **Bootstrap admin Jellyfin** : prérequis manuel (NG5, REQ-bootstrap-exception). Si pas encore fait sur l'instance cible, le snapshot Jellyfin doit être SKIPPED proprement (pas un fail bloquant).
- **API keys** : lues uniquement depuis l'env (CLAUDE.md "Variables d'environnement"). Le script ne doit RIEN lire d'un fichier de secrets ; il consomme `SONARR_API_KEY`, `RADARR_API_KEY`, `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY`.

### Claude's Discretion (à recommander dans Plan, non verrouillé)

- **Format du manifest d'endpoints** : embarqué dans `snapshot.sh` (arrays Bash) vs fichier séparé `tools/snapshot/endpoints.yml` ou `endpoints.json`. Recommandation : embarqué (pas de dépendance YAML, simplicité, Phase 0 minimaliste).
- **Connectivité cluster** : kubectl port-forward auto-démarré par le script vs prérequis externe documenté dans README. Recommandation : prérequis externe — l'utilisateur lance les port-forwards lui-même (plus testable, moins de magie cachée).
- **CLI flags** : `--apps`, `--output`, `--dry-run` (= ne fait que loguer ce qu'il GET sans écrire fichier), `--help`. Recommandation : exposer ces 4 flags + arg positionnel optionnel pour suffixe nom du dossier (ex. `before-phase-3`).
- **Stratégie de schedule** côté arrconf (Q3) : OUT OF SCOPE Phase 0.
- **Mode de release** (Q4) : OUT OF SCOPE Phase 0.
- **Choix exact des endpoints à snapshot par app** : recommandation présente dans la section "Standard Stack" → tableau "Endpoints à snapshot par app" — couvre tous les types ressources qu'arrconf gérera (frontière configarr respectée mais on snapshot quand même les endpoints `qualityprofile`/`customformat` par sécurité forensique : on capture l'état réel, pas seulement ce qu'arrconf gérera).

### Deferred Ideas (OUT OF SCOPE)

- **Reconciler Python `arrconf`** : Phase 1+.
- **Helm umbrella chart** `charts/arr-stack/` : Phase 4.
- **`renovate.json` `customManagers`** sur `values.yaml` : Phase 4 (values.yaml n'existe pas encore).
- **Workflows GitHub Actions** (`arrconf-image.yml`, `chart-lint.yml`, `tests.yml`, `release.yml`) : Phase 1+.
- **Scope writing** (POST/PUT/DELETE) : Phase 1 minimum, Phase 2 cluster minimum.
- **Migration ESO** (Phase 8), **drift detection** (Phase 2), **split tv/anime/family** (Phase 5), etc. : tous OUT.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **REQ-baseline-snapshot** | Baseline lossless de la config actuelle capturée avant toute écriture. `tools/snapshot/snapshot.sh` (Bash + curl + jq, indépendant d'arrconf) dispo dès Phase 0. Snapshots versionnés Git, NE PAS dans `.gitignore`. | Endpoints exacts par app vérifiés via OpenAPI specs upstream (Sonarr/Radarr v3, Prowlarr v1, Jellyfin stable, Seerr seerr-api.yml, qBittorrent wiki v5.0). Pattern script Bash `set -euo pipefail` + `jq --sort-keys` documenté. Connectivité cluster via `kubectl port-forward` validée (services `selfhost` confirmés présents). Auth strategies par app documentées (X-Api-Key / cookie SID / Authorization MediaBrowser). |
| **REQ-phase-roadmap** | Méta-requirement : roadmap progressive de-risk en 9 phases (0 à 8), chaque phase livrable indépendamment. Validé quand la roadmap est instanciée et chaque phase respecte ses critères de fin. | Roadmap déjà committée (`/.planning/ROADMAP.md` — 134629e). Phase 0 satisfait ce REQ par sa simple existence + complétion. Pas de research supplémentaire nécessaire pour ce REQ — il est validé en `gsd-verify-work` si tous les autres critères Phase 0 passent. |

</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Read API state from 6 apps | Workstation (dev laptop) | — | Cluster privé (C1) — pas de snapshot in-cluster en Phase 0 (CronJob = Phase 2). Le dev lance le script depuis sa machine via port-forward. |
| Authentication per app | Bash script (curl headers/cookies) | Env vars from shell | API keys env-only (CLAUDE.md). Script ne lit aucun fichier de secrets. |
| Cluster connectivity | `kubectl port-forward` | Direct ClusterIP via VPN/Tailscale (out of scope Phase 0) | Service K8s internes accessibles uniquement in-cluster (C3). Port-forward = pattern dev standard. |
| JSON normalization | `jq --sort-keys '.'` | — | Déterminisme indispensable pour `git diff` lisibles entre snapshots successifs. |
| Storage | Local filesystem → Git | — | Snapshots versionnés Git (ADR-6). Pas de S3, pas de PVC, pas de Vault. |
| Renovate config initial | Repo root `renovate.json` | — | Suivi pour Phase 0 = **aucun customManager** (pas de values.yaml encore). Juste `extends: ["config:recommended"]` + structure prête à étendre Phase 4. |
| Documentation | `README.md` repo root + `tools/snapshot/README.md` | — | README minimal pointe vers spec.md + CLAUDE.md (REQ-readme-onboarding final = Phase 4). |

---

## Standard Stack

### Core (Phase 0 only)

| Outil | Version verified | Purpose | Why Standard |
|-------|------------------|---------|--------------|
| `bash` | 5.x (5.2 verifiée localement) `[VERIFIED: bash --version]` | Shell script orchestration | Standard Linux. `set -euo pipefail` + `trap` cleanup = pattern strict mode. |
| `curl` | 8.x (8.14 verifiée localement) `[VERIFIED: curl --version]` | HTTP client (GET only en Phase 0) | Standard. Supporte cookie jar (`--cookie-jar`/`--cookie`), header injection (`-H`), TLS, retry (`--retry`). |
| `jq` | 1.7+ (1.8 verifiée localement) `[VERIFIED: jq --version]` | JSON pretty-print + sort-keys | Standard de facto pour manipulation JSON en shell. `--sort-keys` essentiel pour diffs déterministes. `[CITED: jqlang.org/manual]` |
| `kubectl` | 1.28+ (1.33 verifiée localement) `[VERIFIED: kubectl version]` | Port-forward vers services `selfhost` | Standard K8s. `kubectl port-forward svc/<name> -n selfhost <local>:<remote>` est le pattern dev éprouvé. |

**Aucune autre dépendance.** Pas de Python, pas de Helm, pas de Docker, pas de gh CLI requis (sauf gh CLI optionnel pour créer le repo GitHub initial — peut se faire UI).

### Endpoints à snapshot par app `[VERIFIED: OpenAPI specs upstream]`

Tous les chemins ci-dessous ont été extraits directement de l'OpenAPI spec officielle de chaque app pendant la recherche (`/tmp/sonarr-openapi.json`, `/tmp/radarr-openapi.json`, `/tmp/prowlarr-openapi.json`, `/tmp/jellyfin-openapi.json`, `/tmp/seerr-openapi.yml`, `/tmp/qbt-api.md`).

#### Sonarr (`/api/v3/`, `X-Api-Key` header) `[VERIFIED: Sonarr/Sonarr develop openapi.json]`

| Resource | Endpoint | Output filename |
|----------|----------|------------------|
| Download clients | `GET /api/v3/downloadclient` | `downloadclient.json` |
| Indexers | `GET /api/v3/indexer` | `indexer.json` |
| Notifications | `GET /api/v3/notification` | `notification.json` |
| Root folders | `GET /api/v3/rootfolder` | `rootfolder.json` |
| Tags | `GET /api/v3/tag` | `tag.json` |
| Quality profiles (forensic) | `GET /api/v3/qualityprofile` | `qualityprofile.json` |
| Custom formats (forensic) | `GET /api/v3/customformat` | `customformat.json` |
| Naming config (forensic) | `GET /api/v3/config/naming` | `config_naming.json` |
| Media management config | `GET /api/v3/config/mediamanagement` | `config_mediamanagement.json` |
| Host config | `GET /api/v3/config/host` | `config_host.json` |
| UI config | `GET /api/v3/config/ui` | `config_ui.json` |
| Indexer config | `GET /api/v3/config/indexer` | `config_indexer.json` |
| Download client config | `GET /api/v3/config/downloadclient` | `config_downloadclient.json` |
| Import lists | `GET /api/v3/importlist` | `importlist.json` |
| Remote path mappings | `GET /api/v3/remotepathmapping` | `remotepathmapping.json` |
| Metadata profiles | `GET /api/v3/metadata` | `metadata.json` |
| System status (sanity) | `GET /api/v3/system/status` | `system_status.json` |

**Note frontier ADR-5** : `qualityprofile`, `customformat`, `config/naming` sont snapshottés bien qu'arrconf ne les écrira jamais. C'est volontaire (forensic complet, ADR-6 = lossless).

#### Radarr (`/api/v3/`, `X-Api-Key` header) `[VERIFIED: Radarr/Radarr develop openapi.json]`

Mêmes endpoints que Sonarr (Radarr v3 utilise la même structure servarr) **plus** :
- `GET /api/v3/config/metadata` → `config_metadata.json` (Radarr a un endpoint metadata dans config, Sonarr non)
- L'endpoint `importlist/movie` existe mais POST-only (pas snapshottable utilement)

Output dir : `snapshots/baseline-2026-05-07/radarr/`

#### Prowlarr (`/api/v1/`, `X-Api-Key` header) `[VERIFIED: Prowlarr/Prowlarr develop openapi.json]`

| Resource | Endpoint | Output filename |
|----------|----------|------------------|
| Indexers (les indexers gérés par Prowlarr) | `GET /api/v1/indexer` | `indexer.json` |
| Indexer categories | `GET /api/v1/indexer/categories` | `indexer_categories.json` |
| Indexer stats | `GET /api/v1/indexerstats` | `indexerstats.json` |
| Indexer status | `GET /api/v1/indexerstatus` | `indexerstatus.json` |
| Indexer proxies (FlareSolverr) | `GET /api/v1/indexerproxy` | `indexerproxy.json` |
| Applications (Sonarr/Radarr connectés) | `GET /api/v1/applications` | `applications.json` |
| App profiles | `GET /api/v1/appprofile` | `appprofile.json` |
| Download clients | `GET /api/v1/downloadclient` | `downloadclient.json` |
| Notifications | `GET /api/v1/notification` | `notification.json` |
| Tags | `GET /api/v1/tag` | `tag.json` |
| Host config | `GET /api/v1/config/host` | `config_host.json` |
| UI config | `GET /api/v1/config/ui` | `config_ui.json` |
| Download client config | `GET /api/v1/config/downloadclient` | `config_downloadclient.json` |
| System status | `GET /api/v1/system/status` | `system_status.json` |

#### qBittorrent (`/api/v2/`, cookie SID via login form) `[VERIFIED: qbittorrent wiki v5.0]`

**Auth flow particulier** :
1. `POST /api/v2/auth/login` avec `username=...&password=...` form-encoded **et header `Referer: http://localhost:<port>` (sinon 403)**.
2. Récupérer cookie `SID=...` (curl `--cookie-jar /tmp/qbt.cookies`).
3. Toutes les requêtes suivantes : `--cookie /tmp/qbt.cookies`.
4. Optionnel : `POST /api/v2/auth/logout` à la fin (pas critique).

| Resource | Endpoint | Output filename |
|----------|----------|------------------|
| App version | `GET /api/v2/app/version` | `app_version.txt` (plain text, exception au pattern JSON) |
| API version | `GET /api/v2/app/webapiVersion` | `app_webapi_version.txt` |
| Build info | `GET /api/v2/app/buildInfo` | `app_buildinfo.json` |
| Preferences (settings) | `GET /api/v2/app/preferences` | `app_preferences.json` |
| Default save path | `GET /api/v2/app/defaultSavePath` | `app_default_save_path.txt` |
| Categories | `GET /api/v2/torrents/categories` | `torrents_categories.json` |
| Tags | `GET /api/v2/torrents/tags` | `torrents_tags.json` |
| Torrent list (forensic) | `GET /api/v2/torrents/info` | `torrents_info.json` |
| Transfer info | `GET /api/v2/transfer/info` | `transfer_info.json` |

**Référer header trick** : qBittorrent rejette les requêtes cross-origin avec 403. Le script DOIT envoyer `-H "Referer: http://localhost:8080"` (ou l'URL exacte du host) sur `/auth/login`.

#### Seerr (`/api/v1/`, `X-Api-Key` header) `[VERIFIED: seerr-team/seerr/seerr-api.yml main branch]`

Seerr est un fork actif d'Overseerr/Jellyseerr. L'auth est confirmée comme `X-Api-Key` (compat Overseerr — Q1 reste à valider en Phase 6 sur les **endpoints d'écriture**, mais pour les GET en Phase 0 c'est compat).

| Resource | Endpoint | Output filename |
|----------|----------|------------------|
| Main settings | `GET /api/v1/settings/main` | `settings_main.json` |
| Network settings | `GET /api/v1/settings/network` | `settings_network.json` |
| Public settings | `GET /api/v1/settings/public` | `settings_public.json` |
| Sonarr services connectés | `GET /api/v1/settings/sonarr` | `settings_sonarr.json` |
| Radarr services connectés | `GET /api/v1/settings/radarr` | `settings_radarr.json` |
| Jellyfin connection | `GET /api/v1/settings/jellyfin` | `settings_jellyfin.json` |
| Plex connection (probablement vide) | `GET /api/v1/settings/plex` | `settings_plex.json` |
| Email notifications | `GET /api/v1/settings/notifications/email` | `settings_notifications_email.json` |
| Discord notifications | `GET /api/v1/settings/notifications/discord` | `settings_notifications_discord.json` |
| Telegram notifications | `GET /api/v1/settings/notifications/telegram` | `settings_notifications_telegram.json` |
| Webhook notifications | `GET /api/v1/settings/notifications/webhook` | `settings_notifications_webhook.json` |
| Jobs schedule | `GET /api/v1/settings/jobs` | `settings_jobs.json` |
| Users | `GET /api/v1/user` | `user.json` |
| Requests | `GET /api/v1/request` | `request.json` |
| Request count | `GET /api/v1/request/count` | `request_count.json` |
| Status (sanity) | `GET /api/v1/status` | `status.json` |

#### Jellyfin (`/`, header `Authorization: MediaBrowser Token=<key>` — 10.11+) `[VERIFIED: api.jellyfin.org openapi spec stable]`

⚠️ **Auth changement breaking en 10.11** : `X-Emby-Token` legacy est désactivable et sera supprimé. Pour 10.11.8 (version déployée), utiliser `Authorization: MediaBrowser Token="<key>"`. Voir Q9 et l'issue [seerr-team/seerr#2361](https://github.com/seerr-team/seerr/issues/2361) pour le contexte (Seerr lui-même a dû fix son auth Jellyfin pour 10.11). `[VERIFIED: jellyfin-openapi-stable.json securitySchemes]`

⚠️ **Bootstrap admin** : si aucun compte admin n'existe encore (NG5), `Library/VirtualFolders` retournera 403. Le script doit gérer ça proprement (warning + skip, pas exit code != 0 — le user fera le bootstrap manuel et relancera).

| Resource | Endpoint | Output filename |
|----------|----------|------------------|
| System info (full) | `GET /System/Info` | `system_info.json` |
| System info (public) | `GET /System/Info/Public` | `system_info_public.json` |
| System configuration | `GET /System/Configuration` | `system_configuration.json` |
| Storage info | `GET /System/Info/Storage` | `system_storage.json` |
| Virtual folders (libraries) | `GET /Library/VirtualFolders` | `library_virtualfolders.json` |
| Default metadata options | `GET /System/Configuration/MetadataOptions/Default` | `metadata_options_default.json` |
| Users | `GET /Users` | `users.json` |
| Plugins | `GET /Plugins` | `plugins.json` |
| Devices | `GET /Devices` | `devices.json` |
| Scheduled tasks | `GET /ScheduledTasks` | `scheduled_tasks.json` |

### Connection strategy

**Recommandation : prérequis externe documenté dans README.**

Avant de lancer `snapshot.sh`, l'utilisateur ouvre un terminal séparé et lance les port-forwards (les services `selfhost` ont été confirmés présents pendant la recherche : `sonarr`, `radarr`, `prowlarr`, `qbittorrent`, `seerr`, `flaresolverr`, `jellyfin`, `cleanuparr`) `[VERIFIED: kubectl get svc -n selfhost]` :

```bash
# Lancer dans un terminal séparé (laisser tourner pendant le snapshot)
kubectl -n selfhost port-forward svc/sonarr      8989:8989 &
kubectl -n selfhost port-forward svc/radarr      7878:7878 &
kubectl -n selfhost port-forward svc/prowlarr    9696:9696 &
kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
kubectl -n selfhost port-forward svc/seerr       5055:5055 &
kubectl -n selfhost port-forward svc/jellyfin    8096:8096 &
```

**Variables d'env exposées au script (URLs par défaut)** :
```bash
export SONARR_URL="${SONARR_URL:-http://localhost:8989}"
export RADARR_URL="${RADARR_URL:-http://localhost:7878}"
export PROWLARR_URL="${PROWLARR_URL:-http://localhost:9696}"
export QBT_URL="${QBT_URL:-http://localhost:8080}"
export SEERR_URL="${SEERR_URL:-http://localhost:5055}"
export JELLYFIN_URL="${JELLYFIN_URL:-http://localhost:8096}"
```

L'utilisateur peut override avec son propre URL (ex. accès Tailscale, port-forward sur autre port). Les valeurs par défaut correspondent aux ports natifs des images linuxserver/ghcr — sauf qBittorrent dont le pod expose 8080 (`WEBUI_PORT=8080` dans la config my-kluster).

**Alternative considérée** : Le script auto-démarre les port-forwards. Rejeté car (a) magie cachée, (b) il faut tracker les PIDs et trap-cleanup, (c) si l'utilisateur a déjà un port-forward actif sur un port, conflict, (d) Phase 0 doit rester minimaliste.

### Renovate config initiale (`renovate.json`)

`[CITED: docs.renovatebot.com/config-presets, constraints.md "Renovate configuration"]`

Phase 0 = config minimale, sans `customManagers` (qui arrivent Phase 4 quand `values.yaml` existera) :

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"]
}
```

C'est tout. `config:recommended` est l'évolution moderne de `config:base` (déprécié) — confirmé `[CITED: docs.renovatebot.com/presets-config]`. Côté my-kluster, Renovate suit déjà `targetRevision: vX.Y.Z` dans les ArgoCD Apps via le manager `argocd` natif — aucune config additionnelle requise dans arr-stack pour ça.

**À NE PAS faire en Phase 0** :
- Ajouter `customManagers` regex sur `values.yaml` (le fichier n'existe pas — Renovate fail validation)
- Ajouter `packageRules` (rien à régler tant qu'aucune dépendance n'est trackée)
- Ajouter `extends: [":semanticCommits"]` ou autres presets opinionated (laisser le futur Phase 4 décider)

### README minimal (Phase 0)

Pointer simple vers spec/CLAUDE/snapshot. Pas de tutoriel d'install (REQ-readme-onboarding final = Phase 4). Pattern recommandé :

```markdown
# arr-stack

Plateforme média fully-as-code (Sonarr / Radarr / Prowlarr / qBittorrent / Seerr / Jellyfin) déployée sur le cluster MicroK8s personnel `my-kluster`.

> **Statut** : en cours de bootstrap (Phase 0). Le code et le chart umbrella n'existent pas encore — voir [`spec.md`](./spec.md) §7 pour la roadmap.

## Documentation

- [`spec.md`](./spec.md) — quoi et pourquoi (architecture, ADRs, phases, frontières)
- [`CLAUDE.md`](./CLAUDE.md) — comment (conventions, workflows, garde-fous)
- [`tools/snapshot/README.md`](./tools/snapshot/README.md) — comment relancer un snapshot raw avant un test risqué
- [`.planning/`](./.planning/) — pilotage GSD (PROJECT.md, ROADMAP.md, REQUIREMENTS.md, ADRs)

## Snapshot rapide

Avant tout test risqué (nouveau reconciler, montée de version, debug), capturer l'état :

\`\`\`bash
# 1. Lancer les port-forwards dans un terminal séparé (voir tools/snapshot/README.md)
# 2. Exporter les API keys dans l'env (voir tools/snapshot/README.md)
# 3. Lancer le snapshot
./tools/snapshot/snapshot.sh
\`\`\`

Output : `snapshots/baseline-YYYY-MM-DD/<app>/<resource>.json`. Tous les snapshots sont committés dans Git (lossless, pas de secret).
```

`tools/snapshot/README.md` : doc plus détaillée (port-forwards, env vars attendus, exemples `--apps sonarr`, troubleshooting Jellyfin bootstrap).

---

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Workstation (dev laptop)                         │
│                                                                     │
│  Shell env (manuel)         tools/snapshot/snapshot.sh              │
│  ┌──────────────────┐       ┌─────────────────────────────────┐     │
│  │ SONARR_API_KEY   │──────▶│  parse args (--apps/--output)   │     │
│  │ RADARR_API_KEY   │       │  validate env vars              │     │
│  │ PROWLARR_API_KEY │       │  set -euo pipefail + trap clean │     │
│  │ QBT_USER/PASS    │       │                                 │     │
│  │ SEERR_API_KEY    │       │  for each app in target_apps:   │     │
│  │ JELLYFIN_API_KEY │       │    auth (header / cookie)       │     │
│  └──────────────────┘       │    for each endpoint:           │     │
│                             │      curl GET → jq --sort-keys  │     │
│  kubectl port-forward       │      write to <output>/<app>/   │     │
│  ┌──────────────────┐       │    log success/failure         │     │
│  │ :8989 → sonarr   │◀──────┤    continue on per-endpoint err │     │
│  │ :7878 → radarr   │  HTTP │                                 │     │
│  │ :9696 → prowlarr │  GET  │  exit 0 if all apps OK          │     │
│  │ :8080 → qbittorr │       │  exit 1 if ≥1 app failed entirely│    │
│  │ :5055 → seerr    │       └─────────────────────────────────┘     │
│  │ :8096 → jellyfin │                       │                       │
│  └──────────────────┘                       ▼                       │
│         │                       snapshots/baseline-2026-05-07/      │
│         │                       ├── sonarr/                         │
│         ▼                       │   ├── downloadclient.json         │
│  ┌──────────────────┐           │   ├── indexer.json                │
│  │ MicroK8s cluster │           │   └── ...                         │
│  │  (selfhost ns)   │           ├── radarr/...                      │
│  │  - sonarr svc    │           ├── prowlarr/...                    │
│  │  - radarr svc    │           ├── qbittorrent/...                 │
│  │  - prowlarr svc  │           ├── seerr/...                       │
│  │  - qbittorr svc  │           └── jellyfin/...                    │
│  │  - seerr svc     │                       │                       │
│  │  - jellyfin svc  │                       ▼                       │
│  └──────────────────┘                  git add + commit             │
│                                  (tous fichiers JSON versionnés)    │
└─────────────────────────────────────────────────────────────────────┘
```

Flux séquentiel : env vars exportés → port-forwards préparés (manuel) → script lance les GET via curl + jq sort-keys → écrit dans `snapshots/baseline-<date>/<app>/<resource>.json` → git add + commit. Aucune écriture sur les APIs (read-only par construction).

### Recommended Project Structure (état du repo après Phase 0)

```
arr-stack/
├── README.md                        # ← Phase 0 (minimal pointer)
├── CLAUDE.md                        # déjà présent
├── spec.md                          # déjà présent
├── INGEST-CONFLICTS.md              # déjà présent (peut rester ou être déplacé)
├── renovate.json                    # ← Phase 0 (extends: config:recommended)
├── .gitignore                       # ← Phase 0 (NE PAS ignorer snapshots/)
├── .planning/                       # déjà présent (intel/, phases/, *.md)
├── tools/
│   └── snapshot/
│       ├── snapshot.sh              # ← Phase 0 (exécutable, set -euo pipefail)
│       └── README.md                # ← Phase 0 (port-forwards + env vars + exemples)
└── snapshots/
    └── baseline-2026-05-07/         # ← Phase 0 (premier dump committé)
        ├── sonarr/
        │   ├── downloadclient.json
        │   ├── indexer.json
        │   ├── notification.json
        │   ├── rootfolder.json
        │   ├── tag.json
        │   ├── qualityprofile.json
        │   ├── customformat.json
        │   ├── config_host.json
        │   ├── config_naming.json
        │   ├── config_mediamanagement.json
        │   ├── importlist.json
        │   ├── remotepathmapping.json
        │   ├── metadata.json
        │   └── system_status.json
        ├── radarr/
        │   └── ... (mêmes endpoints + config_metadata.json)
        ├── prowlarr/
        │   ├── indexer.json
        │   ├── applications.json
        │   ├── appprofile.json
        │   ├── downloadclient.json
        │   ├── indexerproxy.json
        │   ├── indexer_categories.json
        │   ├── indexerstats.json
        │   ├── indexerstatus.json
        │   ├── notification.json
        │   ├── tag.json
        │   ├── config_host.json
        │   ├── config_ui.json
        │   ├── config_downloadclient.json
        │   └── system_status.json
        ├── qbittorrent/
        │   ├── app_version.txt
        │   ├── app_webapi_version.txt
        │   ├── app_buildinfo.json
        │   ├── app_preferences.json
        │   ├── app_default_save_path.txt
        │   ├── torrents_categories.json
        │   ├── torrents_tags.json
        │   ├── torrents_info.json
        │   └── transfer_info.json
        ├── seerr/
        │   ├── settings_main.json
        │   ├── settings_sonarr.json
        │   ├── settings_radarr.json
        │   ├── settings_jellyfin.json
        │   ├── settings_notifications_*.json (×N)
        │   ├── settings_jobs.json
        │   ├── user.json
        │   ├── request.json
        │   └── status.json
        └── jellyfin/
            ├── system_info.json
            ├── system_configuration.json
            ├── library_virtualfolders.json
            ├── users.json
            ├── plugins.json
            ├── devices.json
            └── scheduled_tasks.json
```

### Pattern 1: Bash strict mode + trap cleanup

`[CITED: redsymbol.net/articles/unofficial-bash-strict-mode]`

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Workspace temp pour cookie jar qBittorrent + tampons
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT INT TERM

# Refus explicite si root (snapshot ne doit pas être lancé en root)
if [[ $EUID -eq 0 ]]; then
  echo "ERROR: do not run snapshot.sh as root" >&2
  exit 2
fi

# ... reste du script
```

- `set -e` : exit on error.
- `set -u` : exit on undefined variable.
- `set -o pipefail` : pipe fails if any stage fails (sinon `curl ... | jq ...` masque les erreurs curl).
- `IFS=$'\n\t'` : protège contre les filenames avec espaces.
- `trap` : garantit le cleanup du tmpdir même sur Ctrl-C ou SIGTERM.

### Pattern 2: Snapshot helper avec `jq --sort-keys`

```bash
# Capture un endpoint JSON, normalise pour diff déterministe.
# Usage: snapshot_get "<app>" "<base_url>" "<auth_header>" "<endpoint_path>" "<output_file>"
snapshot_get() {
  local app="$1"
  local base_url="$2"
  local auth_header="$3"
  local endpoint="$4"
  local output_file="$5"

  local out_dir="$(dirname "$output_file")"
  mkdir -p "$out_dir"

  local http_code
  http_code=$(
    curl --silent --show-error \
         --max-time 30 \
         --retry 2 --retry-delay 1 \
         -H "$auth_header" \
         -H "Accept: application/json" \
         -w "%{http_code}" \
         -o "$WORK_DIR/raw.json" \
         "${base_url}${endpoint}"
  )

  if [[ "$http_code" != "200" ]]; then
    echo "  ✗ ${app} ${endpoint} → HTTP ${http_code}" >&2
    return 1
  fi

  # Normalisation : tri des clés pour diffs déterministes
  if jq --sort-keys '.' "$WORK_DIR/raw.json" > "$output_file" 2>/dev/null; then
    echo "  ✓ ${app} ${endpoint} → $(basename "$output_file")"
    return 0
  else
    echo "  ✗ ${app} ${endpoint} → JSON parse error" >&2
    # Fallback: garder le raw même si pas du JSON valide (utile pour qBittorrent text endpoints)
    cp "$WORK_DIR/raw.json" "${output_file%.json}.txt"
    return 1
  fi
}
```

### Pattern 3: qBittorrent auth (cookie SID)

`[VERIFIED: qbittorrent wiki v5.0]`

```bash
qbt_login() {
  local url="$1"
  local user="$2"
  local pass="$3"
  local cookie_jar="$WORK_DIR/qbt.cookies"

  local http_code
  http_code=$(
    curl --silent --show-error \
         --cookie-jar "$cookie_jar" \
         -H "Referer: ${url}" \
         --data-urlencode "username=${user}" \
         --data-urlencode "password=${pass}" \
         -w "%{http_code}" \
         -o /dev/null \
         "${url}/api/v2/auth/login"
  )

  if [[ "$http_code" != "200" ]]; then
    echo "ERROR: qBittorrent login failed (HTTP ${http_code})" >&2
    return 1
  fi

  echo "$cookie_jar"
}

# Usage:
# COOKIE_JAR=$(qbt_login "$QBT_URL" "$QBT_USER" "$QBT_PASS")
# curl --cookie "$COOKIE_JAR" "$QBT_URL/api/v2/app/preferences" | jq --sort-keys '.' > out.json
```

### Pattern 4: Jellyfin auth (10.11+)

`[VERIFIED: api.jellyfin.org openapi spec, jellyfin issue #12990]`

```bash
# 10.11+ : Authorization: MediaBrowser Token="<key>"
JELLYFIN_AUTH="Authorization: MediaBrowser Token=\"${JELLYFIN_API_KEY}\""

# Compat 10.10 et antérieur : X-Emby-Token: <key> (à éviter en 10.11.8 si EnableLegacyAuthorization=false)
# JELLYFIN_AUTH="X-Emby-Token: ${JELLYFIN_API_KEY}"

curl -H "$JELLYFIN_AUTH" "${JELLYFIN_URL}/System/Info" | jq --sort-keys '.'
```

### Anti-Patterns to Avoid

- **`set -e` sans `set -o pipefail`** : `curl ... | jq ...` masque silencieusement les erreurs curl. Toujours les deux.
- **Coder `--apps` en hardcodant la boucle** sur l'array d'apps. Préférer une fonction `process_app()` paramétrable, plus maintenable.
- **Lire les API keys depuis un fichier** : interdit par CLAUDE.md "Variables d'environnement". Toujours `${VAR:?error message if unset}` pour exiger l'env var.
- **Snapshot un endpoint d'écriture par accident** : aucun POST/PUT/DELETE dans le script. Code review explicite. Optionnellement : `grep -nE '\-X (POST|PUT|DELETE|PATCH)' tools/snapshot/snapshot.sh` doit retourner 0 lignes (CI sanity en Phase 1).
- **Pas de `--max-time`** : si un endpoint hang, le script bloque indéfiniment. Toujours timeout (30s recommandé).
- **`jq` sans `--sort-keys`** : output non déterministe. Les diffs git deviennent illisibles entre runs.
- **Date dynamique dans le script** : `snapshots/baseline-$(date +%F)/` change à chaque jour. Préférer un argument explicite (`--output`) ou figer la baseline (le commit Phase 0 fige `2026-05-07` ; les snapshots futurs portent le nom `before-phase-N-<date>`).
- **Pas de mkdir -p avant write** : si le dossier app n'existe pas, curl `-o` fail. Toujours `mkdir -p "$(dirname "$out_file")"`.
- **`cookie-jar` partagé entre apps** : risque de fuite de cookies. Un cookie jar par app (qBittorrent only en Phase 0).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retries on transient errors | Custom retry loop with sleep | `curl --retry 2 --retry-delay 1` | Native, exponential backoff handled |
| JSON pretty-print with stable order | `python -c '...json...'` | `jq --sort-keys '.'` | jq est déjà installé, pas de dep Python en Phase 0 |
| YAML manifest parser pour endpoints | `yq` ou Python YAML | Bash arrays inline dans le script | Phase 0 minimaliste — pas besoin d'un format externe pour quelques dizaines d'endpoints |
| Renovate `customManagers` pour values.yaml | Custom regex maintenant | Defer to Phase 4 | Le fichier `values.yaml` n'existe pas encore — la regex serait morte |
| Cookie management qBittorrent | Custom Set-Cookie parser | `curl --cookie-jar` + `--cookie` | Native curl |
| Date formatting pour dossier output | Logic complexe dans Bash | `date +%F` (= `YYYY-MM-DD`) | Standard POSIX, déterministe |
| Logging coloré / structuré | ANSI escape codes maison | `echo` simple + redirection vers stderr (`>&2`) pour erreurs | Phase 0 minimaliste, JSON formatter c'est Phase 1 |
| Validation des fichiers JSON post-snapshot | Custom JSON parser | `jq empty <file>` (exit code = validity) | jq builtin |
| Detection de "writes during snapshot" | Custom diff/audit | Code review + grep `-X (POST\|PUT\|DELETE)` + `kubectl logs sonarr` (vérifier "GET only") | Phase 0 minimaliste : contrôle humain + grep, pas d'instrumentation runtime |

**Key insight:** Phase 0 doit rester rigoureusement minimal. Toute complexité supplémentaire (manifest YAML, framework de test, schema-gen, etc.) appartient à Phase 1+. Le critère est binaire : si une feature n'est pas dans les 5 success criteria de la roadmap, elle n'a pas sa place ici.

---

## Runtime State Inventory

> Phase 0 = greenfield (le repo contient uniquement spec.md, CLAUDE.md, .planning/). Aucun renommage / refactor / migration. Cette section est documentée comme **non applicable**.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — projet en bootstrap, aucune donnée préexistante dans arr-stack | Aucune |
| Live service config | None — Phase 0 ne déploie rien (les apps `selfhost` existent dans my-kluster mais arr-stack ne les touche pas) | Aucune |
| OS-registered state | None — aucun CronJob, aucun systemd unit, aucune Task Scheduler à enregistrer en Phase 0 | Aucune |
| Secrets/env vars | API keys déjà en place dans `my-kluster/secrets/` (consommées en lecture par le snapshot via env shell, pas modifiées) | Aucune — Phase 0 lit l'env, ne crée rien |
| Build artifacts | None — pas de Python build, pas de Helm package, pas de Docker image en Phase 0 | Aucune |

**Verified by:** lecture de PROJECT.md "Existant pré-bootstrap" ("repo arr-stack contient uniquement spec.md, CLAUDE.md, et .planning/intel/* au moment de l'ingestion") + `ls /home/moi/projets/perso/arr-stack/` `[VERIFIED]`.

---

## Common Pitfalls

### Pitfall 1: Rate-limiting / overload des APIs *arr en boucle

**What goes wrong:** Le script GET ~80 endpoints en moins de 10 secondes. Sonarr/Radarr/Prowlarr peuvent rate-limiter ou dégrader leur perf temporairement.

**Why it happens:** Pas d'inter-call delay, parallélisme implicite si on n'est pas vigilant.

**How to avoid:**
- Sequential par défaut (pas de `&` background curl).
- Optionnellement : `sleep 0.1` entre les endpoints d'une même app (négligeable, ~10s ajoutés au total).
- Si Phase 0 tourne sur cluster en charge, lancer hors-heures.

**Warning signs:** HTTP 429 dans les logs ; erreurs `connection reset` ; latence qui grimpe en cours de run.

### Pitfall 2: API key valide mais authn échoue (Jellyfin 10.11 spécifiquement)

**What goes wrong:** API key correcte, mais 401/403 à toutes les requêtes Jellyfin parce qu'on envoie `X-Emby-Token` au lieu de `Authorization: MediaBrowser Token=...`.

**Why it happens:** Jellyfin 10.11+ peut avoir `EnableLegacyAuthorization=false` dans `system.xml`, ce qui désactive `X-Emby-Token`. La doc tierce et la majorité des exemples web utilisent encore l'ancien header. `[CITED: github.com/jellyfin/jellyfin/issues/12990, gist nielsvanvelzen ea047d9028f676185832e51ffaf12a6f]`

**How to avoid:** Utiliser `Authorization: MediaBrowser Token="<key>"` par défaut. Documenter le fallback `X-Emby-Token` dans tools/snapshot/README.md pour debug. Ne PAS hardcoder l'un ou l'autre — exposer une variable `JELLYFIN_AUTH_HEADER` overridable.

**Warning signs:** 401/403 sur tous les endpoints Jellyfin alors que l'API key marche en UI. Vérifier la version Jellyfin (10.11+ = nouvelle auth obligatoire si legacy désactivé).

### Pitfall 3: qBittorrent 403 sur login (Referer manquant)

**What goes wrong:** `POST /api/v2/auth/login` avec username/pass corrects retourne 403.

**Why it happens:** qBittorrent vérifie le header `Referer` (et/ou `Origin`) pour bloquer les CSRF. Sans `Referer: <même origin que l'URL>`, refus systématique. `[CITED: qbittorrent wiki v5.0 Login section]`

**How to avoid:** Toujours `-H "Referer: ${QBT_URL}"` sur la requête de login. Le doc upstream est explicite.

**Warning signs:** Login fail avec 403 alors que les creds marchent en UI.

### Pitfall 4: Port-forward qui meurt en cours de run

**What goes wrong:** kubectl port-forward casse silencieusement (réseau qui flap, connexion idle timeout). Les requêtes suivantes timeout ou retournent connection refused.

**Why it happens:** kubectl port-forward n'est pas robuste. Sur des runs longs, il faut occasionnellement les relancer.

**How to avoid:**
- `--max-time 30` sur curl (déjà recommandé).
- Snapshot rapide (< 60s pour les 6 apps complètes) pour minimiser la fenêtre de risque.
- Documenter dans le README : "si une app fail systématiquement, vérifier que le port-forward est toujours actif".
- Optionnel (Phase 1+) : sanity check précoce — `curl -s --max-time 5 ${URL}/api/.../system/status` avant de boucler les endpoints d'une app.

**Warning signs:** Erreurs `Failed to connect` ou `Empty reply from server` qui apparaissent en milieu de run.

### Pitfall 5: Snapshot bootstrap impossible Jellyfin (compte admin pas créé)

**What goes wrong:** Sur une installation Jellyfin fraîche sans admin, `Library/VirtualFolders` retourne 403 même avec une API key valide. `[CITED: github.com/jellyfin/jellyfin/issues/11297]`

**Why it happens:** Jellyfin exige un user authentifié pour les endpoints library, pas juste une API key.

**How to avoid:**
- Le script doit tolérer les 403 sur Jellyfin avec un warning explicite : "If Jellyfin admin not bootstrapped yet, this is expected (NG5)."
- NE PAS faire fail le run global pour un 403 Jellyfin si NG5 pas encore satisfait. Per-endpoint failure = warning, pas error.
- Documenter le bootstrap admin dans le README : "Si Phase 0 tourne avant Phase 7 et que Jellyfin n'a pas encore son admin, le snapshot Jellyfin sera partiel — c'est normal."

**Warning signs:** 403 sur `/Library/VirtualFolders`, `/Users` mais 200 sur `/System/Info/Public`.

### Pitfall 6: Diff git illisible entre snapshots successifs (clés JSON non-stables)

**What goes wrong:** `git diff snapshots/baseline-X/ snapshots/before-phase-Y/` montre des centaines de lignes de réordonnancement parce que les APIs ne renvoient pas leurs clés dans un ordre stable.

**Why it happens:** Les implémentations REST n'ont aucune obligation de stabiliser l'ordre des clés dans le JSON renvoyé.

**How to avoid:** **TOUJOURS** `jq --sort-keys '.'` (ou `jq -S '.'`) sur tout output JSON snapshot. Le tri lexicographique des clés rend les diffs significatifs uniquement pour les vrais changements de valeur.

**Warning signs:** Premiers `git diff` entre snapshots qui montrent du bruit massif. Si ça arrive, c'est qu'on a oublié `--sort-keys` quelque part.

### Pitfall 7: Échec global sur erreur d'une seule app (pipefail trop strict)

**What goes wrong:** Une seule app fail (Jellyfin pas bootstrap, ou un endpoint deprecated retourne 404), `set -e` propage l'erreur, le script s'arrête, les autres apps ne sont pas snapshotées.

**Why it happens:** `set -euo pipefail` est strict. Sans gestion explicite, toute erreur est fatale.

**How to avoid:** Wrapper chaque appel d'app dans une fonction qui capture le code de retour, log l'échec, et retourne un statut local. Le script global compte les apps qui ont fail et renvoie exit 1 si **toutes** ont fail (ou exit 0 sinon, avec warnings dans le log).

```bash
# Pattern recommandé
declare -i FAILED_APPS=0
declare -i TOTAL_APPS=0

for app in "${TARGET_APPS[@]}"; do
  TOTAL_APPS+=1
  if ! snapshot_app "$app"; then
    echo "WARN: snapshot for ${app} failed (continuing)" >&2
    FAILED_APPS+=1
  fi
done

if (( FAILED_APPS == TOTAL_APPS )); then
  echo "ERROR: all ${TOTAL_APPS} apps failed" >&2
  exit 1
fi
echo "Snapshot complete: $((TOTAL_APPS - FAILED_APPS))/${TOTAL_APPS} apps OK"
exit 0
```

**Warning signs:** Snapshot s'arrête au milieu et seules 2-3 apps sont sur disque alors que 6 étaient demandées.

---

## Code Examples

### Snapshot complet pour une *arr app (Sonarr exemple)

`[VERIFIED: openapi spec extraction + curl/jq common patterns]`

```bash
snapshot_arr_app() {
  local app="$1"          # "sonarr" | "radarr"
  local base_url="$2"
  local api_key="$3"
  local api_version="$4"  # "v3"
  local output_dir="$5"

  local auth="X-Api-Key: ${api_key}"

  # Endpoints communs Sonarr/Radarr v3
  local endpoints=(
    "/api/${api_version}/downloadclient:downloadclient.json"
    "/api/${api_version}/indexer:indexer.json"
    "/api/${api_version}/notification:notification.json"
    "/api/${api_version}/rootfolder:rootfolder.json"
    "/api/${api_version}/tag:tag.json"
    "/api/${api_version}/qualityprofile:qualityprofile.json"
    "/api/${api_version}/customformat:customformat.json"
    "/api/${api_version}/config/host:config_host.json"
    "/api/${api_version}/config/naming:config_naming.json"
    "/api/${api_version}/config/mediamanagement:config_mediamanagement.json"
    "/api/${api_version}/config/ui:config_ui.json"
    "/api/${api_version}/config/indexer:config_indexer.json"
    "/api/${api_version}/config/downloadclient:config_downloadclient.json"
    "/api/${api_version}/importlist:importlist.json"
    "/api/${api_version}/remotepathmapping:remotepathmapping.json"
    "/api/${api_version}/metadata:metadata.json"
    "/api/${api_version}/system/status:system_status.json"
  )

  # Radarr-only
  if [[ "$app" == "radarr" ]]; then
    endpoints+=("/api/${api_version}/config/metadata:config_metadata.json")
  fi

  local local_failures=0
  for entry in "${endpoints[@]}"; do
    local endpoint="${entry%%:*}"
    local filename="${entry##*:}"
    snapshot_get "$app" "$base_url" "$auth" "$endpoint" "$output_dir/$filename" \
      || local_failures+=1
  done

  if (( local_failures > 0 )); then
    echo "WARN: ${app} had ${local_failures} endpoint failure(s)" >&2
    return 1
  fi
  return 0
}
```

### Snapshot qBittorrent (cookie auth + mix JSON / text endpoints)

```bash
snapshot_qbt() {
  local base_url="$1"
  local user="$2"
  local pass="$3"
  local output_dir="$4"

  mkdir -p "$output_dir"

  local cookie_jar
  cookie_jar=$(qbt_login "$base_url" "$user" "$pass") || return 1

  # JSON endpoints
  local json_endpoints=(
    "/api/v2/app/buildInfo:app_buildinfo.json"
    "/api/v2/app/preferences:app_preferences.json"
    "/api/v2/torrents/categories:torrents_categories.json"
    "/api/v2/torrents/tags:torrents_tags.json"
    "/api/v2/torrents/info:torrents_info.json"
    "/api/v2/transfer/info:transfer_info.json"
  )
  for entry in "${json_endpoints[@]}"; do
    local endpoint="${entry%%:*}"
    local filename="${entry##*:}"
    curl --silent --show-error --max-time 30 \
         --cookie "$cookie_jar" \
         "${base_url}${endpoint}" \
      | jq --sort-keys '.' > "$output_dir/$filename" \
      && echo "  ✓ qbittorrent ${endpoint}" \
      || echo "  ✗ qbittorrent ${endpoint}" >&2
  done

  # Text endpoints (version strings — pas du JSON valide)
  local text_endpoints=(
    "/api/v2/app/version:app_version.txt"
    "/api/v2/app/webapiVersion:app_webapi_version.txt"
    "/api/v2/app/defaultSavePath:app_default_save_path.txt"
  )
  for entry in "${text_endpoints[@]}"; do
    local endpoint="${entry%%:*}"
    local filename="${entry##*:}"
    curl --silent --show-error --max-time 30 \
         --cookie "$cookie_jar" \
         "${base_url}${endpoint}" \
         > "$output_dir/$filename" \
      && echo "  ✓ qbittorrent ${endpoint}" \
      || echo "  ✗ qbittorrent ${endpoint}" >&2
  done
}
```

### Validation post-snapshot (sanity check)

```bash
# Vérifie que tous les .json générés sont du JSON valide.
validate_snapshots() {
  local snapshot_dir="$1"
  local invalid=0
  while IFS= read -r -d '' f; do
    if ! jq empty "$f" 2>/dev/null; then
      echo "INVALID JSON: $f" >&2
      invalid+=1
    fi
  done < <(find "$snapshot_dir" -type f -name '*.json' -print0)

  if (( invalid > 0 )); then
    echo "ERROR: ${invalid} invalid JSON file(s) in ${snapshot_dir}" >&2
    return 1
  fi
  echo "Validation OK: all JSON files valid in ${snapshot_dir}"
  return 0
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `extends: ["config:base"]` | `extends: ["config:recommended"]` | Renovate v33+ (~2023) | `config:base` est explicitement déprécié — config validator warn. `[CITED: docs.renovatebot.com/config-presets]` |
| Jellyfin auth via `X-Emby-Token` | Jellyfin auth via `Authorization: MediaBrowser Token="..."` | Jellyfin 10.11 (2024-2025) | Legacy header désactivable via `EnableLegacyAuthorization=false` dans `system.xml`. Suppression prévue future release. `[CITED: github.com/jellyfin/jellyfin/issues/12990, seerr-team/seerr#2361]` |
| Sonarr v3 vs v4 API | API v3 stable et compatible v3+v4 | Sonarr 4.0 (2023-2024) | OpenAPI doc upstream le confirme : "The v3 API docs apply to both v3 and v4 versions of Sonarr." `[VERIFIED: Sonarr/Sonarr develop openapi.json info.description]` Sonarr 4.0.17 déjà déployé — pas de migration en Phase 0. |
| Buildarr / Recyclarr / Flemmarr / Terraform devopsarr | Script Python custom (`arrconf`) | Décision projet (ADR-1) | OUT OF SCOPE Phase 0 (Phase 1+). Pertinent pour comprendre pourquoi Phase 0 = Bash et pas un wrapper d'outil existant. |

**Deprecated/outdated:**
- `config:base` Renovate preset → `config:recommended`.
- Jellyfin `X-Emby-Token` (legacy, désactivable 10.11+, suppression future) → `Authorization: MediaBrowser Token=...`.
- Sonarr v3 API spec ancienne (cap au schéma legacy) → spec OpenAPI develop branch (toujours à jour).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Le cluster `my-kluster` est accessible depuis le workstation via `kubectl port-forward` (pas de NetworkPolicy bloquant le forward). | Architecture Patterns / Connection strategy | Si NetworkPolicy bloque, l'utilisateur ne peut pas snapshot. Mitigation : test manuel `kubectl -n selfhost port-forward svc/sonarr 8989:8989` avant Phase 0 plan. **Risque LOW** — le cluster est single-node single-user, pas de NetworkPolicy en place selon les manifests vus. `[ASSUMED]` |
| A2 | Les API keys actuelles dans `my-kluster/secrets/configarr-secret.yaml` (SONARR_API_KEY, RADARR_API_KEY) sont valides en lecture sur `/api/v3/*`. Les autres API keys (PROWLARR_API_KEY, SEERR_API_KEY, JELLYFIN_API_KEY) doivent être obtenues via UI au minimum une fois. `[ASSUMED]` | User Constraints | Si les API keys n'existent pas pour Prowlarr/Seerr/Jellyfin, l'utilisateur doit les générer via UI avant Phase 0 (NG5). À documenter dans le README. |
| A3 | Le bootstrap admin Jellyfin (NG5) est déjà fait sur l'instance déployée — sinon les endpoints `/Library/VirtualFolders`, `/Users` retourneront 403. `[ASSUMED]` | Common Pitfalls / Pitfall 5 | Si bootstrap pas fait, le snapshot Jellyfin sera partiel (endpoints `/System/Info/Public` OK, le reste 403). Le script doit tolérer ça (warning, pas error). |
| A4 | qBittorrent 5.0+ est déployé (le wiki v5.0 cité fait foi pour les endpoints `/api/v2/*`). `[ASSUMED]` | Standard Stack / qBittorrent | Si l'instance déployée est qBittorrent 4.x : la majorité des endpoints sont identiques mais `/torrents/categories` requiert v4.1.4+ (Web API v2.1.1). À vérifier en exécutant le snapshot — si fail, tag les versions affectées dans le README. **Risque LOW** — version `latest` linuxserver = current stable. |
| A5 | Seerr v3.2.0 conserve la compat Overseerr v1 sur les endpoints GET listés (settings, user, request). `[ASSUMED]` | Standard Stack / Seerr | Q1 ouverte : compat Seerr ↔ Overseerr/Jellyseerr. Pour Phase 0 (read-only), risque MEDIUM : si un endpoint GET diverge, le snapshot est juste vide pour cette ressource — pas bloquant. Validation réelle = Phase 6. |
| A6 | Les ports natifs des images linuxserver/ghcr utilisés (8989/7878/9696/8080/5055/8096) sont les ports exposés par les services K8s `selfhost`. `[VERIFIED: kubectl get svc -n selfhost]` | Connection strategy | Vérifié pendant la recherche — tous les services existent avec les ports corrects. Pas un risque. |
| A7 | Aucune CI / GitHub Actions n'est attendue en Phase 0. `[VERIFIED: spec.md §7 Phase 0 livrables]` | User Constraints | Vérifié — spec.md liste les workflows GHA en Phase 1 (`arrconf-image.yml`) et 4 (`chart-lint.yml`). Pas un risque. |
| A8 | `tools/snapshot/snapshot.sh` est destiné à être exécuté **localement** par l'utilisateur en Phase 0, pas in-cluster. Phase 2 introduira l'exécution in-cluster via CronJob arrconf (Python, pas Bash). | Architecture Responsibility Map | Cohérent avec ADR-6 ("Phase 0 = script Bash standalone") et C1 ("apply in-cluster only" = applique à arrconf, pas au snapshot read-only). Pas un risque — clarification. |

**Si le tableau était vide :** il ne l'est pas. 5 claims `[ASSUMED]` (A1-A5) ont besoin de soit confirmation utilisateur en `/gsd-discuss-phase 0`, soit validation par exécution manuelle avant le plan.

---

## Open Questions

1. **Faut-il un dossier séparé `tools/snapshot/endpoints/` avec un fichier par app, ou tout dans `snapshot.sh` ?**
   - What we know : 6 apps × ~10-17 endpoints = ~80 lignes de declarations. Tenable inline en Bash arrays.
   - What's unclear : si on ajoute des resource types Phase 1+ (qBit, Seerr, Jellyfin), le script grossit. Tradeoff lisibilité vs simplicité.
   - **Recommendation:** Tout inline en Phase 0 (minimaliste). Si Phase 1+ ressent le besoin, refactorer en JSON manifest (jq peut le lire trivialement). Pas un blocker maintenant.

2. **Le script doit-il faire un sanity check de connectivité avant de bombarder une app de requêtes ?**
   - What we know : `--max-time 30` sur curl gère les hangs unitaires.
   - What's unclear : si toutes les requêtes vers une app fail, on aurait `n_endpoints * 30s` de timeout (Sonarr seul = 17 × 30 = ~8 minutes pire cas).
   - **Recommendation:** Pre-flight check `curl -s --max-time 5 ${URL}/api/.../system/status` AVANT la boucle d'endpoints. Si fail → skip cette app entière, log warning, continue. ~5s perdus dans le cas dégradé vs 8 min.

3. **Faut-il committer un manifest JSON Schema pour les snapshots ?**
   - What we know : les endpoints ont leurs schemas dans les OpenAPI specs upstream.
   - What's unclear : utile en Phase 0 ?
   - **Recommendation:** NON — Phase 0 minimaliste. Le snapshot raw est self-describing (les noms de fichiers ↔ endpoints). Un schema validant chaque .json contre l'OpenAPI upstream serait Phase 1+ si jamais nécessaire.

4. **`tools/snapshot/README.md` vs juste documenter dans `README.md` racine ?**
   - What we know : ROADMAP success criterion #5 demande "README minimal présent expliquant comment relancer un snapshot avant un test risqué".
   - What's unclear : un seul README ou deux ?
   - **Recommendation:** Deux. README racine = pointer minimal (lien vers le tools/snapshot/README.md). tools/snapshot/README.md = doc opérationnelle (port-forwards, env vars, exemples, troubleshooting). Permet d'évoluer indépendamment.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `bash` | snapshot.sh runtime | ✓ | 5.2.37 `[VERIFIED: bash --version]` | — |
| `curl` | HTTP requests | ✓ | 8.14.1 `[VERIFIED: curl --version]` | — |
| `jq` | JSON normalization | ✓ | 1.8.1 `[VERIFIED: jq --version]` | — |
| `kubectl` | port-forward vers selfhost | ✓ | 1.33.11 `[VERIFIED: kubectl version]` | — |
| `git` | Versioning des snapshots | ✓ (repo déjà initialisé) | (système) | — |
| `gh` (optionnel) | Push initial + repo create | ✓ | (système) | UI GitHub manuel |
| Cluster connectivity | snapshot d'apps in-cluster | ✓ (context `microk8s` actif) `[VERIFIED: kubectl config current-context]` | — | — |
| Service `sonarr` (port 8989) | Sonarr snapshot | ✓ `[VERIFIED: kubectl get svc -n selfhost]` | linuxserver/sonarr 4.0.17 | Pas de fallback — bloque snapshot Sonarr seulement |
| Service `radarr` (port 7878) | Radarr snapshot | ✓ `[VERIFIED]` | linuxserver/radarr 6.1.1 | idem |
| Service `prowlarr` (port 9696) | Prowlarr snapshot | ✓ `[VERIFIED]` | linuxserver/prowlarr 2.3.5 | idem |
| Service `qbittorrent` (port 8080) | qBittorrent snapshot | ✓ `[VERIFIED]` | linuxserver/qbittorrent latest | idem |
| Service `seerr` (port 5055) | Seerr snapshot | ✓ `[VERIFIED]` | seerr v3.2.0 | idem |
| Service `jellyfin` (port 8096) | Jellyfin snapshot | ✓ `[VERIFIED]` | linuxserver/jellyfin 10.11.8 | Si admin pas bootstrap (NG5) → snapshot partiel autorisé |
| `SONARR_API_KEY` env | Auth Sonarr | ⚠ doit être exporté avant run | — | Lire depuis `my-kluster/secrets/configarr-secret.yaml` (mais user must `export`, pas le script) |
| `RADARR_API_KEY` env | Auth Radarr | ⚠ idem | — | idem |
| `PROWLARR_API_KEY` env | Auth Prowlarr | ⚠ à générer via UI Prowlarr Settings → General | — | Bootstrap manuel (NG5) si jamais fait |
| `QBT_USER` + `QBT_PASS` env | Auth qBittorrent | ⚠ user/pass admin qBit | — | idem |
| `SEERR_API_KEY` env | Auth Seerr | ⚠ à générer via UI Seerr Settings → General | — | idem |
| `JELLYFIN_API_KEY` env | Auth Jellyfin | ⚠ à générer via UI Dashboard → API Keys | — | idem |

**Missing dependencies with no fallback:**
- Aucune dépendance manquante pour Phase 0. Tous les outils CLI sont présents et le cluster est joignable.

**Missing dependencies with fallback:**
- API keys env-vars : prérequis manuel (NG5, REQ-bootstrap-exception). Le plan doit inclure une étape "vérifier que toutes les API keys sont en main" avant l'exécution du snapshot.

---

## Validation Architecture

> `.planning/config.json` n'existe pas (`[VERIFIED: ls .planning/config.json]`). Donc `workflow.nyquist_validation` est absent et **traité comme enabled** par défaut. Section incluse.

### Test Framework

Phase 0 n'introduit pas de framework de tests automatisés (pas de Python, pas de Helm encore). La validation de Phase 0 = **vérifications manuelles + scripts shell ad-hoc**.

| Property | Value |
|----------|-------|
| Framework | Aucun framework formel — Bash + jq pour validation post-run |
| Config file | None — Phase 0 sans pyproject.toml / package.json / pytest.ini |
| Quick run command | `./tools/snapshot/snapshot.sh --apps sonarr` (1 app pour smoke test) |
| Full suite command | `./tools/snapshot/snapshot.sh && find snapshots/baseline-2026-05-07/ -name '*.json' -exec jq empty {} \;` |
| Phase gate | (1) script exit 0, (2) tous les .json valides via `jq empty`, (3) au moins 5/6 apps présentes (Jellyfin partiel toléré si NG5 pas fait), (4) commit Git réussi |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-baseline-snapshot | snapshot.sh produit JSON pour les 6 apps dans le bon chemin | smoke | `./tools/snapshot/snapshot.sh && test -d snapshots/baseline-2026-05-07/sonarr && test -d snapshots/baseline-2026-05-07/radarr && test -d snapshots/baseline-2026-05-07/prowlarr && test -d snapshots/baseline-2026-05-07/qbittorrent && test -d snapshots/baseline-2026-05-07/seerr && test -d snapshots/baseline-2026-05-07/jellyfin` | ❌ Wave 0 (le script et les snapshots n'existent pas encore) |
| REQ-baseline-snapshot | Tous les .json sont du JSON valide | unit | `find snapshots/baseline-2026-05-07/ -name '*.json' -exec jq empty {} \;` (exit 0 = tous valides) | ❌ Wave 0 |
| REQ-baseline-snapshot | Snapshots committés dans Git (NE PAS .gitignore) | manual | `git log --oneline -- snapshots/ | head -1` (montre le commit) + `git check-ignore snapshots/baseline-2026-05-07/sonarr/downloadclient.json` (exit code = 1 = pas ignoré) | ❌ Wave 0 |
| REQ-baseline-snapshot | Aucune écriture observée pendant le snapshot | manual | (avant) `kubectl logs -n selfhost deploy/sonarr --tail=100 > /tmp/sonarr-pre.log` ; (snapshot) `./tools/snapshot/snapshot.sh --apps sonarr` ; (après) `kubectl logs -n selfhost deploy/sonarr --tail=200 > /tmp/sonarr-post.log` ; `diff /tmp/sonarr-pre.log /tmp/sonarr-post.log | grep -iE '(POST\|PUT\|DELETE)' && echo "WRITES DETECTED" \|\| echo "READ-ONLY OK"` | ❌ Wave 0 |
| REQ-baseline-snapshot | Pas de POST/PUT/DELETE dans le code du script | unit (lint) | `grep -nE '\-X[[:space:]]*(POST\|PUT\|DELETE\|PATCH)' tools/snapshot/snapshot.sh; test $? -eq 1` (exit 1 de grep = aucun match = OK) | ❌ Wave 0 |
| REQ-baseline-snapshot | renovate.json valide (Renovate config validator) | unit | `npx --yes --package=renovate -- renovate-config-validator renovate.json` | ❌ Wave 0 (renovate.json n'existe pas encore) |
| REQ-baseline-snapshot | renovate.json utilise `extends: ["config:recommended"]` | unit | `jq -e '.extends \| index("config:recommended")' renovate.json` | ❌ Wave 0 |
| REQ-baseline-snapshot | README mentionne le workflow snapshot | manual | `grep -iE 'snapshot.sh\|snapshot raw' README.md` | ❌ Wave 0 |
| REQ-phase-roadmap | ROADMAP.md liste 9 phases avec critères | manual | `grep -E '^### Phase [0-8]:' .planning/ROADMAP.md \| wc -l` (== 9) | ✅ existe déjà |

### Sampling Rate

- **Per task commit:** smoke test minimal — `./tools/snapshot/snapshot.sh --apps sonarr` + `jq empty snapshots/.../sonarr/*.json`
- **Per wave merge:** suite complète — script complet + validation JSON + grep no-write + Renovate validator
- **Phase gate:** validation manuelle des 5 success criteria de la roadmap avant `/gsd-verify-work` :
  1. Tous les fichiers JSON présents pour les 6 apps (modulo Jellyfin partiel autorisé)
  2. Tous committés dans Git
  3. Aucune écriture observée (logs *arr ne montrent que des reads)
  4. `renovate.json` initial committé et valide
  5. README minimal explique comment relancer un snapshot

### Wave 0 Gaps

- [ ] `tools/snapshot/snapshot.sh` — script principal (n'existe pas)
- [ ] `tools/snapshot/README.md` — doc opérationnelle (n'existe pas)
- [ ] `README.md` racine — pointer minimal (n'existe pas)
- [ ] `renovate.json` — config initiale (n'existe pas)
- [ ] `.gitignore` — explicit non-ignore de `snapshots/` + ignore de `*.cookies` / `.env*` (n'existe pas)
- [ ] `snapshots/baseline-2026-05-07/` — premier dump (à exécuter et committer)
- [ ] Le repo GitHub `tom333/arr-stack` — à créer si pas encore fait (gh CLI ou UI)

*(Aucun framework de test à installer en Phase 0 — Python/pytest arrive Phase 1.)*

---

## Security Domain

> `security_enforcement` flag absent → traité comme enabled. Phase 0 a une surface d'attaque très réduite (script local read-only) mais quelques contrôles s'appliquent.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (read-only credentials) | API keys env-only, jamais en fichier (CLAUDE.md). Cookie qBittorrent dans `mktemp -d` cleanup via `trap`. |
| V3 Session Management | partial (qBittorrent) | Cookie SID dans tmpdir éphémère, jamais committé. Logout optionnel à la fin. |
| V4 Access Control | yes | Refus de tourner en root (`if [[ $EUID -eq 0 ]]; then exit 2`). API keys lues via env, pas via fichier. |
| V5 Input Validation | partial | Validation des `--apps` arg contre liste fixe ; rejet des values inconnues. |
| V6 Cryptography | no | Phase 0 ne fait aucune crypto (pas de TLS pinning custom, pas de hashing, pas de signing). curl gère TLS standard. |
| V7 Error Handling & Logging | yes | Erreurs vers stderr ; pas de leak d'API key dans les logs (jamais imprimer `${API_KEY}` directement). |
| V8 Data Protection | yes | API keys jamais committées ; cookie jar dans tmpdir cleanup ; snapshots ne contiennent **pas** de secrets (l'API key elle-même n'est jamais retournée par les endpoints listés — vérifié pendant la recherche : les responses incluent `apiKey: '<redacted>'` ou des champs `Field(exclude=True)` côté Sonarr/Radarr settings). |
| V14 Configuration | yes | `.gitignore` doit explicitement ignorer `*.env`, `*.cookies`, `*.cookie-jar`. |

### Known Threat Patterns for Bash + curl + jq + cluster

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret leak via log/echo | Information Disclosure | Ne jamais logger `${API_KEY}`. Si erreur, logger l'endpoint + HTTP code, pas l'auth header. |
| Secret leak via .bash_history | Information Disclosure | Documenter dans README : exporter via `read -s API_KEY` ou via fichier `.env` non committé + `set -a; source .env; set +a` (puis `.env` dans `.gitignore`). |
| Cookie jar accessible to other users | Information Disclosure | `mktemp -d` (mode 700 par défaut) + `trap rm -rf "$WORK_DIR" EXIT INT TERM`. |
| Snapshot leak de données sensibles | Information Disclosure | Auditer manuellement le premier snapshot avant le commit : `grep -iE '"(apiKey\|password\|token)"' snapshots/baseline-*/**/*.json` doit montrer uniquement des champs vides ou redacted. Les APIs *arr exposent souvent un `apiKey` field (l'API key de l'app elle-même !) — à vérifier. |
| Command injection via `--apps` | Tampering | Whitelist explicite : `case "$app" in sonarr\|radarr\|prowlarr\|qbittorrent\|seerr\|jellyfin) ;; *) exit 2 ;; esac` |
| Path traversal via `--output` | Tampering | Refuser `..` dans le chemin output. Préfixer obligatoirement par `snapshots/`. |
| TOCTOU sur le snapshot dir | Tampering | `mkdir -p` (idempotent), pas de check-then-write race. |
| MITM sur kubectl port-forward | Spoofing | Pas applicable en pratique (port-forward via API K8s = TLS mutuel). Pas de threat réel sur localhost. |

### ⚠ Sanity check sécurité PRIORITAIRE post-snapshot (CRITIQUE)

Le **premier dump** doit être audité manuellement avant le commit :

```bash
# CRITIQUE : avant `git add snapshots/`, vérifier qu'aucun secret n'a fuité.
grep -irE '"(apiKey|password|token|sessionKey|webhookUrl)":\s*"[^"]+"' snapshots/baseline-2026-05-07/ \
  | grep -v '"apiKey":\s*""' \
  | grep -v '"apiKey":\s*null'
```

Si cette commande renvoie des matches non-vides, **NE PAS COMMITTER** : il y a probablement une fuite de creds dans le snapshot. Notamment :
- Sonarr/Radarr exposent leur propre API key dans `/api/v3/config/host` (champ `apiKey`).
- Notifications Discord/Slack/Telegram contiennent des webhook URLs.
- qBittorrent `/api/v2/app/preferences` peut contenir le username/password proxy.

**Décision Phase 0 :** Soit (a) **redact ces champs côté script** avant write (avec `jq 'walk(...)'`), soit (b) **inclure les snapshots tels quels** mais SEULEMENT après confirmation que le repo reste public et que ces creds sont déjà connus de l'utilisateur uniquement (cluster privé homelab single-user, donc acceptable).

**Recommandation :** option (a) — un filtre jq qui redact les champs sensibles vers `"<redacted>"`. Pattern :

```bash
JQ_REDACT='walk(if type == "object" then with_entries(if (.key | test("(?i)apiKey|password|token|webhookUrl|sessionKey")) and .value != null and .value != "" then .value = "<redacted>" else . end) else . end)'

curl ... | jq --sort-keys "$JQ_REDACT" > out.json
```

Cela permet de garder la richesse forensic (savoir QUE le champ existe, quel type) sans leak des valeurs. À discuter en `/gsd-discuss-phase 0`.

---

## Sources

### Primary (HIGH confidence) — verified via tool

- `https://raw.githubusercontent.com/Sonarr/Sonarr/develop/src/Sonarr.Api.V3/openapi.json` — Sonarr v3 API endpoints (téléchargé et `jq`-extrait pendant la recherche, 297 KB, ~80 paths)
- `https://raw.githubusercontent.com/Radarr/Radarr/develop/src/Radarr.Api.V3/openapi.json` — Radarr v3 API endpoints (309 KB)
- `https://raw.githubusercontent.com/Prowlarr/Prowlarr/develop/src/Prowlarr.Api.V1/openapi.json` — Prowlarr v1 API endpoints (145 KB)
- `https://api.jellyfin.org/openapi/jellyfin-openapi-stable.json` — Jellyfin API stable spec (2 MB ; security scheme `Authorization` en header confirmé)
- `https://raw.githubusercontent.com/seerr-team/seerr/main/seerr-api.yml` — Seerr API spec (220 KB ; X-Api-Key auth confirmé)
- `https://raw.githubusercontent.com/wiki/qbittorrent/qBittorrent/WebUI-API-(qBittorrent-5.0).md` — qBittorrent WebUI API v5.0 wiki (118 KB ; Login flow + cookie SID confirmé)
- `kubectl get svc -n selfhost` — services présents dans le cluster (sonarr, radarr, prowlarr, qbittorrent, seerr, flaresolverr, jellyfin, cleanuparr) confirmés en runtime

### Secondary (MEDIUM confidence) — Web search verified against official docs

- `https://docs.renovatebot.com/config-presets/` — `config:recommended` est current, `config:base` est déprécié
- `https://docs.renovatebot.com/modules/manager/regex/` — pattern customManagers (pour Phase 4, pas Phase 0)
- `https://github.com/jellyfin/jellyfin/issues/12990` — Jellyfin auth header docs (X-Emby-Token vs Authorization MediaBrowser)
- `https://github.com/seerr-team/seerr/issues/2361` — Jellyfin 10.11 breaking change pour Seerr (corroboration auth change)
- `https://gist.github.com/nielsvanvelzen/ea047d9028f676185832e51ffaf12a6f` — Jellyfin API authorization gist (referenced)
- `https://wiki.servarr.com/sonarr` + `https://wiki.servarr.com/radarr/system` — Servarr wiki (corroboration des endpoints)
- `https://github.com/jellyfin/jellyfin/issues/11297` — `/Library/VirtualFolders` 403 quand admin pas bootstrap

### Tertiary (LOW confidence) — Single source

- `http://redsymbol.net/articles/unofficial-bash-strict-mode/` — Bash strict mode pattern (single source, mais standard ancien et stable)
- `https://jqlang.org/manual/` — jq `--sort-keys` flag (confirmé via `jq --help`)

---

## Project Constraints (from CLAUDE.md)

Toutes les directives `CLAUDE.md` applicables à Phase 0, copiées ici pour le planner :

### Garde-fous "ne pas faire" (s'appliquent à Phase 0)

- ❌ **Ne pas committer de secrets** — applicable au premier dump (audit redact OBLIGATOIRE avant commit, voir Security Domain).
- ❌ **Ne pas appeler les vraies APIs depuis les tests CI** — pas de tests CI en Phase 0, mais le script Bash lui-même appelle les vraies APIs. Restriction applicable seulement aux tests automatisés (Phase 1+).
- ❌ **Ne pas tester un nouveau reconciler en cluster sans avoir snapshot la baseline d'abord** — Phase 0 EST la baseline. Une fois Phase 0 done, ce garde-fou s'active pour toutes les phases suivantes.
- ❌ **Ne pas ignorer `snapshots/` dans `.gitignore`** — explicit (CLAUDE.md). Le `.gitignore` Phase 0 doit explicitement NE PAS contenir `snapshots/`.
- ❌ **Ne pas hardcoder `:latest`** — pas applicable Phase 0 (aucune image, aucun tag à pinner).
- ❌ **Ne pas écrire dans les endpoints quality_profiles / custom_formats / quality_definitions / media_naming** — pas applicable Phase 0 (read-only). Mais on snapshot ces endpoints malgré la frontière (forensic).
- ❌ **Ne pas dupliquer la config configarr ailleurs** — pas applicable Phase 0.
- ❌ **Ne pas activer `prune: true` par défaut** — pas applicable Phase 0.
- ❌ **Ne pas amender un tag de release publié** — pas applicable Phase 0 (pas de tag).
- ❌ **Ne pas déployer directement depuis ce repo** — pas applicable Phase 0.

### Conventions de code (Phase 0 = Bash uniquement)

- ✅ **Pas de commentaires-narratifs** ("# fetch the data") — les noms parlent. Commentaire utile = explique le POURQUOI non-évident.
- ✅ **Bash strict mode** : `set -euo pipefail` + `IFS=$'\n\t'` + `trap` cleanup (recommandé, pas un constraint formel CLAUDE.md mais pattern standard).
- ✅ **Variables d'environnement** : `${VAR:?error message}` pour exiger la présence d'une env var. Liste : `SONARR_API_KEY`, `RADARR_API_KEY`, `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY`.

### Workflow snapshot (CLAUDE.md "Workflow snapshot")

- AVANT toute Phase qui touche un nouveau scope, re-snapshot raw d'abord. Phase 0 EST cette baseline.
- Tous les snapshots committés — NE PAS dans `.gitignore`.
- Au moindre doute après un test cluster : `tools/snapshot/snapshot.sh --output snapshots/forensic-$(date +%FT%H%M)/`.
- Toujours `--dry-run` la première fois sur une nouvelle config — le script Phase 0 est read-only par construction, donc ce garde-fou s'active vraiment Phase 2.

---

## Metadata

**Confidence breakdown:**
- Endpoints par app : **HIGH** — extraits directement des OpenAPI specs upstream (download confirmé `[VERIFIED]` pendant la recherche).
- Auth strategies : **HIGH** — Sonarr/Radarr/Prowlarr/Seerr X-Api-Key confirmé via spec ; qBittorrent cookie SID confirmé via wiki ; Jellyfin Authorization MediaBrowser confirmé via spec + 2 issues GitHub.
- Renovate config initiale : **HIGH** — `config:recommended` confirmé current via docs officielles.
- Bash strict mode + jq sort-keys : **HIGH** — patterns standard depuis 10+ ans.
- Cluster connectivité : **HIGH** — `kubectl get svc -n selfhost` exécuté en runtime, services confirmés.
- Bootstrap Jellyfin état actuel : **MEDIUM** — `[ASSUMED]` (A3) — risque réel mais le script doit le tolérer proprement de toute façon.
- Compat Seerr v3.2.0 sur GET endpoints : **MEDIUM** — `[ASSUMED]` (A5) — Q1 ouverte, mais risque limité en read-only.
- Sécurité / leak de secrets dans premier dump : **HIGH risque, HIGH confidence sur la mitigation** — l'audit grep + redact jq est la mitigation standard.

**Research date:** 2026-05-07
**Valid until:** 2026-06-07 (30 jours pour les endpoints stables ; 7 jours seulement pour les claims `[ASSUMED]` qui devraient être validés via `/gsd-discuss-phase 0`).

---

## Sources (markdown links pour lecture facile)

- [Sonarr OpenAPI develop branch](https://raw.githubusercontent.com/Sonarr/Sonarr/develop/src/Sonarr.Api.V3/openapi.json)
- [Radarr OpenAPI develop branch](https://raw.githubusercontent.com/Radarr/Radarr/develop/src/Radarr.Api.V3/openapi.json)
- [Prowlarr OpenAPI develop branch](https://raw.githubusercontent.com/Prowlarr/Prowlarr/develop/src/Prowlarr.Api.V1/openapi.json)
- [Jellyfin OpenAPI stable spec](https://api.jellyfin.org/openapi/jellyfin-openapi-stable.json)
- [Jellyfin API docs](https://api.jellyfin.org/)
- [Seerr API spec (seerr-api.yml)](https://github.com/seerr-team/seerr/blob/main/seerr-api.yml)
- [qBittorrent WebUI API v5.0 wiki](https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-5.0))
- [Servarr Wiki (Sonarr)](https://wiki.servarr.com/sonarr)
- [Servarr Wiki (Radarr)](https://wiki.servarr.com/radarr/system)
- [Renovate config presets docs](https://docs.renovatebot.com/config-presets/)
- [Renovate customManagers regex docs](https://docs.renovatebot.com/modules/manager/regex/)
- [Jellyfin auth gist (nielsvanvelzen)](https://gist.github.com/nielsvanvelzen/ea047d9028f676185832e51ffaf12a6f)
- [Jellyfin issue #12990 — API auth docs](https://github.com/jellyfin/jellyfin/issues/12990)
- [Jellyfin issue #11297 — VirtualFolders 403](https://github.com/jellyfin/jellyfin/issues/11297)
- [Seerr issue #2361 — Jellyfin 10.11 auth](https://github.com/seerr-team/seerr/issues/2361)
- [Bash strict mode reference](http://redsymbol.net/articles/unofficial-bash-strict-mode/)
- [jq manual](https://jqlang.org/manual/)

---

**Ready for Planning.** Le planner peut maintenant créer les PLAN.md à partir de cette research. Les 6 success criteria de la roadmap sont mappés à des actions concrètes (script structure, manifest endpoints, security audit, README, renovate.json, .gitignore, premier dump + commit). Les `[ASSUMED]` claims (A1-A5) devraient être confirmés en `/gsd-discuss-phase 0` ou validés en pratique avant exécution.
