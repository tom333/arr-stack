---
phase: 27-trash-cf-picker-recyclarr-reference
plan: "03"
subsystem: arrconf-ui/frontend
tags: [svelte5, trash-guides, recyclarr, picker, custom-formats, quality-profiles, i18n, security]
dependency_graph:
  requires:
    - plans/27-01 (baked catalog JSON assets in trash-metadata/)
    - plans/27-02 (GET /api/trash/* backend endpoints)
  provides:
    - TrashCFPicker.svelte (CFGUI-05: CF add/remove + classification)
    - TrashQPPicker.svelte (CFGUI-08: QP append-only + collision guard)
    - TrashApp, TrashCFEntry, TrashQPEntry, TrashQPItem, RecyclarrTemplateEntry types
    - getTrashCustomFormats, getTrashQualityProfiles, getRecyclarrTemplates api functions
    - FR i18n constants for picker badge/warning text
  affects:
    - plans/27-04 (wires pickers into AppSection; human verification checkpoint)
tech_stack:
  added: []
  patterns:
    - Svelte 5 runes ($state, $derived, $effect) for async catalog load + reactivity
    - Set-reassignment pattern for multi-select reactivity (Pitfall 5)
    - CSS token-only dark theme styling (no hardcoded colors)
    - FR i18n via named const exports in fr.ts (no inline strings in components)
    - Append-only spread for QP insert (T-27-11 mitigation)
key_files:
  created:
    - tools/arrconf-ui/web/src/lib/TrashCFPicker.svelte
    - tools/arrconf-ui/web/src/lib/TrashQPPicker.svelte
  modified:
    - tools/arrconf-ui/web/src/types.ts
    - tools/arrconf-ui/web/src/api.ts
    - tools/arrconf-ui/web/src/i18n/fr.ts
decisions:
  - "Set-reassignment (new Set(selected)) for multi-select toggle per Pitfall 5 — avoids in-place mutation which breaks Svelte 5 reactivity"
  - "trash_description rendered as text (br→newline replacement) not {@html} — avoids XSS surface T-27-10 from upstream catalog HTML"
  - "generateQPEntry field mapping (cutoff→until_quality, cutoffFormatScore→until_score) flagged MEDIUM confidence per research correction #4 — requires human verification in Plan 04 checkpoint"
  - "Unknown trash_ids preserved verbatim on remove (only operator ✕ click removes); picker never auto-strips unknown entries (T-27-09)"
metrics:
  duration_seconds: 243
  completed_date: "2026-05-30"
  tasks_completed: 3
  files_created: 2
  files_modified: 3
---

# Phase 27 Plan 03: Frontend Picker Components — Summary

**One-liner:** TrashCFPicker (CFGUI-05) + TrashQPPicker (CFGUI-08) Svelte 5 components with Set-safe multi-select, trash_id classification (trash/custom/unknown), append-only QP insert, and collision guard — wired to the Plan 02 backend endpoints via 3 new typed api.ts functions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Phase 27 types, api fetch functions, FR i18n | 51d92bf | types.ts, api.ts, i18n/fr.ts |
| 2 | TrashCFPicker.svelte | 74acefc | TrashCFPicker.svelte (created) |
| 3 | TrashQPPicker.svelte | 4bf7ed5 | TrashQPPicker.svelte (created) |

## What Was Built

**types.ts:** Appended 5 new types (TrashApp, TrashCFEntry, TrashQPEntry, TrashQPItem, RecyclarrTemplateEntry) after existing SaveStatus — append-only, no reordering.

**api.ts:** Added TrashApp, TrashCFEntry, TrashQPEntry, RecyclarrTemplateEntry to the `from './types'` import block. Appended 3 one-liner fetch functions following the `getConfigarrSchema()` pattern, using `_fetchJson<T>` with the correct query-param URL shape from Plan 02 endpoints.

**fr.ts:** Appended 3 FIELD_LABELS entries (trash_cf_picker, trash_qp_picker, recyclarr_reference) to the existing record. Appended 6 exported constants after the Phase 26 READONLY/UNSAVED constants: TRASH_CUSTOM_BADGE_TEXT, TRASH_UNKNOWN_BADGE_TEXT, TRASH_COLLISION_WARNING_TEXT, RECYCLARR_REFERENCE_LABEL, TRASH_CF_SEARCH_PLACEHOLDER, TRASH_QP_ADD_LABEL.

**TrashCFPicker.svelte:** Full Svelte 5 runes component:
- Loads baked TRaSH CF catalog via `getTrashCustomFormats(app)` in `$effect`; shows `Spinner` while loading, `.error-msg` on error
- `selected = $state(new Set<string>())` with Set-reassignment toggle (Pitfall 5 safe)
- `filtered = $derived(...)` — real-time name search via text input
- `classify(id)` — resolves against catalog (→ 'trash'), localDefinitions (→ 'custom'), or 'unknown'; uses badge-custom / badge-warn respectively
- `labelFor(id)` — resolves display name from catalog, then local defs, then raw ID fallback
- `confirmAdd()` — skips already-present IDs; builds D-04-shaped entries `{ trash_ids: [id], assign_scores_to: profileNames.map(n => ({ name: n })) }` without explicit score; spread-appends to existingCustomFormats
- `removeEntry(idx)` — operator-only ✕ click removes entry; unknown IDs preserved verbatim otherwise (T-27-09)
- CSS token-only: no `#rrggbb` or `rgb()` anywhere

**TrashQPPicker.svelte:** Full Svelte 5 runes component:
- Loads catalog via `getTrashQualityProfiles(app)` in `$effect`
- Dropdown select → `selectedQP`; optional `nameOverride` text input
- `collisionName = $derived(nameOverride || selectedQP?.name)` — computed final name
- `hasCollision = $derived(existingProfiles.some(p => p.name === collisionName))` — blocks insert
- `generateQPEntry()` maps TRaSH JSON → configarr QP shape: items filtered (allowed !== false), qualities mapped with group expansion, upgrade fields from cutoff/cutoffFormatScore
- `confirmInsert()` — guard `if (!selectedQP || hasCollision) return`; appends via `[...existingProfiles, newEntry]`; never indexes/mutates/sorts existingProfiles (T-27-11)
- `trash_description` rendered via `br→\n` text replacement; no `{@html}` (T-27-10)

## Deviations from Plan

None — plan executed exactly as written.

## Validation Results

All acceptance criteria pass:

**Task 1:**
- `grep -E 'TrashCFEntry|TrashQPEntry|TrashQPItem|RecyclarrTemplateEntry|TrashApp' types.ts` — all 5 types present
- `grep -E 'getTrashCustomFormats|getTrashQualityProfiles|getRecyclarrTemplates' api.ts` — all 3 functions present
- `grep -E 'TRASH_CUSTOM_BADGE_TEXT|TRASH_UNKNOWN_BADGE_TEXT|TRASH_COLLISION_WARNING_TEXT|RECYCLARR_REFERENCE_LABEL' fr.ts` — all 4 constants present
- `npm run typecheck` → exit 0
- `npm run check` → 92 files, 0 errors

**Task 2:**
- `getTrashCustomFormats` present (import + $effect call)
- `classify` and `labelFor` functions present
- `badge-custom` present (chip render + CSS class)
- `badge-warn` present (chip render + CSS class)
- `new Set(selected)` — 1 occurrence (toggle function, Pitfall-5-safe)
- Zero hardcoded `#rrggbb` / `rgb()` colors
- `package.json` unchanged (no new deps)
- `npm run check && typecheck && build` all exit 0

**Task 3:**
- `getTrashQualityProfiles` present (import + $effect call)
- `hasCollision` and `collisionName` both present
- `generateQPEntry` present (definition + call)
- `[...existingProfiles, newEntry]` spread-append present
- Zero `existingProfiles[idx]` / `.splice` / `.sort` mutations
- `disabled` present on insert button (collision + null guard)
- Zero hardcoded colors
- `npm run check && typecheck && build` all exit 0

**Final quad gate (post all tasks):**
- `svelte-check`: 94 files, 0 errors, 0 warnings
- `tsc --noEmit`: exit 0
- `vite build`: 140 modules, built in 959ms

## Known Stubs

None — both components make real API calls to the Plan 02 backend endpoints and compute real config mutations. The MEDIUM-confidence field mapping in `generateQPEntry` (research correction #4) is flagged in the code comment and in the Plan 04 checkpoint for human verification — it is not a functional stub.

## Threat Surface Scan

All threats from the plan's threat model are mitigated:

| Flag | File | Description |
|------|------|-------------|
| T-27-09 mitigated | TrashCFPicker.svelte | removeEntry only on explicit ✕; unknown IDs preserved verbatim; no auto-strip |
| T-27-10 mitigated | TrashQPPicker.svelte | `descriptionAsText()` replaces `<br>` with newlines; no `{@html}` used |
| T-27-11 mitigated | TrashQPPicker.svelte | Append-only `[...existingProfiles, newEntry]`; grep confirms no index/splice/sort |
| T-27-12 mitigated | TrashCFPicker.svelte, TrashQPPicker.svelte | Only calls `/api/trash/*` relative URLs; no *arr host string |

No new threat surface introduced beyond the plan's threat model.

## Self-Check: PASSED

Files exist:
- tools/arrconf-ui/web/src/types.ts — FOUND (commit 51d92bf)
- tools/arrconf-ui/web/src/api.ts — FOUND (commit 51d92bf)
- tools/arrconf-ui/web/src/i18n/fr.ts — FOUND (commit 51d92bf)
- tools/arrconf-ui/web/src/lib/TrashCFPicker.svelte — FOUND (commit 74acefc)
- tools/arrconf-ui/web/src/lib/TrashQPPicker.svelte — FOUND (commit 4bf7ed5)

Commits exist: `git log --oneline | grep -E '51d92bf|74acefc|4bf7ed5'` — all 3 present on main.
