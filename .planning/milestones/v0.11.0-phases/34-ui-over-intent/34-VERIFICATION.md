---
phase: 34-ui-over-intent
verified: 2026-06-08T12:00:00Z
status: human_needed
score: 4/4
overrides_applied: 0
human_verification:
  - test: "Open arrconf-ui in browser (uv run uvicorn arrconf_ui.app:app --reload). Confirm the UI lands on the intent.yml tab by default, with three tabs visible (intent.yml | arrconf.yml | configarr.yml). Click arrconf.yml — verify a 'généré — lecture seule' badge appears and no save button is shown. Click configarr.yml — same. Click back to intent.yml — verify save button reappears."
    expected: "Three tabs visible; intent.yml default active; save button only on intent tab; 'généré — lecture seule' badge on arrconf/configarr tabs with no save button."
    why_human: "Tab visibility, badge display, and save-button conditional rendering require visual inspection. Cannot grep-verify CSS display:none vs absence."
  - test: "On the intent.yml tab, edit any field (e.g., change a category name). Verify the diff-count chip increments. Click Save. Verify MaterializationDiffPanel appears with two labelled sections (arrconf.yml + configarr.yml) and diff lines colorized (+ green, - red). Click 'Confirmer et enregistrer'. Verify a toast confirmation appears and diffCount resets to 0."
    expected: "MaterializationDiffPanel shows arrconf_diff and configarr_diff from the real generator. Toast shown on successful save. diffCount returns to 0."
    why_human: "End-to-end save flow requires a live browser + live backend. The diff panel rendering and toast UX cannot be verified programmatically."
  - test: "On the intent.yml tab, open the profile_definitions section. Verify a ProfileCard renders for each existing profile with a body textarea, CF chip list with per-chip score inputs, and the TRaSH CF/QP pickers. Add a new profile name in the 'Nom du profil' input and click '+ Ajouter un profil' — verify a new empty ProfileCard appears."
    expected: "ProfileDefinitionsEditor renders existing profiles via ProfileCard. Add flow creates a new empty profile. TRaSH pickers visible per profile."
    why_human: "Profile editing UX with picker integration requires live browser interaction. Cannot grep-verify component rendering state."
---

# Phase 34: UI Over Intent — Verification Report

**Phase Goal:** arrconf-ui édite intent.yml comme seule source, les formulaires legacy arrconf.yml/configarr.yml sont retirés (read-only), et l'opérateur peut visualiser le diff généré avant commit.
**Verified:** 2026-06-08T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | intent.yml is the sole editable source — load/modify/save works end-to-end; arrconf.yml/configarr.yml are read-only | ✓ VERIFIED | `GET /api/intent`, `PUT /api/intent`, `POST /api/intent/diff` fully implemented in app.py (lines 146–268). `put_config` and `put_configarr_config` functions absent (grep confirms 0 matches). 8 intent endpoint tests pass (8/8). |
| 2 | Legacy arrconf.yml/configarr.yml forms removed or read-only; GET inspectors retained | ✓ VERIFIED | `putConfig` and `putConfigarrConfig` absent from api.ts (0 matches). D-34-04 comment present. `GET /api/config` and `GET /api/configarr/config` retained. `ReadOnlyInspector.svelte` exists with no save button and no putIntent/putConfig calls. Test `test_put_config_endpoint_removed` passes (405). |
| 3 | TRaSH/Recyclarr CF/QP picker integrated into intent form — per-profile, not cross-profile | ✓ VERIFIED | `ProfileCard.svelte` mounts `TrashCFPicker` + `TrashQPPicker` per profile. `CustomFormatRef[] <-> CustomFormatEntry[]` shape transform via `assign_scores_to[0]` present (1 grep match). `ProfileDefinitionsEditor.svelte` renders one ProfileCard per profile key. Wired into `App.svelte` `{#if activeConfig === 'intent'}` branch. |
| 4 | Diff panel shows generated files produced by REAL generators — not stub/mock | ✓ VERIFIED | `POST /api/intent/diff` calls `generate_arrconf_yml(intent_cfg)` + `generate_configarr_yml(intent_cfg)` directly imported from `arrconf.generators.intent` / `arrconf.generators.configarr` (real package, not mock). Test `test_post_intent_diff_unchanged_has_no_changes` asserts `has_changes == false` when files are pre-regenerated to match — proves generators are the same codepath. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/arrconf-ui/arrconf_ui/locator.py` | `intent_yml_path()` + `intent_schema_json_path()` | ✓ VERIFIED | Both functions present (lines 47–54). Follow existing pattern. |
| `tools/arrconf-ui/arrconf_ui/app.py` | 4 intent endpoints; 2 PUT endpoints removed | ✓ VERIFIED | GET/GET-schema/POST-diff/PUT all present. `def put_config` and `def put_configarr_config` both absent. `generate_arrconf_yml` called 2× (diff + save), `generate_configarr_yml` called 2×. |
| `tools/arrconf-ui/tests/test_intent_endpoints.py` | 8 contract tests incl. `test_put_intent_writes_intent_yml_and_regenerates_both_files` | ✓ VERIFIED | File exists, 8 tests all pass (pytest output: `8 passed`). Regeneration assertion uses real `load_intent` + generators. |
| `tools/arrconf-ui/web/src/lib/MaterializationDiffPanel.svelte` | Two labelled diff blocks + confirm/cancel | ✓ VERIFIED | Contains `Matérialisation — vérifier avant d'enregistrer`, `arrconf.yml`, `configarr.yml`, `Confirmer et enregistrer`, `Aucune modification`. Diff line colorization with `#10b981` / `var(--destructive)` / `var(--accent)`. |
| `tools/arrconf-ui/web/src/lib/ReadOnlyInspector.svelte` | Raw YAML pre block + read-only badge; no save | ✓ VERIFIED | Contains `lecture seule`, `class="inspector"`, `--code-bg`. No `putIntent`/`putConfig` calls. No save button. |
| `tools/arrconf-ui/web/src/api.ts` | `getIntent`/`getIntentSchema`/`postIntentDiff`/`putIntent`; no `putConfig`/`putConfigarrConfig` | ✓ VERIFIED | All 4 intent functions present (lines 75–94). `putConfig` fully absent (0 grep matches). D-34-04 comment present. |
| `tools/arrconf-ui/web/src/constants.ts` | `intent` first key in `CONFIG_FILE_PATHS`; `INTENT_SECTIONS` exported | ✓ VERIFIED | `intent: 'charts/arr-stack/files/intent.yml'` is first key (line 41). `INTENT_SECTIONS` with 6 keys present (lines 48–55). |
| `tools/arrconf-ui/web/src/lib/ProfileCard.svelte` | TrashCFPicker + TrashQPPicker + CF chips + score inputs + inline delete | ✓ VERIFIED | Contains `TrashCFPicker`, `TrashQPPicker`, `assign_scores_to`, `PROFILE_BODY_LABEL`, `aria-label="Retirer le format`, `aria-label="Supprimer le profil`. No `base_url`/`http` calls (0 matches). |
| `tools/arrconf-ui/web/src/lib/ProfileDefinitionsEditor.svelte` | Add/delete profiles; renders ProfileCard per key | ✓ VERIFIED | Contains `ProfileCard`, `Ajouter un profil`, duplicate name guard (`Le profil "${name}" existe déjà.`), `inferApp()` heuristic. |
| `tools/arrconf-ui/web/src/lib/ConfigarrRawEditor.svelte` | Opaque YAML textarea; pass-through helper text | ✓ VERIFIED | Contains `pass-through` HTML comment, `raw-editor`, `--code-bg`, `CONFIGARR_RAW_HELPER` from fr.ts. |
| `tools/arrconf-ui/web/src/i18n/fr.ts` | 6 `intent.*` SECTION_DOCS keys + 7 string constants | ✓ VERIFIED | All 6 `intent.*` keys present (lines 97–117). `READONLY_BADGE_TEXT`, `MATERIALIZATION_EMPTY_TEXT`, `CONFIGARR_RAW_HELPER`, `ADD_PROFILE_TEXT`, `SCORE_OVERRIDE_PLACEHOLDER` all present (lines 455–462). |
| `tools/arrconf-ui/web/src/App.svelte` | Three-tab machine; updateIntent; 6 ordered sections; 34-03 marker removed | ✓ VERIFIED | `activeConfig = $state<ActiveConfig>('intent')` (line 39). `updateIntent()` helper (lines 129–131). All 6 ordered sections present with SectionDoc + components. `34-03: mount intent form sections here` marker absent (0 grep matches). `MaterializationDiffPanel` and `ReadOnlyInspector` both mounted. |
| `tools/arrconf-ui/web/src/lib/HeaderBar.svelte` | 3 tabs; save button intent-only; read-only badge on inspect tabs | ✓ VERIFIED | Three `onTabChange()` calls for 'intent', 'arrconf', 'configarr'. Save button gated `{#if activeConfig === 'intent'}`. `showReadOnlyBadge` derived as `activeConfig !== 'intent'`. `généré — lecture seule` pill present. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py` | `arrconf.generators.intent.generate_arrconf_yml` | direct import | ✓ WIRED | Line 46: `from arrconf.generators.intent import generate_arrconf_yml`. Called at lines 194, 264. |
| `app.py` | `arrconf.generators.configarr.generate_configarr_yml` | direct import | ✓ WIRED | Line 45: `from arrconf.generators.configarr import generate_configarr_yml`. Called at lines 195, 265. |
| `app.py` | `arrconf.intent_config.load_intent / IntentConfig` | direct import | ✓ WIRED | Line 47: `from arrconf.intent_config import IntentConfig, load_intent`. Used in all 4 intent handlers. |
| `App.svelte` | `api.postIntentDiff / api.putIntent` | `openDiffPanel` + `confirmSave` | ✓ WIRED | `openDiffPanel()` calls `api.postIntentDiff(intentState)` (line 93). `confirmSave()` calls `api.putIntent(intentState)` (line 109). |
| `App.svelte` | `ReadOnlyInspector` via `GET /api/config` + `/api/configarr/config` | inspect tab branch | ✓ WIRED | Both `{:else if activeConfig === 'arrconf'}` and `{:else}` branches render `<ReadOnlyInspector>` with `content={inspectorContent}` populated by `loadForConfig()`. |
| `HeaderBar.svelte` | three-tab `onTabChange` | tab buttons | ✓ WIRED | Three `onclick={() => onTabChange('<key>')}` calls for 'intent', 'arrconf', 'configarr' (lines 34–39). |
| `ProfileCard.svelte` | `TrashCFPicker` | `CustomFormatRef[] <-> CustomFormatEntry[]` shape transform | ✓ WIRED | `pickerCFs` derived via `assign_scores_to` transform. `handleCFChange` reads `assign_scores_to[0]?.score`. Passed as `existingCustomFormats={pickerCFs}`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `app.py POST /api/intent/diff` | `new_arrconf`, `new_configarr` | `generate_arrconf_yml(intent_cfg)` / `generate_configarr_yml(intent_cfg)` — real arrconf package functions | Yes — generators call into `arrconf.generators.*` with full `IntentConfig` | ✓ FLOWING |
| `app.py PUT /api/intent` | `intent_text` | YAML safe-dump of validated `IntentConfig` payload | Yes — written atomically to intent.yml; generated files written verbatim | ✓ FLOWING |
| `App.svelte intentState` | `intent`, `schema` | `api.getIntent()` + `api.getIntentSchema()` via `Promise.all` on load | Yes — calls real backend endpoints; `savedIntent` deep-cloned for diffCount | ✓ FLOWING |
| `MaterializationDiffPanel` | `arrconfDiff`, `configarrDiff` | `api.postIntentDiff(intentState)` → backend calls real generators | Yes — not hardcoded; `pendingMatDiff` set from live response | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 8 intent endpoint tests pass | `uv run --project tools/arrconf-ui pytest tests/test_intent_endpoints.py -q` | `8 passed` | ✓ PASS |
| Full backend suite: 72 pass, 3 pre-existing failures | `uv run --project tools/arrconf-ui pytest -q` | `3 failed, 72 passed` — failures are pre-existing `test_io_roundtrip.py` | ✓ PASS |
| Frontend build artifacts present | `ls tools/arrconf-ui/web/dist/` | `index.html` + `assets/` present | ✓ PASS |
| PUT /api/config returns 405 | test `test_put_config_endpoint_removed` | `405` | ✓ PASS |
| Generator called in diff (not stub) | `grep generate_arrconf_yml app.py` | 4 lines: import + 2 calls (diff + save) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| UI-01 | 34-01, 34-02, 34-03 | `arrconf-ui` loads and edits `intent.yml` as the only editable source | ✓ SATISFIED | `GET /api/intent`, `PUT /api/intent` implemented and tested. All 6 intent form sections wired in `App.svelte`. `updateIntent()` drives diffCount + save. |
| UI-02 | 34-01, 34-02 | Legacy arrconf.yml + configarr.yml forms removed or read-only | ✓ SATISFIED | `putConfig` / `putConfigarrConfig` removed from backend and api.ts. `ReadOnlyInspector` renders generated files with badge. Tests assert 405 on PUT /api/config. |
| UI-03 | 34-03 | TRaSH/Recyclarr CF/QP picker integrated into intent edit flow | ✓ SATISFIED | `ProfileCard.svelte` mounts `TrashCFPicker` + `TrashQPPicker` per-profile with `CustomFormatRef <-> CustomFormatEntry` shape transform. Picker writes per-profile `{trash_ids, score}` refs. |
| UI-04 | 34-01, 34-02 | UI exposes `generate` output (diff of generated configs) before commit | ✓ SATISFIED | `POST /api/intent/diff` returns two unified text diffs from real generators. `MaterializationDiffPanel` renders them. `openDiffPanel()` flow wired in `App.svelte`. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `ProfileCard.svelte` | 5, 68 | `PROFILE_NAME_PLACEHOLDER` / `SCORE_OVERRIDE_PLACEHOLDER` — variable name contains "PLACEHOLDER" | ℹ️ Info | These are i18n constant names, not implementation stubs. The values are UI strings imported from `fr.ts`. Not a stub indicator. |

No blockers found. The "placeholder" references are i18n constant names (a naming convention), not implementation stubs.

### Human Verification Required

All 4 observable truths are VERIFIED by code inspection and automated tests. The 3 items below require live browser testing for the visual/interaction layer that cannot be confirmed programmatically.

#### 1. Three-Tab Navigation and Read-Only Badge

**Test:** Launch `uv run uvicorn arrconf_ui.app:app --reload` from `tools/arrconf-ui`. Open `http://localhost:8000`. Verify the UI displays three tabs labeled `intent.yml`, `arrconf.yml`, `configarr.yml` with `intent.yml` active by default. Click `arrconf.yml` — confirm "généré — lecture seule" badge appears and no save button is rendered. Click `configarr.yml` — same. Click back to `intent.yml` — confirm save button reappears.
**Expected:** Three tabs visible; intent.yml default active; save button only on intent tab; read-only badge on arrconf/configarr tabs.
**Why human:** Tab visibility and conditional save button require a rendering browser. The conditional `{#if activeConfig === 'intent'}` is code-verified but the visual outcome needs observation.

#### 2. Save Flow with MaterializationDiffPanel

**Test:** On the intent.yml tab, modify a field (e.g., change a category name in the categories section). Verify the diff-count chip changes. Click Save (Enregistrer). Verify the `MaterializationDiffPanel` appears showing two labelled sections (`arrconf.yml` + `configarr.yml`) with colorized diff lines. Click "Confirmer et enregistrer". Verify the save toast appears and diffCount returns to 0.
**Expected:** MaterializationDiffPanel shows non-empty diffs colored green/red. Toast on success. diffCount resets.
**Why human:** The live diff panel rendering, diff colorization, and toast UX require a running browser + backend with a real intent.yml on disk.

#### 3. ProfileDefinitionsEditor — TRaSH Picker Per-Profile

**Test:** On the intent.yml tab, scroll to the `profile_definitions` section. Verify one ProfileCard is rendered per existing profile. Expand a ProfileCard — verify body textarea, CF chip list with per-chip score inputs, and TrashCFPicker below are rendered. In the "Nom du profil" input, enter a new profile name and click "+ Ajouter un profil" — verify a new empty ProfileCard appears.
**Expected:** Profiles are collapsible cards with all editing controls. TRaSH picker visible. Add flow creates new empty profile. Duplicate name guard shows error on re-entry.
**Why human:** The TrashCFPicker loads data from `/api/trash/custom-formats` (baked catalogue); the live rendering with real catalogue data requires browser inspection.

### Gaps Summary

No gaps. All 4 success criteria are verified at the code/test level. The 3 pre-existing `test_io_roundtrip.py` failures are explicitly out of scope (confirmed pre-existing at base commit `faf7f5b`; caused by Phase 32 CATMIG hard cut changing arrconf.yml format, not by this phase).

Status is `human_needed` because visual/interaction behaviors (tab rendering, diff panel UX, picker rendering) cannot be confirmed programmatically and require live browser testing.

---

_Verified: 2026-06-08T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
