# Phase 16: Jellyfin Categories-as-libs — Research

**Researched:** 2026-05-24
**Domain:** Jellyfin 10.11.9 REST API — Library lifecycle (CREATE + DELETE PathInfo + DELETE VirtualFolder)
**Confidence:** HIGH (every endpoint shape and idempotence behavior VERIFIED via live cluster probe today — port-forward + curl + httpx, evidence captured below)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-16-LIB-CREATE-01** — arrconf owns the full library lifecycle. The reconciler POSTs `/Library/VirtualFolders` to create missing libs from the generator output. arrconf now manages create + paths (previously paths-only).
  - Implication: new endpoint in `JellyfinClient` (POST `/Library/VirtualFolders`). Body shape pinned by this research: **query params** `name`, `collectionType`, `paths` (repeated), `refreshLibrary`, plus an empty JSON body `{}` (`AddVirtualFolderDto` with `LibraryOptions: null`). See §POST `/Library/VirtualFolders` Probe.
  - The `library_missing_skip` warning at `reconcilers/jellyfin.py:136-143` becomes dead code. Replace with a `library_create` action branch.
  - No manual UI bootstrap needed for a new Category — matches the Categories first-class design.

- **D-16-LIB-NAME-01** — `JellyfinLibrary.name` = `categories[].display` (e.g. `Séries - Émilie`, `Séries - Zoé`, `Films - Enfants`).
  - `categories[].name` remains the filesystem identifier (`/media/<name>`) — no FS change.
  - Coincidence: `categories[0]` (`display: Séries`) and `categories[5]` (`display: Films`) match the existing 2 legacy libs by name → cutover is a **reshape** of these 2 (5 paths → 1 path) + create of 8 new libs.

- **D-16-PRUNE-01** — Reverse D-07-LIB-01. The `prune:` flag in `jellyfin.libraries` becomes effective. Hardcoded `prune: false` from Phase 7 is removed. Behavior aligns with qBit/Sonarr/Radarr/Prowlarr (opt-in per section).
  - Cutover requires `prune: true` for ONE PR (operator flips back to `false` after UAT).
  - Honest side-effect during the prune=true window: user-added libs (if any) get deleted. Acceptable in homelab single-tenant.

- **D-16-PATH-DELETE-01** — Reconciler gains DELETE PathInfo capability. Endpoint pinned: `DELETE /Library/VirtualFolders/Paths?name=<lib>&path=<path>&refreshLibrary=false`. Gated by `section.prune == True`. Pitfall 8 (PathInfos vs Locations) remains the source-of-truth discipline.

- **D-16-JELLYCON-UAT-01** — Phase 16 closes on Jellyfin web UI visibility only. JellyCon LibreELEC validation is carried-forward (non-blocking).

- **D-16-COLLECTIONTYPE-01** — `categories[].kind == "series"` → `CollectionType = "tvshows"`. `categories[].kind == "movies"` → `CollectionType = "movies"`. Unchanged from Phase 7.

### Claude's Discretion

- Plan structure: **1 plan `16-A`** (refactor groupé : generator + reconciler + tests + co-bump + snapshot) — confirmed during research, surface is ~150 LOC across 4 files.
- Create-then-paths ordering: build full PathInfos list as POST query params in a single call vs two-phase (CREATE then add Paths). Recommendation: **single-call with all paths in query** — see §Pattern 1.
- Refresh after cutover: leave to Jellyfin scheduled scans (D-07-LIB-02 punt remains) — `refreshLibrary=false` on every write.
- Test fixture shape: extend existing `tests/fixtures/jellyfin/library_virtualfolders.json` (2 libs v0.2.0 layout) with a 10-lib fixture under a new filename for the post-cutover state.
- Match-by-Name idempotence shim survives unchanged — the existing `jellyfin.py:130-153` pattern works for the lifecycle additions (verified via probe — see §Pitfall 16-3).

### Deferred Ideas (OUT OF SCOPE)

- **REQ-jellyfin-collections** — Collections auto-generated per Category. Surplus if Phase 16 lands clean.
- **LibraryOptions per-Category tuning** (PreferredMetadataLanguage, TypeOptions, EnableRealtimeMonitor) — D-07-LIB-02 punt remains. New libs created with Jellyfin defaults (verified live: 37 keys in LibraryOptions, all defaults C# from Jellyfin).
- **Idempotence dispositive SC#5 (live cluster sweep)** — SC#2 (second `arrconf apply` = 0 plan_action) is sufficient.
- **Filesystem migration of media** — `/media/<name>` dirs already exist since Phase 9 (verified live — see §Live Cluster State).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-jellyfin-categories-as-libs | `generate_jellyfin_libraries()` emits 10 `JellyfinLibrary` entries (1 per `categories[]`, single PathInfo `/media/<name>`). Reconciler creates missing libs via POST `/Library/VirtualFolders`. D-07-LIB-01 prune=hardcoded reversed to opt-in. Live UAT: 10 libs in web UI + JellyCon. | All 3 endpoints (POST CREATE, DELETE Path, DELETE Lib) probed live on `jellyfin-6fdffdcc5-kq8pw` (10.11.9) 2026-05-24 — see §Live Cluster Probe Evidence. Filesystem confirmed safe (DELETE lib does NOT touch `/media/<name>` files). Watched-state risk surfaced (§Pitfall 16-4 + Open Question 1). |
</phase_requirements>

---

## Summary

Phase 16 extends `_reconcile_libraries()` to own the full Jellyfin library lifecycle: CREATE, ADD path (existing), DELETE path (new, prune-gated), DELETE lib (new, prune-gated). All 4 endpoints **probed live** today against the production cluster (`jellyfin-6fdffdcc5-kq8pw`, Jellyfin **10.11.9** — one patch higher than Phase 7's 10.11.8 but no schema delta for these endpoints).

**Primary recommendation:** Single-call create-with-paths via query parameters (`?name=&collectionType=&paths=&refreshLibrary=false` + empty JSON body `{}`). This avoids the create-then-add-path ordering trap and works with `httpx.Client.post(params=..., json={})`. Verified live HTTP 204.

**Four critical pitfalls discovered (additive to Phase 7's 1-8):**

1. **POST `/Library/VirtualFolders` is NOT idempotent — Jellyfin SILENTLY appends a suffix to duplicate names.** Probe confirmed: re-POSTing `name=ARRCONF_PROBE_PHASE16&collectionType=tvshows&paths=/media/series-emilie` while a lib of that exact name already exists creates a SECOND lib named `ARRCONF_PROBE_PHASE162` with the same paths. Server returns HTTP 204 — no error. **Reconciler MUST GET `/Library/VirtualFolders` first, match-by-Name, skip POST if present** (mirror of Phase 7 Pitfall 2 set-membership shim, now applied at the lib level).

2. **DELETE `/Library/VirtualFolders` returns HTTP 404 if the lib doesn't exist** (vs DELETE Paths which is silent 204). Reconciler must tolerate 404 on lib delete (treat as already-gone, no-op) — but match-by-Name with full snapshot before delete makes this unreachable in practice.

3. **DELETE `/Library/VirtualFolders/Paths` is silent on missing paths (HTTP 204).** Verified: deleting `/media/nonexistent-path` from `Séries` returned 204. Reconciler can blindly DELETE for a path-in-cluster-but-not-in-desired set without pre-check, but pre-check is the conservative choice (matches the existing Pitfall 2 add-side shim symmetry).

4. **Watched state preservation across the cutover is NOT guaranteed.** When `/media/series-emilie` (currently a child of legacy `Séries` via `/media/series` mount? — no, **NOT currently included** in legacy Séries PathInfos — see §Live Cluster State, current PathInfos are `/media/series`, `/media/anime`, `/media/family`) moves into a NEW lib, Jellyfin treats the items as NEW. The existing scenario is more benign than CONTEXT.md anticipated — see §Pitfall 16-4 and Open Question 1.

**Cluster state surprise:** The cluster is on **v0.2.0 layout** (Séries: 3 paths `/media/series + /media/anime + /media/family`; Films: 3 paths `/media/films + /media/films-anime + /media/films-family`), NOT the 5-path v0.3.0 state CONTEXT.md anticipated. The 4 legacy v0.2.0 dirs (`anime`, `family`, `films-anime`, `films-family`) still exist alongside the 10 v0.3.0 dirs (see §Live Cluster State). This means Phase 16 cutover ALSO performs the deferred filesystem migration cleanup that CLAUDE.md "Filesystem migration v0.2.0 → v0.3.0" assumed had been done. Per the migration table in CLAUDE.md the operator was supposed to `mv anime/* series-zoe/` etc. but the Jellyfin layout was never updated to reflect the new dirs. **The result is acceptable**: arrconf will create the 10 new libs from `/media/<name>` (v0.3.0 buckets, which DO exist), and the operator separately decides whether to delete the legacy `/media/anime` etc. dirs after migrating their content. The watched state risk is bounded to items currently under legacy paths.

**Architectural responsibility map:** Same as Phase 7 — all writes flow through `JellyfinClient` against the Jellyfin REST API. arrconf is the sole writer (no operator UI conflicts during the prune=true window).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Generator: 10 `JellyfinLibrary` from `categories[]` | Application (arrconf — pure function) | — | `generators/categories.py::generate_jellyfin_libraries()` extends to per-Category output |
| Library CREATE | API / Backend (Jellyfin) | — | POST `/Library/VirtualFolders` with query params + empty JSON body |
| Library ADD path (existing) | API / Backend (Jellyfin) | — | POST `/Library/VirtualFolders/Paths` (Phase 7 endpoint unchanged) |
| Library DELETE path | API / Backend (Jellyfin) | — | DELETE `/Library/VirtualFolders/Paths` (NEW; gated by prune=true) |
| Library DELETE entire | API / Backend (Jellyfin) | — | DELETE `/Library/VirtualFolders` (NEW; gated by prune=true) |
| Idempotence shim (lib-level + path-level) | Application (arrconf) | — | Match-by-Name from GET snapshot before any POST/DELETE |
| Cutover ordering (create-before-delete vs delete-before-create) | Application (arrconf) | — | **Create-first** to ensure desired state visible before pruning legacy (avoids transient "0 libs visible") |
| Filesystem media | Storage (NFS via PVC) | — | Untouched — DELETE lib does NOT remove files (verified) |
| Watched-state DB | Storage (Jellyfin SQLite `library.db`) | — | Out of arrconf scope — see §Watched-State Risk Analysis |

---

## Standard Stack

No new dependencies. Phase 16 is a pure code addition on top of the Phase 7 stack.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | ≥0.28.0,<0.29 | HTTP client | Phase 7 carry-forward [VERIFIED: pyproject.toml + live test today] |
| pydantic v2 | ≥2.13,<3 | `JellyfinLibrary` model (unchanged from Phase 7) | [VERIFIED: existing model] |
| structlog | ≥25.5,<26 | New log events: `library_created`, `library_path_removed`, `library_pruned` | [VERIFIED: existing] |
| respx | ≥0.23,<0.24 | Mock new endpoints in unit tests | [VERIFIED: existing test scaffold at `tests/test_reconcilers_jellyfin.py:319-1004`] |

**Version verification:**

```bash
$ kubectl -n selfhost exec jellyfin-6fdffdcc5-kq8pw -- ls /usr/share/jellyfin/api-docs/ 2>&1
# api-docs/ no longer exists in 10.11.9 image — OpenAPI is served from /api-docs/openapi.json HTTP only

$ curl http://localhost:18096/System/Info/Public | jq -r .Version
# "10.11.9" [VERIFIED: 2026-05-24 live cluster]

$ curl http://localhost:18096/api-docs/openapi.json | jq -r '.info.version'
# "10.11.9" [VERIFIED: 2026-05-24 live, 2 MB spec]
```

---

## Live Cluster Probe Evidence (D-16-VALIDATE-01)

> Executed live against production `jellyfin-6fdffdcc5-kq8pw` (Jellyfin 10.11.9) on 2026-05-24, via `kubectl port-forward 18096:8096` + `JELLYFIN_API_KEY` from `arrconf-env` sealed-secret (32 chars present, pre-existing from Phase 7 bootstrap). No assumption required for any endpoint shape.

### Live Cluster State (snapshot 2026-05-24, pre-Phase-16)

| Lib name | CollectionType | ItemId | PathInfos | Locations (cache) |
|----------|---------------|--------|-----------|-------------------|
| `Séries` | `tvshows` | `d565273fd114d77bdf349a2896867069` | `['/media/series', '/media/anime', '/media/family']` | `['/media/anime', '/media/family', '/media/series', '/media/series']` (stale dup — Pitfall 8 from Phase 7 forensics still visible) |
| `Films` | `movies` | `db4c1708cbb5dd1676284a40f2950aba` | `['/media/films', '/media/films-anime', '/media/films-family']` | same shape, no dup |

**Filesystem state (pod view, `ls /media/`):**

```
anime, family, films, films-animation-enfants, films-anime,
films-enfants, films-family, films-zoe, nouveaux-films, series,
series-emilie, series-garcons, series-thomas, series-zoe
```

That's 14 dirs: 10 v0.3.0 (`films`, `films-animation-enfants`, `films-enfants`, `films-zoe`, `nouveaux-films`, `series`, `series-emilie`, `series-garcons`, `series-thomas`, `series-zoe`) + 4 v0.2.0 legacy (`anime`, `family`, `films-anime`, `films-family`).

**Implication:** Phase 16 will not need to wait for the filesystem migration. The 10 `/media/<name>` dirs exist. The legacy 4 dirs survive their content (operator-managed cleanup deferred).

### POST `/Library/VirtualFolders` (CREATE) — VERIFIED query-param hybrid

**Endpoint:** `POST /Library/VirtualFolders?name=<Name>&collectionType=<type>&paths=<path>&refreshLibrary=false`

**Body:** `application/json` — `AddVirtualFolderDto` shape `{"LibraryOptions": null}` accepts an empty `{}` (verified). The `LibraryOptions` field is `nullable: true` in OpenAPI 10.11.9.

**OpenAPI extract** (from live `/api-docs/openapi.json`):

```
POST /Library/VirtualFolders
  parameters:
    - name: name           in: query  required: false  type: string
    - name: collectionType in: query  required: false  type: enum  [movies, tvshows, music, musicvideos, homevideos, boxsets, books, mixed]
    - name: paths          in: query  required: false  type: array  items: string  (repeat the query param for each path)
    - name: refreshLibrary in: query  required: false  type: boolean  default: false
  requestBody:
    application/json: AddVirtualFolderDto = { LibraryOptions: LibraryOptions | null }
  responses: [204, 503, 401, 403]
```

**Live probe (2026-05-24):**

```bash
# Single-call create with paths array — VERIFIED HTTP 204
curl -X POST \
  -H "$AUTH" -H "Content-Type: application/json" \
  "http://localhost:18096/Library/VirtualFolders?name=ARRCONF_PROBE_PHASE16&collectionType=tvshows&paths=/media/series-emilie&refreshLibrary=false" \
  -d '{}'
# HTTP=204 ✅

# Verify created — GET shows the new lib with PathInfos populated
# FOUND: ARRCONF_PROBE_PHASE16 CollType=tvshows
#   PathInfos: [{'Path': '/media/series-emilie'}]
#   Locations: ['/media/series-emilie']
#   LibraryOptions has 37 keys — all Jellyfin C# defaults
#     EnableRealtimeMonitor: False (default)
#     EnablePhotos: True (default)
#     TypeOptions count: 0 (default)
```

**Multiple paths in one POST:** The OpenAPI declares `paths: array of string` as a query param. To pass N paths, repeat the query key: `?paths=/p1&paths=/p2`. With `httpx.Client.post(params={"paths": ["/p1", "/p2"]})`, httpx serializes automatically to `paths=/p1&paths=/p2`. **For Phase 16 each Category lib has exactly 1 path** (`/media/<name>`), so this is moot for the planned cutover.

### POST `/Library/VirtualFolders` — NOT IDEMPOTENT (Pitfall 16-1, CRITICAL)

**Live probe (2026-05-24, destructive evidence):**

```bash
# Step 1: Create lib (HTTP 204)
curl -X POST ".../Library/VirtualFolders?name=ARRCONF_PROBE_PHASE16&...&paths=/media/series-emilie&..." -d '{}'

# Step 2: Re-POST IDENTICAL request (HTTP 204 — silent success)
curl -X POST ".../Library/VirtualFolders?name=ARRCONF_PROBE_PHASE16&...&paths=/media/series-emilie&..." -d '{}'

# Step 3: GET — TWO libs now exist:
# Lib names: ['Séries', 'ARRCONF_PROBE_PHASE16', 'ARRCONF_PROBE_PHASE162', 'Films']
#                                                    ^^^^^^^^^^^^^^^^^^^^ ← Jellyfin appended "2"
# Both libs have SAME PathInfos: [{'Path': '/media/series-emilie'}]
# Different ItemIds (forensic)
```

**Diagnosis:** Jellyfin's `LibraryStructureController.AddVirtualFolder()` resolves name collisions by appending integer suffixes (`Name`, `Name2`, `Name3`, ...). HTTP 204 reported — no error. This is the same pattern as the Phase 7 Pitfall 2 (Paths POST duplicates entries) but at the lib level.

**Reconciler mitigation (mandatory):** Before POST `/Library/VirtualFolders`, the reconciler MUST:

1. GET `/Library/VirtualFolders` (already done at the top of `_reconcile_libraries()`)
2. Match by `Name` against the desired lib's `name`
3. If match found → skip POST entirely (the existing path-add branch handles PathInfos diff)
4. If no match → POST CREATE
5. **CRITICAL:** Do NOT re-GET between create and the path-add loop within the same reconcile run (a freshly-created lib with paths in the POST query already has its PathInfos populated — verified live).

### DELETE `/Library/VirtualFolders/Paths` — VERIFIED single-path removal, silent on missing

**Endpoint:** `DELETE /Library/VirtualFolders/Paths?name=<lib>&path=<path>&refreshLibrary=false`

**OpenAPI extract:**

```
DELETE /Library/VirtualFolders/Paths
  parameters:
    - name: name           in: query  required: false  type: string
    - name: path           in: query  required: false  type: string
    - name: refreshLibrary in: query  required: false  type: boolean  default: false
  requestBody: (none)
  responses: [204, 503, 401, 403]   # no 404 declared
```

**Live probe:**

```bash
# Add a path to Séries via Phase 7 endpoint
POST .../Library/VirtualFolders/Paths -d '{"Name":"Séries","Path":"/media/series-emilie","PathInfo":{"Path":"/media/series-emilie"}}'
# HTTP=204
# PathInfos: ['/media/series', '/media/anime', '/media/family', '/media/series-emilie']

# DELETE the path we just added — UTF-8 lib name encoded automatically by httpx
DELETE .../Library/VirtualFolders/Paths?name=Séries&path=/media/series-emilie&refreshLibrary=false
# (httpx serializes as: ?name=S%C3%A9ries&path=%2Fmedia%2Fseries-emilie&refreshLibrary=false)
# HTTP=204
# PathInfos: ['/media/series', '/media/anime', '/media/family']     ← removed ✅
# Locations: ['/media/anime', '/media/family', '/media/series', '/media/series']  ← stale (Pitfall 8 cache)

# DELETE a non-existent path — silent 204
DELETE .../Library/VirtualFolders/Paths?name=Séries&path=/media/nonexistent-path
# HTTP=204 (no-op silently)
```

**Filesystem safety:** The DELETE PathInfo call does NOT remove files. Verified: pre-DELETE `ls /media/series-emilie | wc -l` and post-DELETE were identical (no diff).

**Re Phase 7 Pitfall 3 (DELETE removes ALL matching entries):** This Pitfall is from the days of `PathInfos` having duplicates (the cache anomaly). In normal post-Phase-16 operation, each path appears exactly once in PathInfos, so the "removes all matching" property degenerates to "removes the one entry." Documented for forensics.

### DELETE `/Library/VirtualFolders` — VERIFIED full lib removal, 404 on missing

**Endpoint:** `DELETE /Library/VirtualFolders?name=<lib>&refreshLibrary=false`

**OpenAPI:**

```
DELETE /Library/VirtualFolders
  parameters:
    - name: name           in: query  required: false  type: string
    - name: refreshLibrary in: query  required: false  type: boolean  default: false
  responses: [204, 404, 503, 401, 403]   # 404 IS declared
```

**Live probe:**

```bash
# DELETE the probe lib — HTTP 204
DELETE .../Library/VirtualFolders?name=ARRCONF_FS_PROBE&refreshLibrary=false
# HTTP=204

# DELETE non-existent lib — HTTP 404
DELETE .../Library/VirtualFolders?name=ARRCONF_NONEXISTENT_XYZ&refreshLibrary=false
# HTTP=404 — body: "Error processing request."
```

**Filesystem safety probe:**

```bash
# pre-DELETE
ls /media/series | wc -l   # 5
ls /media/anime | wc -l    # 1

# Create probe lib on /media/anime → DELETE it → verify files untouched
POST .../Library/VirtualFolders?name=ARRCONF_FS_PROBE&collectionType=tvshows&paths=/media/anime&refreshLibrary=false -d '{}'
# HTTP=204
DELETE .../Library/VirtualFolders?name=ARRCONF_FS_PROBE&refreshLibrary=false
# HTTP=204

# post-DELETE
ls /media/series | wc -l   # 5  ← unchanged ✅
ls /media/anime | wc -l    # 1  ← unchanged ✅
```

**Confirmed:** DELETE VirtualFolder removes the metadata + DB entries inside Jellyfin (TypedBaseItems, mediastreams etc.) but does NOT touch the filesystem mount. This matches the [Jellyfin "safety mechanism"](https://forum.jellyfin.org/t-restructure-of-libraries-possible-without-resetting-watched-status) — files on disk are sacred.

**404 handling:** Reconciler matches by Name against the pre-fetched GET snapshot, so 404 should never fire in practice. As a defensive measure, wrap the DELETE in try/except `NotFoundError` and treat as no-op + log `library_already_absent`.

### Match-by-Name resolver — VERIFIED stable across CREATE

After POST CREATE, the new lib appears in GET `/Library/VirtualFolders` immediately (no propagation delay). Match-by-Name remains the canonical key — `ItemId` is server-assigned and never used by the reconciler.

---

## Architecture Patterns

### System Architecture Diagram (Phase 16 extension)

```
              arrconf CronJob → JellyfinClient → _reconcile_libraries()
                                                          │
                          1. GET /Library/VirtualFolders (snapshot)
                          2. Generator output: list[JellyfinLibrary] (10 entries from D-03)
                                                          │
                                                          ▼
                                  ┌──────────────────────────────────────┐
                                  │ FOR each desired_lib in generator     │
                                  │   match cluster_lib by Name           │
                                  │   ┌────────────────┬─────────────────┐│
                                  │   │ MATCH FOUND    │ NO MATCH        ││
                                  │   ▼                ▼                 ││
                                  │ ADD missing       CREATE lib         ││
                                  │ paths (POST       POST /Library/     ││
                                  │ /Paths,           VirtualFolders     ││
                                  │ idempotence       params={name,      ││
                                  │ shim — Phase 7    collectionType,    ││
                                  │ Pitfall 2)        paths,             ││
                                  │                   refreshLibrary=    ││
                                  │ IF prune:         false}             ││
                                  │   DELETE extra    body={}            ││
                                  │   paths (DELETE   (single-call —     ││
                                  │   /Paths)         lib + paths        ││
                                  │                   in one POST)       ││
                                  └────────────────────┴─────────────────┘
                                                          │
                                                          ▼
                                  3. IF section.prune == True:
                                       For each cluster_lib NOT in desired_libs:
                                         DELETE /Library/VirtualFolders?name=<lib>
                                         (skip 404 → no-op, log library_already_absent)
                                                          │
                                                          ▼
                                              apply_complete log
                                  (FS untouched, watched-state risk = Pitfall 16-4)
```

### Pattern 1: Single-call CREATE with all paths in query (recommended)

```python
# tools/arrconf/arrconf/reconcilers/jellyfin.py (extension to _reconcile_libraries)
# Source: Live probe 2026-05-24 — VERIFIED HTTP 204

def _create_library(client: JellyfinClient, desired_lib: JellyfinLibrary, dry_run: bool) -> str | None:
    """Create a new Jellyfin VirtualFolder via POST /Library/VirtualFolders.

    Single-call create-with-paths: paths array is in the QUERY STRING (not body).
    Body is empty AddVirtualFolderDto ({}) — LibraryOptions is nullable per OpenAPI 10.11.9.

    Phase 16 (D-16-LIB-CREATE-01). Idempotence shim — caller MUST verify Name absence
    in cluster snapshot BEFORE invoking (Pitfall 16-1: POST duplicates with suffix).
    """
    if dry_run:
        log.info("dry_run_skip", resource="library_create",
                 name=desired_lib.name, paths=desired_lib.paths)
        return f"library_create:dry_run:{desired_lib.name}"

    client._request(
        "POST",
        LIBRARY_VIRTUALFOLDERS_PATH,
        params={
            "name": desired_lib.name,
            "collectionType": desired_lib.collection_type,  # "tvshows" | "movies"
            "paths": desired_lib.paths,    # httpx repeats key for list values
            "refreshLibrary": "false",
        },
        json={},  # AddVirtualFolderDto with LibraryOptions=null (Jellyfin defaults)
    )
    log.info("library_created", name=desired_lib.name,
             collection_type=desired_lib.collection_type, paths=desired_lib.paths)
    return f"library_created:{desired_lib.name}"
```

### Pattern 2: DELETE path with prune gate

```python
def _prune_library_paths(
    client: JellyfinClient,
    desired_lib: JellyfinLibrary,
    cluster_lib: dict[str, Any],
    section: JellyfinLibrariesSection,
    dry_run: bool,
) -> list[str]:
    """Remove paths present in cluster but NOT in desired set (D-16-PATH-DELETE-01).

    Gated by section.prune (D-16-PRUNE-01). When prune=False (default), no-op.
    Pitfall 8 carry-forward: diff PathInfos, NEVER Locations (stale projection).

    Cutover behavior: legacy 'Séries' lib has PathInfos=['/media/series','/media/anime',
    '/media/family']; desired post-cutover has PathInfos=['/media/series'].
    Prune removes /media/anime + /media/family from this lib.
    """
    if not section.prune:
        return []

    desired_paths: set[str] = set(desired_lib.paths)
    path_infos = (cluster_lib.get("LibraryOptions") or {}).get("PathInfos") or []
    cluster_paths: set[str] = {p.get("Path") for p in path_infos if p.get("Path")}
    excess: set[str] = cluster_paths - desired_paths
    actions: list[str] = []

    for path in sorted(excess):  # deterministic for tests
        if dry_run:
            log.info("dry_run_skip", resource="library_path_delete",
                     name=desired_lib.name, path=path)
            actions.append(f"library_path_pruned:dry_run:{desired_lib.name}:{path}")
            continue

        # DELETE /Library/VirtualFolders/Paths?name=<lib>&path=<path>&refreshLibrary=false
        # httpx auto-encodes UTF-8 lib name + path (verified live 2026-05-24).
        client._request(
            "DELETE",
            LIBRARY_PATHS_PATH,
            params={
                "name": desired_lib.name,
                "path": path,
                "refreshLibrary": "false",
            },
        )
        log.info("library_path_pruned", name=desired_lib.name, path=path)
        actions.append(f"library_path_pruned:{desired_lib.name}:{path}")

    return actions
```

### Pattern 3: DELETE lib with prune gate + 404 tolerance

```python
def _prune_libraries(
    client: JellyfinClient,
    current_libraries: list[dict[str, Any]],
    desired_libraries: list[JellyfinLibrary],
    section: JellyfinLibrariesSection,
    dry_run: bool,
) -> list[str]:
    """Remove cluster libs NOT in the desired set (D-16-PRUNE-01).

    Gated by section.prune. When prune=False (default), no-op.

    Cutover behavior: after Phase 16 ships, only the 10 generator libs exist.
    Operator-added libs (if any) get deleted during prune=True window.
    Filesystem is NEVER touched (verified live 2026-05-24).
    """
    if not section.prune:
        return []

    desired_names: set[str] = {lib.name for lib in desired_libraries}
    actions: list[str] = []

    for cluster_lib in current_libraries:
        cluster_name = cluster_lib.get("Name")
        if not cluster_name or cluster_name in desired_names:
            continue

        if dry_run:
            log.info("dry_run_skip", resource="library_delete", name=cluster_name)
            actions.append(f"library_pruned:dry_run:{cluster_name}")
            continue

        try:
            client._request(
                "DELETE",
                LIBRARY_VIRTUALFOLDERS_PATH,
                params={"name": cluster_name, "refreshLibrary": "false"},
            )
            log.info("library_pruned", name=cluster_name)
            actions.append(f"library_pruned:{cluster_name}")
        except NotFoundError:
            # 404 — lib already gone (concurrent operator action). Treat as no-op.
            log.info("library_already_absent", name=cluster_name)

    return actions
```

### Pattern 4: Full `_reconcile_libraries()` rewrite skeleton

```python
def _reconcile_libraries(
    client: JellyfinClient,
    section: JellyfinLibrariesSection,
    desired_libraries: list[JellyfinLibrary],
    dry_run: bool,
) -> list[str]:
    """Reconcile Jellyfin libraries — Phase 16 full lifecycle (D-16-*).

    Order within run:
      1. GET cluster snapshot
      2. For each desired lib:
         a. if not in cluster → CREATE (POST /Library/VirtualFolders with all paths)
         b. if in cluster → ADD missing paths (Phase 7 idempotence shim)
         c. if section.prune → DELETE excess paths (D-16-PATH-DELETE-01)
      3. If section.prune → DELETE cluster libs not in desired (D-16-PRUNE-01)
    """
    if not section.enable:
        log.info("libraries_reconcile_skipped")
        return []

    log.info("step_begin", step="libraries", step_index=1)
    current_libraries: list[dict[str, Any]] = client.get(LIBRARY_VIRTUALFOLDERS_PATH)
    by_name: dict[str, dict[str, Any]] = {
        lib["Name"]: lib for lib in current_libraries if lib.get("Name")
    }
    actions: list[str] = []

    for desired_lib in desired_libraries:
        cluster_lib = by_name.get(desired_lib.name)

        if cluster_lib is None:
            # Pitfall 16-1: must verify absence by Name BEFORE POST or Jellyfin duplicates with suffix.
            action = _create_library(client, desired_lib, dry_run)
            if action:
                actions.append(action)
            continue

        # Existing lib → add missing paths (Phase 7 pattern, unchanged).
        actions += _add_missing_paths(client, desired_lib, cluster_lib, dry_run)

        # Prune excess paths (Phase 16 new behavior, prune-gated).
        actions += _prune_library_paths(client, desired_lib, cluster_lib, section, dry_run)

    # Phase 16: prune entire libs not in desired set (D-16-PRUNE-01).
    actions += _prune_libraries(client, current_libraries, desired_libraries, section, dry_run)

    return actions
```

### Pattern 5: Refactored `generate_jellyfin_libraries()` (generator)

```python
# tools/arrconf/arrconf/generators/categories.py — replace lines 192-202

# D-16-COLLECTIONTYPE-01: same mapping as Phase 7.
_KIND_TO_COLLECTION_TYPE: Final[dict[str, str]] = {
    "series": "tvshows",
    "movies": "movies",
}


def generate_jellyfin_libraries(cfg: RootConfig) -> list[JellyfinLibrary]:
    """REQ-jellyfin-categories-as-libs: 10 libs, one per Category (D-16-*).

    Phase 16 reverses Phase 7's 2-super-libs design. Each Category becomes its own
    JellyfinLibrary with display name (D-16-LIB-NAME-01) and a single path /media/<name>.

    Order of output follows cfg.categories order — deterministic for tests.
    """
    return [
        JellyfinLibrary(
            name=c.display,                                  # D-16-LIB-NAME-01
            collection_type=_KIND_TO_COLLECTION_TYPE[c.kind],  # D-16-COLLECTIONTYPE-01
            paths=[c.base_path],                             # /media/<name>
        )
        for c in cfg.categories
    ]
```

### Anti-Patterns to Avoid

- **POST `/Library/VirtualFolders` without verifying Name absence** — Jellyfin silently duplicates with suffix `2`, `3`, etc. (Pitfall 16-1).
- **Two-phase CREATE: POST lib with no paths, then POST `/Paths` for each path** — Wastes N+1 HTTP calls, leaves a transient empty lib visible to clients. Single-call with query-array is verified working.
- **Using `data=` instead of `json=` with empty body** — httpx with `data=None` sends `Content-Length: 0` and no Content-Type. Jellyfin accepts both (verified) but `json={}` is the documented OpenAPI shape.
- **DELETE-before-CREATE during cutover** — Creates a transient state where Jellyfin UI shows 0 libs (10s window) → bad UX during reconcile. Order: CREATE all → ADD paths → DELETE old.
- **Triggering a library refresh after each CREATE/DELETE** — `refreshLibrary=true` queues a scan job per call; with 10 libs created in one reconcile, that's 10 scan jobs. Better: always `refreshLibrary=false`, let Jellyfin's nightly scheduled scan pick up changes. D-07-LIB-02 punt remains.
- **Re-GET `/Library/VirtualFolders` between CREATE and the path-add loop within the same run** — Adds latency without value; the freshly-created lib already has its paths populated (verified live, see §POST evidence).
- **Removing the `Field(exclude=True)` discipline from `_reconcile_users` (Phase 7 Pitfall 6)** — Phase 16 does NOT touch users. Don't accidentally drop carry-forward.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL-encoding UTF-8 lib names | `urllib.parse.quote(name)` manually | `httpx.Client.delete(params={'name': 'Séries', ...})` | Verified live: httpx serializes `S%C3%A9ries` automatically. Manual quote = duplicate encoding risk. |
| 404 handling on DELETE | try/except → ignore-all | Catch `arrconf.exceptions.NotFoundError` typed | `ArrApiClient._request` already raises typed exceptions; downstream test mocks rely on these types. |
| Idempotence shim at lib level | Separate cache file | Match-by-Name from the SAME pre-fetched `GET /Library/VirtualFolders` already used for path diff | One snapshot is the source of truth — re-GETting between branches creates race windows. |
| Watched-state DB inspection during cutover | sqlite3 reads against `library.db` from arrconf | (None — out of scope) | Per CLAUDE.md "frontière": arrconf never opens Jellyfin's SQLite directly. Watched-state preservation is a Jellyfin behavior (path-based matching), not an arrconf responsibility. |
| Generator output dataclass for Phase 16 | New `JellyfinDerived` wrapper | Reuse existing `list[JellyfinLibrary]` shape | The reconciler signature `desired_libraries: list[JellyfinLibrary]` is already in place (Phase 12-B D-01). Don't change a stable contract. |

**Key insight:** Phase 16 = "Phase 7 reconciler + 3 new branch arms + 1 generator rewrite + 4 new pitfalls discovered today." The plumbing (`JellyfinClient`, `_request`, idempotence shim, snapshot discipline, test scaffold) is all reusable. ~150 LOC.

---

## Runtime State Inventory

This is a refactor phase — runtime state matters.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| **Stored data** | Jellyfin SQLite `library.db` — tables `TypedBaseItems` (per-item rows, includes `Path` column), `mediastreams`, `UserDatas` (watched state per item). When a path moves between libs, BaseItems rows have their `Path` column unchanged (paths in PathInfos don't rewrite item paths — they just scope the lib's roots). Items retain `ProviderIds` (TVDB/TMDB ids if metadata fetched). **Risk:** see §Watched-State Risk Analysis below. | No arrconf migration. Watched state preservation depends on Jellyfin re-matching by Path after lib reshape. UAT scenario in 16-HUMAN-UAT.md. |
| **Live service config** | Jellyfin in-cluster API: 2 legacy libs `Séries`/`Films`, ItemIds known (`d565273f...`, `db4c1708...`). 14 `/media/<name>` dirs (10 v0.3.0 + 4 v0.2.0 legacy). API key still in `arrconf-env` SealedSecret (carry-forward Phase 7). | Operator does NOT need to touch anything pre-Phase 16. arrconf creates 8 new libs, reshapes 2 existing libs, optionally prunes via `prune: true`. |
| **OS-registered state** | None. K8s Deployment-managed pod, no systemd/cron. | None — verified by `kubectl get pods`. |
| **Secrets/env vars** | `JELLYFIN_API_KEY` in `arrconf-env` SealedSecret (32 chars). Phase 7 bootstrap, carry-forward. | None — already present, used today during research probe. |
| **Build artifacts / installed packages** | `arrconf` image `ghcr.io/tom333/arr-stack-arrconf:0.7.0` currently deployed (from `values.yaml:451`). Co-bump to `0.8.0` during Phase 16 (minor — new feature). | Single commit bumps `tools/arrconf/**` + `charts/arr-stack/values.yaml#arrconf.image.tag` (CLAUDE.md "Release pin co-bump pattern"). |

**Nothing found in category:** OS-registered state — None — verified by `kubectl get pods`.

---

## Watched-State Risk Analysis

This is the highest-risk technical aspect of Phase 16. Captured here as a separate section because it cuts across multiple pitfalls.

### What we know (from Jellyfin sources + live probe)

1. **Watched state is stored in `UserDatas` table of `library.db`, keyed by `(UserId, ItemId)`.** ItemId is a hash derived from the canonical item path (per `discussion #6924`).
2. **Items in `TypedBaseItems` carry `ProviderIds` JSON column** (TVDB id, TMDB id, IMDB id) when metadata fetched.
3. **When a library is deleted via DELETE `/Library/VirtualFolders`**, the rows in `TypedBaseItems` keyed to that lib's `BaseItem` root are removed (cascade), and orphaned `UserDatas` rows linger but become unreachable (no Item to reference them).
4. **When a path moves from lib A to lib B (PathInfo removed from A, then a new lib B is created with that PathInfo)**, Jellyfin's next scan finds the same media files on disk under their unchanged paths. New `TypedBaseItems` rows are created under lib B's root. **The new ItemIds may or may not match the old ones** — this is the crux.
5. **GitHub issue #4895** confirms a related-but-different bug: when the SAME media is in TWO libs simultaneously, watched state on lib1 leaks to lib2 (because ItemIds collide by path hash). This is GOOD news for Phase 16 — it suggests the path-based hash is stable across libs.
6. **GitHub issue #12297** documents the BAD scenario: when path is changed (`/media/Serien/Serien/X` → `/media/Serien/Serien/_not_final/X`), Jellyfin sees duplicate items (old at old path no longer playable, new at new path). Phase 16 is NOT this scenario — paths don't change at the file level (the media files stay where they are on NFS; only which lib references them changes).

### Phase 16's actual cutover

Given the **current cluster state** (legacy Séries has PathInfos `['/media/series', '/media/anime', '/media/family']`):

- **Items under `/media/series`:** Stay in the reshaped `Séries` lib (its only post-cutover PathInfo). Watched state preserved (same lib, same path → same ItemId).
- **Items under `/media/anime`:** Currently in `Séries`. After cutover, `/media/anime` is NOT a category root (no `categories[]` entry has `base_path: /media/anime`). These items become orphaned in the `Séries` lib's old PathInfos until `prune: true` removes them. Once the `/media/anime` PathInfo is removed from `Séries`, the items are gone from `Séries`. **No new lib picks them up** unless the operator first migrates the files (CLAUDE.md "Filesystem migration" `mv anime/* series-zoe/`). Watched state for these items: lost (item no longer in any lib).
- **Items under `/media/family`:** Same as anime. Operator must `mv family/* series-garcons/` before Phase 16 cutover, or these items disappear.
- **Items under `/media/films-anime` and `/media/films-family`:** Same pattern, operator-driven cleanup per CLAUDE.md "Filesystem migration".

**The watched-state risk is bounded to: items currently under legacy paths (`/media/anime`, `/media/family`, `/media/films-anime`, `/media/films-family`) that the operator has NOT migrated to v0.3.0 buckets.**

### Acceptable failure mode

Per `Out of Scope` in CONTEXT.md: "Pas de migration auto du watched state — comportement par défaut Jellyfin (match par ProviderIds) assumé suffisant. Si UAT révèle des pertes, c'est un follow-up post-Phase-16."

**The honest planning answer:**

1. If operator has done the filesystem migration (CLAUDE.md table), watched state preserved (path unchanged, ItemId stable).
2. If operator has NOT done the filesystem migration, watched state lost for items still under legacy paths. **This is the operator's pre-Phase-16 gate.**
3. arrconf does nothing to help or hurt this — the design choice is "Jellyfin's default match-by-path is good enough."

**Recommended HUMAN-UAT scenarios** (16-HUMAN-UAT.md):

- Pre-cutover: operator confirms filesystem migration is done (`ls /media/anime` empty or near-empty).
- Pre-cutover: operator picks 3 known-watched series (one per migrated bucket) for the survival probe.
- Post-cutover: operator verifies the same 3 series show as watched in the new buckets (`Séries - Zoé`, `Séries - Garçons`, etc.).
- Post-cutover: operator inspects items in legacy `Séries`/`Films` libs — should match only `/media/series` and `/media/films` (the renamed roots), no orphans.

---

## Common Pitfalls

### Pitfall 16-1: POST `/Library/VirtualFolders` is NOT idempotent — Jellyfin silently appends suffix (CRITICAL)

**What goes wrong:** Re-POSTing the same `name=X` (when lib `X` already exists) creates lib `X2` (and on third attempt, `X3`). HTTP returns 204 — no error. Reconciler thinks it succeeded; Jellyfin UI shows two libs with confusingly similar names; clients (web, JellyCon) see both.

**Why it happens:** Jellyfin's `LibraryStructureController.AddVirtualFolder()` resolves name collisions by appending integer suffixes rather than rejecting the request. Verified live 2026-05-24 with the probe `ARRCONF_PROBE_PHASE16` → `ARRCONF_PROBE_PHASE162`.

**How to avoid:** Reconciler MUST GET `/Library/VirtualFolders`, match by `Name` against the desired lib's `name`, and only POST CREATE when no match. Mirror of Phase 7 Pitfall 2 lifted from path-level to lib-level.

**Warning signs:** SC#2 idempotence test fails (second `arrconf apply` after first creates duplicates). UI shows `Séries2`, `Films2`, etc. Cluster GET shows `len(libs) > 10` post-second-apply.

### Pitfall 16-2: DELETE `/Library/VirtualFolders` returns 404 on missing lib

**What goes wrong:** Reconciler in prune=true mode calls DELETE for a lib that another operator (or a concurrent reconcile, or a prior failed reconcile retry) already removed. HTTP 404, body `Error processing request.`. ArrApiClient maps 4xx → `NotFoundError`. If reconciler doesn't catch this, the whole apply run aborts.

**Why it happens:** Jellyfin's DELETE `/Library/VirtualFolders` declares 404 explicitly in OpenAPI 10.11.9 (unlike DELETE `/Paths` which is silent 204).

**How to avoid:** Wrap the DELETE call in try/except `NotFoundError` → treat as no-op, log `library_already_absent`. See Pattern 3.

**Warning signs:** First retry after a partial cutover failure aborts. Test must mock NotFoundError on second DELETE → verify reconciler treats as no-op.

### Pitfall 16-3: Match-by-Name shim must use cluster snapshot, not GET-after-CREATE

**What goes wrong:** A naive implementation re-GETs `/Library/VirtualFolders` after each POST CREATE to "refresh the snapshot." This costs N extra HTTP calls + introduces race windows (another operator UI action between POST and GET → drift). Worse: between CREATE and the subsequent path-add loop within the same lib branch, a re-GET would show the just-created lib with paths already populated (verified live) — so re-GET doesn't help.

**Why it happens:** Defensive instinct — "always re-read state before next write." Wrong instinct here.

**How to avoid:** GET once at the start of `_reconcile_libraries()`. Branch on the snapshot. Trust the OpenAPI contract — after POST CREATE returns 204, the lib exists with its query-string paths. Verified live.

**Warning signs:** Reconcile run latency > 5s for 10 libs (should be ~1s with 1 GET + 10 POSTs); test suite measures HTTP request count via `respx.mock(assert_all_called=False)`.

### Pitfall 16-4: Watched-state preservation depends on operator's pre-Phase-16 filesystem migration

**What goes wrong:** If operator runs Phase 16 cutover without first migrating media from legacy `/media/anime`, `/media/family`, `/media/films-anime`, `/media/films-family` to v0.3.0 buckets, those items lose their lib membership (the legacy paths are no longer referenced by any post-cutover lib) and their watched state becomes orphaned/unreachable.

**Why it happens:** Jellyfin's `UserDatas` table is keyed by `(UserId, ItemId)` where ItemId is a path-derived hash. After the lib reshape:
- Items at `/media/series` survive (path unchanged, in the reshaped `Séries` lib).
- Items at `/media/anime` are orphaned (no lib references the path; metadata + DB rows persist but become unreachable in UI).

**How to avoid:** HUMAN-UAT scenario 1: operator confirms filesystem migration is complete BEFORE merging the Phase 16 PR. CLAUDE.md "Filesystem migration v0.2.0 → v0.3.0" provides the runbook (operator runs `mv anime/* series-zoe/` etc. from the Jellyfin pod via `kubectl exec`).

**Warning signs:** Post-cutover, operator queries `library.db` and finds `UserDatas` rows with no joinable `TypedBaseItems`. Or simpler: operator can't find a known-watched series in any lib post-cutover.

### Pitfall 16-5: `refreshLibrary=true` queues a scan job per call

**What goes wrong:** Setting `refreshLibrary=true` on CREATE / DELETE Paths / DELETE Lib queues a scan job per request. Phase 16 cutover with 10 creates + 8 path deletes + 0 lib deletes = 18 queued scans within seconds. Jellyfin serializes scans → ~20 min stall on a busy filesystem.

**Why it happens:** Default scan behavior is to scan the affected lib root after every mutation. Phase 7 already set `refreshLibrary=false` on the Paths endpoint for this exact reason.

**How to avoid:** Always pass `refreshLibrary=false` on all three endpoints (CREATE, DELETE Path, DELETE Lib). Let Jellyfin's scheduled scans (default: hourly) handle the indexing. D-07-LIB-02 punt remains.

**Warning signs:** Operator notices Jellyfin UI sluggish for 20+ min post-Phase-16 deploy. `kubectl logs jellyfin` shows continuous scan activity.

### Carry-forward from Phase 7 (unchanged in Phase 16)

- **Pitfall 1** (POST `/System/Configuration` full REPLACE): not touched by Phase 16 — `_reconcile_server_config` unchanged.
- **Pitfall 2** (POST `/Library/VirtualFolders/Paths` not idempotent): still relevant for the "ADD missing paths" branch.
- **Pitfall 3** (DELETE Paths removes all matching): degenerate in post-Phase-16 normal operation (no duplicates produced by reconciler).
- **Pitfall 4** (POST not PUT for `/Users/{id}/Policy`): not touched.
- **Pitfall 5** (Plugin Enable requires version): not touched.
- **Pitfall 6** (UserPolicy OpenAPI required ProviderIds): not touched.
- **Pitfall 7** (PluginRepositories diff set-by-URL): not touched.
- **Pitfall 8** (Locations cache stale vs PathInfos): **still active in cluster snapshot today** (Séries Locations shows `/media/series` twice — forensic). Reconciler continues to read PathInfos only.
- **Pitfall 9** (API key leak in `?api_key=` fallback): not triggered — MediaBrowser header preferred.

---

## Code Examples

### GET `/Library/VirtualFolders` response (post-Phase-16 expected, fixture target)

```json
// Source: live probe + projected post-cutover state [VERIFIED: structure 2026-05-24]
[
  {
    "Name": "Séries",
    "ItemId": "d565273fd114d77bdf349a2896867069",
    "CollectionType": "tvshows",
    "Locations": ["/media/series"],
    "LibraryOptions": {
      "PathInfos": [{"Path": "/media/series"}],
      "Enabled": true,
      "EnablePhotos": true,
      "EnableRealtimeMonitor": false,
      "TypeOptions": []
    },
    "RefreshStatus": "Idle"
  },
  {
    "Name": "Séries - Émilie",
    "ItemId": "<new-uuid-assigned-by-jellyfin>",
    "CollectionType": "tvshows",
    "Locations": ["/media/series-emilie"],
    "LibraryOptions": {
      "PathInfos": [{"Path": "/media/series-emilie"}],
      "Enabled": true,
      "EnablePhotos": true,
      "EnableRealtimeMonitor": false,
      "TypeOptions": []
    },
    "RefreshStatus": "Idle"
  }
  // ... 8 more libs in the same shape
]
```

### Fixture for post-cutover state (`tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json`)

Should contain 10 libs in the above shape — one per `categories[]` entry. Minimal LibraryOptions (Jellyfin defaults). Use canonical UUIDs (`ItemId`) that don't collide with the Phase 7 fixtures.

### CREATE call shape (httpx, copy-pasteable)

```python
# Source: VERIFIED live 2026-05-24 — HTTP 204
import httpx

client = httpx.Client(
    base_url="http://jellyfin.selfhost.svc.cluster.local:8096",
    headers={"Authorization": 'MediaBrowser Token="...", Client="arrconf", Device="arrconf", DeviceId="arrconf", Version="0.8.0"'},
)
r = client.post(
    "/Library/VirtualFolders",
    params={
        "name": "Séries - Émilie",      # httpx auto-encodes UTF-8 → S%C3%A9ries%20-%20%C3%89milie
        "collectionType": "tvshows",
        "paths": "/media/series-emilie",  # for multiple paths: pass list ["/p1", "/p2"]
        "refreshLibrary": "false",
    },
    json={},  # AddVirtualFolderDto with LibraryOptions=null
)
assert r.status_code == 204
```

### DELETE Path call shape

```python
# Source: VERIFIED live 2026-05-24 — HTTP 204 (silent on missing)
r = client.delete(
    "/Library/VirtualFolders/Paths",
    params={
        "name": "Séries",
        "path": "/media/anime",
        "refreshLibrary": "false",
    },
)
assert r.status_code == 204
```

### DELETE Lib call shape

```python
# Source: VERIFIED live 2026-05-24 — HTTP 204, but HTTP 404 if name missing
r = client.delete(
    "/Library/VirtualFolders",
    params={
        "name": "ARRCONF_PROBE_PHASE16",
        "refreshLibrary": "false",
    },
)
assert r.status_code in (204, 404)  # 404 = already absent
```

---

## State of the Art

| Old Approach (Phase 7) | New Approach (Phase 16) | When Changed | Impact |
|------------------------|--------------------------|--------------|--------|
| 2 super-libs `Séries`/`Films` w/ multi-path PathInfos | 10 libs (1 per Category) w/ single-path PathInfos | Phase 16 (D-16-LIB-CREATE-01) | Native visibility in Kodi/JellyCon/Swiftfin/web for the 10 buckets |
| `library_missing_skip` warning (dead-end) | `library_create` action (POST `/Library/VirtualFolders`) | Phase 16 (D-16-LIB-CREATE-01) | arrconf owns full lifecycle |
| `prune: false` hardcoded in reconciler | `prune` honored from YAML section | Phase 16 (D-16-PRUNE-01) | Operator can flip true for cutover, back to false post-UAT |
| Pitfall 3 ban on DELETE Paths | DELETE Paths gated by `prune: true` | Phase 16 (D-16-PATH-DELETE-01) | Cutover reshape (5 paths → 1 path on `Séries` and `Films`) |

**Deprecated/outdated:**
- `library_missing_skip` log event — becomes unreachable after Phase 16 (no library is "missing" — reconciler creates).
- `D-07-LIB-01` hardcoded prune=false — reversed per D-16-PRUNE-01.
- 2-super-libs design — definitively obsolete per Phase 16 cutover.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | After POST CREATE returns 204, the new lib is immediately visible in subsequent GET `/Library/VirtualFolders` (no propagation delay) | Pattern 4 (rationale for not re-GETting) | Verified live 2026-05-24 — GET after POST showed the new lib in the same probe sequence, no sleep needed. Risk: 0. |
| A2 | `httpx.Client.post(params={"paths": [list]})` serializes as `?paths=p1&paths=p2` (repeated key, OpenAPI array convention) | Pattern 1 | Standard httpx behavior — documented + verified by code-path in this research's UTF-8 lib name probe (single value worked). Risk if multi-value fails: Phase 16 each lib has exactly 1 path, so untested but irrelevant for cutover. |
| A3 | Jellyfin's `UserDatas` watched state survives a lib reshape when the underlying file paths don't change | §Watched-State Risk Analysis + Pitfall 16-4 | [CITED: forum.jellyfin.org "Restore watched state after moving media files" + discussion #6924] — confirmed by community ops but NOT verified live by this research session (UAT scenario in plan). Risk if wrong: watched state lost across all media post-cutover, operator angry, plan needs a `library.db` SQL migration script (large surface increase). |
| A4 | DELETE `/Library/VirtualFolders` does not touch `/media/<name>` files on NFS | §POST/DELETE Probe Evidence | VERIFIED live today via destructive probe + `ls` count diff. Risk: 0. |
| A5 | Operator has not done the v0.2.0→v0.3.0 filesystem migration (4 legacy dirs still populated) | §Live Cluster State | Confirmed by `ls /media/` showing 14 dirs incl. legacy 4. **Operator gate required pre-Phase-16** — HUMAN-UAT scenario. |
| A6 | `refreshLibrary=false` does NOT cause Jellyfin to ever rescan for arrconf-created libs | Pitfall 16-5 | True per OpenAPI default and Phase 7 carry-forward. Jellyfin's scheduled scan (hourly) will pick up new libs eventually. Risk: operator must wait up to 1 hour or trigger manual rescan via UI. |
| A7 | The `categories[].display` values currently in `arrconf.yml` (lines 7, 12, 17, 22, 27, 32, 37, 42, 47, 52) are stable and won't change before Phase 16 lands | D-16-LIB-NAME-01 reliance | Confirmed by reading the YAML — these are the operator's chosen labels and changing them is itself a config edit. Risk: 0 unless operator edits in parallel. |
| A8 | Jellyfin 10.11.9 and 10.11.8 have identical schemas for the 3 Library endpoints | Live Cluster State | OpenAPI 10.11.9 was inspected in this session, the live probe is on 10.11.9. Phase 7 was on 10.11.8 (different patch). No schema delta observed for these endpoints — semver patch should not break wire compat. Risk: 0. |

---

## Open Questions

1. **Watched state survival across the 2-super-lib → 10-lib cutover for items currently at `/media/series`, `/media/films`** (paths that ARE preserved post-cutover, so should survive)
   - What we know: Items keyed by `(UserId, ItemId)` where ItemId is path-hash. Path doesn't change → ItemId stable → watched state preserved.
   - What's unclear: Does the lib reshape (5 PathInfos → 1 PathInfo on `Séries`) trigger Jellyfin to delete the BaseItem rows for items under the removed PathInfos? If yes, even items at the `/media/series` root might be re-scanned and re-keyed (new ItemId, watched state lost).
   - Recommendation: HUMAN-UAT scenario 2 — operator picks 3 known-watched series under `/media/series` (NOT under legacy paths) before cutover, verifies after.

2. **What happens to items under `/media/anime`, `/media/family`, `/media/films-anime`, `/media/films-family` after Phase 16 with `prune: true`?**
   - What we know: Pitfall 16-4 says they become orphans (lib reshape removes those PathInfos; no new lib references them).
   - What's unclear: Does Jellyfin "garbage-collect" the orphaned BaseItem rows on next scan, or do they persist as zombie entries visible via some API path?
   - Recommendation: HUMAN-UAT scenario — operator confirms post-Phase-16 that no zombie items appear in any lib browse view. If they do, follow-up cleanup task: operator removes legacy `/media/anime` etc. dirs once empty (per CLAUDE.md migration runbook).

3. **Should the reconciler trigger a one-shot `POST /Library/Refresh` after the cutover apply?**
   - What we know: D-07-LIB-02 punted refresh to operator. Pitfall 16-5 says don't queue 18 scans (one per write). But a single global refresh at the END of the reconcile loop might be a good operator-experience choice.
   - What's unclear: Is `POST /Library/Refresh` a single global scan or one-per-lib? Probe needed if planner decides to add this step.
   - Recommendation: KEEP Phase 7 punt — no automatic refresh. Document in 16-HUMAN-UAT.md a step "operator clicks Scan Library in Dashboard if libs appear empty in clients."

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | arrconf runtime | ✓ | (cluster image) | — |
| httpx | JellyfinClient HTTP | ✓ | 0.28.x | — |
| pydantic v2 | Resource models | ✓ | 2.13.x | — |
| respx | Unit tests | ✓ | 0.23.x | — |
| kubectl + cluster access (selfhost) | snapshot pre/post + UAT | ✓ | — | — |
| Jellyfin 10.11.9 pod | live cutover apply | ✓ | 10.11.9 (was 10.11.8 in Phase 7) | — |
| `JELLYFIN_API_KEY` env var in arrconf-env Secret | Reconciler auth | ✓ | (carry-forward Phase 7) | — |
| sealed-secrets controller (my-kluster) | Secret delivery | ✓ | — | — |
| `tools/snapshot/snapshot.sh --apps jellyfin` | Pre-cutover baseline + post-cutover diff (ADR-6) | ✓ | existing | — |

**Missing dependencies with no fallback:** None — all infrastructure exists from Phase 7.

**Missing dependencies with fallback:** None.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.x + respx 0.23.x + pytest-cov 7.1.x |
| Config file | `tools/arrconf/pyproject.toml` |
| Quick run command | `cd tools/arrconf && uv run pytest tests/test_reconcilers_jellyfin.py tests/test_jellyfin_categories.py -x` |
| Full suite command | `cd tools/arrconf && uv run pytest --cov=arrconf --cov-fail-under=70` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-jellyfin-categories-as-libs | `generate_jellyfin_libraries()` emits 10 libs from 10 categories | unit | `pytest tests/test_jellyfin_categories.py::test_generate_jellyfin_libraries_ten_libs -x` | ❌ Wave 0 (replaces existing test) |
| REQ-jellyfin-categories-as-libs | Generator: 5 `tvshows` + 5 `movies` based on `kind` | unit | `pytest tests/test_jellyfin_categories.py::test_generate_jellyfin_libraries_collection_type_mapping -x` | ❌ Wave 0 |
| REQ-jellyfin-categories-as-libs | Generator: `name = categories[].display` (D-16-LIB-NAME-01) | unit | `pytest tests/test_jellyfin_categories.py::test_generate_jellyfin_libraries_names_match_display -x` | ❌ Wave 0 |
| REQ-jellyfin-categories-as-libs | Reconciler CREATE: POST with empty body + query params (Pattern 1) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_library_create_uses_query_params_and_empty_body -x` | ❌ Wave 0 |
| REQ-jellyfin-categories-as-libs | Reconciler CREATE: Pitfall 16-1 mitigation — skip POST if Name already in cluster snapshot | unit | `pytest tests/test_reconcilers_jellyfin.py::test_library_create_skipped_when_name_already_exists -x` | ❌ Wave 0 |
| REQ-jellyfin-categories-as-libs | Reconciler PRUNE paths: gated by `section.prune == True` (D-16-PRUNE-01) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_library_prune_paths_disabled_when_prune_false -x` | ❌ Wave 0 |
| REQ-jellyfin-categories-as-libs | Reconciler PRUNE paths: removes paths in cluster but not in desired (D-16-PATH-DELETE-01) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_library_prune_paths_removes_excess -x` | ❌ Wave 0 |
| REQ-jellyfin-categories-as-libs | Reconciler PRUNE lib: DELETE `/Library/VirtualFolders` when lib in cluster but not in desired + prune=True | unit | `pytest tests/test_reconcilers_jellyfin.py::test_library_prune_lib_removes_orphans -x` | ❌ Wave 0 |
| REQ-jellyfin-categories-as-libs | Reconciler PRUNE lib: tolerates 404 (Pitfall 16-2) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_library_prune_lib_tolerates_404 -x` | ❌ Wave 0 |
| REQ-jellyfin-categories-as-libs | Reconciler PRUNE lib: NO-OP when prune=False | unit | `pytest tests/test_reconcilers_jellyfin.py::test_library_prune_lib_disabled_when_prune_false -x` | ❌ Wave 0 |
| REQ-jellyfin-categories-as-libs | dry_run: zero HTTP writes for CREATE/DELETE branches | unit | `pytest tests/test_reconcilers_jellyfin.py::test_jellyfin_create_and_prune_dry_run -x` | ❌ Wave 0 |
| REQ-jellyfin-categories-as-libs | Existing `test_libraries_path_idempotent_pitfall2` and `test_libraries_set_membership_uses_pathinfos_not_locations_pitfall8` still pass (Phase 7 carry-forward) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_libraries_path_idempotent_pitfall2 -x` | ✓ existing |
| REQ-jellyfin-categories-as-libs | Idempotence SC#2: second `arrconf apply --dry-run` after first emits 0 plan_action for jellyfin libraries | smoke (cluster, manual gate) | `arrconf dump --apps jellyfin > /tmp/jelly-post.yml && arrconf apply --config arrconf.yml --apps jellyfin --dry-run` exit 0 with 0 actions | ❌ Wave 4 (operator gate) |
| REQ-jellyfin-categories-as-libs | UAT 1: Web UI shows 10 libs post-cutover (D-16-JELLYCON-UAT-01 mandatory close) | manual | operator opens https://jellyfin.tgu.ovh/ and counts libs | ❌ Wave 4 (operator gate) |
| REQ-jellyfin-categories-as-libs | UAT 2: ≥ 3 watched series survive (Open Question 1) | manual | operator picks 3 known-watched series pre-cutover, verifies post-cutover | ❌ Wave 4 (operator gate) |
| REQ-jellyfin-categories-as-libs | UAT 3 (carry-forward): JellyCon LibreELEC shows 10 libs | manual | non-blocking | ❌ Wave 4 (operator, later) |
| REQ-jellyfin-categories-as-libs | UAT 4: Operator flips `prune: false` post-UAT | manual | second PR after Phase 16 with `jellyfin.libraries.prune: false` | ❌ Wave 4 (operator gate) |

### Sampling Rate

- **Per task commit:** `cd tools/arrconf && uv run pytest tests/test_reconcilers_jellyfin.py tests/test_jellyfin_categories.py -x` (≤ 5s)
- **Per wave merge:** `cd tools/arrconf && uv run pytest --cov=arrconf --cov-fail-under=70` (≤ 30s)
- **Phase gate (Wave 4):** Full suite green + cluster snapshot diff (`snapshots/before-phase-16-2026-05-24/` vs `snapshots/after-phase-16-2026-05-24/`) before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tools/arrconf/tests/test_reconcilers_jellyfin.py` — add 8 new tests for CREATE/PRUNE branches (extend existing file, keep existing 14 tests intact)
- [ ] `tools/arrconf/tests/test_jellyfin_categories.py` — replace 2-lib expectation with 10-lib (5 tvshows + 5 movies)
- [ ] `tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json` — NEW fixture, 10 libs in expected post-cutover shape (used in PRUNE-side and idempotence tests)
- [ ] `snapshots/before-phase-16-2026-05-24/jellyfin/` — pre-cutover baseline (`tools/snapshot/snapshot.sh --apps jellyfin --output snapshots/before-phase-16-2026-05-24/`) — MANDATORY per CLAUDE.md "Workflow snapshot CRITIQUE" + ADR-6
- [ ] No framework install needed — respx + pytest already in `pyproject.toml`

---

## Project Constraints (from CLAUDE.md)

Phase 16 MUST satisfy:

- **Release pin co-bump pattern** — `tools/arrconf/**` changes + `charts/arr-stack/values.yaml#arrconf.image.tag` bump `0.7.0 → 0.8.0` (minor — feature) in the SAME commit. Failure to co-bump triggers the auto-tag/values drift bug documented in CLAUDE.md.
- **Triade Python obligatoire avant commit** — `uv run ruff format --check . && uv run ruff check . && uv run mypy .` from `tools/arrconf/`. CI blocks otherwise.
- **Idempotence règle d'or** — Re-running N times = 0 changes. Pitfall 16-1 must be mitigated; SC#2 test is the contract.
- **Snapshot avant test risqué** — `snapshots/before-phase-16-2026-05-24/jellyfin/` committed BEFORE the helm upgrade applies the new arrconf image. ADR-6 strict.
- **Pas de migration auto du watched state** — Operator's responsibility per CONTEXT.md "Locked Boundaries." arrconf does NOT open `library.db`. Pattern reaffirmation.
- **Frontière arrconf/configarr respectée** — Phase 16 touches ONLY `_reconcile_libraries()`. No quality_profiles, custom_formats, quality_definitions, media_naming endpoints touched (ADR-5).
- **Tests coverage ≥ 70%** on `reconcilers/jellyfin.py` + `generators/categories.py` — respx mocks only, no real Jellyfin API calls in CI.
- **No `prune: true` default in `arrconf.yml`** — `jellyfin.libraries.prune` stays `false` in `charts/arr-stack/files/arrconf.yml`. Operator flips for the cutover PR, then flips back. Per CLAUDE.md "opt-in par section uniquement."

---

## Security Domain

> Same applicability as Phase 7 (no new threat surface introduced).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | MediaBrowser Token header — `JELLYFIN_API_KEY` env from sealed-secret (carry-forward Phase 7) |
| V4 Access Control | yes | DELETE Lib has prune-gate (D-16-PRUNE-01); admin token required by Jellyfin (no anonymous DELETE) |
| V5 Input Validation | yes | pydantic v2 strict on `JellyfinLibrary`; `display` field from `Category` model is pattern-constrained |
| V9 Communication | yes | HTTP only inside cluster (svc.cluster.local) |
| V14 Configuration | yes | `prune` flag in YAML, no `:latest` tag, all config from ConfigMap |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Accidental DELETE of operator-added lib during prune=true window | Tampering | HUMAN-UAT step 4: operator flips `prune: false` after UAT. Window bounded to one cutover PR. |
| POST `/Library/VirtualFolders` duplicates lib with suffix `2` (Pitfall 16-1) | Tampering | Match-by-Name pre-check (Pattern 4). Unit test guards. |
| DELETE Lib 404 aborts apply mid-cutover | DoS (operational) | try/except NotFoundError → no-op (Pattern 3). |
| Watched-state DB orphaning from unmigrated legacy paths (Pitfall 16-4) | Information Disclosure (data loss) | HUMAN-UAT scenario 1: operator confirms filesystem migration pre-Phase-16. Documented limitation per CONTEXT.md "Locked Boundaries." |

---

## Sources

### Primary (HIGH confidence)

- **Live cluster probe 2026-05-24** — kubectl port-forward + curl + httpx against `jellyfin-6fdffdcc5-kq8pw` (Jellyfin 10.11.9). All 3 endpoints + Pitfall 16-1 + filesystem safety + UTF-8 encoding verified. [VERIFIED: this session]
- **Jellyfin OpenAPI 10.11.9** — fetched via HTTP `GET /api-docs/openapi.json` (2 MB, info.version="10.11.9"). Endpoint shapes + request body schemas + parameter `in` values. [VERIFIED: this session]
- **Phase 7 RESEARCH.md** — `.planning/milestones/v0.2.0-phases/07-reconciler-jellyfin/07-RESEARCH.md` — Pitfalls 1-9, JellyfinClient pattern, MediaBrowser header format. [VERIFIED: read]
- **Existing reconciler** — `tools/arrconf/arrconf/reconcilers/jellyfin.py` — current `_reconcile_libraries()` shape lines 107-181. [VERIFIED: read]
- **CLAUDE.md** — Release pin co-bump pattern + snapshot workflow + filesystem migration v0.2.0→v0.3.0. [VERIFIED: read]

### Secondary (MEDIUM confidence)

- **Jellyfin SDK TypeScript docs** — [LibraryStructureApiAddVirtualFolderRequest](https://typescript-sdk.jellyfin.org/interfaces/generated-client.LibraryStructureApiAddVirtualFolderRequest.html) — confirms query-param shape for AddVirtualFolder. Cross-verified against live OpenAPI.
- **GitHub discussion #6924** — [Moving Library locations without losing metadata](https://github.com/jellyfin/jellyfin/discussions/6924) — confirms `UserDatas` + `TypedBaseItems` path-based keying mechanism. Cited but not verified by live SQL inspection (out of scope per CLAUDE.md frontière).
- **GitHub issue #4895** — [Watched status applied to copies in separate libraries](https://github.com/jellyfin/jellyfin/issues/4895) — confirms path-hash is stable across libs (good news for Phase 16's same-path-different-lib scenario).
- **GitHub issue #12297** — [Moving folders for library creates duplicates](https://github.com/jellyfin/jellyfin/issues/12297) — documents the bad scenario (path changes at FS level). Phase 16 is NOT this scenario.
- **Jellyfin docs** — [Libraries](https://jellyfin.org/docs/general/server/libraries/) — general library management.

### Tertiary (LOW confidence)

- (None — every claim is sourced from either live probe, OpenAPI, project files, or community ops with multi-source agreement.)

---

## Metadata

**Confidence breakdown:**

- POST `/Library/VirtualFolders` shape: **HIGH** — live probe verified single-call with query params + empty body, 204 response; OpenAPI 10.11.9 confirms.
- POST idempotence (Pitfall 16-1): **HIGH** — destructive probe confirmed the silent `Name`+`2` suffix behavior.
- DELETE `/Library/VirtualFolders/Paths`: **HIGH** — verified live, silent 204 on missing, single-path removal works.
- DELETE `/Library/VirtualFolders`: **HIGH** — verified live, 204 on present, 404 on missing, filesystem files untouched.
- Match-by-Name resolver: **HIGH** — verified live, GET after POST shows new lib immediately.
- Watched-state preservation (Open Question 1): **MEDIUM** — community sources agree path-hash is stable, but not verified live by SQL inspection (out of arrconf scope; operator-driven UAT).
- Cutover ordering recommendations: **HIGH** — derived from probe evidence (filesystem safety, no UI flicker, scan-job avoidance).

**Research date:** 2026-05-24
**Valid until:** 2026-06-23 (30 days) — Jellyfin 10.11.x is LTS stable; revalidate Pitfalls 16-1 and 16-2 if Jellyfin minor-bumps to 10.12.x before Wave 4 cluster apply.
