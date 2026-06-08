# Phase 34: UI over intent — Research

**Researched:** 2026-06-08
**Domain:** arrconf-ui pivot (FastAPI + Svelte 5) — intent.yml as sole editable source
**Confidence:** HIGH — primary source is the codebase itself (all claims verified by direct read)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-34-01:** Backend imports `generate_arrconf_yml` + `generate_configarr_yml` from
  `arrconf.generators` directly. `arrconf` is already an editable dep of `arrconf-ui`
  (`pyproject.toml`: `arrconf = {path="../arrconf", editable=true}`).
- **D-34-02:** Diff panel = unified TEXT diff (new-generated-from-edited-intent vs
  current on-disk generated), rendered line-by-line for arrconf.yml AND configarr.yml,
  both labelled.
- **D-34-03:** Schema-mirror baseline via new `/api/intent/schema` from
  `IntentConfig.model_json_schema()`; `profile_definitions` → TRaSH picker special-case;
  `configarr` → raw/opaque block.
- **D-34-04:** Remove PUT endpoints for arrconf.yml/configarr.yml; keep GET as read-only
  inspectors; `ConfigError` on edit attempt of generated file.
- **D-34-05:** Per-profile TRaSH picker; reuse existing `/api/trash/*` endpoints as-is.
- **D-34-06:** Save writes intent.yml then regenerates both files (keeps CI
  `generate-idempotence` green).

### Claude's Discretion

- Structure exacte des composants Svelte (découpage, réutilisation de `SectionDoc`/`DiffPanel`).
- Approche/lib de rendu du diff texte unifié côté frontend.
- Nommage exact des nouveaux endpoints (`/api/intent`, `/api/intent/schema`,
  `/api/intent/diff`, `/api/intent/generate` ou save combiné).
- Forme exacte des erreurs (`ConfigError` → HTTP status) sur tentative d'édition
  d'un fichier généré.

### Deferred Ideas (OUT OF SCOPE)

- `/gsd-ui-phase 34` formel UI contract (already completed — 34-UI-SPEC.md exists).
- Édition structurée du bloc `configarr` pass-through (au-delà du raw editor).
- Migrer médiathèque existante vers buckets Categories v0.3.0 (ops task, unrelated).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | `arrconf-ui` charge et édite `intent.yml` comme seule source éditable | New `/api/intent` GET/PUT + `load_intent`/`write_yaml_atomic` + `intent_yml_path()` to add to locator |
| UI-02 | Formulaires schema-mirror legacy arrconf.yml + configarr.yml retirés (ou réduits à read-only) | Remove PUT `/api/config` + PUT `/api/configarr/config`; keep GET as-is; frontend: 3-tab state machine |
| UI-03 | Picker CF/QP TRaSH intégré au flux d'édition intent | `TrashCFPicker`/`TrashQPPicker` mounted per-profile inside `ProfileDefinitionsEditor`; `/api/trash/*` reused unchanged |
| UI-04 | UI expose sortie `generate` (diff des configs générées) avant commit | New `/api/intent/diff` POST → calls `generate_arrconf_yml` + `generate_configarr_yml` → Python `difflib.unified_diff` → two labelled text diffs |
</phase_requirements>

---

## Summary

Phase 34 pivots `arrconf-ui` so `intent.yml` becomes the only editable file. The frontend
currently operates a two-tab state machine (arrconf.yml / configarr.yml) powered by
PUT endpoints that write to the generated files — after Phases 32/33 those files are
generated artifacts, making the existing UI stale by construction. This phase corrects
the UI/data-model misalignment without touching any generator code.

The backend work is additive + surgical removal: add four new `/api/intent/*` endpoints
(GET, PUT/save, diff preview, schema), add `intent_yml_path()` to `locator.py`, and
remove the two PUT endpoints for generated files. The existing GET endpoints for
arrconf.yml and configarr.yml become pure read-only inspectors. All generator logic is
imported from `arrconf.generators` — the editable dep is already in `pyproject.toml`,
so this is zero new infrastructure.

The frontend work restructures the two-tab state machine into three tabs (intent.yml |
arrconf.yml inspect | configarr.yml inspect), adds five new Svelte 5 components
(`MaterializationDiffPanel`, `ProfileDefinitionsEditor`, `ProfileCard`,
`ConfigarrRawEditor`, `ReadOnlyInspector`), and modifies three existing ones
(`HeaderBar`, `App.svelte`, `constants.ts`). The existing `TrashCFPicker` and
`TrashQPPicker` are reused without modification — only their mount point changes.

**Primary recommendation:** Plan the backend as a single wave (one plan or two plans for
locator+endpoints vs save logic), and the frontend as two waves: (1) three-tab skeleton +
read-only inspectors + App.svelte rewire, (2) intent form sections + picker mount +
MaterializationDiffPanel.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Edit intent.yml | API / Backend | — | File I/O must be server-side; frontend sends JSON payload |
| Regenerate arrconf.yml + configarr.yml | API / Backend | — | `generate_*` are pure Python functions; called on save and on diff preview |
| Unified text diff computation | API / Backend | — | `difflib.unified_diff` in Python; frontend only renders the pre-computed string |
| Intent schema serving | API / Backend | — | `IntentConfig.model_json_schema()` call; already pattern for arrconf + configarr schemas |
| Intent form rendering | Frontend (Svelte) | — | Schema-driven auto-forms + special-cased sections (D-34-03) |
| Profile definitions editor + picker | Frontend (Svelte) | — | Per-profile TRaSH picker mounts inside Svelte component; calls existing `/api/trash/*` |
| Read-only generated file display | Frontend (Svelte) | Backend GET | Frontend renders `<pre>` from existing GET `/api/config` + `/api/configarr/config` |
| Tab navigation + unsaved-change guard | Frontend (Svelte) | — | Entirely client-side state machine |

---

## Standard Stack

No new libraries. Everything below is already installed.

### Backend (Python — `tools/arrconf-ui/`)

| Component | Currently Used | Phase 34 Usage |
|-----------|---------------|----------------|
| `fastapi` 0.115.x | All endpoints | New `/api/intent/*` endpoints follow same pattern |
| `pydantic` v2 | `RootConfig`, `ConfigarrRootConfig` validation | `IntentConfig.model_validate` + `IntentConfig.model_json_schema()` |
| `ruyaml` 0.91.x | `io.py` round-trip read/write | `write_yaml_atomic` reused for intent.yml write |
| `structlog` | Logging | Same pattern |
| `arrconf` (editable dep) | `RootConfig`, `load_config` | Extend imports: `IntentConfig`, `load_intent`, `generate_arrconf_yml`, `generate_configarr_yml` |
| `difflib` (stdlib) | Not currently used | `difflib.unified_diff` for text diff of generated files |

### Frontend (TypeScript/Svelte — `tools/arrconf-ui/web/`)

| Component | Currently Used | Phase 34 Usage |
|-----------|---------------|----------------|
| Svelte 5 runes | All components | New components follow same `$state`/`$derived`/`$props()` pattern |
| `api.ts` fetch wrapper | `getConfig`, `putConfig`, etc. | Add `getIntent`, `getIntentSchema`, `postIntentDiff`, `putIntent` |
| `schema.ts` `resolveNode`/`effectiveNode` | `AppSection` for configarr form | Reused for intent schema form sections |
| `AppSection.svelte` | arrconf + configarr sections | Reused for `sagas`, `apps`, `tools` sections |
| `CategoriesEditor.svelte` | arrconf categories | Reused AS-IS for `intent.categories` |
| `TrashCFPicker.svelte` | configarr section (global) | Mounted per-profile in `ProfileCard.svelte` |
| `TrashQPPicker.svelte` | configarr section (global) | Mounted per-profile in `ProfileCard.svelte` |
| `DiffPanel.svelte` | Semantic field-level diff | REPLACED by `MaterializationDiffPanel.svelte` for intent flow |
| `SectionDoc.svelte` | Above each section | Reused; new `SECTION_DOCS` entries added to `i18n/fr.ts` |

**Version verification:** No new packages — no version check needed.

---

## Architecture Patterns

### System Architecture Diagram

```
intent.yml (hand-edited)
    │
    ▼ POST /api/intent/diff (preview)
    │   load_intent() → IntentConfig
    │   generate_arrconf_yml(intent_cfg) → arrconf_str
    │   generate_configarr_yml(intent_cfg) → configarr_str
    │   on-disk arrconf.yml → current_arrconf_str
    │   on-disk configarr.yml → current_configarr_str
    │   difflib.unified_diff(current, generated) × 2
    │   → { arrconf_diff: str, configarr_diff: str }
    │
    ▼ PUT /api/intent (save)
    │   IntentConfig.model_validate(payload)
    │   write_yaml_atomic(intent_yml_path(), payload_as_ruyaml)
    │   generate_arrconf_yml(intent_cfg) → write arrconf.yml
    │   generate_configarr_yml(intent_cfg) → write configarr.yml
    │   → { saved: true }
    │
    ├── GET /api/intent → load_intent() → IntentConfig.model_dump(mode='json')
    ├── GET /api/intent/schema → IntentConfig.model_json_schema()
    ├── GET /api/config (read-only, unchanged) → arrconf.yml content
    └── GET /api/configarr/config (read-only, unchanged) → configarr.yml content

Frontend (Svelte 5):
    App.svelte
    ├── Tab: intent.yml [active by default]
    │   ├── MaterializationDiffPanel (when showDiffPanel)
    │   ├── SectionDoc + CategoriesEditor (categories)
    │   ├── SectionDoc + AppSection (sagas, apps, tools)
    │   ├── SectionDoc + ProfileDefinitionsEditor
    │   │   └── ProfileCard × N
    │   │       ├── body textarea (raw YAML)
    │   │       ├── CF chip list + TrashCFPicker
    │   │       └── TrashQPPicker
    │   └── SectionDoc + ConfigarrRawEditor
    ├── Tab: arrconf.yml [inspect]
    │   └── ReadOnlyInspector ← GET /api/config
    └── Tab: configarr.yml [inspect]
        └── ReadOnlyInspector ← GET /api/configarr/config
```

### Recommended Project Structure (additions only)

```
tools/arrconf-ui/
├── arrconf_ui/
│   ├── app.py               ← add 4 intent endpoints, remove 2 PUT endpoints
│   └── locator.py           ← add intent_yml_path() + intent_schema_json_path()
└── web/src/
    ├── lib/
    │   ├── MaterializationDiffPanel.svelte  ← NEW
    │   ├── ProfileDefinitionsEditor.svelte  ← NEW
    │   ├── ProfileCard.svelte               ← NEW
    │   ├── ConfigarrRawEditor.svelte        ← NEW
    │   ├── ReadOnlyInspector.svelte         ← NEW
    │   ├── HeaderBar.svelte                 ← MODIFIED (3rd tab, badge)
    │   └── DiffPanel.svelte                 ← KEPT (still used for arrconf/configarr if needed;
    │                                           not used in intent tab)
    ├── App.svelte              ← MODIFIED (3-tab state machine, intent payload)
    ├── api.ts                  ← MODIFIED (4 new functions)
    ├── types.ts                ← MODIFIED (IntentPayload, MaterializationDiffResponse)
    ├── constants.ts            ← MODIFIED (ActiveConfig union + 3rd tab)
    └── i18n/fr.ts              ← MODIFIED (new SECTION_DOCS + copy strings)
```

### Pattern 1: Backend intent endpoint (GET)

```python
# Source: tools/arrconf-ui/arrconf_ui/app.py (existing GET /api/config pattern)
@app.get("/api/intent")
def get_intent() -> Any:
    """Return intent.yml parsed + validated as JSON (IntentConfig.model_dump)."""
    path = intent_yml_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"intent.yml not found at {path}")
    try:
        cfg = load_intent(path)
    except ConfigError as e:
        # Surface parse/validation errors without 500
        return JSONResponse(
            status_code=422,
            content={"detail": str(e)},
        )
    return cfg.model_dump(mode="json")
```

### Pattern 2: Backend intent diff endpoint (POST)

```python
# Source: tools/arrconf-ui/arrconf_ui/app.py (existing POST /api/diff pattern) +
#         tools/arrconf/arrconf/generators/intent.py + generators/configarr.py
@app.post("/api/intent/diff")
def post_intent_diff(payload: dict[str, Any]) -> Any:
    """Stateless preview: generate arrconf.yml + configarr.yml from payload,
    diff against on-disk versions, return unified text diffs.
    
    SC#3 boundary: NEVER constructs or dials a *arr URL.
    """
    try:
        intent_cfg = IntentConfig.model_validate(payload)
    except ValidationError as e:
        detail = json.loads(json.dumps(e.errors(), default=str))
        return JSONResponse(status_code=422, content={"detail": detail})
    
    new_arrconf = generate_arrconf_yml(intent_cfg)
    new_configarr = generate_configarr_yml(intent_cfg)
    
    current_arrconf = arrconf_yml_path().read_text("utf-8") if arrconf_yml_path().exists() else ""
    current_configarr = configarr_yml_path().read_text("utf-8") if configarr_yml_path().exists() else ""
    
    arrconf_diff = "\n".join(difflib.unified_diff(
        current_arrconf.splitlines(), new_arrconf.splitlines(),
        fromfile="arrconf.yml (actuel)", tofile="arrconf.yml (généré)", lineterm=""
    ))
    configarr_diff = "\n".join(difflib.unified_diff(
        current_configarr.splitlines(), new_configarr.splitlines(),
        fromfile="configarr.yml (actuel)", tofile="configarr.yml (généré)", lineterm=""
    ))
    return {
        "arrconf_diff": arrconf_diff,
        "configarr_diff": configarr_diff,
        "has_changes": bool(arrconf_diff or configarr_diff),
    }
```

### Pattern 3: Backend save endpoint (PUT)

```python
# Source: tools/arrconf-ui/arrconf_ui/app.py (existing PUT /api/config pattern)
# + D-34-06: save writes intent.yml AND regenerates both files.
@app.put("/api/intent")
def put_intent(payload: dict[str, Any]) -> Any:
    """Validate → write intent.yml → regenerate arrconf.yml + configarr.yml."""
    try:
        intent_cfg = IntentConfig.model_validate(payload)
    except ValidationError as e:
        detail = json.loads(json.dumps(e.errors(), default=str))
        return JSONResponse(status_code=422, content={"detail": detail})
    
    # Write intent.yml via YAML(typ="safe") — intent.yml has no comments to preserve
    # (it IS the hand-edited file, but the UI-generated version will be validated
    # by pydantic; generator uses YAML safe for determinism).
    # Use write_yaml_atomic for crash safety.
    yaml = YAML(typ="safe")
    yaml.default_flow_style = False
    buf = io.StringIO()
    yaml.dump(payload, buf)
    _write_text_atomic(intent_yml_path(), buf.getvalue())
    
    # Regenerate both files (D-34-06).
    arrconf_yml_path().write_text(generate_arrconf_yml(intent_cfg), encoding="utf-8")
    configarr_yml_path().write_text(generate_configarr_yml(intent_cfg), encoding="utf-8")
    
    log.info("intent_saved")
    return {"saved": True}
```

**Note on intent.yml write:** The existing `write_yaml_atomic` uses `YAML(typ="rt")` round-trip to preserve comments. For intent.yml written by the UI, comments won't be present in the payload (JSON in, JSON out), so either approach works. However, since the generated file has a canonical `# HAND-EDITED` header that must be preserved, the backend may need to prepend it or use `write_yaml_atomic` with a pre-built `CommentedMap`. The simplest approach: use `write_text` (atomic via a temp file pattern) with a serialized YAML safe dump — the header line is not present in the `IntentConfig` payload anyway. **Pitfall: verify whether `intent.yml` contains the `# yaml-language-server: $schema` modeline — it does (verified in source). The UI write will lose it.** See Pitfall 2 below.

### Pattern 4: Locator additions

```python
# Source: tools/arrconf-ui/arrconf_ui/locator.py (existing pattern)
def intent_yml_path() -> Path:
    """Return the canonical path to charts/arr-stack/files/intent.yml."""
    return repo_root() / "charts" / "arr-stack" / "files" / "intent.yml"

def intent_schema_json_path() -> Path:
    """Return the canonical path to schemas/intent-schema.json."""
    return repo_root() / "schemas" / "intent-schema.json"
```

### Pattern 5: TrashCFPicker props for per-profile mount

The existing `TrashCFPicker` has this prop signature (verified in source):

```typescript
// Source: tools/arrconf-ui/web/src/lib/TrashCFPicker.svelte
type Props = {
  app: 'sonarr' | 'radarr';
  existingCustomFormats: CustomFormatEntry[];  // { trash_ids, assign_scores_to }
  localDefinitions: { trash_id: string; name: string }[];
  profileNames: string[];
  onChange: (next: CustomFormatEntry[]) => void;
};
```

**Critical mismatch:** The existing picker's `existingCustomFormats` type uses
`{ trash_ids: string[]; assign_scores_to: { name: string; score?: number }[] }` —
but the `IntentConfig.profile_definitions[name].custom_formats` uses
`{ trash_ids: string[]; score: int | None }` (a `CustomFormatRef` — per-profile, not
cross-profile). The picker was designed for the configarr.yml structure where
`assign_scores_to` lists multiple profiles. In the new per-profile mount, each
`ProfileCard` has its own picker for exactly one profile.

**Resolution:** `ProfileCard.svelte` must transform `CustomFormatRef[]` (from intent) to
the picker's `CustomFormatEntry[]` format when passing `existingCustomFormats`, and
transform back on `onChange`. Specifically:
- intent `custom_formats` item: `{ trash_ids: string[], score: number | null }`
- picker's `CustomFormatEntry`: `{ trash_ids: string[], assign_scores_to: [{ name: profileName, score?: number }] }`

The transform is: `assign_scores_to: [{ name: profileName, ...(score !== null ? {score} : {}) }]`.
On `onChange`, reverse: `{ trash_ids, score: assign_scores_to[0]?.score ?? null }`.

Alternatively, the `ProfileCard` could bypass `TrashCFPicker` entirely for the CF-list
display (render its own chip list from `CustomFormatRef[]`) and use the picker only in
"add" mode, then convert the picker's output to `CustomFormatRef`. This avoids shape
mismatch complexity. The executor should choose based on how much of the picker's
display logic they want to reuse.

### Pattern 6: `diffCount` semantics change

Current `App.svelte` line 37-41:
```typescript
const diffCount = $derived(
  configState && savedConfig
    ? (JSON.stringify(configState) === JSON.stringify(savedConfig) ? 0 : 1)
    : 0
);
```

For Phase 34: `diffCount` must reflect whether the in-memory `intentState` differs from
the last-saved intent. The same `JSON.stringify` equality approach works, but the
variable tracks `intentState` vs `savedIntent` (not `configState` vs `savedConfig`).
When the intent tab is not active, `diffCount` should be 0 (no save button shown).
The UI-SPEC says diffCount reflects in-memory-intent vs last-saved-intent.

### Anti-Patterns to Avoid

- **Calling `generate_*` in the GET `/api/intent` handler.** GET should only
  load+return intent.yml. Generation happens only in diff preview and save.
- **Using `write_yaml_atomic` with `YAML(typ="rt")` for intent.yml output.** Round-trip
  preserves CommentedMap structures, but the payload comes from JSON (plain dicts).
  Use `YAML(typ="safe")` for writing intent.yml from the UI; or use a plain
  `path.write_text(ruyaml_safe_dump(payload))` pattern. The header comment will be
  lost — see Pitfall 2 for the recommended resolution.
- **Importing `ConfigarrRootConfig` from `arrconf_ui.configarr_config` to validate
  intent.configarr.** The `configarr` block is opaque pass-through (`dict[str, Any]`)
  per D-33-07; `IntentConfig.configarr` uses `dict[str, Any]` — no separate validation.
- **Dialing any \*arr API from the intent save path.** ADR-5 is absolute. The save
  handler calls `generate_*` (pure functions) and writes files only.
- **Removing GET `/api/config` or GET `/api/configarr/config`.** These feed the
  read-only inspectors (D-34-04). Keep them.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unified text diff | Custom diff algorithm | `difflib.unified_diff` (stdlib) | Already handles context lines, hunks, `@@` headers correctly |
| YAML serialization of intent payload | Manual string construction | `ruyaml.YAML(typ="safe").dump()` | Handles quoting, indentation, list formatting |
| Atomic file write | `path.write_text()` bare | `write_yaml_atomic` from `arrconf_ui.io` | Same-dir tempfile + `os.replace()` — crash-safe |
| Schema generation | Manual JSON Schema | `IntentConfig.model_json_schema()` | Already used in `schema_gen.py`; identical to `write_intent_schema` |
| Generator invocation | Subprocess `arrconf generate` | Direct import of `generate_arrconf_yml` + `generate_configarr_yml` | Editable dep already in pyproject.toml; D-34-01 locked |

**Key insight:** The entire generate pipeline is already importable from `arrconf.*`.
Phase 34 adds zero new Python dependencies.

---

## Runtime State Inventory

> Phase 34 is a code-only pivot (no rename, no data migration).

Not applicable — this is a greenfield UI pivot, not a rename or migration phase.

---

## Common Pitfalls

### Pitfall 1: `YAML(typ="rt")` vs `YAML(typ="safe")` for intent.yml write

**What goes wrong:** `write_yaml_atomic` uses `YAML(typ="rt")` (round-trip), which
works correctly for files like arrconf.yml where a `CommentedMap` is read first and
then written back. If you pass a plain Python dict (from a JSON payload) to
`write_yaml_atomic`, ruyaml's round-trip serializer works but does not produce the
canonical YAML formatting of the intent file (it may wrap strings unexpectedly or
produce different indentation).

**Why it happens:** `write_yaml_atomic` was designed for reading + writing
CommentedMap objects from existing files. JSON round-trip gives plain dicts.

**How to avoid:** For intent.yml, use `YAML(typ="safe")` with explicit settings
(`default_flow_style=False`, `yaml.indent(mapping=2, sequence=4, offset=2)`) to
produce clean YAML. Wrap the write in the same `tempfile` + `os.replace()` pattern
from `io.py` for atomicity.

**Warning signs:** Intent file content shows `flow-style` dicts `{name: foo, kind: series}`
instead of block-style, or unusual quoting.

---

### Pitfall 2: `# yaml-language-server: $schema=...` modeline lost on UI write

**What goes wrong:** The canonical `intent.yml` starts with:
```yaml
# yaml-language-server: $schema=../../../schemas/intent-schema.json
# HAND-EDITED — source of truth for 'arrconf generate'
```
When arrconf-ui writes back a JSON payload as YAML, these comment lines are not
present in the pydantic-serialized dict and will be dropped.

**Why it happens:** Pydantic `model_dump(mode='json')` returns pure Python dicts —
no YAML comments survive the JSON round-trip. `YAML(typ="safe")` does not preserve
source comments.

**How to avoid:** Two options for the executor (Claude's discretion):
1. Prepend the two header lines to the YAML string before writing (hardcode the
   relative path `../../../schemas/intent-schema.json`).
2. Accept the loss and add a note in the CI `generate-idempotence` check (the guard
   uses `arrconf generate --check` which ignores YAML comments). The header is a
   developer convenience, not a correctness requirement.

Option 1 is cleaner. Option 2 is acceptable since the CI check doesn't verify
the header, only the content.

**Warning signs:** VS Code YAML language server stops offering autocomplete after
a UI save because the `$schema` modeline is gone.

---

### Pitfall 3: `TrashCFPicker` props shape mismatch with `CustomFormatRef`

**What goes wrong:** `TrashCFPicker` expects `existingCustomFormats` to be
`{ trash_ids: string[]; assign_scores_to: [...] }[]` — the configarr.yml
cross-profile format. But `IntentConfig.profile_definitions[name].custom_formats`
is `CustomFormatRef[]` — the intent per-profile format `{ trash_ids: string[], score: number | null }`.

**Why it happens:** The picker was written for the configarr tab where CFs are stored
cross-profile. Intent stores them per-profile with a flat `score` field.

**How to avoid:** `ProfileCard.svelte` adapts the shape before passing to the picker,
and reverses the transform in `onChange`. Specifically (from Pattern 5 above):
incoming `assign_scores_to` always has exactly one entry (the current profile name).
See Pattern 5 for full transform spec.

**Warning signs:** Picker shows all CFs as "already added" (because `existingIds` set
gets built from wrong shape), or `onChange` produces garbled `assign_scores_to` arrays.

---

### Pitfall 4: `generate-idempotence` CI guard failing after save

**What goes wrong:** After a UI save that writes intent.yml + regenerates arrconf.yml
+ configarr.yml, a subsequent `arrconf generate --check` in CI may still detect drift
if the files were not written in the correct format.

**Why it happens:** `generate_arrconf_yml` produces a YAML string with
`_ARRCONF_HEADER` (3-line comment block) prepended. If the UI save writes arrconf.yml
as a plain YAML dump (without the header), the idempotence check will fail — the header
is part of the expected content.

**How to avoid:** The save handler calls `generate_arrconf_yml(intent_cfg)` and
`generate_configarr_yml(intent_cfg)` and writes their return value verbatim to disk —
these functions already include their headers. Do NOT write a separate YAML dump of
arrconf.yml; only write the string returned by the generator.

**Warning signs:** `generate-idempotence` CI job fails after a UI save with
`generate_drift` log event on arrconf.yml or configarr.yml.

---

### Pitfall 5: `put_config` and `put_configarr_config` called by tests

**What goes wrong:** Existing backend tests in `test_app_endpoints.py` and
`test_configarr_endpoints.py` call `PUT /api/config` and `PUT /api/configarr/config`
via `TestClient`. When these endpoints are removed, those tests will fail.

**Why it happens:** D-34-04 removes PUT endpoints for generated files, but existing
tests test those endpoints.

**How to avoid:** When removing PUT endpoints, also update/remove the corresponding
tests. The test for PUT `/api/config` that should be DELETED:
`test_put_config_with_valid_payload_writes_and_returns_diff`,
`test_put_config_with_invalid_payload_returns_422`, and the configarr equivalents in
`test_configarr_endpoints.py`. New tests for the intent endpoints should replace them.

**Warning signs:** `uv run pytest -q` fails on endpoint tests that test PUT on generated files.

---

### Pitfall 6: `mypy` strict on new `arrconf.*` imports

**What goes wrong:** `pyproject.toml` for arrconf-ui has:
```toml
[[tool.mypy.overrides]]
module = ["arrconf.*"]
ignore_missing_imports = true
```
This means mypy will not type-check the arrconf imports — but the CI gate runs
`uv run mypy .` which checks `arrconf_ui/` package. Any incorrect usage of
`generate_arrconf_yml`, `generate_configarr_yml`, `load_intent`, `IntentConfig` will
NOT be caught by mypy (the stubs are silenced). The test suite is the real type guard.

**How to avoid:** Verify function signatures from source (already done in this
research — see exact signatures below in Code Examples). Write tests that exercise
the full round-trip.

---

## Code Examples

### Verified: `generate_arrconf_yml` signature

```python
# Source: tools/arrconf/arrconf/generators/intent.py line 209
def generate_arrconf_yml(intent_cfg: IntentConfig) -> str:
    """Pure: IntentConfig -> arrconf.yml content (apps pass-through)."""
    # Returns: _ARRCONF_HEADER + ruyaml safe dump of sort_dict(dict(intent_cfg.apps))
```

**The function only emits `intent_cfg.apps`.** It does NOT emit `categories`, `sagas`,
`tools`, `profile_definitions`, or `configarr`. Categories materialize at `apply` time.
This is by design (D-32-01).

### Verified: `generate_configarr_yml` signature

```python
# Source: tools/arrconf/arrconf/generators/configarr.py line 56
def generate_configarr_yml(intent_cfg: IntentConfig) -> str:
    """Pure function: IntentConfig -> configarr.yml content string.
    Includes _CONFIGARR_HEADER. Unconditional (D-33-08)."""
    # Algorithm: deep-copy configarr skeleton, inject quality_profiles + custom_formats
    # per instance based on categories routing. Post-process !env tags.
```

### Verified: `load_intent` signature

```python
# Source: tools/arrconf/arrconf/intent_config.py line 259
def load_intent(path: Path) -> IntentConfig:
    """Raises ConfigError for missing file, YAML parse failure, or validation failure."""
```

### Verified: `IntentConfig` fields

```python
# Source: tools/arrconf/arrconf/intent_config.py lines 206-256
class IntentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tools: ToolsConfig          # cross_seed | None, qbit_manage | None
    sagas: list[SagaEntry]
    categories: list[MediaCategory]
    apps: dict[str, Any]        # pass-through → arrconf.yml
    profile_definitions: dict[str, ProfileDefinition]  # keyed by configarr profile name
    configarr: dict[str, Any]   # pass-through skeleton → configarr.yml
```

`ProfileDefinition` fields (D-33-06):
```python
class ProfileDefinition(BaseModel):
    body: dict[str, Any]                  # QP fields — opaque
    custom_formats: list[CustomFormatRef] # [{trash_ids: list[str], score: int | None}]
```

`CustomFormatRef` fields:
```python
class CustomFormatRef(BaseModel):
    trash_ids: list[str]         # CF ids (TRaSH or local)
    score: int | None            # per-profile override; None → use CF default
```

### Verified: `write_intent_schema` — existing CLI for intent schema

```python
# Source: tools/arrconf/arrconf/schema_gen.py line 37
def write_intent_schema(output_path: Path) -> None:
    """Write IntentConfig JSON Schema reproducibly (sort_keys=True)."""
    schema = IntentConfig.model_json_schema(schema_generator=Draft202012Generator)
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

`/api/intent/schema` endpoint can use `IntentConfig.model_json_schema()` directly —
no need to read the committed `schemas/intent-schema.json` file (unlike the arrconf
schema endpoint which reads from disk). Either approach works; reading from disk is
consistent with the existing pattern and avoids runtime schema generation on every
request.

### Verified: Existing test fixture pattern for intent endpoints

```python
# Source: tools/arrconf-ui/tests/conftest.py — sandboxed_arrconf_yml pattern
# New fixture for intent follows same pattern:
@pytest.fixture
def sandboxed_intent_yml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    target = tmp_path / "intent.yml"
    shutil.copy(CANONICAL_INTENT_YML, target)
    monkeypatch.setattr("arrconf_ui.locator.intent_yml_path", lambda: target)
    monkeypatch.setattr("arrconf_ui.app.intent_yml_path", lambda: target)
    yield target
```

Where `CANONICAL_INTENT_YML = REPO_ROOT / "charts" / "arr-stack" / "files" / "intent.yml"`.

The sandboxed pattern also needs to patch `arrconf_yml_path` and `configarr_yml_path`
in the save test so the regenerated files don't overwrite real files. The save test
needs THREE sandboxed paths: intent, arrconf, configarr.

### Verified: Frontend `ActiveConfig` union — current state

```typescript
// Source: tools/arrconf-ui/web/src/constants.ts lines 40-44
export const CONFIG_FILE_PATHS = {
  arrconf: 'charts/arr-stack/files/arrconf.yml',
  configarr: 'charts/arr-stack/files/configarr.yml',
} as const;
export type ActiveConfig = keyof typeof CONFIG_FILE_PATHS;
// Currently: 'arrconf' | 'configarr'
// Phase 34: add 'intent' as primary + keep arrconf/configarr as inspect tabs
```

### Verified: Existing `HeaderBar.svelte` tab mechanism

```typescript
// Source: tools/arrconf-ui/web/src/lib/HeaderBar.svelte lines 28-31
<button type="button" class="tab" class:tab-active={activeConfig === 'arrconf'}
  onclick={() => onTabChange('arrconf')}>arrconf.yml</button>
<button type="button" class="tab" class:tab-active={activeConfig === 'configarr'}
  onclick={() => onTabChange('configarr')}>configarr.yml</button>
// Phase 34: add third button for 'intent', reorder to [intent | arrconf | configarr]
// Save button visible only when activeConfig === 'intent' (D-34-04/UI-SPEC)
```

### Verified: `difflib.unified_diff` API (stdlib)

```python
import difflib

lines_a = "line1\nline2\nline3\n".splitlines()
lines_b = "line1\nline2-modified\nline3\n".splitlines()
diff = "\n".join(difflib.unified_diff(
    lines_a, lines_b,
    fromfile="arrconf.yml (actuel)",
    tofile="arrconf.yml (généré)",
    lineterm=""   # prevent double newlines
))
# Returns unified diff string with @@ headers, +/- lines, context
```

When `lines_a == lines_b`, `unified_diff` returns an empty iterator → `diff == ""`.
Use `bool(diff)` to determine `has_changes`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Edit arrconf.yml directly via UI | Edit intent.yml via UI | Phase 34 | Backend pivot; arrconf.yml becomes generated |
| PUT /api/config writes arrconf.yml | PUT /api/intent writes intent.yml + regenerates both | Phase 34 | Removes risk of editing generated files |
| Two-tab state machine (arrconf/configarr) | Three-tab state machine (intent/arrconf-inspect/configarr-inspect) | Phase 34 | intent.yml = primary editable; others = read-only |
| Semantic field-level diff (DiffPanel) | Unified text diff of generated files (MaterializationDiffPanel) | Phase 34 | Shows exact bytes to be committed |
| TRaSH picker mounted globally in configarr section | TRaSH picker mounted per-profile in ProfileCard | Phase 34 | Locality: picker writes to the profile it's inside |

**Kept unchanged:**
- `DiffPanel.svelte` — still used for the arrconf/configarr semantic diff path (if
  the read-only GET+semantic diff flow is kept for reference); or can be kept as dead code
  until removal. The Phase 34 intent flow uses `MaterializationDiffPanel` instead.
- `/api/trash/*` endpoints — reused as-is (D-34-05).
- `CategoriesEditor.svelte` — reused as-is for `intent.categories`.
- `AppSection.svelte` — reused for `sagas`, `apps`, `tools` schema-driven sections.
- `generate-idempotence` CI guard — kept green by D-34-06 (save always regenerates).

---

## Endpoint Surface Diff (complete)

### Removed from `app.py`

| Endpoint | Method | Reason |
|----------|--------|--------|
| `/api/config` | PUT | D-34-04: arrconf.yml is generated, not hand-edited |
| `/api/configarr/config` | PUT | D-34-04: configarr.yml is generated, not hand-edited |

### Kept unchanged in `app.py`

| Endpoint | Method | Notes |
|----------|--------|-------|
| `/api/config` | GET | Read-only inspector for arrconf.yml (D-34-04) |
| `/api/configarr/config` | GET | Read-only inspector for configarr.yml (D-34-04) |
| `/api/diff` | POST | Still valid (semantic diff for arrconf if ever needed) |
| `/api/schema` | GET | Still valid |
| `/api/configarr/diff` | POST | Still valid |
| `/api/configarr/schema` | GET | Still valid |
| `/api/trash/custom-formats` | GET | Reused as-is (D-34-05) |
| `/api/trash/quality-profiles` | GET | Reused as-is (D-34-05) |
| `/api/trash/recyclarr-templates` | GET | Reused as-is (D-34-05) |

### Added to `app.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/intent` | GET | Load + return `IntentConfig.model_dump(mode='json')` |
| `/api/intent` | PUT | Validate → write intent.yml → regenerate arrconf.yml + configarr.yml |
| `/api/intent/diff` | POST | Stateless: generate from payload → unified text diff vs on-disk |
| `/api/intent/schema` | GET | Return `IntentConfig.model_json_schema()` or read `schemas/intent-schema.json` |

---

## Environment Availability

Step 2.6: SKIPPED — Phase 34 is pure code changes to `tools/arrconf-ui/**`. No
external tools, services, runtimes, or databases beyond what is already installed
in the development environment.

`difflib` is Python stdlib — no installation needed.

---

## Assumptions Log

All claims in this research were verified by direct codebase read in this session.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `write_yaml_atomic` will be adapted for intent.yml (or a parallel `_write_text_atomic` helper used) | Pattern 3 | If executor reuses `write_yaml_atomic` directly with a plain dict, output format may vary |
| A2 | The `# yaml-language-server` modeline loss is acceptable (CI idempotence check ignores it) | Pitfall 2 | If a future CI check verifies the modeline, the UI save will break that check |
| A3 | `TrashCFPicker.profileNames` can receive a single-element list `[profileName]` for the per-profile picker | Pattern 5 | If picker logic breaks with single-element profileNames, executor must test this case |

**All other claims are VERIFIED from direct codebase reads (HIGH confidence).**

---

## Open Questions

1. **Should `PUT /api/intent` also return the generated diffs?**
   - What we know: The existing `PUT /api/config` returns `{diff, has_changes}`. The
     intent save could similarly return `{arrconf_diff, configarr_diff, has_changes}`.
   - What's unclear: The UI-SPEC says the diff is shown via `MaterializationDiffPanel`
     BEFORE the save — so post-save diff is less critical. But it's useful for logging.
   - Recommendation: Return `{saved: true, arrconf_written: bool, configarr_written: bool}`.
     The diff is computed pre-save via `/api/intent/diff`; no need to re-run it on save.

2. **Does `GET /api/intent` return raw YAML or parsed JSON?**
   - What we know: `GET /api/config` returns `RootConfig.model_dump(mode='json')` —
     a validated, normalized JSON dict. The frontend binds this to form state.
   - Recommendation: Follow the same pattern — return `IntentConfig.model_dump(mode='json')`.
     This gives the frontend a clean JSON payload to bind. The `apps` and `configarr` fields
     are `dict[str, Any]` — they pass through as-is.

3. **Does `DiffPanel.svelte` stay or get removed?**
   - What we know: DiffPanel is used for the arrconf/configarr semantic diff flow.
     Phase 34 removes PUT endpoints for those, so there's no trigger to open DiffPanel
     for arrconf/configarr anymore. But the component is not explicitly "removed" by
     any decision.
   - Recommendation: Keep `DiffPanel.svelte` but stop importing it in `App.svelte`
     (dead code, not deleted in Phase 34). A future cleanup phase can remove it.

---

## Sources

### Primary (HIGH confidence — direct codebase reads)

- `tools/arrconf-ui/arrconf_ui/app.py` — complete endpoint surface (11 endpoints)
- `tools/arrconf-ui/arrconf_ui/locator.py` — path resolution (5 functions; `intent_yml_path` absent)
- `tools/arrconf-ui/arrconf_ui/io.py` — `write_yaml_atomic`, `read_yaml` patterns
- `tools/arrconf/arrconf/generators/intent.py` — `generate_arrconf_yml`, `sort_dict` signatures
- `tools/arrconf/arrconf/generators/configarr.py` — `generate_configarr_yml` signature
- `tools/arrconf/arrconf/intent_config.py` — `IntentConfig`, `ProfileDefinition`, `CustomFormatRef`, `load_intent`
- `tools/arrconf/arrconf/__main__.py` — `generate()` command reference
- `tools/arrconf/arrconf/schema_gen.py` — `write_intent_schema`
- `tools/arrconf-ui/web/src/App.svelte` — current two-tab state machine (266 lines)
- `tools/arrconf-ui/web/src/api.ts` — all existing frontend API functions
- `tools/arrconf-ui/web/src/types.ts` — `ConfigPayload`, `SemanticDiff`, `DiffResponse`
- `tools/arrconf-ui/web/src/constants.ts` — `APP_SECTIONS`, `CONFIG_FILE_PATHS`, `ActiveConfig`
- `tools/arrconf-ui/web/src/lib/TrashCFPicker.svelte` — props shape (critical for Pitfall 3)
- `tools/arrconf-ui/web/src/lib/DiffPanel.svelte` — existing diff display pattern
- `tools/arrconf-ui/web/src/lib/HeaderBar.svelte` — tab implementation
- `tools/arrconf-ui/tests/conftest.py` — sandboxed fixture pattern
- `tools/arrconf-ui/pyproject.toml` — confirmed `arrconf` editable dep
- `.github/workflows/tests.yml` — `generate-idempotence` guard definition
- `.planning/phases/34-ui-over-intent/34-CONTEXT.md` — locked decisions D-34-01..06
- `.planning/phases/34-ui-over-intent/34-UI-SPEC.md` — component inventory, copy, typography

### Secondary

- `schemas/intent-schema.json` — confirmed exists (10.5K, committed) [VERIFIED]
- `charts/arr-stack/files/intent.yml` — confirmed `# yaml-language-server` modeline present [VERIFIED]

---

## Metadata

**Confidence breakdown:**
- Endpoint surface map: HIGH — read every line of app.py
- Generator signatures + return types: HIGH — read generators/intent.py + generators/configarr.py
- Frontend component state machine: HIGH — read App.svelte + HeaderBar + constants
- TrashCFPicker prop shape: HIGH — read TrashCFPicker.svelte directly
- Test fixture patterns: HIGH — read conftest.py
- `difflib.unified_diff` API: HIGH — Python stdlib, well-known
- Pitfall 3 (picker shape mismatch): HIGH — verified by comparing `CustomFormatRef` vs picker props

**Research date:** 2026-06-08
**Valid until:** Stable — all claims are from the local codebase, not external sources.
Re-verify only if generators or the picker component are modified before Phase 34 execution.
