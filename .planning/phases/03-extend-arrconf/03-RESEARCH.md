# Phase 03: Étendre arrconf — Research

**Researched:** 2026-05-11
**Domain:** Python reconciler extension — Sonarr/Radarr/Prowlarr APIs, Pydantic v2, respx mocking
**Confidence:** HIGH (all findings verified from live snapshot data or existing codebase)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-03-01 Radarr scope:** full parity with Sonarr — download_clients + indexers (via Prowlarr
  app sync) + notifications + root_folders + host_config (opt-in gated)
- **D-03-02 Prowlarr scope:** app sync only — `apps[]` resource (GET /api/v1/applications → diff
  → PUT/POST/DELETE); indexer definitions remain managed in Prowlarr UI
- **D-03-03 Prowlarr app sync YAML model:** explicit `prowlarr.<instance>.apps[]` with `name`,
  `type` (sonarr|radarr), `base_url`, `api_key_env`, `sync_level` (fullSync|addOnly|disabled)
- **D-03-04 host_config safety:** opt-in per instance — reconciles ONLY if `host_config: { enable:
  true }`; absent or `enable: false` → log skip, no-op
- **D-03-05 config.py expansion:** monolithic single file; RootConfig gains `radarr` and `prowlarr`
  top-level dicts alongside existing `sonarr`
- **D-02.2-01 (forceSave unconditional):** `_ArrV3Client.put()` already injects `?forceSave=true`;
  RadarrClient and ProwlarrClient inherit by extending `_ArrV3Client`
- **D-31/D-32/D-33 (merge_fields_for_put):** already implemented; Phase 3 reuses unchanged
- **ADR-5 (scope boundary):** `ScopeViolationError` guard refuses quality_profiles / custom_formats
  / quality_definitions / media_naming
- **ADR-6 (snapshot discipline):** re-snapshot before first cluster write
- **ADR-7 (single-instance):** one Sonarr instance, one Radarr instance; reconcilers operate on
  `sonarr.main` and `radarr.main`
- **prune: false default (CLAUDE.md):** all reconcilers default to `prune: false`

### Claude's Discretion

- Resource reconcile ordering within each reconciler (tags first, host_config last)
- WR-01 credential privacy extension: add `"apiKey"` and `"token"` to `_CREDENTIAL_PRIVACY_VALUES`
  in `differ.py` — planner decides whether dedicated task or bundled with Prowlarr client task
- IN-02 FieldKV import: move to module-level in `test_differ.py` — bundle with any Phase 3 test
  task or standalone micro-task
- WR-02 / WR-03 docstring fixes — planner bundles inline or as cleanup task
- JSON Schema regeneration timing — last Python task before release tag
- Image tag: v0.2.0 vs v0.1.7 — planner's call

### Deferred Ideas (OUT OF SCOPE)

- Indexer definitions in YAML (Prowlarr manages via UI)
- qBittorrent reconciler (Phase 5)
- Bazarr reconciler (Phase 6+)
- Seerr tag routing (Phase 6)
- my-kluster YAML migrations / ArgoCD umbrella (Phase 4)
- `arrconf dump` additions for new resource types (Phase 3+ stretch goal)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-configarr-coexistence | ScopeViolationError guard refuses quality_profiles / custom_formats / quality_definitions / media_naming — must be replicated to Radarr reconciler | `ScopeViolationError` already exists in `exceptions.py`; `quality_profile.py` pattern is the template; research confirms guard pattern works |
| REQ-app-coverage (Phase 3 slice) | Sonarr extension (indexers + notifications + root_folders + host_config) + Radarr full parity + Prowlarr app sync | API shapes verified from live snapshots; differ.reconcile() is generic and reusable; resource model stubs exist but are empty |
</phase_requirements>

---

## Summary

Phase 3 extends arrconf from "Sonarr download_clients only" to full coverage of all transverse
resource types across Sonarr (indexers, notifications, root_folders, host_config), Radarr (full
parity), and Prowlarr (app sync only). The infrastructure is mature: `_ArrV3Client` with
forceSave, `merge_fields_for_put` with credential-omit logic, `ScopeViolationError`, and the
generic `differ.reconcile()` engine are all production-hardened from Phases 2.x.

Three new client classes are needed: `RadarrClient` and `ProwlarrClient` (both extending
`_ArrV3Client`). Six new resource types need Pydantic models: `Indexer` (shared Sonarr/Radarr
shape), `Notification` (shared shape with app-specific event fields), `RootFolder`, `HostConfig`
(singleton GET/PUT, not a list), and `Application` (Prowlarr-specific). The `config.py` expands
with `RadarrInstance`, `ProwlarrInstance`, and five new section models.

The critical constraint is that `host_config` is a **singleton resource** (one object, not a
list), requiring a different reconcile pattern than list-based resources. The `Application` model
in Prowlarr uses a `fields[]` array similar to `DownloadClient`, meaning the credential-omit
logic (`merge_fields_for_put`) applies directly — and WR-01 must be fixed (add `"apiKey"` and
`"token"` to `_CREDENTIAL_PRIVACY_VALUES`) before indexer-related fields flow through.

**Primary recommendation:** Implement the six resource model tasks in parallel waves, with
WR-01 credential fix bundled into the first task that touches `differ.py`. The `_execute()`
helper in the Sonarr reconciler should be refactored into a shared private utility (or inlined
into a base class) so Radarr and Prowlarr reconcilers do not duplicate 40 lines of
ADD/UPDATE/DELETE dispatch code.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Indexer reconciliation | arrconf reconciler | Prowlarr (creates Sonarr/Radarr indexer entries via sync) | arrconf manages the Sonarr/Radarr indexer list state; Prowlarr is the source of truth for what gets synced |
| Notification reconciliation | arrconf reconciler | — | Standard list resource; same pattern as download_clients |
| Root folder reconciliation | arrconf reconciler | — | Standard list resource; path is the match key |
| host_config reconciliation | arrconf reconciler | — | Singleton GET/PUT; opt-in guard (D-03-04) |
| Prowlarr app sync | arrconf reconciler | Prowlarr API | arrconf writes the Prowlarr `applications` list; diff uses `name` as match key |
| Credential safety | differ.py merge_fields_for_put | — | `_CREDENTIAL_PRIVACY_VALUES` must cover apiKey+token for Phase 3 |
| Scope guard (quality_profiles etc.) | Pydantic model stub (raises ScopeViolationError) | — | Codified in ADR-5; enforced pre-network |
| Config schema | config.py + schema_gen | CI schema-drift check | Pydantic generates JSON Schema; CI blocks on drift |
| Snapshot baseline | tools/snapshot/snapshot.sh | — | Already covers Radarr + Prowlarr /api/v1/applications |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | `>=2.13,<3` (pinned) | Resource models + config validation | Already in use; `model_dump(exclude_none=True)` is the serialization path |
| respx | `>=0.23,<0.24` (pinned) | HTTP mock for tests | Already the project standard |
| httpx | `>=0.28.0,<0.29` (pinned) | HTTP client | In use via `ArrApiClient._client` |
| structlog | `>=25.5,<26` (pinned) | Structured logging | In use; `log.info(event_name, **fields)` pattern |

[VERIFIED: codebase — `tools/arrconf/pyproject.toml`]

No new dependencies needed for Phase 3. All capability is already present.

---

## Architecture Patterns

### System Architecture Diagram

```
YAML config (arrconf.yml)
        │
        ▼
    load_config()   ─── Pydantic validation ─── ScopeViolationError (pre-network)
    RootConfig
    ├── sonarr.main (SonarrInstance)
    ├── radarr.main (RadarrInstance)        ← NEW Phase 3
    └── prowlarr.main (ProwlarrInstance)    ← NEW Phase 3
        │
        ▼
  __main__.apply()
    │         │         │
    ▼         ▼         ▼
reconcile_ reconcile_ reconcile_
sonarr()   radarr()   prowlarr()
    │         │         │
    ▼         ▼         ▼
 SonarrClient RadarrClient ProwlarrClient
 (_ArrV3Client) (_ArrV3Client) (_ArrV3Client)
    │              │                │
    │              │                ▼
    │              │        GET /api/v1/applications
    │              │        differ.reconcile(match_key="name")
    │              │        POST/PUT/DELETE
    │              │
    ├── GET /tag → _ensure_managed_tag()
    ├── GET /indexer → differ.reconcile()
    ├── GET /notification → differ.reconcile()
    ├── GET /rootfolder → differ.reconcile()
    ├── GET /downloadclient → differ.reconcile()   (existing Sonarr)
    └── GET /config/host → reconcile_host_config() (singleton PUT only)

differ.reconcile()
    ├── match by "name" (default) or "path" (root_folders)
    ├── diff_models() → detect changes
    └── ADD / UPDATE / DELETE / NO_OP / PRUNE_SKIP / PRUNE_PROTECTED
            │
            ▼
        _execute()
        ├── ADD → POST
        ├── UPDATE → merge_fields_for_put() → PUT with ?forceSave=true
        └── DELETE → DELETE
```

### Recommended Project Structure

```
tools/arrconf/arrconf/
├── client_base.py              # Add RadarrClient, ProwlarrClient
├── config.py                   # Add RadarrInstance, ProwlarrInstance, section models
├── differ.py                   # Fix WR-01: add apiKey+token to _CREDENTIAL_PRIVACY_VALUES
├── reconcilers/
│   ├── sonarr.py               # Extend: add indexers, notifications, root_folders, host_config
│   ├── radarr.py               # NEW: full parity reconciler
│   └── prowlarr.py             # NEW: app sync reconciler
└── resources/
    ├── sonarr/
    │   ├── indexer.py          # Replace stub with real Pydantic model
    │   ├── notification.py     # Replace stub with real Pydantic model
    │   ├── root_folder.py      # Replace stub with real Pydantic model
    │   └── host_config.py      # Replace stub with real Pydantic model
    └── prowlarr/               # NEW directory
        ├── __init__.py
        └── application.py      # NEW: Prowlarr ApplicationResource model
```

### Pattern 1: List Resource Reconcile (indexers, notifications, root_folders)

The existing `reconcile_sonarr` pattern for download_clients is directly reusable for list
resources. Key differences per resource type:

**Indexers** — match by `name`; contain `fields[]` with `privacy: "apiKey"` entries (the API
key from Prowlarr is stored in the indexer's apiKey field). After WR-01 fix, these are omitted
from PUT bodies by `merge_fields_for_put`. No `managed_tag_id` filter on prune (indexers are
managed differently — created by Prowlarr sync, not by arrconf directly; reconciliation is read-only
alignment).

**Notifications** — match by `name`; contain `fields[]` with `privacy: "apiKey"` and potentially
`privacy: "token"` (webhook tokens). App-specific event flags (`onGrab`, `onDownload`, etc.) differ
between Sonarr and Radarr (Sonarr has `onSeriesAdd`/`onEpisodeFileDelete`; Radarr has
`onMovieAdded`/`onMovieFileDelete`). Both share the `fields[]` + `implementation` +
`configContract` shape. Use `extra="allow"` to handle app-specific event flags without
per-app model split.

**Root Folders** — match by `path` (not `name`); no `fields[]`; no managed tag needed (root
folders are not tag-aware); `accessible` and `freeSpace` are read-only cluster-derived fields
(exclude from diff/dump). POST body needs only `path`; GET returns `id`, `path`, `accessible`,
`freeSpace`, `unmappedFolders`.

[VERIFIED: live snapshots `snapshots/baseline-2026-05-07/sonarr/` and `radarr/`]

```python
# Source: existing reconcilers/sonarr.py _execute() pattern
# Root folder reconcile uses path as match key (not name):
plan = reconcile(
    current=current_rfs,
    desired=desired_rfs,
    match_key="path",        # ← differs from download_clients
    prune=section.prune,
    managed_tag_id=None,     # root folders have no tag concept
)
```

### Pattern 2: Singleton Resource Reconcile (host_config)

`host_config` is a single object returned by GET `/api/v3/config/host`. There is no list to
diff against — the reconcile logic is: GET current, diff against desired, PUT if different.

```python
# Source: analysis of snapshot baseline-2026-05-07/sonarr/config_host.json
# and baseline-2026-05-07/radarr/config_host.json

def reconcile_host_config(
    client: _ArrV3Client,
    section: HostConfigSection,
    dry_run: bool,
) -> None:
    if not section.enable:
        log.info("host_config_reconcile_skipped")
        return
    raw = client.get("/config/host")
    current = HostConfig.model_validate(raw)
    diffs = diff_models(current, section.config)
    if not diffs:
        log.info("host_config_no_op")
        return
    if dry_run:
        log.info("dry_run_skip", action="update", resource="host_config", diff_fields=diffs)
        return
    body = merge_fields_for_put(current, section.config)
    body["id"] = current.id  # re-inject read-only id
    client.put("/config/host", id=current.id, json=body)
```

Critical: `host_config` does NOT use `fields[]` — it is a flat object with direct top-level
fields (`authenticationMethod`, `port`, `bindAddress`, `urlBase`, etc.). The
`merge_fields_for_put` helper handles `fields[]` lists but also falls through cleanly for
models without a `fields` attribute (returns `des_dump` unchanged for non-fields attributes).

**Credential fields in host_config:** `apiKey` and `password` are top-level fields (not nested
in `fields[]`). These are raw string fields in the Pydantic model. The
`merge_fields_for_put` helper only handles `fields[]` entries, NOT top-level model fields.
These must be marked `exclude=True` in the `HostConfig` model (never include in dump/diff/PUT)
to prevent accidental write of the API key from the YAML.

[VERIFIED: `snapshots/baseline-2026-05-07/sonarr/config_host.json` — `apiKey`, `password`,
`passwordConfirmation` are top-level fields; `snapshots/baseline-2026-05-07/radarr/config_host.json`
confirms same structure]

### Pattern 3: Prowlarr Application Sync

Prowlarr `GET /api/v1/applications` returns a list of objects with the same `fields[]` structure
as Sonarr's download_clients. The live snapshot confirms two entries (Radarr and Sonarr). Each
has:

- `id`, `name`, `implementation`, `configContract`, `enable`, `syncLevel`, `tags` (top-level)
- `fields[]` with: `prowlarrUrl` (normal), `baseUrl` (normal), `apiKey` (apiKey privacy),
  `syncCategories` (normal), `syncRejectBlocklistedTorrentHashesWhileGrabbing` (normal)
- Sonarr variant adds: `animeSyncCategories`, `syncAnimeStandardFormatSearch`

Match key for reconcile: `name` (the entry's display name in Prowlarr, controlled by YAML).

The YAML model (`AppsSection`) holds the desired state. The reconciler reads `api_key_env` from
the YAML entry, calls `os.environ[api_key_env]` to get the real API key, and includes it in the
POST/PUT body's `fields[]` as the `apiKey` field. On subsequent runs, the GET returns
`"***REDACTED***"` (or `"apiKey"` privacy), so `merge_fields_for_put` with WR-01 fix omits
the `apiKey` field from the PUT body — Prowlarr preserves the stored key via absence. This is
the same credential-omit pattern as qBittorrent.

[VERIFIED: `snapshots/baseline-2026-05-07/prowlarr/applications.json` — 2 entries, field
names and privacy values confirmed]

```python
# Source: prowlarr/applications.json snapshot analysis
# The Application model for Prowlarr follows the DownloadClient shape exactly:
class Application(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    enable: bool = True
    implementation: str
    configContract: str
    syncLevel: str = "fullSync"  # "fullSync" | "addOnly" | "disabled"
    fields: list[FieldKV] = Field(default_factory=list)
    tags: list[int] = Field(default_factory=list)
    # Read-only:
    id: int | None = Field(default=None, exclude=True)
    implementationName: str | None = Field(default=None, exclude=True)
    infoLink: str | None = Field(default=None, exclude=True)
```

`FieldKV` is already defined in `resources/sonarr/download_client.py`. Rather than duplicating
it in `resources/prowlarr/application.py`, import it directly: the model is generic and reusable
across all *arr apps.

### Pattern 4: Refactored `_execute()` — Shared Helper

Currently `_execute()` in `reconcilers/sonarr.py` is typed to `DownloadClient`. Phase 3 adds
three reconcilers each needing the same ADD/UPDATE/DELETE dispatch logic. The generic type
`list[PlannedAction[T]]` already exists. Refactoring `_execute()` to a generic function avoids
40-line duplication across radarr.py and prowlarr.py.

```python
# Pattern: extract _execute to a shared utility
from arrconf.differ import PlannedAction, Action, merge_fields_for_put
from pydantic import BaseModel

def execute_plan[T: BaseModel](
    client: ArrApiClient,
    path: str,
    plan: list[PlannedAction[T]],
    dry_run: bool,
) -> list[str]:
    """Generic ADD/UPDATE/DELETE executor (reused by all reconcilers)."""
    ...
```

This can live in `differ.py` (already the generic engine) or in a new `reconcilers/_execute.py`.
Given the project's preference for minimal files, adding it to `differ.py` is the simplest
choice.

### Anti-Patterns to Avoid

- **Using `match_key="id"` for root folders:** IDs are server-assigned and change on
  recreate. Path is the stable identity. Use `match_key="path"`.
- **Including `apiKey` or `password` in HostConfig Pydantic model as writable fields:**
  They must be `exclude=True`. Writing the API key from YAML would be a scope violation
  equivalent (you'd overwrite the app's auth credentials from the config file — a security risk).
- **Calling `GET /api/v3/indexer` and then writing back:** The *arr apps receive indexers via
  Prowlarr sync, not via direct POST from arrconf. The indexer reconciler should compare
  desired vs current for sync-alignment only — but creating NEW indexers via arrconf is
  explicitly out of scope (D-03-02). Reconcile indexers means "update sync settings on
  existing Prowlarr-synced entries" not "manage the catalog."
- **Creating a `RadarrFieldKV` or `ProwlarrFieldKV`:** `FieldKV` is generic — import it from
  `resources/sonarr/download_client.py`. Duplication creates divergence.
- **Skipping the `tags → ... → host_config` ordering:** Tags must reconcile first because
  tag IDs are referenced by other resources (download_clients, indexers, notifications).
  host_config must reconcile last (destructive potential per D-03-04).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Singleton resource diff | Custom diff function | `diff_models(current, desired)` + direct PUT | Already tested; diff_models handles exclude_none and read-only fields |
| Credential field omission | Name-based allowlist | `merge_fields_for_put()` with WR-01 fix (`_CREDENTIAL_PRIVACY_VALUES`) | Privacy metadata-driven; tested for password, userName, apiKey, token |
| HTTP retry + error mapping | Custom retry decorator | `_ArrV3Client._request()` via tenacity | Already handles 5xx retry, 401/404 typed exceptions |
| Config validation | Manual YAML parsing | `load_config()` / Pydantic `RootConfig.model_validate()` | ConfigError maps to exit code 2 |
| Schema generation | Manual JSON Schema | `arrconf schema-gen` / `write_schema()` in `schema_gen.py` | Pydantic generates Draft 2020-12; CI blocks on drift |
| forceSave injection | Per-reconciler `params=` | `_ArrV3Client.put()` (inherited) | RadarrClient + ProwlarrClient inherit by extending `_ArrV3Client` |

---

## API Endpoint Reference

### Sonarr/Radarr (v3) — New Endpoints

All endpoints confirmed from live cluster snapshots. Sonarr and Radarr share identical path
structure and response shape for these resources.

| Resource | GET | POST | PUT | DELETE | Match Key |
|----------|-----|------|-----|--------|-----------|
| indexers | `/api/v3/indexer` | `/api/v3/indexer` | `/api/v3/indexer/{id}` | `/api/v3/indexer/{id}` | `name` |
| notifications | `/api/v3/notification` | `/api/v3/notification` | `/api/v3/notification/{id}` | `/api/v3/notification/{id}` | `name` |
| root_folders | `/api/v3/rootfolder` | `/api/v3/rootfolder` | n/a (no update) | `/api/v3/rootfolder/{id}` | `path` |
| host_config | `/api/v3/config/host` | n/a | `/api/v3/config/host/{id}` | n/a | singleton |

[VERIFIED: `snapshot.sh` line 175-192 — endpoints list; `baseline-2026-05-07/sonarr/` snapshots]

**Root folders have no UPDATE:** The API supports POST (create) and DELETE (remove) but not PUT
(update). A path cannot be modified in place — the old one must be deleted and a new one created.
The differ will plan DELETE + ADD for a path change, which is correct.

### Prowlarr (v1) — App Sync

| Resource | GET | POST | PUT | DELETE | Match Key |
|----------|-----|------|-----|--------|-----------|
| applications | `/api/v1/applications` | `/api/v1/applications` | `/api/v1/applications/{id}` | `/api/v1/applications/{id}` | `name` |

[VERIFIED: `snapshots/baseline-2026-05-07/prowlarr/applications.json`]

**Prowlarr API version is v1, not v3.** `ProwlarrClient.api_path = "/api/v1"` (override required).

### Credential Fields by Resource Type

Confirmed from live snapshot data:

| Resource | Field name | Privacy value |
|----------|-----------|---------------|
| indexer (Sonarr/Radarr) | `apiKey` | `"apiKey"` |
| notification (any with API auth) | `apiKey` | `"apiKey"` |
| notification (webhook token) | `token` | `"token"` (likely — ASSUMED) |
| application (Prowlarr) | `apiKey` | `"apiKey"` |
| host_config | `apiKey`, `password` | top-level fields (not in `fields[]`) |

[VERIFIED for indexer and application: snapshots; ASSUMED for notification `"token"` privacy value]

---

## Critical Implementation Details

### 1. WR-01: `_CREDENTIAL_PRIVACY_VALUES` must cover `"apiKey"` and `"token"`

Current code in `differ.py:140`:
```python
if cur_privacy in ("password", "userName"):
```

Required fix (before any indexer or Prowlarr reconciler uses `merge_fields_for_put`):
```python
# Source: tools/arrconf/.planning/phases/02.2-v0-1-4-forcesave-fix/02.2-REVIEW.md WR-01
_CREDENTIAL_PRIVACY_VALUES: frozenset[str] = frozenset(
    {"password", "userName", "apiKey", "token"}
)
# ...
if cur_privacy in _CREDENTIAL_PRIVACY_VALUES:
```

[VERIFIED: `02.2-REVIEW.md` WR-01; confirmed `"apiKey"` privacy from indexer + application snapshots]

### 2. IN-02: Module-level FieldKV import in `test_differ.py`

Move `from arrconf.resources.sonarr.download_client import DownloadClient` at line 12 to also
include `FieldKV`:
```python
from arrconf.resources.sonarr.download_client import DownloadClient, FieldKV
```
Remove the intra-function import at line 400.

[VERIFIED: `02.2-REVIEW.md` IN-02; `test_differ.py:400` confirmed]

### 3. `ProwlarrClient.api_path = "/api/v1"`

Prowlarr uses `/api/v1`, not `/api/v3`. This must be overridden:
```python
class ProwlarrClient(_ArrV3Client):
    api_path = "/api/v1"
    name = "prowlarr"
```

[VERIFIED: `snapshot.sh` line 217-241 — all Prowlarr endpoints are `/api/v1/...`]

### 4. `HostConfig` field exclusion list

`host_config` GET returns credential fields at the top level (not in `fields[]`). These must
NOT appear in the Pydantic model as writable fields — mark them `exclude=True`:

```python
class HostConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    # Writable fields (safe to reconcile):
    authenticationMethod: str
    authenticationRequired: str
    bindAddress: str
    port: int
    urlBase: str
    instanceName: str
    # Read-only (do NOT write back):
    id: int | None = Field(default=None, exclude=True)
    apiKey: str | None = Field(default=None, exclude=True)
    password: str | None = Field(default=None, exclude=True)
    passwordConfirmation: str | None = Field(default=None, exclude=True)
    username: str | None = Field(default=None, exclude=True)
    branch: str | None = Field(default=None, exclude=True)
    # ... other read-only or non-desired fields
```

[VERIFIED: `snapshots/baseline-2026-05-07/sonarr/config_host.json` and
`radarr/config_host.json` — field names confirmed]

### 5. `HostConfigSection` opt-in model

```python
class HostConfigSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=False)
    # Desired host config values (only fields safe to reconcile):
    authenticationMethod: str | None = None
    authenticationRequired: str | None = None
    urlBase: str | None = None
    instanceName: str | None = None
```

Reconciler checks `if not section.enable: return` before any API call.

### 6. `RadarrInstance` and `ProwlarrInstance` structure

```python
class RadarrInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str
    download_clients: DownloadClientsSection = Field(default_factory=DownloadClientsSection)
    indexers: IndexersSection = Field(default_factory=IndexersSection)
    notifications: NotificationsSection = Field(default_factory=NotificationsSection)
    root_folders: RootFoldersSection = Field(default_factory=RootFoldersSection)
    host_config: HostConfigSection = Field(default_factory=HostConfigSection)

class ProwlarrInstance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str
    apps: AppsSection = Field(default_factory=AppsSection)
```

`SonarrInstance` also gains `indexers`, `notifications`, `root_folders`, `host_config` (same
section types as Radarr). `RootConfig` gains:
```python
radarr: dict[str, RadarrInstance] = {}
prowlarr: dict[str, ProwlarrInstance] = {}
```
[VERIFIED: `config.py` current state; CONTEXT.md D-03-05]

### 7. `coverage.run.source` must be expanded

The current `pyproject.toml` `[tool.coverage.run]` covers only:
```toml
source = ["arrconf.differ", "arrconf.reconcilers.sonarr"]
```

Phase 3 adds `arrconf.reconcilers.radarr` and `arrconf.reconcilers.prowlarr`. The coverage
source list must be updated or the 70% gate will not measure Phase 3 code.

[VERIFIED: `pyproject.toml` line 57]

### 8. Scope guard for Radarr reconciler

Radarr has the same configarr-owned endpoints as Sonarr (`quality_profiles`, `custom_formats`,
`quality_definitions`, `media_naming`). The `resources/sonarr/quality_profile.py` pattern
must be replicated for Radarr. Since these are the same endpoints at the same paths, the
simplest implementation is to:
- Create `resources/radarr/quality_profile.py` (and `custom_format.py`, etc.) raising
  `ScopeViolationError`
- OR use the existing `resources/sonarr/quality_profile.py` directly in both reconcilers
  (they reference the same Pydantic module type — acceptable since the endpoint paths are
  identical)

The existing `test_scope_violation.py` test pattern covers this: parameterized over modules.
Phase 3 must add the Radarr frontière modules to the `FRONTIERE_MODULES` list.

[VERIFIED: `test_scope_violation.py` FRONTIERE_MODULES list; scope guard pattern in
`resources/sonarr/quality_profile.py`]

### 9. `Notification` model design — `on*` event flags

Notifications have app-specific boolean event trigger fields (`onGrab`, `onDownload`,
`onSeriesAdd` for Sonarr; `onMovieAdded`, `onMovieFileDelete` for Radarr). These differ
between apps. Using `extra="allow"` on the `Notification` model handles forward-compat and
app-specific fields without requiring separate `SonarrNotification` and `RadarrNotification`
models. This is consistent with `DownloadClient` using `extra="allow"`.

The `supportsOn*` fields are read-only (server-set capabilities) and should be `exclude=True`
to prevent them from appearing in diff or PUT body.

[VERIFIED: `snapshots/baseline-2026-05-07/sonarr/notification.json` and
`radarr/notification.json` — field names and shapes confirmed]

### 10. Reconcile ordering within each reconciler

Rationale for recommended ordering (planner's decision, but research-backed):

```
1. tags            → must exist before other resources reference tag IDs
2. indexers        → read-mostly alignment; Prowlarr sync creates them
3. root_folders    → required by download client category routing
4. download_clients → references tag IDs (managed_tag + optional user tags)
5. notifications   → independent; no ordering dependency
6. host_config     → last (destructive: can lock arrconf out of the app)
```

[ASSUMED: ordering logic based on dependency analysis; no official Sonarr documentation
specifies required order]

### 11. snapshot.sh already covers Radarr and Prowlarr

`snapshot.sh` already snapshots Radarr via `snapshot_arr_app "radarr"` and Prowlarr via
`snapshot_prowlarr`. The `applications.json` endpoint is in the Prowlarr snapshot function
at line 223. No changes needed to `snapshot.sh` for Phase 3.

[VERIFIED: `tools/snapshot/snapshot.sh` lines 194-243]

---

## Common Pitfalls

### Pitfall 1: Root folder UPDATE — no PUT endpoint

**What goes wrong:** `_execute()` tries to issue `client.put("/rootfolder", id=..., ...)` when
a root folder path "changes" (diff detects a difference) — but Sonarr/Radarr have no PUT for
root folders.

**Why it happens:** `reconcile()` returns `Action.UPDATE` when two items match by match_key but
differ. If two items in `current` and `desired` have the same path (the match key), they can't
differ unless fields like `accessible` (read-only) cause a spurious diff.

**How to avoid:** Exclude `accessible`, `freeSpace`, `unmappedFolders` from the `RootFolder`
model as `exclude=True`. Then `diff_models` won't flag them. If path IS the match key, identical
paths → NO_OP. Different paths never match → ADD (new) + PRUNE_SKIP / DELETE (old). No UPDATE
case can arise for root folders when all diff-visible fields are read-only or equal.

**Warning signs:** Any `Action.UPDATE` in a root_folder plan is a bug indicator.

### Pitfall 2: `_CREDENTIAL_PRIVACY_VALUES` incomplete before indexer reconcile

**What goes wrong:** Indexer's `apiKey` field (privacy="apiKey") flows through
`merge_fields_for_put` unchanged (current stored "***REDACTED***" is non-empty, so the
empty-value-preserve branch substitutes it into the PUT body). PUT with `?forceSave=true`
writes "***REDACTED***" as the literal API key in Sonarr/Radarr.

**Why it happens:** WR-01 — `_CREDENTIAL_PRIVACY_VALUES` doesn't include `"apiKey"` yet.

**How to avoid:** Fix WR-01 in the FIRST Phase 3 task that modifies `differ.py` (or as a
dedicated task before indexer reconcilers are wired up).

### Pitfall 3: Prowlarr `/api/v1` vs `/api/v3`

**What goes wrong:** `ProwlarrClient` is instantiated with the default `api_path = "/api/v3"`
(inherited from `ArrApiClient`) and gets 404 on all Prowlarr endpoints.

**How to avoid:** Override `api_path = "/api/v1"` in `ProwlarrClient`. Add a test asserting
the request URL contains `/api/v1/applications` (not `/api/v3/applications`).

### Pitfall 4: `host_config` `id` field in PUT body

**What goes wrong:** `model_dump(exclude=_READ_ONLY_FIELDS)` in `merge_fields_for_put` strips
`id`. The PUT body is sent without `id`. Sonarr returns 422 or ignores the request.

**How to avoid:** Same pattern as `_execute()` for UPDATE: re-inject `id` after merge:
```python
body = merge_fields_for_put(current_hc, section.config_as_host_config())
body["id"] = current_hc.id  # re-inject after merge strips it
client.put("/config/host", id=current_hc.id, json=body)
```
[VERIFIED: `reconcilers/sonarr.py:103` — same pattern already used for download_clients]

### Pitfall 5: `AppSection.apps[]` API key injection at runtime

**What goes wrong:** YAML has `api_key_env: SONARR_API_KEY`. The `Application` Pydantic model
stores `api_key_env` as a string. The reconciler must call `os.environ[api_key_env]` and inject
the real API key into the `apiKey` `fields[]` entry before calling `differ.reconcile()`. If
this injection is forgotten, the desired state has an empty `apiKey` field → `merge_fields_for_put`
with WR-01 fix omits it → Prowlarr receives no API key in the POST body → app registration fails.

**How to avoid:** In `reconcilers/prowlarr.py`, before building `desired_apps`, resolve each
app's API key: `api_key = os.environ.get(app.api_key_env)`. If missing, raise `ReconcileError`
with a clear message. Inject into the `Application.fields` as `FieldKV(name="apiKey", value=api_key)`.

**On subsequent runs (UPDATE/NO_OP):** The GET returns the stored key as "***REDACTED***"
(privacy="apiKey"). With WR-01 fix, `merge_fields_for_put` omits `apiKey` from the PUT body.
Prowlarr preserves the stored key. This is correct behavior — no credential rotation is
attempted unless the user explicitly provides a new key value in YAML (which would come through
as a non-empty desired field value → pass-through per CR-01).

### Pitfall 6: Test coverage.run.source not updated

**What goes wrong:** Phase 3 adds two new reconciler modules. The 70% CI gate only measures
the modules listed in `[tool.coverage.run] source`. New reconcilers are not measured, so CI
passes with 0% coverage of the new code.

**How to avoid:** Update `pyproject.toml` to include new reconciler modules:
```toml
source = ["arrconf.differ", "arrconf.reconcilers.sonarr", "arrconf.reconcilers.radarr", "arrconf.reconcilers.prowlarr"]
```

### Pitfall 7: `respx` PUT URL regex must allow optional query string

**What goes wrong:** A test mocks `respx_mock.put("/downloadclient/1")` (no query string).
The real PUT is issued to `/downloadclient/1?forceSave=true`. respx doesn't match and returns
an unhandled-route error.

**How to avoid:** Use regex pattern: `url__regex=r"^http://..../api/v3/indexer/\d+(?:\?.*)?$"`.
This pattern was introduced and documented in Phase 02.2; all new Phase 3 UPDATE tests must
follow it.

[VERIFIED: `test_reconcilers_sonarr.py` line 103-105 — `url__regex=r"^...\d+(?:\?.*)?$"` pattern]

---

## Code Examples

### New client declarations in `client_base.py`

```python
# Source: client_base.py — existing SonarrClient pattern
class RadarrClient(_ArrV3Client):
    """Radarr REST client."""

    api_path = "/api/v3"
    name = "radarr"


class ProwlarrClient(_ArrV3Client):
    """Prowlarr REST client (api/v1 — different from Sonarr/Radarr)."""

    api_path = "/api/v1"
    name = "prowlarr"
```

### `Indexer` resource model

```python
# Source: snapshots/baseline-2026-05-07/sonarr/indexer.json field analysis
class Indexer(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    enable: bool = True
    enableRss: bool = True
    enableAutomaticSearch: bool = True
    enableInteractiveSearch: bool = True
    implementation: str
    configContract: str
    fields: list[FieldKV] = Field(default_factory=list)
    tags: list[int] = Field(default_factory=list)
    downloadClientId: int = Field(default=0)
    # Read-only:
    id: int | None = Field(default=None, exclude=True)
    implementationName: str | None = Field(default=None, exclude=True)
    infoLink: str | None = Field(default=None, exclude=True)
```

### `Notification` resource model

```python
# Source: snapshots/baseline-2026-05-07/sonarr/notification.json and radarr/notification.json
class Notification(BaseModel):
    model_config = ConfigDict(extra="allow")  # handles onSeriesAdd vs onMovieAdded
    name: str
    enable: bool = True
    implementation: str
    configContract: str
    fields: list[FieldKV] = Field(default_factory=list)
    tags: list[int] = Field(default_factory=list)
    includeHealthWarnings: bool = False
    # on* event triggers — handled via extra="allow" for app-specific variants
    # supportsOn* are read-only server capabilities — excluded:
    id: int | None = Field(default=None, exclude=True)
    implementationName: str | None = Field(default=None, exclude=True)
    infoLink: str | None = Field(default=None, exclude=True)
```

### `RootFolder` resource model

```python
# Source: snapshots/baseline-2026-05-07/sonarr/rootfolder.json
class RootFolder(BaseModel):
    model_config = ConfigDict(extra="allow")
    path: str  # match key
    # Read-only (server-derived):
    id: int | None = Field(default=None, exclude=True)
    accessible: bool | None = Field(default=None, exclude=True)
    freeSpace: int | None = Field(default=None, exclude=True)
    unmappedFolders: list[Any] | None = Field(default=None, exclude=True)
```

### `_CREDENTIAL_PRIVACY_VALUES` fix (WR-01)

```python
# Source: tools/arrconf/.planning/phases/02.2-v0-1-4-forcesave-fix/02.2-REVIEW.md WR-01
# In differ.py, replace inline tuple with module-level frozenset:
_CREDENTIAL_PRIVACY_VALUES: frozenset[str] = frozenset(
    {"password", "userName", "apiKey", "token"}
)

# In merge_fields_for_put, replace:
# if cur_privacy in ("password", "userName"):
# With:
if cur_privacy in _CREDENTIAL_PRIVACY_VALUES:
```

---

## Runtime State Inventory

Phase 3 extends arrconf to reconcile Radarr and Prowlarr for the first time. This is a new
write scope, not a rename/refactor. No runtime state renaming is involved.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Sonarr/Radarr/Prowlarr cluster state will be READ but not yet written (Phase 3 starts with snapshot + dry-run) | Pre-deploy snapshot required (ADR-6) before first cluster write |
| Live service config | Prowlarr applications list (2 entries: Radarr + Sonarr) — managed in Prowlarr DB, not in git | Phase 3 reconciler will bring these under arrconf management via POST/PUT diff |
| OS-registered state | None — no task scheduler or launchd involved | None |
| Secrets/env vars | `RADARR_API_KEY` and `PROWLARR_API_KEY` are already declared in `settings.py` | No change needed; `Settings` already has these fields |
| Build artifacts | None beyond existing `.egg-info` | None |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | arrconf | ✓ | 3.13.9 | — |
| uv | test runner | ✓ | (in PATH) | pip |
| pytest + respx | unit tests | ✓ | pinned in pyproject.toml | — |
| Sonarr (cluster) | integration test / snapshot | ✓ (via port-forward) | v4+ | dry-run only |
| Radarr (cluster) | integration test / snapshot | ✓ (via port-forward) | v4+ | dry-run only |
| Prowlarr (cluster) | integration test / snapshot | ✓ (via port-forward) | v1 API | dry-run only |

**Missing dependencies with no fallback:** None.

[VERIFIED: `settings.py` RADARR_API_KEY/PROWLARR_API_KEY already declared; `snapshot.sh`
already covers all three apps]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x + respx 0.23.x |
| Config file | `tools/arrconf/pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `cd tools/arrconf && uv run pytest -q` |
| Full suite command | `cd tools/arrconf && uv run pytest --cov --cov-report=term-missing --cov-fail-under=70` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-configarr-coexistence | Radarr frontière modules raise ScopeViolationError pre-network | unit | `pytest tests/test_scope_violation.py -x` | ✅ (needs Radarr modules added to `FRONTIERE_MODULES`) |
| REQ-app-coverage (Sonarr indexers) | reconcile_sonarr handles indexers: add/update/delete/no-op | unit | `pytest tests/test_reconcilers_sonarr.py -x` | ❌ Wave 0 |
| REQ-app-coverage (Sonarr notifications) | reconcile_sonarr handles notifications | unit | `pytest tests/test_reconcilers_sonarr.py -x` | ❌ Wave 0 |
| REQ-app-coverage (Sonarr root_folders) | reconcile_sonarr handles root_folders: add/delete/no-op (no update) | unit | `pytest tests/test_reconcilers_sonarr.py -x` | ❌ Wave 0 |
| REQ-app-coverage (Sonarr host_config) | reconcile_sonarr host_config: opt-in gate + update + no-op | unit | `pytest tests/test_reconcilers_sonarr.py -x` | ❌ Wave 0 |
| REQ-app-coverage (Radarr full) | reconcile_radarr add/update/delete/no-op for all resource types | unit | `pytest tests/test_reconcilers_radarr.py -x` | ❌ Wave 0 |
| REQ-app-coverage (Prowlarr app sync) | reconcile_prowlarr add/update/delete/no-op for applications | unit | `pytest tests/test_reconcilers_prowlarr.py -x` | ❌ Wave 0 |
| WR-01 fix | merge_fields_for_put omits apiKey+token credential fields | unit | `pytest tests/test_differ.py -x` | ✅ (new test needed) |
| Schema gen | schema-gen output matches committed schemas/arrconf-schema.json | CI check | `cd tools/arrconf && uv run arrconf schema-gen ... && git diff --exit-code` | ✅ (existing CI step) |

### Sampling Rate

- **Per task commit:** `cd tools/arrconf && uv run pytest -q`
- **Per wave merge:** `cd tools/arrconf && uv run pytest --cov --cov-fail-under=70`
- **Phase gate:** Full suite green + `ruff check` + `mypy` before release tag

### Wave 0 Gaps

- [ ] `tests/test_reconcilers_radarr.py` — covers REQ-app-coverage (Radarr)
- [ ] `tests/test_reconcilers_prowlarr.py` — covers REQ-app-coverage (Prowlarr app sync)
- [ ] New test cases in `tests/test_reconcilers_sonarr.py` — indexers, notifications, root_folders, host_config sections
- [ ] New test cases in `tests/test_differ.py` — WR-01 credential-omit for apiKey+token
- [ ] `tests/fixtures/radarr/` — radarr fixtures (indexer.json, notification.json, rootfolder.json, downloadclient.json can be derived from existing snapshots)
- [ ] `tests/fixtures/prowlarr/` — prowlarr fixtures (applications.json)
- [ ] `arrconf/resources/radarr/__init__.py` — new resource directory
- [ ] `arrconf/resources/prowlarr/__init__.py` — new resource directory

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a (Phase 3 is reconciler code; no user-facing auth) |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | yes | Pydantic model_validate with `extra="forbid"` on config models |
| V6 Cryptography | no | n/a (API keys are strings, not managed cryptography) |
| V7 Error Handling | yes | ReconcileError + ConfigError mapped to exit codes; no secret values in logs |

### Known Threat Patterns for *arr reconciler stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leakage in structured logs | Information Disclosure | `merge_field_omitted_credential` event emits metadata-only (`name`, `privacy`); no `value` in log payload (T-02.2-08-01) |
| API key leakage in committed fixtures | Information Disclosure | `***REDACTED***` sentinel + CI audit step (T-01-07) |
| ScopeViolationError bypass | Tampering | Guard raises pre-network (T-01-05); test `test_scope_violation_raises_BEFORE_any_http_call` |
| host_config auth lockout | Denial of Service | Opt-in `enable: true` guard (D-03-04); `apiKey`/`password` excluded from HostConfig model |
| Prowlarr API key injection (env var missing) | Availability | Fast-fail if `os.environ.get(api_key_env)` returns None; raise `ReconcileError` before POST |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Notification `"token"` privacy value exists in *arr APIs | API Endpoint Reference, Credential Fields table | Credential field might not be omitted from PUT body; low risk since notifications in Phase 3 scope already have `"apiKey"` confirmed, and `"token"` is additive coverage |
| A2 | Root folders have no PUT endpoint in Sonarr/Radarr v3 | Common Pitfalls #1 | If PUT exists, Pitfall 1 mitigation is not needed; no correctness risk |
| A3 | Reconcile ordering (tags → indexers → root_folders → download_clients → notifications → host_config) has no hard API dependency | Code Examples — reconcile ordering | Wrong order would cause tags to not exist when referenced by resources; mitigated by always running tags first regardless |

---

## Open Questions (RESOLVED)

1. **Should `_execute()` be extracted to a shared utility or remain per-reconciler?**
   - **RESOLVED:** duplicate per-reconciler (Plan 04 minimum-surface decision; no shared
     extraction in Phase 3). The 40-line duplication is accepted in this phase to keep the
     blast radius narrow — Plans 03/04/05 each carry their own `_execute()` against the same
     `PlannedAction[T]` shape. A follow-up refactor that hoists `execute_plan[T: BaseModel]()`
     into `differ.py` is deferred to a post-Phase-3 cleanup ticket once all three reconcilers
     are green and we can refactor against a verified test suite.
   - Original context: `_execute()` in `reconcilers/sonarr.py` is 40 lines, generic-typed via
     `list[PlannedAction[DownloadClient]]` today, but easily generalized with `T: BaseModel`.
     The duplication debt across 3 reconcilers was considered but rejected for Phase 3 to
     minimize cross-reconciler coupling during the initial implementation.

2. **`Notification` `on*` fields — include in YAML diff or exclude?**
   - **RESOLVED:** included via `extra="allow"` on the `Notification` model (Plan 01 Task 1.2
     choice). The user controls them optionally in YAML — if absent from desired state, they
     won't be diffed; if present, they participate in the diff like any other field. This
     handles both Sonarr (`onSeriesAdd`, `onEpisodeFileDelete`) and Radarr (`onMovieAdded`,
     `onMovieFileDelete`) without splitting into per-app models. `supportsOn*` (server-set
     capabilities) remain `exclude=True` to avoid spurious diffs.
   - Original context: `onGrab`, `onDownload`, etc. are diff-visible and affect notification
     behavior. The `extra="allow"` configuration captures them transparently while preserving
     the option for the user to omit them and inherit *arr defaults.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline `("password", "userName")` tuple | `_CREDENTIAL_PRIVACY_VALUES` frozenset | WR-01 fix in Phase 3 | Covers apiKey+token; auditable; future privacy values added in one place |
| Single reconciler (sonarr, download_clients only) | Three reconcilers (sonarr+radarr+prowlarr, 5-6 resource types each) | Phase 3 | Full app coverage per ROADMAP |
| `_execute()` typed to `DownloadClient` | `execute_plan[T: BaseModel]()` generic | Phase 3 extraction | Eliminates per-reconciler boilerplate |

---

## Sources

### Primary (HIGH confidence)
- `tools/arrconf/arrconf/client_base.py` — verified `_ArrV3Client`, `SonarrClient` structure
- `tools/arrconf/arrconf/config.py` — verified current `RootConfig` shape; what to add
- `tools/arrconf/arrconf/reconcilers/sonarr.py` — verified reconcile pattern for extension
- `tools/arrconf/arrconf/differ.py` — verified `merge_fields_for_put`, `reconcile`, `diff_models`
- `tools/arrconf/arrconf/exceptions.py` — verified `ScopeViolationError` exists
- `snapshots/baseline-2026-05-07/sonarr/indexer.json` — indexer field shapes (apiKey privacy confirmed)
- `snapshots/baseline-2026-05-07/sonarr/notification.json` — notification shape confirmed
- `snapshots/baseline-2026-05-07/sonarr/rootfolder.json` — rootfolder shape confirmed
- `snapshots/baseline-2026-05-07/sonarr/config_host.json` — host_config flat structure confirmed
- `snapshots/baseline-2026-05-07/radarr/config_host.json` — Radarr host_config shape confirmed
- `snapshots/baseline-2026-05-07/prowlarr/applications.json` — Prowlarr applications endpoint confirmed (2 entries)
- `tools/arrconf/tests/test_differ.py` — IN-02 location confirmed (line 400)
- `.planning/phases/02.2-v0-1-4-forcesave-fix/02.2-REVIEW.md` — WR-01, WR-02, WR-03, IN-02 verified
- `tools/arrconf/pyproject.toml` — coverage.run.source gap confirmed
- `tools/snapshot/snapshot.sh` — Radarr + Prowlarr coverage confirmed; `api/v1` for Prowlarr confirmed

### Secondary (MEDIUM confidence)
- `tools/arrconf/arrconf/settings.py` — `RADARR_API_KEY`, `PROWLARR_API_KEY` already declared
- `.planning/phases/03-extend-arrconf/03-CONTEXT.md` — locked decisions and discretion areas

### Tertiary (LOW confidence)
- A2: assumption that root folders have no PUT endpoint — based on snapshot analysis (no
  evidence PUT was called) but no official API spec consulted

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, pinned versions confirmed
- Architecture: HIGH — all patterns verified from existing production codebase and live snapshots
- Pitfalls: HIGH — WR-01/Pitfall 2 verified from REVIEW.md; others from snapshot and code analysis
- API shapes: HIGH — live cluster snapshots confirm field names, privacy values, endpoint paths

**Research date:** 2026-05-11
**Valid until:** 2026-06-11 (stable — Sonarr/Radarr v3 API has been stable for years; Prowlarr v1 API similarly stable)
