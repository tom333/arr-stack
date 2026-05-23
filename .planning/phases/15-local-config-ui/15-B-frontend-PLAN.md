---
phase: 15-local-config-ui
plan: 15-B
type: execute
wave: 2
depends_on:
  - 15-A
files_modified:
  - tools/arrconf-ui/web/package.json
  - tools/arrconf-ui/web/tsconfig.json
  - tools/arrconf-ui/web/vite.config.ts
  - tools/arrconf-ui/web/index.html
  - tools/arrconf-ui/web/svelte.config.js
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
  - README.md
autonomous: false
requirements:
  - REQ-local-config-ui-frontend
  - REQ-local-config-ui-packaging
tags:
  - svelte
  - vite
  - typescript
  - frontend
  - ui

must_haves:
  truths:
    - "`cd tools/arrconf-ui/web && npm install && npm run build` exits 0 and produces `dist/index.html` + `dist/assets/*.{js,css}` (SC#1 packaging)."
    - "After build, `uv run arrconf-ui --no-browser` serves the SPA at http://127.0.0.1:8765/ (StaticFiles mount from 15-A picks up `web/dist/`) — `curl -s http://localhost:8765/` returns HTTP 200 with `<div id=\"app\">` in the body (SC#1)."
    - "On page load, the SPA fetches GET /api/schema (D-13 source of truth) AND GET /api/config (current state) — Network tab shows both requests, no other endpoint dependency for initial render."
    - "Categories editor (Surface 2) renders all categories from arrconf.yml in a table; ↑ ↓ buttons reorder; ✕ button shows inline confirm + deletes; 'Add category' inline form adds a new row (SC#3, D-08)."
    - "Per-app collapsible sections (Surface 3) render for sonarr/radarr/prowlarr/qbittorrent/seerr/jellyfin via the schema-driven FieldInput dispatcher (D-13) — NO hand-coded per-field UI in the codebase (SC#2)."
    - "Every form label with a non-empty schema description has an `(i)` HelpTooltip (D-14); hovering/focusing shows the pydantic Field(description=...) verbatim."
    - "The 7 SuggestArr-coupled fields per D-09 show the SuggestArr coupling badge with the tooltip text from CONTEXT D-09 verbatim (Surface 5)."
    - "Clicking 'Save config' opens the DiffPanel (Surface 6) BEFORE writing; 'Confirm & Save' triggers PUT /api/config; 'Keep editing' closes the panel without writing (SC#4)."
    - "PUT /api/config returning 422 surfaces the ValidationBanner (Surface 4) + per-field red borders + per-field error text from the pydantic `detail[].loc/msg` array (SC#5)."
    - "PUT /api/config returning 200 shows the SaveToast (Surface 7) 'Saved — run `git diff` to review, then push.' auto-dismissing after 4s (SC#6)."
    - "README.md gains a '## Local config UI' section with launch + workflow + dev mode instructions (SC#7)."
    - "ZERO modifications to `charts/arr-stack/values.yaml#arrconf.image.tag` (D-11)."
  artifacts:
    - path: tools/arrconf-ui/web/package.json
      provides: "Svelte 5 + Vite + TypeScript build config; `npm run build` produces `dist/`."
    - path: tools/arrconf-ui/web/vite.config.ts
      provides: "Vite build config + dev-server proxy `/api → http://127.0.0.1:8765` (Claude's Discretion — dev workflow)."
    - path: tools/arrconf-ui/web/src/App.svelte
      provides: "Root component holding $state for configState/savedConfig/validationErrors/saveStatus."
    - path: tools/arrconf-ui/web/src/lib/FieldInput.svelte
      provides: "Schema-driven widget dispatcher per D-13 — walks JSON Schema node, picks widget. THE load-bearing component."
    - path: tools/arrconf-ui/web/src/lib/HelpTooltip.svelte
      provides: "(i) icon next to every label that surfaces JSON Schema `description` as tooltip (D-14)."
    - path: tools/arrconf-ui/web/src/lib/SuggestArrBadge.svelte
      provides: "Inline badge on the 7 coupled fields from Phase 14 D-05/D-06/D-07 (D-09)."
    - path: tools/arrconf-ui/web/src/lib/CategoriesEditor.svelte
      provides: "Surface 2 — categories table + ↑ ↓ ✕ + inline add (D-08)."
    - path: tools/arrconf-ui/web/src/lib/AppSection.svelte
      provides: "Surface 3 — generic `<details>` wrapper, walks schema $defs and renders fields via FieldInput."
    - path: tools/arrconf-ui/web/src/lib/DiffPanel.svelte
      provides: "Surface 6 — semantic diff preview (renders D-07 structure from POST /api/diff or PUT response)."
    - path: tools/arrconf-ui/web/src/lib/SaveToast.svelte
      provides: "Surface 7 — fixed bottom-right toast, auto-dismiss 4s."
    - path: tools/arrconf-ui/web/src/lib/ValidationBanner.svelte
      provides: "Surface 4 — top-of-page error count + per-field error wiring (uses pydantic 422 `detail` array)."
    - path: tools/arrconf-ui/web/src/lib/HeaderBar.svelte
      provides: "Surface 1 — Save button, diff-count chip, file path label."
    - path: tools/arrconf-ui/web/src/lib/CategoryRow.svelte
      provides: "Single category row + ↑ ↓ ✕ actions with aria-labels."
    - path: tools/arrconf-ui/web/src/lib/Spinner.svelte
      provides: "Surface 8 — CSS-only loading state."
    - path: tools/arrconf-ui/web/src/api.ts
      provides: "Typed fetch wrappers for GET /api/config, PUT /api/config, GET /api/schema, POST /api/diff."
    - path: tools/arrconf-ui/web/src/schema.ts
      provides: "JSON Schema walker — resolves `$ref` against `$defs`, returns the effective node for FieldInput dispatch."
    - path: tools/arrconf-ui/web/src/constants.ts
      provides: "The 7 SuggestArr-coupled field paths from D-09 + the SuggestArr tooltip text — single source of truth for SuggestArrBadge."
    - path: README.md
      provides: "'Local config UI' section: launch + workflow + dev mode (SC#7)."
  key_links:
    - from: "tools/arrconf-ui/web/src/lib/FieldInput.svelte"
      to: "JSON Schema node (resolved)"
      via: "schema.type / schema.enum / schema.format / schema.$ref dispatch"
      pattern: "schema\\.(type|enum|format|properties|items)"
    - from: "tools/arrconf-ui/web/src/lib/SuggestArrBadge.svelte"
      to: "constants.SUGGESTARR_COUPLED_PATHS"
      via: "Set membership check by dotted path"
      pattern: "SUGGESTARR_COUPLED_PATHS"
    - from: "tools/arrconf-ui/web/src/App.svelte"
      to: "POST /api/diff via api.ts"
      via: "Diff preview before PUT"
      pattern: "api\\.postDiff|fetch.*api/diff"
    - from: "tools/arrconf-ui/web/src/App.svelte"
      to: "PUT /api/config via api.ts"
      via: "Save flow after diff confirm"
      pattern: "api\\.putConfig|fetch.*api/config"
    - from: "tools/arrconf-ui/web/vite.config.ts"
      to: "http://127.0.0.1:8765"
      via: "server.proxy['/api']"
      pattern: "127\\.0\\.0\\.1:8765"
---

<objective>
Build the Svelte 5 + Vite + TypeScript SPA that consumes the 4 endpoints shipped in Plan 15-A. Schema-driven form (D-13) — NO hand-coded per-field UI; FieldInput.svelte is a JSON-Schema walker that dispatches to typed widgets. Inline help tooltips (D-14) surface the 54 pydantic Field(description=...) strings. SuggestArr coupling badge (D-09) decorates the 7 Phase 14-coupled fields. Save flow: client computes preview diff via POST /api/diff → opens DiffPanel → operator confirms → PUT /api/config → success toast OR validation errors highlighted in-form.

Purpose: complete REQ-local-config-ui-frontend + close the Phase 15 packaging requirement (README update). After this plan, milestone v0.4.0 ships (4/4 phases done).

Output: 25 files under `tools/arrconf-ui/web/` + 1 README update. `npm run build` produces `tools/arrconf-ui/web/dist/` that Plan 15-A's FastAPI app picks up via StaticFiles mount. NO `arrconf.image.tag` co-bump (D-11). 1 checkpoint at end: operator verifies the live UI loads arrconf.yml + can edit a category + can save successfully.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/15-local-config-ui/15-CONTEXT.md
@.planning/phases/15-local-config-ui/15-UI-SPEC.md
@.planning/phases/15-local-config-ui/15-A-backend-PLAN.md
@.planning/phases/14-suggestarr-implementation/14-CONTEXT.md
@CLAUDE.md
@README.md
@tools/arrconf/arrconf/config.py
@schemas/arrconf-schema.json
@charts/arr-stack/files/arrconf.yml

<interfaces>
<!-- Plan 15-A's backend contract — copy-paste this section for downstream code. -->

Plan 15-A ships 4 endpoints on `http://127.0.0.1:8765`:

```typescript
// GET /api/config — current arrconf.yml validated as JSON
type ApiConfigResponse = {
  categories: MediaCategory[];
  sonarr: Record<string, SonarrInstance>;
  radarr: Record<string, RadarrInstance>;
  prowlarr: Record<string, ProwlarrInstance>;
  qbittorrent: Record<string, QbittorrentInstance>;
  seerr: Record<string, SeerrInstance>;
  jellyfin: Record<string, JellyfinInstance>;
};

// MediaCategory shape (the only typed object the UI hand-models; everything
// else flows through the JSON Schema walker)
type MediaCategory = {
  name: string;             // kebab-case slug, stable match key
  kind: "series" | "movies";
  profile: "general" | "anime" | "family";
  display: string;
  base_path: string;        // absolute path under /media
};

// GET /api/schema — JSON Schema (Draft 2020-12) — DRIVES THE ENTIRE UI per D-13
type ApiSchemaResponse = {
  $schema: string;
  $defs: Record<string, JsonSchemaNode>;
  properties: Record<string, JsonSchemaNode>;
  required?: string[];
};

type JsonSchemaNode = {
  type?: "string" | "integer" | "boolean" | "array" | "object" | "null";
  enum?: string[];
  format?: string;
  pattern?: string;
  minimum?: number;
  maximum?: number;
  description?: string;
  title?: string;
  default?: unknown;
  properties?: Record<string, JsonSchemaNode>;
  items?: JsonSchemaNode | JsonSchemaNode[];
  required?: string[];
  $ref?: string;            // "#/$defs/TypeName" — schema.ts resolves these
  anyOf?: JsonSchemaNode[];
  additionalProperties?: boolean | JsonSchemaNode;
};

// PUT /api/config — payload is the edited config; returns diff OR 422
// 200 response:
type ApiPutSuccessResponse = {
  diff: SemanticDiff;
  has_changes: boolean;
};
// 422 response (pydantic ValidationError):
type ApiPutErrorResponse = {
  detail: Array<{
    loc: (string | number)[];   // e.g., ["categories", 0, "kind"]
    msg: string;
    type: string;
    input?: unknown;
  }>;
};

// POST /api/diff — same payload as PUT, returns same 200 shape, NEVER writes
type ApiDiffResponse = ApiPutSuccessResponse;

type SemanticDiff = {
  categories: { added: string[]; modified: string[]; removed: string[] };
  // Plus per-instance keys like "sonarr.main", "radarr.main", ...
  [sectionKey: string]: { changed_fields: string[] } | SemanticDiff["categories"];
};
```

**The 7 SuggestArr-coupled field paths (D-09 — verbatim from CONTEXT.md):**

```typescript
// tools/arrconf-ui/web/src/constants.ts — SINGLE source of truth.
export const SUGGESTARR_COUPLED_PATHS: ReadonlySet<string> = new Set([
  "seerr.main.sonarr_service.activeAnimeProfileId",
  "seerr.main.sonarr_service.activeProfileId",
  "seerr.main.sonarr_service.activeAnimeDirectory",
  "seerr.main.sonarr_service.activeDirectory",
  "seerr.main.radarr_service.activeProfileId",
  "seerr.main.radarr_service.activeDirectory",
  // The 7th is path-shaped — categories[name="films-zoe"].base_path.
  // SuggestArrBadge handles this special case via name-match (see component).
]);

export const SUGGESTARR_COUPLED_CATEGORY_NAMES: ReadonlySet<string> = new Set([
  "films-zoe",   // base_path = D-07 fallback for anime_movie.rootFolder
]);

export const SUGGESTARR_TOOLTIP_TEXT =
  "Linked to SuggestArr's SEER_ANIME_PROFILE_CONFIG (Phase 14 D-05/D-06/D-07). " +
  "Changing this value requires re-pasting routing config in SuggestArr's web UI " +
  "per evidence/derived-routing-values.md.";
```

**Schema-driven dispatch rules (D-13):**

| Schema node | Widget rendered by FieldInput.svelte |
|---|---|
| `type: "string"` + `enum: [...]` | `<select>` with enum options |
| `type: "string"` (no enum) | `<input type="text">` (use `pattern` attr if present) |
| `type: "integer"` | `<input type="number" step="1">` (honor `minimum`/`maximum`) |
| `type: "boolean"` | `<input type="checkbox">` with inline label |
| `type: "array"` of objects | Repeatable list editor (rows with ↑ ↓ ✕) |
| `type: "array"` of primitives | Comma-separated text input (e.g., `tags: [2, 3]` → "2, 3") |
| `type: "object"` | Nested collapsible sub-section |
| `$ref: "#/$defs/X"` | Resolve via schema.ts, then dispatch on the resolved node |
| `anyOf: [...]` | Pick first non-null branch (Phase 15 simplification — sufficient for `string | None` cases) |

**Component decomposition (per UI-SPEC §"Component Inventory" — 11 components):**

1. `App.svelte` — root state + GET /api/schema + GET /api/config orchestration
2. `HeaderBar.svelte` — Surface 1
3. `CategoriesEditor.svelte` — Surface 2 wrapper
4. `CategoryRow.svelte` — Surface 2 row primitive
5. `AppSection.svelte` — Surface 3 wrapper (sonarr/radarr/...)
6. `FieldInput.svelte` — D-13 schema-driven dispatcher (LOAD-BEARING)
7. `HelpTooltip.svelte` — D-14 (i) icon + description popover
8. `SuggestArrBadge.svelte` — D-09 link badge
9. `DiffPanel.svelte` — Surface 6
10. `SaveToast.svelte` — Surface 7
11. `ValidationBanner.svelte` — Surface 4
12. `Spinner.svelte` — Surface 8 (12 total counting Spinner; 11 per UI-SPEC table that didn't list Spinner separately — both counts are accurate, just different framing)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Bootstrap Vite + Svelte 5 + TypeScript project + API client + schema walker + constants</name>
  <files>
    tools/arrconf-ui/web/package.json,
    tools/arrconf-ui/web/tsconfig.json,
    tools/arrconf-ui/web/vite.config.ts,
    tools/arrconf-ui/web/svelte.config.js,
    tools/arrconf-ui/web/index.html,
    tools/arrconf-ui/web/.gitignore,
    tools/arrconf-ui/web/src/main.ts,
    tools/arrconf-ui/web/src/app.css,
    tools/arrconf-ui/web/src/types.ts,
    tools/arrconf-ui/web/src/api.ts,
    tools/arrconf-ui/web/src/schema.ts,
    tools/arrconf-ui/web/src/constants.ts
  </files>
  <read_first>
    - .planning/phases/15-local-config-ui/15-CONTEXT.md (D-01 Svelte 5 vanilla + Vite + TypeScript; Claude's Discretion: hand-written types vs generated — Plan 15-B picks hand-written for narrow scope; CSS framework: vanilla Svelte scoped styles)
    - .planning/phases/15-local-config-ui/15-UI-SPEC.md (§"Design System" — vanilla Svelte scoped + Unicode icons + system-ui font; §"API Integration" — proxy `/api → http://127.0.0.1:8765`; §"Color" — 5-color palette CSS custom properties)
    - .planning/phases/15-local-config-ui/15-A-backend-PLAN.md (`<interfaces>` block — `app = create_app()` ASGI module-level + 4 endpoint contracts)
    - .planning/phases/14-suggestarr-implementation/14-CONTEXT.md (D-05/D-06/D-07 — the 7 SuggestArr-coupled field paths to hard-code in constants.ts)
    - schemas/arrconf-schema.json (the LIVE schema the UI consumes — confirm `$defs`, `properties`, `$ref` shape)
  </read_first>
  <action>
Bootstrap the Vite + Svelte 5 + TypeScript project under `tools/arrconf-ui/web/`. NO `npx create-svelte` / NO `npm create vite@latest` — hand-write the config files so they match exactly the Phase 15 constraints (Svelte 5 vanilla NOT SvelteKit, dev proxy to 127.0.0.1:8765, build output to `dist/`).

**1.1 — `tools/arrconf-ui/web/package.json`**:

```json
{
  "name": "arrconf-ui-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "check": "svelte-check --tsconfig ./tsconfig.json",
    "typecheck": "tsc --noEmit"
  },
  "devDependencies": {
    "@sveltejs/vite-plugin-svelte": "^5.0.0",
    "@tsconfig/svelte": "^5.0.0",
    "svelte": "^5.0.0",
    "svelte-check": "^4.0.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0"
  }
}
```

**1.2 — `tools/arrconf-ui/web/svelte.config.js`**:

```javascript
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
  preprocess: vitePreprocess(),
  compilerOptions: {
    // Svelte 5 runes mode — required for $state / $derived / $effect.
    runes: true,
  },
};
```

**1.3 — `tools/arrconf-ui/web/vite.config.ts`** (dev proxy targets 127.0.0.1:8765 — Plan 15-A's default port):

```typescript
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// Dev mode: vite serves on 5173, proxies /api/* to FastAPI on 127.0.0.1:8765.
// Production: `npm run build` emits dist/, served by FastAPI StaticFiles.
export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
```

**1.4 — `tools/arrconf-ui/web/tsconfig.json`**:

```json
{
  "extends": "@tsconfig/svelte/tsconfig.json",
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "allowSyntheticDefaultImports": true,
    "resolveJsonModule": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"]
  },
  "include": ["src/**/*.ts", "src/**/*.svelte"],
  "exclude": ["node_modules", "dist"]
}
```

**1.5 — `tools/arrconf-ui/web/index.html`**:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>arrconf editor</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

**1.6 — `tools/arrconf-ui/web/.gitignore`**:

```
node_modules/
dist/
.svelte-kit/
*.tsbuildinfo
```

**1.7 — `tools/arrconf-ui/web/src/main.ts`**:

```typescript
import { mount } from 'svelte';
import App from './App.svelte';
import './app.css';

const target = document.getElementById('app');
if (!target) {
  throw new Error('#app target element missing from index.html');
}

const app = mount(App, { target });

export default app;
```

**1.8 — `tools/arrconf-ui/web/src/app.css`** (UI-SPEC §"Color" + §"Spacing" + §"Typography" CSS custom properties):

```css
/* CSS custom properties per UI-SPEC §"Color" + §"Spacing" + §"Typography" */
:root {
  /* Spacing scale (4px base) */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
  --space-3xl: 64px;

  /* 5-color palette */
  --color-surface: #f8f9fa;
  --color-panel: #ffffff;
  --color-accent: #3b82f6;
  --color-destructive: #ef4444;
  --color-border: #e2e8f0;

  /* Derived */
  --color-accent-fg: #ffffff;
  --color-destructive-fg: #ffffff;
  --color-muted: #6b7280;
  --color-error-border: #ef4444;
  --color-error-bg: #fef2f2;
  --color-badge-bg: #eff6ff;
  --color-badge-fg: #1d4ed8;
  --color-row-alt: #f1f5f9;

  /* Typography */
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color: #111827;
  background: var(--color-surface);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 0;
}

/* Inherit body font in form elements */
input, select, textarea, button {
  font: inherit;
  color: inherit;
}

/* Focus ring (accessibility) */
:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* Default button reset */
button {
  cursor: pointer;
  border: 1px solid var(--color-border);
  background: var(--color-panel);
  border-radius: 4px;
  padding: var(--space-sm) var(--space-md);
}
button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Default input styling */
input[type="text"], input[type="number"], select, textarea {
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: var(--space-xs) var(--space-sm);
  background: var(--color-panel);
}
input.has-error, select.has-error {
  border-color: var(--color-error-border);
  background: var(--color-error-bg);
}

code {
  background: var(--color-surface);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 12px;
}
```

**1.9 — `tools/arrconf-ui/web/src/types.ts`** (mirror of the `<interfaces>` block above):

```typescript
// Single source of truth for TypeScript types consumed by Svelte components.
// MediaCategory is the only hand-typed shape (used by CategoriesEditor); every
// other section flows through the JSON Schema walker (D-13).

export type CategoryKind = "series" | "movies";
export type CategoryProfile = "general" | "anime" | "family";

export type MediaCategory = {
  name: string;
  kind: CategoryKind;
  profile: CategoryProfile;
  display: string;
  base_path: string;
};

export type ConfigPayload = {
  categories: MediaCategory[];
  sonarr: Record<string, unknown>;
  radarr: Record<string, unknown>;
  prowlarr: Record<string, unknown>;
  qbittorrent: Record<string, unknown>;
  seerr: Record<string, unknown>;
  jellyfin: Record<string, unknown>;
};

export type JsonSchemaNode = {
  type?: "string" | "integer" | "boolean" | "array" | "object" | "null";
  enum?: string[];
  format?: string;
  pattern?: string;
  minimum?: number;
  maximum?: number;
  description?: string;
  title?: string;
  default?: unknown;
  properties?: Record<string, JsonSchemaNode>;
  items?: JsonSchemaNode | JsonSchemaNode[];
  required?: string[];
  $ref?: string;
  anyOf?: JsonSchemaNode[];
  additionalProperties?: boolean | JsonSchemaNode;
};

export type RootSchema = {
  $schema: string;
  $defs: Record<string, JsonSchemaNode>;
  properties: Record<string, JsonSchemaNode>;
  required?: string[];
  title?: string;
};

export type PydanticErrorEntry = {
  loc: (string | number)[];
  msg: string;
  type: string;
  input?: unknown;
};

export type SemanticDiff = Record<
  string,
  | { added: string[]; modified: string[]; removed: string[] }
  | { changed_fields: string[] }
>;

export type DiffResponse = {
  diff: SemanticDiff;
  has_changes: boolean;
};

export type SaveStatus = "idle" | "saving" | "saved" | "error";
```

**1.10 — `tools/arrconf-ui/web/src/api.ts`** (typed fetch wrappers):

```typescript
import type {
  ConfigPayload,
  DiffResponse,
  PydanticErrorEntry,
  RootSchema,
} from './types';

const API_BASE = '/api';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: PydanticErrorEntry[] | string,
  ) {
    super(`API ${status}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`);
  }
}

async function _fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    let detail: PydanticErrorEntry[] | string;
    try {
      const body = await resp.json();
      detail = body.detail ?? body;
    } catch {
      detail = await resp.text();
    }
    throw new ApiError(resp.status, detail);
  }
  return (await resp.json()) as T;
}

export async function getConfig(): Promise<ConfigPayload> {
  return _fetchJson<ConfigPayload>(`${API_BASE}/config`);
}

export async function getSchema(): Promise<RootSchema> {
  return _fetchJson<RootSchema>(`${API_BASE}/schema`);
}

export async function putConfig(payload: ConfigPayload): Promise<DiffResponse> {
  return _fetchJson<DiffResponse>(`${API_BASE}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function postDiff(payload: ConfigPayload): Promise<DiffResponse> {
  return _fetchJson<DiffResponse>(`${API_BASE}/diff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
```

**1.11 — `tools/arrconf-ui/web/src/schema.ts`** (JSON Schema walker — resolves `$ref` against `$defs`):

```typescript
import type { JsonSchemaNode, RootSchema } from './types';

/**
 * Resolve a `$ref: "#/$defs/TypeName"` against the root schema's `$defs`.
 * Returns the referenced node, OR the input node unchanged if no $ref.
 *
 * Implementation note: ref strings are always the simple
 * "#/$defs/TypeName" shape pydantic emits (no nested refs, no JSON Pointer
 * escapes beyond the leaf segment). If pydantic ever emits more complex
 * refs (e.g., "#/$defs/TypeName/properties/foo"), extend here.
 */
export function resolveNode(node: JsonSchemaNode, root: RootSchema): JsonSchemaNode {
  if (!node.$ref) {
    return node;
  }
  const match = node.$ref.match(/^#\/\$defs\/(.+)$/);
  if (!match) {
    console.warn('Unrecognized $ref shape:', node.$ref);
    return node;
  }
  const defName = match[1];
  const resolved = root.$defs?.[defName];
  if (!resolved) {
    console.warn('$ref target missing in $defs:', defName);
    return node;
  }
  return resolved;
}

/**
 * Pick the first non-null branch from an `anyOf` array. Phase 15
 * simplification — covers the `string | None` pattern that pydantic emits
 * for Optional[str] fields (the common case). If a future model uses a
 * more complex union, this will need to be extended.
 */
export function pickAnyOf(node: JsonSchemaNode): JsonSchemaNode {
  if (!node.anyOf || node.anyOf.length === 0) {
    return node;
  }
  const nonNull = node.anyOf.find((b) => b.type !== 'null');
  return nonNull ?? node.anyOf[0];
}

/**
 * Walk a top-level schema property by name and return the effective node
 * (refs resolved, anyOf narrowed).
 */
export function effectiveNode(node: JsonSchemaNode, root: RootSchema): JsonSchemaNode {
  let n = node;
  if (n.anyOf) {
    n = pickAnyOf(n);
  }
  n = resolveNode(n, root);
  return n;
}
```

**1.12 — `tools/arrconf-ui/web/src/constants.ts`** (SuggestArr coupling per D-09 — VERBATIM from CONTEXT):

```typescript
// Phase 14 D-05/D-06/D-07 — the 7 SuggestArr-coupled field paths (D-09).
// Surfaced in the UI via SuggestArrBadge.svelte as a visual hint (informational,
// not a guard — the field remains editable per D-09).

export const SUGGESTARR_COUPLED_PATHS: ReadonlySet<string> = new Set([
  "seerr.main.sonarr_service.activeAnimeProfileId",
  "seerr.main.sonarr_service.activeProfileId",
  "seerr.main.sonarr_service.activeAnimeDirectory",
  "seerr.main.sonarr_service.activeDirectory",
  "seerr.main.radarr_service.activeProfileId",
  "seerr.main.radarr_service.activeDirectory",
]);

// The 7th coupled "field" is path-shaped: categories[name="films-zoe"].base_path.
// CategoryRow.svelte checks this name against this Set to decide whether to
// render the SuggestArrBadge next to the base_path input.
export const SUGGESTARR_COUPLED_CATEGORY_NAMES: ReadonlySet<string> = new Set([
  "films-zoe",
]);

// VERBATIM from CONTEXT D-09:
export const SUGGESTARR_TOOLTIP_TEXT =
  "Linked to SuggestArr's SEER_ANIME_PROFILE_CONFIG (Phase 14 D-05/D-06/D-07). " +
  "Changing this value requires re-pasting routing config in SuggestArr's web UI " +
  "per evidence/derived-routing-values.md.";

// Order in which app sections appear in the UI (matches RootConfig declaration order).
export const APP_SECTIONS = [
  "sonarr",
  "radarr",
  "prowlarr",
  "qbittorrent",
  "seerr",
  "jellyfin",
] as const;

export type AppSectionName = typeof APP_SECTIONS[number];
```

**1.13 — Run install + type check to confirm scaffolding is sound:**

```bash
cd /data/projets/perso/arr-stack/tools/arrconf-ui/web
npm install
npm run typecheck   # tsc --noEmit — only validates .ts files; .svelte deferred to Task 2+
```
  </action>
  <verify>
    <automated>
cd /data/projets/perso/arr-stack/tools/arrconf-ui/web && npm install --silent && npm run typecheck && test -f node_modules/svelte/package.json && test -f src/api.ts && test -f src/schema.ts && test -f src/constants.ts && grep -q "SUGGESTARR_COUPLED_PATHS" src/constants.ts && grep -c "seerr.main.sonarr_service" src/constants.ts | grep -q "^4$" && grep -q "127.0.0.1:8765" vite.config.ts && grep -q '"runes": true' svelte.config.js
    </automated>
  </verify>
  <acceptance_criteria>
    - `npm install` completes without errors (svelte 5, vite 5, typescript 5 installed under node_modules/).
    - `npm run typecheck` exits 0 (all .ts files type-check).
    - `tools/arrconf-ui/web/vite.config.ts` references `http://127.0.0.1:8765` in the server.proxy section.
    - `tools/arrconf-ui/web/svelte.config.js` sets `compilerOptions.runes = true` (Svelte 5 runes mode).
    - `tools/arrconf-ui/web/src/constants.ts` contains all 4 `seerr.main.sonarr_service.*` paths (`grep -c "seerr.main.sonarr_service" src/constants.ts` ≥ 4).
    - `tools/arrconf-ui/web/src/constants.ts` contains both `radarr_service` paths (`grep -c "seerr.main.radarr_service" src/constants.ts` ≥ 2).
    - `tools/arrconf-ui/web/src/constants.ts` contains `films-zoe` in `SUGGESTARR_COUPLED_CATEGORY_NAMES`.
    - `tools/arrconf-ui/web/src/constants.ts` `SUGGESTARR_TOOLTIP_TEXT` matches verbatim the CONTEXT D-09 tooltip text (single line, includes "Phase 14 D-05/D-06/D-07" and "evidence/derived-routing-values.md").
    - `tools/arrconf-ui/web/.gitignore` lists `node_modules/` and `dist/`.
  </acceptance_criteria>
  <done>
    Vite + Svelte 5 + TS scaffold compiles; API client + schema walker + constants ready; dev proxy points at 127.0.0.1:8765.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Schema-driven FieldInput + HelpTooltip + SuggestArrBadge + leaf primitives (D-13 + D-14 + D-09)</name>
  <files>
    tools/arrconf-ui/web/src/lib/FieldInput.svelte,
    tools/arrconf-ui/web/src/lib/HelpTooltip.svelte,
    tools/arrconf-ui/web/src/lib/SuggestArrBadge.svelte,
    tools/arrconf-ui/web/src/lib/Spinner.svelte,
    tools/arrconf-ui/web/src/lib/SaveToast.svelte,
    tools/arrconf-ui/web/src/lib/ValidationBanner.svelte
  </files>
  <read_first>
    - .planning/phases/15-local-config-ui/15-CONTEXT.md (D-13 schema-driven dispatch table — the load-bearing rule; D-14 inline help via JSON Schema description; D-09 SuggestArr badge — 7 coupled fields)
    - .planning/phases/15-local-config-ui/15-UI-SPEC.md (§"Component Inventory" — FieldInput.svelte is THE schema-driven widget dispatcher; §5 SuggestArr coupling badge appearance; §4 Validation error display; §7 Save toast; §8 Empty/loading states)
    - tools/arrconf-ui/web/src/types.ts (JsonSchemaNode shape created Task 1)
    - tools/arrconf-ui/web/src/schema.ts (resolveNode + effectiveNode helpers)
    - tools/arrconf-ui/web/src/constants.ts (SUGGESTARR_COUPLED_PATHS + SUGGESTARR_TOOLTIP_TEXT)
  </read_first>
  <action>
**2.1 — `tools/arrconf-ui/web/src/lib/FieldInput.svelte`** (THE schema-driven widget dispatcher — D-13):

```svelte
<script lang="ts">
  import type { JsonSchemaNode, RootSchema } from '../types';
  import { effectiveNode } from '../schema';
  import HelpTooltip from './HelpTooltip.svelte';
  import SuggestArrBadge from './SuggestArrBadge.svelte';

  /**
   * D-13 schema-driven widget dispatcher.
   *
   * Walks a JSON Schema node and renders the right HTML widget.
   * NEVER hand-codes a per-field UI — every form input in the application
   * flows through this component.
   *
   * Dispatch rules (per CONTEXT D-13 + UI-SPEC §3):
   *   enum               → <select>
   *   integer            → <input type="number">  (min/max from schema)
   *   boolean            → <input type="checkbox">
   *   string + format    → <input type="text"> (pattern attr)
   *   string             → <input type="text">
   *   array primitives   → comma-separated text
   *   array of objects   → handled by parent (CategoriesEditor / AppSection sub-tables)
   *   object             → recursive nested form
   *   $ref / anyOf       → resolved via effectiveNode() helper
   */
  type Props = {
    schema: JsonSchemaNode;
    root: RootSchema;
    value: unknown;
    onChange: (next: unknown) => void;
    /** Dotted path like "seerr.main.sonarr_service.activeAnimeProfileId" — used by SuggestArrBadge. */
    path: string;
    /** Field label (e.g., "Active Anime Profile Id"). Defaults to the leaf segment of path. */
    label?: string;
    /** Pydantic 422 error message for this exact path, if any. */
    errorMsg?: string;
    /** Show label + help inline? Set false when the parent already rendered the label. */
    showLabel?: boolean;
  };

  let { schema, root, value, onChange, path, label, errorMsg, showLabel = true }: Props = $props();

  const effective = $derived(effectiveNode(schema, root));
  const leafLabel = $derived(label ?? path.split('.').pop()?.replace(/_/g, ' ') ?? path);
  const description = $derived(effective.description ?? '');
  const hasError = $derived(!!errorMsg);

  function handleStringInput(e: Event) {
    onChange((e.target as HTMLInputElement).value);
  }
  function handleNumberInput(e: Event) {
    const raw = (e.target as HTMLInputElement).value;
    onChange(raw === '' ? null : Number(raw));
  }
  function handleBoolInput(e: Event) {
    onChange((e.target as HTMLInputElement).checked);
  }
  function handleSelect(e: Event) {
    onChange((e.target as HTMLSelectElement).value);
  }
  function handleArrayInput(e: Event) {
    // Comma-separated text input for list[int] / list[str].
    const raw = (e.target as HTMLInputElement).value;
    const items = raw
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    // Try to coerce to numbers if the array items hint at numbers.
    const itemsSchema = Array.isArray(effective.items) ? effective.items[0] : effective.items;
    if (itemsSchema?.type === 'integer') {
      onChange(items.map((s) => Number(s)).filter((n) => !Number.isNaN(n)));
    } else {
      onChange(items);
    }
  }
</script>

{#if showLabel && effective.type !== 'object'}
  <label class="field-label" for={path}>
    {leafLabel}
    {#if description}
      <HelpTooltip text={description} />
    {/if}
    <SuggestArrBadge {path} />
  </label>
{/if}

{#if effective.enum}
  <select id={path} class:has-error={hasError} value={value as string} onchange={handleSelect}>
    {#each effective.enum as opt}
      <option value={opt}>{opt}</option>
    {/each}
  </select>
{:else if effective.type === 'integer'}
  <input
    id={path}
    type="number"
    step="1"
    min={effective.minimum}
    max={effective.maximum}
    class:has-error={hasError}
    value={value === null || value === undefined ? '' : (value as number)}
    oninput={handleNumberInput}
  />
{:else if effective.type === 'boolean'}
  <input
    id={path}
    type="checkbox"
    class:has-error={hasError}
    checked={!!value}
    onchange={handleBoolInput}
  />
{:else if effective.type === 'array'}
  <input
    id={path}
    type="text"
    class:has-error={hasError}
    placeholder="comma-separated (e.g., 2, 3)"
    value={Array.isArray(value) ? (value as unknown[]).join(', ') : ''}
    oninput={handleArrayInput}
  />
{:else if effective.type === 'string'}
  <input
    id={path}
    type="text"
    pattern={effective.pattern}
    class:has-error={hasError}
    value={(value ?? '') as string}
    oninput={handleStringInput}
  />
{:else if effective.type === 'object' && effective.properties}
  <fieldset class="nested-object">
    {#if showLabel}
      <legend>
        {leafLabel}
        {#if description}<HelpTooltip text={description} />{/if}
      </legend>
    {/if}
    {#each Object.entries(effective.properties) as [childKey, childSchema]}
      {@const childPath = `${path}.${childKey}`}
      {@const childValue = (value as Record<string, unknown> | null | undefined)?.[childKey]}
      <div class="field-row">
        <FieldInput
          schema={childSchema}
          {root}
          value={childValue}
          onChange={(next) => {
            const current = (value ?? {}) as Record<string, unknown>;
            onChange({ ...current, [childKey]: next });
          }}
          path={childPath}
        />
      </div>
    {/each}
  </fieldset>
{:else}
  <span class="unsupported">[Unsupported schema node: type={effective.type ?? '?'}]</span>
{/if}

{#if errorMsg}
  <div class="error-msg">Error: {errorMsg}</div>
{/if}

<style>
  .field-label {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
    font-size: 14px;
    margin-right: var(--space-sm);
  }
  .nested-object {
    border: 1px solid var(--color-border);
    border-radius: 4px;
    padding: var(--space-md);
    margin: var(--space-sm) 0;
    background: var(--color-panel);
  }
  .nested-object legend {
    padding: 0 var(--space-sm);
    font-weight: 600;
    font-size: 14px;
  }
  .field-row {
    display: flex;
    flex-direction: column;
    margin-bottom: var(--space-sm);
  }
  .error-msg {
    color: var(--color-destructive);
    font-size: 12px;
    margin-top: var(--space-xs);
  }
  .unsupported {
    color: var(--color-muted);
    font-style: italic;
    font-size: 12px;
  }
</style>
```

**2.2 — `tools/arrconf-ui/web/src/lib/HelpTooltip.svelte`** (D-14 inline help — `(i)` icon + native title for tooltip):

```svelte
<script lang="ts">
  // D-14 — surfaces pydantic Field(description=...) verbatim from JSON Schema.
  // Implementation: native `title` attribute on a small (i) span. Touch + focus
  // accessible (browsers handle title-on-focus + screen-reader announcement).
  // Empty descriptions: the parent component should not render this widget
  // (FieldInput.svelte guards via `{#if description}` block).

  type Props = { text: string };
  let { text }: Props = $props();
</script>

<span class="help-icon" title={text} aria-label={`Help: ${text}`}>ⓘ</span>

<style>
  .help-icon {
    display: inline-block;
    color: var(--color-muted);
    cursor: help;
    user-select: none;
    margin-left: var(--space-xs);
    font-size: 12px;
  }
  .help-icon:hover,
  .help-icon:focus-visible {
    color: var(--color-accent);
  }
</style>
```

**2.3 — `tools/arrconf-ui/web/src/lib/SuggestArrBadge.svelte`** (D-09 — checks path against the 7-path constant set):

```svelte
<script lang="ts">
  import {
    SUGGESTARR_COUPLED_PATHS,
    SUGGESTARR_COUPLED_CATEGORY_NAMES,
    SUGGESTARR_TOOLTIP_TEXT,
  } from '../constants';

  // D-09 — informational badge for 7 fields coupled to Phase 14 SuggestArr
  // routing config. Field remains editable; this is a visual hint only.

  type Props = {
    /** Dotted path of the field. */
    path: string;
    /** For categories[].base_path rendering: the category name (e.g., "films-zoe"). */
    categoryName?: string;
  };
  let { path, categoryName }: Props = $props();

  const isCoupled = $derived(
    SUGGESTARR_COUPLED_PATHS.has(path) ||
      (path.endsWith('.base_path') &&
        !!categoryName &&
        SUGGESTARR_COUPLED_CATEGORY_NAMES.has(categoryName)),
  );
</script>

{#if isCoupled}
  <span class="badge" title={SUGGESTARR_TOOLTIP_TEXT} aria-label={SUGGESTARR_TOOLTIP_TEXT}>
    ↗ SuggestArr
  </span>
{/if}

<style>
  .badge {
    display: inline-block;
    background: var(--color-badge-bg);
    color: var(--color-badge-fg);
    border-radius: 4px;
    font-size: 12px;
    padding: 2px 6px;
    margin-left: var(--space-xs);
    cursor: help;
    user-select: none;
  }
</style>
```

**2.4 — `tools/arrconf-ui/web/src/lib/Spinner.svelte`** (CSS-only loading state — Surface 8):

```svelte
<script lang="ts">
  type Props = { label?: string };
  let { label = 'Loading…' }: Props = $props();
</script>

<div class="spinner-wrap" role="status" aria-live="polite">
  <div class="spinner" aria-hidden="true"></div>
  <div class="spinner-label">{label}</div>
</div>

<style>
  .spinner-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-md);
    padding: var(--space-2xl);
  }
  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  .spinner-label {
    color: var(--color-muted);
    font-size: 14px;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
```

**2.5 — `tools/arrconf-ui/web/src/lib/SaveToast.svelte`** (Surface 7 — copy verbatim from UI-SPEC §"Copywriting Contract"):

```svelte
<script lang="ts">
  // UI-SPEC §7 — Save toast notification.
  // Copy: "Saved — run `git diff` to review, then push." (verbatim).
  // Auto-dismiss after 4s; click-to-dismiss.

  type Props = {
    onDismiss: () => void;
  };
  let { onDismiss }: Props = $props();

  $effect(() => {
    const t = setTimeout(onDismiss, 4000);
    return () => clearTimeout(t);
  });
</script>

<button
  type="button"
  class="toast"
  onclick={onDismiss}
  role="status"
  aria-live="polite"
>
  Saved — run <code>git diff</code> to review, then push.
</button>

<style>
  .toast {
    position: fixed;
    right: var(--space-lg);
    bottom: var(--space-lg);
    background: var(--color-panel);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--color-accent);
    border-radius: 6px;
    padding: 12px 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
    color: inherit;
    text-align: left;
    cursor: pointer;
    font-size: 14px;
    z-index: 1000;
  }
</style>
```

**2.6 — `tools/arrconf-ui/web/src/lib/ValidationBanner.svelte`** (Surface 4 — copy verbatim):

```svelte
<script lang="ts">
  import type { PydanticErrorEntry } from '../types';

  type Props = {
    errors: PydanticErrorEntry[];
    onDismiss: () => void;
  };
  let { errors, onDismiss }: Props = $props();
</script>

{#if errors.length > 0}
  <div class="banner" role="alert">
    <span class="msg">
      {errors.length} validation error{errors.length === 1 ? '' : 's'} — fix the highlighted fields before saving.
    </span>
    <button type="button" class="dismiss" onclick={onDismiss} aria-label="Dismiss error banner">✕</button>
  </div>
{/if}

<style>
  .banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--color-error-bg);
    border-left: 4px solid var(--color-destructive);
    padding: var(--space-sm) var(--space-md);
    margin-bottom: var(--space-md);
    border-radius: 4px;
  }
  .msg {
    color: var(--color-destructive);
    font-size: 14px;
  }
  .dismiss {
    background: transparent;
    border: none;
    color: var(--color-destructive);
    cursor: pointer;
    padding: var(--space-xs);
  }
</style>
```
  </action>
  <verify>
    <automated>
cd /data/projets/perso/arr-stack/tools/arrconf-ui/web && npm run check && grep -c "effective.enum\|effective.type === 'integer'\|effective.type === 'boolean'\|effective.type === 'string'\|effective.type === 'array'\|effective.type === 'object'" src/lib/FieldInput.svelte | awk '$1 >= 6 {exit 0} {exit 1}' && grep -q "SUGGESTARR_COUPLED_PATHS" src/lib/SuggestArrBadge.svelte && grep -q "films-zoe\|SUGGESTARR_COUPLED_CATEGORY_NAMES" src/lib/SuggestArrBadge.svelte && grep -q "Saved — run" src/lib/SaveToast.svelte && grep -q "validation error" src/lib/ValidationBanner.svelte
    </automated>
  </verify>
  <acceptance_criteria>
    - `npm run check` (svelte-check) exits 0 — no TypeScript errors in any .svelte file.
    - `FieldInput.svelte` dispatches on 6 distinct schema shapes: `enum`, `type === 'integer'`, `type === 'boolean'`, `type === 'string'`, `type === 'array'`, `type === 'object'`. Grep proves ≥ 6 dispatch branches.
    - `FieldInput.svelte` recurses into itself for nested objects (the `<FieldInput .../>` call inside the `{#if effective.type === 'object'}` block).
    - `FieldInput.svelte` calls `HelpTooltip` (D-14 wiring) — verified by `grep -q "<HelpTooltip" src/lib/FieldInput.svelte`.
    - `FieldInput.svelte` calls `SuggestArrBadge` — verified by `grep -q "<SuggestArrBadge" src/lib/FieldInput.svelte`.
    - `SuggestArrBadge.svelte` imports from `../constants` and uses `SUGGESTARR_COUPLED_PATHS` + `SUGGESTARR_COUPLED_CATEGORY_NAMES` + `SUGGESTARR_TOOLTIP_TEXT`.
    - `SaveToast.svelte` copy contains "Saved — run" + `<code>git diff</code>` (verbatim UI-SPEC).
    - `ValidationBanner.svelte` copy contains "validation error" + "fix the highlighted fields before saving" (verbatim UI-SPEC).
  </acceptance_criteria>
  <done>
    Schema-driven dispatch primitive ready (D-13); inline help (D-14) wired; SuggestArr coupling badge (D-09) wired; Spinner, SaveToast, ValidationBanner complete.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Surface 1+2+3+6 components + App root + GET/POST/PUT orchestration</name>
  <files>
    tools/arrconf-ui/web/src/lib/HeaderBar.svelte,
    tools/arrconf-ui/web/src/lib/CategoriesEditor.svelte,
    tools/arrconf-ui/web/src/lib/CategoryRow.svelte,
    tools/arrconf-ui/web/src/lib/AppSection.svelte,
    tools/arrconf-ui/web/src/lib/DiffPanel.svelte,
    tools/arrconf-ui/web/src/App.svelte
  </files>
  <read_first>
    - .planning/phases/15-local-config-ui/15-UI-SPEC.md (Surfaces 1, 2, 3, 6 + §"Copywriting Contract" + §"Keyboard Accessibility" + §"State management" — App.svelte holds 4 $state runes)
    - .planning/phases/15-local-config-ui/15-CONTEXT.md (D-07 semantic diff shape + D-08 ↑↓✕ + inline confirm)
    - tools/arrconf-ui/web/src/lib/FieldInput.svelte (created Task 2 — consumed by AppSection)
    - tools/arrconf-ui/web/src/api.ts (created Task 1 — getConfig / getSchema / putConfig / postDiff)
    - tools/arrconf-ui/web/src/constants.ts (APP_SECTIONS order)
  </read_first>
  <action>
**3.1 — `tools/arrconf-ui/web/src/lib/HeaderBar.svelte`** (Surface 1):

```svelte
<script lang="ts">
  import type { SaveStatus } from '../types';

  type Props = {
    filePath: string;
    diffCount: number;
    saveStatus: SaveStatus;
    onSaveClick: () => void;
  };
  let { filePath, diffCount, saveStatus, onSaveClick }: Props = $props();

  const isDisabled = $derived(diffCount === 0 || saveStatus === 'saving');
  const buttonLabel = $derived(saveStatus === 'saving' ? 'Saving…' : 'Save config');
</script>

<header class="header">
  <div class="title-wrap">
    <h1 class="title">arrconf editor</h1>
    <code class="filepath">{filePath}</code>
  </div>
  <div class="actions">
    {#if diffCount > 0}
      <span class="diff-chip">
        {diffCount} unsaved change{diffCount === 1 ? '' : 's'}
      </span>
    {/if}
    <button type="button" class="save-btn" disabled={isDisabled} onclick={onSaveClick}>
      {buttonLabel}
    </button>
  </div>
</header>

<style>
  .header {
    position: sticky;
    top: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-md) var(--space-lg);
    background: var(--color-panel);
    border-bottom: 1px solid var(--color-border);
    z-index: 10;
  }
  .title-wrap { display: flex; flex-direction: column; gap: 2px; }
  .title { margin: 0; font-size: 20px; font-weight: 600; line-height: 1.2; }
  .filepath { color: var(--color-muted); font-size: 12px; }
  .actions { display: flex; align-items: center; gap: var(--space-sm); }
  .diff-chip {
    color: var(--color-muted);
    font-size: 12px;
  }
  .save-btn {
    background: var(--color-accent);
    color: var(--color-accent-fg);
    border: none;
    padding: var(--space-sm) var(--space-md);
    border-radius: 4px;
    font-size: 14px;
  }
  .save-btn:disabled {
    background: var(--color-accent);
    /* opacity rule from app.css applies */
  }
</style>
```

**3.2 — `tools/arrconf-ui/web/src/lib/CategoryRow.svelte`** (Surface 2 row):

```svelte
<script lang="ts">
  import type { MediaCategory } from '../types';
  import SuggestArrBadge from './SuggestArrBadge.svelte';

  type Props = {
    category: MediaCategory;
    index: number;
    total: number;
    onMoveUp: () => void;
    onMoveDown: () => void;
    onDelete: () => void;
    onChange: (next: MediaCategory) => void;
  };
  let { category, index, total, onMoveUp, onMoveDown, onDelete, onChange }: Props = $props();

  let confirmingDelete = $state(false);

  function handleField<K extends keyof MediaCategory>(key: K, value: MediaCategory[K]) {
    onChange({ ...category, [key]: value });
  }
</script>

<tr class:alt={index % 2 === 1}>
  <td>
    <input
      type="text"
      value={category.name}
      oninput={(e) => handleField('name', (e.target as HTMLInputElement).value)}
    />
  </td>
  <td>
    <select
      value={category.kind}
      onchange={(e) => handleField('kind', (e.target as HTMLSelectElement).value as MediaCategory['kind'])}
    >
      <option value="series">series</option>
      <option value="movies">movies</option>
    </select>
  </td>
  <td>
    <select
      value={category.profile}
      onchange={(e) => handleField('profile', (e.target as HTMLSelectElement).value as MediaCategory['profile'])}
    >
      <option value="general">general</option>
      <option value="anime">anime</option>
      <option value="family">family</option>
    </select>
  </td>
  <td>
    <input
      type="text"
      value={category.display}
      oninput={(e) => handleField('display', (e.target as HTMLInputElement).value)}
    />
  </td>
  <td>
    <input
      type="text"
      value={category.base_path}
      oninput={(e) => handleField('base_path', (e.target as HTMLInputElement).value)}
    />
    <SuggestArrBadge path={`categories[${index}].base_path`} categoryName={category.name} />
  </td>
  <td class="actions">
    {#if confirmingDelete}
      <button type="button" class="confirm-del" onclick={() => { confirmingDelete = false; onDelete(); }}>
        Confirm
      </button>
      <button type="button" onclick={() => (confirmingDelete = false)}>Keep row</button>
    {:else}
      <button
        type="button"
        disabled={index === 0}
        aria-label={`Move ${category.name} up`}
        onclick={onMoveUp}
      >↑</button>
      <button
        type="button"
        disabled={index === total - 1}
        aria-label={`Move ${category.name} down`}
        onclick={onMoveDown}
      >↓</button>
      <button
        type="button"
        class="delete-btn"
        aria-label={`Delete category ${category.name}`}
        onclick={() => (confirmingDelete = true)}
      >✕</button>
    {/if}
  </td>
</tr>

<style>
  tr.alt { background: var(--color-row-alt); }
  td { padding: var(--space-sm) var(--space-md); vertical-align: middle; }
  td input[type="text"], td select { width: 100%; }
  td.actions { display: flex; gap: var(--space-xs); align-items: center; }
  td.actions button {
    min-width: 32px;
    min-height: 32px;
    padding: var(--space-xs);
    color: var(--color-muted);
  }
  td.actions .delete-btn:hover { color: var(--color-destructive); }
  td.actions .confirm-del { background: var(--color-destructive); color: var(--color-destructive-fg); border: none; }
</style>
```

**3.3 — `tools/arrconf-ui/web/src/lib/CategoriesEditor.svelte`** (Surface 2):

```svelte
<script lang="ts">
  import type { MediaCategory } from '../types';
  import CategoryRow from './CategoryRow.svelte';

  type Props = {
    categories: MediaCategory[];
    onChange: (next: MediaCategory[]) => void;
  };
  let { categories, onChange }: Props = $props();

  let newRow = $state<MediaCategory>({
    name: '',
    kind: 'series',
    profile: 'general',
    display: '',
    base_path: '',
  });

  function moveUp(idx: number) {
    if (idx === 0) return;
    const next = [...categories];
    [next[idx - 1], next[idx]] = [next[idx], next[idx - 1]];
    onChange(next);
  }
  function moveDown(idx: number) {
    if (idx === categories.length - 1) return;
    const next = [...categories];
    [next[idx], next[idx + 1]] = [next[idx + 1], next[idx]];
    onChange(next);
  }
  function deleteRow(idx: number) {
    onChange(categories.filter((_, i) => i !== idx));
  }
  function updateRow(idx: number, updated: MediaCategory) {
    const next = [...categories];
    next[idx] = updated;
    onChange(next);
  }
  function addRow() {
    if (!newRow.name.trim()) return;
    onChange([...categories, { ...newRow }]);
    newRow = { name: '', kind: 'series', profile: 'general', display: '', base_path: '' };
  }
  function resetRow() {
    newRow = { name: '', kind: 'series', profile: 'general', display: '', base_path: '' };
  }
</script>

<section class="categories">
  <h2>Categories</h2>
  {#if categories.length === 0}
    <p class="empty">No categories defined. Use the form below to add one.</p>
  {:else}
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Kind</th>
          <th>Profile</th>
          <th>Display</th>
          <th>Base path</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {#each categories as cat, idx (cat.name)}
          <CategoryRow
            category={cat}
            index={idx}
            total={categories.length}
            onMoveUp={() => moveUp(idx)}
            onMoveDown={() => moveDown(idx)}
            onDelete={() => deleteRow(idx)}
            onChange={(updated) => updateRow(idx, updated)}
          />
        {/each}
      </tbody>
    </table>
  {/if}

  <form class="add-row" onsubmit={(e) => { e.preventDefault(); addRow(); }}>
    <h3>Add category</h3>
    <input
      type="text"
      placeholder="name (e.g., series-zoe)"
      bind:value={newRow.name}
      required
    />
    <select bind:value={newRow.kind}>
      <option value="series">series</option>
      <option value="movies">movies</option>
    </select>
    <select bind:value={newRow.profile}>
      <option value="general">general</option>
      <option value="anime">anime</option>
      <option value="family">family</option>
    </select>
    <input type="text" placeholder="display" bind:value={newRow.display} />
    <input type="text" placeholder="/media/..." bind:value={newRow.base_path} />
    <button type="submit" class="add-btn">Add</button>
    <button type="button" onclick={resetRow}>Reset</button>
  </form>
</section>

<style>
  .categories { padding: var(--space-lg); }
  h2 { font-size: 16px; font-weight: 600; margin: 0 0 var(--space-md) 0; }
  table { width: 100%; border-collapse: collapse; }
  th, td {
    text-align: left;
    border-bottom: 1px solid var(--color-border);
    padding: var(--space-sm) var(--space-md);
    font-size: 14px;
  }
  th { font-weight: 600; font-size: 12px; color: var(--color-muted); }
  .empty { color: var(--color-muted); padding: var(--space-md); }
  .add-row {
    display: grid;
    grid-template-columns: 1fr auto auto 1fr 1fr auto auto;
    gap: var(--space-sm);
    align-items: center;
    margin-top: var(--space-md);
    padding-top: var(--space-md);
    border-top: 1px solid var(--color-border);
  }
  .add-row h3 { grid-column: 1 / -1; font-size: 14px; font-weight: 600; margin: 0; }
  .add-btn { background: var(--color-accent); color: var(--color-accent-fg); border: none; }
</style>
```

**3.4 — `tools/arrconf-ui/web/src/lib/AppSection.svelte`** (Surface 3 — schema-driven per-app collapsible section):

```svelte
<script lang="ts">
  import type { JsonSchemaNode, PydanticErrorEntry, RootSchema } from '../types';
  import { effectiveNode } from '../schema';
  import FieldInput from './FieldInput.svelte';

  type Props = {
    sectionName: string;             // "sonarr", "radarr", ...
    sectionSchema: JsonSchemaNode;   // root.properties[sectionName]
    root: RootSchema;
    value: Record<string, unknown>;  // { main: { ... } } typically
    onChange: (next: Record<string, unknown>) => void;
    errors: PydanticErrorEntry[];
  };
  let { sectionName, sectionSchema, root, value, onChange, errors }: Props = $props();

  // Each app section is a dict of `{ instanceName: InstanceModel }`.
  // The schema is `additionalProperties: { $ref: "#/$defs/SonarrInstance" }`.
  // For Phase 15 single-instance convention (ADR-7), only "main" exists.
  const additional = $derived(
    typeof sectionSchema.additionalProperties === 'object' && sectionSchema.additionalProperties !== null
      ? effectiveNode(sectionSchema.additionalProperties, root)
      : null,
  );

  const instances = $derived(Object.entries(value ?? {}));
  const fieldCount = $derived(
    additional?.properties ? Object.keys(additional.properties).length : 0,
  );

  function errorForPath(path: string): string | undefined {
    const e = errors.find((err) => err.loc.join('.') === path);
    return e?.msg;
  }
</script>

<details class="app-section">
  <summary>
    <span class="section-title">{sectionName}</span>
    <span class="field-count">{fieldCount * instances.length} fields</span>
  </summary>
  <div class="section-body">
    {#each instances as [instanceKey, instanceValue]}
      <div class="instance">
        <span class="instance-chip">{instanceKey}</span>
        {#if additional?.properties}
          {#each Object.entries(additional.properties) as [fieldKey, fieldSchema]}
            {@const fieldPath = `${sectionName}.${instanceKey}.${fieldKey}`}
            {@const fieldValue = (instanceValue as Record<string, unknown> | null | undefined)?.[fieldKey]}
            <div class="field-row">
              <FieldInput
                schema={fieldSchema}
                {root}
                value={fieldValue}
                onChange={(next) => {
                  const currentInstance = (instanceValue ?? {}) as Record<string, unknown>;
                  onChange({
                    ...value,
                    [instanceKey]: { ...currentInstance, [fieldKey]: next },
                  });
                }}
                path={fieldPath}
                errorMsg={errorForPath(fieldPath)}
              />
            </div>
          {/each}
        {/if}
      </div>
    {/each}
  </div>
</details>

<style>
  .app-section {
    background: var(--color-panel);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    margin-bottom: var(--space-md);
  }
  summary {
    padding: var(--space-md) var(--space-lg);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: var(--space-md);
    font-size: 16px;
    font-weight: 600;
    list-style: revert;
  }
  .section-title { text-transform: lowercase; }
  .field-count { color: var(--color-muted); font-size: 12px; font-weight: 400; }
  .section-body { padding: var(--space-lg); }
  .instance { margin-bottom: var(--space-md); }
  .instance-chip {
    display: inline-block;
    background: var(--color-surface);
    color: var(--color-muted);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    margin-bottom: var(--space-sm);
  }
  .field-row {
    display: flex;
    flex-direction: column;
    margin-bottom: var(--space-sm);
  }
</style>
```

**3.5 — `tools/arrconf-ui/web/src/lib/DiffPanel.svelte`** (Surface 6):

```svelte
<script lang="ts">
  import type { SemanticDiff } from '../types';

  type Props = {
    diff: SemanticDiff;
    onConfirm: () => void;
    onCancel: () => void;
  };
  let { diff, onConfirm, onCancel }: Props = $props();

  const catChange = $derived(diff.categories as { added: string[]; modified: string[]; removed: string[] } | undefined);

  const changedSections = $derived(
    Object.entries(diff)
      .filter(([k, v]) => {
        if (k === 'categories') {
          const c = v as { added: string[]; modified: string[]; removed: string[] };
          return c.added.length + c.modified.length + c.removed.length > 0;
        }
        return (v as { changed_fields: string[] }).changed_fields.length > 0;
      }),
  );
</script>

<aside class="panel" role="dialog" aria-labelledby="diff-panel-heading">
  <h2 id="diff-panel-heading">Pending changes — review before saving</h2>

  {#if changedSections.length === 0}
    <p class="empty">No pending changes detected.</p>
  {/if}

  {#if catChange && (catChange.added.length || catChange.modified.length || catChange.removed.length)}
    <section>
      <h3>Categories</h3>
      <ul>
        {#each catChange.added as n}
          <li>+ added: <code>{n}</code></li>
        {/each}
        {#each catChange.modified as n}
          <li>~ modified: <code>{n}</code></li>
        {/each}
        {#each catChange.removed as n}
          <li>- removed: <code>{n}</code></li>
        {/each}
      </ul>
    </section>
  {/if}

  {#each changedSections.filter(([k]) => k !== 'categories') as [sectionKey, sectionDiff]}
    {@const fields = (sectionDiff as { changed_fields: string[] }).changed_fields}
    {#if fields.length > 0}
      <section>
        <h3>{sectionKey}</h3>
        <ul>
          {#each fields as path}
            <li>~ <code>{path}</code></li>
          {/each}
        </ul>
      </section>
    {/if}
  {/each}

  <div class="actions">
    <button type="button" class="confirm-btn" onclick={onConfirm}>Confirm & Save</button>
    <button type="button" onclick={onCancel}>Keep editing</button>
  </div>
</aside>

<style>
  .panel {
    background: var(--color-panel);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    padding: var(--space-lg);
    margin: var(--space-md) var(--space-lg);
  }
  h2 { font-size: 16px; font-weight: 600; margin: 0 0 var(--space-md) 0; }
  h3 { font-size: 14px; font-weight: 600; margin: var(--space-md) 0 var(--space-sm) 0; }
  ul { margin: 0; padding-left: var(--space-md); }
  li { padding: var(--space-xs) 0; font-size: 14px; }
  .empty { color: var(--color-muted); }
  .actions { display: flex; gap: var(--space-sm); margin-top: var(--space-md); }
  .confirm-btn { background: var(--color-accent); color: var(--color-accent-fg); border: none; }
</style>
```

**3.6 — `tools/arrconf-ui/web/src/App.svelte`** (root + orchestration):

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import type { ConfigPayload, MediaCategory, PydanticErrorEntry, RootSchema, SaveStatus, SemanticDiff } from './types';
  import { APP_SECTIONS } from './constants';
  import * as api from './api';
  import { ApiError } from './api';
  import HeaderBar from './lib/HeaderBar.svelte';
  import CategoriesEditor from './lib/CategoriesEditor.svelte';
  import AppSection from './lib/AppSection.svelte';
  import DiffPanel from './lib/DiffPanel.svelte';
  import SaveToast from './lib/SaveToast.svelte';
  import ValidationBanner from './lib/ValidationBanner.svelte';
  import Spinner from './lib/Spinner.svelte';

  // State (Svelte 5 runes per UI-SPEC).
  let schema = $state<RootSchema | null>(null);
  let configState = $state<ConfigPayload | null>(null);
  let savedConfig = $state<ConfigPayload | null>(null);
  let validationErrors = $state<PydanticErrorEntry[]>([]);
  let saveStatus = $state<SaveStatus>('idle');
  let loadError = $state<string | null>(null);

  // Diff panel + toast visibility.
  let showDiffPanel = $state(false);
  let pendingDiff = $state<SemanticDiff | null>(null);
  let showSaveToast = $state(false);

  // Derived: diff count for HeaderBar chip.
  const diffCount = $derived(() => {
    if (!configState || !savedConfig) return 0;
    return JSON.stringify(configState) === JSON.stringify(savedConfig) ? 0 : 1;
  });

  onMount(async () => {
    try {
      const [s, c] = await Promise.all([api.getSchema(), api.getConfig()]);
      schema = s;
      configState = c;
      savedConfig = JSON.parse(JSON.stringify(c));
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    }
  });

  function updateCategories(next: MediaCategory[]) {
    if (!configState) return;
    configState = { ...configState, categories: next };
  }

  function updateAppSection(name: string, next: Record<string, unknown>) {
    if (!configState) return;
    configState = { ...configState, [name]: next } as ConfigPayload;
  }

  async function openDiffPanel() {
    if (!configState) return;
    try {
      const resp = await api.postDiff(configState);
      pendingDiff = resp.diff;
      showDiffPanel = true;
    } catch (e) {
      console.error('diff preview failed', e);
      // Fall back to opening with an empty diff — operator still can confirm.
      pendingDiff = {} as SemanticDiff;
      showDiffPanel = true;
    }
  }

  async function confirmSave() {
    if (!configState) return;
    saveStatus = 'saving';
    showDiffPanel = false;
    try {
      const resp = await api.putConfig(configState);
      savedConfig = JSON.parse(JSON.stringify(configState));
      validationErrors = [];
      saveStatus = 'saved';
      showSaveToast = true;
      pendingDiff = resp.diff;
    } catch (e) {
      saveStatus = 'error';
      if (e instanceof ApiError && Array.isArray(e.detail)) {
        validationErrors = e.detail;
      } else {
        console.error('save failed', e);
      }
    }
  }

  function cancelDiffPanel() {
    showDiffPanel = false;
  }
</script>

<HeaderBar
  filePath="charts/arr-stack/files/arrconf.yml"
  diffCount={diffCount()}
  {saveStatus}
  onSaveClick={openDiffPanel}
/>

{#if loadError}
  <div class="load-error" role="alert">
    Could not load arrconf.yml — {loadError}. Check the file path and try again.
  </div>
{:else if !configState || !schema}
  <Spinner label="Loading arrconf.yml…" />
{:else}
  <main class="page">
    <ValidationBanner errors={validationErrors} onDismiss={() => (validationErrors = [])} />

    {#if showDiffPanel && pendingDiff}
      <DiffPanel diff={pendingDiff} onConfirm={confirmSave} onCancel={cancelDiffPanel} />
    {/if}

    <CategoriesEditor categories={configState.categories} onChange={updateCategories} />

    {#each APP_SECTIONS as sectionName}
      {@const sectionSchema = schema.properties[sectionName]}
      {#if sectionSchema}
        <AppSection
          {sectionName}
          {sectionSchema}
          root={schema}
          value={configState[sectionName] as Record<string, unknown>}
          onChange={(next) => updateAppSection(sectionName, next)}
          errors={validationErrors}
        />
      {/if}
    {/each}
  </main>
{/if}

{#if showSaveToast}
  <SaveToast onDismiss={() => (showSaveToast = false)} />
{/if}

<style>
  .page {
    max-width: 960px;
    margin: var(--space-lg) auto;
    padding: 0 var(--space-lg);
  }
  .load-error {
    margin: var(--space-lg);
    padding: var(--space-md);
    background: var(--color-error-bg);
    border-left: 4px solid var(--color-destructive);
    border-radius: 4px;
    color: var(--color-destructive);
  }
</style>
```
  </action>
  <verify>
    <automated>
cd /data/projets/perso/arr-stack/tools/arrconf-ui/web && npm run check && grep -q "APP_SECTIONS" src/App.svelte && grep -q "<CategoriesEditor" src/App.svelte && grep -q "<AppSection" src/App.svelte && grep -q "<DiffPanel" src/App.svelte && grep -q "<SaveToast" src/App.svelte && grep -q "<ValidationBanner" src/App.svelte && grep -q "<HeaderBar" src/App.svelte && grep -q "<Spinner" src/App.svelte && grep -q "api.postDiff\|postDiff" src/App.svelte && grep -q "api.putConfig\|putConfig" src/App.svelte && grep -q "api.getConfig\|getConfig" src/App.svelte && grep -q "api.getSchema\|getSchema" src/App.svelte && ls src/lib/*.svelte | wc -l | awk '$1 >= 11 {exit 0} {exit 1}'
    </automated>
  </verify>
  <acceptance_criteria>
    - `npm run check` (svelte-check) exits 0 across all components.
    - `src/App.svelte` mounts all 8 child components (HeaderBar, CategoriesEditor, AppSection, DiffPanel, SaveToast, ValidationBanner, Spinner, FieldInput-via-AppSection).
    - `src/App.svelte` calls all 4 API endpoints (`getConfig`, `getSchema`, `postDiff`, `putConfig`).
    - `src/lib/` contains ≥ 11 .svelte components (HeaderBar, CategoriesEditor, CategoryRow, AppSection, FieldInput, HelpTooltip, SuggestArrBadge, DiffPanel, SaveToast, ValidationBanner, Spinner).
    - `CategoryRow.svelte` has `aria-label={`Move ${category.name} up/down`}` + `aria-label={`Delete category ${category.name}`}` per UI-SPEC §"Keyboard Accessibility".
    - `DiffPanel.svelte` has `role="dialog"` + `aria-labelledby="diff-panel-heading"`.
    - `ValidationBanner.svelte` has `role="alert"`.
    - `SaveToast.svelte` has `role="status"` + `aria-live="polite"`.
  </acceptance_criteria>
  <done>
    All 11 Svelte components present + wired through App.svelte. svelte-check is green. Schema-driven dispatch operates through FieldInput → AppSection.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 4: Build + integration smoke + README "Local config UI" section</name>
  <files>
    README.md
  </files>
  <read_first>
    - .planning/phases/15-local-config-ui/15-CONTEXT.md (D-12 launch UX + Claude's Discretion: README content as Plan 15-B deliverable)
    - .planning/phases/15-local-config-ui/15-UI-SPEC.md (§"API Integration" — dev workflow with Vite proxy)
    - README.md (existing README — current head + structure; "Local config UI" section is NEW)
  </read_first>
  <action>
**4.1 — Run the production build to confirm everything compiles:**

```bash
cd /data/projets/perso/arr-stack/tools/arrconf-ui/web
npm run build
ls -la dist/
```

The build MUST produce `dist/index.html` + `dist/assets/index-*.js` + `dist/assets/index-*.css`. Investigate any error before proceeding.

**4.2 — Smoke test: start backend + curl the served SPA:**

```bash
# Terminal A (background):
cd /data/projets/perso/arr-stack
uv run --directory tools/arrconf-ui arrconf-ui --no-browser &
ARRCONF_UI_PID=$!

# Wait for uvicorn to bind.
sleep 2

# Terminal B:
curl -s http://127.0.0.1:8765/ -o /tmp/served-spa.html
grep -q '<div id="app"></div>' /tmp/served-spa.html && echo OK_INDEX_SERVED || echo FAIL_INDEX
curl -s http://127.0.0.1:8765/api/schema | head -c 50
curl -s http://127.0.0.1:8765/api/config | python3 -c "import json,sys; data=json.load(sys.stdin); print('categories=', len(data['categories']))"

# Cleanup
kill $ARRCONF_UI_PID
```

If `OK_INDEX_SERVED` does NOT appear, check that the FastAPI app from Plan 15-A picked up `tools/arrconf-ui/web/dist/` via the StaticFiles mount. (15-A code: `if dist.exists(): app.mount("/", StaticFiles(...), name="ui")`.)

**4.3 — Add the "Local config UI" section to `README.md`.**

Read the current `README.md` head to find where the new section should go (insert after the "Vue d'ensemble" section, before "Architecture"). Use the Edit tool to insert verbatim:

```markdown
## Local config UI

Phase 15 (v0.4.0) ships a local web UI for editing `charts/arr-stack/files/arrconf.yml` from a browser. Single-tenant homelab tool — bound to `127.0.0.1` only, no auth.

### Launch

From the repo root:

```bash
cd tools/arrconf-ui
uv sync                          # one-time: installs FastAPI + uvicorn + arrconf (editable)
uv run arrconf-ui                # default port 8765, auto-opens browser
uv run arrconf-ui --port 9000    # alternate port
uv run arrconf-ui --no-browser   # headless (URL still printed to stdout)
```

Or override via env var: `ARRCONF_UI_PORT=9000 uv run arrconf-ui`.

The UI loads `charts/arr-stack/files/arrconf.yml`, renders a schema-driven typed form (Categories table + per-app collapsible sections for sonarr/radarr/prowlarr/qbittorrent/seerr/jellyfin), shows a semantic diff preview on Save, validates via pydantic on Save (422 errors highlighted in-form), and writes the file back via ruyaml round-trip (comments + blank lines + key ordering preserved). No git automation — Save shows a toast "Saved — run `git diff` to review, then push."

### Workflow

1. `uv run arrconf-ui` from `tools/arrconf-ui/`.
2. Edit Categories / per-app fields in the browser.
3. Click **Save config** → review the diff preview → **Confirm & Save**.
4. In the terminal: `git diff charts/arr-stack/files/arrconf.yml` to review.
5. `git add` / `git commit` / `git push` manually.

### Dev mode (frontend hot reload)

If you're modifying the frontend (`tools/arrconf-ui/web/src/`), run the FastAPI backend AND Vite dev server in parallel:

```bash
# Terminal A — backend on 127.0.0.1:8765
cd tools/arrconf-ui
uv run arrconf-ui --no-browser

# Terminal B — Vite dev server on 127.0.0.1:5173 (proxies /api/* → 8765)
cd tools/arrconf-ui/web
npm install
npm run dev
```

Open `http://localhost:5173/` for the hot-reloading dev UI.

### Building the static bundle

```bash
cd tools/arrconf-ui/web
npm install
npm run build       # produces tools/arrconf-ui/web/dist/
```

After build, `arrconf-ui` auto-serves the bundle from FastAPI's `StaticFiles` mount at `/`.

### What's NOT in scope

- `configarr.yml` editor (deferred — REQ-config-ui-multi-config v0.5.x).
- Auto-commit / auto-push (deferred — REQ-config-ui-git-integration v0.5.x).
- Remote exposure / Ingress / Tailscale (single-tenant homelab; `127.0.0.1` only).
- Auth (single-operator localhost-only).

```

**4.4 — Final build re-verify after README:**

```bash
cd /data/projets/perso/arr-stack/tools/arrconf-ui/web && npm run check && npm run build
```
  </action>
  <verify>
    <automated>
cd /data/projets/perso/arr-stack/tools/arrconf-ui/web && npm run build && test -f dist/index.html && ls dist/assets/*.js dist/assets/*.css >/dev/null && grep -q '## Local config UI' /data/projets/perso/arr-stack/README.md && grep -q 'uv run arrconf-ui' /data/projets/perso/arr-stack/README.md && grep -q '127.0.0.1' /data/projets/perso/arr-stack/README.md && grep -q 'npm run dev' /data/projets/perso/arr-stack/README.md && grep -E "arrconf\.image\.tag:\s*0\.6\.7" /data/projets/perso/arr-stack/charts/arr-stack/values.yaml
    </automated>
  </verify>
  <acceptance_criteria>
    - `npm run build` exits 0 and produces `dist/index.html` + `dist/assets/index-*.js` + `dist/assets/index-*.css`.
    - `npm run check` (svelte-check) still passes after Task 3 changes.
    - `README.md` contains a `## Local config UI` section with launch instructions, dev mode, and "What's NOT in scope".
    - `charts/arr-stack/values.yaml` `arrconf.image.tag` is UNCHANGED from before Phase 15 started (D-11 enforcement — Phase 15 ships at the same image tag).
    - `tools/arrconf-ui/web/dist/` is in `.gitignore` (don't commit build artifacts).
    - Manual smoke test (curl HTTP 200 + `<div id="app">` present in served HTML + GET /api/config returns ≥ 1 category) succeeds.
  </acceptance_criteria>
  <done>
    Build produces dist/; FastAPI serves the SPA; README updated; D-11 (no arrconf.image.tag bump) confirmed.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 5: Operator smoke + UAT (browser interaction)</name>
  <what-built>
    Plan 15-B delivered the full Svelte 5 + Vite + TS frontend (25 files under `tools/arrconf-ui/web/`), wired through Plan 15-A's 4 endpoints. README updated. Schema-driven form (D-13), inline help (D-14), SuggestArr coupling badge on 7 fields (D-09), Categories editor with ↑↓✕ + inline confirm (D-08), semantic diff preview (D-07), pydantic 422 highlighting (D-06), atomic ruyaml write via PUT (D-05), 127.0.0.1 bind (D-04).
  </what-built>
  <how-to-verify>
    Open a terminal at the repo root:

    1. **Launch:** `cd tools/arrconf-ui && uv sync && cd web && npm install && npm run build && cd .. && uv run arrconf-ui`
       - Expected: browser auto-opens at `http://localhost:8765/`. Terminal prints `INFO: Local config UI ready at http://localhost:8765`.

    2. **Initial render check:**
       - Page title: `arrconf editor` (20px semibold).
       - File path below title: `charts/arr-stack/files/arrconf.yml` (12px muted).
       - **Save config** button disabled (opacity 0.4) — no pending changes yet.
       - Categories table renders 10 rows (series, series-emilie, series-thomas, series-garcons, series-zoe, films, nouveaux-films, films-enfants, films-animation-enfants, films-zoe).
       - 6 collapsible app sections below: sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin (collapsed by default).

    3. **Inline help tooltip (D-14) — open `sonarr` section:**
       - Expected: every form label has a `(i)` icon to its right.
       - Hover the `(i)` next to `Base Url` — tooltip shows "Sonarr base URL e.g. http://sonarr.svc:8989" verbatim from pydantic Field(description=...).

    4. **SuggestArr badge (D-09) — open `seerr` section, expand to `sonarr_service`:**
       - Expected: blue `↗ SuggestArr` badge next to:
         - `activeAnimeProfileId`
         - `activeProfileId`
         - `activeAnimeDirectory`
         - `activeDirectory`
       - Hover the badge: tooltip text matches CONTEXT D-09 verbatim ("Linked to SuggestArr's SEER_ANIME_PROFILE_CONFIG (Phase 14 D-05/D-06/D-07). Changing this value requires re-pasting routing config in SuggestArr's web UI per evidence/derived-routing-values.md.").
       - In `radarr_service`: badge on `activeProfileId` + `activeDirectory`.
       - In Categories table on the `films-zoe` row: badge next to the `base_path` input.

    5. **Categories edit + diff preview (D-07, D-08):**
       - Click ✕ on the last category row (`films-zoe`) — inline confirm shows up: `[Confirm] [Keep row]`. Click `Keep row` — row restored. Click ✕ again, click `Confirm` — row removed.
       - HeaderBar chip appears: `1 unsaved change`. Save button enabled (accent blue).
       - Click `↑` on the 5th row (`series-zoe`) — it moves up to 4th.
       - Use the inline `Add category` form at the bottom: name=`test-uat`, kind=series, profile=general, display=`Test UAT`, base_path=`/media/test-uat`. Click `Add` — new row appears at the bottom. Chip now `3 unsaved changes`.
       - Click **Save config** — DiffPanel slides in showing:
         - Categories section: `+ added: test-uat`, `- removed: films-zoe`, `~ modified: series-zoe` (reordered position only).
       - Click `Keep editing` — panel closes, no write.
       - Click **Save config** again, click `Confirm & Save` — toast appears bottom-right: `Saved — run git diff to review, then push.` Auto-dismisses after 4s.

    6. **Validation error path (D-06):**
       - Edit the seerr `activeAnimeProfileId` to a string like `"not_an_int"` (use browser DevTools to override the number input as text if needed, OR set it via the categories profile dropdown to an invalid enum value).
       - Click Save → Confirm & Save → expect **422** → red banner at top: `1 validation error — fix the highlighted fields before saving.` → red border + "Error: ..." text on the offending field.

    7. **File round-trip check (in terminal):**
       - `git diff charts/arr-stack/files/arrconf.yml` → should show:
         - `+ name: test-uat` block added (or whatever you added).
         - Comments preserved (Phase 6/7 D-XX comment blocks untouched).
         - First line still: `# yaml-language-server: $schema=...`.
       - Revert: `git checkout charts/arr-stack/files/arrconf.yml` (the canonical file should NOT be polluted by UAT).

    8. **Co-bump check (D-11):**
       - `grep "tag:" charts/arr-stack/values.yaml | head -5` — `arrconf.image.tag` should be **unchanged** (still `0.6.7` or whatever was current pre-Phase-15).

    9. **Shut down:** `Ctrl-C` in the terminal — uvicorn shuts down cleanly, no Python tracebacks.
  </how-to-verify>
  <resume-signal>
    Type "approved" if all 9 steps pass.
    Type a numbered list of failing steps (e.g., "4, 6 — SuggestArr badge missing on films-zoe; validation banner copy says 'errors' instead of 'error(s)'") if any step is wrong.
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser DOM ↔ user input | Free-form text input; UI relies on backend pydantic validation as final guard. |
| frontend → backend | Same-origin fetch on 127.0.0.1; relies on D-04 loopback bind. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-15-B-01 | S (Spoofing) | Browser fetch to /api/* | accept | Same-origin loopback; no remote callers possible per D-04 (Plan 15-A binds 127.0.0.1 only). |
| T-15-B-02 | T (Tampering) | Operator types arbitrary text in form | mitigate | Pydantic `RootConfig.model_validate` on backend rejects type mismatches with 422. Frontend client-side checks (D-06) are NON-AUTHORITATIVE per CONTEXT — backend is source of truth. |
| T-15-B-03 | I (Info disclosure) | Browser cache of arrconf.yml content | accept | Operator's own browser; single-tenant homelab. No PII in arrconf.yml; secrets live in sealed-secrets (out of scope). |
| T-15-B-04 | E (Elevation) | Schema-driven dispatch + arbitrary user input | mitigate | FieldInput dispatches by schema-controlled types (enum, int, bool, string, array, object) — no `eval` / no `innerHTML` / no template injection. Svelte auto-escapes interpolated text. |
| T-15-B-05 | D (DoS) | Operator pastes a huge string into a field | accept | Pydantic validation is O(field count); arrconf.yml is < 100 fields. Browser handles 10MB strings without issue. Frontend has no rate limit (single-tenant). |
| T-15-B-06 | T | XSS via category `display` field | mitigate | All operator-supplied strings are interpolated via Svelte `{value}` (auto-escapes HTML) — never via `{@html ...}`. svelte-check warns on unsafe HTML interpolation. |
| T-15-B-07 | I | SuggestArr badge tooltip leaks routing detail | accept | Information is already in CONTEXT.md D-09 (committed to git). Tooltip text is verbatim from that decision. |
| T-15-B-08 | T | Race: operator saves while another process modifies arrconf.yml | accept | Single-tenant + Phase 15 explicitly out-of-scope: "Hot reload of arrconf.yml" is deferred (CONTEXT D-10). Operator-discipline: don't edit in two places at once. |
</threat_model>

<verification>
**Phase 15-B close checks:**

1. `cd tools/arrconf-ui/web && npm install && npm run check && npm run build` exits 0.
2. `cd tools/arrconf-ui && uv run arrconf-ui --no-browser` starts server; `curl -s http://127.0.0.1:8765/` returns HTML containing `<div id="app">`.
3. `grep -c "FieldInput" tools/arrconf-ui/web/src/lib/AppSection.svelte` ≥ 1 (AppSection dispatches every field through FieldInput per D-13).
4. `grep -c "<HelpTooltip" tools/arrconf-ui/web/src/lib/FieldInput.svelte` ≥ 1 (D-14 wired into the schema-driven dispatcher).
5. `grep -c "<SuggestArrBadge" tools/arrconf-ui/web/src/lib/FieldInput.svelte` ≥ 1 (D-09 wired).
6. `grep -E "0\.6\.7|<unchanged>" charts/arr-stack/values.yaml | grep -c "arrconf"` confirms `arrconf.image.tag` not changed (D-11).
7. Operator UAT (Task 5) — 9 verification steps all pass.
</verification>

<success_criteria>
**Plan 15-B is complete when:**

- All 25 frontend files + 1 README update created.
- `npm run check` + `npm run build` both exit 0.
- The 11-component inventory from UI-SPEC §"Component Inventory" is fulfilled (HeaderBar, CategoriesEditor, CategoryRow, AppSection, FieldInput, HelpTooltip, SuggestArrBadge, DiffPanel, SaveToast, ValidationBanner, Spinner).
- FieldInput.svelte dispatches on ≥ 6 schema shapes (enum, integer, boolean, string, array, object) — verified by grep.
- The 7 Phase 14 SuggestArr-coupled field paths from D-09 are hard-coded VERBATIM in `constants.ts` (4 sonarr_service + 2 radarr_service + 1 categories[films-zoe].base_path).
- HelpTooltip.svelte is present + invoked from FieldInput (D-14 — surfaces 54 pydantic Field descriptions).
- Operator UAT (Task 5) passes all 9 steps with "approved" signal.
- ZERO changes to `charts/arr-stack/values.yaml#arrconf.image.tag` (D-11).
- README has a "Local config UI" section with launch + workflow + dev mode + out-of-scope items.
- All 12 must_haves.truths verified.
- All 8 STRIDE threats addressed.
</success_criteria>

<output>
After Task 5 approval, create `.planning/phases/15-local-config-ui/15-B-SUMMARY.md` capturing:

- All 26 files (25 new + 1 README updated) with line counts.
- `npm run build` output (size of dist/assets/*.js, *.css).
- Operator UAT result (which of the 9 steps passed; any deviations noted).
- Confirmation of D-11 (image tag unchanged) with a `git diff charts/arr-stack/values.yaml | head` excerpt.
- Hand-off note to milestone close: "Phase 15 closes v0.4.0 (4/4 phases done). Categories cleanup (12) + SuggestArr research (13) + SuggestArr impl (14) + Local config UI (15) all shipped."
- 11 Svelte component inventory checklist (each component → file path + line count).
- Schema-driven coverage check: `grep -rn "type=\"number\"\|type=\"text\"\|type=\"checkbox\"" tools/arrconf-ui/web/src/lib/ | grep -v FieldInput.svelte | wc -l` — should be ≈ 0 (only FieldInput and CategoryRow contain raw HTML inputs; CategoryRow is the one hand-typed exception for the Categories table per UI-SPEC Surface 2).
</output>
