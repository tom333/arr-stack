---
phase: 27-trash-cf-picker-recyclarr-reference
verified: 2026-05-31T00:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "QP insert end-to-end: collision check normalization (WR-01)"
    expected: "Inserting 'multi.vf' (lowercase of 'MULTi.VF') should either be blocked as collision or produce a harmless second profile — operator should confirm expected behavior"
    why_human: "hasCollision uses exact-string name comparison; case/whitespace normalization is not implemented; cannot verify correct UX behavior programmatically"
  - test: "QP field mapping correctness in saved configarr.yml"
    expected: "Inserted QP entry has upgrade.until_quality == TRaSH cutoff value, qualities[] reflects items[allowed!=false] in baked order (Feb-2026), no extra/missing fields"
    why_human: "MEDIUM-confidence field mapping (research correction #4) was operator-approved in the Plan 04 checkpoint; verifier cannot re-run that approval programmatically"
---

# Phase 27: TRaSH CF Picker / QP Picker / Recyclarr Reference — Verification Report

**Phase Goal:** Operators can add or remove TRaSH custom formats by human-readable name (no manual hex trash_id copying), apply TRaSH quality profiles by name (add-as-new, never touching the hand-rolled profiles), and reference Recyclarr template names as an informational guide without risk of inadvertent `include:` insertion.
**Verified:** 2026-05-31
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC#1: CF picker inserts trash_id by name — operator searches by name, new entry gets `trash_ids:[id]`, no manual hex copying | ✓ VERIFIED | `TrashCFPicker.svelte`: `getTrashCustomFormats(app)` loads catalog; `filtered=$derived(catalog.filter(c=>c.name.toLowerCase().includes(query)))` enables name search; `confirmAdd()` builds `{trash_ids:[id], assign_scores_to:profileNames.map(n=>({name:n}))}` per D-04 |
| 2 | SC#2: TRaSH+Recyclarr catalog served from build-time baked snapshot — zero runtime GitHub HTTP | ✓ VERIFIED | 6 catalog JSON + manifest.json committed at pinned SHAs (`1ef7baa5`/`505c1e56`); 3 FastAPI handlers read only `trash_metadata_dir()`; no `httpx/requests/urllib/github` in handler bodies (grep confirmed 0 matches) |
| 3 | SC#3: Recyclarr reference dropdown shows template names, NEVER inserts `include:` | ✓ VERIFIED | `RecyclarrReferencePicker.svelte`: no `onChange` prop (grep: 0), no `include:` string (grep: 0), single clipboard action `copyId()`; confirmed by operator in 8-step human checkpoint |
| 4 | SC#4: known-custom badge for local CFs (fr-vff etc.), warning + verbatim preserve for unknown ids | ✓ VERIFIED | `classify()` checks catalog first ('trash'), then `localDefinitions` ('custom'), then 'unknown'; `badge-custom` and `badge-warn` CSS classes rendered accordingly; CR-01 fix: `removeId(entryIdx, idIdx)` operates per-id within multi-id entries (flatMap dedup), unknown ids preserved until explicit ✕ |
| 5 | SC#5: QP picker append-only — 3 hand-rolled profiles untouched, name collision blocked | ✓ VERIFIED | `confirmInsert()`: `onChange([...existingProfiles, newEntry])` spread-append only; `hasCollision=$derived(existingProfiles.some(...name===collisionName))` disables insert button; grep: 0 matches for `existingProfiles[`/`.splice`/`.sort`; CR-02 fix: no hardcoded `min_format_score:1` in upgrade block |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/scripts/fetch-trash-metadata.sh` | Dev-time catalog fetch + transform script | ✓ VERIFIED | Exists, executable, `set -euo pipefail`, both SHAs pinned, no `git clone`, `curl`+`python3` guards |
| `tools/arrconf-ui/web/src/assets/trash-metadata/sonarr-cf.json` | Sonarr CF catalog `[{trash_id,name,default_score}]` | ✓ VERIFIED | 235 entries; structure validated; `fr-vff` correctly absent |
| `tools/arrconf-ui/web/src/assets/trash-metadata/radarr-cf.json` | Radarr CF catalog | ✓ VERIFIED | 240 entries; structure validated |
| `tools/arrconf-ui/web/src/assets/trash-metadata/sonarr-qp.json` | Sonarr QP catalog with `items[]` | ✓ VERIFIED | 19 entries; `trash_id`+`items` on all entries |
| `tools/arrconf-ui/web/src/assets/trash-metadata/radarr-qp.json` | Radarr QP catalog | ✓ VERIFIED | 36 entries; structure validated |
| `tools/arrconf-ui/web/src/assets/trash-metadata/recyclarr-sonarr.json` | Sonarr Recyclarr template ids `[{id,template}]` | ✓ VERIFIED | 34 entries; `id`+`template` only, no `description` field |
| `tools/arrconf-ui/web/src/assets/trash-metadata/recyclarr-radarr.json` | Radarr Recyclarr template ids | ✓ VERIFIED | 64 entries; same structure |
| `tools/arrconf-ui/web/src/assets/trash-metadata/manifest.json` | SHA + counts manifest | ✓ VERIFIED | `trash_sha`, `recyclarr_sha`, `fetched_at`, `counts` block with all 6 values |
| `tools/arrconf-ui/arrconf_ui/locator.py` | `trash_metadata_dir()` path resolver | ✓ VERIFIED | Function present, resolves to `repo_root()/tools/arrconf-ui/web/src/assets/trash-metadata`; Test 8 passes |
| `tools/arrconf-ui/arrconf_ui/app.py` | 3 read-only TRaSH metadata endpoints | ✓ VERIFIED | `GET /api/trash/custom-formats`, `/quality-profiles`, `/recyclarr-templates`; each has enum 400 gate + 404 guard; ADR-5 boundary comment |
| `tools/arrconf-ui/tests/test_trash_endpoints.py` | 8 endpoint tests | ✓ VERIFIED | 8 tests, all pass; path-traversal + 400 + 422 + happy-path; no respx; `template in entry` assertion (IN-01 fix) |
| `tools/arrconf-ui/web/src/types.ts` | 5 Phase 27 types | ✓ VERIFIED | `TrashApp`, `TrashCFEntry`, `TrashQPEntry`, `TrashQPItem`, `RecyclarrTemplateEntry` all present |
| `tools/arrconf-ui/web/src/api.ts` | 3 fetch functions | ✓ VERIFIED | `getTrashCustomFormats`, `getTrashQualityProfiles`, `getRecyclarrTemplates` all present |
| `tools/arrconf-ui/web/src/i18n/fr.ts` | 6 i18n constants | ✓ VERIFIED | `TRASH_CUSTOM_BADGE_TEXT`, `TRASH_UNKNOWN_BADGE_TEXT`, `TRASH_COLLISION_WARNING_TEXT`, `RECYCLARR_REFERENCE_LABEL`, `TRASH_CF_SEARCH_PLACEHOLDER`, `TRASH_QP_ADD_LABEL` all present |
| `tools/arrconf-ui/web/src/lib/TrashCFPicker.svelte` | CF picker, searchable multi-select, classification, add/remove | ✓ VERIFIED | 333 lines; CR-01 fixed (flatMap dedup, per-id chip, `removeId(entryIdx,idIdx)`); `classify()`+`labelFor()`; `badge-custom`+`badge-warn`; `new Set(selected)` safe reassign; 0 hardcoded colors |
| `tools/arrconf-ui/web/src/lib/TrashQPPicker.svelte` | QP picker append-only + collision guard | ✓ VERIFIED | 268 lines; CR-02 fixed (no `min_format_score:1` in upgrade block); `hasCollision`+`collisionName`; `[...existingProfiles, newEntry]`; `disabled` on collision; 0 mutations of existing entries |
| `tools/arrconf-ui/web/src/lib/RecyclarrReferencePicker.svelte` | Read-only Recyclarr dropdown + clipboard copy | ✓ VERIFIED | 196 lines; 0 `onChange`, 0 `include:`; WR-05 fixed (clipboard fallback on non-secure context); `RECYCLARR_REFERENCE_LABEL`+lock badge present |
| `tools/arrconf-ui/web/src/lib/AppSection.svelte` | `configarrMode` gate + 3 picker mount points | ✓ VERIFIED | `configarrMode?:boolean` prop; `{#if configarrMode && (sectionName==='sonarr' \|\| sectionName==='radarr')}` guard; all 3 pickers mounted with correct props; `updateMain()` reuses existing `onChange→PUT` path |
| `tools/arrconf-ui/web/src/App.svelte` | Passes `configarrMode={true}` + `localDefinitions` on configarr branch only | ✓ VERIFIED | Line 195: `configarrMode={true}`; `localDefinitions` from `configState.customFormatDefinitions`; arrconf branch (lines 166-179) has no `configarrMode` prop |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `fetch-trash-metadata.sh` | `trash-metadata/` dir | writes 6 JSON + manifest | ✓ WIRED | All 7 files present; manifest records both SHAs and counts |
| `app.py` | `trash-metadata/*.json` | `trash_metadata_dir() / f"{app}-{suffix}.json"` | ✓ WIRED | Path resolver confirmed; 3 endpoints all use it; 8 tests pass against real disk |
| `TrashCFPicker.svelte` | `/api/trash/custom-formats` | `getTrashCustomFormats(app)` in `$effect` | ✓ WIRED | Import present; `$effect` calls the function; catalog loaded into `$state` |
| `TrashQPPicker.svelte` | `/api/trash/quality-profiles` | `getTrashQualityProfiles(app)` in `$effect` | ✓ WIRED | Import present; `$effect` calls the function |
| `RecyclarrReferencePicker.svelte` | `/api/trash/recyclarr-templates` | `getRecyclarrTemplates(app)` in `$effect` | ✓ WIRED | Import present; `$effect` calls the function |
| `AppSection.svelte` | `TrashCFPicker / TrashQPPicker / RecyclarrReferencePicker` | `{#if configarrMode && sonarr\|radarr}` | ✓ WIRED | Mount block at line 97; all 3 picker imports at top of file |
| `App.svelte` | `AppSection.svelte` | `configarrMode={true}` on configarr branch only | ✓ WIRED | `configarrMode={true}` at line 195 (configarr branch); arrconf branch (lines 170-177) has no such prop |
| Picker `onChange` | existing `PUT /api/configarr/config` path | `updateMain(key, next) → onChange → updateAppSection → PUT` | ✓ WIRED | `updateMain()` wraps the existing `onChange` prop; no second write path; Phase 25 ruyaml tag-safety preserved |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `TrashCFPicker.svelte` | `catalog` | `GET /api/trash/custom-formats?app=` → disk JSON | Yes — 235/240 baked entries; 8 tests pass | ✓ FLOWING |
| `TrashQPPicker.svelte` | `catalog` | `GET /api/trash/quality-profiles?app=` → disk JSON | Yes — 19/36 baked entries | ✓ FLOWING |
| `RecyclarrReferencePicker.svelte` | `templates` | `GET /api/trash/recyclarr-templates?app=` → disk JSON | Yes — 34/64 baked entries | ✓ FLOWING |
| `AppSection.svelte` | `mainCustomFormats`, `mainProfiles` | `$derived` from `value.main.custom_formats` / `value.main.quality_profiles` | Yes — reflects real configarr.yml data passed in from App.svelte | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend test suite (8 trash endpoint tests) | `cd tools/arrconf-ui && uv run pytest tests/test_trash_endpoints.py -v` | 8 passed in 0.42s | ✓ PASS |
| Full backend test suite | `cd tools/arrconf-ui && uv run pytest -v` | 73 passed in 2.42s | ✓ PASS |
| Backend triade (ruff format + check + mypy arrconf_ui) | `cd tools/arrconf-ui && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf_ui` | All pass, 0 issues | ✓ PASS |
| Frontend svelte-check | `cd tools/arrconf-ui/web && npm run check` | 95 files, 0 errors, 0 warnings | ✓ PASS |
| Frontend production build | `cd tools/arrconf-ui/web && npm run build` | 146 modules transformed, built in 971ms | ✓ PASS |
| Catalog structure validation | `python3 -c "..."` on all 6 JSON files | All valid; counts match manifest; fr-vff absent | ✓ PASS |
| No values.yaml co-bump | `git log --oneline charts/arr-stack/values.yaml` | Most recent Phase 27 commit to values.yaml: none (last is Phase 24) | ✓ PASS |
| ADR-5: no *arr URLs in picker/api files | `grep -rE "8989\|7878\|9696\|sonarr\.selfhost\|radarr\.selfhost\|prowlarr\." web/src/lib/ web/src/api.ts web/src/types.ts` | 0 matches | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CFGUI-05 | Plans 01, 02, 03, 04 | CF picker by name backed by baked catalog, no manual trash_id | ✓ SATISFIED | TrashCFPicker.svelte wired to `/api/trash/custom-formats`; add/remove/classify implemented and operator-verified |
| CFGUI-06 | Plans 01, 02, 04 | Recyclarr templates as read-only reference, no `include:` insertion | ✓ SATISFIED | RecyclarrReferencePicker.svelte: 0 `onChange`, 0 `include:`, clipboard-only action; operator-verified |
| CFGUI-08 | Plans 01, 02, 03, 04 | QP picker add-as-new, hand-rolled profiles untouched, collision blocked | ✓ SATISFIED | TrashQPPicker.svelte: append-only spread, `hasCollision` guard, disabled button, CR-02 fix confirms catalog's `minFormatScore` used; operator-verified |

No orphaned requirements: CFGUI-05/06/08 are the only REQUIREMENTS.md entries assigned to Phase 27.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `TrashCFPicker.svelte` | 35 | `error = String(e)` surfaces raw error (may include server path) to operator | ⚠ Warning (WR-04) | LAN-trusted tool; absolute path disclosed in error panel — cosmetic, not a security gate |
| `TrashQPPicker.svelte` | 29 | `error = String(e)` same issue | ⚠ Warning (WR-04) | Same as above |
| `RecyclarrReferencePicker.svelte` | 29 | `error = String(e)` same issue (clipboard errors now use `RECYCLARR_COPY_FAILED_TEXT` — only fetch errors remain raw) | ⚠ Warning (WR-04) | Same as above |
| `TrashQPPicker.svelte` | 34-38 | Collision check is exact-string, case/whitespace-sensitive (WR-01) | ⚠ Warning (WR-01) | `MULTi.VF` vs `multi.vf` passes gate; produces a second profile — unintended but not data-destructive; noted as known follow-up in 27-REVIEW.md |
| `TrashQPPicker.svelte` | 65-71 | Whitespace-only `nameOverride` not blocked (WR-03) | ⚠ Warning (WR-03) | Can insert profile with `name: "   "` — invalid downstream; cosmetic; known follow-up |
| `fetch-trash-metadata.sh` | 42-54,68-80 | Shell fetches tree/recyclarr JSON then Python re-fetches same URLs (WR-06) | ℹ Info (WR-06) | Wasteful double round-trip at dev time; no runtime impact; known follow-up |
| `fetch-trash-metadata.sh` | 36 | `--dry-run` message says "7 files + manifest" (should be "6 catalogs + manifest") (IN-02) | ℹ Info (IN-02) | Cosmetic wording confusion; no functional impact |
| `fetch-trash-metadata.sh` | 151 | `# type: ignore[arg-type]` unnecessary after isinstance guard (IN-03) | ℹ Info (IN-03) | Dead comment noise; no impact |
| `App.svelte` | 196 | `customFormatDefinitions` cast is lossy narrowing — malformed local def (missing `trash_id`) would cause `classify()` to label as 'unknown' (IN-04) | ℹ Info (IN-04) | Display-only badge impact; no data loss; known follow-up |

All warnings above are tracked in `27-REVIEW.md` as non-blocking known follow-ups. None prevent the phase goal from being achieved.

### Human Verification Required

The following items require human testing. All automated checks pass; the gate is the UX-level behavior that cannot be verified programmatically.

#### 1. QP collision check normalization (WR-01)

**Test:** In the running UI, switch to `configarr.yml`, expand `sonarr`. In the QP picker, pick any TRaSH profile, then type `multi.vf` (lowercase of the hand-rolled `MULTi.VF`) in the name override field. Attempt to insert.
**Expected:** Either the collision is blocked (if normalization is deemed required) OR the insert creates a second profile with that lowercase name (current behavior — operator should decide if this is acceptable for the homelab use-case).
**Why human:** `hasCollision` uses exact-string comparison; programmatic verification cannot decide whether the current behavior is acceptable or a blocker.

#### 2. QP field mapping in saved configarr.yml (MEDIUM-confidence, research correction #4)

**Test:** Insert a TRaSH quality profile. Open the diff preview, then save. Inspect `charts/arr-stack/files/configarr.yml` — examine the new `quality_profiles[]` entry.
**Expected:** `upgrade.until_quality` == TRaSH `cutoff` field value; `qualities[]` entries appear in baked catalog order (not re-sorted); no `upgrade.min_format_score` key (CR-02 fix confirmed); `min_format_score` at top level comes from catalog's `minFormatScore`.
**Why human:** Operator approved this mapping in the Plan 04 checkpoint; this re-verification item confirms the fix is still present in the post-CR commit (it is, per code read and CR-02 grep) and that no regression appeared. Programmatic check is insufficient for the correctness of the YAML structure semantics.

### Gaps Summary

No blocking gaps. All 5 ROADMAP success criteria are verified against actual code. The two human verification items are UX-quality and field-mapping confirmation checks, not missing functionality.

Known follow-ups (tracked in `27-REVIEW.md`, all non-blocking):
- WR-01: Case/whitespace-insensitive collision check
- WR-02: `trash_description` HTML entity handling
- WR-03: Whitespace-only nameOverride not blocked
- WR-04: Raw error strings surfaced to operator
- WR-06: Double round-trip in fetch script
- IN-02/IN-03/IN-04: Minor code/comment quality items

---

_Verified: 2026-05-31_
_Verifier: Claude (gsd-verifier)_
