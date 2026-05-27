# Stack Research — v0.9.0 New Features

**Domain:** arr-stack v0.9.0 — configarr-in-UI + Jellyfin intro skipper
**Researched:** 2026-05-27
**Confidence:** HIGH (all key facts verified against live source files, manifests, and upstream type definitions)

---

## Scope

This document covers ONLY the stack additions needed for the two new features in v0.9.0.
The existing validated stack (Python 3.13, httpx, pydantic v2, ruyaml, structlog, pytest/respx,
FastAPI, Svelte 5, Vite, TypeScript) is not re-researched.

---

## Feature A — REQ-config-ui-multi-config (configarr.yml editor in arrconf-ui)

### A1. configarr config.yml — schema source

**No published JSON Schema exists.** configarr (raydak-labs, TypeScript + Zod) does NOT export
a `configarr-schema.json`. The schema lives in `src/types/config.types.ts` as TypeScript types.

The authoritative model is the `InputConfigSchema` / `InputConfigArrInstance` / `InputConfigQualityProfile`
type tree, verified live from the main branch (2026-05-27):

```
InputConfigSchema
  trashGuideUrl, recyclarrConfigUrl           # optional URL overrides
  compatibilityTrashGuide20260219Enabled       # IMPORTANT: default false = new Feb-2026 behavior
  customFormatDefinitions[]                    # local CF objects (TrashCF shape: trash_id, trash_scores, name, specifications[])
  sonarr: Record<name, InputConfigArrInstance>
  radarr: Record<name, InputConfigArrInstance>

InputConfigArrInstance
  base_url: string
  api_key: string                              # always !env or !secret in production
  quality_definition: { type, qualities[] }
  include[]: { template, source?: "TRASH"|"RECYCLARR" }   # template IDs
  custom_format_groups[]                       # cf-group refs (experimental, v1.12+ / v1.28+)
  custom_formats[]: { trash_ids[], assign_scores_to[] }
  quality_profiles[]: InputConfigQualityProfile
  renameQualityProfiles[]                      # { from, to }
  cloneQualityProfiles[]                       # { from, to }
  media_naming                                 # recyclarr-compatible naming config

InputConfigQualityProfile
  name, language, reset_unmatched_scores, upgrade, min_format_score, quality_sort
  qualities[]: { name, qualities[]?, enabled? }
```

**Implication for UI schema design:** The pydantic-generated `arrconf-schema.json` pattern
(used today for arrconf.yml) CANNOT be reused for configarr.yml — configarr has no pydantic
model. The UI must define its own Python pydantic model for the configarr config file structure,
used to:
1. Validate the YAML before write (pydantic, backend)
2. Generate a JSON Schema for the Svelte form dispatcher (same `FieldInput.svelte` + `AppSection.svelte` pattern)

**Recommended approach:** Hand-write a pydantic v2 model `ConfigarrRootConfig` in
`tools/arrconf-ui/` (NOT in `tools/arrconf/` — ADR-5 boundary). The model covers:
- Global fields: `trashGuideUrl`, `recyclarrConfigUrl`, `compatibilityTrashGuide20260219Enabled`
- `customFormatDefinitions` list
- `sonarr` / `radarr` dicts of instance models
- Per-instance: `quality_definition`, `include[]`, `custom_formats[]`, `quality_profiles[]`,
  `renameQualityProfiles[]`, `cloneQualityProfiles[]`

The model does NOT need to cover experimental/optional fields like `root_folders`, `download_clients`,
`delay_profiles`, `custom_format_groups` — these are already managed by arrconf and out of configarr's
scope per ADR-5, or rarely used in this homelab.

Confidence: HIGH — source types verified live from `https://github.com/raydak-labs/configarr/blob/main/src/types/config.types.ts`

### A2. ruyaml round-trip with !env / !secret tags

**ruyaml ALREADY handles !env and !secret tags without any custom constructor.** The round-trip
YAML parser (`YAML(typ="rt")`) represents them as `ruyaml.comments.TaggedScalar` objects and
preserves both the tag and the scalar value verbatim on dump. This was verified live:

```python
# Input:  api_key: !env SONARR_API_KEY
# After read_yaml() + write_yaml_atomic() → api_key: !env SONARR_API_KEY   (unchanged)
```

The existing `arrconf_ui/io.py` `_yaml()` factory (`YAML(typ="rt")`, `preserve_quotes=True`)
works for configarr.yml without modification.

**Constraint for the pydantic layer:** The pydantic model for `ConfigarrRootConfig` must treat
`api_key` fields as `str | Any` or skip them from validation (they are `TaggedScalar` objects
after YAML load, not plain strings). The pattern is to do the JSON round-trip normalization
(already done in `_read_current()` for arrconf.yml) only for the in-memory form state, NOT for
the write path. The write path must operate on the ruyaml CommentedMap directly to preserve tags.

No new libraries needed for YAML handling. Confidence: HIGH — tested live with ruyaml 0.91.

### A3. TRaSH-Guides custom format catalog

**Source:** `https://github.com/TRaSH-Guides/Guides` (official, no authentication)

**Custom format JSON path:** `docs/json/radarr/cf/<name>.json` and `docs/json/sonarr/cf/<name>.json`

**Verified structure** (live, `br-disk.json`):
```json
{
  "trash_id": "ed38b889b31be83fda192888e2286d83",
  "trash_scores": { "default": -10000, "german": -35000 },
  "name": "BR-DISK",
  "includeCustomFormatWhenRenaming": false,
  "specifications": [...]
}
```

**BREAKING CHANGE (Feb 2026):** TRaSH-Guides changed CF group semantics in commit
`2994a797` (2026-02-19). configarr 1.22.0+ defaults to the new behavior
(`compatibilityTrashGuide20260219Enabled: false`). This project's `configarr.yml` already uses
custom `customFormatDefinitions` (not cf-groups or includes), so this change does NOT affect the
current config. A new UI that adds `include:` template support must warn the operator that
templates written before Feb 2026 may have inverted semantics.

**For the UI's TRaSH picker (CF names):** The UI does NOT need to clone the TRaSH-Guides repo.
The picker is a UX convenience — operator sees CF name, selects it, and the `trash_id` is
inserted. Two approaches:
1. Static baked-in catalog (enumerate from `docs/json/{radarr,sonarr}/cf/` at build time)
2. Runtime fetch from GitHub raw (adds latency, requires network from the UI)

**Recommended:** Baked-in catalog as a TypeScript constant generated at build time from a
`scripts/fetch-trash-catalog.py` script. This is a dev-time artifact only, not a runtime
dependency. The catalog maps `name → trash_id` per app (sonarr/radarr). Update manually or
via Renovate-triggered script when TRaSH-Guides publishes a new release.

No new Python or npm libraries needed for the catalog itself. Confidence: HIGH — TRaSH-Guides
repo structure verified live.

### A4. Recyclarr templates catalog

**Source:** `https://github.com/recyclarr/config-templates`

**Structure:** `includes.json` maps `id` → template YAML file path. Template IDs are strings
like `sonarr-v4-quality-profile-web-1080p`, `radarr-quality-profile-hd-bluray-web`. These IDs
go directly into `include[].template` in `configarr.yml`.

**Verified live (64 radarr includes, 34 sonarr includes in `includes.json`).**

configarr uses Recyclarr templates by resolving `include.template` values against its local
clone of `recyclarr/config-templates`. No extra field is needed in `configarr.yml` for the
repo URL (`recyclarrConfigUrl` defaults to `https://github.com/recyclarr/config-templates`).

**For the UI:** Same baked-in catalog approach as TRaSH-Guides CFs. A Python script fetches
`includes.json` at build time and writes a `recyclarr-templates.ts` constant with IDs + display
names. The operator picks templates by name from a `<select>` dropdown; the ID is written to
`include[].template`.

No new libraries needed. Confidence: HIGH.

### A5. configarr.yml multi-config backend endpoints (arrconf-ui extension)

The existing `app.py` serves exactly 4 endpoints for `arrconf.yml`. For `configarr.yml`, add
a parallel set of 4 endpoints with a `configarr` prefix:

| New Endpoint | Mirrors |
|---|---|
| `GET /api/configarr/config` | `GET /api/config` |
| `PUT /api/configarr/config` | `PUT /api/config` |
| `POST /api/configarr/diff` | `POST /api/diff` |
| `GET /api/configarr/schema` | `GET /api/schema` |

`locator.py` needs a `configarr_yml_path()` function (same `repo_root() / "charts/arr-stack/files/configarr.yml"` pattern).

`schema` endpoint returns a hand-crafted or pydantic-generated JSON Schema for `ConfigarrRootConfig`.

**No new Python libraries needed.** The existing `fastapi`, `ruyaml`, `pydantic`, `structlog` stack
covers the configarr-ui backend extension entirely.

### A6. Svelte frontend extension for configarr tab

The Svelte app needs a second tab/mode that switches between `arrconf.yml` and `configarr.yml`
forms. The existing `AppSection.svelte` + `FieldInput.svelte` schema-driven dispatcher already
handles arbitrary JSON Schema, so rendering the configarr form is a matter of wiring the new
`/api/configarr/*` endpoints and a tab-switch component.

**Special handling needed:**
- `trash_ids` fields: render as a multi-select or comma-separated text with the TRaSH catalog
  as an autocomplete/datalist. The baked-in catalog enables `<datalist>` suggestions in plain HTML5.
- `include[].template` fields: render as a searchable `<select>` from the Recyclarr catalog.
- `api_key` fields: render as masked `<input type="password">` even though the value stored is
  `!env VAR_NAME` (a string, not a secret). The UI displays the literal string (e.g., `SONARR_API_KEY`);
  it is NOT a secrets manager.

**No new npm packages needed.** The existing Svelte 5 / Vite / TypeScript stack is sufficient.
The catalog constants add a few KB of TypeScript — no separate library.

---

## Feature B — REQ-jellyfin-skip-intro (Intro Skipper plugin + chapter images)

### B1. Intro Skipper plugin — verified metadata

**Maintained fork:** `intro-skipper/intro-skipper` (GitHub org: `intro-skipper`)  
The original `ConfusedPolarBear/intro-skipper` is unmaintained. The active fork is
the canonical community continuation.

**Manifest URL for Jellyfin 10.11:** `https://intro-skipper.org/manifest.json`  
(Serves version-specific manifest based on the Jellyfin instance requesting it)

**Version-pinned manifest URL:**
`https://raw.githubusercontent.com/intro-skipper/manifest/refs/heads/main/10.11/manifest.json`

**Verified manifest values (live, 2026-05-27):**

| Field | Value |
|---|---|
| GUID | `c83d86bb-a1e0-4c35-a113-e2101cf4ee6b` |
| Name | `Intro Skipper` |
| Latest version (10.11 branch) | `1.10.11.19` |
| targetAbi | `10.11.8.0` (minimum Jellyfin 10.11.8) |
| Category | `MoviesAndShows` |

Jellyfin 10.11.8 is the version running in production — compatible. Confidence: HIGH.

**Requirements:**
- Jellyfin's own fork of ffmpeg must be installed, version 7.1.1-7 or newer
  (already present in `jellyfin/jellyfin` container images by default)
- No additional K8s changes needed

### B2. Jellyfin REST API for plugin repository + installation

**Add repo (existing arrconf reconciler pattern):**
The existing `_reconcile_server_config()` already manages `PluginRepositories` via the
`POST /System/Configuration` full-replace pattern with the 7-field allowlist. Adding the
Intro Skipper repo is a change to `arrconf.yml` `server_config.plugin_repositories[]`, not
a code change.

Current arrconf.yml allowlist already includes `PluginRepositories` as a managed field
(verified in `reconcilers/jellyfin.py` `SERVER_CONFIG_ALLOWLIST`).

**Add the repo entry to `arrconf.yml`:**
```yaml
jellyfin:
  main:
    server_config:
      plugin_repositories:
        - Name: "Intro Skipper"
          Url: "https://intro-skipper.org/manifest.json"
          Enabled: true
```

This flows through the existing `_server_config_equivalent()` set-by-URL comparison and the
existing `_reconcile_server_config()` POST. No new code needed for repo registration.

**Install a plugin (NEW — not currently in arrconf):**
Installing a plugin is NOT the same as activating one. The existing `_reconcile_plugins()`
handler only activates already-installed plugins via `POST /Plugins/{id}/{version}/Enable`
(D-07-PLUGINS-01 activation-only by design).

To install Intro Skipper declaratively, a new install step is needed:

```
POST /Packages/Installed/{packageName}
  Query: assemblyGuid=c83d86bb-a1e0-4c35-a113-e2101cf4ee6b&version=1.10.11.19&repositoryUrl=https://intro-skipper.org/manifest.json
  Body: (empty)
  Response: 204 No Content (success) or 404/400 (not found in repos)
  Side-effect: Jellyfin downloads and installs the plugin; server restart required
```

**IMPORTANT — restart requirement:** Plugin installation requires a Jellyfin server restart
to take effect. This cannot be automated safely from arrconf (would kill the arrconf pod's
own HTTP connection to Jellyfin). Recommended approach: install is best-effort + log a warning
if restart is pending (`Status: "NotSupported"` or `Status: "Superceded"` in `/Plugins` response
after install indicates restart needed). The operator restarts Jellyfin once manually.

**Plugin config (Intro Skipper settings):**
Intro Skipper exposes its settings via a plugin-specific endpoint (not `/System/Configuration`).
The plugin config is managed via Jellyfin's plugin-specific API:
- `GET /Plugins/{pluginId}/Configuration` — read current plugin config
- `POST /Plugins/{pluginId}/Configuration` — write plugin config (JSON body)

The Intro Skipper plugin config controls detection sensitivity, auto-skip vs button, segment
types to analyze (intro, credits, preview, recap). For initial setup, the defaults are
reasonable. Config management via arrconf is optional for v0.9.0 — can be added as a
follow-up.

Confidence: MEDIUM — install endpoint inferred from Jellyfin OpenAPI + community usage;
restart behavior documented in Jellyfin plugin system docs.

### B3. Media Segments API (Jellyfin 10.10+)

Media Segments is a server-side API introduced in Jellyfin 10.10 for typed time-spans
(intro, outro, commercial, preview, recap, unknown). Intro Skipper 1.10.x writes to this
API after fingerprint analysis. Clients that support Media Segments (Jellyfin web, Android app,
Swiftfin iOS/tvOS) display native "Skip" buttons without any client-side configuration.

**Kodi/JellyCon compatibility:** JellyCon on LibreELEC does NOT support Media Segments as of
2026 (confirmed by community sources). Skip functionality on the Kodi salon box is
best-effort/degraded as specified in the requirement.

The Media Segments API (`/MediaSegments/{itemId}`) is a Jellyfin server API — arrconf does not
need to call it directly. It is populated by the Intro Skipper plugin after scanning.

### B4. Chapter image extraction

Chapter image extraction is controlled by a field in `LibraryOptions` per virtual library
(`POST /Library/VirtualFolders/LibraryOptions` or via the library creation payload). The
`EnableChapterImageExtraction` boolean is part of `LibraryOptions`, NOT part of
`/System/Configuration`.

**Current arrconf reconciler scope:** `_reconcile_libraries()` creates VirtualFolders with
an empty `AddVirtualFolderDto {}` (no `LibraryOptions`). Enabling chapter image extraction
requires passing `LibraryOptions.EnableChapterImageExtraction: true` in the POST body when
creating a library, or a separate update via `POST /Library/VirtualFolders/LibraryOptions`.

For v0.9.0 scope: the simplest implementation is to add `EnableChapterImageExtraction: true`
as a field on `JellyfinLibraryOptions` in `arrconf.yml` and pass it through
`_create_library()`. Idempotence is maintained by comparing the existing LibraryOptions
`EnableChapterImageExtraction` value in `_add_missing_paths()` or a new `_update_library_options()`
helper.

Alternatively, chapter image extraction can be enabled globally via the scheduled task
`ExtractChapterImages` — but this is a Jellyfin UI action, not an API toggle.

Confidence: MEDIUM — `EnableChapterImageExtraction` field confirmed via Jellyfin TypeScript SDK
interface `ServerConfiguration`; the LibraryOptions pathway is inferred from Jellyfin source
code patterns.

### B5. No new Python/npm libraries needed for Feature B

The arrconf Jellyfin reconciler already uses `httpx` via `JellyfinClient`. Adding the
install step and optional plugin config management requires only:
- New methods on `JellyfinClient` (or `_reconcile_plugins()` extension)
- New pydantic fields in `JellyfinPluginsSection` for install vs activate distinction
- No new external dependencies

---

## Recommended Stack Additions Summary

### New Python packages (arrconf-ui only)

| Package | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| None | — | — | ruyaml, pydantic v2, fastapi already cover configarr-ui backend |

### New npm packages (arrconf-ui frontend only)

| Package | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| None | — | — | Svelte 5 + Vite + TypeScript covers the tab + TRaSH picker |

### New files to add

| File | Layer | Purpose |
|------|-------|---------|
| `tools/arrconf-ui/arrconf_ui/configarr_config.py` | Python backend | Pydantic model `ConfigarrRootConfig` — schema source for configarr form |
| `tools/arrconf-ui/arrconf_ui/configarr_app.py` | Python backend | 4 endpoints mirroring `app.py` for configarr.yml |
| `tools/arrconf-ui/scripts/fetch-trash-catalog.py` | Dev tool | Build-time script to generate `src/lib/trash-catalog.ts` from TRaSH-Guides repo |
| `tools/arrconf-ui/web/src/lib/trash-catalog.ts` | Frontend | Baked-in `name → trash_id` mapping (sonarr + radarr) |
| `tools/arrconf-ui/web/src/lib/recyclarr-catalog.ts` | Frontend | Baked-in Recyclarr template IDs (from `includes.json`) |
| `tools/arrconf-ui/web/src/lib/ConfigarrSection.svelte` | Frontend | Tab/form wrapper for configarr.yml (reuses AppSection + FieldInput) |

### arrconf changes (tools/arrconf)

| Change | File | Type |
|--------|------|------|
| Add `POST /Packages/Installed` install support | `reconcilers/jellyfin.py` | Feature extension of `_reconcile_plugins()` |
| Add `EnableChapterImageExtraction` to LibraryOptions | `reconcilers/jellyfin.py` | New field in `_create_library()` |
| Add repo URL + GUID to `arrconf.yml` + `config.py` pydantic models | `config.py` + `arrconf.yml` | Config schema + YAML |

---

## Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| configarr | 1.28.0 | Already deployed. `silenceRequiredCfGroupExclusionWarnings` available (v1.28). |
| Jellyfin | 10.11.8 | Deployed. Media Segments supported (10.10+). targetAbi match for plugin. |
| Intro Skipper | 1.10.11.19 | Latest for 10.11 branch (2026-05-02). GUID `c83d86bb-a1e0-4c35-a113-e2101cf4ee6b`. |
| ruyaml | 0.91.x | !env/!secret tags preserved verbatim by TaggedScalar — verified live. |
| TRaSH-Guides | master | Feb 2026 breaking change to CF group semantics — new behavior is the default. |

---

## Alternatives Considered

| Area | Recommended | Alternative | Why Not |
|------|-------------|-------------|---------|
| configarr schema | Hand-write pydantic model | Scrape configarr Zod types | configarr has no JSON Schema export; scraping TS types is fragile |
| TRaSH catalog | Baked-in TS constant (build-time) | Runtime fetch from GitHub | Adds network latency; offline LAN UI would fail |
| Plugin install | New arrconf `install` step + manual restart | Operator installs via Jellyfin UI | Declarative install is cleaner but requires restart warning |
| Chapter images | LibraryOptions per-library | Global ExtractChapterImages task | Per-library is more precise; task is fire-and-forget |

---

## What NOT to Add

| Avoid | Why |
|-------|-----|
| `python-json-schema-validator` or `jsonschema` lib | Pydantic v2 already validates; redundant |
| `httpx` for arrconf-ui backend to call TRaSH GitHub at runtime | Offline LAN use case breaks; baked catalog is sufficient |
| Recyclarr CLI as a sidecar | Out of scope; configarr already handles Recyclarr templates |
| Bazarr / Whisparr / Readarr | Out of scope (PROJECT.md explicit exclusion) |
| `configarr`-owned scope in arrconf pydantic (quality_profiles in arrconf reconcilers) | ADR-5 hard frontier: arrconf never writes quality_profiles/custom_formats |

---

## Sources

- `https://github.com/raydak-labs/configarr/blob/main/src/types/config.types.ts` — Full TypeScript type tree for `InputConfigSchema`, `InputConfigArrInstance`, `InputConfigQualityProfile`, `InputConfigIncludeItem` (HIGH confidence, verified live)
- `https://raw.githubusercontent.com/raydak-labs/configarr/main/docs/docs/configuration/_include/config-file-sample.yml` — Canonical annotated configarr.yml sample with all sections (HIGH confidence, verified live)
- `https://raw.githubusercontent.com/intro-skipper/manifest/refs/heads/main/10.11/manifest.json` — Intro Skipper GUID, version 1.10.11.19, targetAbi 10.11.8.0 (HIGH confidence, verified live)
- `https://github.com/TRaSH-Guides/Guides` — CF JSON structure: `trash_id`, `trash_scores`, `name`, `specifications[]` (HIGH confidence, live sample verified)
- `https://github.com/recyclarr/config-templates` — `includes.json` structure: 64 radarr + 34 sonarr template IDs (HIGH confidence, live)
- ruyaml 0.91 live test — TaggedScalar round-trips !env/!secret verbatim (HIGH confidence, tested locally)
- `https://typescript-sdk.jellyfin.org/interfaces/generated-client.ServerConfiguration.html` — `EnableChapterImageExtraction` in Jellyfin SDK (MEDIUM confidence, SDK confirmed field exists)
- `https://jellyfin.org/docs/general/server/metadata/media-segments/` — Media Segments API introduced 10.10 (HIGH confidence, official docs)
- `https://github.com/intro-skipper/intro-skipper/wiki/Installation` — Install instructions + Jellyfin 10.11.8 + ffmpeg 7.1.1-7 requirements (HIGH confidence, official wiki)

---

*Stack research for: arr-stack v0.9.0 — configarr-ui + Jellyfin intro skipper*
*Researched: 2026-05-27*
