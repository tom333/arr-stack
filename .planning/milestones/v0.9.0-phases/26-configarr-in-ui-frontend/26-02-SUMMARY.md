---
phase: 26-configarr-in-ui-frontend
plan: "02"
subsystem: arrconf-ui-frontend
tags: [frontend, svelte, typescript, i18n, config-selector, two-config, checkpoint]
dependency_graph:
  requires: [configarr-api-functions, readonly-schema-field, config-file-paths, i18n-configarr-strings, readonly-widget-rendering]
  provides: [config-tab-selector, two-config-orchestration, unsaved-switch-confirm, configarr-section-render]
  affects: [27]
tech_stack:
  added: []
  patterns: [active-config-state, parametrized-load-save-pipeline, additionalProperties-section-filter, config-scoped-section-docs]
key_files:
  created: []
  modified:
    - tools/arrconf-ui/web/src/lib/HeaderBar.svelte
    - tools/arrconf-ui/web/src/App.svelte
    - tools/arrconf-ui/web/src/i18n/fr.ts
decisions:
  - "Config section list for configarr derived from schema.properties keys filtered on additionalProperties (sonarr + radarr maps) — no CategoriesEditor on the configarr tab"
  - "Unsaved-switch confirm gated on diffCount > 0 (D-04); inline confirm dialog, not browser confirm()"
  - "configarr SectionDocs use config-scoped keys (configarr / configarr.sonarr / configarr.radarr) — the plain sonarr/radarr keys describe arrconf's reconciler and would be wrong context on the configarr tab (checkpoint feedback)"
metrics:
  duration: "5m + checkpoint enhancement"
  completed_date: "2026-05-30"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 3
---

# Phase 26 Plan 02: Config Selector + Two-Config Orchestration Summary

Wires the config selector and two-config orchestration into the UI: a two-tab selector in `HeaderBar.svelte` plus an `App.svelte` parametrized by the active config so one load → render → diff → save pipeline drives both `arrconf.yml` and `configarr.yml`. Adds the unsaved-switch confirm gate and configarr-specific explanatory docs. Satisfies all three Phase 26 success criteria (SC#1 selector, SC#2 read-only form render, SC#3 round-trip).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add config-selector tab bar to HeaderBar.svelte | bdb9afe | lib/HeaderBar.svelte |
| 2 | Parametrize App.svelte by active config (load, save, sections, unsaved-switch confirm) | 2c94848 | App.svelte |
| 3 | Verify the three success criteria in the running UI (human checkpoint) | — | (human-verify; approved) |
| +  | Checkpoint enhancement: configarr section docs + per-field descriptions | 4914948 | i18n/fr.ts, App.svelte |

## What Was Built

**Task 1 — HeaderBar tab bar:**
- Optional `activeConfig: ActiveConfig` + `onTabChange: (cfg) => void` props.
- Two-button nav tab bar rendered inside `.title-wrap` when `onTabChange` is provided (backward-compatible: HeaderBar still works without the selector).
- CSS uses design tokens only (no hex literals).

**Task 2 — App.svelte parametrization:**
- `activeConfig` state rune, default `'arrconf'`.
- `loadForConfig(cfg)` dispatches to `getSchema`/`getConfig` or `getConfigarrSchema`/`getConfigarrConfig`.
- `openDiffPanel` + `confirmSave` dispatch by `activeConfig` to the matching diff/put API functions.
- `requestTabChange` gates on `diffCount > 0` → inline confirm dialog with `UNSAVED_SWITCH_MESSAGE` ("Annuler"/"Changer"); `doSwitch` performs the load (D-04).
- configarr section list = `Object.keys(schema.properties)` filtered on `additionalProperties != null` → sonarr + radarr instance maps only (scalar keys `trashGuideUrl`/`recyclarrConfigUrl`/`customFormatDefinitions` excluded).
- `CategoriesEditor` rendered only when `activeConfig === 'arrconf'`.

**Task 3 + checkpoint enhancement — explanatory docs:**
- configarr intro `SectionDoc` (open by default) at the top of the configarr tab.
- config-scoped section docs `configarr.sonarr` / `configarr.radarr` (the plain `sonarr`/`radarr` keys describe arrconf's reconciler — wrong context).
- per-field `FIELD_DESCRIPTIONS` for `ArrInstance`, `QualityProfile`, `QualityGroup`, `CustomFormat`, `AssignScoresTo` (incl. why each readOnly field is locked) + French `FIELD_LABELS` for configarr keys.

## Verification

- `npm run check`: 0 errors, 0 warnings (92 files)
- `npm run typecheck`: exit 0
- `npm run build`: exit 0 (96.86 kB JS, 18.88 kB CSS)
- Human checkpoint: SC#1 (no-reload tab switch), SC#2 (configarr form render with quality_definition/media_naming/api_key read-only), SC#3 (score round-trip through Phase 25 backend, diff shows only the changed field, `!env`/`!secret` tags + comments + key order preserved), D-04 (unsaved-switch confirm) — all approved by operator.

## Deviations from Plan

- Plan stopped at the human-verify checkpoint as designed (`autonomous: false`). During the checkpoint the operator requested explanatory text on the configarr tab; implemented as commit `4914948` (configarr-scoped section docs + per-field descriptions) before approval. No scope change to the three success criteria.

## Threat Surface Scan

No new network endpoints. App.svelte calls only the existing `/api/*` and `/api/configarr/*` functions from 26-01 (same LAN-trusted operator-browser → arrconf-ui-backend boundary). HeaderBar and the i18n additions introduce no fetch/URL construction. ADR-5 preserved: no *arr API URL appears in the frontend.

## Known Stubs

None. Both configs drive the full load → render → diff → save pipeline. CFGUI-04 success criteria met.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| HeaderBar.svelte modified | FOUND |
| App.svelte modified | FOUND |
| i18n/fr.ts modified | FOUND |
| SUMMARY.md exists | FOUND |
| Commit bdb9afe (Task 1) | FOUND |
| Commit 2c94848 (Task 2) | FOUND |
| Commit 4914948 (checkpoint docs) | FOUND |
| Human checkpoint approved | YES |
