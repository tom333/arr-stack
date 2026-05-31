# Phase 25: configarr-in-UI backend - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

The arrconf-ui **backend** gains read / validate / diff / write support for
`configarr.yml`, symmetric to the existing `arrconf.yml` endpoints, with the
same safety guarantees plus zero risk of secret leakage via `!env` / `!secret`
tag drop.

Delivers (CFGUI-01, CFGUI-02, CFGUI-03, CFGUI-07):
- Task-zero `!env`/`!secret` round-trip anti-leak test (ships BEFORE any write-path code)
- Hand-written `ConfigarrRootConfig` pydantic model + generated JSON Schema (lives in `tools/arrconf-ui/` ONLY)
- 4 endpoints: `GET /api/configarr/config`, `PUT /api/configarr/config`, `GET /api/configarr/schema`, `POST /api/configarr/diff`
- CI gate validating the written `configarr.yml` via configarr's own native validator

**Out of scope (other phases):**
- Frontend config selector + form rendering → Phase 26 (CFGUI-04)
- TRaSH CF name-picker + Recyclarr reference dropdown → Phase 27 (CFGUI-05, CFGUI-06)

**Independent of Phase 24** — can run in parallel (no code dependency between the
arrconf Python reconciler and the arrconf-ui pydantic model).
</domain>

<decisions>
## Implementation Decisions

### Pydantic model strictness (field policy)
- **D-01:** `ConfigarrRootConfig` uses `extra="forbid"` — mirrors arrconf's `RootConfig` (`tools/arrconf/arrconf/config.py:45`). Unknown top-level keys are rejected, not silently passed through.
- **D-02:** Because `forbid` rejects any unmodeled key, **every** top-level key of `configarr.yml` must be modeled — including the read-only sections. The editable subset (`quality_profiles`, `custom_formats`, `customFormatDefinitions`, `language`) is fully typed AND editable; `quality_definition` + `media_naming` are fully typed but marked `readOnly: true` in the JSON Schema. Also model: `trashGuideUrl`, `recyclarrConfigUrl`, and any other present top-level keys.
- **D-03:** Read-only sections are **fully typed** (not opaque `dict[str,Any]`). Accepted tradeoff: maximum validation strength at the cost of model/schema churn whenever configarr/TRaSH add fields. Research must map the complete `quality_definition` + `media_naming` shape (from configarr docs/source) so the hand-written model is exhaustive.
- **D-04:** `api_key` fields hold a `!env`/`!secret` tag reference (e.g. `!env SONARR_API_KEY`), not a literal secret. Treat as an opaque string value; the tag reference itself is safe to surface (it is a variable name, not a secret). `api_key` marked `readOnly: true` in schema per CFGUI-02 / SC#3.

### Diff endpoint (`POST /api/configarr/diff`)
- **D-05:** Build a **configarr-specific structured diff** (per-quality-profile, per-custom-format semantic grouping) — do NOT reuse `tools/arrconf-ui/arrconf_ui/diff.py`, which is hard-coded to arrconf's shape (`categories`, `APP_SECTIONS` = sonarr/radarr/prowlarr/qbittorrent/seerr/jellyfin) and cannot diff configarr's shape.
- **D-06:** The diff MUST operate on the round-trip data so `!env`/`!secret` tags appear as literals (e.g. `!env SONARR_API_KEY`) in the output, never a resolved value (SC#4). The structured diff must hand-preserve these tag literals — do not pass values through a resolver or `model_dump` path that would drop the tag.

### CI validation gate (CFGUI-07)
- **D-07 (DOWNGRADED 2026-05-29 — see D-08 resolution):** Original intent was **native configarr validation** as the authoritative gate. Research (25-RESEARCH.md `## BLOCKER / ESCALATION`) proved configarr v1.28.0 has NO offline validate mode (`DRY_RUN` still hits live *arr; startup "validation" is a TypeScript cast, not a runtime schema check). D-07 cannot be satisfied offline. **Resolved: pydantic IS the CI authority for Phase 25.**
- **D-08 (RESOLVED 2026-05-29 — user escalation):** No offline configarr validation mode exists. User chose **Option C: pydantic-only CI gate**. The CI gate (CFGUI-07) is `ConfigarrRootConfig.model_validate` run against the written `configarr.yml` (e.g. round-trip → validate in `tests.yml` arrconf-ui-backend job). **Do NOT** spin up ephemeral *arr containers; **do NOT** invoke configarr in CI. The pydantic `extra="forbid"` model is the authoritative structural gate. This is an explicit, user-acknowledged downgrade of D-07.

### Anti-leak runtime guard (PUT write path)
- **D-09:** Beyond the task-zero round-trip test, add a **runtime guard** on the `PUT /api/configarr/config` write path: after the atomic write, re-read the file and assert every `!env`/`!secret` tag is byte-present; if any tag was lost, **roll back the write and return 500**. Defense-in-depth against future ruyaml/model regressions.
- **D-10:** ruyaml round-trip (`YAML(typ="rt")` in `tools/arrconf-ui/arrconf_ui/io.py`) **already preserves `!env`/`!secret` verbatim today** (verified during discussion against the real `configarr.yml`). The existing `io.py` read/write helpers can be reused as-is for the IO layer; the task-zero test is expected to pass against current code, and the runtime guard (D-09) protects against drift.

### Claude's Discretion
- Endpoint wiring details, error-response shapes, schema-generation mechanics — follow the existing arrconf endpoint patterns in `tools/arrconf-ui/arrconf_ui/app.py`.
- Whether `ConfigarrRootConfig` is one file or split per-section — planner's call (KISS).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — CFGUI-01, CFGUI-02, CFGUI-03, CFGUI-07 (Phase 25 requirements; CFGUI-04/05/06 are later phases)
- `.planning/ROADMAP.md` §"Phase 25: configarr-in-UI backend" — Goal + 5 Success Criteria
- `.planning/PROJECT.md` `<decisions>` — **ADR-5** (configarr frontier): `ConfigarrRootConfig` lives in `tools/arrconf-ui/` ONLY, never `tools/arrconf/`; NO `*arr` API URL anywhere in arrconf-ui source (SC#3 boundary assertion)

### Data the backend operates on
- `charts/arr-stack/files/configarr.yml` — the real file to round-trip; contains `!env SONARR_API_KEY` (line 144), `!env RADARR_API_KEY` (line 309); top-level keys: `trashGuideUrl`, `recyclarrConfigUrl`, `customFormatDefinitions`, `sonarr`, `radarr` (each with `quality_profiles`, `custom_formats`, etc.)

### Existing arrconf-ui patterns to mirror / reuse
- `tools/arrconf-ui/arrconf_ui/io.py` — ruyaml `YAML(typ="rt")` round-trip read + atomic write (`os.replace`); **reuse as-is** (D-10), preserves tags verbatim
- `tools/arrconf-ui/arrconf_ui/app.py` — existing arrconf endpoints (GET/PUT `/api/config`, GET `/api/schema`, POST `/api/diff`); imports `RootConfig` from `arrconf.config` — the configarr endpoints must be **symmetric** but import the NEW local `ConfigarrRootConfig` (CFGUI-03)
- `tools/arrconf-ui/arrconf_ui/diff.py` — arrconf-shape diff; **reference for structure, do NOT reuse** for configarr (D-05)
- `tools/arrconf/arrconf/config.py:45` — `model_config = ConfigDict(extra="forbid")` pattern to mirror (D-01)

### External (research targets)
- Configarr docs — https://configarr.de/docs/intro/ — confirm v1.28.0 validate/dry-run modes (D-08), and the full `quality_definition` + `media_naming` schema shape (D-03)
- TRaSH-Guides — https://trash-guides.info/ — source of truth for custom-format / quality-definition field shapes
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `arrconf_ui/io.py` (`read_yaml`, `write_yaml_atomic`, `dump_yaml_to_str`): tag-preserving ruyaml IO — reuse directly for the configarr IO layer.
- `arrconf_ui/app.py` arrconf endpoints: the GET/PUT/schema/diff shape to clone for `/api/configarr/*`.
- `arrconf/config.py` `extra="forbid"` ConfigDict: the strictness pattern for `ConfigarrRootConfig`.

### Established Patterns
- Atomic write = temp file in same dir + `os.fsync` + `os.replace` (POSIX-atomic). Keep for the configarr PUT path; layer the D-09 re-read/rollback guard on top.
- Schema generation: arrconf ships `schemas/arrconf-schema.json` via `arrconf schema-gen`; configarr schema is generated from the new local pydantic model (mechanism = planner's call; do NOT touch arrconf's schema pipeline).
- FieldInput.svelte (frontend) renders fields from JSON Schema `$defs` + `$ref` — the Phase 25 schema's `readOnly: true` markers are what Phase 26's form will honor. Backend produces the markers; frontend consumes them.

### Integration Points
- New `ConfigarrRootConfig` model file under `tools/arrconf-ui/arrconf_ui/` (e.g. `configarr_config.py`) — NEVER under `tools/arrconf/` (ADR-5).
- New configarr endpoints registered in `arrconf_ui/app.py` alongside arrconf endpoints.
- Locator (`arrconf_ui/locator.py`) currently resolves `arrconf.yml` + schema paths; needs a configarr.yml path resolver.
- CI: a new gate in `.github/workflows/tests.yml` (or equivalent) invoking configarr's native validator against the written file.

### ADR-5 boundary self-check (MANDATORY in implementation)
- SC#3 asserts NO `*arr` API URL appears anywhere in arrconf-ui source. The configarr endpoints read/write a file; they MUST NOT construct or call any Sonarr/Radarr/Prowlarr URL. configarr (the external tool) owns all *arr API contact, in-cluster, not in arrconf-ui.
</code_context>

<specifics>
## Specific Ideas

- User picked the strict / thorough option on every gray area: `extra="forbid"` + fully-typed read-only sections, configarr-specific structured diff, authoritative native configarr validation (escalate rather than weaken), and a re-read/rollback anti-leak runtime guard. Bias the whole phase toward maximum safety/validation strength over minimal code.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 25 backend scope. (Frontend selector/form = Phase 26; TRaSH name-picker + Recyclarr reference = Phase 27, already roadmapped.)
</deferred>

---

*Phase: 25-configarr-in-ui-backend*
*Context gathered: 2026-05-29*
