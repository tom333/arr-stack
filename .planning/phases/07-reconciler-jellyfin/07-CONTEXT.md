# Phase 7: Reconciler Jellyfin - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Ajouter `tools/arrconf/arrconf/reconcilers/jellyfin.py` qui réconcilie déclarativement Jellyfin 10.11.8 (image `lscr.io/linuxserver/jellyfin`) depuis `arrconf.yml`. Bootstrap admin + `JELLYFIN_API_KEY` sont déjà acquis (REQ-bootstrap-exception). Surface arrconf alignée sur la frontière spec.md §316-319 (libraries / users / server config / plugins best-effort).

**In scope (minimum viable) :**

- **Nouveau `jellyfin.py` reconciler** dans `tools/arrconf/arrconf/reconcilers/` :
  - `class JellyfinClient(ArrApiClient)` avec `api_path = ""` (Jellyfin API root) — **PAS de `_ArrV3Client`** (spec.md §895, §926 : Jellyfin OUT-OF-SCOPE de forceSave + merge_fields_for_put).
  - **Auth Q9 — délégué au probe live** : Stratégie d'auth déterminée par les agents downstream (research). `client_base.py:51` `auth_headers()` est overridable. Préférence par défaut : `Authorization: MediaBrowser Token="<key>"` (recommendé par la doc Jellyfin 10.11+) ; fallback `?api_key=<key>` query param. Probe à effectuer AVANT d'écrire le client (D-07-VALIDATE-01, mirror de D-06-VALIDATE-01).
  - **Resources managed (4 scopes) :**
    1. **Libraries** — 2 libraries merged multi-path (D-07-LIB-01) :
       - `Séries` (CollectionType=tvshows) → PathInfos `[/media/series, /media/anime, /media/family]`
       - `Films` (CollectionType=movies) → PathInfos `[/media/films, /media/films-anime, /media/films-family]`
       - Reconciliation : `POST /Library/VirtualFolders` (CREATE), `POST /Library/VirtualFolders/Paths` (ADD path), `DELETE /Library/VirtualFolders/Paths` (REMOVE path). Match par `Name`. Scope sur `Name + CollectionType + PathInfos uniquement` (D-07-LIB-02). LibraryOptions (TypeOptions/fetchers/locale/EnableRealtimeMonitor) restent operator-managed.
    2. **Users** — Admin only (`moi`, ID `82fd95db72904569b08d83271823ceaa`) per D-07-USERS-01. Scope : `Policy` (IsAdministrator, Enable*, Block*, quotas, RemoteClientBitrateLimit, MaxActiveSessions). Pas `Configuration` (UI prefs). Pas `Password`. Pas `AuthenticationProviderId`. `PUT /Users/{id}/Policy`. Match par Name="moi" résolu en Id au runtime. `emilie` reste operator-managed via UI (prune=false hardcoded — pas de suppression accidentelle).
    3. **Server config** — Subset locale + retention + ServerName + PluginRepositories (D-07-CONFIG-01). Champs : `UICulture`, `MetadataCountryCode`, `PreferredMetadataLanguage`, `ActivityLogRetentionDays`, `LogFileRetentionDays`, `ServerName`, `PluginRepositories`. Endpoint : `POST /System/Configuration` (ou PUT — à valider par probe ; Jellyfin OpenAPI confirmera). Les autres ~43 fields (`TrickplayOptions`, `MetadataOptions[]`, `CodecsUsed`, etc.) restent operator-managed.
    4. **Plugins** — Activation-only (D-07-PLUGINS-01). Allowlist YAML des 6 plugins actuels (`TMDb`, `OMDb`, `MusicBrainz`, `AudioDb`, `StudioImages`, `KodiSyncQueue`). Pour chaque plugin déclaré, vérifier `Status == "Active"`. Si Disabled → endpoint d'activation (à découvrir live — probable `POST /Plugins/{id}/Enable` ou flag dans `/Plugins/{id}/Configuration`). PAS d'install (`POST /Plugins/Packages/Installed/{name}`). PAS d'uninstall. Best-effort minimal.
  - `prune: false` par défaut (CLAUDE.md "no automatic delete unless opt-in").
  - YAML schema (à raffiner par planner) :
    ```yaml
    jellyfin:
      main:
        base_url: http://jellyfin.selfhost.svc.cluster.local:8096
        libraries:
          enable: true
          prune: false
          items:
            - name: "Séries"
              collection_type: tvshows
              paths: ["/media/series", "/media/anime", "/media/family"]
            - name: "Films"
              collection_type: movies
              paths: ["/media/films", "/media/films-anime", "/media/films-family"]
        users:
          enable: true
          admin:
            name: "moi"
            policy:
              is_administrator: true
              enable_content_deletion: true
              enable_remote_access: true
              # ... allowlist exhaustive à expanser par planner depuis snapshots/baseline-2026-05-07/jellyfin/users.json
        server_config:
          enable: true
          ui_culture: "fr"
          metadata_country_code: "FR"
          preferred_metadata_language: "fr"
          activity_log_retention_days: 30
          log_file_retention_days: 3
          server_name: "jellyfin"
          plugin_repositories:
            - name: "Jellyfin Stable"
              url: "https://repo.jellyfin.org/files/plugin/manifest.json"
              enabled: true
        plugins:
          enable: true
          required:
            - name: "TMDb"
              # match par Id si Name ambigu : "b8715ed16c4745289ad3f72deb539cd4"
            - name: "OMDb"
            - name: "MusicBrainz"
            - name: "AudioDb"
            - name: "Studio Images"
            - name: "Kodi Sync Queue"
    ```

- **Snapshot baseline** (re-snapshot Jellyfin avant toute écriture, ADR-6 + ROADMAP discipline) :
  - `snapshots/before-phase-7-<date>/jellyfin/` via `tools/snapshot/snapshot.sh --apps jellyfin`.
  - La baseline Phase 0 `snapshots/baseline-2026-05-07/jellyfin/` reste utilisable comme référence.
  - **Anti-leak** : surface attendue Jellyfin contient probablement des secrets (API tokens dans /Devices) — appliquer le pattern Phase 6 (grep manuel + rédaction si nécessaire avant commit). Carry-forward Phase 5/6 #4 + #6 (snapshot.sh redaction defect).

**Out of scope (defer) :**

- ❌ **Multi-user declarative** — admin only per D-07-USERS-01. `emilie` reste operator-managed. Defer à un Phase 7+1 si besoin.
- ❌ **LibraryOptions exhaustif** (TypeOptions/fetchers, EnableRealtimeMonitor, ImageFetchers TMDb/OMDb order, etc.) — operator-managed via UI.
- ❌ **Server config exhaustif** (TrickplayOptions, MetadataOptions[], CodecsUsed, CastReceiverApplications, etc.) — operator-managed via Dashboard. Pas de scope HW transcoding.
- ❌ **Plugin install/uninstall** — activation-only. Defer le full lifecycle à un Phase 7+1.
- ❌ **Plugin configuration** (`.xml` files dans `/config/plugins/configurations`) — out of scope arrconf (config par fichier, pas par API).
- ❌ **Devices management** (DELETE des devices inactifs depuis `/Devices/Items?id=...`) — out of scope arrconf.
- ❌ **ApiKeys management** — opérator gère via Dashboard (la `JELLYFIN_API_KEY` arrconf est bootstrap-only).
- ❌ **Password reset** (admin ou utilisateur) — secret par user, hors scope.
- ❌ **Authentication providers** (AuthenticationProviderId, PasswordResetProviderId) — operator-managed.
- ❌ **NFR-validation par PUT-probe pré-code** (Plan 06-01 obsolete pattern) — research fait probe pre-plan via D-06-VALIDATE-01 inheritance.

</domain>

<decisions>
## Implementation Decisions

### Auth strategy (Q9)
- **D-07-AUTH-01** : `class JellyfinClient(ArrApiClient)`, override `auth_headers()`. Stratégie d'auth déterminée par PROBE LIVE en research (D-07-VALIDATE-01). Préférence : `Authorization: MediaBrowser Token="<key>", Client="arrconf", Device="arrconf", DeviceId="arrconf", Version="0.x"` (header recommandé Jellyfin 10.11+). Fallback : `?api_key=<key>` query param sur chaque request. PAS de `X-Api-Key` (Jellyfin ne supporte pas ce header — c'est spécifique aux *arr).
  - **Why** : Q9 explicitement listée dans PROJECT.md comme à résoudre Phase 7. La spec mentionne 3 options (`X-Emby-Token` / `MediaBrowser` / `?api_key=`) sans trancher. La doc Jellyfin 10.11 documente `MediaBrowser` header comme officielle. `?api_key=` est en pratique le plus simple (tous les endpoints le supportent). Le probe live tranche définitivement.
  - **How to apply** : Plan Wave 1 (research) inclut un curl manuel sur 3 endpoints représentatifs (GET /System/Info, POST /System/Configuration, POST /Library/VirtualFolders/Paths) avec les 2 stratégies. Le résultat alimente `client_base.py:JellyfinClient.auth_headers()`.

### Library reorganization
- **D-07-LIB-01** : Merged 2 libraries multi-path (vs split 6 libraries).
  - **Why** : Phase 5 a créé `/media/{anime, family, films-anime, films-family}` côté Sonarr/Radarr. Les libraries Jellyfin baseline ne pointent que sur `/media/series` (Séries) et `/media/films` (Films) — donc le contenu Anime/Family arrivant en Sonarr/Radarr depuis Phase 5 n'est PAS visible dans Jellyfin sans intervention. L'opérateur a explicitement choisi **merged multi-path** : un seul libraries "Séries" agrégeant les 3 paths TV + un seul "Films" agrégeant les 3 paths films. Le tag `arrconf-managed`/`anime`/`family` côté Sonarr/Radarr reste l'autorité de catégorisation ; Jellyfin agrège l'ensemble pour navigation simple.
  - **How to apply** : Reconciler ajoute les 2 paths manquants au library "Séries" (`/media/anime`, `/media/family`) et au library "Films" (`/media/films-anime`, `/media/films-family`). Endpoint `POST /Library/VirtualFolders/Paths?name=<lib>&path=<path>`. Idempotent : si le path est déjà présent (intersection avec PathInfos[].Path), no-op.

- **D-07-LIB-02** : Scope arrconf sur libraries = `Name + CollectionType + PathInfos` uniquement.
  - **Why** : L'opérateur a explicitement rejeté la couverture LibraryOptions (locale, fetchers, EnableRealtimeMonitor). Surface YAML minimale. Cohérent avec D-07-CONFIG-01 (allowlist exclut TypeOptions/MetadataOptions). Inconsistance baseline (Séries.PreferredMetadataLanguage="" vs Films="fr") reste operator-typed.
  - **How to apply** : Le pydantic model `Library` n'expose que `name`, `collection_type`, `paths`. Tout autre champ LibraryOptions est `Field(exclude=True)` (ne participe pas au diff/PUT). En PUT body, on n'envoie que les paths ; Jellyfin préserve les autres options.

### User management
- **D-07-USERS-01** : Admin only (`moi`) sur Policy uniquement.
  - **Why** : Mirror Seerr D-06-SCOPE-01 (minimum viable). 2 users live mais `emilie` est operator-managed et change peu. Scope `Policy` couvre l'incident-prevention (IsAdministrator, EnableContentDeletion, Block* tags) sans toucher aux UI prefs (Configuration block).
  - **How to apply** : Reconciler GET /Users → match par Name="moi" → résout en Id `82fd95db72904569b08d83271823ceaa` → PUT /Users/{id}/Policy avec le body de Policy. Le pydantic UserPolicy expose les ~30 fields de Policy en allowlist. `EnabledChannels`, `EnabledDevices`, `EnabledFolders` (listes vides en baseline = "all") gardent leur sémantique. Pas de `PUT /Users/{id}` (qui toucherait Configuration). Pas de password.

### Server config
- **D-07-CONFIG-01** : Allowlist locale + retention + ServerName + PluginRepositories.
  - **Why** : L'opérateur a explicitement choisi le minimum viable. Pas de transcoding/HW (spec.md §624 le mentionnait "in scope" mais l'opérateur a tranché contre — operator-typed). TrickplayOptions / MetadataOptions / CodecsUsed restent operator-managed.
  - **How to apply** : Pydantic model `ServerConfiguration` expose `UICulture`, `MetadataCountryCode`, `PreferredMetadataLanguage`, `ActivityLogRetentionDays`, `LogFileRetentionDays`, `ServerName`, `PluginRepositories` (liste d'objets `{Enabled, Name, Url}`). Tous les autres fields = `Field(exclude=True)`. PUT/POST body ne contient QUE l'allowlist ; Jellyfin préserve le reste (à valider par probe — si Jellyfin remplace le doc entier, il faudra GET → merge → POST). **CAVEAT** : `EnableLegacyAuthorization=true` actuel — non touché par allowlist. Si Q9 résout sur `MediaBrowser` modern header, l'allowlist pourrait inclure `EnableLegacyAuthorization=false` en future iteration.

### Plugin management
- **D-07-PLUGINS-01** : Activation-only (verify Status == Active pour 6 plugins déclarés).
  - **Why** : 5/6 plugins ont `CanUninstall=false` (bundled linuxserver image). Seul `Kodi Sync Queue` est CanUninstall=true. Install/uninstall via API ajoute peu de valeur quand les plugins sont déjà bundled. Activation-only = best-effort minimal cohérent avec spec.md §625 ("Optionnel best-effort : plugins").
  - **How to apply** : Reconciler GET /Plugins → pour chaque plugin déclaré dans YAML (par Name, fallback Id si ambigu), vérifier `Status == "Active"`. Si Disabled → endpoint d'activation à découvrir par probe (probable `POST /Plugins/{id}/Enable` ou flag dans `/Plugins/{id}/Configuration`). Pas d'install, pas d'uninstall, pas de prune.

### Credentials handling
- **D-07-CREDS-01** : Pattern Seerr D-06-CREDS-01 (NON merge_fields_for_put).
  - **Why** : Jellyfin n'a pas la structure `fields: list[FieldKV]` des *arr (download clients, indexers). Les modèles Jellyfin ont des champs top-level. `merge_fields_for_put` ne s'applique pas (spec.md §926 explicite). En pratique pour Phase 7, peu de champs masqués au sens *arr — `JELLYFIN_API_KEY` est l'auth header, pas un field reconcilié. Les ApiKeys management est out-of-scope (operator-typed).
  - **How to apply** : Pas d'introduction de helper de merge spécifique. Si un champ Jellyfin mask un secret en GET (à découvrir par probe), appliquer le pattern Seerr : `Field(exclude=True)` + merge cluster-value en pré-PUT.

### Live PUT probe (validation pre-code)
- **D-07-VALIDATE-01** : Mirror D-06-VALIDATE-01. Research fait probe live sur :
  - **Auth** : 2 stratégies (`MediaBrowser` header + `?api_key=`) sur GET /System/Info, POST /System/Configuration, POST /Library/VirtualFolders/Paths.
  - **POST vs PUT** : Confirmer la méthode pour `/System/Configuration` (Jellyfin OpenAPI dit POST mais à vérifier sur 10.11.8 live).
  - **Replace vs merge sémantique** : `POST /System/Configuration` — est-ce que le body remplace tout le doc, ou merge partiel ? Si replace : pattern GET → modify subset → POST entier.
  - **Plugin Enable endpoint** : Découvrir l'endpoint exact (`POST /Plugins/{id}/Enable` n'est pas dans la doc 10.11.8 standard, à confirmer).
  - **Excludable fields** : Carry-forward Phase 6 #9 — re-valider que les `Field(exclude=True)` choisis ne sont pas réellement REQUIRED par l'OpenAPI 10.11.8 (D-06-OPENAPI-01 leçon : la classification research-time peut être stale).
  - **Why** : Le live probe en research évite la classe d'erreur D-06-OPENAPI-01 (Pitfall 3 stale qui a déclenché le hotfix `:0.4.4`). Capture l'evidence dans `07-RESEARCH.md` § Q9 PUT probe et `evidence/q9-put-probe.txt`.
  - **How to apply** : Plan Wave 0 inclut le re-snapshot + le probe live evidence (mirror Plan 06-01). Pas de "Wave 0 = bloquant si probe fail" — recherche absorbée par /gsd-plan-phase research.

### Single-instance pattern
- **D-07-INSTANCE-01** : `jellyfin.main` (single instance, ADR-7) — pas de multi-instance.
  - **Why** : ADR-7 LOCKED pour TOUTE la stack média. Jellyfin déjà single-instance.
  - **How to apply** : `RootConfig.jellyfin: dict[str, JellyfinInstance]` avec une seule clé `main` (mirror Sonarr/Radarr/Seerr structure).

### Reconciler ordering invariant
- **D-07-ORDER-01** : Ordre d'exécution des steps reconciler — `libraries → users → server_config → plugins`.
  - **Why** : Aucun step ne dépend des autres (4 endpoints indépendants). Ordre alphabétique / "lourd au léger" pour log lisibility. Pas d'invariant D-05-ORDER-01 à reproduire (cet invariant Phase 5 portait sur l'ordre tags→download_clients pour la résolution de label→id, ce qui n'a pas d'équivalent ici).
  - **How to apply** : `JellyfinClient.reconcile()` appelle les 4 steps séquentiellement, idempotents. Un échec sur un step ne bloque pas les suivants (continue + log warning, exit code 1 si une app échoue — semantics arrconf standard).

### Claude's Discretion (downstream agents decide)
- **Plan structure** : probablement 6-8 plans (Wave 0 snapshot + probe ; Wave 1 schema + fixtures ; Wave 2 client + 4 reconcile methods ; Wave 3 arrconf.yml + values.yaml + chart-validation ; Wave 4 cluster apply via Renovate-substitute manual pattern). Planner détermine.
- **Pydantic model granularité** : combien de submodels pour `JellyfinInstance` (LibrarySection, UserSection, ServerConfigSection, PluginSection). Mirror Seerr structure recommandé.
- **Test fixture content** : Phase 5/6 fixtures pattern (snapshots/baseline sanitized → `tests/fixtures/jellyfin_<resource>.json`). Surface attendue : library_virtualfolders, users (admin slice uniquement), system_configuration, plugins.
- **PluginRepositories diff sémantique** : comparer la liste comme set (matching par Url) ou ordered list ? Probable set (semantique URL = unique).
- **`?api_key=` vs `MediaBrowser` header** : tranché en research D-07-VALIDATE-01. Si les 2 marchent, préférer le header (cleaner, pas de secret dans les query strings/logs).
- **Reconciler signature pour ressources sans Id stable** (libraries matchent par Name) — pattern label→id resolver Phase 5 réutilisable.
- **Endpoint pour Plugin Enable** — à découvrir live, multiple options possibles (`POST /Plugins/{id}/Enable`, `PUT /Plugins/{id}` with status flag, etc.).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spec / Roadmap (authoritative)
- `spec.md` § "Phase 7 — Reconciler arrconf Jellyfin" (lines 611-633) — livrables, pré-requis, critères de fin
- `spec.md` § "11. Décisions clés" — ADR-7 (single instance + tags), ADR-8/8.1 (forceSave + merge_fields_for_put hors-scope Jellyfin lines 895, 903, 926)
- `spec.md` § "Q9 — Jellyfin auth header" (line 741) — open question résolue en Phase 7 via D-07-VALIDATE-01
- `.planning/REQUIREMENTS.md` — REQ-app-coverage (Jellyfin), REQ-bootstrap-exception (JELLYFIN_API_KEY in arrconf-env Secret)
- `.planning/ROADMAP.md` § "Phase 7: Reconciler Jellyfin" — phase scope + dépendance Phase 6
- `.planning/PROJECT.md` § "Open Questions" Q9 — Jellyfin auth strategy

### Phase 6 patterns this phase inherits (closest analog)
- `.planning/phases/06-reconciler-seerr/06-CONTEXT.md` — pattern non-_ArrV3Client, manual credential preservation, single-instance match, scope minimum viable
- `.planning/phases/06-reconciler-seerr/06-RESEARCH.md` — Q1 PUT probe pattern (D-06-VALIDATE-01) à reproduire pour Q9
- `.planning/phases/06-reconciler-seerr/06-07-SUMMARY.md` — D-06-OPENAPI-01 hotfix (Pitfall 3 stale leçon — appliquer à Phase 7 exclude=True fields)
- `tools/arrconf/arrconf/reconcilers/seerr.py` — closest analog (4 PUT-based resources, single-instance match, label→id resolver pattern)
- `tools/arrconf/arrconf/resources/seerr/` — pydantic model layout pattern
- `tools/arrconf/arrconf/client_base.py:166-200` `SeerrClient(ArrApiClient)` — modèle de subclass non-_ArrV3Client

### Phase 5 patterns this phase inherits
- `.planning/phases/05-reconciler-qbittorrent-split-tv-anime-family/05-08-SUMMARY.md` — 7 deviations carried-forward (notamment #4 snapshot.sh redaction, #2 chart filesystem prereqs)
- `tools/arrconf/arrconf/reconcilers/sonarr.py` `_reconcile_series_tags` + `_reconcile_content_tags` — pattern label→id resolver (Phase 7 plugins peuvent réutiliser Id resolver pour matcher par Name)
- `charts/arr-stack/files/arrconf.yml` — Phase 5+6 a ajouté `qbittorrent`, `sonarr.main`, `radarr.main`, `seerr.main` ; Phase 7 ajoute `jellyfin.main`

### Phase 2.1 / 2.2 patterns (référence — NON applicables Phase 7 directement)
- `.planning/phases/02.1-field-merge-fix/` — `merge_fields_for_put` helper. **NON applicable Jellyfin** (spec.md §926).
- `.planning/phases/02.2-v0-1-4-forcesave-fix/` — `_ArrV3Client.put()` forceSave. **NON applicable Jellyfin** (spec.md §895). Concept "pré-save credential mask preservation" reste pertinent SI Jellyfin a un champ masqué (à découvrir par probe D-07-VALIDATE-01).

### Live cluster state to absorb
- `snapshots/baseline-2026-05-07/jellyfin/library_virtualfolders.json` — 2 libraries (Séries → /media/series ; Films → /media/films). Phase 7 ajoute paths.
- `snapshots/baseline-2026-05-07/jellyfin/users.json` — 2 users (admin "moi" Id `82fd95db72904569b08d83271823ceaa` ; emilie restricted Id `8901eacec3634d169958d11bd95d4078`). Phase 7 reconcile "moi" Policy only.
- `snapshots/baseline-2026-05-07/jellyfin/system_configuration.json` — ~50 fields baseline, allowlist Phase 7 = 7 fields (locale + retention + ServerName + PluginRepositories).
- `snapshots/baseline-2026-05-07/jellyfin/plugins.json` — 6 plugins actifs (TMDb, OMDb, MusicBrainz, AudioDb, StudioImages, KodiSyncQueue) — allowlist Phase 7.
- `snapshots/baseline-2026-05-07/jellyfin/system_info.json` + `system_info_public.json` — version Jellyfin 10.11.8 confirmée.

### Chart side
- `charts/arr-stack/files/arrconf.yml` — Phase 7 wave 4 ajoute `jellyfin.main` section
- `charts/arr-stack/values.yaml` arrconf alias — image bump path (Renovate-substitute pattern Phase 6)
- `charts/arr-stack/values.schema.json` — extend pour valider section jellyfin

### CI side (inherits Phase 5.1 chain)
- `.github/workflows/chart-lint.yml` — auto-tag chain (Phase 5.1)
- `.github/workflows/arrconf-image.yml` — repository_dispatch (Phase 5.1)
- F1/F2 backlog (chart-lint paths, metadata-action `value=` legacy push:tags fix) — deferred, reproduit Phase 6, applicable Phase 7

### Jellyfin API documentation (external)
- https://api.jellyfin.org/ — OpenAPI complet (spec.md §960)
- https://repo.jellyfin.org/files/plugin/manifest.json — plugin repository manifest (référencé dans system_configuration.json baseline)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ArrApiClient` (`tools/arrconf/arrconf/client_base.py:29`)** : base class avec `auth_headers()` overridable (line 51) — Phase 7 override pour MediaBrowser header / api_key query param. Pattern propre Seerr (`client_base.py:166`).
- **Pattern Seerr label→id resolver** (`tools/arrconf/arrconf/reconcilers/seerr.py`) — réutilisable pour matcher libraries par Name → ItemId, users par Name → Id, plugins par Name → Id.
- **`differ.Action` enum + reconcile loop** (`tools/arrconf/arrconf/differ.py`) — pattern générique `GET list → match by key → compute Action (add/update/no_op/delete)` applicable aux 4 ressources Phase 7. Libraries match par Name ; users par Name ; plugins par Name (fallback Id).
- **`Field(exclude=True)` allowlist pattern** — utilisé Seerr (`id` field), réutilisable pour exclure les ~43 fields de `system_configuration.json` qu'on ne touche pas.
- **Audit event vocabulary** (`merge_field_omitted_credential`, `apply_complete`, etc.) — `tools/arrconf/arrconf/_shared.py` — Phase 7 émet `apply_complete` per reconcile step + warnings spécifiques (ex: `library_path_already_present`).

### Established Patterns
- **Single-instance + dict-by-name** : `RootConfig.jellyfin: dict[str, JellyfinInstance]` avec une seule clé `main` (mirror sonarr/radarr/prowlarr/seerr).
- **`prune: false` default** : opt-in par section (REQ-prune-opt-in). Phase 7 reconcile libraries/users/plugins avec prune=false hardcoded à minima (D-07-USERS-01 hardcode pas-de-suppression).
- **Scope-violation guard pattern** (`tools/arrconf/arrconf/reconcilers/_shared.py` + frontière configarr) — applicable Phase 7 SI on découvre des endpoints Jellyfin qu'on veut explicitement bloquer (ex: ApiKeys management). Pas obligatoire en Phase 7.
- **Reconciler step ordering invariant** : Phase 5 introduit D-05-ORDER-01 pour Sonarr/Radarr ; Phase 7 D-07-ORDER-01 reproduit le pattern (ordre stable, testé).
- **Test pattern via respx** : `tools/arrconf/tests/test_<app>.py` + `tests/fixtures/<app>_<resource>.json`. Coverage cible ≥70% sur `reconcilers/jellyfin.py`.

### Integration Points
- **`tools/arrconf/arrconf/__main__.py`** : ajouter `--apps jellyfin` au routing CLI (mirror Phase 6 D-06-CHART-ARGS-01 — ne pas oublier `chart/files/arrconf.yml` `args:` + cluster `--apps` list).
- **`tools/arrconf/arrconf/diff_cmd.py`** : ajouter routing `jellyfin` → `JellyfinClient.dump()` + `diff()`.
- **`tools/arrconf/arrconf/config.py` `RootConfig`** : ajouter `jellyfin: dict[str, JellyfinInstance] = {}` champ + JSON Schema regen.
- **`schemas/arrconf-schema.json`** : auto-régénéré par `arrconf schema-gen` ; CI bloque si manuel/oubli (REQ-yaml-autocomplete).
- **`charts/arr-stack/files/arrconf.yml`** : ajout section `jellyfin.main` avec les 4 sub-sections (libraries/users/server_config/plugins).
- **`charts/arr-stack/values.yaml` arrconf args** : ajouter `jellyfin` au `--apps` arg list (sinon D-06-CHART-ARGS-01 reproduit — l'app ne sera pas reconciled même si présente en YAML).
- **`charts/arr-stack/values.schema.json`** : extend pour valider la nouvelle section jellyfin.
- **`tests/test_config.py`** : extend pour valider que RootConfig parse une section jellyfin valide.
- **`tests/test_scope_violation.py`** : potentielle extension si on bloque explicitement des endpoints Jellyfin (ApiKeys, etc.) — Claude's discretion.

</code_context>

<specifics>
## Specific Ideas

- **Library paths déjà décidés** : `[/media/series, /media/anime, /media/family]` pour Séries ; `[/media/films, /media/films-anime, /media/films-family]` pour Films. Cohérent avec D-05-PATHS-01 Phase 5.
- **Allowlist server config = 7 fields exacts** : `UICulture`, `MetadataCountryCode`, `PreferredMetadataLanguage`, `ActivityLogRetentionDays`, `LogFileRetentionDays`, `ServerName`, `PluginRepositories`.
- **Allowlist plugins = 6 noms exacts** (mirror baseline): TMDb, OMDb, MusicBrainz, AudioDb, Studio Images, Kodi Sync Queue.
- **Admin user = "moi"** (`Id=82fd95db72904569b08d83271823ceaa`). `emilie` reste operator-managed.
- **JELLYFIN_API_KEY** déjà bootstrappé côté Operator (REQ-bootstrap-exception) ; doit être dans sealed-secret `arrconf-env` côté my-kluster avant Wave 4 cluster apply. Vérifier l'existence avant Plan Wave 0 (carry-forward leçon Phase 5/6).
- **Préférence auth** : `Authorization: MediaBrowser` header (cleaner que `?api_key=` en logs cluster) — si probe confirme.

</specifics>

<deferred>
## Deferred Ideas

- **Multi-user Jellyfin declarative** (emilie + futurs users) — D-07-USERS-01 scope expansion, defer à Phase 7+1 si besoin.
- **LibraryOptions exhaustif** (TypeOptions fetchers TMDb/OMDb order, EnableRealtimeMonitor, PreferredMetadataLanguage par library) — defer à Phase 7+1.
- **Server config exhaustif** (TrickplayOptions, MetadataOptions[] par MediaType, CodecsUsed, CorsHosts) — operator-managed indéfiniment.
- **Plugin full lifecycle** (install via `POST /Plugins/Packages/Installed/{name}`, uninstall via `DELETE /Plugins/{id}`, prune opt-in) — defer à Phase 7+1.
- **HW transcoding declarative** (TrickplayOptions.EnableHwAcceleration, codec acceleration per node) — spec.md §624 le mentionnait in-scope ; l'opérateur a tranché contre, defer indéfiniment.
- **Plugin configuration .xml files** — fichiers `/config/plugins/configurations/*.xml`, hors scope arrconf (config par fichier pas par API). Pourrait être géré par configarr ultérieurement si pertinent.
- **Devices cleanup** (DELETE devices inactifs depuis /Devices/Items) — operator-managed via Dashboard.
- **ApiKeys management arrconf** — operator-managed, defer indéfiniment.
- **Bidirectional Seerr ↔ Jellyfin user sync** (carry-forward Phase 6 deferred) — encore differé Phase 7 (admin-only scope).
- **Phase 5 follow-ups carry-forward** : items #1 (download_client POST credentials), #2 (chart initContainer filesystem prereqs), #3-#8 — non bloquants pour Phase 7 mais à surveiller. #4 (snapshot.sh redaction) particulièrement pertinent — Jellyfin baseline a déjà des secrets dans /Devices/Items (Id b64-encoded contient user agent + token).
- **Q9 `X-Emby-Token` legacy header** — defer ; D-07-AUTH-01 préfère MediaBrowser header. Fallback `?api_key=` query param suffit pour le reste.
- **`EnableLegacyAuthorization=false` toggle** — actuellement `true` en baseline ; si MediaBrowser header confirmé fonctionnel par probe, l'allowlist server_config pourrait inclure ce flag en future iteration pour disable l'auth legacy. Defer Phase 7+1.

</deferred>

---

*Phase: 7-reconciler-jellyfin*
*Context gathered: 2026-05-17*
