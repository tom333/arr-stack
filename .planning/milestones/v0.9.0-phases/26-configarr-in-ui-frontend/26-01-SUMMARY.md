---
phase: 26-configarr-in-ui-frontend
plan: "01"
subsystem: arrconf-ui-frontend
tags: [frontend, svelte, typescript, i18n, schema-driven, readonly]
dependency_graph:
  requires: []
  provides: [configarr-api-functions, readonly-schema-field, config-file-paths, i18n-configarr-strings, readonly-widget-rendering]
  affects: [26-02, 26-03]
tech_stack:
  added: []
  patterns: [schema-driven-readonly, prop-threading, isReadOnly-derived]
key_files:
  created: []
  modified:
    - tools/arrconf-ui/web/src/api.ts
    - tools/arrconf-ui/web/src/types.ts
    - tools/arrconf-ui/web/src/constants.ts
    - tools/arrconf-ui/web/src/i18n/fr.ts
    - tools/arrconf-ui/web/src/lib/FieldInput.svelte
decisions:
  - "readOnly derived from BOTH prop OR schema node — single source of truth at the schema level; prop used for parent-driven inheritance"
  - "CONFIG_FILE_PATHS uses 'as const' + keyof for compile-time ActiveConfig type"
  - "configarr functions use Record<string,unknown> payload — no TS model for configarr (configarr has its own schema served at runtime)"
metrics:
  duration: "4m"
  completed_date: "2026-05-30"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
---

# Phase 26 Plan 01: configarr Foundation Layer Summary

Foundation layer for editing configarr.yml in arrconf-ui: 4 configarr HTTP client functions, `readOnly` schema field, per-config file-path map, French i18n strings, and `readOnly` rendering support in the schema-driven `FieldInput.svelte` dispatcher.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add configarr API functions, readOnly type, file-path constants, i18n strings | 3be5eab | api.ts, types.ts, constants.ts, i18n/fr.ts |
| 2 | Add readOnly rendering (disabled widgets + lock badge) to FieldInput | 4e2b40e | lib/FieldInput.svelte |

## What Was Built

**Task 1 — Foundation contracts:**

- `api.ts`: 4 configarr HTTP functions (`getConfigarrConfig`, `getConfigarrSchema`, `putConfigarrConfig`, `postConfigarrDiff`) targeting `/api/configarr/*`, mirroring the existing arrconf 4-function pattern. Uses `Record<string, unknown>` as payload type — no TS model for configarr (schema is served at runtime).
- `types.ts`: `readOnly?: boolean` added as the last field on `JsonSchemaNode` (Phase 26 D-02). Present on configarr `ArrInstance` fields `api_key`, `media_naming`, `quality_definition`.
- `constants.ts`: `CONFIG_FILE_PATHS` map (`arrconf` → `charts/arr-stack/files/arrconf.yml`, `configarr` → `charts/arr-stack/files/configarr.yml`) + `ActiveConfig` type exported for HeaderBar use in 26-02.
- `i18n/fr.ts`: 10 configarr field labels added to `FIELD_LABELS`, `READONLY_TOOLTIP_TEXT` + `UNSAVED_SWITCH_MESSAGE` top-level exports, `configarr` entry added to `SECTION_DOCS`.

**Task 2 — readOnly widget rendering:**

- `FieldInput.svelte`: `readOnly?: boolean` prop (default `false`) added to `Props` type and destructure.
- `isReadOnly` derived: `$derived(readOnly || effective.readOnly === true)` — combines prop inheritance with schema-node marker.
- Lock badge: `<span class="lock-badge" title={READONLY_TOOLTIP_TEXT}>🔒</span>` in the label block, gated on `isReadOnly`.
- `disabled={isReadOnly}` applied to all 5 leaf editable widgets: `<select>`, `<input type="number">`, `<input type="checkbox">`, primitive-array `<input>`, string `<input>`.
- `readOnly={isReadOnly}` threaded through both recursion paths: array-of-objects nested `<FieldInput>` and object recursion `<FieldInput>`. This makes `media_naming` and `quality_definition` object subtrees render fully disabled at all leaf levels.
- `.lock-badge` CSS added following the `.array-count` token pattern.

## Verification

- `npm run check`: 0 errors, 0 warnings (92 files)
- `npm run typecheck`: exit 0
- `npm run build`: exit 0 (88.73 kB JS, 17.63 kB CSS)
- ADR-5 gate: `grep -c "fetch(\|/api/v3\|http://"` in FieldInput = 0

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints introduced in this plan. FieldInput contains no fetch/URL construction (T-26-03 acceptance gate enforced via grep check). The `api.ts` configarr functions mirror the existing arrconf pattern — same trust boundary (operator browser → arrconf-ui backend, LAN-trusted), same `/api/*` base path. No new trust boundaries.

## Known Stubs

None. All 4 configarr API functions are complete implementations (no TODO/placeholder). The `readOnly` prop and derived are wired to the schema source of truth. Plan 26-02 will consume these contracts to wire the App.svelte orchestration.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| api.ts exists | FOUND |
| types.ts exists | FOUND |
| constants.ts exists | FOUND |
| i18n/fr.ts exists | FOUND |
| FieldInput.svelte exists | FOUND |
| SUMMARY.md exists | FOUND |
| Commit 3be5eab (Task 1) | FOUND |
| Commit 4e2b40e (Task 2) | FOUND |
