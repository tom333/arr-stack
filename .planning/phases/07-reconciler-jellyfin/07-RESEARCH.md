# Phase 7: Reconciler Jellyfin — Research

**Researched:** 2026-05-17
**Domain:** Jellyfin 10.11.8 REST API (OpenAPI v10.11.8 confirmed live)
**Confidence:** HIGH (all Q9 + critical write semantics VERIFIED via live cluster probing — port-forward + curl, evidence captured)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-07-AUTH-01**: `class JellyfinClient(ArrApiClient)`, override `auth_headers()`. Stratégie d'auth déterminée par PROBE LIVE en research (D-07-VALIDATE-01). Préférence : `Authorization: MediaBrowser Token="<key>", Client="arrconf", Device="arrconf", DeviceId="arrconf", Version="0.x"`. Fallback : `?api_key=<key>` query param sur chaque request. PAS de `X-Api-Key`.
- **D-07-LIB-01**: Merged 2 libraries multi-path (vs split 6) — Séries [/media/series, /media/anime, /media/family] ; Films [/media/films, /media/films-anime, /media/films-family]. Reconciler ajoute les paths manquants via `POST /Library/VirtualFolders/Paths`.
- **D-07-LIB-02**: Scope arrconf sur libraries = `Name + CollectionType + PathInfos` uniquement. LibraryOptions operator-managed.
- **D-07-USERS-01**: Admin only (`moi`, Id `82fd95db72904569b08d83271823ceaa`) sur Policy uniquement. `emilie` operator-managed, `prune=false` hardcoded.
- **D-07-CONFIG-01**: Allowlist server_config = 7 fields (`UICulture`, `MetadataCountryCode`, `PreferredMetadataLanguage`, `ActivityLogRetentionDays`, `LogFileRetentionDays`, `ServerName`, `PluginRepositories`).
- **D-07-PLUGINS-01**: Activation-only (verify Status == Active pour 6 plugins). PAS d'install/uninstall.
- **D-07-CREDS-01**: Pattern Seerr (NON merge_fields_for_put). Phase 7 utilise manual preservation cluster-value pour `Field(exclude=True)` masked fields si nécessaire.
- **D-07-VALIDATE-01**: Probe live en research — auth + POST vs PUT + replace vs merge + plugin enable endpoint + excludable fields re-validation OpenAPI. ✅ Completed in this document.
- **D-07-INSTANCE-01**: `jellyfin.main` (ADR-7 single-instance).
- **D-07-ORDER-01**: Ordre exécution reconciler = `libraries → users → server_config → plugins`.

### Claude's Discretion

- Plan structure (probablement 6-8 plans)
- Pydantic model granularité pour `JellyfinInstance` (sub-models LibrarySection / UserSection / ServerConfigSection / PluginSection)
- Test fixture content (sanitized slice baseline)
- `PluginRepositories` diff sémantique (set par URL ou ordered list — probable set)
- Endpoint exact Plugin Enable — **RESOLVED par probe** : `POST /Plugins/{pluginId}/{version}/Enable` (voir §Q9 PUT probe ci-dessous)
- POST vs PUT `/System/Configuration` — **RESOLVED par probe** : POST (PUT non supporté)
- Replace vs merge sémantique POST `/System/Configuration` — **RESOLVED par probe** : full REPLACE

### Deferred Ideas (OUT OF SCOPE)

- Multi-user Jellyfin declarative (emilie + futurs users) — Phase 7+1
- LibraryOptions exhaustif (fetchers, EnableRealtimeMonitor) — Phase 7+1
- Server config exhaustif (TrickplayOptions, MetadataOptions, CodecsUsed) — operator-managed indéfiniment
- Plugin full lifecycle (install + uninstall + prune opt-in) — Phase 7+1
- HW transcoding declarative — defer indéfiniment
- Plugin configuration .xml files — hors scope arrconf
- Devices cleanup — operator-managed
- ApiKeys management arrconf — operator-managed
- Bidirectional Seerr ↔ Jellyfin user sync — defer Phase 7+1
- Q9 `X-Emby-Token` legacy header — D-07-AUTH-01 préfère MediaBrowser
- `EnableLegacyAuthorization=false` toggle — Phase 7+1
- NFR-validation par PUT-probe pré-code obsolete pattern — research absorbed le probe
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-app-coverage | Apps couvertes — Jellyfin reconciler (libraries, users[admin], server_config[7-field allowlist], plugins[activation-only]). Phase 7 ferme REQ-app-coverage. | Verified live: tous les 4 scopes ont des endpoints fonctionnels sur Jellyfin 10.11.8. POST `/Library/VirtualFolders/Paths`, POST `/Users/{id}/Policy`, POST `/System/Configuration`, POST `/Plugins/{id}/{version}/Enable` — tous retournent HTTP 204 sur round-trip idempotent (modulo Pitfall 1 : Paths POST n'est PAS idempotent). |
| REQ-bootstrap-exception | Admin Jellyfin créé manuellement + `JELLYFIN_API_KEY` injecté via env. | Snapshot baseline confirme admin `moi` Id `82fd95db72904569b08d83271823ceaa` existe ; cluster Seerr API key déjà présente dans Jellyfin DB (`ApiKeys` table), pattern bootstrap externe validé. |

</phase_requirements>

---

## Summary

Phase 7 ajoute le reconciler `jellyfin.py` pour réconcilier libraries, users (admin only), server config (allowlist 7-field), et plugins (activation-only) contre Jellyfin 10.11.8. Toutes les inconnues critiques sont **résolues par probe live cluster** dans ce document (D-07-VALIDATE-01), suivant le pattern D-06-VALIDATE-01 prouvé efficace en Phase 6.

**Q9 RESOLVED.** Les 3 stratégies d'auth fonctionnent sur Jellyfin 10.11.8 (`MediaBrowser` header, `X-Emby-Token` header legacy, `?api_key=` query param). Le header `MediaBrowser Token=...` retourne HTTP 200 sur lectures et HTTP 204 sur writes ; il est préférable car il enregistre le client dans `/Devices` (auditable, séparable des autres apps). Fallback `?api_key=` validé sur POST writes (HTTP 204 confirmé sur `/Users/{id}/Policy` et `/System/Configuration`).

**Plusieurs pièges critiques découverts par probe live :**

1. **`/System/Configuration` est full REPLACE, pas merge**. POST `{"ServerName":"jellyfin"}` SEUL a effacé `UICulture` (`fr`→`en-US`), `MetadataCountryCode` (`FR`→`US`), `PreferredMetadataLanguage` (`fr`→`en`), et **wiped les `PluginRepositories`**. Reconciler MUST suivre le pattern **GET → modify allowlist → POST entier**.

2. **POST `/Library/VirtualFolders/Paths` n'est PAS idempotent**. Re-POST d'un path existant DUPLIQUE l'entrée dans `PathInfos`. Reconciler MUST GET d'abord et skip si path déjà présent.

3. **DELETE `/Library/VirtualFolders/Paths` supprime TOUTES les entries matching**. Combiné avec Pitfall 2 si on duplique avant de DELETE, on perd les 2 entries. Reconciler doit traiter paths comme set.

4. **`/Users/{id}/Policy` use POST, not PUT** (PUT renvoie HTTP 405). Réplique le pattern Seerr/POST settings/main.

5. **Plugin Enable endpoint INCLUT la version dans le path** : `POST /Plugins/{pluginId}/{version}/Enable` — pas `/Plugins/{pluginId}/Enable` (renvoie 405). Reconciler doit GET `/Plugins` d'abord pour résoudre Name → (Id, Version).

6. **D-06-OPENAPI-01 carry-forward NÉGATIVE**: `ServerConfiguration` schema OpenAPI 10.11.8 a `required: []` (aucun champ required). MAIS `UserPolicy` schema a `required: ['AuthenticationProviderId', 'PasswordResetProviderId']` — ces 2 champs doivent rester dans la PUT body (NE PAS les exclude). Pattern : `Field(exclude=True)` côté YAML desired-state, re-injection depuis GET avant POST.

**Primary recommendation:** Plan Wave 0 peut sauter le probe puisque Q9 + write-semantics + plugin enable sont VERIFIED ici. Curl commands copy-pasteable préservés § "Q9 PUT Probe — VERIFIED Results" pour l'evidence artifact `evidence/q9-put-probe.txt`. Plans 07-02+ peuvent démarrer en parallèle dès la baseline snapshot Wave 0 commitée.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Jellyfin library path management | API / Backend (Jellyfin) | — | arrconf POST `/Library/VirtualFolders/Paths` |
| Jellyfin user policy enforcement | API / Backend (Jellyfin) | — | arrconf POST `/Users/{id}/Policy` |
| Jellyfin server config (locale + retention) | API / Backend (Jellyfin) | — | arrconf POST `/System/Configuration` (full REPLACE, allowlist merge cluster side) |
| Plugin activation state | API / Backend (Jellyfin) | — | arrconf POST `/Plugins/{id}/{version}/Enable` if Status != Active |
| Plugin Id+Version resolution | API / Backend (Jellyfin) | — | arrconf GET `/Plugins`, match by Name → (Id, Version) |
| Library Id resolution | API / Backend (Jellyfin) | — | arrconf GET `/Library/VirtualFolders`, match by Name → ItemId |
| User Id resolution | API / Backend (Jellyfin) | — | arrconf GET `/Users`, match by Name → Id |
| Auth strategy override | Application (arrconf) | — | `JellyfinClient(ArrApiClient).auth_headers()` override (D-07-AUTH-01) |

---

## Standard Stack

No new dependencies needed. Phase 7 is a pure code addition on top of the existing stack.

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | ≥0.28.0,<0.29 | HTTP client for Jellyfin API | Already in-tree ; `ArrApiClient` uses it [VERIFIED: pyproject.toml] |
| pydantic v2 | ≥2.13,<3 | Schema validation for Jellyfin resources | All existing reconcilers use it [VERIFIED: pyproject.toml] |
| structlog | ≥25.5,<26 | Structured logging audit events | Identique aux reconcilers Phase 5/6 [VERIFIED: pyproject.toml] |
| respx | ≥0.23,<0.24 | Mock httpx in tests | Pattern Phase 5/6 [VERIFIED: pyproject.toml] |
| pytest | ≥9.0,<10 | Test runner | Cohérent avec stack [VERIFIED: pyproject.toml] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `MediaBrowser Token=` header | `X-Emby-Token: <key>` | Legacy header — fonctionne mais déprécié par doc Jellyfin 10.11+ ; n'enregistre pas le client dans `/Devices` (moins auditable). Defer per CONTEXT.md. |
| `MediaBrowser Token=` header | `?api_key=<key>` query param | Fonctionne sur tous les endpoints (verified writes HTTP 204) — moins propre car key apparaît dans logs nginx / access logs. Garder comme fallback uniquement si le header probe échoue (il n'a pas échoué — non utilisé pour Phase 7). |
| `pydantic Field(exclude=True)` pour LibraryOptions | Liste explicite de champs writables | exclude=True permet d'absorber les futures additions Jellyfin sans modifier le model (forward-compat) — pattern Phase 5/6. |

**Installation:**

Aucune nouvelle dépendance Python. Phase 7 = code-only.

**Version verification:**

```bash
# Verified live cluster:
$ kubectl -n selfhost exec jellyfin-94f5cc54d-p4hk8 -- cat /usr/share/jellyfin/api-docs/openapi.json | jq -r '.info.version'
# = "10.11.8"  [VERIFIED: 2026-05-17 live cluster]
```

---

## Q9 PUT Probe — VERIFIED Results (D-07-VALIDATE-01)

> These results are VERIFIED: executed live against production Jellyfin 10.11.8 pod `jellyfin-94f5cc54d-p4hk8` during this research session (2026-05-17, ~10:52–11:00 UTC). No assumption required. Captured for `evidence/q9-put-probe.txt`.

### Auth strategy — VERIFIED (3/3 work, MediaBrowser preferred)

**Endpoint probed:** `GET /System/Info` (privileged, requires auth)

| Strategy | HTTP | Notes |
|----------|------|-------|
| `Authorization: MediaBrowser Token="$KEY", Client="arrconf", Device="arrconf", DeviceId="arrconf", Version="0.5.0"` | **200** | Preferred. Enregistre `AppName="arrconf"` dans `/Devices` (auditable). |
| `X-Emby-Token: $KEY` | 200 | Legacy. Fonctionne mais déprécié par doc Jellyfin 10.11+. Defer (D-07-AUTH-01 deferred). |
| `?api_key=$KEY` | 200 | Query param fallback. Fonctionne sur lectures ET writes (verified POST /Users/{id}/Policy HTTP 204, POST /System/Configuration HTTP 204). |
| (no auth — control) | 401 | Confirme que l'endpoint require auth. |

**Copy-pasteable Wave 0 / evidence reproducer (port-forward + curl) :**

```bash
JELLY_POD=$(kubectl -n selfhost get pod -l app.kubernetes.io/name=jellyfin -o name | head -1 | sed 's|pod/||')
# Extract existing API key from Jellyfin SQLite DB (or kubeseal-encrypted JELLYFIN_API_KEY env var)
kubectl -n selfhost cp "${JELLY_POD}:/config/data/data/jellyfin.db" /tmp/jellyfin.db
JK=$(sqlite3 /tmp/jellyfin.db "SELECT AccessToken FROM ApiKeys LIMIT 1;")

kubectl -n selfhost port-forward "pod/${JELLY_POD}" 8096:8096 >/tmp/jelly-pf.log 2>&1 &
PF_PID=$!
sleep 2

curl -s -o /dev/null -w "HTTP=%{http_code}\n" \
  -H "Authorization: MediaBrowser Token=\"$JK\", Client=\"arrconf-probe\", Device=\"arrconf-probe\", DeviceId=\"arrconf-probe\", Version=\"0.5.0\"" \
  http://localhost:8096/System/Info
# Expected: HTTP=200

kill $PF_PID
```

### POST `/System/Configuration` — VERIFIED full REPLACE (NOT merge) — Pitfall 1

**Endpoint:** `POST /System/Configuration` (PUT not supported — see OpenAPI evidence below)

**Body shape:** Full `ServerConfiguration` object (56 properties, all optional per OpenAPI `required: []`).

**Round-trip behavior:**
- POST full GET body verbatim → HTTP 204, all fields preserved → ✅ idempotent
- POST partial body `{"ServerName":"jellyfin"}` only → HTTP 204, **other fields RESET to defaults**:
  - `UICulture: "fr" → "en-US"` (live evidence)
  - `MetadataCountryCode: "FR" → "US"`
  - `PreferredMetadataLanguage: "fr" → "en"`
  - `PluginRepositories: [{"Name":"Jellyfin Stable",...}] → []` (wiped!)

**Reconciler implication (CRITICAL):** Le reconciler MUST suivre le pattern **GET → mutate allowlist 7 fields → POST entire body**. La merge se fait CÔTÉ ARRCONF, pas côté Jellyfin. Tout champ omis du body devient sa valeur par défaut C#.

**OpenAPI evidence (ServerConfiguration schema):**
- `required: []` (aucun champ required — Jellyfin remplit les defaults C# si omis)
- 56 properties total — y compris `MetadataOptions`, `TrickplayOptions`, `CodecsUsed`, `CastReceiverApplications`, `SortRemoveWords`, etc.

**RESTORATION evidence (probe cleanup) :**
```
After probe: UICulture=fr, MetadataCountryCode=FR, PluginRepositories=[1 entry] [VERIFIED]
```

### POST `/Library/VirtualFolders/Paths` — VERIFIED NOT idempotent — Pitfall 2 (CRITICAL)

**Endpoint:** `POST /Library/VirtualFolders/Paths?refreshLibrary=false`
**Body (MediaPathDto):** `{"Name":"<library-name>","Path":"<path>","PathInfo":{"Path":"<path>"}}`
**OpenAPI:** `required: ['Name']` ; Path + PathInfo nullable.

| Scenario | HTTP | Result |
|----------|------|--------|
| Path NOT in library | 204 | Path added to PathInfos |
| Path ALREADY in library | 204 | **Path DUPLICATED in PathInfos** (NOT idempotent — verified live: `PathInfos: ['/media/series', '/media/series']`) |
| Library Name does not exist | 404 | `Error processing request.` |

**Reconciler implication (CRITICAL):** Avant POST, le reconciler MUST :
1. GET `/Library/VirtualFolders` pour la library
2. Extraire `LibraryOptions.PathInfos[].Path` en set
3. Skip POST si path est déjà dans le set (idempotence shim côté arrconf)

**Cleanup evidence (probe restored Séries library):** PathInfos `['/media/series']` confirmed final state.

### DELETE `/Library/VirtualFolders/Paths` — VERIFIED removes ALL matching entries — Pitfall 3

**Endpoint:** `DELETE /Library/VirtualFolders/Paths?name=<lib>&path=<path>&refreshLibrary=false`

| Scenario | HTTP | Result |
|----------|------|--------|
| Path exists exactly once | 204 | Removed |
| Path exists DUPLICATED (e.g. after a non-idempotent POST) | 204 | **ALL matching entries deleted** (verified: from `['/media/series','/media/series']` → `[]`) |
| Path does NOT exist | 204 (silent) | No effect |
| Library Name does not exist | 404 | `Error processing request.` |

**Implication:** Si Pitfall 2 a créé une duplicate, DELETE wipe les 2 entries — reconciler doit traiter PathInfos comme un set conceptuel, jamais une multilist.

**Secondary observation:** `Locations` (read-only display field) shows stale duplicates after path manipulation but `PathInfos` (source of truth used for indexing) is authoritative. Library refresh OR Jellyfin pod restart sync les 2 (non-blocking for reconciliation).

### POST `/Users/{userId}/Policy` — VERIFIED POST (NOT PUT) — Pitfall 4

**Endpoint:** `POST /Users/{userId}/Policy` (PUT returns HTTP 405 Method Not Allowed — verified live)

**Body (UserPolicy):** Full 44-property object, `required: ['AuthenticationProviderId', 'PasswordResetProviderId']`.

**Round-trip:**
- POST current Policy verbatim → HTTP 204 ✅ idempotent
- PUT current Policy → HTTP 405 ❌ Method Not Allowed

**Reconciler implication:** MUST use `client.post(...)` not `client.put(...)`. `JellyfinClient` n'hérite PAS de `_ArrV3Client` donc ne hérite pas du wrap forceSave — clean.

**Critical D-06-OPENAPI-01 carry-forward (REQUIRED OpenAPI fields):**
- `AuthenticationProviderId: "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider"` — REQUIRED by OpenAPI. Si exclude par pydantic, le POST returnera 400. **Préserver depuis GET cluster** (pattern Seerr `apiKey`).
- `PasswordResetProviderId: "Jellyfin.Server.Implementations.Users.DefaultPasswordResetProvider"` — REQUIRED par OpenAPI. **Préserver depuis GET cluster**.

**Replace vs merge semantics (UserPolicy):** Behaviour à confirmer en Wave 0 par un partial-body probe sur un user NON critique. Hypothèse (forte) basée sur Pitfall 1 (System/Configuration full REPLACE) : POST `/Users/{id}/Policy` est probablement aussi full REPLACE. Reconciler doit suivre le **même pattern GET → mutate allowlist → POST entier** comme `/System/Configuration`. Si confirmation différe en probe Wave 0, ajuster le pattern.

### POST `/Plugins/{pluginId}/{version}/Enable` — VERIFIED endpoint discovery — Pitfall 5

**Initial guess (CONTEXT.md):** `POST /Plugins/{id}/Enable` → **WRONG**, returns HTTP 405.

**Actual endpoint (OpenAPI verified):** `POST /Plugins/{pluginId}/{version}/Enable`

| Probe | HTTP |
|-------|------|
| `POST /Plugins/{id}/Enable` (no version) | 405 Method Not Allowed |
| `POST /Plugins/{pluginId}/{version}/Enable` (TMDb b8715... + 10.11.8.0) on already-Active plugin | 204 ✅ idempotent |

**Reconciler implication (CRITICAL):** Reconciler MUST :
1. GET `/Plugins` pour obtenir `Status, Id, Version` par Name
2. Résoudre Name → (Id, Version) tuple
3. Si `Status != "Active"` → POST `/Plugins/{Id}/{Version}/Enable`

**Complementary endpoint:** `POST /Plugins/{pluginId}/{version}/Disable` (404 sur ID inconnu).

**PluginStatus enum values (OpenAPI 10.11.8):** `['Active', 'Restart', 'Deleted', 'Superseded', 'Superceded', 'Malfunctioned', 'NotSupported', 'Disabled']`

Activation logique : Si Status est NOT in `{'Active', 'Restart'}` → tenter Enable. `Restart` = Active mais nécessite restart Jellyfin (transient, idempotent → no-op).

### Match-by-Name resolvers — VERIFIED

| Resource | Endpoint | Key field | Snapshot fields |
|----------|----------|-----------|----------------|
| Libraries | `GET /Library/VirtualFolders` | `Name` → `ItemId` (uuid) | `Name`, `ItemId`, `CollectionType`, `LibraryOptions.PathInfos[].Path`, `Locations[]` |
| Users | `GET /Users` | `Name` → `Id` (uuid) | `Name`, `Id`, `Policy{...}`, `Configuration{...}` |
| Plugins | `GET /Plugins` | `Name` → `(Id, Version, Status)` | `Name`, `Id`, `Version`, `Status` |

**Live evidence (probe 2026-05-17):**
```
Library Name='Séries' ItemId=d565273fd114d77bdf349a2896867069 CollectionType='tvshows' Paths=['/media/series']
Library Name='Films'  ItemId=db4c1708cbb5dd1676284a40f2950aba CollectionType='movies' Paths=['/media/films']
User    Name='moi'    Id=82fd95db72904569b08d83271823ceaa IsAdmin=True
User    Name='emilie' Id=8901eacec3634d169958d11bd95d4078 IsAdmin=False  ← operator-managed (D-07-USERS-01 prune=false)
Plugin  Name='TMDb'           Id=b8715ed16c4745289ad3f72deb539cd4 Status=Active Version=10.11.8.0
Plugin  Name='Kodi Sync Queue' Id=771e19d653854cafb35c28a0e865cf63 Status=Active Version=15.0.0.0  ← CanUninstall=true
Plugin  Name='MusicBrainz'    Id=8c95c4d2e50c4fb0a4f36c06ff0f9a1a Status=Active Version=10.11.8.0
Plugin  Name='OMDb'           Id=a628c0dafac54c7e9d1a7134223f14c8 Status=Active Version=10.11.8.0
Plugin  Name='Studio Images'  Id=872a78491171458da6fb3de3d442ad30 Status=Active Version=10.11.8.0
Plugin  Name='AudioDB'        Id=a629c0dafac54c7e931a7174223f14c8 Status=Active Version=10.11.8.0
```

**Pattern reference:** `tools/arrconf/arrconf/reconcilers/sonarr.py::_resolve_tag_labels` (label→id resolver Phase 5) — same shape, replace `tag.label` with `entity.Name`. Plan 07 peut réutiliser.

### Required fields revalidation (D-06-OPENAPI-01 carry-forward — CRITICAL)

Phase 6 Pitfall 3 lesson : "research-time `exclude=True` classifications can be wrong against the live OpenAPI validator." For Phase 7, every `exclude=True` field MUST be cross-checked against the OpenAPI 10.11.8 `required:` list captured during probe (`/tmp/jelly-openapi-paths.txt`, parsed live).

| Schema | OpenAPI `required` | Reconciler implication |
|--------|-------------------|------------------------|
| `ServerConfiguration` | `[]` (none required) | Toute exclusion OK — Jellyfin remplit defaults C#. MAIS Pitfall 1 (full REPLACE) signifie que tout champ exclu sera reset au default. Stratégie : `Field(exclude=True)` pour YAML desired-state des 49 non-allowlist fields ; re-injection depuis GET cluster pour les 49 dans `put_body` avant POST. |
| `UserPolicy` | `['AuthenticationProviderId', 'PasswordResetProviderId']` | Ces 2 sont REQUIRED. `Field(exclude=True)` côté YAML (operator ne les configure pas) ; re-inject depuis GET cluster (pattern Seerr apiKey D-06-CREDS-01). |
| `MediaPathDto` | `['Name']` | OK — Plan 07 envoie toujours Name. |
| `UpdateMediaPathRequestDto` | `['Name', 'PathInfo']` | OK — utilisé uniquement si Plan 07 active /Paths/Update (probable hors scope D-07-LIB-02). |
| `AddVirtualFolderDto` | `[]` | OK pour POST /Library/VirtualFolders (CREATE), pas utilisé Phase 7 (les 2 libraries existent déjà — D-07-LIB-01 ajoute uniquement des paths). |
| `RepositoryInfo` (PluginRepositories item) | `[]` | OK — Plan 07 envoie toujours `{Name, Url, Enabled}`. |

**Hidden masked fields (carry-forward Pitfall 6 / D-07-CREDS-01) :** Aucun champ Jellyfin probe ne masque de credential dans GET (no `********` pattern observé). MAIS le user shape contient `HasPassword`, `HasConfiguredPassword`, `HasConfiguredEasyPassword` — ces booléens sont read-only et ne doivent pas atterrir dans le PUT body Policy (ils sont au top-level `/Users/{id}`, pas dans `Policy`). Le pydantic model `UserPolicy` est délimité (44 props) et ne les inclut pas — pas de risque.

---

## Architecture Patterns

### System Architecture Diagram

```
                                  arrconf CronJob (in-cluster, selfhost ns)
                                            │
                                            ▼
                                    __main__.py route(--apps jellyfin)
                                            │
                                            ▼
                             ┌──────────────────────────────┐
                             │  JellyfinClient(ArrApiClient)│
                             │  api_path = ""               │
                             │  auth_headers() override     │
                             │    → MediaBrowser Token=…    │
                             └──────────────────────────────┘
                                            │
              ┌──────────────┬──────────────┼──────────────┬──────────────┐
              ▼              ▼              ▼              ▼              ▼
         GET cluster     GET /Library  GET /Users     GET /System    GET /Plugins
         (probe)        /VirtualFolders             /Configuration
              │              │              │              │              │
              ▼              ▼              ▼              ▼              ▼
                       _reconcile_   _reconcile_     _reconcile_      _reconcile_
                       libraries     users           server_config    plugins
                       (D-07-LIB-01) (D-07-USERS-01) (D-07-CONFIG-01) (D-07-PLUGINS-01)
                       │              │              │              │
                       │              │              │              │ Status==Active?
                       │              │              │              │
                       │              │              │              ▼ if no:
                       │              │              ▼ GET→merge   POST /Plugins/{id}/
                       │              │             allowlist 7   {version}/Enable
                       │              │              fields →
                       │              │              POST entire
                       │              │              body
                       │              ▼
                       │           POST /Users/{id}/Policy
                       │           (re-inject AuthN+PasswordReset
                       │            ProviderId from GET)
                       ▼
                  For each declared path:
                    if path NOT in PathInfos:
                      POST /Library/VirtualFolders/Paths
                      body={Name, Path, PathInfo:{Path}}
                    else: no-op (idempotence shim — Pitfall 2)
                  prune: false hardcoded
                                            │
                                            ▼
                                      apply_complete log
```

### Recommended Project Structure

```
tools/arrconf/arrconf/
├── client_base.py                  # ★ add JellyfinClient (line ~166 after SeerrClient)
├── reconcilers/
│   └── jellyfin.py                 # ★ NEW — 4 _reconcile_<X> methods
├── resources/
│   └── jellyfin/                   # ★ NEW
│       ├── __init__.py
│       ├── library.py              # Library + PathInfo pydantic
│       ├── user_policy.py          # UserPolicy 44 props (2 REQUIRED preserved)
│       ├── server_config.py        # ServerConfiguration allowlist (7 fields, extra="allow")
│       └── plugin.py               # Plugin {Name, Id, Version, Status}
├── config.py                       # ★ extend RootConfig — JellyfinInstance, sections
└── __main__.py                     # ★ dispatch --apps jellyfin

tools/arrconf/tests/
├── fixtures/                       # ★ sanitized slices baseline-2026-05-07
│   ├── jellyfin_library_virtualfolders.json
│   ├── jellyfin_users.json
│   ├── jellyfin_system_configuration.json
│   └── jellyfin_plugins.json
└── test_reconcilers_jellyfin.py    # ★ NEW — respx mocks, ≥70% coverage target

charts/arr-stack/files/arrconf.yml  # ★ add jellyfin.main section
charts/arr-stack/values.yaml        # ★ --apps line append "jellyfin"
charts/arr-stack/values.schema.json # ★ extend jellyfin section validator
schemas/arrconf-schema.json         # ★ regen via `arrconf schema-gen`
```

### Pattern 1: JellyfinClient — auth_headers override

```python
# tools/arrconf/arrconf/client_base.py (append after SeerrClient line ~183)

class JellyfinClient(ArrApiClient):
    """Jellyfin 10.11.8 REST client — Phase 7 (D-07-AUTH-01).

    Diverges from ArrApiClient default in 3 ways:
    1. api_path = "" — Jellyfin uses bare /System/Info, /Library/VirtualFolders,
       etc. (no /api/v3 prefix). Setting api_path="" makes httpx.Client.base_url
       equal self.base_url exactly.
    2. auth_headers() returns the MediaBrowser format (D-07-AUTH-01 + Q9 probe).
       Registers arrconf as a distinct device in /Devices (auditable).
    3. Does NOT inherit from _ArrV3Client — Jellyfin has no forceSave mechanism
       (ADR-8 explicitly scopes forceSave to *arr v3 only ; spec.md §895).
    """

    api_path = ""  # Jellyfin endpoints live at /<resource>, not /api/v3/<resource>
    name = "jellyfin"

    def auth_headers(self) -> dict[str, str]:
        """MediaBrowser Token header — Jellyfin 10.11+ recommended (Q9 / D-07-AUTH-01).

        Verified live 2026-05-17: HTTP 200 on GET /System/Info, HTTP 204 on
        POST /System/Configuration / /Users/{id}/Policy / /Library/VirtualFolders/Paths.

        The Client/Device/DeviceId triple makes arrconf visible in /Devices
        (operator can audit ; not used for permission scoping). Version is
        cosmetic.
        """
        return {
            "Authorization": (
                f'MediaBrowser Token="{self.api_key}", '
                f'Client="arrconf", '
                f'Device="arrconf", '
                f'DeviceId="arrconf", '
                f'Version="0.5.0"'
            )
        }
```

**Source:** Probe live 2026-05-17, cluster jellyfin-94f5cc54d-p4hk8 (10.11.8).

### Pattern 2: GET → mutate allowlist → POST entire body (System/Configuration, UserPolicy)

```python
def _reconcile_server_config(
    client: JellyfinClient,
    desired_section: ServerConfigSection,
    dry_run: bool,
) -> list[str]:
    """Reconcile /System/Configuration with allowlist merge (Pitfall 1 — full REPLACE).

    Pattern: GET cluster → mutate ONLY allowlist fields → POST entire body.
    POSTing a partial body resets non-allowlist fields to Jellyfin C# defaults.
    """
    log.info("step_begin", step="server_config", step_index=3)
    cluster_config: dict[str, Any] = client.get("/System/Configuration")

    # Allowlist 7 fields (D-07-CONFIG-01)
    merged = dict(cluster_config)  # start from cluster (preserves 49 non-allowlist fields)
    merged["UICulture"] = desired_section.ui_culture
    merged["MetadataCountryCode"] = desired_section.metadata_country_code
    merged["PreferredMetadataLanguage"] = desired_section.preferred_metadata_language
    merged["ActivityLogRetentionDays"] = desired_section.activity_log_retention_days
    merged["LogFileRetentionDays"] = desired_section.log_file_retention_days
    merged["ServerName"] = desired_section.server_name
    merged["PluginRepositories"] = [r.model_dump() for r in desired_section.plugin_repositories]

    # Idempotence check
    if _allowlist_equivalent(cluster_config, merged):
        log.info("server_config_no_op")
        return []
    if dry_run:
        log.info("dry_run_skip", resource="server_config")
        return ["server_config:dry_run"]

    client.post("/System/Configuration", json=merged)  # Pitfall 1: full REPLACE
    log.info("server_config_applied")
    return ["server_config:applied"]
```

**Source:** Verified probe 2026-05-17 + Pitfall 1 evidence (`UICulture` regression on partial POST).

### Pattern 3: POST /Library/VirtualFolders/Paths idempotence shim (Pitfall 2)

```python
def _reconcile_libraries(
    client: JellyfinClient,
    desired_section: LibrariesSection,
    dry_run: bool,
) -> list[str]:
    """Reconcile /Library/VirtualFolders/Paths — idempotence shim (Pitfall 2).

    POST /Library/VirtualFolders/Paths DUPLICATES path if already present.
    Reconciler MUST GET first and skip if path is already in PathInfos.
    """
    log.info("step_begin", step="libraries", step_index=1)
    current_libraries: list[dict[str, Any]] = client.get("/Library/VirtualFolders")
    actions: list[str] = []

    for desired_lib in desired_section.items:
        cluster_lib = next(
            (lib for lib in current_libraries if lib["Name"] == desired_lib.name),
            None,
        )
        if cluster_lib is None:
            # Library doesn't exist — out of scope D-07-LIB-01 (uses CREATE only at bootstrap).
            log.warning("library_missing_skip", name=desired_lib.name)
            continue

        existing_paths: set[str] = {
            p["Path"] for p in cluster_lib["LibraryOptions"]["PathInfos"]
        }
        for path in desired_lib.paths:
            if path in existing_paths:
                log.info("library_path_already_present", name=desired_lib.name, path=path)
                continue  # idempotent — Pitfall 2 shim
            if dry_run:
                log.info("dry_run_skip", resource="library_path", name=desired_lib.name, path=path)
                actions.append(f"library_path:dry_run:{desired_lib.name}:{path}")
                continue
            client.post(
                "/Library/VirtualFolders/Paths",
                params={"refreshLibrary": "false"},
                json={"Name": desired_lib.name, "Path": path, "PathInfo": {"Path": path}},
            )
            log.info("library_path_added", name=desired_lib.name, path=path)
            actions.append(f"library_path:added:{desired_lib.name}:{path}")

    # prune: false hardcoded (D-07-LIB-01) — do NOT remove paths not declared in YAML
    return actions
```

**Source:** Probe live 2026-05-17 — duplicate `['/media/series', '/media/series']` evidence.

### Pattern 4: Plugin Enable with Name → (Id, Version) resolver

```python
def _reconcile_plugins(
    client: JellyfinClient,
    desired_section: PluginsSection,
    dry_run: bool,
) -> list[str]:
    """Reconcile plugin activation — best-effort (D-07-PLUGINS-01).

    For each plugin in YAML required list:
      1. GET /Plugins → resolve Name → (Id, Version, Status)
      2. If Status not in {'Active', 'Restart'} → POST /Plugins/{Id}/{Version}/Enable
    No install, no uninstall (D-07-PLUGINS-01).
    """
    log.info("step_begin", step="plugins", step_index=4)
    current_plugins: list[dict[str, Any]] = client.get("/Plugins")
    by_name = {p["Name"]: p for p in current_plugins}
    actions: list[str] = []

    for desired in desired_section.required:
        cluster = by_name.get(desired.name)
        if cluster is None:
            log.warning("plugin_missing_skip", name=desired.name)
            continue

        plugin_id = cluster["Id"]
        plugin_version = cluster["Version"]
        status = cluster["Status"]

        if status in {"Active", "Restart"}:
            log.info("plugin_already_active", name=desired.name, status=status)
            continue
        if dry_run:
            log.info("dry_run_skip", resource="plugin_enable", name=desired.name)
            actions.append(f"plugin_enable:dry_run:{desired.name}")
            continue
        client.post(
            f"/Plugins/{plugin_id}/{plugin_version}/Enable",
        )
        log.info("plugin_enabled", name=desired.name, id=plugin_id, version=plugin_version)
        actions.append(f"plugin_enabled:{desired.name}")

    return actions
```

**Source:** OpenAPI 10.11.8 + probe 2026-05-17 (`POST /Plugins/{id}/{version}/Enable` HTTP 204 on TMDb idempotent).

### Anti-Patterns to Avoid

- **❌ POST `/System/Configuration` with partial body** — Pitfall 1, wipes other fields. Always GET first, merge allowlist, POST entire body.
- **❌ POST `/Library/VirtualFolders/Paths` without GET first** — Pitfall 2, duplicates path. Always check `PathInfos` set membership.
- **❌ `PUT /Users/{id}/Policy`** — HTTP 405, use POST.
- **❌ `POST /Plugins/{id}/Enable` (no version)** — HTTP 405, use `POST /Plugins/{id}/{version}/Enable`.
- **❌ Excluding `AuthenticationProviderId` / `PasswordResetProviderId` from UserPolicy body** — OpenAPI-required, HTTP 400 on missing. Re-inject from GET cluster (pattern Seerr D-06-CREDS-01).
- **❌ `prune: true` default sur libraries/users/plugins** — D-07-USERS-01 explicit (emilie operator-managed), CLAUDE.md "no automatic delete unless opt-in".
- **❌ `JellyfinClient(_ArrV3Client)`** — Jellyfin n'a pas `forceSave` (spec.md §895). Doit hériter directement de `ArrApiClient`.
- **❌ Hand-rolled HTTP retry/auth in `jellyfin.py`** — `ArrApiClient._request` déjà fait tenacity retry + 4xx/5xx classification. Réutiliser.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Auth header per request | Manual httpx.Client(headers=...) per call | Override `ArrApiClient.auth_headers()` (line 51) | Pattern propre Seerr — `httpx.Client(base_url, headers=auth_headers())` injecte sur toutes les requêtes. |
| 4xx/5xx classification + retry | try/except chain | Inherit `ArrApiClient._request` | tenacity retry (3x exp backoff sur 5xx + network) + AuthError/NotFoundError/ServerError typed exceptions déjà en place. |
| OpenAPI schema fetch | Manual JSON parsing for required fields | Live probe `GET /api-docs/openapi.json` once + bake into pydantic | Probe-time strategy : génère un fichier de référence ; pydantic model encode les findings. Pas de runtime OpenAPI dep (overkill homelab). |
| Idempotence diff | Hand-roll `if a == b` field-by-field | `_payloads_equivalent` style Seerr | Pattern Seerr `tools/arrconf/arrconf/reconcilers/seerr.py:97` — "all(current[k] == v for k, v in desired.items())". Extra keys in cluster GET ignored. |
| Path set comparison | List equality + dedup | Python `set()` from `PathInfos[].Path` | Pitfall 2 force set semantics — set membership skip avant POST. |
| Mock httpx in tests | unittest.mock patches | `respx` MockRouter | Pattern Phase 5/6 — `respx.mock(base_url=...).route(...).mock(return_value=...)` ; déjà dans pyproject. |

**Key insight:** Phase 7 = "Phase 6 pattern + 4 new endpoints + 5 newly discovered Pitfalls". Toute la mécanique (différ, reconcile loop, snapshot, dump, CLI dispatch) est déjà éprouvée — Plan 07 doit RÉUTILISER, pas réinventer.

---

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Jellyfin SQLite DB `/config/data/data/jellyfin.db` — `ApiKeys` table (1 entry "Seerr" already present). Reconciler n'écrit pas dans DB ; n'écrit que via API REST (operator-managed) | Aucune migration. Operator bootstrap = créer `JELLYFIN_API_KEY` via Dashboard → API Keys avant Wave 4. |
| Live service config | Jellyfin `/Devices` (registered clients): Seerr, Firefox, Kodi, Android. Après Phase 7 apply, arrconf apparaîtra comme `AppName="arrconf"`. Non-destructif | Aucune action (auditable, not breaking). Operator peut prune devices anciens via Dashboard si désiré (out of scope). |
| OS-registered state | Aucune. Jellyfin n'enregistre rien dans systemd/Windows Task Scheduler côté cluster (pod K8s, lifecycle via Deployment) | None — verified by `kubectl get pods` showing single Deployment-managed pod. |
| Secrets/env vars | `JELLYFIN_API_KEY` env var — déclaré dans `tools/snapshot/snapshot.sh:52` MAIS PAS DANS `arrconf-env` sealed-secret actuel (verified: `kubectl -n selfhost get secret arrconf-env` shows 6 keys — PROWLARR, QBT_USER, QBT_PASS, RADARR, SEERR, SONARR — pas de JELLYFIN). **Operator MUST bootstrap before Wave 4 cluster apply** | Operator step (D-07-CREDS-01 / REQ-bootstrap-exception) : générer API key via Dashboard, `kubeseal --raw` encrypt, ajouter à `my-kluster/secrets/sealed/arrconf-secret.yaml` (alphabetical entry between JELLYFIN-not-yet-existing and PROWLARR). Pattern carry-forward Phase 6 D-06-CRED-MGMT exactly. |
| Build artifacts / installed packages | Plugins déjà installés (bundled linuxserver image) : TMDb / OMDb / MusicBrainz / AudioDB / Studio Images / Kodi Sync Queue — 5/6 ont `CanUninstall=false` (bundled), 1/6 `CanUninstall=true` (Kodi Sync Queue). Aucun rebuild requis | Aucune action (D-07-PLUGINS-01 activation-only). Si un plugin disparaît de l'image upstream linuxserver/jellyfin lors d'un bump Renovate, le reconciler loggera `plugin_missing_skip` — Wave 4 verification step doit checker cet event. |

---

## Common Pitfalls

### Pitfall 1: POST /System/Configuration is FULL REPLACE, not merge — CRITICAL
**What goes wrong:** Operator (or test) POSTs `{"ServerName": "jellyfin"}` thinking they're patching a single field. Jellyfin **resets every other field** to C# defaults: `UICulture: fr → en-US`, `MetadataCountryCode: FR → US`, `PreferredMetadataLanguage: fr → en`, `PluginRepositories: [...] → []`.
**Why it happens:** OpenAPI says `ServerConfiguration.required = []` mais l'endpoint replace le doc entier ASP.NET-style — fields absents = defaults.
**How to avoid:** Reconciler MUST `GET /System/Configuration → mutate allowlist 7 fields → POST entire body`. Pattern Pattern 2 du §Architecture Patterns.
**Warning signs:** Post-apply snapshot diff montre dérive sur >7 fields ; UI Jellyfin Dashboard montre langue passée en EN ; `PluginRepositories` vide → install bloquée.

### Pitfall 2: POST /Library/VirtualFolders/Paths is NOT idempotent — CRITICAL
**What goes wrong:** Re-POST d'un path existant duplique l'entrée. After 2 reconciles: `PathInfos: ['/media/series', '/media/series']`. After 3 reconciles: triplicate. Library performance dégrade et display est confus.
**Why it happens:** Jellyfin API ne dédup pas les paths — chaque POST = un append.
**How to avoid:** Pattern 3 du §Architecture Patterns — GET first, set membership check, skip if present.
**Warning signs:** Idempotence test SC#4 fail (round-trip dump→apply --dry-run produit `add` events au lieu de `no_op`) ; snapshot diff montre PathInfos count incrementing.

### Pitfall 3: DELETE /Library/VirtualFolders/Paths removes ALL matching entries
**What goes wrong:** Si Pitfall 2 a créé un duplicate `[a, a]`, DELETE supprime les deux. Library devient vide (PathInfos `[]`).
**Why it happens:** `DELETE ?name=X&path=Y` matche tous les entries `Path == Y` dans la library X.
**How to avoid:** Reconciler ne devrait jamais avoir besoin de DELETE en Phase 7 (D-07-LIB-01 prune=false hardcoded). Si une future phase active prune, traiter PathInfos comme set (1 DELETE = remove from intent set).
**Warning signs:** Library `Locations` shows duplicates but `PathInfos` is empty (state corruption signal).

### Pitfall 4: /Users/{id}/Policy uses POST not PUT
**What goes wrong:** `client.put("/Users/...", id=..., json=body)` retourne HTTP 405 Method Not Allowed.
**Why it happens:** Jellyfin API contract — historical Emby behavior.
**How to avoid:** `JellyfinClient` n'hérite PAS de `_ArrV3Client` (correctement) → `client.put` est l'ArrApiClient générique. Mais Phase 7 doit explicitement appeler `client.post(f"/Users/{user_id}/Policy", json=...)`. Pas de `client.put(...)`.
**Warning signs:** First apply fails HTTP 405 dans `apply_complete` event.

### Pitfall 5: Plugin Enable endpoint requires VERSION in path
**What goes wrong:** `POST /Plugins/{id}/Enable` → HTTP 405. Reconciler interpréte comme erreur ; le plugin reste Disabled.
**Why it happens:** OpenAPI 10.11.8 endpoint shape = `/Plugins/{pluginId}/{version}/Enable` (version required path param).
**How to avoid:** GET /Plugins d'abord pour résoudre Name → (Id, Version) ; construire le path complet (Pattern 4 §Architecture Patterns).
**Warning signs:** First plugin reconcile reports `plugin_enable_failed http_code=405` ; plugin reste in Disabled status après plusieurs runs.

### Pitfall 6: UserPolicy OpenAPI requires AuthenticationProviderId + PasswordResetProviderId
**What goes wrong:** Si pydantic `Field(exclude=True)` sur ces 2 champs (parce que opérateur ne les set pas en YAML), POST renvoie HTTP 400 `request.body should have required property 'AuthenticationProviderId'`.
**Why it happens:** D-06-OPENAPI-01 carry-forward : "research-time `exclude=True` peut être faux selon OpenAPI live validator."
**How to avoid:** Pattern Seerr `apiKey` (D-06-CREDS-01) — `Field(exclude=True)` pour YAML desired-state symmetry + re-injection cluster value depuis GET avant POST. Carry-forward du fix Phase 6 commit `75e1661`.
**Warning signs:** First apply fails HTTP 400 sur `_reconcile_users` avec `request.body should have required property` ; arrconf reportera comme erreur dans `apply_complete`.

### Pitfall 7: PluginRepositories diff semantic = set by URL, not ordered list
**What goes wrong:** Reconciler compare PluginRepositories comme ordered list. Operator reorders manually via UI → arrconf re-PUT systématique sur chaque run (false-positive update).
**Why it happens:** Jellyfin n'ordonne pas les repos sémantiquement — URL est la clé de unicité.
**How to avoid:** Diff sémantique = `set(r.url for r in current) == set(r.url for r in desired)` + per-URL field comparison. Decision left to planner (Claude's Discretion in CONTEXT.md).
**Warning signs:** Idempotence test fails on PluginRepositories field (similar shape to Phase 6 D-06-SEERR-USER-FP).

### Pitfall 8: Locations cache shows stale duplicates after path manipulation
**What goes wrong:** Après une probe corruptive (POST duplicate → DELETE → POST restore), `Locations` shows `['/media/series', '/media/series']` mais `PathInfos` is `['/media/series']`. Non-critical mais confusing.
**Why it happens:** `Locations` est un projection display field — Jellyfin re-derive depuis PathInfos au démarrage ; entre temps stale.
**How to avoid:** Reconciler N'utilise QUE `PathInfos` (jamais `Locations`). Operator peut force refresh via `POST /Library/Refresh` (verified HTTP 204) ou pod restart. Non-blocking.
**Warning signs:** Snapshot diff entre baseline et post-apply montre Locations duplicates mais PathInfos cohérent.

### Pitfall 9: Token used in MediaBrowser header leaks in URL when fallback to ?api_key=
**What goes wrong:** Si fallback `?api_key=$KEY` activé (D-07-AUTH-01 fallback), la query string contient le secret. nginx/ingress access logs vont le persister. snapshot.sh fait aussi un curl avec cette URL — possible leak dans evidence files.
**Why it happens:** API key in query string = standard observability/log antipattern.
**How to avoid:** Préférer le MediaBrowser header (verified HTTP 200/204 sur tous les writes — pas besoin du fallback). Si le fallback est utilisé en debug, redact `api_key=` from any committed evidence file (carry-forward Phase 5/6 #4 snapshot.sh redaction).
**Warning signs:** Pattern `api_key=[a-f0-9]{32}` détecté dans `snapshots/before-phase-7-*/jellyfin/*.json` ou `evidence/*.txt`.

---

## Code Examples

### Library VirtualFolders GET response shape

```json
// Source: GET /Library/VirtualFolders [VERIFIED: 2026-05-17 live cluster]
[
  {
    "CollectionType": "tvshows",
    "ItemId": "d565273fd114d77bdf349a2896867069",
    "Name": "Séries",
    "Locations": ["/media/series"],
    "LibraryOptions": {
      "PathInfos": [{"Path": "/media/series"}],
      "PreferredMetadataLanguage": "",
      "MetadataCountryCode": ""
      // ... 40+ other LibraryOptions fields, all out of scope D-07-LIB-02
    },
    "PrimaryImageItemId": "d565273fd114d77bdf349a2896867069",
    "RefreshStatus": "Idle"
  }
]
```

### POST /Library/VirtualFolders/Paths body shape

```bash
# Source: OpenAPI 10.11.8 MediaPathDto [VERIFIED: probe 2026-05-17]
curl -X POST "http://jellyfin:8096/Library/VirtualFolders/Paths?refreshLibrary=false" \
  -H "Authorization: MediaBrowser Token=\"$KEY\", Client=\"arrconf\", Device=\"arrconf\", DeviceId=\"arrconf\", Version=\"0.5.0\"" \
  -H "Content-Type: application/json" \
  -d '{"Name":"Séries","Path":"/media/anime","PathInfo":{"Path":"/media/anime"}}'
# Expected: HTTP 204 (idempotent IF /media/anime not already in PathInfos — see Pitfall 2)
```

### POST /Users/{id}/Policy body shape (re-inject required fields)

```python
# Source: Probe 2026-05-17 + OpenAPI 10.11.8 UserPolicy
# desired_section: UserPolicySection (allowlist subset, no AuthN/PasswordReset Provider IDs)
cluster_user = client.get(f"/Users/{user_id}")  # full user object
cluster_policy = cluster_user["Policy"]  # contains the 2 OpenAPI-required ProviderIds

desired_payload = desired_section.model_dump()  # 30 allowlist fields
# Re-inject the 2 OpenAPI-required fields from cluster (D-06-OPENAPI-01 carry-forward)
desired_payload["AuthenticationProviderId"] = cluster_policy["AuthenticationProviderId"]
desired_payload["PasswordResetProviderId"] = cluster_policy["PasswordResetProviderId"]

client.post(f"/Users/{user_id}/Policy", json=desired_payload)
# Expected: HTTP 204 [VERIFIED: probe 2026-05-17 on user moi Id=82fd95db...]
```

### POST /System/Configuration full-merge pattern

```python
# Source: Probe 2026-05-17 (Pitfall 1 evidence — partial body wipes UICulture)
cluster_config = client.get("/System/Configuration")  # 56-field dict
merged = dict(cluster_config)
# Override only the 7 allowlist fields (D-07-CONFIG-01)
merged["UICulture"] = "fr"
merged["MetadataCountryCode"] = "FR"
merged["PreferredMetadataLanguage"] = "fr"
merged["ActivityLogRetentionDays"] = 30
merged["LogFileRetentionDays"] = 3
merged["ServerName"] = "jellyfin"
merged["PluginRepositories"] = [
    {"Name": "Jellyfin Stable", "Url": "https://repo.jellyfin.org/files/plugin/manifest.json", "Enabled": True}
]
client.post("/System/Configuration", json=merged)
# Expected: HTTP 204 (49 non-allowlist fields preserved from cluster GET)
```

### POST /Plugins/{id}/{version}/Enable

```bash
# Source: OpenAPI 10.11.8 + probe 2026-05-17 on TMDb
PLUGIN_ID="b8715ed16c4745289ad3f72deb539cd4"
VERSION="10.11.8.0"
curl -X POST "http://jellyfin:8096/Plugins/${PLUGIN_ID}/${VERSION}/Enable" \
  -H "Authorization: MediaBrowser Token=\"$KEY\", Client=\"arrconf\", Device=\"arrconf\", DeviceId=\"arrconf\", Version=\"0.5.0\"" \
  -H "Content-Length: 0"
# Expected: HTTP 204 (idempotent on already-Active plugin)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `X-Emby-Token: <key>` auth | `Authorization: MediaBrowser Token="<key>"` | Jellyfin 10.6+ deprecated X-Emby ; 10.11 keeps it as fallback | Préférer MediaBrowser — registers in /Devices, future-proof. |
| Plugin install/uninstall via `/Plugins/Packages` | Out of scope arrconf — operator manages | N/A | Phase 7 activation-only ; full lifecycle defer Phase 7+1. |
| Library CRUD via `/Library/VirtualFolders` POST | Partial: ADD path via `/Paths`, ne CREATE pas de library (operator did already) | Phase 7 D-07-LIB-01 | Existing libraries Séries/Films suffisent ; reconciler ne CREATE pas. |
| User CRUD via `/Users/New` POST + Policy | Out of scope Phase 7 — admin only via Policy | D-07-USERS-01 | emilie operator-managed ; reconciler hardcoded prune=false. |

**Deprecated/outdated:**
- `X-Emby-Token` header — still works in 10.11.8 but deprecated. Use MediaBrowser.
- Plugin Enable without version — used to work in Emby pre-10.0, returns 405 in Jellyfin 10.11.
- `PUT /Users/{id}/Policy` — never supported in Jellyfin (only POST). The OpenAPI 10.11.8 explicitly only declares `post`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | POST `/Users/{id}/Policy` is full REPLACE (not merge) — based on Pitfall 1 pattern symmetry | Q9 PUT Probe — `/Users/{id}/Policy` | Si en réalité c'est merge, le pattern "GET → merge allowlist → POST" reste valide (juste sur-ingénierie) — no risk. Si REPLACE comme assumed, omitting AuthenticationProviderId+PasswordResetProviderId → 400 (Pitfall 6 mitigates). |
| A2 | `Restart` PluginStatus = "Active mais needs restart" (no-op pour Phase 7) | Pitfall 5 + Plugin enum | Si en réalité `Restart` veut dire "needs explicit POST Enable", le reconciler skipperait et le plugin resterait pending. Cluster baseline montre tous Status=Active, peu probable. Operator peut force Enable via UI si necessaire. |
| A3 | `PluginRepositories` diff sémantique = set by URL (Pitfall 7) | Common Pitfalls + Claude's Discretion | Si ordered list comparison utilisé, idempotence test sera flaky (operator reorders → arrconf re-PUT). Choix laissé au planner ; set-by-URL est la recommandation. |
| A4 | `MediaBrowser` header `Client="arrconf"` value is cosmetic (not used for permission scoping) | Pattern 1 JellyfinClient | Si Jellyfin a un client allowlist (improbable per OpenAPI), POST writes failed. Verified live HTTP 204 sur tous les writes → no risk. |
| A5 | Operator will bootstrap `JELLYFIN_API_KEY` in sealed-secret before Wave 4 (REQ-bootstrap-exception) | Runtime State Inventory | Si pas fait, premier CronJob run = `missing_api_key` exit 2 (carry-forward Phase 6 D-06-CRED-MGMT exact pattern). Plan 07 Wave 0/4 doit checklist cet operator step. |
| A6 | snapshot.sh `JELLYFIN_AUTH_HEADER` defaut (line 103) suit le bon format MediaBrowser | Code Examples + Don't Hand-Roll | Si le format est mauvais, snapshot.sh échoue (Phase 0 baseline aurait failed — mais baseline existe complete = format OK). Verified. |

---

## Open Questions (RESOLVED)

All 4 questions are resolved through CONTEXT.md decisions + the live probe + planner-time pattern selection. None are blocking — each has a concrete resolution applied during planning.

1. **POST /Users/{id}/Policy replace vs merge semantics (A1)**
   - What we know: HTTP 204 sur round-trip body complet. OpenAPI required = AuthN+PasswordReset Provider Ids.
   - What was unclear: Une POST partielle (e.g. just `{"IsAdministrator":true}`) — reset-elle les autres 43 fields à defaults C# comme `/System/Configuration` ?
   - **RESOLVED**: Plan 04 implements the defensive GET → merge allowlist → POST pattern unconditionally (full body, re-injecting required ProviderIds — Pitfall 6). Cost is one extra GET per reconcile (negligible). This is correct whether the endpoint is replace OR merge — so the ambiguity is absorbed by the implementation choice. No Wave 0 additional probe required.

2. **`Restart` PluginStatus — actionable ou pending (A2)**
   - What we know: enum OpenAPI = `['Active', 'Restart', 'Deleted', 'Superseded', 'Superceded', 'Malfunctioned', 'NotSupported', 'Disabled']`. Cluster baseline = tout `Active`.
   - What was unclear: si après un Jellyfin upgrade un plugin passe en `Restart`, faut-il POST Enable ou attendre operator restart ?
   - **RESOLVED**: Treat `Restart` as no-op (semantically "active but pending Jellyfin restart") + emit warn log via structlog (`plugin_status_restart_pending`). Operator handles via Dashboard restart. Formal handling deferred to Phase 7+1 if cluster ever encounters this state in practice. Implemented in Plan 04 Task 4.2 `_reconcile_plugins` step.

3. **PluginRepositories diff semantic (A3)**
   - What we know: list of `{Name, Url, Enabled}` objects. URL est la clé unique sémantique.
   - What was unclear: Reorder UI → diff naive flagge update. Acceptable false-positive ou bug ?
   - **RESOLVED**: Plan 04 implements diff set-by-URL (sort the list by URL before comparison, both desired and current). Avoids the D-06-SEERR-USER-FP false-positive pattern. Documented as test case `test_plugin_repositories_diff_set_by_url` in Plan 04 Task 4.3.

4. **Snapshot leak risk for /Devices**
   - What we know: `/Devices` GET returns `Id` field b64-encoded (UserAgent + maybe token). Phase 6 D-06-OPENAPI-01 leak Phase a sensibilisé.
   - What was unclear: Le b64 contient-il du token ou juste UserAgent ?
   - **RESOLVED**: `/Devices` is OUT OF SCOPE for Phase 7 (not reconciled, not snapshotted in fixtures). `tools/snapshot/snapshot.sh` Jellyfin endpoint list intentionally excludes `/Devices`. Carry-forward Phase 5/6 #4 redaction discipline remains active for the in-scope endpoints (library_virtualfolders, users, system_configuration, plugins) — Plan 01 Task 1.3 anti-leak grep covers this.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | arrconf runtime | ✓ | (cluster image) | — |
| httpx | JellyfinClient HTTP | ✓ | 0.28.x | — |
| pydantic v2 | Resource models | ✓ | 2.13.x | — |
| respx | Unit tests | ✓ | 0.23.x | — |
| pytest | Test runner | ✓ | 9.0.x | — |
| sqlite3 (operator local) | DB probe for existing API keys (Wave 0 only) | ✓ | (host system) | Operator generates new key via Dashboard UI |
| kubectl + cluster access (selfhost) | Port-forward + apply | ✓ | k8s 1.28+ | — |
| Jellyfin 10.11.8 pod running | All reconcile operations | ✓ | 10.11.8 | — (no fallback — phase requires live cluster) |
| `JELLYFIN_API_KEY` env var in arrconf-env Secret | Reconciler auth | ✗ | — | **BLOCKING** — operator must bootstrap before Wave 4 cluster apply (REQ-bootstrap-exception). |
| sealed-secrets controller (my-kluster) | Operator delivery path for JELLYFIN_API_KEY | ✓ | (already used Phase 6) | — |

**Missing dependencies with no fallback:**
- `JELLYFIN_API_KEY` in `arrconf-env` Secret — operator must bootstrap before Wave 4 cluster apply. Pattern carry-forward Phase 6 D-06-CRED-MGMT exactly.

**Missing dependencies with fallback:**
- (none)

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.x + respx 0.23.x + pytest-cov 7.1.x |
| Config file | `tools/arrconf/pyproject.toml` (`[tool.pytest.ini_options]` line 58, `[tool.coverage.*]` line 62–66) |
| Quick run command | `cd tools/arrconf && pytest tests/test_reconcilers_jellyfin.py -x` |
| Full suite command | `cd tools/arrconf && pytest --cov=arrconf --cov-fail-under=70` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-app-coverage | Jellyfin reconciler libraries: add missing paths, idempotent | unit | `pytest tests/test_reconcilers_jellyfin.py::test_libraries_add_missing_path -x` | ❌ Wave 0 (Plan 07-XX creates) |
| REQ-app-coverage | Jellyfin reconciler libraries: no-op when path already present (Pitfall 2 shim) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_libraries_no_op_when_path_present -x` | ❌ Wave 0 |
| REQ-app-coverage | Jellyfin reconciler users: Policy POST with AuthN+PasswordReset re-injected from GET | unit | `pytest tests/test_reconcilers_jellyfin.py::test_users_policy_reinjects_required_fields -x` | ❌ Wave 0 |
| REQ-app-coverage | Jellyfin reconciler users: POST uses POST verb (not PUT) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_users_policy_uses_post_not_put -x` | ❌ Wave 0 |
| REQ-app-coverage | Jellyfin reconciler server_config: merges allowlist into cluster GET before POST (Pitfall 1) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_server_config_full_replace_preserves_non_allowlist -x` | ❌ Wave 0 |
| REQ-app-coverage | Jellyfin reconciler plugins: POST /Plugins/{id}/{version}/Enable when Status != Active | unit | `pytest tests/test_reconcilers_jellyfin.py::test_plugins_enable_when_disabled -x` | ❌ Wave 0 |
| REQ-app-coverage | Jellyfin reconciler plugins: no-op when Status == Active | unit | `pytest tests/test_reconcilers_jellyfin.py::test_plugins_no_op_when_active -x` | ❌ Wave 0 |
| REQ-app-coverage | Jellyfin reconciler dry_run: no httpx writes when ARRCONF_DRY_RUN=true | unit | `pytest tests/test_reconcilers_jellyfin.py::test_jellyfin_dry_run_no_writes -x` | ❌ Wave 0 |
| REQ-app-coverage | JellyfinClient.auth_headers() returns MediaBrowser format (D-07-AUTH-01) | unit | `pytest tests/test_client_base.py::test_jellyfin_client_mediabrowser_header -x` | ❌ Wave 0 |
| REQ-app-coverage | RootConfig parses jellyfin section + schemas/arrconf-schema.json includes jellyfin (REQ-yaml-autocomplete) | unit | `pytest tests/test_config.py::test_jellyfin_instance_parse + tests/test_schema_gen.py::test_schema_includes_jellyfin -x` | ❌ Wave 0 |
| REQ-app-coverage | Round-trip idempotence: `dump --apps jellyfin → diff --apps jellyfin` → 0 actions | integration (cluster, manual gate) | `arrconf dump --apps jellyfin > /tmp/jelly-baseline.yml && arrconf diff --config /tmp/jelly-baseline.yml --apps jellyfin` exit 0 | ❌ Wave 4 (cluster) |
| REQ-app-coverage | Snapshot diff: `snapshots/before-phase-7-*` vs `snapshots/after-phase-7-*` shows only intentional changes | smoke (cluster) | `diff -r snapshots/before-phase-7-<date>/jellyfin/ snapshots/after-phase-7-<date>/jellyfin/` | ❌ Wave 4 |
| REQ-bootstrap-exception | sealed-secret `arrconf-env` includes JELLYFIN_API_KEY before Wave 4 | manual (operator gate) | `kubectl -n selfhost get secret arrconf-env -o jsonpath='{.data}' \| jq 'keys'` includes `"JELLYFIN_API_KEY"` | manual operator step |

### Sampling Rate

- **Per task commit:** `cd tools/arrconf && pytest tests/test_reconcilers_jellyfin.py -x` (≤ 5s for 8–12 reconciler tests)
- **Per wave merge:** `cd tools/arrconf && pytest --cov=arrconf --cov-fail-under=70` (≤ 30s full suite, blocks if coverage on `reconcilers/jellyfin.py` < 70%)
- **Phase gate (Wave 4):** Full suite green + cluster round-trip + snapshot diff before `/gsd-verify-work`. Carry-forward Phase 6 SC dispositive pattern.

### Wave 0 Gaps

- [ ] `tools/arrconf/tests/test_reconcilers_jellyfin.py` — covers REQ-app-coverage Jellyfin (8–12 tests)
- [ ] `tools/arrconf/tests/fixtures/jellyfin_library_virtualfolders.json` — sanitized slice baseline (no Devices leakage)
- [ ] `tools/arrconf/tests/fixtures/jellyfin_users.json` — moi admin only (emilie pruned from fixture for D-07-USERS-01 scope clarity)
- [ ] `tools/arrconf/tests/fixtures/jellyfin_system_configuration.json` — full 56-field baseline
- [ ] `tools/arrconf/tests/fixtures/jellyfin_plugins.json` — 6 plugins as live cluster
- [ ] `tools/arrconf/tests/conftest.py` extensions (jellyfin_instance fixture, jellyfin_settings env var)
- [ ] No framework install (pytest + respx already in pyproject) — Wave 0 just adds files, no `pip install`
- [ ] `snapshots/before-phase-7-<date>/jellyfin/` re-snapshot via `tools/snapshot/snapshot.sh --apps jellyfin` (ADR-6 discipline)

---

## Project Constraints (from CLAUDE.md)

Reconciler `jellyfin.py` MUST satisfy the following CLAUDE.md directives (planner verifies compliance):

- **Code style:** `ruff check` + `ruff format --check` + `mypy` strict on public signatures. CI blocks. (CLAUDE.md "Conventions développement — arrconf")
- **Idempotence rule (RÈGLE D'OR):** GET, diff explicit before POST. Re-running N times = 0 changes if YAML unchanged. (CLAUDE.md "Idempotence")
- **Prune default false:** `prune: false` par défaut, opt-in par section. D-07-USERS-01 hardcodes prune=false for emilie protection — aligns. (CLAUDE.md + REQ-prune-opt-in)
- **Test coverage ≥ 70%:** on `reconcilers/jellyfin.py` + any new code in `differ.py` (none expected — generic engine reused). respx mocks only — no real Jellyfin API calls in CI. (CLAUDE.md "Tests" + REQ-test-coverage)
- **Type hints partout sur signatures publiques.** (CLAUDE.md)
- **No secrets in repo:** `JELLYFIN_API_KEY` reads from env only (`os.environ["JELLYFIN_API_KEY"]` in `arrconf/config.py` Settings model). Never logged. (CLAUDE.md "Ce que tu NE dois PAS faire" + REQ-secret-management)
- **No tag `:latest` hardcoded in chart values.** Phase 7 only bumps `arrconf` image tag via auto-tag chain. (CLAUDE.md)
- **Frontière configarr respectée:** Phase 7 ne touche PAS aux endpoints quality_profiles / custom_formats / quality_definitions / media_naming (configarr-exclusive — ADR-5). Jellyfin n'a pas ces concepts directement, mais le reconciler `jellyfin.py` doit explicitement N'ÊTRE QUE sur les 4 scopes Phase 7 (Library, Users, System/Configuration, Plugins). Pas de `/Items/{id}/Metadata` PUT etc. (CLAUDE.md "frontière")
- **Snapshot avant test risqué:** Wave 0 obligatoire `snapshots/before-phase-7-<date>/jellyfin/` commité avant tout cluster write. (CLAUDE.md "Workflow snapshot")
- **Aucune dépendance Python sans pinning dans pyproject.toml.** Phase 7 N'AJOUTE PAS de dep — code-only sur stack existant. (CLAUDE.md)
- **No real API calls in CI:** respx mocks pour tous les tests. Live cluster probe uniquement en research/Wave 0/Wave 4 (operator-driven). (CLAUDE.md)
- **Pas de `prune: true` par défaut:** D-07-USERS-01 + D-07-PLUGINS-01 + D-07-LIB-01 + D-07-CONFIG-01 tous prune=false. (CLAUDE.md + REQ-prune-opt-in)
- **snapshot.sh existe pour Jellyfin** (line 331 `snapshot_jellyfin()`, line 103 `JELLYFIN_AUTH_HEADER`) — Wave 0 reuse, no new code.

---

## Security Domain

> arr-stack project has no formal ASVS enforcement config — but the following constraints apply by CLAUDE.md and CONTEXT.md.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `JELLYFIN_API_KEY` env var only (REQ-bootstrap-exception). MediaBrowser Token header (D-07-AUTH-01). No password / cookie auth. |
| V3 Session Management | no | API-key auth ; no sessions. |
| V4 Access Control | yes | Admin user `moi` only reconciled (D-07-USERS-01). `emilie` operator-managed, prune=false hardcoded. |
| V5 Input Validation | yes | pydantic v2 strict (`extra="forbid"` on declared sections; `extra="allow"` on forward-compat sections per Phase 6 pattern). JSON Schema gate via `arrconf schema-gen`. |
| V6 Cryptography | no | No crypto in arrconf. Sealed-secrets (Bitnami) handles key encryption at rest in my-kluster. |
| V7 Error Handling | yes | `tools/arrconf/arrconf/exceptions.py` typed exceptions (AuthError / NotFoundError / ServerError / ReconcileError). Never log API keys in exception messages. |
| V9 Communication | yes | HTTP only inside cluster (svc.cluster.local). External Jellyfin URL (jellyfin.tgu.ovh) NOT used by arrconf (cluster-internal access). |
| V14 Configuration | yes | All config from sealed-secret env + ConfigMap YAML. No filesystem secret reads. No `:latest` tags. |

### Known Threat Patterns for arr-stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leak via snapshot file commit | Information Disclosure | `tools/snapshot/snapshot.sh` redaction (Phase 5/6 #4 carry-forward — manual sed redaction before commit until fix lands) ; never snapshot `/Devices` (b64-encoded payloads may contain tokens) |
| API key leak via query param (`?api_key=`) in logs | Information Disclosure | Use MediaBrowser header by default (D-07-AUTH-01) ; redact `api_key=[a-f0-9]+` if fallback ever activated |
| Accidental DELETE of emilie user (declarative drift) | Tampering | D-07-USERS-01 hardcodes prune=false ; user list never wiped |
| POST /System/Configuration partial body resets locale | Tampering (configuration corruption) | Pitfall 1 mitigation — always GET → merge allowlist → POST entire body |
| Plugin reactivated despite operator intent to disable | Tampering | D-07-PLUGINS-01 activation-only (operator can disable via UI, arrconf will re-enable on next run — explicit pattern, documented) |
| arrconf writing to quality_profiles (ADR-5 frontière) | Tampering | Reconciler `jellyfin.py` scoped to 4 endpoints only ; `tests/test_scope_violation.py` extension for Jellyfin if needed |
| Credentials in Helm values committed | Information Disclosure | All API keys via sealed-secret only (`arrconf-env`) ; chart `files/arrconf.yml` has NO key, only references |

---

## Sources

### Primary (HIGH confidence)

- Jellyfin OpenAPI 10.11.8 — `kubectl exec ... cat /usr/share/jellyfin/api-docs/openapi.json` [VERIFIED: 2026-05-17 local copy `/tmp/jelly-openapi-paths.txt`, 2 MB, info.version="10.11.8"]
- Live cluster probe — `kubectl port-forward + curl` against `jellyfin-94f5cc54d-p4hk8` pod 2026-05-17 ~10:52–11:00 UTC [VERIFIED: 12 probe sequences, all HTTP codes captured]
- `snapshots/baseline-2026-05-07/jellyfin/` — 10 files committed Phase 0 [VERIFIED: in repo, git log]
- `tools/arrconf/arrconf/client_base.py` — base class + 4 existing subclass patterns (Sonarr/Radarr/Prowlarr/Seerr/qBittorrent) [VERIFIED: line numbers 29, 101, 127, 134, 147, 166, 185]
- `tools/arrconf/arrconf/reconcilers/seerr.py` — closest analog (non-_ArrV3Client, POST-based, single-instance match) [VERIFIED: read]
- `.planning/phases/06-reconciler-seerr/06-07-SUMMARY.md` — Phase 6 deviations + carry-forward lessons [VERIFIED: read]
- `.planning/phases/06-reconciler-seerr/06-RESEARCH.md` — D-06-VALIDATE-01 probe pattern replicated here [VERIFIED: read]

### Secondary (MEDIUM confidence)

- Jellyfin official API docs https://api.jellyfin.org/ — cross-referenced for MediaBrowser header format [WebSearch not needed — OpenAPI in-cluster authoritative]
- `tools/arrconf/arrconf/reconcilers/sonarr.py` — `_reconcile_series_tags` label→id resolver pattern reused for plugin Name→Version resolver [VERIFIED: read line 1-60]

### Tertiary (LOW confidence)

- (none — every claim sourced from either OpenAPI 10.11.8 or live probe in this session)

---

## Metadata

**Confidence breakdown:**

- Q9 auth strategy: **HIGH** — 3 strategies probed live, all return HTTP 200 ; MediaBrowser preferred per D-07-AUTH-01.
- Write semantics (POST vs PUT, replace vs merge): **HIGH** — POST /System/Configuration full REPLACE verified via destructive probe + restore ; POST /Users/{id}/Policy verified (PUT 405) ; POST /Library/VirtualFolders/Paths NOT idempotent verified.
- Plugin Enable endpoint: **HIGH** — `/Plugins/{id}/{version}/Enable` verified live HTTP 204 ; OpenAPI confirms shape.
- Required OpenAPI fields (D-06-OPENAPI-01 carry-forward): **HIGH** — schemas extracted from `/tmp/jelly-openapi-paths.txt` ; UserPolicy required = AuthN+PasswordResetProviderId ; ServerConfiguration required = [].
- Match-by-Name resolvers: **HIGH** — live snapshots confirm Name + Id pairs for libraries / users / plugins.
- Reconciler architecture pattern: **HIGH** — mirrors Seerr exactly + adds auth_headers override + 3 newly discovered Pitfalls (POST-not-PUT for Policy, version-in-path for plugin Enable, idempotence shim for /Paths).
- Validation test plan: **HIGH** — 11 unit tests + 2 cluster smoke tests mapped to REQ-app-coverage ; pattern Phase 6 6-07-SUMMARY SC dispositive.
- Security/leak risk: **MEDIUM** — `/Devices` snapshot leak risk known (b64-encoded UA + maybe token) ; Phase 7 explicitly excludes `/Devices` from snapshot scope (carry-forward Phase 5/6 #4).

**Research date:** 2026-05-17
**Valid until:** 2026-06-16 (30 days — Jellyfin 10.11.8 is stable LTS, OpenAPI unchanging on patch versions ; revalidate Q9 probe if Jellyfin minor bumps to 10.12.x before Wave 4 cluster apply).
