---
phase: 34-ui-over-intent
plan: "03"
subsystem: arrconf-ui-frontend
tags: [svelte5, profile-card, trash-picker, intent-form, configarr-raw, profile-definitions, i18n]
dependency_graph:
  requires: [34-02]
  provides: [ProfileCard, ProfileDefinitionsEditor, ConfigarrRawEditor, intent-form-complete]
  affects: [arrconf-ui-frontend, App.svelte, fr.ts]
tech_stack:
  added: []
  patterns: [custom-format-ref-transform, collapsible-profile-card, inline-delete-confirm, opaque-raw-editor]
key_files:
  created:
    - tools/arrconf-ui/web/src/lib/ProfileCard.svelte
    - tools/arrconf-ui/web/src/lib/ProfileDefinitionsEditor.svelte
    - tools/arrconf-ui/web/src/lib/ConfigarrRawEditor.svelte
  modified:
    - tools/arrconf-ui/web/src/i18n/fr.ts
    - tools/arrconf-ui/web/src/App.svelte
decisions:
  - "CustomFormatRef<->CustomFormatEntry shape transform via assign_scores_to[0] — ProfileCard wraps per-profile refs into picker-compatible entries"
  - "JSON.stringify as minimal YAML substitute — no new npm packages; parse error displayed inline but does not crash"
  - "AppSection with JSON fallback for sagas/apps/tools — if schema node absent, raw JSON pre rendered"
  - "localDefinitions=[] for ProfileDefinitionsEditor in App.svelte — no customFormatDefinitions in intent schema sourced"
metrics:
  duration: "~25 minutes"
  completed_date: "2026-06-08"
  tasks_completed: 3
  files_modified: 5
---

# Phase 34 Plan 03: Intent Form Sections Summary

**One-liner:** Three new Svelte 5 components (ProfileCard + ProfileDefinitionsEditor + ConfigarrRawEditor) complete the intent.yml editing form, wiring all six ordered sections into App.svelte with per-profile TRaSH CF/QP pickers and FR i18n strings.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | ProfileCard with body editor + CF chips + TRaSH pickers | 590db40 | ProfileCard.svelte, fr.ts (partial) |
| 2 | ProfileDefinitionsEditor + ConfigarrRawEditor + i18n | 8e58dce | ProfileDefinitionsEditor.svelte, ConfigarrRawEditor.svelte |
| 3 | Wire six intent sections into App.svelte intent tab | d4e89a1 | App.svelte |

## What Was Built

### `tools/arrconf-ui/web/src/lib/ProfileCard.svelte` (NEW)

- Collapsible `<details>` card per profile (IBM Plex Mono profile name, `--panel` bg + `--border` border)
- Inline delete confirm: `✕` swaps header to `Supprimer {name} ?` + `[Annuler la suppression]` / `[Supprimer le profil]` buttons — no modal
- Body textarea: JSON-serialized `profile.body`, IBM Plex Mono 12px, `--code-bg`, parse error inline; uses `PROFILE_BODY_LABEL` from fr.ts
- CF chip list: one chip per `CustomFormatRef` entry; per-chip score `<input type="number">` (5em, placeholder from `SCORE_OVERRIDE_PLACEHOLDER`); `aria-label="Retirer le format {name}"`
- `CustomFormatRef[] <-> CustomFormatEntry[]` shape transform via `assign_scores_to[0]` (Pattern 5)
- TrashCFPicker mounted per profile; TrashQPPicker feeds into `profile.body` via merge
- No `*arr` URL, no `base_url`, no `{@html}` — ADR-5 preserved

### `tools/arrconf-ui/web/src/lib/ProfileDefinitionsEditor.svelte` (NEW)

- Renders one `ProfileCard` per key in `profiles: Record<string, ProfileDefinition>`
- `+ Ajouter un profil` button (`--accent-soft` bg, `--accent` border, IBM Plex Sans 14px weight 400) with inline text input
- Duplicate name guard: shows error "Le profil X existe déjà." — no empty/duplicate key added
- `inferApp(name)`: heuristic mapping profile name to `'sonarr' | 'radarr'` (radarr if contains radarr/movie/film, else sonarr)
- Add/delete pattern mirrors CategoriesEditor lines 39-46

### `tools/arrconf-ui/web/src/lib/ConfigarrRawEditor.svelte` (NEW)

- Props: `{ value: Record<string, unknown>; onChange: ... }`
- Label: `CONFIGARR_RAW_LABEL` (IBM Plex Sans 14px weight 600)
- Textarea `class="raw-editor"`: IBM Plex Mono 12px, `--code-bg`, `1px solid var(--border)`, min-height 200px, resize vertical
- Helper text via `<code>`: `CONFIGARR_RAW_HELPER` (IBM Plex Sans 12px weight 400 italic `--ink-faint`) — opaque pass-through semantics (D-33-07/08)
- HTML comment `pass-through: this block is emitted verbatim to configarr.yml`
- No `{@html}`, no *arr API calls

### `tools/arrconf-ui/web/src/i18n/fr.ts` (MODIFIED)

Phase 34 additions:
- Six `intent.*` SECTION_DOCS entries: `intent.categories`, `intent.sagas`, `intent.apps`, `intent.tools`, `intent.profile_definitions`, `intent.configarr`
- String constants: `READONLY_BADGE_TEXT`, `MATERIALIZATION_EMPTY_TEXT`, `PROFILE_BODY_LABEL`, `CONFIGARR_RAW_LABEL`, `CONFIGARR_RAW_HELPER`, `ADD_PROFILE_TEXT`, `PROFILE_NAME_PLACEHOLDER`, `SCORE_OVERRIDE_PLACEHOLDER`

### `tools/arrconf-ui/web/src/App.svelte` (MODIFIED)

- Imports: `SectionDoc`, `CategoriesEditor`, `AppSection`, `ProfileDefinitionsEditor`, `ConfigarrRawEditor`
- `updateIntent<K>()` helper: `intentState = { ...intentState!, [key]: val }` drives diffCount and save button
- Replaced `<!-- 34-03: mount intent form sections here -->` + `<pre>` with six ordered sections:
  1. `<SectionDoc section="intent.categories" />` + `<CategoriesEditor>`
  2. `<SectionDoc section="intent.sagas" />` + `<AppSection>` (or JSON fallback)
  3. `<SectionDoc section="intent.apps" />` + `<AppSection>` (or JSON fallback)
  4. `<SectionDoc section="intent.tools" />` + `<AppSection>` (or JSON fallback)
  5. `<SectionDoc section="intent.profile_definitions" />` + `<ProfileDefinitionsEditor>`
  6. `<SectionDoc section="intent.configarr" />` + `<ConfigarrRawEditor>`
- `.section-raw` CSS for fallback raw JSON display; removed obsolete `.intent-preview`

## Verification

All plan success criteria met:

- `node_modules/.bin/svelte-check --threshold error` → 0 errors, 2 warnings (pre-existing Svelte 5 state pattern)
- `npm run build` → 154 modules built in 1.13s
- `npm run typecheck` → 0 errors (tsc --noEmit)
- No `{@html}` in any new component
- No `base_url` or `http` in ProfileCard (ADR-5 preserved)
- `grep -c "34-03: mount intent form sections here" App.svelte` → 0 (marker removed)
- All six `intent.*` SECTION_DOCS keys in fr.ts
- `updateIntent` helper present in App.svelte
- All required i18n string constants exported from fr.ts

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes

- `SECTION_DOCS` is not imported in App.svelte: `SectionDoc` reads it internally from fr.ts by `section` prop key. The acceptance criterion references "SECTION_DOCS['intent.categories']" as a pattern — the component achieves this via `section="intent.categories"` prop which SectionDoc resolves internally.
- AppSection JSON fallback: when `schema.properties.sagas/apps/tools` is null, a raw JSON `<pre>` is shown. Safe and non-blocking.
- `localDefinitions=[]` passed to ProfileDefinitionsEditor: the intent payload doesn't include `customFormatDefinitions`; the picker fetches the baked TRaSH catalogue via `/api/trash/*` (ADR-5).
- No co-bump of `arrconf.image.tag`: this plan touches only `tools/arrconf-ui/**` (CLAUDE.md exception rule).

## Threat Surface Scan

No new threat surface beyond plan's threat model:
- T-34-10 (ADR-5 elevation): ProfileCard writes per-profile refs only; no *arr URL; grep-verified clean
- T-34-11 (XSS): All content in text nodes; no `{@html}` anywhere; Svelte escapes all interpolated text
- T-34-12 (tampering): Parse errors displayed inline; backend re-validates on save
- T-34-13 (auth): LAN-trusted single-operator; accepted

## Known Stubs

None — all sections render actual data from intentState; no hardcoded empty values blocking intent editing.

## Self-Check: PASSED

Files created:
- `tools/arrconf-ui/web/src/lib/ProfileCard.svelte` exists in worktree
- `tools/arrconf-ui/web/src/lib/ProfileDefinitionsEditor.svelte` exists in worktree
- `tools/arrconf-ui/web/src/lib/ConfigarrRawEditor.svelte` exists in worktree

Commits verified:
- `590db40` (Task 1 — ProfileCard + fr.ts partial): present
- `8e58dce` (Task 2 — ProfileDefinitionsEditor + ConfigarrRawEditor): present
- `d4e89a1` (Task 3 — App.svelte wiring): present
