# Phase 26: configarr-in-UI frontend - Pattern Map

**Mapped:** 2026-05-30
**Files analyzed:** 8 (6 modified + 2 supporting)
**Analogs found:** 8 / 8 — all files are extensions of existing code; no greenfield

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `web/src/App.svelte` | component (orchestrator) | request-response | self (current `App.svelte`) | exact — parametrize existing |
| `web/src/lib/FieldInput.svelte` | component (widget dispatcher) | transform | self (current `FieldInput.svelte`) | exact — extend Props + branch |
| `web/src/lib/HeaderBar.svelte` | component (chrome) | event-driven | self (current `HeaderBar.svelte`) | exact — add tab bar |
| `web/src/api.ts` | utility (HTTP client) | request-response | self (current `api.ts`) | exact — mirror 4 functions |
| `web/src/constants.ts` | config | — | self (current `constants.ts`) | exact — add export |
| `web/src/types.ts` | config | — | self (current `types.ts`) | exact — add `readOnly` field |
| `web/src/schema.ts` | utility (schema resolver) | transform | self (current `schema.ts`) | reused as-is |
| `web/src/i18n/fr.ts` | config (i18n) | — | self (current `fr.ts`) | exact — add keys |

---

## Pattern Assignments

### `web/src/App.svelte` (orchestrator, request-response)

**Analog:** self — current `App.svelte` (lines 1–156).

**Current state — what to parametrize:**
The existing file is hardwired to a single config. Every pattern below must be
replicated per active config, gated on which tab is selected.

**State rune pattern** (lines 17–34 — copy and extend):
```typescript
// Svelte 5 $state — add activeConfig and confirmSwitchOpen
let schema = $state<RootSchema | null>(null);
let configState = $state<ConfigPayload | null>(null);
let savedConfig = $state<ConfigPayload | null>(null);
let validationErrors = $state<PydanticErrorEntry[]>([]);
let saveStatus = $state<SaveStatus>('idle');
let loadError = $state<string | null>(null);
let showDiffPanel = $state(false);
let pendingDiff = $state<SemanticDiff | null>(null);
let showSaveToast = $state(false);

// NEW for Phase 26:
let activeConfig = $state<'arrconf' | 'configarr'>('arrconf');
let confirmSwitchOpen = $state(false);
let pendingSwitch = $state<'arrconf' | 'configarr' | null>(null);
```

**Derived dirty-state pattern** (lines 30–34 — reuse for switch gate):
```typescript
const diffCount = $derived(
  configState && savedConfig
    ? (JSON.stringify(configState) === JSON.stringify(savedConfig) ? 0 : 1)
    : 0
);
// diffCount > 0 gates the unsaved-switch confirm dialog (D-04).
```

**onMount load pattern** (lines 36–45 — parametrize by activeConfig):
```typescript
onMount(async () => {
  try {
    const [s, c] = await Promise.all([api.getSchema(), api.getConfig()]);
    schema = s;
    configState = c;
    savedConfig = JSON.parse(JSON.stringify(c)) as ConfigPayload;
  } catch (e) {
    loadError = e instanceof Error ? e.message : String(e);
  }
});
// For Phase 26: extract into a loadForConfig(cfg) async helper that calls
// either [api.getSchema(), api.getConfig()] or
// [api.getConfigarrSchema(), api.getConfigarrConfig()].
// Call from onMount for 'arrconf', and re-call on confirmed tab switch.
```

**Save pipeline pattern** (lines 57–94 — parametrize postDiff/putConfig):
```typescript
async function openDiffPanel() {
  if (!configState) return;
  try {
    const resp = await api.postDiff(configState);   // ← swap to api.postConfigarrDiff for configarr
    pendingDiff = resp.diff;
    showDiffPanel = true;
  } catch (e) {
    pendingDiff = {} as SemanticDiff;
    showDiffPanel = true;
  }
}

async function confirmSave() {
  if (!configState) return;
  saveStatus = 'saving';
  showDiffPanel = false;
  try {
    const resp = await api.putConfig(configState);  // ← swap to api.putConfigarrConfig for configarr
    savedConfig = JSON.parse(JSON.stringify(configState)) as ConfigPayload;
    validationErrors = [];
    saveStatus = 'saved';
    showSaveToast = true;
    pendingDiff = resp.diff;
  } catch (e) {
    saveStatus = 'error';
    if (e instanceof ApiError && Array.isArray(e.detail)) {
      validationErrors = e.detail as PydanticErrorEntry[];
    }
  }
}
```

**Template section-iteration pattern** (lines 121–135 — adapt for configarr):
```svelte
{#each APP_SECTIONS as sectionName}
  {@const sectionSchema = schema.properties[sectionName]}
  {#if sectionSchema}
    <SectionDoc section={sectionName} />
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
```
For configarr: replace `APP_SECTIONS` with `Object.keys(schema.properties)` (the
schema properties drive the section list — D-05, no `CategoriesEditor` block).
`CategoriesEditor` is arrconf-only; omit it entirely when `activeConfig === 'configarr'`.

**HeaderBar props pattern** (lines 97–102):
```svelte
<HeaderBar
  filePath="charts/arr-stack/files/arrconf.yml"
  {diffCount}
  {saveStatus}
  onSaveClick={openDiffPanel}
/>
```
For Phase 26: add `activeConfig` + `onTabChange` props to HeaderBar (see HeaderBar section below).

---

### `web/src/lib/FieldInput.svelte` (widget dispatcher, transform)

**Analog:** self — current `FieldInput.svelte` (lines 1–434).

**Props pattern** (lines 27–42 — add `readOnly`):
```typescript
type Props = {
  schema: JsonSchemaNode;
  root: RootSchema;
  value: unknown;
  onChange: (next: unknown) => void;
  path: string;
  label?: string;
  errorMsg?: string;
  showLabel?: boolean;
  // NEW for Phase 26 (D-02):
  readOnly?: boolean;
};
let { schema, root, value, onChange, path, label, errorMsg, showLabel = true, readOnly = false }: Props = $props();
```

**readOnly source — derive from schema node** (after line 44):
```typescript
const effective = $derived(effectiveNode(schema, root));
// NEW: honour schema-level readOnly (Phase 25 JSON Schema has readOnly: true on
// api_key, media_naming, quality_definition inside ArrInstance).
const isReadOnly = $derived(readOnly || (effective as { readOnly?: boolean }).readOnly === true);
```

**readOnly rendering pattern — disabled input + lock badge** (D-02):
For each widget branch (`select`, `input[type=number]`, `input[type=checkbox]`,
`input[type=text]`), add `disabled={isReadOnly}`. Add a lock badge after the
`<label>` when `isReadOnly`:
```svelte
{#if showLabel && effective.type !== 'object' && !isArrayOfObjects}
  <label class="field-label" for={path}>
    <span class="label-text">{leafLabel}</span>
    {#if description}<HelpTooltip text={description} />{/if}
    <SuggestArrBadge {path} />
    <!-- NEW: -->
    {#if isReadOnly}
      <span class="lock-badge" title="Géré par configarr/TRaSH — éditer le fichier directement">🔒</span>
    {/if}
  </label>
{/if}
```

**Thread readOnly through array-of-objects recursion** (lines 234–250 — the nested
`<FieldInput>` call inside the array-item-body must forward `readOnly`):
```svelte
<FieldInput
  schema={subSchema}
  {root}
  value={subValue}
  onChange={...}
  path={subPath}
  readOnly={isReadOnly}   <!-- NEW: thread through -->
/>
```

**Thread readOnly through object recursion** (lines 289–304):
```svelte
<FieldInput
  schema={childSchema}
  {root}
  value={childValue}
  onChange={...}
  path={childPath}
  readOnly={isReadOnly}   <!-- NEW: thread through -->
/>
```

**Lock badge CSS** (add to `<style>` block, following the `.array-count` pattern at lines 349–353):
```css
.lock-badge {
  font-size: 11px;
  opacity: 0.7;
  cursor: help;
  user-select: none;
}
/* Disabled inputs follow generic button:disabled pattern in app.css (opacity 0.5). */
```

**AppSection → FieldInput call site** (in `AppSection.svelte` lines 50–63):
`AppSection` calls `FieldInput` without a `readOnly` prop today. No change needed
there — `readOnly` is derived directly from `effective.readOnly` inside `FieldInput`
itself, so the schema node is the single source of truth.

---

### `web/src/lib/HeaderBar.svelte` (chrome component, event-driven)

**Analog:** self — current `HeaderBar.svelte` (lines 1–113).

**Props pattern** (lines 5–11 — add tab props):
```typescript
type Props = {
  filePath: string;
  diffCount: number;
  saveStatus: SaveStatus;
  onSaveClick: () => void;
  // NEW for Phase 26 (D-01):
  activeConfig?: 'arrconf' | 'configarr';
  onTabChange?: (next: 'arrconf' | 'configarr') => void;
};
let { filePath, diffCount, saveStatus, onSaveClick,
      activeConfig = 'arrconf', onTabChange }: Props = $props();
```

**Derived disabled pattern** (line 13 — unchanged):
```typescript
const isDisabled = $derived(diffCount === 0 || saveStatus === 'saving');
```

**Tab bar template pattern** — insert inside `.title-wrap` div, after `<code class="filepath">`:
```svelte
{#if onTabChange}
  <nav class="tab-bar" aria-label="Sélection du fichier de configuration">
    <button
      type="button"
      class="tab"
      class:tab-active={activeConfig === 'arrconf'}
      onclick={() => onTabChange('arrconf')}
    >arrconf.yml</button>
    <button
      type="button"
      class="tab"
      class:tab-active={activeConfig === 'configarr'}
      onclick={() => onTabChange('configarr')}
    >configarr.yml</button>
  </nav>
{/if}
```

**Tab bar CSS** — follow the `.diff-chip` / `.save-btn` token pattern (lines 88–112):
```css
.tab-bar {
  display: flex;
  gap: 2px;
  margin-top: var(--space-xs);
}
.tab {
  font-size: 12px;
  font-family: 'IBM Plex Mono', monospace;
  padding: 2px 10px;
  border-radius: 3px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--ink-muted);
  cursor: pointer;
}
.tab-active {
  background: var(--accent-soft);
  color: var(--accent);
  border-color: var(--accent);
  font-weight: 500;
}
```

---

### `web/src/api.ts` (HTTP utility, request-response)

**Analog:** self — current `api.ts` (lines 1–56). The four new functions are exact
mirrors of the existing four, pointing at `/api/configarr/*` endpoints.

**Existing function shape to mirror** (lines 34–56):
```typescript
// Pattern: single _fetchJson<T> call, typed return, same error contract.
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

**New functions to add** (copy shape, swap path + payload type):
```typescript
// configarr endpoints — Phase 26 (D-03)
// Payload type: use Record<string, unknown> (configarr has no TS-typed model yet).
export async function getConfigarrConfig(): Promise<Record<string, unknown>> {
  return _fetchJson<Record<string, unknown>>(`${API_BASE}/configarr/config`);
}
export async function getConfigarrSchema(): Promise<RootSchema> {
  return _fetchJson<RootSchema>(`${API_BASE}/configarr/schema`);
}
export async function putConfigarrConfig(payload: Record<string, unknown>): Promise<DiffResponse> {
  return _fetchJson<DiffResponse>(`${API_BASE}/configarr/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
export async function postConfigarrDiff(payload: Record<string, unknown>): Promise<DiffResponse> {
  return _fetchJson<DiffResponse>(`${API_BASE}/configarr/diff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
```

**`_fetchJson` and `ApiError`** (lines 10–32): unchanged — shared by all 8 functions.

---

### `web/src/types.ts` (type definitions)

**Analog:** self — current `types.ts` (lines 1–71).

**`JsonSchemaNode` extension** (lines 26–42 — add `readOnly`):
```typescript
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
  readOnly?: boolean;   // NEW — Phase 26 D-02; present in configarr schema ArrInstance
};
```

No other type changes needed. `ConfigPayload` remains arrconf-specific; configarr
uses `Record<string, unknown>` throughout (no TS model, consistent with `api.ts`
above).

---

### `web/src/constants.ts` (config)

**Analog:** self — current `constants.ts` (lines 28–37).

**Existing `APP_SECTIONS` pattern** (lines 28–37):
```typescript
export const APP_SECTIONS = [
  "sonarr", "radarr", "prowlarr", "qbittorrent", "seerr", "jellyfin",
] as const;
export type AppSectionName = typeof APP_SECTIONS[number];
```

**What to add for Phase 26** — file paths per config (used by HeaderBar):
```typescript
// Config file paths shown in HeaderBar (D-01)
export const CONFIG_FILE_PATHS = {
  arrconf: 'charts/arr-stack/files/arrconf.yml',
  configarr: 'charts/arr-stack/files/configarr.yml',
} as const;
export type ActiveConfig = keyof typeof CONFIG_FILE_PATHS;
```

The configarr section list is derived dynamically from `schema.properties` in
`App.svelte` (not a hardcoded constant), consistent with D-05 which says "configarr's
top-level keys drive the section list instead of `APP_SECTIONS`".

---

### `web/src/i18n/fr.ts` (i18n, config)

**Analog:** self — current `fr.ts` (lines 1–322).

**Key patterns to add** — follow the existing FIELD_LABELS / SECTION_DOCS / FIELD_DESCRIPTIONS structure:

**FIELD_LABELS additions** (after line 291, following the existing key pattern):
```typescript
// Phase 26 — configarr fields
trashGuideUrl: 'URL TRaSH Guide',
recyclarrConfigUrl: 'URL config Recyclarr',
customFormatDefinitions: 'Définitions custom formats',
quality_profiles: 'Quality profiles',
custom_formats: 'Custom formats',
quality_definition: 'Quality definition',
media_naming: 'Nommage média',
api_key: 'API key',
assign_scores_to: 'Assigner scores à',
score: 'Score',
```

**Lock tooltip text** (new constant, parallel to `SUGGESTARR_TOOLTIP_TEXT` pattern in `constants.ts`):
This is a tooltip string for the lock badge on readOnly fields. Define inline in
`FieldInput.svelte` as a literal or export from `fr.ts`:
```typescript
// Add to fr.ts or inline in FieldInput:
export const READONLY_TOOLTIP_TEXT =
  "Géré par configarr/TRaSH — ce champ est en lecture seule. Éditez le fichier directement.";
```

**Unsaved-switch dialog text** (add as a named export for the confirm dialog in `App.svelte`):
```typescript
export const UNSAVED_SWITCH_MESSAGE =
  "Des modifications non enregistrées seront perdues. Changer de fichier ?";
```

**SECTION_DOCS additions** (follow the existing multi-paragraph pattern, lines 28–73):
```typescript
// Example shape to follow:
configarr: {
  title: 'configarr — quality profiles et custom formats',
  body: `configarr applique les profils qualité et custom formats TRaSH-Guides sur Sonarr et Radarr. ...`
},
```

---

### `web/src/schema.ts` (schema resolver utility)

**Analog:** self — current `schema.ts` (lines 1–55).

**Reused as-is.** `effectiveNode()` (line 48) already handles `$ref` + `anyOf` — it
is called by `FieldInput.svelte` to resolve `ArrInstance` from
`additionalProperties.$ref`. No changes needed; the `readOnly` field on the
resolved node is read directly by `FieldInput` after `effectiveNode()` returns.

---

## Shared Patterns

### Svelte 5 runes style
**Source:** `App.svelte` lines 17–34, `FieldInput.svelte` line 42, `HeaderBar.svelte` line 11
**Apply to:** all `.svelte` modifications
```typescript
// $state for mutable reactive values
let foo = $state<Type>(initial);
// $derived for computed values (no side effects)
const bar = $derived(expression);
// $props() destructure for component props
let { propA, propB = default }: Props = $props();
```

### CSS design-token pattern
**Source:** `app.css` lines 17–80, `HeaderBar.svelte` lines 37–113
**Apply to:** all new CSS in modified components
- Spacing: `var(--space-xs/sm/md/lg/xl)`
- Colors: `var(--ink)`, `var(--ink-muted)`, `var(--accent)`, `var(--accent-soft)`, `var(--border)`
- Typography: `font-family: 'IBM Plex Mono', monospace` for IDs/paths/codes; IBM Plex Sans (default) for labels
- Never hardcode hex colors — always use tokens

### Error handling pattern
**Source:** `api.ts` lines 10–32, `App.svelte` lines 83–87
**Apply to:** `App.svelte` configarr load + save handlers
```typescript
// Throw ApiError on non-ok fetch; catch in App.svelte:
} catch (e) {
  if (e instanceof ApiError && Array.isArray(e.detail)) {
    validationErrors = e.detail as PydanticErrorEntry[];
  } else {
    console.error('operation failed', e);
  }
}
```

### Config-file-aware API dispatch pattern
**Apply to:** `App.svelte` — use a helper rather than inline conditionals:
```typescript
// Follow the existing Promise.all pattern (onMount lines 38-39),
// just dispatch by activeConfig:
async function loadForConfig(cfg: 'arrconf' | 'configarr') {
  if (cfg === 'arrconf') {
    return Promise.all([api.getSchema(), api.getConfig()]);
  } else {
    return Promise.all([api.getConfigarrSchema(), api.getConfigarrConfig()]);
  }
}
```

---

## No Analog Found

None — every file in this phase is a modification of an existing file. No greenfield
component or module is introduced. The only genuinely new code is:
- `readOnly` prop + lock badge in `FieldInput.svelte` (net-new branch in an existing dispatcher)
- Tab bar in `HeaderBar.svelte` (net-new HTML block in an existing component)
- 4 new functions in `api.ts` (copies of existing 4)

---

## configarr Schema Quick Reference

Extracted from `schemas/configarr-schema.json` for planner use:

**Top-level `properties` keys** (= configarr section list, replaces `APP_SECTIONS`):
- `trashGuideUrl` — string
- `recyclarrConfigUrl` — string
- `customFormatDefinitions` — array
- `sonarr` — `{ additionalProperties: { $ref: "#/$defs/ArrInstance" } }`
- `radarr` — same shape as `sonarr`

**`$defs.ArrInstance.properties`** (fields per arr instance):
- `api_key` — string, **`readOnly: true`**
- `base_url` — string
- `custom_formats` — array
- `media_naming` — object, **`readOnly: true`**
- `quality_definition` — object, **`readOnly: true`**
- `quality_profiles` — array (editable — this is the primary edit target)

`readOnly: true` fields must render as disabled + lock badge (D-02). They are present
on the ArrInstance `$defs` node, so `effectiveNode()` in `FieldInput` exposes them
after `$ref` resolution — no special-casing needed beyond reading `effective.readOnly`.

---

## Metadata

**Analog search scope:** `tools/arrconf-ui/web/src/` (all 22 files read)
**Files scanned:** 22
**Pattern extraction date:** 2026-05-30
