# Phase 26: configarr-in-UI frontend - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

The arrconf-ui **Svelte frontend** gains the ability to select, view, and edit
`configarr.yml` alongside `arrconf.yml`, reusing the existing schema-driven
`FieldInput.svelte` dispatcher and the Phase 25 `/api/configarr/*` backend
endpoints.

Delivers (CFGUI-04):
- A config selector (tab bar) switching `arrconf.yml` ↔ `configarr.yml` with no page reload (SC#1)
- configarr form rendered via the existing schema-driven machinery: quality_profiles, custom_formats, scores per profile editable; `quality_definition` + `media_naming` (+ `api_key`) rendered **read-only** (SC#2)
- Edit a quality-profile score → diff preview shows only the changed field → save round-trips correctly through the Phase 25 backend (no tag corruption) (SC#3)

**Out of scope (other phases):**
- TRaSH custom-format name-picker → Phase 27 (CFGUI-05)
- Recyclarr reference dropdown → Phase 27 (CFGUI-06)

**Depends on Phase 25** (backend endpoints + JSON Schema with readOnly markers — shipped).
</domain>

<decisions>
## Implementation Decisions

### Config selector (SC#1)
- **D-01:** Add a **tab bar inside `HeaderBar.svelte`** with two tabs (`arrconf` / `configarr`), next to the existing file-path label. Switching is a client-side state swap — no page reload. HeaderBar already owns the file-path display, so the active tab also drives which path it shows. Tab bar (not dropdown/segmented) for discoverability and to scale cleanly if more configs are added later.

### readOnly field rendering (SC#2)
- **D-02:** `FieldInput.svelte` has **no `readOnly` handling today** — this is net-new. Render readOnly fields (`api_key`, `quality_definition`, `media_naming`) as the **normal widget but disabled (greyed, non-editable) + a small lock badge/icon** with a tooltip explaining the field is managed elsewhere (configarr/TRaSH — edit the file). Reuses existing widgets, keeps the value visible, and signals *why* it's locked. The `readOnly: true` marker comes from the Phase 25 JSON Schema (`api_key`, `media_naming`, `quality_definition`); `FieldInput` must read it from the effective schema node and thread it through nested-object + array-of-objects recursion.

### Two-config state model + unsaved-switch
- **D-03:** Parametrize the existing single-config flow by the **active config**: the active tab selects which API endpoints (`/api/config*` vs `/api/configarr/config*`), which schema, and which section list/renderers are used. Prefer evolving `App.svelte` over a forked component tree (KISS, one diff/save pipeline).
- **D-04:** On config switch **with unsaved edits**: show a **confirm dialog** ("Unsaved changes will be lost — switch anyway?"). The existing `diffCount` derived state already tracks dirty state — gate the switch on it. (Not: silent discard; not: dual in-memory buffers — rejected as over-engineering for a single-operator local tool.)

### configarr form layout (SC#2)
- **D-05:** **Reuse `AppSection.svelte` + `FieldInput.svelte`** driven by configarr's JSON Schema. `quality_profiles[]` / `custom_formats[]` render as repeatable nested forms automatically via the existing array-of-objects machinery; scores are leaf fields within each profile. KISS, consistent with arrconf, minimal new code. The only configarr-specific deltas: (a) readOnly support (D-02), (b) **skip `CategoriesEditor`** — configarr has no `categories` concept, (c) configarr's top-level keys (`trashGuideUrl`, `recyclarrConfigUrl`, `customFormatDefinitions`, `sonarr`, `radarr`) drive the section list instead of arrconf's `APP_SECTIONS`.

### Claude's Discretion
- Exact `api.ts` function names + how the active-config selector threads endpoints (follow existing `getConfig`/`getSchema`/`postDiff`/`putConfig` shape).
- Tab-bar styling specifics (use existing CSS tokens / dark theme / IBM Plex).
- How the configarr section list is derived from its schema `properties` (vs arrconf's hardcoded `APP_SECTIONS` in `constants.ts`) — planner's call.
- i18n keys for the new tab labels, lock tooltip, and unsaved-switch dialog (FR, follow `web/src/i18n/fr.ts`).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — CFGUI-04 (Phase 26); CFGUI-05/06 are Phase 27 (out of scope)
- `.planning/ROADMAP.md` §"Phase 26: configarr-in-UI frontend" — Goal + 3 Success Criteria
- `.planning/PROJECT.md` `<decisions>` — ADR-5 (UI edits the file; configarr applies; no *arr API URL in arrconf-ui source)

### Phase 25 backend this frontend consumes
- `.planning/phases/25-configarr-in-ui-backend/25-CONTEXT.md` — backend decisions (D-04 api_key readOnly; D-08 pydantic gate)
- `tools/arrconf-ui/arrconf_ui/app.py` — `/api/configarr/*` endpoints (GET/PUT config, GET schema, POST diff) the frontend calls
- `schemas/configarr-schema.json` — the JSON Schema the form renders from; `readOnly: true` on `api_key`, `media_naming`, `quality_definition`

### Existing frontend to extend / mirror
- `tools/arrconf-ui/web/src/App.svelte` — top-level orchestration (currently hardwired to arrconf: single config, `APP_SECTIONS`, `CategoriesEditor`); the file to parametrize by active config
- `tools/arrconf-ui/web/src/lib/FieldInput.svelte` — D-13 schema-driven dispatcher; **needs readOnly support added** (no `readOnly` handling today)
- `tools/arrconf-ui/web/src/lib/AppSection.svelte` — section renderer to reuse for configarr sections
- `tools/arrconf-ui/web/src/lib/HeaderBar.svelte` — where the config-selector tab bar lands; owns file-path display
- `tools/arrconf-ui/web/src/lib/DiffPanel.svelte` — diff preview before save (SC#3)
- `tools/arrconf-ui/web/src/api.ts` — add configarr endpoint calls mirroring existing `getConfig`/`getSchema`/`postDiff`/`putConfig`
- `tools/arrconf-ui/web/src/constants.ts` (`APP_SECTIONS`), `types.ts`, `schema.ts` (`effectiveNode`), `i18n/fr.ts` — supporting modules
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FieldInput.svelte`: schema-driven widget dispatcher (enum→select, integer→number, array-of-objects→repeatable nested form). Reuse for the whole configarr form; extend with readOnly rendering.
- `AppSection.svelte` + `schema.ts effectiveNode()` ($ref/anyOf resolution): drive configarr sections from its schema.
- `DiffPanel.svelte` + `postDiff`/`putConfig` flow in `App.svelte`: the existing preview→confirm→save pipeline works as-is once parametrized by active config.
- `diffCount` derived state in `App.svelte`: already tracks dirty state — reuse for the unsaved-switch confirm gate (D-04).

### Established Patterns
- Svelte 5 runes (`$state`/`$derived`); dark theme + IBM Plex via CSS tokens; FR i18n in `web/src/i18n/fr.ts`; D-13 "never hand-code per-field UI — everything flows through FieldInput".

### Integration Points
- `App.svelte` `onMount` currently `Promise.all([getSchema(), getConfig()])` for arrconf only → must become active-config-aware.
- configarr has **no `categories`** → the `CategoriesEditor` block is arrconf-only; configarr sections come from configarr's schema `properties`, not `APP_SECTIONS`.
- ADR-5 / SC#3 (Phase 25): the frontend only reads/writes the file via the backend; it MUST NOT construct or call any *arr API URL. The Phase 25 D-09 guard + tag-literal handling protect tag integrity on save.
</code_context>

<specifics>
## Specific Ideas

- User picked all recommended options: tab bar in HeaderBar, disabled-input + lock-badge for readOnly, warn-and-confirm on unsaved switch, and maximal reuse of the existing schema-driven rendering. Bias toward consistency with the existing arrconf UI and minimal net-new components — the only genuinely new piece is readOnly support in `FieldInput`.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 26 frontend scope. (TRaSH name-picker = CFGUI-05 / Phase 27; Recyclarr reference dropdown = CFGUI-06 / Phase 27, already roadmapped.)
</deferred>

---

*Phase: 26-configarr-in-ui-frontend*
*Context gathered: 2026-05-30*
