---
phase: 15-local-config-ui
plan: 15-B
subsystem: arrconf-ui-frontend
tags: [svelte, vite, typescript, frontend, ui, schema-driven]
dependency_graph:
  requires: [arrconf-ui-backend-package, fastapi-4-endpoints, cli-launcher]
  provides: [arrconf-ui-frontend-spa, local-config-ui-complete]
  affects: [README.md]
tech_stack:
  added: [svelte@5, vite@6, @sveltejs/vite-plugin-svelte@5, typescript@5, svelte-check@4]
  patterns: [schema-driven-form, svelte5-runes, vite-proxy, css-custom-properties, effectiveNode-ref-resolver]
key_files:
  created:
    - tools/arrconf-ui/web/package.json
    - tools/arrconf-ui/web/vite.config.ts
    - tools/arrconf-ui/web/tsconfig.json
    - tools/arrconf-ui/web/svelte.config.js
    - tools/arrconf-ui/web/index.html
    - tools/arrconf-ui/web/.gitignore
    - tools/arrconf-ui/web/src/main.ts
    - tools/arrconf-ui/web/src/app.css
    - tools/arrconf-ui/web/src/types.ts
    - tools/arrconf-ui/web/src/api.ts
    - tools/arrconf-ui/web/src/schema.ts
    - tools/arrconf-ui/web/src/constants.ts
    - tools/arrconf-ui/web/src/App.svelte
    - tools/arrconf-ui/web/src/lib/HeaderBar.svelte
    - tools/arrconf-ui/web/src/lib/CategoriesEditor.svelte
    - tools/arrconf-ui/web/src/lib/CategoryRow.svelte
    - tools/arrconf-ui/web/src/lib/AppSection.svelte
    - tools/arrconf-ui/web/src/lib/FieldInput.svelte
    - tools/arrconf-ui/web/src/lib/HelpTooltip.svelte
    - tools/arrconf-ui/web/src/lib/SuggestArrBadge.svelte
    - tools/arrconf-ui/web/src/lib/DiffPanel.svelte
    - tools/arrconf-ui/web/src/lib/SaveToast.svelte
    - tools/arrconf-ui/web/src/lib/ValidationBanner.svelte
    - tools/arrconf-ui/web/src/lib/Spinner.svelte
    - .planning/phases/15-local-config-ui/15-HUMAN-UAT.md
  modified:
    - README.md
decisions:
  - "vite bumped to ^6.0.0 (vite-plugin-svelte@5 peer dep requires vite@^6)"
  - "FieldInput self-imports itself for recursive Svelte 5 component reference"
  - "SaveToast role=status moved to wrapper div (a11y: interactive elements cannot have noninteractive roles)"
  - "DiffPanel aside changed to div for role=dialog compliance"
  - "CategoriesEditor add-row form is a hand-coded Surface 2 exception (per D-08)"
metrics:
  duration: "~45m"
  completed_date: "2026-05-23"
  tasks_completed: 4
  files_created: 25
  files_modified: 1
  tests_passed: 0
---

# Phase 15 Plan B: Svelte 5 + Vite Frontend SPA Summary

Svelte 5 + Vite 6 + TypeScript SPA with schema-driven form (D-13) consuming the 4 Plan 15-A FastAPI endpoints. 25 new files under `tools/arrconf-ui/web/`. `npm run build` produces 61.7 KB JS + 8 KB CSS bundle served by FastAPI StaticFiles. Inline help tooltips (D-14) surface 40+ pydantic Field descriptions. SuggestArr coupling badge (D-09) on 7 fields. Save flow: POST /api/diff → DiffPanel → PUT /api/config → SaveToast or 422 ValidationBanner.

**Operator UAT: PENDING** — Task 5 requires browser interaction the executor cannot perform. See `15-HUMAN-UAT.md`.

## Files Created (25 new + 1 README updated)

### Scaffold (config files)

| File | Lines | Purpose |
|------|-------|---------|
| `tools/arrconf-ui/web/package.json` | 21 | Svelte 5, vite@6, typescript@5, svelte-check@4 |
| `tools/arrconf-ui/web/vite.config.ts` | 21 | Dev proxy /api → 127.0.0.1:8765; build outDir dist/ |
| `tools/arrconf-ui/web/tsconfig.json` | 18 | ES2022, strict, bundler moduleResolution |
| `tools/arrconf-ui/web/svelte.config.js` | 9 | runes: true (Svelte 5 runes mode) |
| `tools/arrconf-ui/web/index.html` | 12 | Entry: `<div id="app">` + module script |
| `tools/arrconf-ui/web/.gitignore` | 4 | node_modules/, dist/ |

### TS source modules

| File | Lines | Purpose |
|------|-------|---------|
| `src/main.ts` | 12 | Svelte 5 `mount(App, { target })` |
| `src/app.css` | 89 | CSS custom properties (5-color palette, spacing, typography per UI-SPEC) |
| `src/types.ts` | 70 | MediaCategory, ConfigPayload, JsonSchemaNode, RootSchema, PydanticErrorEntry, SemanticDiff, SaveStatus |
| `src/api.ts` | 56 | getConfig, getSchema, putConfig, postDiff — typed fetch wrappers with ApiError class |
| `src/schema.ts` | 55 | resolveNode ($ref), pickAnyOf (anyOf/null), effectiveNode — JSON Schema walker |
| `src/constants.ts` | 37 | 7 SuggestArr-coupled paths (D-09), APP_SECTIONS order |

### Svelte components (11 in lib/ + App.svelte root)

| Component | Lines | Surface | Purpose |
|-----------|-------|---------|---------|
| `src/App.svelte` | 153 | Root | onMount loads schema+config; openDiffPanel/confirmSave/cancelDiffPanel orchestration |
| `src/lib/HeaderBar.svelte` | 65 | 1 | Sticky header, Save config button, unsaved-changes chip |
| `src/lib/CategoriesEditor.svelte` | 130 | 2 | Categories table + inline Add form |
| `src/lib/CategoryRow.svelte` | 107 | 2 | Editable row, ↑↓✕ buttons, SuggestArrBadge for films-zoe |
| `src/lib/AppSection.svelte` | 107 | 3 | Collapsible `<details>` per app, walks schema.additionalProperties → FieldInput |
| `src/lib/FieldInput.svelte` | 199 | 3 | **D-13 schema-driven dispatcher** — 6 branches + self-recursive + effectiveNode |
| `src/lib/HelpTooltip.svelte` | 27 | — | D-14: `ⓘ` icon with native title attr for pydantic descriptions |
| `src/lib/SuggestArrBadge.svelte` | 45 | 5 | D-09: `↗ SuggestArr` badge on 7 coupled fields |
| `src/lib/DiffPanel.svelte` | 84 | 6 | Diff preview dialog (role=dialog), Confirm & Save / Keep editing |
| `src/lib/SaveToast.svelte` | 46 | 7 | Fixed bottom-right toast, auto-dismiss 4s, role=status |
| `src/lib/ValidationBanner.svelte` | 42 | 4 | Red top-of-page banner for 422 errors, role=alert |
| `src/lib/Spinner.svelte` | 34 | 8 | CSS-only loading spinner |

**Total frontend source: 1,443 lines**

## npm run build Output

```
vite v6.4.2 building for production...
transforming...
✓ 134 modules transformed.
dist/index.html                  0.40 kB │ gzip:  0.27 kB
dist/assets/index-Ce3NtMnF.css   8.04 kB │ gzip:  2.01 kB
dist/assets/index-CK91dmY0.js   61.73 kB │ gzip: 22.49 kB
✓ built in 848ms
```

## Mechanical Pre-Checks

| Check | Result |
|-------|--------|
| `npm run check` (svelte-check) | 0 errors, 0 warnings |
| `npm run build` | exit 0 |
| `curl http://127.0.0.1:8765/` HTTP status | 200 |
| `<div id="app">` in served HTML | PRESENT |
| GET /api/schema — $defs count | 40 |
| GET /api/config — categories count | 10 |
| POST /api/diff — response shape | has_changes key present |
| D-11: arrconf.image.tag | 0.7.0 (unchanged) |
| Files modified outside web/ + README.md | 0 |

## D-11 Confirmation

```
grep "0.7.0" charts/arr-stack/values.yaml
            tag: "0.7.0"
```

`charts/arr-stack/values.yaml#arrconf.image.tag` = `"0.7.0"` — unchanged. Phase 15 is a sibling package; no arrconf image co-bump (D-11 explicit).

## Operator UAT Result

**✅ APPROVED** (opérateur 2026-05-23) — all 10 scenarios PASSED.

Scope expanded mid-UAT to include 3 post-original-scope improvements:
- **Scenario 10 added**: LAN-accessible binding (default `0.0.0.0:8765` per
  operator request, CONTEXT D-04 amended). `--host 127.0.0.1` override
  available + auto-detected LAN URL logged at startup.
- **Design refresh**: array-of-objects bug fixed (`[object Object]` → repeatable
  nested form), French i18n layer (54+ field tooltips + 7 section docs),
  dark theme with `data-theme` attribute + ThemeToggle, IBM Plex Sans/Mono
  typography. Driven by frontend-design skill ("architectural-blueprint"
  aesthetic).
- **Full FR strings**: every visible UI string in French, including all
  aria-labels, placeholders, button labels, error messages, toast copy,
  spinner default, diff panel headings and op markers.

See `15-HUMAN-UAT.md` for the 10 PASSED scenarios + `15-VERIFICATION.md`
for the full SC#1-7 compliance check.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `87d68dc` | feat(15-B) | Bootstrap Vite 6 + Svelte 5 + TS project scaffold |
| `362014d` | feat(15-B) | Schema-driven FieldInput + HelpTooltip + SuggestArrBadge + leaf primitives |
| `ae9b394` | feat(15-B) | Surface 1+2+3+6 components + App root + GET/POST/PUT orchestration |
| `f104e8c` | feat(15-B) | Build production dist + README Local config UI section |
| `1024d5c` | docs(15-B) | Initial SUMMARY + HUMAN-UAT (UAT pending) |
| `7ce43e1` | feat(15-B) | Bind 0.0.0.0 by default — LAN-accessible UI (D-04 amended) |
| `cd877cf` | feat(15-B) | UI design pass — array-of-objects fix + i18n FR + dark theme + IBM Plex |
| `48bdd56` | feat(15-B) | Full FR i18n pass — every visible string in French |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] vite version bumped to ^6.0.0**

- **Found during:** Task 1 — `npm install`
- **Issue:** `@sveltejs/vite-plugin-svelte@5.x` has `peerDependencies: { vite: "^6.0.0" }`. The plan specified `vite@^5.4.0` which conflicts.
- **Fix:** Updated `package.json` to `"vite": "^6.0.0"`.
- **Files modified:** `tools/arrconf-ui/web/package.json`
- **Commit:** `87d68dc`

**2. [Rule 1 - Bug] FieldInput self-import for recursive Svelte 5 component**

- **Found during:** Task 2 — `npm run check`
- **Issue:** Svelte 5 requires an explicit `import FieldInput from './FieldInput.svelte'` in the script block when a component references itself in the template. Without the import, TypeScript throws `Cannot find name 'FieldInput'`.
- **Fix:** Added `import FieldInput from './FieldInput.svelte'` to the script block.
- **Files modified:** `tools/arrconf-ui/web/src/lib/FieldInput.svelte`
- **Commit:** `362014d`

**3. [Rule 1 - Bug] SaveToast role=status moved to wrapper div**

- **Found during:** Task 2 — `npm run check`
- **Issue:** Svelte a11y lint: `<button>` cannot have `role="status"` (interactive element cannot have noninteractive role).
- **Fix:** Wrapped in `<div class="toast-wrap" role="status" aria-live="polite">` containing the `<button>`.
- **Files modified:** `tools/arrconf-ui/web/src/lib/SaveToast.svelte`
- **Commit:** `362014d`

**4. [Rule 1 - Bug] DiffPanel `<aside>` changed to `<div>` for role=dialog**

- **Found during:** Task 3 — `npm run check`
- **Issue:** Svelte a11y lint: non-interactive element `<aside>` cannot have interactive role `dialog`.
- **Fix:** Changed `<aside>` → `<div role="dialog" aria-modal="true">`.
- **Files modified:** `tools/arrconf-ui/web/src/lib/DiffPanel.svelte`
- **Commit:** `ae9b394`

**5. [Rule 1 - Bug] CategoriesEditor unused CSS `td` selector removed**

- **Found during:** Task 3 — `npm run check`
- **Issue:** `th, td` CSS selector in CategoriesEditor.svelte — the `td` part was unused (td styling lives in CategoryRow.svelte which is a separate component scope).
- **Fix:** Changed to `th` selector only with all required styles.
- **Files modified:** `tools/arrconf-ui/web/src/lib/CategoriesEditor.svelte`
- **Commit:** `ae9b394`

## Schema-Driven Coverage Check

```bash
grep -rn 'type="number"\|type="text"\|type="checkbox"' tools/arrconf-ui/web/src/lib/ \
  | grep -v FieldInput.svelte | grep -v CategoryRow.svelte | wc -l
# Result: 3
```

The 3 non-FieldInput inputs are all in `CategoriesEditor.svelte`'s `Add category` form — a hand-coded exception for Surface 2 (the add-row inline form, per D-08). All per-app section fields (sonarr/radarr/prowlarr/qbittorrent/seerr/jellyfin) flow exclusively through `FieldInput.svelte`. CategoryRow.svelte is the other hand-typed exception (categories table edit — also Surface 2 per plan).

## Known Stubs

None. All data flows from the live `charts/arr-stack/files/arrconf.yml` via the backend endpoints.

## Threat Flags

None new. All 8 STRIDE threats from the plan threat register are addressed:

| Threat | Status |
|--------|--------|
| T-15-B-01 (Spoofing) | Accept — loopback only per D-04 |
| T-15-B-02 (Tampering) | Mitigate — pydantic validation on PUT |
| T-15-B-03 (Info disclosure) | Accept — operator's own browser |
| T-15-B-04 (Elevation via dispatch) | Mitigate — schema types control dispatch, no eval/innerHTML, Svelte auto-escapes |
| T-15-B-05 (DoS) | Accept — single-tenant |
| T-15-B-06 (XSS via display field) | Mitigate — all strings via `{value}` (Svelte auto-escapes), no `{@html}` |
| T-15-B-07 (Badge tooltip info) | Accept — already in CONTEXT.md |
| T-15-B-08 (Race condition) | Accept — single-tenant, D-10 deferred |

## Hand-off Note

Phase 15 closes **v0.4.0** (4/4 phases done):

- Phase 12: Categories deprecation (flat sections removed, generators are sole source)
- Phase 13: SuggestArr architecture research (sidecar Helm, Option A — D-01 lock)
- Phase 14: SuggestArr implementation (sidecar chart + routing config + evidence)
- Phase 15: Local config UI (FastAPI backend + Svelte 5 frontend)

After operator UAT approval, update this file with the UAT result and close the phase.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| 24 frontend source files exist on disk | PASSED |
| 15-HUMAN-UAT.md created | PASSED |
| README.md `## Local config UI` section | PASSED |
| Commit 87d68dc exists | PASSED |
| Commit 362014d exists | PASSED |
| Commit ae9b394 exists | PASSED |
| Commit f104e8c exists | PASSED |
| D-11: arrconf.image.tag = 0.7.0 (unchanged) | PASSED |
| npm run build exits 0 | PASSED |
| npm run check exits 0 | PASSED |
| FastAPI serves dist/index.html (HTTP 200) | PASSED |
