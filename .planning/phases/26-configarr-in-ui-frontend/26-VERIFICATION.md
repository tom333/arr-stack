---
phase: 26-configarr-in-ui-frontend
verified: 2026-05-30T05:52:20Z
status: passed
score: 3/3 must-haves verified (SC#1 programmatic; SC#2 + SC#3 operator-confirmed post-CR-01-fix 2026-05-30)
human_verification_result: "Operator re-verified SC#2 (quality_definition + media_naming render disabled + lock badge at all nested leaves after commit 33c4c4b) and SC#3 (score edit → diff shows only changed field → save round-trips, !env/!secret tags + comments + key order preserved) against the running UI. Approved 2026-05-30."
overrides_applied: 0
human_verification:
  - test: "SC#1 and SC#2 re-verification after CR-01 fix"
    expected: "arrconf.yml / configarr.yml tab selector switches without page reload; quality_definition and media_naming render as disabled + lock badge (not editable); api_key reads as disabled string"
    why_human: "CR-01 was fixed after the original operator checkpoint (commit 33c4c4b). The checkpoint that approved SC#2 occurred before the fix and was done against the broken isReadOnly formula. No frontend tests exist (WR-04). The corrected formula reads schema.readOnly on the raw node before effectiveNode() strips it — logically sound — but only a browser session against the running UI on the configarr tab can confirm the readOnly subtree behaviour is now correct."
  - test: "SC#3 — editing a quality-profile score, diff preview, and save round-trip"
    expected: "Diff panel shows only the changed score field. After confirming save, git diff charts/arr-stack/files/configarr.yml shows: (a) only the score line changed, (b) every !env/!secret tag is verbatim, (c) comments and key order preserved. Revert with git checkout charts/arr-stack/files/configarr.yml."
    why_human: "SC#3 requires a running arrconf-ui instance connected to the Phase 25 backend. The operator approved SC#3 in the human checkpoint (26-02-SUMMARY.md, Task 3), but because that checkpoint predates the CR-01 fix commit (33c4c4b), the save round-trip should be re-confirmed. The static wiring check (postConfigarrDiff / putConfigarrConfig dispatch in App.svelte lines 75-95) is verified programmatically — only the end-to-end diff/save behavior needs the human run."
---

# Phase 26: configarr-in-UI frontend — Verification Report

**Phase Goal:** Operators can select, view, and edit `configarr.yml` from the arrconf-ui web interface alongside `arrconf.yml`, using the same schema-driven form pattern.
**Verified:** 2026-05-30T05:52:20Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The arrconf-ui web UI displays a config selector (tab/dropdown) allowing switch between arrconf.yml and configarr.yml without a page reload | ✓ VERIFIED | `HeaderBar.svelte` lines 26-33: `{#if onTabChange}` nav with two `<button class="tab">` elements; `App.svelte` line 129-134 passes `{activeConfig}` + `onTabChange={requestTabChange}`; `requestTabChange` calls `doSwitch` which updates `activeConfig` state and calls `loadForConfig` — no `location.reload()` or full-page navigation |
| 2 | After selecting configarr.yml, the form renders quality profiles, custom formats, and scores via the FieldInput dispatcher; quality_definition and media_naming appear read-only | ? UNCERTAIN | Wiring verified: (a) configarr section filter on `additionalProperties != null` correctly produces sonarr+radarr (App.svelte lines 182-183); (b) the CR-01 fix (commit 33c4c4b) corrects `isReadOnly = $derived(readOnly \|\| schema.readOnly === true \|\| effective.readOnly === true)` — `schema.readOnly` reads the raw node before anyOf stripping; (c) configarr-schema.json confirms `media_naming` and `quality_definition` carry `readOnly: true` on their anyOf wrapper. However: the human checkpoint that approved SC#2 predates the fix. Needs re-confirmation in the running UI. |
| 3 | Editing a quality-profile score and saving round-trips through the Phase 25 configarr backend; the diff preview shows only the changed field | ? UNCERTAIN | Static wiring verified: `openDiffPanel` dispatches to `api.postConfigarrDiff` when `activeConfig !== 'arrconf'` (App.svelte line 77); `confirmSave` dispatches to `api.putConfigarrConfig` (App.svelte line 95). Both functions are substantive implementations in `api.ts` (lines 72-78). End-to-end behavior (diff scope, tag preservation) requires human re-run since it involves the Phase 25 backend at runtime. |

**Score:** Programmatic verification: 2/3 truths fully verified; 1 verified at wiring level only; SC#1 is VERIFIED; SC#2 and SC#3 are UNCERTAIN pending human re-run after CR-01 fix.

### CR-01 Fix Status

The code review (26-REVIEW.md CR-01) identified that `media_naming` and `quality_definition` rendered editable because `effectiveNode()` ran `pickAnyOf()` first, discarding the `anyOf` wrapper that carries `readOnly: true`.

**Fix committed:** `33c4c4b fix(26-02): honor readOnly on anyOf wrapper nodes (CR-01)` (2026-05-30, after the human checkpoint)

**Current code** (FieldInput.svelte lines 86-94):
```js
// Phase 26 D-02: local prop OR readOnly marker. Check the RAW schema node too:
// pydantic emits `media_naming`/`quality_definition` as `anyOf:[{$ref},{null}], readOnly:true`,
// and effectiveNode() runs pickAnyOf() first — which discards the wrapper carrying readOnly
// (CR-01). The inner $ref branch has no readOnly, so the marker must be read off `schema`.
const isReadOnly = $derived(
  readOnly ||
    schema.readOnly === true ||
    (effective as { readOnly?: boolean }).readOnly === true,
);
```

**Schema confirmation:** `schemas/configarr-schema.json` verifies `media_naming.readOnly === true` and `quality_definition.readOnly === true` on the anyOf wrapper node in `$defs.ArrInstance`. The fix reads `schema.readOnly` (raw node, before stripping) which is the correct source for these fields. Logic is sound.

**Remaining gap:** The operator checkpoint (approved in 26-02-SUMMARY.md) predates this fix and therefore cannot serve as evidence that SC#2 now passes. A fresh browser verification is required.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/arrconf-ui/web/src/api.ts` | 4 configarr HTTP functions targeting `/api/configarr/*` | VERIFIED | Lines 59-78: `getConfigarrConfig`, `getConfigarrSchema`, `putConfigarrConfig`, `postConfigarrDiff` — all substantive, reuse `_fetchJson`/`API_BASE`; `_fetchJson`/`ApiError`/`API_BASE` unchanged |
| `tools/arrconf-ui/web/src/lib/FieldInput.svelte` | readOnly prop + isReadOnly derived + disabled widgets + lock badge | VERIFIED | Lines 41-44: prop declared and defaulted to false; lines 86-94: isReadOnly derived (CR-01 fix applied); line 181: lock badge; lines 187/202/211/288/299: 5× `disabled={isReadOnly}`; lines 265/322: 2× `readOnly={isReadOnly}` threading |
| `tools/arrconf-ui/web/src/types.ts` | readOnly field on JsonSchemaNode | VERIFIED | Line 43: `readOnly?: boolean;` with D-02 comment |
| `tools/arrconf-ui/web/src/constants.ts` | CONFIG_FILE_PATHS + ActiveConfig | VERIFIED | Lines 40-44: both exported, `as const` pattern, keyof type |
| `tools/arrconf-ui/web/src/i18n/fr.ts` | configarr field labels + READONLY_TOOLTIP_TEXT + UNSAVED_SWITCH_MESSAGE | VERIFIED | grep confirms all three present; SECTION_DOCS has `configarr`, `configarr.sonarr`, `configarr.radarr` entries |
| `tools/arrconf-ui/web/src/lib/HeaderBar.svelte` | tab bar with activeConfig/onTabChange props | VERIFIED | Lines 11-13: props declared; lines 26-33: two-tab nav rendered conditionally; token-based CSS (lines 124-133) |
| `tools/arrconf-ui/web/src/App.svelte` | active-config state, loadForConfig, parametrized save pipeline, unsaved-switch confirm | VERIFIED | Lines 32-34: state runes; lines 43-56: loadForConfig; lines 72-86: openDiffPanel dispatches by activeConfig; lines 88-109: confirmSave dispatches by activeConfig; lines 116-125: requestTabChange/doSwitch/cancelSwitch; lines 137-147: confirm dialog; lines 163-198: arrconf/configarr conditional rendering |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| App.svelte tab switch | `loadForConfig(cfg)` | `requestTabChange` → `doSwitch` → `loadForConfig` gated on `diffCount > 0` confirm | WIRED | App.svelte lines 116-124 |
| App.svelte save pipeline | `api.postConfigarrDiff` / `api.putConfigarrConfig` | dispatch by `activeConfig === 'arrconf'` ternary | WIRED | App.svelte lines 75-77 and 93-95 |
| App.svelte configarr render | schema.properties keys filtered on `additionalProperties != null` | `Object.keys(schema.properties).filter(...)` drives section list; no CategoriesEditor | WIRED | App.svelte lines 182-183; CategoriesEditor guarded at line 163 |
| FieldInput.svelte isReadOnly | schema.readOnly (raw node) | `$derived(readOnly \|\| schema.readOnly === true \|\| effective.readOnly === true)` | WIRED | FieldInput.svelte lines 90-94; CR-01 fix applied |
| api.ts configarr functions | `/api/configarr/config`, `/api/configarr/schema`, `/api/configarr/diff` | `_fetchJson` with `${API_BASE}/configarr/...` | WIRED | api.ts lines 59-78 |
| HeaderBar tab buttons | `onTabChange` callback | `onclick={() => onTabChange('arrconf')}` / `onclick={() => onTabChange('configarr')}` | WIRED | HeaderBar.svelte lines 29-30 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| App.svelte (configarr tab) | `schema`, `configState` | `loadForConfig('configarr')` → `api.getConfigarrSchema()` + `api.getConfigarrConfig()` | Real HTTP GET to Phase 25 backend at runtime | WIRED (runtime dependency on Phase 25 backend — not statically verifiable) |
| App.svelte (save) | `putConfigarrConfig` response | `api.putConfigarrConfig(configState)` → Phase 25 PUT endpoint | Real file write via Phase 25 backend | WIRED (runtime) |

### Behavioral Spot-Checks

Step 7b: SKIPPED — frontend-only phase; no runnable entry point for headless checks. The UI requires a browser + running Phase 25 backend. Items routed to human verification (Step 8).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CFGUI-04 | 26-01-PLAN.md, 26-02-PLAN.md | Le frontend offre un sélecteur de config (arrconf.yml ↔ configarr.yml); le formulaire configarr s'affiche via le dispatcher FieldInput.svelte existant | PARTIAL — wiring complete, SC#2 fix applied but needs human re-verification | Tab selector VERIFIED; FieldInput dispatcher VERIFIED; readOnly fix applied (CR-01); SC#2/SC#3 runtime behavior needs human re-run |

**No orphaned requirements:** CFGUI-01, CFGUI-02, CFGUI-03, CFGUI-07 are Phase 25 (complete). CFGUI-05, CFGUI-06 are Phase 27 (pending). CFGUI-04 is this phase — accounted for.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| App.svelte | 80-85 | Diff preview failure opens panel with empty diff (`pendingDiff = {} as SemanticDiff`) — WR-01 from review | Warning | Operator may see blank diff and proceed to overwrite; review finding, not a phase blocker |
| App.svelte | 101-108 | Non-validation save errors only go to `console.error`; `saveStatus = 'error'` not rendered — WR-02 from review | Warning | No user-visible signal on 500/network failure; review finding, not a phase blocker |
| App.svelte | 143 | Confirm dialog has no keyboard affordances (no focus trap, no Escape/Enter handling) — WR-03 from review | Warning | UX gap for a destructive action gate; review finding, not a phase blocker |
| (all web/) | — | No frontend unit/render tests — WR-04 from review | Warning | CR-01 regressed silently past all automated gates; this is a test coverage gap, not a code defect in the current state |

No BLOCKER anti-patterns found in the Phase 26 scope. WR-01 through WR-04 are review findings already captured in 26-REVIEW.md; they are tracked but do not block the phase goal (LAN-trusted single-operator tool).

No TODO/FIXME/placeholder patterns found in the 7 modified files. No hardcoded empty returns in API functions. ADR-5 gate passes: `grep -n "fetch\b"` and `grep -n "http://"` in FieldInput.svelte both return 0 matches.

### Human Verification Required

#### 1. SC#2 Re-verification after CR-01 fix

**Test:** Start the arrconf-ui backend (`uv run` from `tools/arrconf-ui/`) and the dev server (`npm run dev` from `tools/arrconf-ui/web/`). Open the browser, click the `configarr.yml` tab. Within the sonarr or radarr section, confirm that `quality_definition` and `media_naming` fields (and all their nested leaf widgets) are greyed out, show a lock badge (🔒), and the inputs are non-interactive (cannot type or click). Confirm `api_key` is also read-only. Confirm `quality_profiles`, `custom_formats`, and per-profile `score` fields are editable.

**Expected:** quality_definition and media_naming subtrees render disabled + lock badge at every leaf level; api_key reads as a disabled string input with lock badge; quality_profiles and scores are editable.

**Why human:** No frontend tests exist (WR-04). The checkpoint that originally approved SC#2 predates the CR-01 fix commit (33c4c4b). The fix logic is sound (`schema.readOnly === true` on the raw anyOf wrapper) and confirmed against the schema, but runtime rendering cannot be asserted without a browser.

#### 2. SC#3 — Quality-profile score edit, diff preview, and save round-trip

**Test:** On the configarr.yml tab, edit one quality-profile score value, click "Enregistrer". In the diff panel, confirm only the score field changed. Confirm the save. Then run `git diff charts/arr-stack/files/configarr.yml` and verify: (a) only the score line changed, (b) every `!env`/`!secret` tag is present verbatim, (c) comments and key order are preserved. Revert with `git checkout charts/arr-stack/files/configarr.yml`.

**Expected:** Diff panel shows exactly one changed field. File on disk preserves tags, comments, key order. No corruption.

**Why human:** Requires running Phase 25 backend. The operator approved this in the original checkpoint, but since the CR-01 fix touches FieldInput rendering, re-running the full flow confirms the fix did not affect the save pipeline.

### Gaps Summary

No structural BLOCKER gaps: all required artifacts exist and are substantive, all key links are wired, the CR-01 fix is committed and logically correct. The `human_needed` status is driven exclusively by the fact that SC#2 was approved before the CR-01 fix was applied, and WR-04 (no frontend tests) means there is no automated regression net. The two human verification items above constitute a targeted spot-check that can be completed in under 5 minutes with the UI running.

---

_Verified: 2026-05-30T05:52:20Z_
_Verifier: Claude (gsd-verifier)_
