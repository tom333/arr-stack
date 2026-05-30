# Phase 27: TRaSH CF picker + Recyclarr reference + QP picker - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

The arrconf-ui **Svelte frontend** (Phase 26 configarr form) gains three
metadata-driven helpers for editing `configarr.yml`, all backed by a
**build-time-baked catalog** (no runtime GitHub calls):

1. **TRaSH custom-format picker** (CFGUI-05) — add/remove CFs by human-readable
   name; the `trash_id` is inserted into `custom_formats[].trash_ids`. No manual
   hex entry.
2. **TRaSH quality-profile picker** (CFGUI-08, **scope expansion 2026-05-30**) —
   apply a TRaSH quality profile by name; **append-only** into
   `quality_profiles[]`, never modifying the 3 hand-rolled profiles.
3. **Recyclarr template reference** (CFGUI-06) — read-only informational
   dropdown of template names + descriptions. **NEVER** inserts `include:`.

**Scope expansion note:** CFGUI-08 (QP picker) was added during this
discuss-phase at the operator's explicit request. It is **not** an ADR-5
violation — configarr legitimately owns `quality_profiles`; the UI edits the
**file** and configarr applies. Phase 26 already made QP scores editable; this
adds an add-as-new template helper. ROADMAP Phase 27 + REQUIREMENTS updated
(CFGUI-08, SC#5) in the same discuss-phase commit.

**Out of scope (deferred / other phases):**
- Recyclarr `include:` **insertion** → CFGUI-F1 / v1.x (merge-hazard vs the 6 hand-rolled French CFs)
- Live catalog refresh + trash_id drift detection → CFGUI-F2 / v1.x
- Deep quality_definition / media_naming editing → CFGUI-F3 / v1.x (read-only since Phase 26)
- QP picker **overwrite/merge** of existing profiles → explicitly rejected (add-as-new only, D-09)

**Depends on Phase 26** (configarr form + `FieldInput.svelte` + config-selector tab — shipped).
**Touches only `tools/arrconf-ui/**`** → NO arrconf image co-bump, NO chart auto-tag (STATE roadmap decision, v0.9.0).
</domain>

<decisions>
## Implementation Decisions

### TRaSH CF picker — ID classification (SC#4)
- **D-01:** Resolve every existing `custom_formats[].trash_ids` entry against
  **BOTH** sources: the baked TRaSH catalog AND the file's own
  `customFormatDefinitions[].trash_id`. An ID found in either is "known".
- **D-02:** A `trash_id` that resolves only against local
  `customFormatDefinitions` (e.g. `fr-vff`, `fr-vfi`, `fr-vfq`, `fr-multi`,
  `fr-vostfr`, `fr-mhd`, `fr-x265-hd`) renders with its name + a **"custom"
  badge** — NOT a warning. The 6+ hand-rolled French CFs are first-class, no
  false alarms.
- **D-03:** A `trash_id` in **neither** the catalog nor local definitions
  renders with a **warning indicator** (icon + tooltip "unknown trash_id — not
  in catalog or local definitions") and is **preserved verbatim** on save.
  Never silently dropped, never blocks save, no auto-remove. Protects against
  catalog staleness. (Satisfies SC#4 literally.)

### TRaSH CF picker — insertion semantics (CFGUI-05)
- **D-04:** Each picked CF is written as its **own** `custom_formats[]` entry:
  `{ trash_ids: [<id>], assign_scores_to: [<all quality_profiles in that app>] }`
  with no explicit `score` (TRaSH default applies implicitly). Mirrors the
  existing fr-* grouping shape. Operator tunes scores afterward via the Phase 26
  form.
- **D-05:** Picker is a **searchable multi-select** — tick several CFs, each
  becomes its own entry on confirm. **Removal** = a remove control on each
  existing `custom_formats[]` entry/chip. Symmetric add/remove (CFGUI-05 "add or
  remove by name").
- **D-06:** Picker is **app-context-filtered**: when editing the `sonarr`
  section it offers sonarr CFs; `radarr` section offers radarr CFs (TRaSH ships
  distinct CF sets per app).

### Baked catalog scope + pinning (SC#2)
- **D-07:** Catalog metadata per CF: `{ name, trash_id, default_score, app:
  sonarr|radarr }`, split by app. Quality-profile catalog baked too (for
  CFGUI-08), per app. Dev-time fetch script (`tools/scripts/fetch-trash-metadata.sh`
  per research) pulls + commits as static assets under
  `tools/arrconf-ui/web/src/assets/trash-metadata/`. No quality_definition/
  media_naming catalogs (read-only, out of scope).
- **D-08:** Pin to **latest stable HEAD** of TRaSH-Guides + Recyclarr
  config-templates at build time (operator choice over the configarr-v7.4.0-fork
  baseline). Record the resolved SHAs in a manifest committed with the assets.
  **⚠ Researcher/planner MUST verify:** configarr v1.28.0 still *resolves* the
  baked IDs at apply time — the baked catalog is a **name→trash_id lookup only**;
  configarr does the real resolution in-cluster, so a HEAD-only ID that v7.4.0
  can't resolve would surface as a **configarr apply error** (not a UI error).
  Document this risk + the chosen mitigation (e.g. CI cross-check, or doc note).

### TRaSH QP picker (CFGUI-08 — scope expansion)
- **D-09:** Picker **appends only** — a new `quality_profiles[]` entry seeded
  from the TRaSH template. The 3 hand-rolled profiles (MULTi.VF / Anime /
  Family) are **never modified or reordered**. No overwrite, no merge.
- **D-10:** **Name collision** (picked template name already exists in
  `quality_profiles[]`) → **block + warn**, require the operator to rename
  before insert. Protects the French tuning from silent clobber.
- **D-11:** QP picker is app-context-filtered (sonarr vs radarr QP catalogs),
  same as the CF picker (D-06).

### Recyclarr reference dropdown (CFGUI-06 — read-only)
- **D-12:** Lives **inside each app's section** (sonarr / radarr) in the
  configarr form, filtered to that app's templates (~34 sonarr / ~64 radarr per
  research). Selecting a template name shows its **name + description** in a
  read-only panel. Clearly labelled "Reference only — no `include:` inserted".
- **D-13:** The only convenience action is a **"copy template name"** button
  (clipboard). **No** config mutation of any kind — never writes `include:` or
  any other key. (CFGUI-06 / SC#3 boundary.)

### Claude's Discretion
- Exact component names (research suggests `TrashPicker.svelte`,
  `RecyclarrTemplatePicker.svelte`; QP picker component name = planner's call).
- Read-only metadata endpoint shapes (research suggests
  `GET /api/trash/custom-formats?app=…`, `GET /api/trash/quality-profiles?app=…`)
  — follow existing arrconf-ui endpoint patterns; MUST serve from baked assets,
  no GitHub HTTP.
- Picker search/styling, default-score display formatting, chip/badge visuals
  (use existing CSS tokens / dark theme / IBM Plex).
- Diff-preview grouping for newly-inserted CF/QP entries (reuse Phase 25
  configarr structured diff).
- i18n keys (FR) for picker labels, "custom"/"unknown" badges, collision
  warning, Recyclarr reference panel — follow `web/src/i18n/fr.ts`.
- Exact pinned SHAs + manifest format (planner, per D-08 verification).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — CFGUI-05, CFGUI-06, **CFGUI-08** (Phase 27); v1.x deferrals CFGUI-F1/F2/F3
- `.planning/ROADMAP.md` §"Phase 27: TRaSH CF picker + Recyclarr reference + QP picker" — Goal + 5 Success Criteria
- `.planning/PROJECT.md` `<decisions>` — **ADR-5** (UI edits the file; configarr applies; configarr owns quality_profiles/custom_formats; NO *arr API URL in arrconf-ui source)

### Research (consumed at requirements time — re-read for Phase 27)
- `.planning/research/SUMMARY.md` — Tension 1 (TRaSH/Recyclarr picker scope split), Phase 27 file map, Research-flag: identify Recyclarr config-templates v7.4.0 fork-point SHA
- `.planning/research/ARCHITECTURE.md` — Phase 27 component + endpoint layout
- `.planning/research/FEATURES.md` — CF picker shows name + default score; Recyclarr include = P3 anti-feature (deferred)
- `.planning/research/PITFALLS.md` — A5 (catalog staleness → pin snapshot), A6 (Recyclarr/configarr compat), anti-pattern: no runtime GitHub calls from FastAPI

### Phase 25/26 this phase builds on
- `.planning/phases/26-configarr-in-ui-frontend/26-CONTEXT.md` — configarr form, `FieldInput.svelte` dispatcher, readOnly rendering, config-selector tab
- `.planning/phases/25-configarr-in-ui-backend/25-CONTEXT.md` — `ConfigarrRootConfig` model, configarr endpoints, structured diff (D-05), `!env`/`!secret` tag-preservation
- `schemas/configarr-schema.json` — JSON Schema the form renders from
- `charts/arr-stack/files/configarr.yml` — the real file: `customFormatDefinitions` (7 hand-rolled CFs incl. fr-vff/fr-vfi/fr-vfq/fr-multi/fr-vostfr/fr-mhd/fr-x265-hd at lines 24-132); `custom_formats[].trash_ids` referencing them (sonarr L271, radarr L432); `quality_profiles[]` MULTi.VF/Anime/Family (sonarr L193+); `trashGuideUrl` L18, `recyclarrConfigUrl` L19

### Existing arrconf-ui code to extend / mirror
- `tools/arrconf-ui/web/src/lib/FieldInput.svelte` — schema-driven dispatcher (the picker components plug into / replace specific array-of-objects fields)
- `tools/arrconf-ui/web/src/lib/AppSection.svelte` — per-app section renderer (Recyclarr dropdown + QP picker land here, D-12)
- `tools/arrconf-ui/web/src/lib/DiffPanel.svelte` — diff preview before save
- `tools/arrconf-ui/web/src/api.ts` — add the read-only TRaSH metadata endpoint calls
- `tools/arrconf-ui/arrconf_ui/app.py` — register the 2 read-only metadata endpoints (serve baked assets; NO GitHub HTTP, NO *arr URL)
- `tools/arrconf-ui/arrconf_ui/configarr_diff.py` — configarr structured diff to extend for new CF/QP entries
- `tools/scripts/fetch-trash-metadata.sh` — NEW dev-time fetch script (research-named); commits assets + SHA manifest

### External (research targets — pin SHAs)
- `https://github.com/TRaSH-Guides/Guides` — CF + QP JSON structure (`docs/json/`); note Feb-2026 CF-group-semantics breaking change
- `https://github.com/recyclarr/config-templates` — `includes.json` (64 radarr + 34 sonarr template IDs); identify v7.4.0-compatible fork-point SHA
- `https://configarr.de/docs/intro/` — confirm v1.28.0 trash_id resolution behavior at apply (D-08 risk)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FieldInput.svelte` / `AppSection.svelte`: the configarr form is already
  schema-driven (Phase 26). The pickers replace/augment specific fields
  (`custom_formats[].trash_ids`, `quality_profiles[]`) rather than rebuilding
  the form.
- `configarr_diff.py` + `DiffPanel.svelte`: the preview→confirm→save pipeline
  works as-is; new CF/QP entries flow through it.
- `io.py` ruyaml `YAML(typ="rt")` round-trip: preserves comments/order/tags.
  **Constraint (research):** never introduce a second YAML instance or shallow
  dict-replace a tagged subtree (`sonarr.main`, `radarr.main`) — would drop
  `!env`/`!secret` tags.

### Established Patterns
- Svelte 5 runes (`$state`/`$derived`); dark theme + IBM Plex CSS tokens; FR
  i18n in `web/src/i18n/fr.ts`; D-13 (Phase 26): everything flows through the
  schema-driven dispatcher — pickers are the justified exception (specialized
  metadata UX).
- Build-time assets: baked TRaSH/Recyclarr catalogs are TypeScript constants /
  static JSON generated by the fetch script — a few KB, no new npm/Python dep
  (research STACK.md).

### Integration Points
- New read-only metadata endpoints in `app.py` serving baked assets — MUST NOT
  call GitHub at runtime (SC#2) and MUST NOT construct any *arr API URL (ADR-5).
- Pickers write into the in-memory configarr config object that the existing
  PUT path persists via `configarr_io.py` — same tag-safe write path as Phase 25.
- App-context filtering: pickers read the active section (sonarr/radarr) to
  filter the catalog (D-06, D-11).

### ADR-5 boundary self-check (MANDATORY in implementation)
- arrconf-ui reads/writes the `configarr.yml` file only. NO Sonarr/Radarr/
  Prowlarr URL anywhere in arrconf-ui source. configarr (external, in-cluster)
  owns all *arr API contact and all trash_id resolution.
</code_context>

<specifics>
## Specific Ideas

- Operator deliberately **expanded scope** to include a full TRaSH
  quality-profile picker (CFGUI-08) after being shown the tradeoff — wants it in
  Phase 27, not a separate phase, but constrained to **add-as-new** so the
  hand-rolled MULTi.VF/Anime/Family profiles are untouchable.
- Operator chose **latest stable HEAD** pinning over the configarr-v7.4.0
  compatibility baseline despite the stated divergence risk — accepts that a
  HEAD-only ID surfaces as a configarr apply error, not a UI error. Planner must
  document the mitigation.
- Strong bias toward **safety on existing config**: known-custom badge (not
  warning) for the French CFs, verbatim preservation of unknown IDs, append-only
  QP insertion, collision-blocking. Consistent with the Phase 25/26 "protect the
  hand-rolled French setup" theme.
- Recyclarr stays **strictly reference** — copy-name button is the only action;
  no `include:` ever (CFGUI-06 / Tension 1 honored).
</specifics>

<deferred>
## Deferred Ideas

- **Recyclarr `include:` insertion** (CFGUI-F1 / v1.x) — merge-order hazard vs
  the 6 hand-rolled French CFs; configarr pinned to Recyclarr v7.4.0 templates.
  Reference-only in Phase 27.
- **Live catalog refresh + trash_id drift detection** (CFGUI-F2 / v1.x) — baked
  snapshot only for now.
- **QP picker overwrite/merge mode** — explicitly rejected for Phase 27
  (add-as-new only, D-09); could be revisited if the operator later wants
  TRaSH-sync of existing profiles, but that re-opens the clobber hazard.

None of these block Phase 27.
</deferred>

---

*Phase: 27-trash-cf-picker-recyclarr-reference*
*Context gathered: 2026-05-30*
