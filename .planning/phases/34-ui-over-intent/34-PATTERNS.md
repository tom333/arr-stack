# Phase 34: UI over intent - Pattern Map

**Mapped:** 2026-06-08
**Files analyzed:** 16 (8 backend + 8 frontend)
**Analogs found:** 16 / 16

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tools/arrconf-ui/arrconf_ui/locator.py` | utility | — | self (add 2 functions) | self-extension |
| `tools/arrconf-ui/arrconf_ui/app.py` | controller | request-response | self (add/remove endpoints) | self-extension |
| `tools/arrconf-ui/tests/conftest.py` | test/fixture | — | self | self-extension |
| `tools/arrconf-ui/tests/test_intent_endpoints.py` | test | request-response | `tests/test_app_endpoints.py` | exact |
| `tools/arrconf-ui/web/src/api.ts` | utility | request-response | self | self-extension |
| `tools/arrconf-ui/web/src/types.ts` | utility | — | self | self-extension |
| `tools/arrconf-ui/web/src/constants.ts` | utility | — | self | self-extension |
| `tools/arrconf-ui/web/src/i18n/fr.ts` | utility | — | self | self-extension |
| `tools/arrconf-ui/web/src/App.svelte` | component | request-response | self | self-extension |
| `tools/arrconf-ui/web/src/lib/HeaderBar.svelte` | component | event-driven | self | self-extension |
| `tools/arrconf-ui/web/src/lib/MaterializationDiffPanel.svelte` | component | request-response | `lib/DiffPanel.svelte` | exact |
| `tools/arrconf-ui/web/src/lib/ProfileDefinitionsEditor.svelte` | component | event-driven | `lib/CategoriesEditor.svelte` | role-match |
| `tools/arrconf-ui/web/src/lib/ProfileCard.svelte` | component | event-driven | `lib/TrashCFPicker.svelte` | role-match |
| `tools/arrconf-ui/web/src/lib/ConfigarrRawEditor.svelte` | component | event-driven | `lib/SectionDoc.svelte` + app.css | partial |
| `tools/arrconf-ui/web/src/lib/ReadOnlyInspector.svelte` | component | request-response | `lib/DiffPanel.svelte` (panel structure) | partial |

---

## Pattern Assignments

### `tools/arrconf-ui/arrconf_ui/locator.py` — add `intent_yml_path()` + `intent_schema_json_path()`

**Analog:** self (lines 1-54 — read already)

**Copy these two existing functions exactly as template** (lines 27-44):
```python
# tools/arrconf-ui/arrconf_ui/locator.py lines 27-44
def arrconf_yml_path() -> Path:
    """Return the canonical path to charts/arr-stack/files/arrconf.yml."""
    return repo_root() / "charts" / "arr-stack" / "files" / "arrconf.yml"


def configarr_yml_path() -> Path:
    """Return the canonical path to charts/arr-stack/files/configarr.yml."""
    return repo_root() / "charts" / "arr-stack" / "files" / "configarr.yml"
```

**New functions to add** (Pattern 4 from RESEARCH.md — verified paths):
```python
def intent_yml_path() -> Path:
    """Return the canonical path to charts/arr-stack/files/intent.yml."""
    return repo_root() / "charts" / "arr-stack" / "files" / "intent.yml"


def intent_schema_json_path() -> Path:
    """Return the canonical path to schemas/intent-schema.json."""
    return repo_root() / "schemas" / "intent-schema.json"
```

---

### `tools/arrconf-ui/arrconf_ui/app.py` — 4 new intent endpoints + remove 2 PUT endpoints

**Analog:** self

**Import pattern to extend** (lines 24-55):
```python
# Add to existing imports in app.py:
import difflib
import io as _io

from arrconf.intent_config import IntentConfig, load_intent
from arrconf.generators.intent import generate_arrconf_yml
from arrconf.generators.configarr import generate_configarr_yml
from arrconf_ui.locator import (
    arrconf_yml_path,
    configarr_schema_json_path,
    configarr_yml_path,
    intent_yml_path,      # NEW
    intent_schema_json_path,  # NEW
    repo_root,
    schema_json_path,
    trash_metadata_dir,
)
```

**GET endpoint pattern** — copy from existing `get_config` (lines 88-103):
```python
# tools/arrconf-ui/arrconf_ui/app.py lines 88-103
@app.get("/api/config")
def get_config() -> Any:
    """Return arrconf.yml parsed + validated as JSON (RootConfig.model_dump)."""
    raw = _read_current()
    try:
        validated = RootConfig.model_validate(raw)
    except ValidationError as e:
        detail = json.loads(json.dumps(e.errors(), default=str))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": detail, "raw": raw},
        )
    return validated.model_dump(mode="json")
```
New `GET /api/intent` follows this pattern — replace `_read_current()`/`RootConfig` with `load_intent(intent_yml_path())`/`IntentConfig`.

**POST diff endpoint pattern** — copy from existing `post_diff` (lines 153-162):
```python
# tools/arrconf-ui/arrconf_ui/app.py lines 153-162
@app.post("/api/diff")
def post_diff(payload: dict[str, Any]) -> Any:
    """Stateless preview: return diff between payload and on-disk arrconf.yml."""
    before = _read_current()
    diff = diff_configs(before, payload)
    return {"diff": diff, "has_changes": has_changes(diff)}
```
New `POST /api/intent/diff` follows this pattern but calls `generate_arrconf_yml` + `generate_configarr_yml` + `difflib.unified_diff` instead (see RESEARCH.md Pattern 2 for exact implementation).

**PUT save endpoint pattern** — copy from existing `put_config` (lines 105-151):
```python
# tools/arrconf-ui/arrconf_ui/app.py lines 105-151 (key structure)
@app.put("/api/config")
def put_config(payload: dict[str, Any]) -> Any:
    try:
        RootConfig.model_validate(payload)
    except ValidationError as e:
        detail = json.loads(json.dumps(e.errors(), default=str))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": detail},
        )
    # ... write + log ...
    log.info("config_saved", ...)
    return {"diff": diff, "has_changes": has_changes(diff)}
```
New `PUT /api/intent` validates via `IntentConfig.model_validate`, writes intent.yml (YAML safe, NOT write_yaml_atomic with rt-mode), then calls `generate_arrconf_yml`/`generate_configarr_yml` and writes both files. See RESEARCH.md Pitfall 1+4 for write mechanics.

**GET schema pattern** — copy from existing `get_schema` (lines 164-174):
```python
# tools/arrconf-ui/arrconf_ui/app.py lines 164-174
@app.get("/api/schema")
def get_schema() -> Any:
    path = schema_json_path()
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema file not found at {path}",
        )
    return json.loads(path.read_text(encoding="utf-8"))
```
New `GET /api/intent/schema` follows the same pattern — read `intent_schema_json_path()` (the committed `schemas/intent-schema.json`).

**SC#3 boundary comment** — copy from configarr block (lines 175-178):
```python
# SC#3 boundary: NONE of these handlers construct or dial a *arr URL.
# base_url is stored/echoed verbatim from the file; nothing calls it.
```
Add equivalent comment to all intent handlers.

**Endpoints to REMOVE** (D-34-04):
- `put_config` function (lines 105-151) — DELETE entirely
- `put_configarr_config` function (lines 210-258) — DELETE entirely

---

### `tools/arrconf-ui/tests/conftest.py` — add `sandboxed_intent_yml` fixture

**Analog:** self (lines 1-62 — read already)

**Copy `sandboxed_arrconf_yml` fixture pattern** (lines 23-35):
```python
# tools/arrconf-ui/tests/conftest.py lines 23-35
@pytest.fixture
def sandboxed_arrconf_yml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Copy the canonical arrconf.yml to tmp_path; patch locator to return the copy."""
    target = tmp_path / "arrconf.yml"
    shutil.copy(CANONICAL_ARRCONF_YML, target)

    def fake_path() -> Path:
        return target

    monkeypatch.setattr("arrconf_ui.locator.arrconf_yml_path", fake_path)
    monkeypatch.setattr("arrconf_ui.app.arrconf_yml_path", fake_path)
    yield target
```

**New fixture to add** (per RESEARCH.md "Verified test fixture pattern"):
```python
CANONICAL_INTENT_YML = REPO_ROOT / "charts" / "arr-stack" / "files" / "intent.yml"

@pytest.fixture
def sandboxed_intent_yml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    target = tmp_path / "intent.yml"
    shutil.copy(CANONICAL_INTENT_YML, target)
    monkeypatch.setattr("arrconf_ui.locator.intent_yml_path", lambda: target)
    monkeypatch.setattr("arrconf_ui.app.intent_yml_path", lambda: target)
    yield target
```

The save test needs THREE sandboxed paths (intent + arrconf + configarr) — combine fixtures. The `sandboxed_arrconf_yml` and `sandboxed_configarr_yml` fixtures already exist; request all three in the save test.

---

### `tools/arrconf-ui/tests/test_intent_endpoints.py` — NEW test file

**Analog:** `tools/arrconf-ui/tests/test_app_endpoints.py` (exact role-match)

**Test file structure pattern** (lines 1-18):
```python
# tools/arrconf-ui/tests/test_app_endpoints.py lines 1-18
"""FastAPI endpoint contracts — GET/PUT/POST/GET on /api/* (D-02)."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from arrconf_ui.app import create_app

@pytest.fixture
def client(sandboxed_arrconf_yml: Path, sandboxed_schema: Path) -> TestClient:
    """Fresh app instance with patched locators."""
    return TestClient(create_app())
```

**Test structure to replicate** (from lines 20-80):
```python
def test_get_config_returns_200_with_top_level_keys(client: TestClient) -> None:
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert "categories" in body
    ...

def test_put_config_with_valid_payload_writes_and_returns_diff(
    client: TestClient, sandboxed_arrconf_yml: Path
) -> None:
    current = client.get("/api/config").json()
    new_payload = json.loads(json.dumps(current))
    resp = client.put("/api/config", json=new_payload)
    assert resp.status_code == 200, resp.text
    ...
```

New test file mirrors these cases for intent endpoints:
- `test_get_intent_returns_200_with_top_level_keys` (categories, sagas, apps, tools, profile_definitions, configarr)
- `test_get_intent_schema_returns_json_schema`
- `test_post_intent_diff_returns_two_labelled_diffs`
- `test_put_intent_writes_intent_yml_and_regenerates_both_files`
- `test_put_intent_with_invalid_payload_returns_422`
- `test_get_config_still_returns_200_readonly` (PUT `/api/config` gone but GET stays)

Client fixture for new tests requests `sandboxed_intent_yml`, `sandboxed_arrconf_yml`, `sandboxed_configarr_yml` (all three paths for save tests).

---

### `tools/arrconf-ui/web/src/api.ts` — add 4 intent functions

**Analog:** self (lines 1-95 — read already)

**Import block pattern** (lines 1-21):
```typescript
// tools/arrconf-ui/web/src/api.ts lines 1-21
import type {
  ConfigPayload,
  DiffResponse,
  PydanticErrorEntry,
  ...
} from './types';

const API_BASE = '/api';

export class ApiError extends Error { ... }

async function _fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    let detail: PydanticErrorEntry[] | string;
    try { const body = await resp.json(); detail = body.detail ?? body; }
    catch { detail = await resp.text(); }
    throw new ApiError(resp.status, detail);
  }
  return (await resp.json()) as T;
}
```

**GET function pattern** (lines 38-40):
```typescript
export async function getConfig(): Promise<ConfigPayload> {
  return _fetchJson<ConfigPayload>(`${API_BASE}/config`);
}
```

**PUT function pattern** (lines 46-52):
```typescript
export async function putConfig(payload: ConfigPayload): Promise<DiffResponse> {
  return _fetchJson<DiffResponse>(`${API_BASE}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
```

**POST function pattern** (lines 54-60):
```typescript
export async function postDiff(payload: ConfigPayload): Promise<DiffResponse> {
  return _fetchJson<DiffResponse>(`${API_BASE}/diff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
```

**New functions to add** (copy patterns above, change types and URLs):
```typescript
// GET /api/intent → IntentPayload
export async function getIntent(): Promise<IntentPayload> {
  return _fetchJson<IntentPayload>(`${API_BASE}/intent`);
}
// GET /api/intent/schema → RootSchema
export async function getIntentSchema(): Promise<RootSchema> {
  return _fetchJson<RootSchema>(`${API_BASE}/intent/schema`);
}
// POST /api/intent/diff → MaterializationDiffResponse
export async function postIntentDiff(payload: IntentPayload): Promise<MaterializationDiffResponse> {
  return _fetchJson<MaterializationDiffResponse>(`${API_BASE}/intent/diff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
// PUT /api/intent → { saved: boolean }
export async function putIntent(payload: IntentPayload): Promise<{ saved: boolean }> {
  return _fetchJson<{ saved: boolean }>(`${API_BASE}/intent`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
```

**Functions to remove** (D-34-04): `putConfig` and `putConfigarrConfig` (or mark as dead code).

---

### `tools/arrconf-ui/web/src/types.ts` — add `IntentPayload` + `MaterializationDiffResponse`

**Analog:** self (lines 1-107 — read already)

**Type definition pattern** — copy shape of `ConfigPayload` (lines 16-24):
```typescript
// tools/arrconf-ui/web/src/types.ts lines 16-24
export type ConfigPayload = {
  categories: MediaCategory[];
  sonarr: Record<string, unknown>;
  radarr: Record<string, unknown>;
  prowlarr: Record<string, unknown>;
  qbittorrent: Record<string, unknown>;
  seerr: Record<string, unknown>;
  jellyfin: Record<string, unknown>;
};
```

**New types to add** (mirror `IntentConfig` shape from RESEARCH.md):
```typescript
// Per-profile custom format ref (D-33-06 shape)
export type CustomFormatRef = {
  trash_ids: string[];
  score: number | null;
};

export type ProfileDefinition = {
  body: Record<string, unknown>;      // opaque QP body
  custom_formats: CustomFormatRef[];
};

export type IntentPayload = {
  categories: MediaCategory[];
  sagas: Record<string, unknown>[];
  apps: Record<string, unknown>;
  tools: Record<string, unknown>;
  profile_definitions: Record<string, ProfileDefinition>;
  configarr: Record<string, unknown>;  // opaque pass-through (D-33-07)
};

export type MaterializationDiffResponse = {
  arrconf_diff: string;
  configarr_diff: string;
  has_changes: boolean;
};
```

---

### `tools/arrconf-ui/web/src/constants.ts` — add `intent` to `ActiveConfig`

**Analog:** self (lines 1-44 — read already)

**Current `ActiveConfig` and `CONFIG_FILE_PATHS`** (lines 40-44):
```typescript
// tools/arrconf-ui/web/src/constants.ts lines 40-44
export const CONFIG_FILE_PATHS = {
  arrconf: 'charts/arr-stack/files/arrconf.yml',
  configarr: 'charts/arr-stack/files/configarr.yml',
} as const;
export type ActiveConfig = keyof typeof CONFIG_FILE_PATHS;
```

**Modification** — add `intent` first (default tab), keep others:
```typescript
export const CONFIG_FILE_PATHS = {
  intent: 'charts/arr-stack/files/intent.yml',
  arrconf: 'charts/arr-stack/files/arrconf.yml',
  configarr: 'charts/arr-stack/files/configarr.yml',
} as const;
export type ActiveConfig = keyof typeof CONFIG_FILE_PATHS;

// Section order for the intent tab
export const INTENT_SECTIONS = [
  'categories',
  'sagas',
  'apps',
  'tools',
  'profile_definitions',
  'configarr',
] as const;
```

---

### `tools/arrconf-ui/web/src/i18n/fr.ts` — add new `SECTION_DOCS` entries

**Analog:** self (lines 28-95 — read already)

**Pattern for new SECTION_DOCS entries** — copy shape of existing entries (lines 29-36):
```typescript
// tools/arrconf-ui/web/src/i18n/fr.ts lines 29-36
export const SECTION_DOCS: Record<string, { title: string; body: string }> = {
  categories: {
    title: 'Catégories — la source de vérité du routing',
    body: `Les catégories sont la **brique fondatrice** ...`,
  },
  ...
};
```

**New entries to add** (per UI-SPEC Copywriting Contract):
```typescript
'intent.categories': {
  title: 'Catégories média',
  body: `...`,
},
'intent.sagas': {
  title: 'Sagas (collections Radarr + BoxSets Jellyfin)',
  body: `...`,
},
'intent.apps': {
  title: 'Configuration des apps (pass-through arrconf.yml)',
  body: `...`,
},
'intent.tools': {
  title: 'Outils externes (cross-seed, qbit_manage)',
  body: `...`,
},
'intent.profile_definitions': {
  title: 'Définitions de profils qualité (configarr)',
  body: `...`,
},
'intent.configarr': {
  title: 'Squelette configarr (pass-through verbatim)',
  body: `Ce bloc est émis verbatim dans configarr.yml. arrconf-ui ne le valide pas.`,
},
```

Also add new string constants at the bottom of the file:
```typescript
export const READONLY_BADGE_TEXT = 'généré — lecture seule';
export const MATERIALIZATION_EMPTY_TEXT = 'Aucune modification';
export const PROFILE_BODY_LABEL = 'Bloc corps du profil (YAML brut)';
export const CONFIGARR_RAW_LABEL = 'Bloc configarr pass-through (YAML brut)';
export const CONFIGARR_RAW_HELPER = "Ce bloc est émis verbatim dans configarr.yml. arrconf-ui ne le valide pas.";
```

---

### `tools/arrconf-ui/web/src/App.svelte` — 3-tab state machine

**Analog:** self (lines 1-267 — read already)

**State declarations pattern** (lines 19-40 — copy and extend):
```typescript
// tools/arrconf-ui/web/src/App.svelte lines 19-40
let schema = $state<RootSchema | null>(null);
let configState = $state<ConfigPayload | null>(null);
let savedConfig = $state<ConfigPayload | null>(null);
let validationErrors = $state<PydanticErrorEntry[]>([]);
let saveStatus = $state<SaveStatus>('idle');
let loadError = $state<string | null>(null);
let showDiffPanel = $state(false);
let pendingDiff = $state<SemanticDiff | null>(null);
let showSaveToast = $state(false);
let activeConfig = $state<ActiveConfig>('arrconf');
let confirmSwitchOpen = $state(false);
let pendingSwitch = $state<ActiveConfig | null>(null);

const diffCount = $derived(
  configState && savedConfig
    ? (JSON.stringify(configState) === JSON.stringify(savedConfig) ? 0 : 1)
    : 0
);
```

New state for intent pivot: replace `configState`/`savedConfig` with `intentState`/`savedIntent` for the intent tab. The `diffCount` derived replaces `configState`/`savedConfig` with `intentState`/`savedIntent`, restricted to `activeConfig === 'intent'`.

**`loadForConfig` pattern** (lines 43-56 — copy, extend for 3 tabs):
```typescript
async function loadForConfig(cfg: ActiveConfig) {
  schema = null; configState = null;
  try {
    const [s, c] = cfg === 'arrconf'
      ? await Promise.all([api.getSchema(), api.getConfig()])
      : await Promise.all([api.getConfigarrSchema(), api.getConfigarrConfig()]);
    schema = s;
    configState = c as ConfigPayload;
    savedConfig = JSON.parse(JSON.stringify(c)) as ConfigPayload;
    loadError = null;
  } catch (e) {
    loadError = e instanceof Error ? e.message : String(e);
  }
}
```

**Tab switch + confirm gate pattern** (lines 116-125 — reuse verbatim):
```typescript
function requestTabChange(next: ActiveConfig) {
  if (next === activeConfig) return;
  if (diffCount > 0) { pendingSwitch = next; confirmSwitchOpen = true; return; }
  void doSwitch(next);
}
async function doSwitch(next: ActiveConfig) {
  activeConfig = next; confirmSwitchOpen = false; pendingSwitch = null;
  await loadForConfig(next);
}
function cancelSwitch() { confirmSwitchOpen = false; pendingSwitch = null; }
```

**`openDiffPanel` / `confirmSave` pattern** (lines 72-109): For intent tab, `openDiffPanel` calls `api.postIntentDiff(intentState)` and stores `pendingMatDiff` (materialization diff). `confirmSave` calls `api.putIntent(intentState)`.

**Conditional rendering pattern** (lines 163-201): Extend `{#if activeConfig === 'arrconf'}...{:else if activeConfig === 'configarr'}...{:else}...{/if}` to three branches. Intent tab renders `MaterializationDiffPanel` (instead of `DiffPanel`) + intent form sections. Arrconf/configarr tabs render `ReadOnlyInspector` only.

**Confirm dialog markup** (lines 137-147 — reuse verbatim):
```html
{#if confirmSwitchOpen}
  <div class="confirm-overlay" role="dialog" aria-modal="true">
    <div class="confirm-dialog">
      <p class="confirm-message">{UNSAVED_SWITCH_MESSAGE}</p>
      <div class="confirm-actions">
        <button ...>Annuler</button>
        <button ...>Changer</button>
      </div>
    </div>
  </div>
{/if}
```

**Load error / spinner pattern** (lines 149-154 — reuse verbatim):
```html
{#if loadError}
  <div class="load-error" role="alert">
    Impossible de charger {CONFIG_FILE_PATHS[activeConfig]} — {loadError}. Vérifie...
  </div>
{:else if !configState || !schema}
  <Spinner label="Chargement de {CONFIG_FILE_PATHS[activeConfig]}…" />
```

---

### `tools/arrconf-ui/web/src/lib/HeaderBar.svelte` — add 3rd tab, conditional save button

**Analog:** self (lines 1-134 — read already)

**Tab button pattern** (lines 28-33 — copy and add 3rd tab):
```html
<!-- tools/arrconf-ui/web/src/lib/HeaderBar.svelte lines 28-33 -->
<button type="button" class="tab" class:tab-active={activeConfig === 'arrconf'}
  onclick={() => onTabChange('arrconf')}>arrconf.yml</button>
<button type="button" class="tab" class:tab-active={activeConfig === 'configarr'}
  onclick={() => onTabChange('configarr')}>configarr.yml</button>
```

New button order: intent first, then arrconf, then configarr. Add `intent.yml` tab button with same CSS class.

**Save button conditional visibility** — currently shown unconditionally; add `{#if activeConfig === 'intent'}` guard. Hide entirely (not just disabled) on inspect tabs per UI-SPEC.

**Read-only badge for generated files** — add inline `<span>` after `<code class="filepath">` when `activeConfig !== 'intent'`. Style copy: `.diff-chip` shape from lines 99-107:
```css
/* tools/arrconf-ui/web/src/lib/HeaderBar.svelte lines 99-107 */
.diff-chip {
  color: var(--accent);
  background: var(--accent-soft);
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
  font-weight: 500;
  font-family: 'IBM Plex Mono', monospace;
}
```
Badge style: same pill shape but `--panel-alt` bg + `--ink-muted` text (not accent — not actionable per UI-SPEC).

---

### `tools/arrconf-ui/web/src/lib/MaterializationDiffPanel.svelte` — NEW

**Analog:** `tools/arrconf-ui/web/src/lib/DiffPanel.svelte` (exact)

**Props pattern** (DiffPanel lines 1-9):
```typescript
// tools/arrconf-ui/web/src/lib/DiffPanel.svelte lines 1-9
<script lang="ts">
  import type { SemanticDiff } from '../types';
  type Props = {
    diff: SemanticDiff;
    onConfirm: () => void;
    onCancel: () => void;
  };
  let { diff, onConfirm, onCancel }: Props = $props();
```

New props type:
```typescript
type Props = {
  arrconfDiff: string;    // unified text diff string from POST /api/intent/diff
  configarrDiff: string;  // unified text diff string
  onConfirm: () => void;
  onCancel: () => void;
};
```

**Panel container CSS** (DiffPanel lines 69-78 — copy verbatim):
```css
/* tools/arrconf-ui/web/src/lib/DiffPanel.svelte lines 69-78 */
.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: var(--space-lg);
  margin: var(--space-md) 0;
  box-shadow: var(--shadow-md);
}
h2 { font-size: 16px; font-weight: 600; margin: 0 0 var(--space-md) 0; color: var(--ink); }
```

**Actions row CSS** (DiffPanel lines 118-130 — copy verbatim):
```css
/* tools/arrconf-ui/web/src/lib/DiffPanel.svelte lines 118-130 */
.actions {
  display: flex;
  gap: var(--space-sm);
  margin-top: var(--space-lg);
  padding-top: var(--space-md);
  border-top: 1px solid var(--border);
}
.confirm-btn {
  background: var(--accent);
  color: var(--accent-fg);
  border: 1px solid var(--accent);
  font-weight: 500;
}
```

**Diff line coloring** (DiffPanel lines 110-113 — copy op-* classes, adapt for text lines):
```css
/* tools/arrconf-ui/web/src/lib/DiffPanel.svelte lines 110-113 */
.op-add .op { color: #10b981; }
.op-mod .op { color: var(--accent); }
.op-del .op { color: var(--destructive); }
```

New CSS for text diff lines (parse line prefix in `$derived`):
```css
.line-add { color: #10b981; background: rgba(16, 185, 129, 0.08); }
.line-del { color: var(--destructive); background: rgba(248, 113, 113, 0.08); }
.line-hunk { color: var(--accent); background: color-mix(in srgb, var(--accent-soft) 30%, transparent); }
.line-ctx { color: var(--ink-muted); }
```

**Template structure** (DiffPanel lines 25-67 — structural skeleton to copy):
```html
<!-- tools/arrconf-ui/web/src/lib/DiffPanel.svelte lines 25-67 -->
<div class="panel" role="dialog" aria-labelledby="diff-panel-heading" aria-modal="true">
  <h2 id="diff-panel-heading">Modifications en attente — vérifie avant d'enregistrer</h2>
  {#if changedSections.length === 0}
    <p class="empty">Aucune modification détectée.</p>
  {/if}
  ...
  <div class="actions">
    <button type="button" class="confirm-btn" onclick={onConfirm}>Confirmer et enregistrer</button>
    <button type="button" onclick={onCancel}>Continuer l'édition</button>
  </div>
</div>
```

Adaptation: replace section-by-section semantic diff with two `<pre>` blocks — one per labelled file. Use `diffDiff.split('\n').map(line => ({text: line, cls: lineClass(line)}))` to colorize.

---

### `tools/arrconf-ui/web/src/lib/ProfileDefinitionsEditor.svelte` — NEW

**Analog:** `tools/arrconf-ui/web/src/lib/CategoriesEditor.svelte` (role-match: list editor with add/delete)

**Props + state pattern** (CategoriesEditor lines 1-17):
```typescript
// tools/arrconf-ui/web/src/lib/CategoriesEditor.svelte lines 1-17
type Props = {
  categories: MediaCategory[];
  onChange: (next: MediaCategory[]) => void;
};
let { categories, onChange }: Props = $props();

let newRow = $state<MediaCategory>({ name: '', kind: 'series', profile: 'general', display: '', base_path: '' });
```

New props:
```typescript
type Props = {
  profiles: Record<string, ProfileDefinition>;  // keyed by profile name
  onChange: (next: Record<string, ProfileDefinition>) => void;
};
```

**Add/delete pattern** (CategoriesEditor lines 39-46):
```typescript
// tools/arrconf-ui/web/src/lib/CategoriesEditor.svelte lines 39-46
function addRow() {
  if (!newRow.name.trim()) return;
  onChange([...categories, { ...newRow }]);
  newRow = { name: '', kind: 'series', profile: 'general', display: '', base_path: '' };
}
function deleteRow(idx: number) {
  onChange(categories.filter((_, i) => i !== idx));
}
```

Adaptation: `addProfile(name)` adds `{body: {}, custom_formats: []}` entry. `deleteProfile(name)` removes key from dict. Profiles rendered as a list of `ProfileCard` children (one per key).

---

### `tools/arrconf-ui/web/src/lib/ProfileCard.svelte` — NEW

**Analog:** `tools/arrconf-ui/web/src/lib/TrashCFPicker.svelte` (role-match: CF chip list + picker)

**CF chip display pattern** (TrashCFPicker lines 107-120):
```html
<!-- tools/arrconf-ui/web/src/lib/TrashCFPicker.svelte lines 107-120 -->
<div class="existing-entries">
  {#each existingCustomFormats as entry, idx}
    {#each entry.trash_ids as id, idIdx}
      <div class="cf-chip">
        <span class="cf-label">{labelFor(id)}</span>
        <button type="button" class="array-delete" onclick={() => removeId(idx, idIdx)} aria-label="Supprimer">✕</button>
      </div>
    {/each}
  {/each}
</div>
```

**CF chip CSS** (TrashCFPicker lines 195-202 — copy verbatim):
```css
/* tools/arrconf-ui/web/src/lib/TrashCFPicker.svelte lines 195-202 */
.cf-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  background: var(--panel-alt);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px var(--space-xs);
  font-size: 12px;
  font-family: 'IBM Plex Mono', monospace;
}
```

**Add button CSS** (TrashCFPicker lines 304-319 — copy verbatim):
```css
/* tools/arrconf-ui/web/src/lib/TrashCFPicker.svelte lines 304-319 */
.array-add {
  align-self: flex-start;
  background: var(--accent-soft);
  border: 1px solid var(--accent);
  border-radius: 4px;
  color: var(--accent-fg);
  cursor: pointer;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 13px;
  padding: var(--space-xs) var(--space-sm);
}
```

**Critical: TrashCFPicker shape adapter** — `ProfileCard` receives `CustomFormatRef[]` (per-profile) but `TrashCFPicker` expects `CustomFormatEntry[]` (cross-profile). Transform before passing to picker (RESEARCH.md Pattern 5):
```typescript
// Transform CustomFormatRef[] → CustomFormatEntry[] for TrashCFPicker
const pickerCFs = $derived(
  profile.custom_formats.map((ref) => ({
    trash_ids: ref.trash_ids,
    assign_scores_to: [{ name: profileName, ...(ref.score !== null ? { score: ref.score } : {}) }],
  }))
);
// Reverse transform on onChange
function handleCFChange(next: CustomFormatEntry[]) {
  const refs: CustomFormatRef[] = next.map((entry) => ({
    trash_ids: entry.trash_ids,
    score: entry.assign_scores_to[0]?.score ?? null,
  }));
  onChange({ ...profile, custom_formats: refs });
}
```

**`<details>` card pattern** — use `SectionDoc.svelte` collapsible `<details>` structure (lines 42-56):
```html
<!-- tools/arrconf-ui/web/src/lib/SectionDoc.svelte lines 42-56 -->
<details class="section-doc" open={isOpen} ontoggle={...}>
  <summary>
    <svg class="chevron" .../>
    <span class="doc-title">{doc.title}</span>
    <span class="doc-toggle-hint">{isOpen ? 'masquer' : 'à propos de cette section'}</span>
  </summary>
  <div class="doc-body">...</div>
</details>
```

Card CSS from SectionDoc (lines 59-68 — use as base, adjust for profile card):
```css
/* tools/arrconf-ui/web/src/lib/SectionDoc.svelte lines 59-68 */
.section-doc {
  background: var(--doc-bg);
  border-left: 3px solid var(--doc-border);
  border-top: 1px solid var(--border);
  border-right: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  border-radius: 0 3px 3px 0;
  margin-bottom: var(--space-sm);
}
```
Profile card uses `--panel` bg + `--border` border (not doc-bg) per UI-SPEC.

Score input: `<input type="number">` width 5em, `IBM Plex Mono`, placeholder `défaut` — inline next to each CF chip. No existing analog; use standard `<input>` with app.css focus styles.

---

### `tools/arrconf-ui/web/src/lib/ConfigarrRawEditor.svelte` — NEW

**Analog:** app.css textarea styles + SectionDoc label pattern

**Textarea styled with mono font** — no exact analog in components, but app.css already defines textarea base styles. Use `IBM Plex Mono` 12px, background `--code-bg`, border `--border`:
```css
/* New component: match existing code/pre conventions from app.css */
textarea.raw-editor {
  width: 100%;
  min-height: 200px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: var(--space-sm) var(--space-md);
  color: var(--ink);
  resize: vertical;
}
textarea.raw-editor:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
```

**Label pattern** — copy the `h2` style from DiffPanel (line 78):
```css
/* tools/arrconf-ui/web/src/lib/DiffPanel.svelte line 78 */
h2 { font-size: 16px; font-weight: 600; margin: 0 0 var(--space-md) 0; color: var(--ink); }
```
Label is `14px IBM Plex Sans weight 600` (mini-heading per UI-SPEC, not h2 size). Use `<label>` or `<p>` with explicit styles.

**Props pattern:**
```typescript
type Props = {
  value: Record<string, unknown>;   // intent.configarr — opaque dict
  onChange: (next: Record<string, unknown>) => void;
};
```
Internal: serialize `value` to YAML string for display; parse on change. Use a simple `JSON.stringify(value, null, 2)` as initial approximation — or a YAML serializer if available (no new libraries).

---

### `tools/arrconf-ui/web/src/lib/ReadOnlyInspector.svelte` — NEW

**Analog:** `tools/arrconf-ui/web/src/lib/DiffPanel.svelte` (panel structure) + App.svelte load-error pattern

**Panel container** — copy `.panel` CSS from DiffPanel (lines 69-77):
```css
/* tools/arrconf-ui/web/src/lib/DiffPanel.svelte lines 69-77 */
.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: var(--space-lg);
  margin: var(--space-md) 0;
  box-shadow: var(--shadow-md);
}
```

**Pre block** — UI-SPEC: `IBM Plex Mono 12px`, background `--code-bg`, border, `overflow-y: auto`, no max-height:
```css
pre.inspector {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: var(--space-lg);
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
```

**Load error pattern** — copy from App.svelte (lines 149-151):
```html
<!-- tools/arrconf-ui/web/src/App.svelte lines 149-151 -->
{#if loadError}
  <div class="load-error" role="alert">
    Impossible de charger {CONFIG_FILE_PATHS[activeConfig]} — {loadError}. Vérifie le chemin du fichier puis réessaie.
  </div>
```

**Props:**
```typescript
type Props = {
  content: string | null;  // raw YAML string from GET /api/config or GET /api/configarr/config
  filePath: string;
  loadError: string | null;
};
```

**Read-only field treatment** (UI-SPEC): `--surface` background (not `--panel`), `opacity: 0.6`, `pointer-events: none` on any inputs — this component has none, so just ensure background is `--surface`.

---

## Shared Patterns

### Svelte 5 Runes (`$state`, `$derived`, `$props`, `$effect`)

**Source:** `tools/arrconf-ui/web/src/App.svelte` lines 19-41 + `TrashCFPicker.svelte` lines 23-36
**Apply to:** All new Svelte components

```typescript
// All components use $props() for prop destructuring:
let { propA, propB }: Props = $props();

// All mutable state uses $state():
let loading = $state(false);

// All derived values use $derived():
const isDisabled = $derived(diffCount === 0 || saveStatus === 'saving');

// All async side effects use $effect():
$effect(() => {
  loading = true;
  api.getStuff().then((data) => { result = data; loading = false; });
});
```

### Python ValidationError → JSONResponse pattern

**Source:** `tools/arrconf-ui/arrconf_ui/app.py` lines 108-117
**Apply to:** All new backend POST/PUT handlers

```python
# tools/arrconf-ui/arrconf_ui/app.py lines 108-117
try:
    RootConfig.model_validate(payload)
except ValidationError as e:
    # e.errors() ctx values may contain non-JSON-serializable objects
    detail = json.loads(json.dumps(e.errors(), default=str))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail},
    )
```

### 404 file-not-found HTTPException pattern

**Source:** `tools/arrconf-ui/arrconf_ui/app.py` lines 70-75
**Apply to:** All new GET endpoints that read from disk

```python
# tools/arrconf-ui/arrconf_ui/app.py lines 70-75
path = arrconf_yml_path()
if not path.exists():
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"arrconf.yml not found at {path}",
    )
```

### Atomic write for text content

**Source:** `tools/arrconf-ui/arrconf_ui/io.py` lines 48-81 (`write_yaml_atomic`)
**Apply to:** `PUT /api/intent` save handler — intent.yml write

The existing `write_yaml_atomic` uses `YAML(typ="rt")` round-trip for CommentedMap objects. For intent.yml written from a JSON payload (plain dict), use `YAML(typ="safe")` instead. Same `tempfile` + `os.replace()` atomicity recipe:
```python
# Pattern from io.py lines 61-81 — adapt for safe YAML + plain dict:
tmp = tempfile.NamedTemporaryFile(
    mode="w", encoding="utf-8",
    dir=str(intent_yml_path().parent),
    prefix=".intent.yml.", suffix=".tmp", delete=False,
)
try:
    yaml = YAML(typ="safe"); yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.dump(payload, tmp)
    tmp.flush(); os.fsync(tmp.fileno()); tmp.close()
    os.replace(tmp.name, intent_yml_path())
except Exception:
    tmp.close()
    try: os.unlink(tmp.name)
    except FileNotFoundError: pass
    raise
```

### structlog event naming

**Source:** `tools/arrconf-ui/arrconf_ui/app.py` lines 141-150
**Apply to:** All new save endpoints

```python
# tools/arrconf-ui/arrconf_ui/app.py lines 141-150
log.info(
    "config_saved",
    has_changes=has_changes(diff),
    changed_sections=[...],
)
```
New intent endpoint logs `log.info("intent_saved")`.

### Test client fixture pattern

**Source:** `tools/arrconf-ui/tests/test_app_endpoints.py` lines 14-17
**Apply to:** `test_intent_endpoints.py`

```python
@pytest.fixture
def client(sandboxed_arrconf_yml: Path, sandboxed_schema: Path) -> TestClient:
    """Fresh app instance with patched locators."""
    return TestClient(create_app())
```

### Sandboxed fixture monkeypatch pattern

**Source:** `tools/arrconf-ui/tests/conftest.py` lines 23-35
**Apply to:** New `sandboxed_intent_yml` fixture in conftest.py

Both the `locator` module symbol AND the re-exported name in `app.py` must be patched (same two-`setattr` pattern as existing fixtures).

---

## No Analog Found

All files have close analogs. No entries.

---

## Metadata

**Analog search scope:** `tools/arrconf-ui/` (all Python + TypeScript/Svelte sources)
**Files read:** 17 source files
**Pattern extraction date:** 2026-06-08
