---
phase: 34-ui-over-intent
plan: "02"
subsystem: arrconf-ui-frontend
tags: [svelte5, three-tab, intent, materialization-diff, read-only-inspector, ui-pivot, d-34-04]
dependency_graph:
  requires: [34-01]
  provides: [three-tab-state-machine, materialization-diff-panel, read-only-inspector, intent-api-layer]
  affects: [arrconf-ui-frontend, HeaderBar, App.svelte, api.ts, constants.ts, types.ts]
tech_stack:
  added: []
  patterns: [three-tab-state-machine, unified-diff-colorizer, read-only-inspector, intent-save-flow]
key_files:
  created:
    - tools/arrconf-ui/web/src/lib/ReadOnlyInspector.svelte
    - tools/arrconf-ui/web/src/lib/MaterializationDiffPanel.svelte
  modified:
    - tools/arrconf-ui/web/src/constants.ts
    - tools/arrconf-ui/web/src/types.ts
    - tools/arrconf-ui/web/src/api.ts
    - tools/arrconf-ui/web/src/lib/HeaderBar.svelte
    - tools/arrconf-ui/web/src/App.svelte
decisions:
  - "D-34-04 enforced on frontend: putConfig + putConfigarrConfig removed from api.ts; only GET inspector sources kept"
  - "App.svelte three-tab default: intent (editable), arrconf (read-only inspector), configarr (read-only inspector)"
  - "diffCount semantics: compares JSON.stringify(intentState) vs savedIntent on intent tab; 0 on inspect tabs"
  - "Inspector tabs use api.getConfig()/getConfigarrConfig() stringify output — sufficient for YAML inspection until YAML string endpoint added"
  - "Temporary intent <pre> JSON preview placed at 34-03 marker; form sections wired in 34-03"
metrics:
  duration: "~25 minutes"
  completed_date: "2026-06-08"
  tasks_completed: 3
  files_modified: 7
---

# Phase 34 Plan 02: Three-Tab Frontend Skeleton Summary

**One-liner:** Svelte 5 frontend restructured from two-tab (arrconf/configarr) to three-tab (intent.yml editable | arrconf.yml inspect | configarr.yml inspect) with materialization diff panel, read-only inspector, and full intent API layer.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | constants + types + api.ts intent layer | c5657dd | constants.ts, types.ts, api.ts |
| 2 | ReadOnlyInspector + MaterializationDiffPanel | fefb853 | ReadOnlyInspector.svelte, MaterializationDiffPanel.svelte |
| 3 | HeaderBar 3rd tab + App.svelte three-tab wiring | b74513b | HeaderBar.svelte, App.svelte |

## What Was Built

### `tools/arrconf-ui/web/src/constants.ts`

- Added `intent: 'charts/arr-stack/files/intent.yml'` as first key in `CONFIG_FILE_PATHS` (makes it the default tab)
- Added `INTENT_SECTIONS` constant with 6 ordered section keys: categories, sagas, apps, tools, profile_definitions, configarr
- `ActiveConfig` type now has 3 members: `'intent' | 'arrconf' | 'configarr'`

### `tools/arrconf-ui/web/src/types.ts`

Added Phase 34 intent types:
- `CustomFormatRef`: `{ trash_ids: string[]; score: number | null }`
- `ProfileDefinition`: `{ body: Record<string, unknown>; custom_formats: CustomFormatRef[] }`
- `IntentPayload`: 6-key type mirroring `IntentConfig` backend shape
- `MaterializationDiffResponse`: `{ arrconf_diff: string; configarr_diff: string; has_changes: boolean }`

### `tools/arrconf-ui/web/src/api.ts`

- Added `getIntent()`, `getIntentSchema()`, `postIntentDiff()`, `putIntent()` following existing `_fetchJson` patterns
- Removed `putConfig` and `putConfigarrConfig` (D-34-04 enforcement); replaced with D-34-04 comment
- Kept `getConfig()`, `getConfigarrConfig()` as read-only inspector sources

### `tools/arrconf-ui/web/src/lib/ReadOnlyInspector.svelte` (NEW)

Props: `{ content: string | null; filePath: string; loadError: string | null }`
- File label `<code>` (12px IBM Plex Mono, `--ink-muted`) + pill badge "généré — lecture seule" (`--panel-alt` bg)
- `<pre class="inspector">`: IBM Plex Mono 12px, `--code-bg`, `1px solid var(--border)`, border-radius 4px, `overflow-y:auto`, `white-space:pre-wrap`, `word-break:break-all`, no max-height
- Load error: `.load-error` card (red left-border, matches App.svelte pattern)
- No save button, no `putIntent`/`putConfig` calls (T-34-07 mitigated)

### `tools/arrconf-ui/web/src/lib/MaterializationDiffPanel.svelte` (NEW)

Props: `{ arrconfDiff: string; configarrDiff: string; onConfirm: () => void; onCancel: () => void }`
- h2: "Matérialisation — vérifier avant d'enregistrer"
- Two labelled file sections (arrconf.yml, configarr.yml), each with `<code>` label (12px mono, border-top rule) + `<pre>` diff block (max-height 300px, overflow-y auto, `--code-bg`)
- Diff line colorization via `$derived`: `+` → `#10b981` (emerald), `-` → `var(--destructive)`, `@@` → `var(--accent)`, context → `var(--ink-muted)`
- "Aucune modification" in `--ink-faint` italic when diff string empty
- Actions row: "Continuer l'édition" + "Confirmer et enregistrer" (`--accent` bg, weight 600)
- `role="dialog" aria-modal="true"`, no `{@html}` anywhere (T-34-08 mitigated)

### `tools/arrconf-ui/web/src/lib/HeaderBar.svelte`

- Three tabs: `intent.yml`, `arrconf.yml`, `configarr.yml` (in order)
- Save button visible ONLY when `activeConfig === 'intent'` (hidden on inspect tabs)
- "généré — lecture seule" pill badge shown after filepath on arrconf/configarr tabs
- Default `activeConfig` changed from `'arrconf'` to `'intent'`

### `tools/arrconf-ui/web/src/App.svelte`

Complete three-tab state machine rewrite:
- State: `intentState`, `savedIntent`, `schema`, `inspectorContent`, `validationErrors`, `saveStatus`, `loadError`, `showDiffPanel`, `pendingMatDiff`, `showSaveToast`, `activeConfig` (default `'intent'`), `confirmSwitchOpen`, `pendingSwitch`
- `diffCount`: compares `JSON.stringify(intentState) === JSON.stringify(savedIntent)` on intent tab; 0 on inspect tabs
- `loadForConfig('intent')`: `Promise.all([getIntentSchema(), getIntent()])`; `loadForConfig('arrconf')`: `getConfig()` stringify; `loadForConfig('configarr')`: `getConfigarrConfig()` stringify
- `openDiffPanel()`: calls `postIntentDiff(intentState)`, stores `pendingMatDiff`, shows `MaterializationDiffPanel`
- `confirmSave()`: calls `putIntent(intentState)`, updates `savedIntent`, shows `SaveToast`
- Intent tab body: `MaterializationDiffPanel` when `showDiffPanel`, else temporary `<pre>` JSON preview with `<!-- 34-03: mount intent form sections here -->` marker
- Inspect tabs: `ReadOnlyInspector` with correct `filePath` and `loadError`
- Tab switch guard preserved (diffCount gate + confirmSwitchOpen dialog)

## Verification

All plan success criteria met:

- `cd tools/arrconf-ui/web && node_modules/.bin/svelte-check --threshold error` → 0 errors, 0 warnings
- `npm run build` → ✓ built in 742ms (127 modules)
- No `{@html}` in any new/modified component
- No raw hex colors beyond UI-SPEC diff palette (#10b981 only in MaterializationDiffPanel)
- `grep -c "putConfig\b" api.ts` → 0 (function removed)
- HeaderBar: 3 onTabChange calls for 'intent', 'arrconf', 'configarr'
- HeaderBar: save button gated with `activeConfig === 'intent'` + "généré — lecture seule" badge
- App.svelte: `$state<ActiveConfig>('intent')` default
- App.svelte: contains `api.postIntentDiff`, `api.putIntent`, `api.getIntent`, `MaterializationDiffPanel`, `ReadOnlyInspector`
- App.svelte: `<!-- 34-03: mount intent form sections here -->` marker present

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] App.svelte referenced removed API functions during Task 2 svelte-check**
- **Found during:** Task 2 verification (`svelte-check --threshold error` reported 2 errors)
- **Issue:** Task 2 runs `svelte-check` on the whole codebase; App.svelte still called `api.putConfig` and `api.putConfigarrConfig` which were removed in Task 1
- **Fix:** Implemented Task 3 (HeaderBar + App.svelte rewrite) before committing Task 2, allowing svelte-check to pass; committed Task 2 and Task 3 as separate commits in the correct order
- **Files modified:** `tools/arrconf-ui/web/src/lib/HeaderBar.svelte`, `tools/arrconf-ui/web/src/App.svelte`
- **Commits:** fefb853 (Task 2), b74513b (Task 3)

### Notes

- Inspector tabs display JSON-stringified config objects (since `getConfig()` returns `ConfigPayload` object, not raw YAML string). This is functional for inspection purposes; a future plan could add a dedicated `/api/config/raw` endpoint returning the YAML string for a cleaner display. Logged in deferred-items.
- No changes to arrconf Python code → no co-bump of `arrconf.image.tag` required (frontend-only task)

## Threat Surface Scan

No new threat surface beyond plan's threat model:
- T-34-06 (info disclosure): ReadOnlyInspector renders operator's own config; LAN-trusted; accepted
- T-34-07 (tampering): ReadOnlyInspector has no inputs, no save button, no PUT functions; mitigated by construction
- T-34-08 (XSS): All content rendered as text nodes via Svelte interpolation; no `{@html}` anywhere; mitigated
- T-34-09 (auth): LAN-trusted single-operator; accepted

## Self-Check: PASSED

Files created:
- `/data/projets/perso/arr-stack/.claude/worktrees/agent-a8901ec2832ee4314/tools/arrconf-ui/web/src/lib/ReadOnlyInspector.svelte` ✓
- `/data/projets/perso/arr-stack/.claude/worktrees/agent-a8901ec2832ee4314/tools/arrconf-ui/web/src/lib/MaterializationDiffPanel.svelte` ✓

Files modified:
- `/data/projets/perso/arr-stack/.claude/worktrees/agent-a8901ec2832ee4314/tools/arrconf-ui/web/src/constants.ts` ✓
- `/data/projets/perso/arr-stack/.claude/worktrees/agent-a8901ec2832ee4314/tools/arrconf-ui/web/src/types.ts` ✓
- `/data/projets/perso/arr-stack/.claude/worktrees/agent-a8901ec2832ee4314/tools/arrconf-ui/web/src/api.ts` ✓
- `/data/projets/perso/arr-stack/.claude/worktrees/agent-a8901ec2832ee4314/tools/arrconf-ui/web/src/lib/HeaderBar.svelte` ✓
- `/data/projets/perso/arr-stack/.claude/worktrees/agent-a8901ec2832ee4314/tools/arrconf-ui/web/src/App.svelte` ✓

Commits verified:
- `c5657dd` (Task 1 — intent layer): ✓ present
- `fefb853` (Task 2 — components): ✓ present
- `b74513b` (Task 3 — wiring): ✓ present
