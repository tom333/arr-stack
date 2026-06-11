# arrconf-ui Phase-34 Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve all advisory findings from `34-REVIEW.md` (5 Warnings WR-01..05, 4 Infos IN-01..04) plus the 3 stale pre-existing `test_io_roundtrip.py` failures, leaving the arrconf-ui test suite fully green.

**Architecture:** arrconf-ui is a two-part tool inside the arr-stack monorepo: a FastAPI backend (`tools/arrconf-ui/arrconf_ui/`, tested with pytest + Starlette TestClient) and a Svelte 5 (runes) frontend (`tools/arrconf-ui/web/src/`, no component test harness — verification is `svelte-check` + `vite build` + manual). Backend changes follow TDD; frontend changes are verified by typecheck/build because no JS test runner exists in this project (do NOT add one — out of scope).

**Tech Stack:** Python 3.13, FastAPI, pytest, ruyaml; Svelte 5 runes (`$state`/`$derived`/`$effect`), TypeScript, Vite.

---

## Context you must know before starting

- **Working directory for backend commands:** `/data/projets/perso/arr-stack/tools/arrconf-ui` (uses `uv`).
- **Working directory for frontend commands:** `/data/projets/perso/arr-stack/tools/arrconf-ui/web` (uses `npm`).
- **Backend quality gate (run before every backend commit):** `uv run ruff format --check . && uv run ruff check . && uv run mypy .` from `tools/arrconf-ui/`.
- **Frontend quality gate (run before every frontend commit):** `npm run check && npm run build` from `tools/arrconf-ui/web/`.
- **Baseline test status:** 72 backend tests pass; 3 fail in `tests/test_io_roundtrip.py` (fixed by Task 8). Do not be surprised by these 3 failures before Task 8.
- `intent.yml` is the only editable source. `arrconf.yml` and `configarr.yml` are 100% generated. The UI must never construct or call a Sonarr/Radarr URL (ADR-5).
- Commits use Conventional Commits format. Do not push — pushing `main` triggers an auto-tagger and a downstream Renovate PR.

---

### Task 1: WR-01 — Atomic writes for generated files in `put_intent`

`PUT /api/intent` writes three files: `intent.yml` (already atomic via `_write_text_atomic`) then `arrconf.yml` and `configarr.yml` with plain `Path.write_text()`. A crash mid-write can leave a truncated generated file. `_write_text_atomic` already exists at `arrconf_ui/app.py:102`.

**Files:**
- Modify: `tools/arrconf-ui/arrconf_ui/app.py` (the two `write_text` lines inside `put_intent`, around lines 264-265)
- Test: `tools/arrconf-ui/tests/test_intent_endpoints.py`

- [ ] **Step 1: Write the failing test**

Append to `tools/arrconf-ui/tests/test_intent_endpoints.py`:

```python
def test_put_intent_writes_all_files_atomically(
    client: TestClient,
    sandboxed_intent_yml: Path,
    sandboxed_arrconf_yml: Path,
    sandboxed_configarr_yml: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All three files written by PUT /api/intent go through _write_text_atomic (WR-01)."""
    import arrconf_ui.app as app_module

    written_paths: list[Path] = []
    real_atomic = app_module._write_text_atomic

    def recording_atomic(path: Path, text: str) -> None:
        written_paths.append(path)
        real_atomic(path, text)

    monkeypatch.setattr(app_module, "_write_text_atomic", recording_atomic)

    intent = client.get("/api/intent").json()
    resp = client.put("/api/intent", json=intent)
    assert resp.status_code == 200, resp.text

    names = sorted(p.name for p in written_paths)
    assert names == ["arrconf.yml", "configarr.yml", "intent.yml"], (
        f"expected all 3 files via _write_text_atomic, got {names}"
    )
```

Note: if `pytest`, `Path`, or `TestClient` are not already imported at the top of the file, they are — check the existing imports first; this file already uses all three.

- [ ] **Step 2: Run test to verify it fails**

Run from `tools/arrconf-ui/`:
```bash
uv run pytest tests/test_intent_endpoints.py::test_put_intent_writes_all_files_atomically -v
```
Expected: FAIL with `assert names == [...]` showing only `["intent.yml"]` recorded (the two generated files bypass the atomic helper).

⚠️ Caveat: `put_intent` calls `_write_text_atomic` by module-global reference. If the monkeypatch does not intercept it (test fails with empty list instead of `["intent.yml"]`), patch the name the handler actually resolves — it is defined and called in the same module, so `monkeypatch.setattr(app_module, "_write_text_atomic", ...)` works **only if** `create_app()` resolves it at call time (it does: it is a plain module-level function call, not captured in a closure default). If the recorded list is empty, the TestClient fixture built the app before the patch — patch before creating the client by using the `monkeypatch` fixture ordering or patching at module level as shown.

- [ ] **Step 3: Apply the fix**

In `tools/arrconf-ui/arrconf_ui/app.py`, inside `put_intent`, replace:

```python
        arrconf_yml_path().write_text(generate_arrconf_yml(intent_cfg), encoding="utf-8")
        configarr_yml_path().write_text(generate_configarr_yml(intent_cfg), encoding="utf-8")
```

with:

```python
        _write_text_atomic(arrconf_yml_path(), generate_arrconf_yml(intent_cfg))
        _write_text_atomic(configarr_yml_path(), generate_configarr_yml(intent_cfg))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_intent_endpoints.py -v
```
Expected: all tests in the file PASS (including the new one).

- [ ] **Step 5: Quality gate + commit**

```bash
uv run ruff format --check . && uv run ruff check . && uv run mypy .
git add arrconf_ui/app.py tests/test_intent_endpoints.py
git commit -m "fix(arrconf-ui): atomic writes for generated files in put_intent (WR-01)"
```

---

### Task 2: WR-05 — Regression test for removed `PUT /api/configarr/config`

`test_intent_endpoints.py` has `test_put_config_endpoint_removed` for the arrconf side. The configarr side has no equivalent.

**Files:**
- Test: `tools/arrconf-ui/tests/test_configarr_endpoints.py`

- [ ] **Step 1: Write the test**

Append to `tools/arrconf-ui/tests/test_configarr_endpoints.py` (mirror of the existing arrconf test at `tests/test_intent_endpoints.py:178`):

```python
def test_put_configarr_endpoint_removed(client: TestClient) -> None:
    """PUT /api/configarr/config must not be routable (D-34-04) — returns 405 or 404."""
    resp = client.put("/api/configarr/config", json={})
    assert resp.status_code in (404, 405), (
        f"Expected 404 or 405 (endpoint removed), got {resp.status_code}: {resp.text}"
    )
```

`TestClient` is already imported in this file (it is used by every other test there).

- [ ] **Step 2: Run test to verify it passes immediately**

This is a regression guard for already-removed code, so it must pass right away:
```bash
uv run pytest tests/test_configarr_endpoints.py::test_put_configarr_endpoint_removed -v
```
Expected: PASS. If it FAILS with a 200, the endpoint still exists — stop and report, that would contradict phase 34 verification.

- [ ] **Step 3: Quality gate + commit**

```bash
uv run ruff format --check . && uv run ruff check . && uv run mypy .
git add tests/test_configarr_endpoints.py
git commit -m "test(arrconf-ui): guard PUT /api/configarr/config removal (WR-05)"
```

---

### Task 3: Stale `test_io_roundtrip.py` tests — retarget to a dedicated fixture

3 tests assert comments/accents in the canonical `charts/arr-stack/files/arrconf.yml`, which since Phase 32 is a generated stub with none of those markers. The io-layer guarantees (comment preservation, modeline, UTF-8) are still worth testing — against a **dedicated fixture file**, not the canonical file.

**Files:**
- Create: `tools/arrconf-ui/tests/fixtures/roundtrip_sample.yml`
- Modify: `tools/arrconf-ui/tests/conftest.py` (add one fixture)
- Modify: `tools/arrconf-ui/tests/test_io_roundtrip.py` (retarget 3 tests)

- [ ] **Step 1: Create the fixture file**

Create `tools/arrconf-ui/tests/fixtures/roundtrip_sample.yml` with exactly this content (it intentionally reproduces every marker the 3 tests assert):

```yaml
# yaml-language-server: $schema=../../schemas/arrconf-schema.json
# Round-trip sample — markers used by test_io_roundtrip.py:
# D-06-SCOPE-01 — Seerr scope decision comment block
# D-07-INSTANCE-01 — single-instance pattern comment
# ADR-8 — _ArrV3Client mixin reference
categories:
  - name: series-emilie
    label: Séries d'Émilie
  - name: series-garcons
    label: Séries des Garçons
  - name: series-zoe
    label: Séries de Zoé
```

- [ ] **Step 2: Add the conftest fixture**

In `tools/arrconf-ui/tests/conftest.py`, after the existing `sandboxed_intent_yml` fixture, add:

```python
ROUNDTRIP_SAMPLE_YML = Path(__file__).parent / "fixtures" / "roundtrip_sample.yml"


@pytest.fixture
def roundtrip_sample(tmp_path: Path) -> Path:
    """Copy the comment-rich round-trip sample to tmp_path (no locator patching needed)."""
    target = tmp_path / "roundtrip_sample.yml"
    shutil.copy(ROUNDTRIP_SAMPLE_YML, target)
    return target
```

`Path`, `pytest`, and `shutil` are already imported in conftest.py.

- [ ] **Step 3: Retarget the 3 stale tests**

In `tools/arrconf-ui/tests/test_io_roundtrip.py`, replace the three failing tests (`test_modeline_preserved_on_round_trip`, `test_phase_6_section_comments_preserved`, `test_dump_yaml_to_str_is_utf8`) with versions using the new fixture. Leave `test_atomic_write_no_corruption_on_failure` untouched. Final file content for those three tests:

```python
def test_modeline_preserved_on_round_trip(roundtrip_sample: Path) -> None:
    data = read_yaml(roundtrip_sample)
    write_yaml_atomic(roundtrip_sample, data)
    content = roundtrip_sample.read_text(encoding="utf-8")
    # Line 1 of the sample is `# yaml-language-server: $schema=...`
    assert content.splitlines()[0].startswith("# yaml-language-server:")


def test_section_comments_preserved(roundtrip_sample: Path) -> None:
    """Comment blocks (decision markers) survive round-trip."""
    data = read_yaml(roundtrip_sample)
    write_yaml_atomic(roundtrip_sample, data)
    content = roundtrip_sample.read_text(encoding="utf-8")
    assert "D-06-SCOPE-01" in content
    assert "D-07-INSTANCE-01" in content
    assert "ADR-8" in content


def test_dump_yaml_to_str_is_utf8(roundtrip_sample: Path) -> None:
    """Émilie / Garçons / Zoé accented strings survive dump."""
    data = read_yaml(roundtrip_sample)
    out = dump_yaml_to_str(data)
    assert "Émilie" in out
    assert "Garçons" in out
    assert "Zoé" in out
```

Note the rename `test_phase_6_section_comments_preserved` → `test_section_comments_preserved` (the "Phase 6" reference is obsolete). Update the module docstring if it mentions the canonical arrconf.yml.

- [ ] **Step 4: Run the full backend suite — must be 100% green now**

```bash
uv run pytest -q
```
Expected: `78 passed` (75 previous green + 1 from Task 1 + 1 from Task 2 + net ±0 here — exact count may differ by one or two; the requirement is **0 failed**).

- [ ] **Step 5: Quality gate + commit**

```bash
uv run ruff format --check . && uv run ruff check . && uv run mypy .
git add tests/fixtures/roundtrip_sample.yml tests/conftest.py tests/test_io_roundtrip.py
git commit -m "test(arrconf-ui): retarget io round-trip tests to dedicated fixture (arrconf.yml is generated)"
```

---

### Task 4: WR-04 + IN-04 — Snapshot the intent at diff time; no silent empty-diff fallback

Two related bugs in `tools/arrconf-ui/web/src/App.svelte`:
- **WR-04:** `openDiffPanel()` diffs `intentState` at open time, but `confirmSave()` saves the **live** `intentState` — the operator reviews version N and saves version N+1 if they keep editing while the panel is open.
- **IN-04:** on diff API failure, the catch block shows the panel with empty diffs ("Aucune modification"), misleading the operator into confirming a save they never reviewed.

**Files:**
- Modify: `tools/arrconf-ui/web/src/App.svelte` (functions `openDiffPanel`, `confirmSave`, `cancelDiffPanel`, around lines 90-128)

- [ ] **Step 1: Add the snapshot state and rewrite the three functions**

In `App.svelte`, near the other `$state` declarations (around line 24-30), add:

```ts
  let pendingSaveSnapshot = $state<IntentPayload | null>(null);
```

Replace the existing `openDiffPanel`, `confirmSave`, and `cancelDiffPanel` functions with:

```ts
  async function openDiffPanel() {
    if (!intentState) return;
    // WR-04: snapshot what the operator will review — confirmSave saves THIS,
    // not whatever intentState becomes while the panel is open.
    const snapshot = JSON.parse(JSON.stringify(intentState)) as IntentPayload;
    try {
      const r = await api.postIntentDiff(snapshot);
      pendingSaveSnapshot = snapshot;
      pendingMatDiff = r;
      showDiffPanel = true;
    } catch (e) {
      // IN-04: do NOT show an empty diff on failure — surface the error instead.
      console.error('diff preview failed', e);
      loadError = e instanceof Error ? e.message : String(e);
    }
  }

  async function confirmSave() {
    if (!pendingSaveSnapshot) return;
    const toSave = pendingSaveSnapshot;
    saveStatus = 'saving';
    showDiffPanel = false;
    try {
      await api.putIntent(toSave);
      savedIntent = JSON.parse(JSON.stringify(toSave)) as IntentPayload;
      validationErrors = [];
      saveStatus = 'saved';
      showSaveToast = true;
    } catch (e) {
      saveStatus = 'error';
      if (e instanceof ApiError && Array.isArray(e.detail)) {
        validationErrors = e.detail as PydanticErrorEntry[];
      } else {
        console.error('save failed', e);
      }
    } finally {
      pendingSaveSnapshot = null;
    }
  }

  function cancelDiffPanel() {
    showDiffPanel = false;
    pendingSaveSnapshot = null;
  }
```

Behavioral consequence (intended): if the operator edits while the panel is open, those edits are NOT saved by Confirmer — `savedIntent` is set to the snapshot, so `diffCount` stays > 0 and the save button remains active for the follow-up edits. Note `loadError` is reused for the diff failure message; it renders in the existing `role="alert"` block. This is acceptable for a LAN-trusted single-operator tool — do not build a separate error channel (YAGNI).

- [ ] **Step 2: Verify with typecheck + build**

Run from `tools/arrconf-ui/web/`:
```bash
npm run check && npm run build
```
Expected: `0 ERRORS` from svelte-check (2 pre-existing `state_referenced_locally` warnings disappear after Task 5 — still present at this point) and a successful vite build.

- [ ] **Step 3: Commit**

```bash
git add src/App.svelte
git commit -m "fix(arrconf-ui): snapshot intent at diff time; no silent empty-diff fallback (WR-04, IN-04)"
```

---

### Task 5: WR-02 — Resync `$state`-initialized textareas when the intent is reloaded

`ConfigarrRawEditor.svelte` (`rawText`, line 14) and `ProfileCard.svelte` (`bodyRaw`, line 30) initialize local `$state` from props **once**. When `App.svelte` reloads `intentState` (tab switch away and back), the textareas keep showing the previous load's JSON. The 2 `state_referenced_locally` svelte-check warnings flag exactly this.

**Fix strategy:** remount the whole intent form when a fresh intent is loaded, via `{#key loadEpoch}` in App.svelte. Do NOT use `$effect` to resync the textareas — that re-runs on every keystroke round-trip (edit → onChange → parent state → prop → effect resets text), causing cursor jumps and reformatting while typing. A load-epoch key remounts components only on genuine reloads.

**Files:**
- Modify: `tools/arrconf-ui/web/src/App.svelte` (add `loadEpoch`, wrap intent sections)
- Modify: `tools/arrconf-ui/web/src/lib/ConfigarrRawEditor.svelte` (suppress now-correct warning)
- Modify: `tools/arrconf-ui/web/src/lib/ProfileCard.svelte` (suppress now-correct warning)

- [ ] **Step 1: Add the load epoch in App.svelte**

Near the other `$state` declarations:

```ts
  let loadEpoch = $state(0);
```

In `loadForConfig`, in the `intent` branch, right after `savedIntent = ...` (line ~61), add:

```ts
        loadEpoch += 1;
```

- [ ] **Step 2: Key the intent form on the epoch**

In the template, the intent tab's `<main class="page">` contains the six sections (CategoriesEditor → ConfigarrRawEditor). Wrap the six section mounts (everything from `<!-- 1. categories -->` through the closing of the ConfigarrRawEditor block, but NOT the ValidationBanner and NOT the MaterializationDiffPanel) in a key block:

```svelte
      {#key loadEpoch}
        <!-- 1. categories -->
        ... (existing six sections, unchanged) ...
        <!-- 6. configarr -->
        <ConfigarrRawEditor
          value={intentState.configarr}
          onChange={(c) => updateIntent('configarr', c)}
        />
      {/key}
```

Why exclude the diff panel and banner: remounting them on reload is harmless but pointless; keying only the form keeps the change minimal.

- [ ] **Step 3: Mark the two intentional init-from-prop reads**

The `state_referenced_locally` warnings become **intentional** once remount-on-reload guarantees freshness. Add the suppression comment directly above each:

In `ConfigarrRawEditor.svelte` (line ~13-14):
```ts
  // Init-from-prop is safe: App.svelte remounts this component via {#key loadEpoch}
  // whenever a fresh intent is loaded (WR-02).
  // svelte-ignore state_referenced_locally
  let rawText = $state(JSON.stringify(value, null, 2));
```

In `ProfileCard.svelte` (line ~29-30):
```ts
  // Init-from-prop is safe: App.svelte remounts this component via {#key loadEpoch}
  // whenever a fresh intent is loaded (WR-02).
  // svelte-ignore state_referenced_locally
  let bodyRaw = $state(JSON.stringify(profile.body, null, 2));
```

- [ ] **Step 4: Verify**

```bash
npm run check && npm run build
```
Expected: `0 ERRORS 0 WARNINGS` from svelte-check (the 2 warnings are now suppressed-with-justification), successful build.

Manual spot-check (optional but recommended if dev servers are running): edit the configarr raw textarea → switch to arrconf.yml tab → return to intent.yml → textarea shows the **reloaded** value.

- [ ] **Step 5: Commit**

```bash
git add src/App.svelte src/lib/ConfigarrRawEditor.svelte src/lib/ProfileCard.svelte
git commit -m "fix(arrconf-ui): remount intent form on reload — stale textarea state (WR-02)"
```

---

### Task 6: WR-03 — Remove false `aria-modal` from MaterializationDiffPanel

The panel declares `role="dialog" aria-modal="true"` but renders **inline** — the form below stays interactive. `aria-modal="true"` tells screen readers the background is inert, which is false. Minimal correct fix: drop `aria-modal`, keep `role="dialog"` + labelledby.

**Files:**
- Modify: `tools/arrconf-ui/web/src/lib/MaterializationDiffPanel.svelte:36`

- [ ] **Step 1: Apply the one-line fix**

Replace:
```svelte
<div class="panel" role="dialog" aria-labelledby="mat-diff-heading" aria-modal="true">
```
with:
```svelte
<div class="panel" role="dialog" aria-labelledby="mat-diff-heading">
```

- [ ] **Step 2: Verify + commit**

```bash
npm run check && npm run build
git add src/lib/MaterializationDiffPanel.svelte
git commit -m "fix(arrconf-ui): drop false aria-modal on inline diff panel (WR-03)"
```

---

### Task 7: IN-03 — Guard `NaN` in profile score override

`updateScore` in `ProfileCard.svelte` does `Number(raw)` — pasting non-numeric text yields `NaN`, which propagates into the intent payload.

**Files:**
- Modify: `tools/arrconf-ui/web/src/lib/ProfileCard.svelte` (function `updateScore`, around line 58-65)

- [ ] **Step 1: Apply the guard**

Replace:
```ts
  function updateScore(idx: number, raw: string) {
    const parsed = raw === '' ? null : Number(raw);
```
with:
```ts
  function updateScore(idx: number, raw: string) {
    const n = Number(raw);
    const parsed = raw === '' || Number.isNaN(n) ? null : n;
```
(the rest of the function body is unchanged — it maps `profile.custom_formats` and calls `onChange`).

- [ ] **Step 2: Verify + commit**

```bash
npm run check && npm run build
git add src/lib/ProfileCard.svelte
git commit -m "fix(arrconf-ui): treat non-numeric score input as null (IN-03)"
```

---

### Task 8: IN-01 + IN-02 — Remove dead API functions and stale types

After the intent pivot, four `api.ts` functions are called by nothing: `getSchema`, `postDiff`, `getConfigarrSchema`, `postConfigarrDiff` (verified by grep — only `getIntentSchema`, `getIntent`, `getConfig`, `getConfigarrConfig`, `postIntentDiff`, `putIntent` plus the `/api/trash/*` functions are used). The `DiffResponse` type is only referenced by the dead functions. `ConfigPayload` is only used as `getConfig`'s return type, and its `categories` field is stale (categories moved to intent.yml in Phase 32); `App.svelte` only stringifies the result.

Backend endpoints (`GET /api/schema`, `POST /api/diff`, etc.) are NOT touched — removing live API surface is out of scope for a dead-code cleanup.

**Files:**
- Modify: `tools/arrconf-ui/web/src/api.ts`
- Modify: `tools/arrconf-ui/web/src/types.ts`

- [ ] **Step 1: Re-verify the functions are dead (cheap insurance)**

Run from `tools/arrconf-ui/web/`:
```bash
grep -rn "getSchema\b\|postDiff\b\|getConfigarrSchema\b\|postConfigarrDiff\b" src/ --include="*.svelte" --include="*.ts" | grep -v "src/api.ts"
```
Expected: no output. If any caller appears, STOP — do not delete that function; report instead.

- [ ] **Step 2: Delete the dead code**

In `src/api.ts`:
- Delete the four functions `getSchema`, `postDiff`, `getConfigarrSchema`, `postConfigarrDiff` (keep the `// D-34-04: direct write ... removed` comments — they document the decision).
- Remove `DiffResponse` and `ConfigPayload` from the type import list at the top.
- Change `getConfig`'s signature to:

```ts
export async function getConfig(): Promise<Record<string, unknown>> {
  return _fetchJson<Record<string, unknown>>(`${API_BASE}/config`);
}
```

In `src/types.ts`:
- Delete the `ConfigPayload` type (lines ~16-24) and the `DiffResponse` type (line ~67). Keep `MediaCategory` (used by CategoriesEditor) and `MaterializationDiffResponse` (used by the diff panel).

In `src/App.svelte` (line ~68): update the now-inaccurate comment:
```ts
        // getConfig returns the parsed YAML as a plain object; stringify for inspector display.
```

- [ ] **Step 3: Verify + commit**

```bash
npm run check && npm run build
```
Expected: 0 errors — if `tsc` complains about a remaining `ConfigPayload`/`DiffResponse` reference, you missed a usage; fix it before committing.

```bash
git add src/api.ts src/types.ts src/App.svelte
git commit -m "refactor(arrconf-ui): drop dead post-pivot API fns and stale types (IN-01, IN-02)"
```

---

### Task 9: Final verification sweep

**Files:** none modified.

- [ ] **Step 1: Full backend suite**

From `tools/arrconf-ui/`:
```bash
uv run pytest -q
```
Expected: **0 failed** (the 3 historical io_roundtrip failures are gone since Task 3).

- [ ] **Step 2: Full backend quality gate**

```bash
uv run ruff format --check . && uv run ruff check . && uv run mypy .
```
Expected: all three exit 0.

- [ ] **Step 3: Full frontend gate**

From `tools/arrconf-ui/web/`:
```bash
npm run check && npm run typecheck && npm run build
```
Expected: svelte-check `0 ERRORS 0 WARNINGS`, tsc clean, build succeeds.

- [ ] **Step 4: Confirm no co-bump needed**

This plan touches `tools/arrconf-ui/**` only. Verify no file under `tools/arrconf/` changed:
```bash
git -C /data/projets/perso/arr-stack diff --name-only HEAD~8..HEAD -- tools/arrconf/ | head
```
Expected: no output → no `arrconf.image.tag` co-bump required (per CLAUDE.md the co-bump rule only fires for `tools/arrconf/**`).

(Adjust `HEAD~8` to however many commits this plan actually produced.)

---

## Out of scope — deliberately NOT in this plan

- **Milestone v0.11.0 closure** (`/gsd-complete-milestone`): GSD-internal lifecycle, not convertible to a code plan. Run it manually after this plan lands. Known footguns: `gsd-sdk milestone.complete --help` is destructive; rewrite the MILESTONES.md accomplishments entry manually; do NOT git-tag the milestone and do NOT auto-push (auto-tagger + Renovate).
- **Adding a JS test harness (vitest)** for the Svelte components: project has none; adding infra is a separate decision.
- **Removing backend endpoints** `GET /api/schema`, `POST /api/diff`, `GET /api/configarr/schema`, `POST /api/configarr/diff`: live API surface, separate decision.
- **Focus trap implementation** for the diff panel: WR-03 is fixed by removing the false claim, not by building modal infrastructure (YAGNI for a LAN-trusted single-operator tool).
