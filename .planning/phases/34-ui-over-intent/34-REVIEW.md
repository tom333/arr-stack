---
phase: 34-ui-over-intent
reviewed: 2026-06-08T14:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - tools/arrconf-ui/arrconf_ui/app.py
  - tools/arrconf-ui/arrconf_ui/locator.py
  - tools/arrconf-ui/tests/conftest.py
  - tools/arrconf-ui/tests/test_app_endpoints.py
  - tools/arrconf-ui/tests/test_configarr_endpoints.py
  - tools/arrconf-ui/tests/test_intent_endpoints.py
  - tools/arrconf-ui/web/src/App.svelte
  - tools/arrconf-ui/web/src/api.ts
  - tools/arrconf-ui/web/src/constants.ts
  - tools/arrconf-ui/web/src/types.ts
  - tools/arrconf-ui/web/src/i18n/fr.ts
  - tools/arrconf-ui/web/src/lib/ConfigarrRawEditor.svelte
  - tools/arrconf-ui/web/src/lib/HeaderBar.svelte
  - tools/arrconf-ui/web/src/lib/MaterializationDiffPanel.svelte
  - tools/arrconf-ui/web/src/lib/ProfileCard.svelte
  - tools/arrconf-ui/web/src/lib/ProfileDefinitionsEditor.svelte
  - tools/arrconf-ui/web/src/lib/ReadOnlyInspector.svelte
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 34: Code Review Report

**Reviewed:** 2026-06-08T14:00:00Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 34 pivots arrconf-ui from a two-tab editable-config UI to a three-tab model where `intent.yml` is the sole editable source and `arrconf.yml`/`configarr.yml` are read-only generated inspectors. The backend changes are structurally clean: path functions follow existing locator conventions, the four intent endpoints are correctly scoped, and the two removed PUT endpoints leave no dangling routes. No path traversal risk exists — all write paths are derived from fixed locator functions, never from user-supplied strings.

The main concerns are: (1) non-atomic writes for the two generated files in `put_intent` (WARNING), which could corrupt `arrconf.yml` or `configarr.yml` under a crash or exception between the two `write_text` calls; (2) a stale local state pattern in `ConfigarrRawEditor` and `ProfileCard` that causes the textarea to display outdated content if the parent re-initializes `intentState` (WARNING); (3) a misleading `aria-modal="true"` on `MaterializationDiffPanel` without a corresponding focus trap (WARNING); (4) a diff/save race window where the diff panel shows a snapshot but the save writes a (potentially different) live state (WARNING); (5) missing test coverage for the removal of `PUT /api/configarr/config` (WARNING).

No secrets are leaked to the frontend. No injection vectors exist. The Svelte 5 `state_referenced_locally` suppressions are correctly placed and represent real (but bounded) stale-state risks rather than compile errors.

## Warnings

### WR-01: Non-atomic writes for generated files in `put_intent` — partial-state risk on crash

**File:** `tools/arrconf-ui/arrconf_ui/app.py:264-265`
**Issue:** `intent.yml` is written atomically via `_write_text_atomic` (tempfile + `os.replace`), but the two downstream generated files use plain `Path.write_text`. If the process is killed after `arrconf_yml_path().write_text(...)` succeeds but before `configarr_yml_path().write_text(...)` completes, `configarr.yml` will be truncated to zero bytes (Python `open("w")` truncates before writing). The result is `intent.yml` containing the new intent, `arrconf.yml` containing the newly generated content, and `configarr.yml` empty — a triply inconsistent state. Additionally, if `generate_configarr_yml(intent_cfg)` raises an exception after `arrconf_yml_path().write_text(...)` has already returned, `arrconf.yml` is permanently updated but `configarr.yml` is not.

**Fix:**
```python
# Replace lines 264-265 with atomic writes for both generated files:
_write_text_atomic(arrconf_yml_path(), generate_arrconf_yml(intent_cfg))
_write_text_atomic(configarr_yml_path(), generate_configarr_yml(intent_cfg))
```
The `_write_text_atomic` function already exists in the same file and handles the tempfile + fsync + os.replace pattern correctly.

---

### WR-02: Stale local textarea state in `ConfigarrRawEditor` when `intentState` is reloaded

**File:** `tools/arrconf-ui/web/src/lib/ConfigarrRawEditor.svelte:14`
**Issue:** `let rawText = $state(JSON.stringify(value, null, 2))` initializes `rawText` once from the `value` prop at component mount time. In Svelte 5, `$state` initialized from a prop is not reactive to prop changes — if the parent resets `intentState` (e.g., after a tab switch back to `intent` triggers `loadForConfig('intent')` which sets `intentState = null` then a new object), the `ConfigarrRawEditor` is not remounted (no `key` prop) and `rawText` remains the value from the previous render cycle. The textarea will display stale JSON while the parent's intent state has been refreshed.

The same pattern exists in `ProfileCard.svelte:30` for `bodyRaw`, with the additional Svelte 5 `state_referenced_locally` warning already suppressed at line 25. The `isOpen` suppression in `ProfileCard` is benign (correctly two-way synced via `ontoggle`), but `rawText` / `bodyRaw` are genuine stale-state risks.

**Fix:** Drive the textarea value from a `$derived` instead of `$state`, or add a `{#key ...}` wrapper at the call site to force remount when intent is reloaded:

```svelte
<!-- In App.svelte, force remount of ConfigarrRawEditor when intentState changes identity -->
{#key intentState}
  <ConfigarrRawEditor
    value={intentState.configarr}
    onChange={(c) => updateIntent('configarr', c)}
  />
{/key}
```

Alternatively, in `ConfigarrRawEditor.svelte`, use `$effect` to re-sync `rawText` when the prop changes and there is no pending user edit:

```ts
$effect(() => {
  // Only reset from props if not currently in a user-edit cycle
  rawText = JSON.stringify(value, null, 2);
});
```

---

### WR-03: `aria-modal="true"` without focus trap on `MaterializationDiffPanel` — misleading ARIA

**File:** `tools/arrconf-ui/web/src/lib/MaterializationDiffPanel.svelte:36`
**Issue:** The panel declares `role="dialog" aria-modal="true"` but is rendered inline in the page flow (not as an overlay with `position: fixed`). The form sections below it remain fully interactive in the DOM. `aria-modal="true"` tells screen readers that content outside the dialog is inert — but because no `inert` attribute is set on the background content and no focus trap is implemented, keyboard users and screen reader users can still reach the form fields below the panel. This creates a mismatch between what ARIA promises and what the DOM provides.

**Fix:** Either remove `aria-modal="true"` (since this is not a true blocking modal — the spec calls it an inline panel), or enforce the modal contract by adding `inert` to the background when the panel is open:

```svelte
<!-- In App.svelte, mark the form sections inert while diff panel is shown -->
<main class="page" inert={showDiffPanel || undefined}>
  ...form sections...
</main>
```

Note: the `aria-labelledby="mat-diff-heading"` reference is correct and should be kept.

---

### WR-04: Diff/save state divergence — diff panel shows snapshot, save writes live state

**File:** `tools/arrconf-ui/web/src/App.svelte:90-122`
**Issue:** `openDiffPanel()` captures `intentState` at call time to generate `pendingMatDiff`, then stores the result and sets `showDiffPanel = true`. The diff panel renders `pendingMatDiff` (the snapshot). However, the form remains interactive while the panel is open, and `confirmSave()` calls `api.putIntent(intentState)` using the current live `intentState`, which may have been mutated after the diff was computed. The operator sees a diff for version N but saves version N+1 without a new diff.

This is a functional correctness issue: the review step ("vérifier avant d'enregistrer") can be bypassed by editing the form after opening the diff panel.

**Fix:** Snapshot `intentState` when opening the diff panel and use that snapshot for saving:

```typescript
let snapshotForSave = $state<IntentPayload | null>(null);

async function openDiffPanel() {
  if (!intentState) return;
  snapshotForSave = JSON.parse(JSON.stringify(intentState)) as IntentPayload;
  try {
    const r = await api.postIntentDiff(snapshotForSave);
    pendingMatDiff = r;
    showDiffPanel = true;
  } catch (e) { ... }
}

async function confirmSave() {
  if (!snapshotForSave) return;
  saveStatus = 'saving';
  showDiffPanel = false;
  try {
    await api.putIntent(snapshotForSave);
    savedIntent = snapshotForSave;
    ...
  }
}
```

---

### WR-05: No test asserting `PUT /api/configarr/config` returns 404/405

**File:** `tools/arrconf-ui/tests/test_configarr_endpoints.py:1-162`
**Issue:** `test_intent_endpoints.py` tests that `PUT /api/config` returns 404 or 405 (enforcing D-34-04 for the arrconf endpoint removal). The equivalent regression test is absent for `PUT /api/configarr/config`, which was also removed in D-34-04. If the endpoint were accidentally re-added (e.g., during a merge conflict resolution), no test would catch it.

**Fix:** Add a test analogous to `test_put_config_endpoint_removed`:

```python
def test_put_configarr_config_endpoint_removed(client: TestClient) -> None:
    """PUT /api/configarr/config must not be routable (D-34-04) — returns 405 or 404."""
    resp = client.put("/api/configarr/config", json={})
    assert resp.status_code in (404, 405), (
        f"Expected 404 or 405 (endpoint removed), got {resp.status_code}: {resp.text}"
    )
```

---

## Info

### IN-01: Dead functions in `api.ts` — `getSchema`, `postDiff`, `getConfigarrSchema`, `postConfigarrDiff`

**File:** `tools/arrconf-ui/web/src/api.ts:44-71`
**Issue:** Four functions (`getSchema`, `postDiff`, `getConfigarrSchema`, `postConfigarrDiff`) are exported from `api.ts` but are no longer called from any Svelte component. The old two-tab editing flow used them; the new three-tab intent flow does not. They are dead code that will accumulate as confusion for future developers.
**Fix:** Remove the four dead functions. If the read-only inspector tabs need raw-YAML display in a future phase, the endpoint and function can be re-added then.

---

### IN-02: `ConfigPayload` type in `types.ts` still declares `categories` field — stale type

**File:** `tools/arrconf-ui/web/src/types.ts:16-24`
**Issue:** `ConfigPayload.categories: MediaCategory[]` was valid before Phase 32 migrated `categories` to `intent.yml`. The backend `GET /api/config` no longer returns a `categories` key (as confirmed by the updated test in `test_app_endpoints.py`). The type is now incorrect and will mislead future code that tries to read `configPayload.categories`.
**Fix:** Remove the `categories` field from `ConfigPayload`:

```typescript
export type ConfigPayload = {
  // categories removed in Phase 32 (CATMIG) — lives in IntentPayload now
  sonarr: Record<string, unknown>;
  radarr: Record<string, unknown>;
  ...
};
```

---

### IN-03: `updateScore` propagates `NaN` when user types non-numeric text into score input

**File:** `tools/arrconf-ui/web/src/lib/ProfileCard.svelte:59-64`
**Issue:** `const parsed = raw === '' ? null : Number(raw)`. `Number('abc')` returns `NaN`, which propagates into `CustomFormatRef.score`. `NaN` is not `null`, not a number, and serializes as `null` in `JSON.stringify` (silently losing the user's intent). While `<input type="number">` normally prevents non-numeric characters in most browsers, pasting or programmatic assignment can still produce non-numeric strings.
**Fix:**
```typescript
function updateScore(idx: number, raw: string) {
  const n = Number(raw);
  const parsed = raw === '' || isNaN(n) ? null : n;
  ...
}
```

---

### IN-04: `openDiffPanel` error fallback silently allows save with empty diffs

**File:** `tools/arrconf-ui/web/src/App.svelte:96-101`
**Issue:** If `postIntentDiff` fails (network error, server 500), the catch block sets `pendingMatDiff = { arrconf_diff: '', configarr_diff: '', has_changes: false }` and opens the panel anyway. The operator sees "Aucune modification" in both diff blocks and may click "Confirmer et enregistrer" without knowing the diff could not be computed. The save then proceeds against the live backend regardless.

This is a UX concern for a LAN-trusted tool, but operators making assumptions based on empty diffs could inadvertently confirm saves of larger-than-expected changes.
**Fix:** Display an explicit error message in the diff panel when the diff endpoint failed, rather than showing empty diffs:

```typescript
} catch (e) {
  console.error('diff preview failed', e);
  pendingMatDiff = {
    arrconf_diff: '[Erreur : impossible de calculer le diff — ' + String(e) + ']',
    configarr_diff: '',
    has_changes: true,  // conservatively mark as changed
  };
  showDiffPanel = true;
}
```

---

_Reviewed: 2026-06-08T14:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
