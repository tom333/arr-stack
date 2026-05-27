# Architecture Research

**Domain:** arr-stack v0.9.0 — integration of two new features into existing architecture
**Researched:** 2026-05-27
**Confidence:** HIGH (based on direct code inspection + targeted web research)

## Existing Architecture (DO NOT RE-RESEARCH — context only)

```
Operator laptop
├── arrconf-ui (uv run, LAN-only)
│   ├── FastAPI backend (5 endpoints)
│   │   ├── GET  /api/config  → reads charts/arr-stack/files/arrconf.yml
│   │   ├── PUT  /api/config  → validates RootConfig → atomic write
│   │   ├── GET  /api/schema  → returns schemas/arrconf-schema.json
│   │   └── POST /api/diff   → stateless preview
│   └── Svelte 5 SPA (schema-driven FieldInput.svelte)
│
└── charts/arr-stack/files/
    ├── arrconf.yml          ← arrconf-ui reads/writes
    └── configarr.yml        ← configarr reads (NOT currently touched by arrconf-ui)

Git commit + push (manual, no git-integration in UI)
    ↓
GitHub → ArgoCD → MicroK8s cluster (namespace: selfhost)
    ├── arrconf CronJob (Python reconciler, 6 apps)
    │   └── JellyfinReconciler: libraries / users / server_config / plugins (best-effort)
    │       └── _reconcile_plugins(): activation-only (D-07-PLUGINS-01)
    └── configarr CronJob (Node.js, reads configarr.yml mounted as ConfigMap)
```

---

## FEATURE A — REQ-config-ui-multi-config

### Integration Overview

The feature extends `arrconf-ui` to edit `configarr.yml` alongside `arrconf.yml`. The core
architectural question is: (1) where does the configarr schema come from, and (2) how does
TRaSH/Recyclarr metadata reach the UI?

### configarr Schema Source

configarr is a TypeScript/Node.js application (raydak-labs). Its configuration types live in
`src/types/config.types.ts` and use zod for validation — there is no published JSON Schema
artifact analogous to `schemas/arrconf-schema.json`. The project does NOT ship a
`configarr-schema.json` that arrconf-ui can consume directly.

**Decision: hand-author a JSON Schema for the configarr.yml subset used by this project.**

Rationale: the existing configarr.yml (460 lines) uses only a deterministic subset of
configarr's capabilities: `trashGuideUrl`, `recyclarrConfigUrl`,
`customFormatDefinitions[]`, `sonarr.<instance>.{base_url, api_key, media_naming,
quality_definition, quality_profiles[], custom_formats[]}`, and the same structure for
`radarr`. This subset is stable (configarr 1.16.0 in production) and maps cleanly to a
hand-authored JSON Schema. The schema lives at `schemas/configarr-schema.json` (mirroring
the arrconf pattern) and is regenerated manually when configarr's schema changes.

The schema must be pre-validated against the live configarr.yml before being committed to
avoid silent schema drift.

### TRaSH / Recyclarr Metadata: Build-time Bundled Snapshot (RECOMMENDED)

Two fetch strategies exist:

| Strategy | Mechanics | Trade-offs |
|----------|-----------|-----------|
| **Build-time bundled snapshot** | CI or developer runs a fetch script that pulls `docs/json/{sonarr,radarr}/cf/*.json` + quality profile templates from `github.com/TRaSH-Guides/Guides` and `github.com/recyclarr/config-templates`, bundles them as static JSON assets in `tools/arrconf-ui/web/src/assets/trash-metadata/` | No runtime network dependency; deterministic; offline-capable; update requires explicit refresh commit |
| Runtime live fetch | arrconf-ui backend calls GitHub raw at request time | Requires internet from operator laptop; adds latency; rate-limit risk; unstable in air-gapped scenarios |

**Recommend build-time bundled snapshot** (MEDIUM confidence — confirmed pattern used by Recyclarr and Sonarr/Radarr themselves to avoid GitHub rate limits at runtime). The fetch script (`tools/scripts/fetch-trash-metadata.sh` or a small Python script) runs manually when the operator wants to refresh the catalog; the result is committed. This is consistent with the project's "everything in git" ethos and the existing snapshot/ADR-6 discipline.

The metadata bundle required for the picker:
- `docs/json/sonarr/cf/*.json` — one file per Custom Format (contains `trash_id`, `name`, `trash_scores`)
- `docs/json/radarr/cf/*.json` — same for Radarr
- `docs/json/sonarr/quality-profiles/*.json` — named quality profiles (TRaSH-provided templates)
- `docs/json/radarr/quality-profiles/*.json` — same for Radarr
- Recyclarr config templates (`config-templates/docs/json/{sonarr,radarr}/*.yaml`) for `include:` template names

The arrconf-ui backend exposes this metadata through new read-only endpoints (see below); the
frontend renders a picker that translates name selections into `trash_ids` in the payload.

### New Backend Endpoints

The backend (`tools/arrconf-ui/arrconf_ui/app.py`) gains parallel configarr endpoints plus
metadata query endpoints:

```
Existing (unchanged)
  GET  /api/config          → arrconf.yml
  PUT  /api/config          → write arrconf.yml
  GET  /api/schema          → schemas/arrconf-schema.json
  POST /api/diff            → arrconf.yml diff preview

New — configarr file editing
  GET  /api/configarr/config   → charts/arr-stack/files/configarr.yml (parsed, validated)
  PUT  /api/configarr/config   → validate → atomic write → semantic diff
  POST /api/configarr/diff     → stateless preview vs on-disk configarr.yml
  GET  /api/configarr/schema   → schemas/configarr-schema.json

New — TRaSH/Recyclarr metadata (read-only, served from bundled snapshot)
  GET  /api/trash/custom-formats?app=sonarr|radarr
       → [{trash_id, name, description?, category?}, ...]
  GET  /api/trash/quality-profiles?app=sonarr|radarr
       → [{name, trash_id?, source: "TRASH"|"RECYCLARR"}, ...]
```

No new external HTTP calls from the backend at runtime. The metadata endpoints serve the
pre-bundled JSON files from disk (similar to how `/api/schema` serves `arrconf-schema.json`).

### locator.py Extension

`arrconf_ui/locator.py` gets two new helper functions:

```python
def configarr_yml_path() -> Path:
    return repo_root() / "charts" / "arr-stack" / "files" / "configarr.yml"

def configarr_schema_json_path() -> Path:
    return repo_root() / "schemas" / "configarr-schema.json"

def trash_metadata_dir() -> Path:
    return repo_root() / "tools" / "arrconf-ui" / "web" / "src" / "assets" / "trash-metadata"
```

### configarr.yml Validation Strategy

configarr uses `!env VAR_NAME` YAML tags for API keys (`api_key: !env SONARR_API_KEY`).
ruyaml round-trip preserves these tags correctly (as `TaggedScalar` objects). The arrconf-ui
io.py `read_yaml` / `write_yaml_atomic` path already handles tagged scalars — **no change
needed** to the IO layer. The JSON round-trip normalization in `_read_current()` drops tags
when building the `dict` for pydantic validation, which is correct (pydantic sees the string
`"!env SONARR_API_KEY"` as a string, or the validator can special-case the pattern).

The configarr JSON Schema should mark `api_key` fields as `readOnly: true` in the UI
(display-only, never edited through the UI — operator manages them via sealed-secrets).

### Svelte Frontend Changes

The frontend must support **config selector** (switch between `arrconf.yml` and
`configarr.yml`). Two integration options:

| Option | Mechanics | Verdict |
|--------|-----------|---------|
| **Tab/selector in App.svelte** | Single SPA, top-level tab `{ arrconf | configarr }`, loads different schema+config pair | RECOMMENDED — minimal new code; reuses all existing components |
| Separate route / separate page | Second `<Route>` or second static SPA entry | Overkill for a local single-user tool |

The existing `FieldInput.svelte` schema-driven dispatcher handles all YAML types present in
`configarr.yml` (strings, integers, booleans, arrays of objects, nested objects). No changes
to `FieldInput.svelte` are expected — the component is already generic.

The new TRaSH picker for `custom_formats[].trash_ids` requires a **new specialized
component** (`TrashPicker.svelte`) that renders a searchable multi-select from the metadata
catalog rather than a comma-separated text field. This component is invoked from
`FieldInput.svelte` when `path` matches the pattern `*.custom_formats[*].trash_ids` (or via
a schema annotation like `x-widget: trash-picker`).

Similarly, quality profile `include[].template` benefits from a name autocomplete dropdown
(`RecyclarrTemplatePicker.svelte`) driven by the bundled Recyclarr template catalog.

### `api.ts` Extension

The frontend `api.ts` gains parallel functions for the configarr endpoints plus metadata
fetchers:

```typescript
getConfigarrConfig(): Promise<ConfigarrPayload>
putConfigarrConfig(payload): Promise<ConfigarrDiffResponse>
postConfigarrDiff(payload): Promise<ConfigarrDiffResponse>
getConfigarrSchema(): Promise<RootSchema>
getTrashCustomFormats(app: 'sonarr' | 'radarr'): Promise<TrashCFEntry[]>
getTrashQualityProfiles(app: 'sonarr' | 'radarr'): Promise<TrashQPEntry[]>
```

### ADR-5 Boundary Preservation

ADR-5 is preserved: arrconf-ui edits the **file** `configarr.yml`; configarr continues to
apply it in-cluster via its CronJob. arrconf itself never touches quality_profiles or custom
formats APIs. The `ScopeViolationError` guard in arrconf reconcilers is unchanged.

### Data Flow — Feature A

```
Operator (browser)
    ↓ GET /api/configarr/config + GET /api/configarr/schema + GET /api/trash/custom-formats
arrconf-ui FastAPI backend
    ├── reads charts/arr-stack/files/configarr.yml (ruyaml round-trip)
    ├── reads schemas/configarr-schema.json (hand-authored)
    └── reads tools/arrconf-ui/web/src/assets/trash-metadata/{sonarr,radarr}/*.json (bundled)
    ↓
Svelte SPA (configarr tab)
    ├── App.svelte: config selector (arrconf | configarr) drives schema+config pair
    ├── FieldInput.svelte: generic fields (unchanged)
    ├── TrashPicker.svelte: NEW — multi-select from TRaSH CF catalog
    └── RecyclarrTemplatePicker.svelte: NEW — dropdown from Recyclarr template list
    ↓ PUT /api/configarr/config (on save)
arrconf-ui FastAPI backend
    └── validate → atomic write → configarr.yml updated on disk
    ↓
Manual git commit + push (operator)
    ↓
ArgoCD → configarr CronJob reads updated ConfigMap → applies to Sonarr/Radarr
```

---

## FEATURE B — REQ-jellyfin-skip-intro

### Plugin Delivery: Repository-Install vs Pre-baked Image

Two strategies for getting the Intro Skipper binary into the Jellyfin pod:

| Strategy | Mechanics | Verdict |
|----------|-----------|---------|
| **Jellyfin plugin-repo install via API** | arrconf adds the Intro Skipper manifest URL to `PluginRepositories` in `/System/Configuration`, then calls `POST /Packages/Installed?packageName=Intro%20Skipper&assemblyGuid=<guid>&version=<ver>` to trigger in-cluster download+install; restart required | RECOMMENDED — no image customization; Renovate-trackable via `values.yaml` annotation on the plugin version |
| Pre-baked custom Jellyfin image | Fork/extend linuxserver/jellyfin, copy the plugin `.dll` into the image | Requires custom Dockerfile + new GHCR repo + Renovate tracking two versions; heavy for a single plugin |

**Recommended: repository-install via API**, extended across two arrconf reconciler steps:

1. **Step 3 (`_reconcile_server_config`)** — existing step already manages `PluginRepositories`. Add the Intro Skipper repository entry (`https://intro-skipper.org/manifest.json`, `Name: "Intro Skipper"`) to the `plugin_repositories` list in `arrconf.yml`. This is purely declarative and idempotent — the existing `_server_config_equivalent()` set-by-URL comparison already handles it.

2. **Step 4 (`_reconcile_plugins`)** — existing step currently handles activation-only (D-07-PLUGINS-01). It logs `plugin_missing_skip` when a plugin is not installed. For Intro Skipper, the step must be extended to **also trigger install** when the plugin is absent from `GET /Plugins` but is present in a known repository.

### Extending D-07-PLUGINS-01: Activation-only → Install + Activate

Current behavior: if plugin not in `GET /Plugins` → log warning, skip. This was the correct
conservative default. For Intro Skipper, the operator currently installs via UI.

New behavior for plugins with `install: true` in the YAML config:
```
GET /Plugins → plugin absent
  → POST /Packages/Installed?packageName=...&assemblyGuid=...&version=...
     (triggers in-cluster download from the already-configured repo URL)
  → log "plugin_install_triggered"; note "restart required"
  → next reconciler run (after Jellyfin restart): GET /Plugins → plugin present
  → POST /Plugins/{id}/{version}/Enable (existing activation path)
```

The `POST /Packages/Installed` endpoint (confirmed via Jellyfin source/community):
- Requires `packageName` (display name) + `assemblyGuid` (UUID from manifest) + `version`
- Uses existing `JELLYFIN_API_KEY` — no new credentials needed
- Download happens in-process; server restart required for the plugin to activate
- Install is idempotent (calling again on an already-installed plugin is a no-op or safe error)

The `assemblyGuid` and `version` for Intro Skipper are known from the manifest and must be
pinned in `arrconf.yml` (Renovate can track them via a custom regex manager).

**Important constraint:** Jellyfin 10.11.8 (current production) is confirmed compatible with
Intro Skipper (requires 10.11.8+ and ffmpeg 7.1.1-7+). The `linuxserver/jellyfin` image
bundles its own ffmpeg. Verify that the bundled ffmpeg version meets the requirement before
the first live run.

### Intro Skipper Configuration

After installation, Intro Skipper exposes a plugin configuration endpoint. The plugin
auto-schedules a "Detect and Analyze Media Segments" background task after restart. No
per-episode API calls from arrconf are needed — the plugin runs autonomously on its schedule.

arrconf's role is:
1. Ensure the plugin repository is declared (server_config step)
2. Ensure the plugin is installed (packages step — new)
3. Ensure the plugin is enabled/active (plugins step — existing)
4. Optionally: POST to the plugin's configuration endpoint to set scan schedule / enable
   chapter markers (MEDIUM confidence this endpoint exists; confirm against live instance)

The chapter marker extraction (for Kodi/JellyCon) is handled by Intro Skipper itself — it
writes chapter metadata to Jellyfin's media segments. No arrconf reconciler code needed for
chapter data.

### Kodi/JellyCon Support

Kodi support for media segment skip is NOT native JellyCon as of the research date. The
mechanism requires the third-party `service.jellyskip` Kodi addon
(`github.com/SgtJalau/service.jellyskip`) which calls Jellyfin's Media Segments API
(`GET /MediaSegments/{itemId}`) and shows a skip button. JellyCon itself has an open issue
(jellyfin/jellyfin-kodi#953) for native support but it is not merged.

**Implication for roadmap:** Kodi/JellyCon skip is best-effort and requires a separate
operator step (install `service.jellyskip` on LibreELEC), not managed by arrconf. arrconf
only needs to ensure the plugin is installed and enabled in Jellyfin — the client-side Kodi
addon is entirely out of arrconf's scope.

### arrconf.yml Changes for Feature B

New section under `jellyfin.main.server_config.plugin_repositories`:

```yaml
jellyfin:
  main:
    server_config:
      plugin_repositories:
        - Name: "Intro Skipper"
          Url: "https://intro-skipper.org/manifest.json"
          Enabled: true
    plugins:
      required:
        - name: "Intro Skipper"
          id: "<assemblyGuid-from-manifest>"   # pinned, Renovate-trackable
          version: "<version>"                  # pinned
          install: true                         # new field — triggers POST /Packages/Installed
```

### Data Flow — Feature B

```
arrconf apply (CronJob in-cluster)
    ↓ Step 3: _reconcile_server_config
    ├── GET /System/Configuration
    ├── merge PluginRepositories (add Intro Skipper repo URL if absent)
    └── POST /System/Configuration (if changed)
    ↓ Step 4: _reconcile_plugins (extended)
    ├── GET /Plugins
    ├── Intro Skipper absent? → POST /Packages/Installed?packageName=...
    │   (Jellyfin downloads .zip from intro-skipper.org/manifest.json repo)
    ├── Operator: restart Jellyfin pod (kubectl rollout restart or ArgoCD)
    └── Next run: GET /Plugins → present → POST /Plugins/{id}/{version}/Enable
    ↓ Jellyfin (after restart)
    └── Intro Skipper plugin active
        └── "Detect and Analyze Media Segments" scheduled task runs autonomously
            ├── Web/Swiftfin: native skip prompt (Media Segments API, Jellyfin 10.10+)
            └── Kodi salon: service.jellyskip (operator-installed addon, best-effort)
```

---

## Component Boundaries: New vs Modified

### Feature A

| Component | Status | Change |
|-----------|--------|--------|
| `arrconf_ui/locator.py` | MODIFIED | Add `configarr_yml_path()`, `configarr_schema_json_path()`, `trash_metadata_dir()` |
| `arrconf_ui/app.py` | MODIFIED | Add 4 configarr endpoints + 2 trash metadata endpoints |
| `arrconf_ui/io.py` | UNCHANGED | Already handles tagged scalars correctly |
| `schemas/configarr-schema.json` | NEW | Hand-authored JSON Schema for configarr.yml subset |
| `tools/scripts/fetch-trash-metadata.sh` | NEW | Fetches TRaSH/Recyclarr JSON files → bundled assets |
| `tools/arrconf-ui/web/src/assets/trash-metadata/` | NEW | Bundled TRaSH/Recyclarr catalog snapshots |
| `web/src/App.svelte` | MODIFIED | Add config selector (tab/toggle for arrconf vs configarr) |
| `web/src/api.ts` | MODIFIED | Add configarr + trash metadata API functions |
| `web/src/lib/TrashPicker.svelte` | NEW | Multi-select from TRaSH CF catalog |
| `web/src/lib/RecyclarrTemplatePicker.svelte` | NEW | Dropdown for Recyclarr include templates |
| `web/src/lib/FieldInput.svelte` | POTENTIALLY MODIFIED | Hook for `x-widget: trash-picker` dispatch |
| `web/src/types.ts` | MODIFIED | Add `ConfigarrPayload`, `TrashCFEntry`, `TrashQPEntry` types |
| `tools/arrconf-ui/tests/` | MODIFIED | Add tests for the 6 new endpoints |

### Feature B

| Component | Status | Change |
|-----------|--------|--------|
| `arrconf/reconcilers/jellyfin.py` | MODIFIED | Extend `_reconcile_plugins()` to support `install: true` via `POST /Packages/Installed` |
| `arrconf/config.py` | MODIFIED | Add `install: bool = False` field to `JellyfinPluginEntry` (or equivalent config model) |
| `charts/arr-stack/files/arrconf.yml` | MODIFIED | Add Intro Skipper repo + plugin entry |
| `arrconf/tests/test_jellyfin.py` | MODIFIED | Add tests for install path (plugin absent + install:true → POST /Packages/Installed) |
| `tools/arrconf/arrconf/reconcilers/jellyfin.py` CONSTANTS | MODIFIED | Add `PACKAGES_PATH = "/Packages/Installed"` |

---

## Build Order (Phase Dependencies)

### Feature A Dependency Chain

```
1. Fetch + bundle TRaSH metadata (script + committed assets)
   → prerequisite for TrashPicker component
2. Hand-author schemas/configarr-schema.json
   → prerequisite for GET /api/configarr/schema endpoint and frontend form
3. Backend: add configarr file endpoints (locator + app.py)
   → prerequisite for frontend configarr tab
4. Backend: add trash metadata endpoints
   → prerequisite for TrashPicker
5. Frontend: config selector + configarr tab (App.svelte + api.ts + types.ts)
   → depends on steps 2+3
6. Frontend: TrashPicker + RecyclarrTemplatePicker components
   → depends on steps 4+5
7. Tests: new backend endpoint tests + frontend smoke
   → depends on all above
```

### Feature B Dependency Chain

```
1. Confirm Intro Skipper manifest assemblyGuid + version (from manifest URL)
   → prerequisite for arrconf.yml update + config.py model change
2. Extend JellyfinPluginEntry config model (config.py)
   → prerequisite for reconciler change
3. Extend _reconcile_plugins() in jellyfin.py + add tests
   → depends on step 2
4. Update arrconf.yml (plugin_repositories + plugins.required entry)
   → depends on step 1 (need the GUID)
5. Co-bump arrconf image tag in values.yaml
   → depends on step 3 (code change triggers image bump requirement)
6. Live cluster test: dry-run first, then non-dry-run
   → depends on steps 3+4+5
```

### Cross-feature ordering

Features A and B are **independent** — they touch different codebases (arrconf-ui vs arrconf
Python + chart) and can be built in parallel or sequentially. No shared dependency.

Suggested milestone phase order:
1. **Phase 24**: Feature B (smaller scope, touches arrconf which has tighter test discipline)
2. **Phase 25**: Feature A — schema authoring + backend endpoints + metadata fetch script
3. **Phase 26**: Feature A — frontend config selector + configarr form
4. **Phase 27**: Feature A — TrashPicker + RecyclarrTemplatePicker specialized components

Alternatively Feature A first if the operator wants the UI improvement sooner.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Runtime fetch of TRaSH metadata from GitHub in the backend

**What people do:** Call `https://raw.githubusercontent.com/TRaSH-Guides/Guides/master/docs/json/...`
at request time from the FastAPI backend.

**Why wrong:** Adds GitHub API rate-limit risk (60 req/h unauthenticated); makes arrconf-ui
non-functional offline or when GitHub is slow; adds latency to every picker interaction.

**Do this instead:** Bundle the metadata as static files committed to the repo. Refresh via
an explicit script run (operator-controlled, not automatic).

### Anti-Pattern 2: Generating configarr schema from TypeScript source at runtime

**What people do:** Run `ts-json-schema-generator` against configarr's `config.types.ts`
as part of arrconf-ui startup or CI.

**Why wrong:** Requires Node.js toolchain in the arrconf-ui Python environment; the full
configarr TypeScript type tree is much larger than the subset this project uses; subtle
type differences between configarr's internal types and the operator's actual YAML.

**Do this instead:** Hand-author a JSON Schema covering only the fields present in the
project's `configarr.yml`. Pin it to the configarr version in production. Update manually
when upgrading configarr.

### Anti-Pattern 3: Extending arrconf to write quality_profiles/custom_formats via API

**What people do:** Add a reconciler method that pushes quality profile data to
`/api/v3/qualityprofile` in Sonarr/Radarr.

**Why wrong:** ADR-5 hard frontier. configarr is the exclusive owner of these endpoints.
arrconf has a `ScopeViolationError` guard.

**Do this instead:** Edit `configarr.yml` via the UI (Feature A) and let configarr apply
it in-cluster. The operator edits the file; configarr does the API writes.

### Anti-Pattern 4: Pre-baking Intro Skipper into a custom Jellyfin image

**What people do:** Create a custom Dockerfile extending `lscr.io/linuxserver/jellyfin`,
COPY the plugin .dll, manage a second GHCR repo + Renovate tracking.

**Why wrong:** Duplicates infrastructure; plugin updates require image rebuilds; linuxserver
base image updates must be rebased.

**Do this instead:** Use the Jellyfin plugin repository API to install at runtime. The
plugin binary is managed by Jellyfin's own package system; Renovate can track the version
via a custom regex annotation on the `id`/`version` fields in `arrconf.yml`.

### Anti-Pattern 5: Treating plugin install as idempotent without checking restart state

**What people do:** Call `POST /Packages/Installed` on every arrconf run.

**Why wrong:** May trigger unnecessary re-downloads; the endpoint behavior on
already-installed plugins is not guaranteed no-op across Jellyfin versions.

**Do this instead:** Only call `POST /Packages/Installed` when `GET /Plugins` confirms the
plugin is absent. Gate on `entry.install == True` in the YAML. Log that a restart is
required; do not attempt to restart from arrconf (out of scope for a CronJob reconciler).

---

## Integration Points Summary

### External Services (new for v0.9.0)

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| TRaSH-Guides GitHub repo | Build-time fetch script, bundled as static assets | No runtime network; update via explicit script commit |
| Recyclarr config-templates GitHub repo | Same fetch script | Template names for `include:` picker |
| Intro Skipper manifest (`intro-skipper.org/manifest.json`) | Jellyfin reads during plugin install (in-cluster) | arrconf adds repo URL to PluginRepositories; Jellyfin does the actual HTTP fetch |
| Jellyfin `POST /Packages/Installed` | Called from arrconf CronJob in-cluster when plugin absent | Uses existing `JELLYFIN_API_KEY`; restart required after |

### Internal Boundaries (new for v0.9.0)

| Boundary | Communication | Notes |
|----------|---------------|-------|
| arrconf-ui → configarr.yml | Direct file read/write (ruyaml round-trip), same path pattern as arrconf.yml | `locator.configarr_yml_path()` |
| arrconf-ui → trash-metadata bundle | Static file serve from bundled assets dir | No HTTP; backend reads from disk |
| arrconf Jellyfin reconciler → Jellyfin Packages API | `POST /Packages/Installed` via existing `JellyfinClient._request()` | Requires Jellyfin restart after; arrconf logs warning |
| arrconf Jellyfin reconciler → Jellyfin PluginRepositories | Already managed via server_config step; Intro Skipper repo entry is purely additive | Idempotent via existing set-by-URL logic in `_server_config_equivalent()` |

---

## Sources

- `tools/arrconf-ui/arrconf_ui/app.py` (direct inspection — existing endpoint contract)
- `tools/arrconf-ui/arrconf_ui/locator.py` (direct inspection — file path pattern)
- `tools/arrconf-ui/arrconf_ui/io.py` (direct inspection — ruyaml tagged scalar handling)
- `tools/arrconf/arrconf/reconcilers/jellyfin.py` (direct inspection — D-07-PLUGINS-01 current behavior)
- `charts/arr-stack/files/configarr.yml` (direct inspection — fields in use, `!env` tag pattern)
- [Configarr configuration file docs](https://configarr.de/docs/configuration/config-file/)
- [Configarr config.types.ts](https://github.com/raydak-labs/configarr/blob/main/src/types/config.types.ts)
- [TRaSH Guides JSON structure](https://deepwiki.com/TRaSH-Guides/Guides/2.1-custom-format-structure)
- [TRaSH Guides GitHub — `docs/json/` paths](https://github.com/TRaSH-Guides/Guides/blob/master/metadata.json)
- [Intro Skipper GitHub](https://github.com/intro-skipper/intro-skipper)
- [Intro Skipper plugin repository manifest](https://github.com/intro-skipper/jellyfin-plugin-repo/blob/main/manifest.json)
- [Intro Skipper installation wiki](https://github.com/intro-skipper/intro-skipper/wiki/Installation)
- [Jellyfin skip intro — Kodi/JellyCon issue #953](https://github.com/jellyfin/jellyfin-kodi/issues/953)
- [service.jellyskip (Kodi addon)](https://github.com/SgtJalau/service.jellyskip)

---
*Architecture research for: arr-stack v0.9.0 integration (REQ-config-ui-multi-config + REQ-jellyfin-skip-intro)*
*Researched: 2026-05-27*
