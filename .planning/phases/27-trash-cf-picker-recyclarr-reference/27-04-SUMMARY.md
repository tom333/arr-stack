---
phase: 27-trash-cf-picker-recyclarr-reference
plan: 04
subsystem: ui
tags: [svelte5, typescript, recyclarr, configarr, pickers, trash-guides]

# Dependency graph
requires:
  - phase: 27-03
    provides: TrashCFPicker + TrashQPPicker Svelte 5 components, types, api functions, i18n keys
provides:
  - RecyclarrReferencePicker.svelte — read-only Recyclarr template dropdown with copy-name (CFGUI-06)
  - AppSection.svelte with configarrMode gate mounting CF/QP/Recyclarr pickers for sonarr+radarr
  - App.svelte passing configarrMode + localDefinitions on configarr branch only
  - End-to-end verified: CF/QP/Recyclarr pickers observable in running UI with save round-trip intact
affects:
  - future UI plans touching AppSection or configarr form sections

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "configarrMode gate: optional boolean prop on AppSection controls picker visibility — pickers never mount in arrconf form"
    - "Read-only component pattern: RecyclarrReferencePicker has no onChange, no config write — clipboard-only action (D-13)"
    - "Derived helpers from section value: main, mainCustomFormats, mainProfiles, profileNames all via $derived()"
    - "updateMain() thin wrapper: reuses existing onChange → updateAppSection → PUT path; no second write path"

key-files:
  created:
    - tools/arrconf-ui/web/src/lib/RecyclarrReferencePicker.svelte
  modified:
    - tools/arrconf-ui/web/src/lib/AppSection.svelte
    - tools/arrconf-ui/web/src/App.svelte

key-decisions:
  - "Recyclarr picker is strictly read-only (D-13): no onChange, no include: insertion — clipboard copy of template id only"
  - "configarrMode gate: pickers mounted in AppSection only when configarrMode=true AND sectionName in {sonarr,radarr} — never in arrconf form"
  - "MEDIUM-confidence QP field mapping (research correction #4) confirmed by operator: upgrade.until_quality == TRaSH cutoff, qualities[] reflects items[allowed!=false] in baked order"

patterns-established:
  - "configarrMode prop pattern: AppSection accepts optional configarrMode boolean; App.svelte sets it only on the configarr branch"
  - "Section value derivation: use $derived((value?.main ?? {}) as Record<string, unknown>) to safely extract nested configarr section data"

requirements-completed: [CFGUI-05, CFGUI-06, CFGUI-08]

# Metrics
duration: 2 sessions (Task 1+2 executor + human verification)
completed: 2026-05-31
---

# Phase 27 Plan 04: RecyclarrReferencePicker + Full Picker Integration Summary

**RecyclarrReferencePicker (CFGUI-06) wired alongside CF/QP pickers in AppSection under configarrMode gate — all 3 pickers operator-verified end-to-end with save round-trip, tag safety, and QP field mapping confirmed**

## Performance

- **Duration:** Multi-session (implementation + human verification)
- **Started:** 2026-05-30
- **Completed:** 2026-05-31
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint — approved)
- **Files modified:** 3

## Accomplishments

- Created `RecyclarrReferencePicker.svelte`: read-only Svelte 5 runes component — loads Recyclarr templates via `getRecyclarrTemplates(app)`, displays template `id` as primary label (no fabricated description per research correction #1), greyed `template` path as subtitle, "Référence uniquement" header + lock badge, and a single "Copier le nom" clipboard action. No `onChange`, no `include:` insertion ever written.
- Wired all 3 pickers (TrashCFPicker, TrashQPPicker, RecyclarrReferencePicker) into `AppSection.svelte` behind `{#if configarrMode && (sectionName === 'sonarr' || sectionName === 'radarr')}` — pickers never appear in the arrconf form.
- Updated `App.svelte` to pass `configarrMode={true}` and `localDefinitions` only on the configarr branch; arrconf branch unchanged.
- Operator ran 8-step verification: CF custom/unknown classification, QP append-only + collision block, Recyclarr read-only copy-name, save diff preserves 3 hand-rolled profiles + `!env`/`!secret` tags, QP field mapping (MEDIUM confidence — confirmed correct), zero github.com network calls. All 8 checks passed.

## Task Commits

1. **Task 1: RecyclarrReferencePicker.svelte** - `3d21207` (feat)
2. **Task 2: Wire 3 pickers into AppSection + App.svelte** - `c70774a` (feat)
3. **Task 3: Human-verify checkpoint** - APPROVED by operator (no commit — verification task)

## Files Created/Modified

- `tools/arrconf-ui/web/src/lib/RecyclarrReferencePicker.svelte` — New: read-only Recyclarr template dropdown with copy-name; Svelte 5 runes; no onChange/include: (CFGUI-06)
- `tools/arrconf-ui/web/src/lib/AppSection.svelte` — Added: `configarrMode` prop, `localDefinitions` prop, derived helpers, `updateMain()`, picker mount block with `.picker-section` CSS
- `tools/arrconf-ui/web/src/App.svelte` — Added: `configarrMode={true}` + `localDefinitions` props on configarr branch only

## Decisions Made

- **Recyclarr picker strictly read-only (D-13):** No `include:` insertion deferred to v1.x due to merge-hazard with 6 hand-rolled French CFs. Clipboard copy of template id is the only action. Locked decision from Phase 27 planning.
- **No description field (research correction #1):** Recyclarr config-templates have no `description` field — component displays `id` as primary label and `template` path as subtitle. Code comment references correction #1.
- **MEDIUM-confidence QP field mapping confirmed:** `upgrade.until_quality == TRaSH cutoff`, `qualities[]` reflects `items[allowed!=false]` in baked order (Feb-2026). Operator verified step 7 and found mapping correct — no discrepancy reported.
- **configarrMode gate:** Pickers absent from arrconf form — ADR-5 boundary enforced at the prop level.

## Deviations from Plan

None — plan executed exactly as written. The MEDIUM-confidence QP mapping (research correction #4) was flagged in the plan and confirmed correct during human verification.

## Issues Encountered

None. Frontend quad (svelte-check + tsc + vite build) passed with 0 errors, 0 warnings on both task commits and final verification run.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Phase 27 is complete. All 4 plans delivered:
- Plan 01: TRaSH/Recyclarr baked catalog (offline, no GitHub at runtime)
- Plan 02: 3 metadata endpoints `/api/trash/*`
- Plan 03: TrashCFPicker + TrashQPPicker Svelte 5 components
- Plan 04: RecyclarrReferencePicker + full integration (this plan)

CFGUI-05 (CF picker), CFGUI-06 (Recyclarr reference), CFGUI-08 (QP picker) are all satisfied in the running UI. SC#1/#3/#4/#5 are observable. Save round-trip preserves tags (SC#2 / ADR-8). Zero external network calls at runtime.

Ready for Phase 28 (IaC revisit — parked) or next v0.9.0 milestone closure.

---

## Threat Surface Scan

No new threat surface beyond what was covered in the plan's threat model. All T-27-13 through T-27-16 mitigations confirmed by operator during step 5 (Recyclarr write-free), step 6 (tag safety), step 8 (zero GitHub calls), and acceptance criteria grep gates:
- `onChange` count in RecyclarrReferencePicker.svelte = 0
- `include:` count in RecyclarrReferencePicker.svelte = 0
- No *arr API URLs found in `web/src/`

---

*Phase: 27-trash-cf-picker-recyclarr-reference*
*Completed: 2026-05-31*
