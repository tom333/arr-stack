# Phase 29: Sagas — Research

**Researched:** 2026-05-31
**Domain:** Radarr Collections API + Jellyfin tmdbboxsets plugin + Jellyfin Collections API + intent.yml apply-time wiring
**Confidence:** HIGH (core Radarr/Jellyfin APIs verified from official source code; tmdbboxsets GUID/version verified from official plugin repo)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `apply` loads `intent.yml` (via the existing `load_intent`) in addition to `arrconf.yml`. New pure generators in `arrconf/generators/sagas.py` transform `SagaEntry` → desired Radarr Collection resources + Jellyfin presentation desired-state, consumed in-memory by the new reconciler code — mirroring `arrconf/generators/categories.py`. Sagas are NOT written into `arrconf.yml`, and `arrconf generate` stays scoped to external-tool configs only.
- **D-02:** Tighten `SagaEntry` from the P28 `extra="allow"` / `name`-only stub to the full locked schema with `model_config = ConfigDict(extra="forbid")`: `name: str`, `kind: Literal["movies", "series"]`, `tmdb_collection: int | None` (required when `kind == "movies"`, validator enforces), `profile: str`, `root: str`, `items: list[...] | None` (series BoxSet members; shape to be confirmed by research), `extra="forbid"`. Regenerate `schemas/intent-schema.json` via `arrconf intent-schema-gen`.
- **D-03:** New reconciler + `arrconf/resources/radarr/collection.py`. Mechanics: `GET /api/v3/collection`, match desired `kind=movies` sagas by `tmdbId`, PUT only on drift. Reconciled fields: `monitored`, `qualityProfileId` (from `profile`), `rootFolderPath` (from `root`), `minimumAvailability`, `searchOnAdd`. PUT-only on EXISTING collections; absent → log warning + skip. No POST-create, no Import-List bootstrap.
- **D-04:** Reuse the existing two-run plugin reconciler (`_reconcile_plugins`, ADR-9) for tmdbboxsets. Add the tmdbboxsets repo URL + package to the Jellyfin plugins desired config.
- **D-05:** `kind=series` sagas: arrconf creates/maintains a curated Jellyfin BoxSet (Collection) via the Jellyfin Collections API (`POST /Collections` + `POST /Collections/{id}/Items`) + tags the member series `arrconf-managed` in Sonarr. No Sonarr Collections reconciler.
- **D-06:** `profile` → Radarr `qualityProfileId` via `GET /api/v3/qualityprofile` name-match (`ConfigError` if not found). `root` → `rootFolderPath` verbatim.
- **D-07:** Radarr Collections reconcile is strictly idempotent (2nd run = 0 plan_actions). Jellyfin plugin install + BoxSet presentation is best-effort (ADR-9 two-run). Phase exits 0 even when Jellyfin presentation is pending Run N+1. Co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` (0.18.0 → 0.19.0) in the same commit.

### Claude's Discretion

- Exact module split (one `generators/sagas.py` vs movies/series helpers), reconciler function placement, test fixture layout.
- Whether the apply-time intent.yml load is wired into the existing `apply` flow or a dedicated saga sub-step.
- minimumAvailability default value for collections.

### Deferred Ideas (OUT OF SCOPE)

- Radarr Import-List bootstrap to auto-populate empty TMDB collections.
- Advanced series-BoxSet curation / ordering; multi-BoxSet hierarchies.
- `categories[]` → intent migration, `arrconf.yml` made generated, UI on intent — all v2.
- cross-seed deploy (Phase 30), qbit_manage (Phase 31).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SAGAS-01 | Operator declares a saga (`{name, tmdb_collection, profile, root}`) in `intent.yml` | D-02 SagaEntry schema locked; pure generator in `generators/sagas.py` mirrors categories.py pattern |
| SAGAS-02 | arrconf reconciles Radarr Collections from declared sagas (new reconciler: GET-match by `tmdbId`, PUT idempotent) | Radarr API verified: `GET /api/v3/collection`, `PUT /api/v3/collection/{id}` with full CollectionResource shape including tmdbId, qualityProfileId, rootFolderPath, monitored, searchOnAdd, minimumAvailability |
| SAGAS-03 | arrconf presents sagas in Jellyfin via the `tmdbboxsets` plugin (reconciler plugin best-effort, two-run model) | GUID verified: `bc4aad2e-d3d0-4725-a5e2-fd07949e5b42`; version 13.0.0.0 (latest); repo URL: `https://repo.jellyfin.org/files/plugin/manifest.json` (already in arrconf.yml); plugin auto-creates BoxSets from TMDB metadata — no per-saga config needed |
| SAGAS-04 | Series sagas presented via arrconf-managed Sonarr tag + curated Jellyfin BoxSet | Jellyfin Collections API verified VIABLE with caveats; `POST /Collections` creates BoxSet; `POST /Collections/{id}/Items` is idempotent (AddToCollectionAsync skips already-linked items); listing BoxSets: `GET /Items?includeItemTypes=BoxSet&recursive=true&fields=ProviderIds`; series member resolution: title-based search via `GET /Items?includeItemTypes=Series&searchTerm=<title>&recursive=true&fields=ProviderIds` |
</phase_requirements>

---

## Summary

Phase 29 delivers four interlocking capabilities: (1) a locked `SagaEntry` schema replacing the P28 stub, (2) a new Radarr Collections reconciler wired from sagas in `intent.yml`, (3) the `tmdbboxsets` Jellyfin plugin installed via the existing ADR-9 two-run model, and (4) series-saga presentation via curated Jellyfin BoxSets and Sonarr `arrconf-managed` tagging.

The Radarr Collections API is clean and well-suited to idempotent reconcile: `GET /api/v3/collection` returns all auto-discovered collections, matched by `tmdbId`, updated by `PUT /api/v3/collection/{id}` with the drift-only fields. The critical constraint — Radarr auto-discovers a collection only once ≥1 member movie exists — is unchanged and the plan simply log-skips absent collections (D-03 unchanged).

The `tmdbboxsets` plugin is an official Jellyfin plugin (GUID `bc4aad2e-d3d0-4725-a5e2-fd07949e5b42`, latest version 13.0.0.0), already served by the `https://repo.jellyfin.org/files/plugin/manifest.json` repository already declared in `arrconf.yml`. It operates autonomously: once installed and active, it scans library movies, groups those sharing a TMDB collection `ProviderId`, and creates/maintains BoxSets automatically — no per-saga arrconf config required.

The Jellyfin BoxSet creation for series sagas is **assessed VIABLE for idempotent reconcile in this tranche** — with the specific strategy detailed in the D-05 section. The `AddToCollectionAsync` implementation is inherently idempotent (it checks `currentLinkedChildrenIds` before adding). `POST /Collections` is NOT idempotent on its own (creates duplicates), but the reconciler MUST pre-check existing BoxSets by name from `GET /Items?includeItemTypes=BoxSet` before calling POST. Series member resolution uses title-based `GET /Items` search against the Jellyfin library.

**Primary recommendation:** Proceed with all four capabilities as locked. The Jellyfin BoxSet path (D-05) requires one mitigation pattern — GET-before-POST name check — which exactly mirrors the Pitfall 16-1 mitigation already in `_reconcile_libraries`. Use `items: list[str]` with series titles as the `SagaEntry` identifier (title-based resolution, most operator-friendly).

---

## [VALIDATE D-01] — In-memory generator path: VALIDATED

**Verdict: CONFIRMED SOUND. Implement as D-01 specifies.**

The CONTEXT.md D-01 concern was: DESIGN §3 conceptually lists "Radarr Collections in arrconf.yml" as output — does that mean the plan should emit a committed file instead?

After reading DESIGN §3 literally: the table row says output is "Radarr Collections (PUT par `tmdbId`) + plugin Jellyfin `tmdbboxsets`". These are **reconcile targets** (live Radarr API calls), not committed files. The parenthetical "Radarr Collections in arrconf.yml" in DESIGN §3 is a conceptual note about which app owns the reconcile, not an instruction to write a config file.

The in-memory expansion (D-01) is strictly cleaner:
- `arrconf.yml` stays hand-edited, never touched by sagas (P28 D-01 preserved).
- `generate` stays scoped to external tool configs (cross-seed, qbit_manage) that produce committed files for non-reconciled tools.
- Sagas are reconciler-driven (like categories), not file-driven — the DESIGN §2 "architecture cible" diagram confirms this: `sagas` → `arrconf apply` → `APIs *arr/jellyfin`.
- The `generate` command already has `load_intent` in scope (line 881 of `__main__.py`) — no new import chain required.

**How to wire apply:** The `apply` command in `__main__.py` currently calls `load_config` (line 208) and never calls `load_intent`. The cleanest pattern: add `load_intent` call at the top of the `apply` function body (after `load_config`), guard with `intent_path.exists()`, default path mirrors arrconf.yml location (`/etc/arrconf/intent.yml`). Add `--intent` CLI option at the callback level (parallels `--config`). Pass the resolved `IntentConfig` (or its sagas list) into the new saga reconciler branches.

The intent path must be optional for backward-compatibility: if `intent.yml` does not exist, skip all saga reconcile steps silently (existing clusters without intent.yml must not break).

---

## [VALIDATE D-02] — SagaEntry.items identifier: VALIDATED

**Verdict: USE `items: list[str]` WHERE STRINGS ARE SERIES TITLES (not tvdbIds).**

The question was: what identifier should `SagaEntry.items` use for series BoxSet membership?

Options evaluated:
1. **tvdbId (int)** — Jellyfin stores tvdbId in `ProviderIds.Tvdb` and the `/Items?includeItemTypes=Series` endpoint returns this in the `fields=ProviderIds` response. However, `GET /Items` does NOT have a direct `?tvdbId=<exact>` query filter — the HTTP API only exposes `hasTvdbId=true/false` (existence check). Resolution would require: `GET /Items?includeItemTypes=Series&recursive=true&fields=ProviderIds` then filter in-code by `ProviderIds.Tvdb == str(tvdbId)`. Reliable but requires operator to know tvdbIds.
2. **series title (str)** — `GET /Items?includeItemTypes=Series&recursive=true&searchTerm=<title>&fields=ProviderIds` returns fuzzy matches. Operator-friendly, but fuzzy search can return multiple results; reconciler must match on exact `Name` (or warn if ambiguous).
3. **Jellyfin item id (Guid)** — Direct but opaque; changes if library rescans destroy and recreate items (fragile).

**Recommendation: `items: list[str]` with exact series titles.** Rationale: most operator-friendly (mirrors what operators know — "Star Wars: Andor", "The Mandalorian"). Resolution: `GET /Items?includeItemTypes=Series&recursive=true&fields=ProviderIds,Name` then exact-match on `Name` field. Log warning + skip if no exact match (log-and-continue best-effort, consistent with ADR-9). If multiple exact matches exist (unlikely for Series), use the first.

The `items` field is `None` for `kind=movies` (movies BoxSet managed by tmdbboxsets plugin, not by arrconf per-item) and `list[str]` for `kind=series`.

A validator in `SagaEntry` should enforce: `tmdb_collection` is required when `kind == "movies"`, `items` is required when `kind == "series"` (can be empty list for tag-only, non-BoxSet series sagas if desired, but must be explicitly declared).

---

## [VALIDATE D-03] — Radarr Collections API: VALIDATED (HIGH CONFIDENCE)

**Source: Radarr source code (github.com/Radarr/Radarr develop branch), verified 2026-05-31.**

### CollectionResource shape (from `CollectionResource.cs`)

```csharp
public class CollectionResource : RestResource  // inherits: int Id
{
    public string Title { get; set; }
    public string SortTitle { get; set; }
    public int TmdbId { get; set; }       // ← match key for saga→collection binding
    public List<MediaCover> Images { get; set; }
    public string Overview { get; set; }
    public bool Monitored { get; set; }   // ← reconciled field
    public string RootFolderPath { get; set; }  // ← reconciled field
    public int QualityProfileId { get; set; }   // ← reconciled field
    public bool SearchOnAdd { get; set; }        // ← reconciled field
    public MovieStatusType MinimumAvailability { get; set; }  // ← reconciled field
    public List<CollectionMovieResource> Movies { get; set; }
    public int MissingMovies { get; set; }
    public HashSet<int> Tags { get; set; }
}
```

`MinimumAvailability` is an enum (string in JSON): `"tba"`, `"announced"`, `"inCinemas"`, `"released"`, `"deleted"`. Recommended default: `"released"` (operator sees only already-available movies).

### API endpoints (from `CollectionController.cs`)

| Method | Path | Parameters | Behavior |
|--------|------|-----------|----------|
| `GET` | `/api/v3/collection` | `?tmdbId=<int>` (optional) | Returns all collections (or single by tmdbId). Auto-discovered only. |
| `PUT` | `/api/v3/collection/{id}` | Body: `CollectionResource` | Updates single collection by Radarr internal `id`. Returns HTTP 202 Accepted with collection id. |
| `PUT` | `/api/v3/collection` (no id) | Body: `CollectionUpdateResource` | Bulk update multiple collections by `CollectionIds[]`. |

**Key finding: `GET /api/v3/collection` returns only auto-discovered collections.** There is NO POST endpoint to create a collection — Radarr auto-creates a collection record when a movie belonging to a TMDB collection is first added. The controller has no `[HttpPost]` method. D-03 (log-skip absent collections) is the only valid approach.

**Idempotent reconcile pattern:** `GET /api/v3/collection` → build `by_tmdb_id: dict[int, dict]` → for each `kind=movies` saga: lookup `by_tmdb_id.get(saga.tmdb_collection)` → if None: `log.warning("collection_absent_skip", tmdb_collection=saga.tmdb_collection)` + continue → if found: compare reconciled fields → if drift: `PUT /api/v3/collection/{id}`. Second run with no drift = 0 PUT calls.

**Sanitized fixture template:**
```json
{
  "id": 1,
  "title": "James Bond Collection",
  "sortTitle": "james bond collection",
  "tmdbId": 645,
  "monitored": true,
  "qualityProfileId": 3,
  "rootFolderPath": "/media/films",
  "searchOnAdd": true,
  "minimumAvailability": "released",
  "missingMovies": 0,
  "movies": [],
  "tags": [],
  "images": []
}
```

---

## [VALIDATE D-04] — tmdbboxsets plugin: VALIDATED (HIGH CONFIDENCE)

**Source: official Jellyfin plugin repository, verified 2026-05-31.**

### Plugin identity

| Field | Value | Source |
|-------|-------|--------|
| Name | `"TMDb Box Sets"` | `Plugin.cs` `Name` property |
| GUID | `bc4aad2e-d3d0-4725-a5e2-fd07949e5b42` | `Plugin.cs` `Id` property |
| Latest version | `13.0.0.0` (released 2026-05-05) | `https://repo.jellyfin.org/files/plugin/tmdb-box-sets/` |
| Package name | `tmdb-box-sets` | Repo directory name |
| Repo manifest URL | `https://repo.jellyfin.org/files/plugin/manifest.json` | **ALREADY in arrconf.yml `plugin_repositories`** |
| Config fields | `MinimumNumberOfMovies: int` (default 2), `StripCollectionKeywords: bool` (default false) | `PluginConfiguration.cs` |

The repo URL is the same general Jellyfin stable manifest that is already declared in `arrconf.yml` `server_config.plugin_repositories`. No new repository entry needed — the tmdbboxsets plugin is already in the Jellyfin stable catalog.

### How tmdbboxsets works (from `TMDbBoxSetManager.cs`)

The plugin operates as a Jellyfin hosted service (`IHostedService`) with an event-triggered and a scheduled-task path:
1. It listens on `ILibraryManager.ItemUpdated` events (movie metadata refresh triggers it).
2. On trigger, it groups library movies by their `TmdbCollection` provider ID.
3. For each group with ≥ `MinimumNumberOfMovies` movies: if no BoxSet exists with matching TMDB collection provider ID → `CreateCollectionAsync` (creates BoxSet); add missing movies to the BoxSet.
4. It also cleans up orphaned BoxSets (no more matching movies).

**Critical finding:** The plugin creates BoxSets **automatically from movie metadata** — it reads `movie.GetProviderId(MetadataProvider.TmdbCollection)` (set by the Jellyfin TMDb metadata provider). No per-saga configuration is needed beyond installing the plugin. The `tmdb_collection: int` in `SagaEntry` feeds Radarr (which monitors/routes the collection), NOT tmdbboxsets directly.

**No scheduled-task trigger needed from arrconf.** The plugin auto-runs on library item updates. After install + restart, a library scan triggers it. The `MinimumNumberOfMovies = 2` default means a single-film collection will not create a BoxSet — the operator can override this via plugin config if desired (but that's operator UI configuration, not arrconf scope).

**arrconf.yml entry for tmdbboxsets plugin:**
```yaml
# In jellyfin.main.plugins.required:
- name: "TMDb Box Sets"
  install_guid: "bc4aad2e-d3d0-4725-a5e2-fd07949e5b42"
  install_version: "13.0.0.0"
  install_repo_url: "https://repo.jellyfin.org/files/plugin/manifest.json"
  # No config block needed — plugin is auto-configured via its defaults
```

The `install_repo_url` matches an already-declared `plugin_repositories` entry, so the _server_config_equivalent set-by-URL check produces no additional repo diff on the second run.

---

## [HIGH-RISK VALIDATE D-05] — Jellyfin Collections API for series sagas: VIABLE WITH MITIGATION

**Verdict: PROCEED. The Collections API is viable for idempotent reconcile in this tranche, with a required GET-before-POST name check (mirrors Pitfall 16-1 pattern).**

### Collections API endpoints (from `CollectionController.cs` — Jellyfin source)

| Method | Path | Behavior |
|--------|------|----------|
| `POST` | `/Collections` | Creates a BoxSet. Params: `?name=<str>&ids=<comma-separated-guids>`. NOT idempotent by itself — will create duplicates. Returns `CollectionCreationResult { Id: Guid }`. |
| `POST` | `/Collections/{collectionId}/Items` | Adds items to existing BoxSet. `?ids=<comma-separated-guids>`. **Idempotent**: `AddToCollectionAsync` checks `currentLinkedChildrenIds` before adding — already-present items are silently skipped. |
| `DELETE` | `/Collections/{collectionId}/Items` | Removes items from BoxSet. `?ids=<comma-separated-guids>`. |

**There is no `GET /Collections` endpoint.** Listing existing BoxSets uses the standard Items API:
```
GET /Items?includeItemTypes=BoxSet&recursive=true&fields=ProviderIds,Name
```
Returns `Items[]` with `Name: str` and `Id: Guid`. Match existing BoxSet by `Name == saga.name`.

### Idempotent reconcile algorithm for series BoxSets

```
1. GET /Items?includeItemTypes=BoxSet&recursive=true&fields=Name,ProviderIds
   → build by_name: dict[str, Guid]

2. For each kind=series saga:
   a. Resolve member item IDs:
      for title in saga.items:
          GET /Items?includeItemTypes=Series&recursive=true&searchTerm=<title>&fields=Name,ProviderIds
          exact match on Name → get item Guid; log warning + skip if no exact match

   b. If saga.name not in by_name:
      POST /Collections?name=<saga.name>&ids=<resolved-guids>  (creates + populates)
   else:
      collection_id = by_name[saga.name]
      POST /Collections/{collection_id}/Items?ids=<new-resolved-guids>  (idempotent add-only)

3. Sonarr: ensure arrconf-managed tag on resolved series (existing _ensure_managed_tag pattern)
```

**Why POST /Collections is NOT idempotent:** `CreateCollectionAsync` calls `Directory.CreateDirectory(path)` with `name + " [boxset]"` — if run twice, it creates a second `Name2 [boxset]` directory. The GET-before-POST name check is MANDATORY (exactly mirrors Pitfall 16-1 in `_reconcile_libraries`).

**Why AddToCollectionAsync IS idempotent:** Source code (line verified 2026-05-31) explicitly checks `currentLinkedChildrenIds.Contains(id)` before adding. Adding an already-present series is a no-op with no error.

**Fragility assessment:** The primary fragility is series title resolution — if a series title has changed (e.g., show renamed in Jellyfin metadata), `searchTerm` may not find it. Mitigation: log structured warning with `saga_name`, `unresolved_title`, move on (best-effort, consistent with ADR-9 spirit for Jellyfin presentation). The Sonarr tagging branch is independent and always proceeds.

**Fallback NOT taken:** Research finds the API sufficient for reliable idempotent reconcile. The "tag-only + operator-manual BoxSet" fallback is not recommended — the Collections API works with the GET-before-POST guard.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SagaEntry schema + validation | `intent_config.py` | — | Mirrors existing IntentConfig/CrossSeedConfig pattern; central schema file |
| Saga pure generator (SagaEntry → desired resources) | `generators/sagas.py` | — | Mirrors categories.py; no I/O, deterministic, mypy-strict |
| Radarr Collections reconcile | `reconcilers/radarr.py` (new function) | `resources/radarr/collection.py` (new schema) | Follows existing pattern: reconcile fn lives in reconcilers/, schema in resources/radarr/ |
| tmdbboxsets install (two-run) | `reconcilers/jellyfin.py` (`_reconcile_plugins` — existing) | `arrconf.yml` (plugin entry) | Reuse ADR-9 machinery; only wiring needed |
| Series BoxSet create/maintain | `reconcilers/jellyfin.py` (new `_reconcile_sagas_boxsets`) | `generators/sagas.py` (series desired-state) | Jellyfin reconciler owns all Jellyfin API calls |
| Sonarr arrconf-managed tag (series) | `reconcilers/sonarr.py` or `reconcilers/radarr.py` (_ensure_managed_tag) | — | Existing helpers; tag operations already in radarr/sonarr reconcilers |
| apply-time intent.yml load | `__main__.py` (`apply` command) | `intent_config.py` (`load_intent`) | apply is the wiring point; `load_intent` already imported (line 37) |
| Schema regeneration | `schemas/intent-schema.json` (output) | `arrconf intent-schema-gen` (command) | P28 CI guard already covers this; just regenerate after SagaEntry lock |

---

## Standard Stack

No new dependencies required. Phase 29 is pure Python extending existing patterns.

### Core (existing — no additions)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| `pydantic` v2 | pinned in pyproject.toml | SagaEntry schema, CollectionResource schema | `model_config = ConfigDict(extra="forbid")` for SagaEntry; `extra="allow"` for CollectionResource (API may return extra fields) |
| `httpx` | pinned | Radarr PUT + Jellyfin POST /Collections calls | Via existing `client_base.py` clients |
| `structlog` | pinned | Structured log events (`collection_absent_skip`, `boxset_created`, etc.) | Existing pattern |
| `respx` | pinned | Mock HTTP for tests | Existing test pattern |

---

## Architecture Patterns

### System Architecture Diagram

```
intent.yml (hand-edited)
       │
       ▼ load_intent()  [apply command, __main__.py]
IntentConfig.sagas: list[SagaEntry]
       │
       ▼ generators/sagas.py (pure, no I/O)
       ├─ generate_radarr_collections(sagas) → list[DesiredCollection]
       │       ↓
       │  reconcilers/radarr.py :: reconcile_radarr_collections()
       │       │ GET /api/v3/collection   (list all, indexed by tmdbId)
       │       │ GET /api/v3/qualityprofile  (name → id)
       │       │ PUT /api/v3/collection/{id}  (on drift)
       │       └→ Radarr (live cluster API)
       │
       └─ generate_jellyfin_sagas(sagas) → SagasDesiredState
               ├─ plugin_entry: PluginEntry (tmdbboxsets)
               │       ↓
               │  reconcilers/jellyfin.py :: _reconcile_plugins()  [REUSE]
               │       │ GET /Plugins
               │       │ POST /Packages/Installed/{name}  (Run N — install)
               │       └→ Jellyfin (live cluster API)
               │
               └─ series_boxsets: list[SeriesBoxSetDesired]
                       ↓
               reconcilers/jellyfin.py :: _reconcile_sagas_boxsets()  [NEW]
                       │ GET /Items?includeItemTypes=BoxSet  (existing collections)
                       │ GET /Items?includeItemTypes=Series&searchTerm=  (member resolution)
                       │ POST /Collections?name=  (create, if absent)
                       │ POST /Collections/{id}/Items?ids=  (add members, idempotent)
                       └→ Jellyfin (live cluster API)
```

### Recommended Module Layout (new files only)

```
tools/arrconf/arrconf/
├── generators/
│   └── sagas.py           # NEW: pure generators, SagaEntry → desired resources
├── resources/
│   └── radarr/
│       └── collection.py  # NEW: CollectionResource pydantic schema
└── reconcilers/
    ├── radarr.py           # MODIFIED: add reconcile_radarr_collections() + wiring
    └── jellyfin.py         # MODIFIED: add _reconcile_sagas_boxsets()
intent_config.py             # MODIFIED: tighten SagaEntry extra="forbid" + full fields
__main__.py                  # MODIFIED: load_intent in apply + intent path option
```

### Pattern 1: Radarr Collection Reconcile (idempotent PUT-on-drift)

```python
# Source: verified from Radarr CollectionController.cs + CollectionResource.cs

COLLECTION_PATH = "/collection"
QUALITY_PROFILE_PATH = "/qualityprofile"

def reconcile_radarr_collections(
    client: RadarrClient,
    sagas: list[SagaEntry],
    dry_run: bool,
) -> list[str]:
    """Reconcile Radarr Collections from kind=movies SagaEntry list.
    GET-match by tmdbId, PUT-on-drift. Absent collections → log-skip (D-03).
    """
    # Resolve quality profile names → ids (read-only GET, no side effects)
    raw_qp = client.get(QUALITY_PROFILE_PATH)
    qp_by_name: dict[str, int] = {qp["name"]: qp["id"] for qp in raw_qp}

    # GET all collections, index by tmdbId
    raw_collections = client.get(COLLECTION_PATH)
    by_tmdb_id: dict[int, dict] = {c["tmdbId"]: c for c in raw_collections}

    movie_sagas = [s for s in sagas if s.kind == "movies"]
    actions: list[str] = []

    for saga in movie_sagas:
        assert saga.tmdb_collection is not None  # enforced by pydantic validator
        cluster = by_tmdb_id.get(saga.tmdb_collection)

        if cluster is None:
            # D-03: Radarr auto-discovers collections only when ≥1 member movie present
            log.warning(
                "collection_absent_skip",
                tmdb_collection=saga.tmdb_collection,
                saga_name=saga.name,
                hint="Add at least one movie from this collection to Radarr first",
            )
            continue

        # Resolve profile name → id
        if saga.profile not in qp_by_name:
            raise ConfigError(f"quality profile '{saga.profile}' not found in Radarr")
        quality_profile_id = qp_by_name[saga.profile]

        # Build desired state (fields we own)
        desired = {
            "monitored": True,
            "qualityProfileId": quality_profile_id,
            "rootFolderPath": saga.root,
            "searchOnAdd": True,
            "minimumAvailability": "released",
        }
        # Drift check: only PUT if something changed
        drift_fields = {
            k for k, v in desired.items()
            if cluster.get(k) != v
        }
        if not drift_fields:
            log.info("collection_no_op", saga_name=saga.name, tmdb_id=saga.tmdb_collection)
            continue

        if dry_run:
            log.info("dry_run_skip", resource="collection", saga_name=saga.name, drift=list(drift_fields))
            actions.append(f"collection:dry_run:{saga.name}")
            continue

        # PUT with cluster's full body + desired overrides (re-inject id)
        body = dict(cluster)  # start from cluster state
        body.update(desired)
        body["id"] = cluster["id"]  # Pitfall 4 pattern: re-inject id
        client.put(COLLECTION_PATH, id=cluster["id"], json=body)
        log.info("collection_updated", saga_name=saga.name, tmdb_id=saga.tmdb_collection, drift=list(drift_fields))
        actions.append(f"collection:updated:{saga.name}")

    return actions
```

### Pattern 2: Jellyfin Series BoxSet Reconcile (GET-before-POST idempotence)

```python
# Source: verified from Jellyfin CollectionController.cs + CollectionManager.cs

ITEMS_PATH = "/Items"
COLLECTIONS_PATH = "/Collections"

def _reconcile_sagas_boxsets(
    client: JellyfinClient,
    series_sagas: list[SagaEntry],  # kind=series only
    dry_run: bool,
) -> list[str]:
    """Reconcile series-saga Jellyfin BoxSets.

    Idempotent contract:
    - POST /Collections is NOT idempotent alone → MUST check existing by name first
      (mirrors Pitfall 16-1 from _reconcile_libraries).
    - POST /Collections/{id}/Items IS idempotent (AddToCollectionAsync skips duplicates).
    - Best-effort: unresolved series titles log warning + skip (ADR-9 spirit).
    """
    if not series_sagas:
        return []

    # Step 1: GET existing BoxSets (index by Name for idempotent create)
    raw_boxsets = client.get(
        ITEMS_PATH,
        params={"includeItemTypes": "BoxSet", "recursive": "true", "fields": "Name,ProviderIds"},
    )
    existing_by_name: dict[str, str] = {
        item["Name"]: str(item["Id"])
        for item in raw_boxsets.get("Items", [])
        if item.get("Name") and item.get("Id")
    }

    actions: list[str] = []
    for saga in series_sagas:
        # Step 2: Resolve member series titles → Jellyfin item GUIDs
        resolved_ids: list[str] = []
        for title in (saga.items or []):
            results = client.get(
                ITEMS_PATH,
                params={
                    "includeItemTypes": "Series",
                    "recursive": "true",
                    "searchTerm": title,
                    "fields": "Name,ProviderIds",
                },
            )
            exact = next(
                (item for item in results.get("Items", []) if item.get("Name") == title),
                None,
            )
            if exact is None:
                log.warning(
                    "series_saga_member_unresolved",
                    saga_name=saga.name,
                    title=title,
                    hint="Check that the series name in intent.yml matches Jellyfin library exactly",
                )
                continue
            resolved_ids.append(str(exact["Id"]))

        if not resolved_ids and saga.items:
            log.warning("series_saga_no_members_resolved", saga_name=saga.name)

        # Step 3: Create or update BoxSet
        if saga.name not in existing_by_name:
            # Pitfall 16-1 mirror: name absent → safe to POST
            if dry_run:
                log.info("dry_run_skip", resource="saga_boxset_create", saga_name=saga.name)
                actions.append(f"saga_boxset:dry_run_create:{saga.name}")
                continue
            result = client._request(
                "POST",
                COLLECTIONS_PATH,
                params={"name": saga.name, "ids": ",".join(resolved_ids)},
            )
            log.info("saga_boxset_created", saga_name=saga.name, member_count=len(resolved_ids))
            actions.append(f"saga_boxset:created:{saga.name}")
        else:
            # BoxSet exists: add missing members (POST /Collections/{id}/Items is idempotent)
            collection_id = existing_by_name[saga.name]
            if not resolved_ids:
                log.info("saga_boxset_no_op", saga_name=saga.name)
                continue
            if dry_run:
                log.info("dry_run_skip", resource="saga_boxset_items", saga_name=saga.name)
                actions.append(f"saga_boxset:dry_run_items:{saga.name}")
                continue
            client._request(
                "POST",
                f"{COLLECTIONS_PATH}/{collection_id}/Items",
                params={"ids": ",".join(resolved_ids)},
            )
            log.info("saga_boxset_items_added", saga_name=saga.name, member_count=len(resolved_ids))
            actions.append(f"saga_boxset:items_added:{saga.name}")

    return actions
```

### Pattern 3: SagaEntry locked schema

```python
# Source: P28 intent_config.py SagaEntry stub; full schema per D-02

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class SagaEntry(BaseModel):
    """A single saga declaration (Phase 29 locked schema — D-02).

    kind=movies: tmdb_collection REQUIRED; profile + root REQUIRED; items ignored.
    kind=series: items OPTIONAL (titles of member series); profile/root/tmdb_collection not used.
    """
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Saga display name; also the Jellyfin BoxSet name for series.")
    kind: Literal["movies", "series"] = Field(description="Discriminator.")
    tmdb_collection: int | None = Field(
        default=None,
        description="TMDB collection id. Required when kind=movies.",
    )
    profile: str = Field(
        default="",
        description="Radarr quality profile name. Required when kind=movies.",
    )
    root: str = Field(
        default="",
        description="Radarr root folder path. Required when kind=movies.",
    )
    items: list[str] | None = Field(
        default=None,
        description="Series titles for Jellyfin BoxSet membership. kind=series only.",
    )

    @model_validator(mode="after")
    def check_kind_constraints(self) -> "SagaEntry":
        if self.kind == "movies" and self.tmdb_collection is None:
            raise ValueError("tmdb_collection is required when kind=movies")
        if self.kind == "movies" and not self.profile:
            raise ValueError("profile is required when kind=movies")
        if self.kind == "movies" and not self.root:
            raise ValueError("root is required when kind=movies")
        return self
```

### Pattern 4: apply-time intent.yml wiring in __main__.py

```python
# Source: existing __main__.py pattern; apply callback at line 178

@app.callback()
def main(
    ctx: typer.Context,
    config: Path = typer.Option(Path("/etc/arrconf/arrconf.yml"), ...),
    intent: Path = typer.Option(
        Path("/etc/arrconf/intent.yml"),
        "--intent",
        help="Path to intent.yml (sagas, tools). Optional — skipped if absent.",
    ),
    log_level: str = ...,
) -> None:
    ctx.obj = {"config_path": config, "intent_path": intent}


@app.command()
def apply(ctx, apps, dry_run):
    root = load_config(ctx.obj["config_path"])  # existing

    # New: load intent (optional — backward-compatible)
    intent_path: Path = ctx.obj["intent_path"]
    intent_cfg: IntentConfig | None = None
    if intent_path.exists():
        try:
            intent_cfg = load_intent(intent_path)
        except ConfigError as e:
            log.error("intent_config_error", error=str(e))
            raise typer.Exit(code=2) from e
    # ... existing app branches ...
    # New saga branches at the end:
    if intent_cfg is not None and intent_cfg.sagas:
        if "radarr" in targets and "main" in root.radarr and radarr_api_key:
            # reconcile_radarr_collections(radarr_client, intent_cfg.sagas, dry_run)
            pass
        if "jellyfin" in targets and "main" in root.jellyfin and jellyfin_api_key:
            # _reconcile_sagas_boxsets(jellyfin_client, series_sagas, dry_run)
            pass
```

**Ordering constraint:** saga reconcile branches run AFTER the existing app branches (Radarr tags/DCs must already be reconciled before collections need the quality profile; Sonarr tags must exist before arrconf-managed tagging of series).

### Anti-Patterns to Avoid

- **POST /Collections without GET-before-POST name check:** Creates duplicate BoxSets with `Name2`, `Name3` suffixes. Use `GET /Items?includeItemTypes=BoxSet` snapshot FIRST.
- **Using Radarr `GET /api/v3/collection?tmdbId=<id>` for match-only:** Works for single lookups but requires N GET calls. Use bulk `GET /api/v3/collection` and build an in-memory dict (same pattern as all other reconcilers).
- **Embedding `movies[].tmdbId` resolution in the Collections reconciler:** The `movies[]` array in CollectionResource is Radarr-read-only (list of movies currently in the collection); arrconf does NOT write to this array.
- **Calling tmdbboxsets plugin's scheduled task via API:** Not needed. The plugin auto-triggers on library item updates. No arrconf API call required post-install.
- **Using `profile` and `root` for `kind=series` sagas:** These fields are Radarr-specific (movies only). SagaEntry validator blocks this via `extra="forbid"` and a `model_validator`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Quality profile name → id resolution | Custom lookup | `GET /api/v3/qualityprofile` name-match (existing pattern in arrconf) | Already proven in codebase |
| Movie BoxSet grouping by TMDB collection | Custom aggregation | tmdbboxsets plugin | Plugin does it correctly from Jellyfin metadata; re-implementing it is error-prone and duplicates functionality |
| Plugin install machinery | New install code | `_reconcile_plugins` ADR-9 two-run model | Already battle-tested with Intro Skipper; exact same interface |
| Drift detection for Collection fields | Custom dict diff | Explicit field-by-field comparison (no generic `diff_models` needed) | CollectionResource has mixed types (bool, int, str, enum); direct comparison is clearer and avoids the pydantic `extra="allow"` drift |

---

## Common Pitfalls

### Pitfall 1: Radarr PUT /collection body must include `id` field
**What goes wrong:** `client.put(COLLECTION_PATH, id=cluster_id, json=desired_dict)` passes `id` in the URL but if the JSON body doesn't also contain `id`, the Radarr API may reject or misroute it (Pitfall 4 pattern from existing reconcilers).
**Why it happens:** `merge_fields_for_put` strips read-only fields including `id`; CollectionResource has an `Id` field.
**How to avoid:** Start from `body = dict(cluster)` (full cluster state), override desired fields, then ensure `body["id"] = cluster["id"]` is set before PUT.

### Pitfall 2: POST /Collections without name-check creates duplicates
**What goes wrong:** Calling `POST /Collections?name=Star Wars` twice creates `Star Wars [boxset]` and then a second `Star Wars2 [boxset]` directory.
**Why it happens:** `CreateCollectionAsync` calls `Directory.CreateDirectory` unconditionally.
**How to avoid:** Always `GET /Items?includeItemTypes=BoxSet` and check `by_name` BEFORE any `POST /Collections` call. Exact same mitigation as Pitfall 16-1 in `_reconcile_libraries`.

### Pitfall 3: tmdbboxsets needs Jellyfin restart before activation
**What goes wrong:** Run N installs the plugin but it's not Active yet; reconciler tries to enable and gets wrong status.
**Why it happens:** Jellyfin only loads plugins at startup (ADR-9 two-run model, already known).
**How to avoid:** The existing `_reconcile_plugins` two-run model handles this correctly. Run N queues install + logs `plugin_install_queued` warning with kubectl rollout restart hint. Run N+1 enables.

### Pitfall 4: `GET /api/v3/collection` returns empty for unseen sagas
**What goes wrong:** A newly declared movie saga has its `tmdb_collection` in `intent.yml` but returns nothing from Radarr because no member movie has been added yet.
**Why it happens:** Radarr auto-discovers a collection only when ≥1 member movie exists in the library (documented in DESIGN §3, verified in controller — no POST endpoint).
**How to avoid:** D-03 log-skip pattern is the correct behavior. Log at WARNING level with a clear `hint` field pointing the operator to add a movie first.

### Pitfall 5: Series title fuzzy search returns multiple items
**What goes wrong:** `searchTerm=Andor` returns both "Andor" (the series) and potentially other items if Jellyfin fuzzy-matches partial names.
**Why it happens:** Jellyfin `SearchTerm` is a fuzzy substring search, not an exact-match filter.
**How to avoid:** Always filter results to `item["Name"] == title` (exact string match after the search). Log warning if no exact match; skip the item rather than using a wrong series.

### Pitfall 6: CollectionResource `minimumAvailability` is a C# enum string
**What goes wrong:** Sending `"Released"` (PascalCase) vs `"released"` (camelCase) may cause a 400 from Radarr.
**Why it happens:** C# enum serialization conventions vary by Radarr version.
**How to avoid:** Mirror the existing `MovieStatusType` values from Radarr's actual API responses (typically camelCase in v3 JSON: `"tba"`, `"announced"`, `"inCinemas"`, `"released"`, `"deleted"`). Use `"released"` as default. If the cluster returns `"Released"`, match what it sends back when building desired state.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 29 |
|-----------|-------------------|
| Idempotence RÈGLE D'OR: GET-match-PUT-on-drift, prune opt-in, arrconf-managed tag | Radarr Collections reconciler: drift-only PUT; Jellyfin BoxSets: GET-before-POST; Sonarr tagging: `_ensure_managed_tag` |
| Python triade: `ruff format --check && ruff check && mypy` must pass | New files must be mypy-strict on public signatures; test files may have pre-existing mypy noise (ignore new errors only) |
| ≥70% coverage on reconcilers + respx mocks | New `reconcile_radarr_collections` and `_reconcile_sagas_boxsets` need unit tests with respx mocks; NO live API calls in CI |
| Release pin co-bump: Python change → arrconf.image.tag bump same commit | Phase 29 ships Python reconciler code → MUST co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` from `0.18.0` to `0.19.0` in the same commit |
| ADR-5 frontière: NEVER touch quality_profiles/custom_formats from arrconf | `GET /api/v3/qualityprofile` for name→id resolution is read-only and explicitly allowed; no write to quality profiles |
| ADR-9: Jellyfin plugin two-run model | tmdbboxsets installation reuses `_reconcile_plugins` exactly — no new install machinery |
| extra="forbid" on all Section pydantic models | SagaEntry must switch from `extra="allow"` (P28 stub) to `extra="forbid"` (D-02) |
| ADR-6: snapshot raw BEFORE first live cluster test | Operator MUST run `tools/snapshot/snapshot.sh` before first `arrconf apply` with sagas |
| No secrets in repo, env vars only | No new env vars needed for sagas (RADARR_API_KEY, JELLYFIN_API_KEY already used) |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Radarr Collections: no arrconf support | GET-match-PUT idempotent reconcile from sagas | Phase 29 (this) | New capability |
| Jellyfin BoxSets: manual UI creation | Curated BoxSet via `/Collections` API + arrconf-managed tag | Phase 29 (this) | Automates series presentation |
| Jellyfin tmdbboxsets: not installed | Plugin installed via existing ADR-9 two-run model | Phase 29 (this) | Movie BoxSets auto-created from TMDB metadata |
| SagaEntry: P28 stub `extra="allow"` name-only | Full locked schema `extra="forbid"` with kind/tmdb_collection/profile/root/items | Phase 29 (this) | CI blocks unknown fields; schema is authoritative |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `minimumAvailability` enum values in Radarr v3 JSON are camelCase (`"released"` not `"Released"`) | Pitfall 6 / CollectionResource | A wrong casing would cause a 400 from Radarr PUT; mitigated by reading cluster value first and matching it |
| A2 | The Jellyfin `GET /Items?includeItemTypes=BoxSet` returns all BoxSets including arrconf-created ones | Jellyfin BoxSet reconcile | If BoxSets are not in the Items index yet (right after creation), second-run detection may fail; mitigated by using Name-match on a pre-run snapshot |
| A3 | `POST /Collections/{id}/Items` accepts GUID format as comma-separated string in `?ids=` param | Jellyfin BoxSet reconcile | Wrong format → 400 or silent failure; can be tested against live cluster before merge |

**Claims A1-A3 are LOW confidence (assumed from source code reading). Recommend validating A3 with a live test on the cluster before merging the implementation plan.**

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Radarr `/api/v3/collection` endpoint | SAGAS-02 | Assumed ✓ (standard Radarr v3 since 4.x) | Radarr 4.x+ | None — required |
| Jellyfin `POST /Collections` endpoint | SAGAS-04 | Assumed ✓ (standard Jellyfin since 10.8+) | Jellyfin 10.11.x (cluster) | None — required |
| tmdbboxsets v13 in Jellyfin stable manifest | SAGAS-03 | ✓ confirmed 2026-05-31 | 13.0.0.0 | — |
| `RADARR_API_KEY` env var | SAGAS-02 | ✓ already declared | — | None — already used |
| `JELLYFIN_API_KEY` env var | SAGAS-03, SAGAS-04 | ✓ already declared | — | None — already used |

---

## Open Questions (RESOLVED)

All three are resolved for planning. A1/A2 carry a live-cluster confirmation step (baked into the plan actions as "mirror the cluster value", never a hardcoded guess); A3 is resolved by design.

1. **minimumAvailability casing in Radarr JSON responses**
   - What we know: C# enum `MovieStatusType` has values `tba`, `announced`, `inCinemas`, `released`, `deleted` (from codebase).
   - RESOLVED: Do NOT hardcode casing — the reconciler PUTs `body = dict(cluster); body.update(desired)`, so the cluster's own enum casing is preserved verbatim for every non-overridden field. Generator default `"released"`. Plan 29-02 implements this cluster-mirroring; live confirmation is a test-time observation, not a planning blocker.

2. **`POST /Collections/{id}/Items` IDs format**
   - What we know: Jellyfin `Guid[] ids`, comma-delimited query param (controller signature).
   - RESOLVED: Use the `Id` string exactly as returned by `GET /Items` (Jellyfin returns lowercase `8-4-4-4-12` UUIDs) — no reformatting, no braces. Plan 29-03 passes the API-returned `Id` verbatim. Source-verified via CollectionController.cs; live confirmation recommended pre-merge but non-blocking.

3. **Sonarr arrconf-managed tag for series sagas: which reconciler step?**
   - RESOLVED: Sub-step inside the Jellyfin saga branch in `__main__.py` (after BoxSet creation), using the Sonarr client; guarded on `"sonarr" in targets and settings.sonarr_api_key`. Keeps saga operations together. Plan 29-03 implements this with the full GET /series → PUT /series/editor tagging pattern (mirror `_reconcile_series_tags`).

---

## Sources

### Primary (HIGH confidence)
- `github.com/Radarr/Radarr/blob/develop/src/Radarr.Api.V3/Collections/CollectionController.cs` — GET, PUT endpoint signatures, no POST (auto-discovered only)
- `github.com/Radarr/Radarr/blob/develop/src/Radarr.Api.V3/Collections/CollectionResource.cs` — full CollectionResource field list
- `github.com/jellyfin/jellyfin/blob/master/Jellyfin.Api/Controllers/CollectionController.cs` — POST /Collections, POST /{id}/Items, DELETE /{id}/Items signatures
- `github.com/jellyfin/jellyfin/blob/master/Emby.Server.Implementations/Collections/CollectionManager.cs` — `CreateCollectionAsync` (NOT idempotent), `AddToCollectionAsync` (IS idempotent — skips duplicates by id check)
- `github.com/jellyfin/jellyfin-plugin-tmdbboxsets/blob/master/Jellyfin.Plugin.TMDbBoxSets/Plugin.cs` — GUID `bc4aad2e-d3d0-4725-a5e2-fd07949e5b42`, Name `"TMDb Box Sets"`
- `github.com/jellyfin/jellyfin-plugin-tmdbboxsets/blob/master/Jellyfin.Plugin.TMDbBoxSets/TMDbBoxSetManager.cs` — how plugin auto-groups movies by TmdbCollection ProviderId
- `github.com/jellyfin/jellyfin-plugin-tmdbboxsets/blob/master/Jellyfin.Plugin.TMDbBoxSets/Configuration/PluginConfiguration.cs` — config fields: `MinimumNumberOfMovies`, `StripCollectionKeywords`
- `https://repo.jellyfin.org/files/plugin/tmdb-box-sets/` — version 13.0.0.0 latest (2026-05-05)
- `/data/projets/perso/arr-stack/tools/arrconf/arrconf/__main__.py` — existing `apply` flow, `load_intent` import at line 37, current arrconf.yml config sections
- `/data/projets/perso/arr-stack/tools/arrconf/arrconf/intent_config.py` — existing `SagaEntry` stub (P28)
- `/data/projets/perso/arr-stack/tools/arrconf/arrconf/reconcilers/radarr.py` — `_reconcile_list_resource`, `_execute`, `_ensure_managed_tag` patterns
- `/data/projets/perso/arr-stack/tools/arrconf/arrconf/reconcilers/jellyfin.py` — `_reconcile_plugins` two-run model (ADR-9), `_reconcile_libraries` Pitfall 16-1 pattern

### Secondary (MEDIUM confidence)
- `github.com/jellyfin/jellyfin/blob/master/Jellyfin.Api/Controllers/ItemsController.cs` — `GET /Items` signature with `includeItemTypes=BoxSet/Series`, `searchTerm`, `hasTvdbId` parameters (verified titles-based series search approach)
- `/data/projets/perso/arr-stack/charts/arr-stack/files/arrconf.yml` — existing plugin_repositories structure, intro-skipper entry as template for tmdbboxsets

### Tertiary (LOW confidence)
- A1-A3 open questions above are LOW confidence (inferred from source code, not tested against live cluster)

---

## Metadata

**Confidence breakdown:**
- Radarr Collections API (shape, GET/PUT behavior, no POST): HIGH — source code verified
- tmdbboxsets GUID/version/behavior: HIGH — official plugin repo verified
- Jellyfin /Collections POST/AddItems behavior: HIGH — source code verified (idempotent add, non-idempotent create)
- SagaEntry items identifier choice (titles vs tvdbIds): MEDIUM — reasoned from Items API capabilities
- minimumAvailability casing / POST ids format: LOW — inferred, needs live validation

**Research date:** 2026-05-31
**Valid until:** 2026-06-30 (APIs stable; Jellyfin plugin version may update but GUID is stable)
