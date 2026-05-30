# Phase 27: TRaSH CF Picker + Recyclarr Reference + QP Picker - Research

**Researched:** 2026-05-30
**Domain:** arrconf-ui Svelte frontend metadata pickers — build-time-baked TRaSH/Recyclarr catalogs
**Confidence:** HIGH (all external sources verified live; configarr source code inspected)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**TRaSH CF picker — ID classification (SC#4)**
- D-01: Resolve every existing `custom_formats[].trash_ids` entry against BOTH sources: the baked TRaSH catalog AND the file's own `customFormatDefinitions[].trash_id`. An ID found in either is "known".
- D-02: A `trash_id` that resolves only against local `customFormatDefinitions` (e.g. `fr-vff`, `fr-vfi`, `fr-vfq`, `fr-multi`, `fr-vostfr`, `fr-mhd`, `fr-x265-hd`) renders with its name + a **"custom" badge** — NOT a warning.
- D-03: A `trash_id` in neither the catalog nor local definitions renders with a **warning indicator** (icon + tooltip "unknown trash_id — not in catalog or local definitions") and is **preserved verbatim** on save.

**TRaSH CF picker — insertion semantics (CFGUI-05)**
- D-04: Each picked CF is written as its own `custom_formats[]` entry: `{ trash_ids: [<id>], assign_scores_to: [<all quality_profiles in that app>] }` with no explicit `score`.
- D-05: Picker is a **searchable multi-select** — tick several CFs, each becomes its own entry on confirm. Removal = a remove control on each existing entry/chip.
- D-06: Picker is **app-context-filtered**: sonarr section → sonarr CFs; radarr section → radarr CFs.

**Baked catalog scope + pinning (SC#2)**
- D-07: Catalog metadata per CF: `{ name, trash_id, default_score, app: sonarr|radarr }`, split by app. Quality-profile catalog baked too (for CFGUI-08), per app. Dev-time fetch script (`tools/scripts/fetch-trash-metadata.sh`) pulls + commits as static assets under `tools/arrconf-ui/web/src/assets/trash-metadata/`. No quality_definition/media_naming catalogs (out of scope).
- D-08: Pin to **latest stable HEAD** of TRaSH-Guides + Recyclarr config-templates at build time. Record the resolved SHAs in a manifest committed with the assets. **See D-08 Risk Assessment below** — D-08 risk is LOW because configarr itself also resolves TRaSH HEAD at apply time.

**TRaSH QP picker (CFGUI-08)**
- D-09: Picker **appends only** — a new `quality_profiles[]` entry seeded from the TRaSH template. The 3 hand-rolled profiles (MULTi.VF / Anime / Family) are never modified or reordered.
- D-10: **Name collision** (picked template name already exists in `quality_profiles[]`) → **block + warn**, require rename before insert.
- D-11: QP picker is app-context-filtered (sonarr vs radarr QP catalogs), same as CF picker.

**Recyclarr reference dropdown (CFGUI-06 — read-only)**
- D-12: Lives inside each app's section (sonarr / radarr), filtered to that app's templates (~34 sonarr / ~64 radarr). Selecting a template shows name + description in a read-only panel. Clearly labelled "Reference only — no `include:` inserted".
- D-13: Only convenience action is a **"copy template name"** button (clipboard). No config mutation of any kind.

### Claude's Discretion
- Exact component names (research suggests `TrashPicker.svelte`, `RecyclarrTemplatePicker.svelte`; QP picker component name = planner's call).
- Read-only metadata endpoint shapes (research suggests `GET /api/trash/custom-formats?app=…`, `GET /api/trash/quality-profiles?app=…`) — follow existing arrconf-ui endpoint patterns; MUST serve from baked assets, no GitHub HTTP.
- Picker search/styling, default-score display formatting, chip/badge visuals (use existing CSS tokens / dark theme / IBM Plex).
- Diff-preview grouping for newly-inserted CF/QP entries (reuse Phase 25 configarr structured diff).
- i18n keys (FR) for picker labels, "custom"/"unknown" badges, collision warning, Recyclarr reference panel — follow `web/src/i18n/fr.ts`.
- Exact pinned SHAs + manifest format (planner, per D-08 verification).

### Deferred Ideas (OUT OF SCOPE)
- Recyclarr `include:` insertion → CFGUI-F1 / v1.x (merge-hazard vs the 6 hand-rolled French CFs)
- Live catalog refresh + trash_id drift detection → CFGUI-F2 / v1.x
- Deep quality_definition / media_naming editing → CFGUI-F3 / v1.x (read-only since Phase 26)
- QP picker overwrite/merge of existing profiles → explicitly rejected (add-as-new only, D-09)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFGUI-05 | Operator adds/removes TRaSH custom formats by name via picker backed by baked catalog (`name → trash_id`). No manual hex entry. | TRaSH CF JSON structure verified: `docs/json/{sonarr,radarr}/cf/*.json` — each file has `trash_id`, `name`, `trash_scores.default`. 235 sonarr + 240 radarr CF files at HEAD. |
| CFGUI-06 | Recyclarr templates surfaced as read-only informational dropdown. No `include:` insertion. | `includes.json` structure verified: 64 radarr + 34 sonarr template IDs, each `{ template: path, id: string }`. No description field — ID is the display value. |
| CFGUI-08 | Operator applies TRaSH quality profile by name via picker. Append-only into `quality_profiles[]`. 3 hand-rolled profiles never modified. Name collision → block + warn. | TRaSH QP JSON structure verified: 19 sonarr + 36 radarr QP files. Configarr resolves QPs by `trash_id` key in its cache. Full QP YAML generation from TRaSH JSON is the correct insertion path (not `include:` directive). |
</phase_requirements>

---

## Summary

Phase 27 adds three metadata-driven helpers to the arrconf-ui Svelte frontend. All depend on a build-time-baked catalog committed as static assets — no GitHub network calls at UI runtime. The Phase 26 foundation (configarr form, `FieldInput.svelte`, `AppSection.svelte`, `configarr_diff.py`) is fully in place.

The research confirmed the exact JSON shapes needed for all three catalogs, resolved the critical D-08 risk question, and identified the correct insertion mechanism for the QP picker. The key finding: configarr v1.28.0 clones TRaSH-Guides at `trashRevision ?? "master"` at apply time — it does NOT bundle a pinned TRaSH version. Baking the Phase 27 catalog from HEAD is therefore consistent with what configarr will resolve. The D-08 risk (baked ID that configarr can't resolve) is LOW, not a blocking concern.

The Feb-2026 TRaSH breaking change (PR #2590 merged 2026-02-20) changed CF group semantics and quality ordering. configarr v1.22.0 added support for the new semantics and handles both old and new formats. This change only affects cf-groups and quality-profile ordering — the individual CF `trash_id`, `name`, and `trash_scores.default` fields (what the baked catalog needs) are unaffected.

**Primary recommendation:** Implement the fetch script first (Wave 0 / task 0) to produce the committed assets — all three picker components depend on them. The backend endpoints are simple disk-serve additions to `app.py`. The frontend components are new but follow the established Svelte 5 runes + IBM Plex token pattern.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CF/QP/Recyclarr catalog fetch | Dev-time script | — | Build-time baked, committed to git; no runtime dependency |
| Catalog serving at runtime | API / Backend (FastAPI) | — | Static file serve from `trash-metadata/` dir; MUST NOT call GitHub |
| CF picker UI + app-context filter | Browser / Client (Svelte) | — | Pure frontend; reads catalog from backend API |
| QP picker UI + collision guard | Browser / Client (Svelte) | — | Reads current `quality_profiles[]` from config state for collision check |
| Recyclarr reference dropdown | Browser / Client (Svelte) | — | Read-only display; clipboard copy only |
| CF/QP write-back into configarr.yml | API / Backend (FastAPI) | — | Existing PUT `/api/configarr/config` path — no new write endpoint |
| trash_id resolution at apply | configarr CronJob (in-cluster) | — | ADR-5: arrconf-ui never contacts *arr APIs; configarr owns resolution |

---

## Standard Stack

### Core (no new dependencies — confirmed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Svelte 5 | existing | New picker components | Already in project; runes API established |
| FastAPI | existing | 2 new read-only metadata endpoints | Mirrors existing endpoint pattern in `app.py` |
| Python stdlib (json, pathlib) | existing | Serve baked JSON from disk | No new pip dep needed |
| Bash + curl/python3 | existing | Dev-time fetch script | No new toolchain dep |

`[VERIFIED: direct code inspection of tools/arrconf-ui/]` — zero new pip or npm dependencies confirmed by prior research (SUMMARY.md HIGH confidence).

### Baked Catalog Asset Shape (new files, no new deps)

```
tools/arrconf-ui/web/src/assets/trash-metadata/
├── sonarr-cf.json           # [{trash_id, name, default_score}] — 235 entries
├── radarr-cf.json           # [{trash_id, name, default_score}] — 240 entries
├── sonarr-qp.json           # [{trash_id, name, trash_description, trash_score_set}] — 19 entries
├── radarr-qp.json           # [{trash_id, name, trash_description, trash_score_set}] — 36 entries
├── recyclarr-sonarr.json    # [{id, template}] — 34 entries
├── recyclarr-radarr.json    # [{id, template}] — 64 entries
└── manifest.json            # {trash_sha, recyclarr_sha, fetched_at}
```

`[VERIFIED: github.com/TRaSH-Guides/Guides, github.com/recyclarr/config-templates via Python urllib inspection 2026-05-30]`

---

## Architecture Patterns

### System Architecture Diagram

```
Dev workstation (fetch script runs once, output committed)
  tools/scripts/fetch-trash-metadata.sh
    ├── curl TRaSH-Guides HEAD SHA + docs/json/{sonarr,radarr}/cf/*.json
    ├── curl TRaSH-Guides HEAD SHA + docs/json/{sonarr,radarr}/quality-profiles/*.json
    ├── curl recyclarr/config-templates HEAD SHA + includes.json
    ├── transform → 6 JSON files + manifest.json
    └── commit to tools/arrconf-ui/web/src/assets/trash-metadata/

Operator browser (runtime)
  GET /api/trash/custom-formats?app=sonarr|radarr
  GET /api/trash/quality-profiles?app=sonarr|radarr
    → FastAPI (app.py) reads baked JSON from disk
    → NO GitHub HTTP at runtime

  Svelte SPA (configarr tab)
    ├── AppSection.svelte (sonarr/radarr)
    │   ├── TrashCFPicker.svelte         (CFGUI-05)
    │   │   ├── loads catalog via GET /api/trash/custom-formats?app=
    │   │   ├── searchable multi-select
    │   │   ├── resolves existing trash_ids → known (TRaSH) / custom (local def) / unknown
    │   │   └── on confirm: writes new custom_formats[] entries into config state
    │   ├── TrashQPPicker.svelte         (CFGUI-08)
    │   │   ├── loads catalog via GET /api/trash/quality-profiles?app=
    │   │   ├── collision guard vs existing quality_profiles[].name
    │   │   └── on confirm: appends new quality_profiles[] entry into config state
    │   └── RecyclarrReferencePicker.svelte  (CFGUI-06)
    │       ├── reads baked recyclarr catalog via GET /api/trash/recyclarr-templates?app=
    │       ├── shows id as display name (no description field in includes.json)
    │       └── clipboard copy only — no config write
    │
  PUT /api/configarr/config (existing path, unchanged)
    → writes updated config state → configarr.yml on disk
```

### Recommended Project Structure

No structural change to existing layout. New files only:

```
tools/scripts/
└── fetch-trash-metadata.sh        # NEW — dev-time catalog fetch

tools/arrconf-ui/
├── arrconf_ui/
│   └── app.py                     # MODIFIED — add 2-3 read-only metadata endpoints
└── web/src/
    ├── assets/
    │   └── trash-metadata/        # NEW — baked catalog + manifest (committed)
    │       ├── sonarr-cf.json
    │       ├── radarr-cf.json
    │       ├── sonarr-qp.json
    │       ├── radarr-qp.json
    │       ├── recyclarr-sonarr.json
    │       ├── recyclarr-radarr.json
    │       └── manifest.json
    ├── api.ts                     # MODIFIED — add 2-3 fetch functions
    ├── types.ts                   # MODIFIED — add TrashCFEntry, TrashQPEntry, RecyclarrTemplateEntry
    ├── i18n/fr.ts                 # MODIFIED — picker labels/badges in FR
    └── lib/
        ├── FieldInput.svelte      # POSSIBLY MODIFIED — hook for x-widget dispatch (planner's call)
        ├── AppSection.svelte      # MODIFIED — add 3 picker components below each instance
        ├── TrashCFPicker.svelte   # NEW
        ├── TrashQPPicker.svelte   # NEW
        └── RecyclarrReferencePicker.svelte  # NEW
```

---

## Critical Verified Facts

### TRaSH-Guides JSON Structure

`[VERIFIED: github.com/TRaSH-Guides/Guides master branch, inspected 2026-05-30 SHA 1ef7baa523a5]`

**CF file shape** (`docs/json/{sonarr|radarr}/cf/<name>.json`):
```json
{
  "trash_id": "32b367365729d530ca1c124a0b180c64",
  "trash_scores": {
    "default": -10000,
    "french-multi-vf": 0
  },
  "name": "Bad Dual Groups",
  "includeCustomFormatWhenRenaming": false,
  "specifications": [...]
}
```

Key for baked catalog: `trash_id`, `name`, `trash_scores.default` (may be absent → treat as 0).

**CF counts:** sonarr: 235 files | radarr: 240 files (at HEAD 2026-05-30).

**QP file shape** (`docs/json/{sonarr|radarr}/quality-profiles/<name>.json`):
```json
{
  "trash_id": "72dae194fc92bf828f32cde7744e51a1",
  "name": "WEB-1080p",
  "trash_description": "Quality Profile that covers:<br>- WEBDL: 1080p",
  "trash_score_set": "french-multi-vf",
  "upgradeAllowed": true,
  "cutoff": "WEB 1080p",
  "minFormatScore": 0,
  "cutoffFormatScore": 10000,
  "minUpgradeFormatScore": 1,
  "language": "French",
  "items": [{"name": "WEB 1080p", "allowed": true, "items": ["WEBRip-1080p", "WEBDL-1080p"]}, ...],
  "formatItems": {"Repack/Proper": "ec8fa7296b64e8cd390a1600981f3923", ...}
}
```

Key for baked catalog: `trash_id`, `name`, `trash_description` (for display), `trash_score_set` (to identify the French profiles). `items` is needed to generate the `qualities[]` list when creating a new QP entry.

**QP counts:** sonarr: 19 files | radarr: 36 files.

**Feb-2026 breaking change (TRaSH PR #2590, merged 2026-02-20):** Changed CF group semantics (include-based instead of exclude-based) and inverted quality ordering in QP files to human-readable (highest-to-lowest). `[VERIFIED: github.com/TRaSH-Guides/Guides commit 2994a7979d80, github.com/raydak-labs/configarr issues #392/#393]`

**Impact on Phase 27 baked catalog:** The breaking change affects `cf-groups/` files and QP `items` ordering — it does NOT affect the individual CF `trash_id`, `name`, `trash_scores.default` fields used by the baked CF catalog. The QP catalog uses `items` for quality group generation, but since configarr v1.22.0 handles new QP ordering natively, a QP inserted from the HEAD baked catalog will be applied correctly by configarr v1.28.0.

### Recyclarr config-templates Structure

`[VERIFIED: github.com/recyclarr/config-templates, includes.json inspected 2026-05-30 HEAD SHA 505c1e565c08]`

`includes.json` shape:
```json
{
  "radarr": [
    {"template": "radarr/includes/custom-formats/radarr-custom-formats-anime.yml", "id": "radarr-custom-formats-anime"},
    ...
  ],
  "sonarr": [
    {"template": "sonarr/includes/custom-formats/sonarr-v4-custom-formats-anime.yml", "id": "sonarr-v4-custom-formats-anime"},
    ...
  ]
}
```

**No description field** — the `id` string is both the identifier and the display label. The baked `recyclarr-{sonarr|radarr}.json` should store `[{id}]` only (the `template` path is not needed for a reference-only dropdown). 64 radarr + 34 sonarr template IDs confirmed.

**Template structure example** (`radarr-quality-profile-hd-bluray-web.yml`):
```yaml
quality_profiles:
  - name: HD Bluray + WEB
    reset_unmatched_scores:
      enabled: true
    upgrade:
      allowed: true
      until_quality: Bluray-1080p
      until_score: 10000
```

No embedded description field — only the template ID (from `includes.json`) is available. The reference dropdown shows the ID as-is.

**Fork-point SHA note (informational):** The "configarr forked from Recyclarr v7" refers to the Recyclarr TOOL (v7.4.0 released 2024-11-11), not to a pinned `config-templates` git SHA. configarr clones `recyclarr/config-templates` at `recyclarrRevision ?? "master"` at apply time — same as TRaSH-Guides. No config-templates-specific fork-point SHA exists; the compatibility concern is about YAML schema format (configarr implements Recyclarr v7.2.0+ `assign_scores_to` syntax and warns on deprecated `quality_profiles` key).

### D-08 Risk Assessment: Configarr v1.28.0 Trash_id Resolution

`[VERIFIED: github.com/raydak-labs/configarr src/trash-guide.ts + src/recyclarr-importer.ts, inspected 2026-05-30]`

**How configarr resolves trash_ids at apply time:**
1. `cloneTrashRepo()` clones `trashGuideUrl ?? "https://github.com/TRaSH-Guides/Guides"` at `trashRevision ?? "master"` on each CronJob run
2. `loadQPFromTrash()` builds a `Map<trash_id, TrashQP>` from `docs/json/{sonarr|radarr}/quality-profiles/*.json`
3. `loadTrashCFs()` builds `Map<trash_id, ConfigarrCF>` from `docs/json/{sonarr|radarr}/cf/*.json`
4. The `include` section with `source: "TRASH"` checks `trash.has(current.template)` — where `template` is the `trash_id` string

**D-08 risk verdict: LOW.** The baked catalog and configarr both resolve against TRaSH-Guides master. A baked ID that doesn't exist in configarr's cloned TRaSH copy is only possible if:
- configarr has a stale git clone cache (it detects URL changes, but may not re-clone on revision changes)
- OR the baked catalog was captured at a newer HEAD than configarr's cached clone

**Mitigation (documentation approach, sufficient for homelab scope):** Include a note in the Phase 27 runbook: "After updating the baked catalog (re-running fetch-trash-metadata.sh), run `arrconf apply --dry-run` against the current cluster config to verify configarr accepts the new IDs. If configarr logs `Custom format not found`, its TRaSH cache may be stale — the next CronJob run will re-clone and resolve." No CI cross-check needed for homelab scale.

**configarr v1.28.0 CF-group improvement:** The v1.28.0 release (2026-05-04) specifically improved "handling of TRaSH CF groups" (issue #433). This is about the `cf-groups` feature — NOT about individual CF `trash_id` resolution. The baked catalog uses individual CF files, not cf-groups, so this change is neutral.

### QP Picker Insertion Mechanism

`[VERIFIED: configarr src/types/config.types.ts + configarr docs config-file.md, inspected 2026-05-30]`

Two mechanisms exist in configarr for adding TRaSH quality profiles:

1. **`include` with `source: "TRASH"` + `template: <trash_id>`** — configarr looks up the `trash_id` in its QP map and applies the TRaSH template. Available since v1.18.0. This is what D-08 describes for include-based insertion.

2. **Full `quality_profiles[]` entry** — a manually-authored YAML block with `name`, `reset_unmatched_scores`, `upgrade`, `qualities[]`. This is what the 3 existing hand-rolled profiles use.

**For the QP picker (D-09), the correct approach is OPTION 2: generate a full `quality_profiles[]` entry seeded from the TRaSH QP JSON.** This is because:
- The picker goal is add-as-new with operator visibility of what's being inserted
- D-09 explicitly says "append a new `quality_profiles[]` entry seeded from the TRaSH template"
- The `include` mechanism would be hidden in the config (operator can't easily see or modify the resulting profile)
- The full entry approach is consistent with the existing 3 profiles — operator can subsequently tune it via the Phase 26 form

**QP JSON → configarr YAML mapping:**
```
TRaSH JSON                      configarr quality_profiles[] YAML
-------------------------------------------------------------------
name                         → name (operator may rename per D-10 rename-before-insert)
upgradeAllowed = true        → upgrade.allowed: true
cutoff                       → upgrade.until_quality: <cutoff>
cutoffFormatScore (default?) → upgrade.until_score: 10000 (TRaSH default)
minFormatScore               → min_format_score: <minFormatScore>
language (if present)        → language: <language>
items[].name + .items        → qualities[].name (+ .qualities for groups)
items[].allowed              → filter: only allowed:true items
```

The `formatItems` dict (CF scoring) is NOT transferred — that's handled separately by the CF picker. The new QP entry has no custom format scores by default; the operator adds them via the Phase 26 form.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Searching 235-240 CFs by name | Custom fuzzy search | Native browser `<input>` with `Array.filter()` or a minimal Svelte list filter | Volume is small (~500 items total); no library needed |
| Fetching TRaSH JSON at runtime | GitHub API calls from FastAPI | Pre-baked JSON served from disk | Rate-limit risk; offline-incompatible; ADR-5 contamination |
| Configarr QP apply logic | Re-implementing TRaSH→*arr API transform in Python | Let configarr do it — UI writes the full YAML entry to configarr.yml | Duplicates configarr's engine; ADR-5 violation |
| Recyclarr template text descriptions | Scraping recyclarr template YAML for first-line comments | Display `id` string as-is | No description field exists in includes.json; id is self-descriptive |

---

## Common Pitfalls

### Pitfall 1: Assuming Recyclarr Templates Have Descriptions

**What goes wrong:** Planner or implementer expects `includes.json` to have a `description` field for each template, and designs the UI around showing rich descriptions.

**Why it happens:** Research summaries (including earlier project research) mentioned "name + description" for the Recyclarr dropdown. The live `includes.json` structure has only `{ template: path, id: string }`.

**How to avoid:** Display the `id` field directly as the dropdown label. The id strings are already descriptive (e.g., `sonarr-v4-quality-profile-bluray-web-1080p-french-multi-vf`). If the operator wants to inspect a template's content, the `template` path can be shown as a secondary subtitle pointing to the GitHub file path.

**Warning signs:** Dropdown renders empty strings or `undefined` in the description slot.

### Pitfall 2: QP JSON `items` Ordering Change (Feb-2026)

**What goes wrong:** The baked catalog snapshot captures QP `items` in the new human-readable order (highest quality first), but older versions of configarr (< v1.22.0) expected the API-reversed order. If the project ever downgrades configarr, QP inserts would create mis-ordered quality lists.

**Why it happens:** TRaSH PR #2590 inverted the `items` order in QP JSON files on 2026-02-20. configarr v1.22.0 added support.

**How to avoid:** Not a concern for v1.28.0 (the deployed version). Document in the runbook: "Baked QP catalog uses Feb-2026+ TRaSH ordering; requires configarr >= v1.22.0." If configarr is ever downgraded, re-bake the catalog from a pre-2026-02-20 commit.

**Warning signs:** After QP insert + configarr apply, Sonarr/Radarr shows the quality profile with qualities in inverted order.

### Pitfall 3: French CF Local IDs Look Like TRaSH IDs to the Picker

**What goes wrong:** The 7 French custom format IDs (`fr-vff`, `fr-vfi`, `fr-vfq`, `fr-multi`, `fr-vostfr`, `fr-mhd`, `fr-x265-hd`) are human-readable strings, NOT UUID-style TRaSH IDs. A naive picker that matches only hex-UUID patterns would mark them as "unknown".

**Why it happens:** TRaSH trash_ids look like `32b367365729d530ca1c124a0b180c64` (hex UUID without dashes). The French CFs use `fr-vff` style. A pattern-based classifier would get this wrong.

**How to avoid:** D-01/D-02 define the resolution logic explicitly: check BOTH the baked TRaSH catalog AND `customFormatDefinitions[].trash_id` from the same config file. An ID found in `customFormatDefinitions` is "custom" (badge, not warning). Never use hex-UUID pattern matching as the sole classification signal.

### Pitfall 4: App-Context Contamination (Wrong CF Set Shown)

**What goes wrong:** The CF picker shows sonarr CFs while editing the radarr section, allowing the operator to insert a sonarr-specific CF into radarr's `custom_formats[]`.

**Why it happens:** `AppSection.svelte` renders both sonarr and radarr instances; if the picker component doesn't receive the active `sectionName`, it may default to all CFs.

**How to avoid:** D-06/D-11 mandate app-context filtering. The `AppSection.svelte` already passes `sectionName` as a prop. The picker component MUST accept a `app: 'sonarr' | 'radarr'` prop and filter the catalog accordingly. Backend endpoint uses `?app=sonarr|radarr` query param.

### Pitfall 5: Svelte 5 Picker Multi-select State Management

**What goes wrong:** A multi-select picker in Svelte 5 using `$state` for a `Set<string>` of selected IDs triggers reactivity issues if the Set is mutated in place.

**Why it happens:** Svelte 5 `$state` uses fine-grained reactivity; mutating an object/Set in-place without reassignment does not trigger re-renders.

**How to avoid:** Use `$state(new Set<string>())` + reassign on toggle:
```typescript
let selected = $state(new Set<string>());
function toggle(id: string) {
  const next = new Set(selected);
  if (next.has(id)) { next.delete(id); } else { next.add(id); }
  selected = next; // reassignment triggers reactivity
}
```

### Pitfall 6: Fetch Script Commits Binary/Large Assets

**What goes wrong:** The fetch script downloads the full TRaSH-Guides repo (hundreds of MB) and commits it.

**Why it happens:** Naive `git clone` instead of sparse fetch.

**How to avoid:** The script must use:
- GitHub raw URLs to fetch only the needed JSON files directly (curl per-file), OR
- GitHub Contents API to list files + fetch each one
- Never clone the full repo in the script

Output is ~500 KB total (235+240+19+36 small JSON files → transformed compact output).

---

## Code Examples

### Baked Catalog Production — CF Entry Shape

`[VERIFIED: TRaSH-Guides docs/json/sonarr/cf/bad-dual-groups.json, 2026-05-30]`

```python
# In fetch-trash-metadata.sh (or a Python helper it calls)
# Each CF source file shape:
cf_entry = {
    "trash_id": "32b367365729d530ca1c124a0b180c64",
    "name": "Bad Dual Groups",
    "default_score": -10000  # from trash_scores.default, default 0 if absent
}
```

Transform logic: `default_score = entry.get("trash_scores", {}).get("default", 0)`

### Baked Catalog Production — QP Entry Shape

`[VERIFIED: TRaSH-Guides docs/json/sonarr/quality-profiles/french-multi-vf-bluray-web-1080p.json, 2026-05-30]`

```python
qp_entry = {
    "trash_id": "58e8dc75731040612dd6f4ac0676bfd7",
    "name": "[French MULTi.VF] HD Bluray + WEB (1080p)",
    "trash_description": "French Quality Profile that covers:<br>- WEBDL: 720p, 1080p<br>- Bluray 720p, 1080p",
    "trash_score_set": "french-multi-vf",  # optional, for display hint
    "upgradeAllowed": True,
    "cutoff": "Bluray|WEB 1080p",
    "minFormatScore": 0,
    "cutoffFormatScore": 10000,
    "items": [...]  # quality groups, for YAML generation
}
```

The `items` array is needed to generate `qualities[]` when inserting a new profile.

### QP Insert YAML Generation (UI-side, TypeScript)

`[ASSUMED — shape derived from configarr types/config.types.ts InputConfigQualityProfile inspection]`

```typescript
// TrashQPPicker.svelte — on confirm, generate a quality_profiles[] entry
function generateQPEntry(qp: TrashQPEntry, profileName: string): QualityProfileEntry {
  const qualities = qp.items
    .filter(item => item.allowed !== false)  // only allowed quality groups
    .map(item => item.items
      ? { name: item.name, qualities: item.items }
      : { name: item.name }
    );
  return {
    name: profileName,  // operator may have renamed to avoid collision
    language: qp.language ?? 'Any',
    reset_unmatched_scores: { enabled: true },
    upgrade: {
      allowed: qp.upgradeAllowed,
      until_quality: qp.cutoff,
      until_score: qp.cutoffFormatScore ?? 10000,
      min_format_score: 1,
    },
    min_format_score: qp.minFormatScore ?? 0,
    quality_sort: 'top',
    qualities,
  };
}
```

### Backend Metadata Endpoint (FastAPI, Pattern)

`[VERIFIED: tools/arrconf-ui/arrconf_ui/app.py existing endpoint pattern]`

```python
# In create_app() in app.py — follows existing /api/schema pattern
@app.get("/api/trash/custom-formats")
def get_trash_custom_formats(app: str) -> Any:
    """Return baked TRaSH CF catalog for sonarr or radarr.
    
    SC#3 boundary: NO *arr URL constructed here.
    Serves from committed static assets only.
    """
    if app not in ("sonarr", "radarr"):
        raise HTTPException(status_code=400, detail="app must be 'sonarr' or 'radarr'")
    path = trash_metadata_dir() / f"{app}-cf.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Catalog not found — run fetch-trash-metadata.sh")
    return json.loads(path.read_text(encoding="utf-8"))
```

### locator.py Extension

`[VERIFIED: tools/arrconf-ui/arrconf_ui/locator.py current state — trash_metadata_dir() missing]`

```python
def trash_metadata_dir() -> Path:
    """Return path to baked TRaSH/Recyclarr metadata assets."""
    return repo_root() / "tools" / "arrconf-ui" / "web" / "src" / "assets" / "trash-metadata"
```

### AppSection.svelte Extension Pattern

`[VERIFIED: tools/arrconf-ui/web/src/lib/AppSection.svelte inspected]`

The three pickers are added BELOW the existing `FieldInput` loop inside the instance div. The `sectionName` prop provides the app context (`'sonarr'` or `'radarr'`). Only add pickers when `activeConfig === 'configarr'` (the pickers are configarr-specific; the component is shared):

```svelte
<!-- Inside AppSection.svelte, after the existing FieldInput loop -->
{#if sectionName === 'sonarr' || sectionName === 'radarr'}
  <TrashCFPicker
    app={sectionName}
    existingEntries={...}
    localDefinitions={...}
    onChange={...}
  />
  <TrashQPPicker
    app={sectionName}
    existingProfiles={...}
    onChange={...}
  />
  <RecyclarrReferencePicker app={sectionName} />
{/if}
```

**Alternative:** The planner may choose to add a `configarrMode?: boolean` prop to `AppSection.svelte` to avoid rendering pickers when showing the arrconf form.

### Fetch Script Manifest Format

```bash
# tools/scripts/fetch-trash-metadata.sh (new file)
# Output manifest.json:
{
  "trash_sha": "1ef7baa523a5f6585a987a4dab6e06bc96994a74",
  "recyclarr_sha": "505c1e565c08d994520c0ca46fc23dee7bf99fd9",
  "fetched_at": "2026-05-30T07:20:34Z",
  "counts": {
    "sonarr_cf": 235,
    "radarr_cf": 240,
    "sonarr_qp": 19,
    "radarr_qp": 36,
    "sonarr_recyclarr": 34,
    "radarr_recyclarr": 64
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| configarr.yml `custom_formats[].trash_ids` entered manually by operator | Phase 27 picker: human-readable name → hex ID looked up automatically | Phase 27 | Eliminates hex ID transcription errors |
| TRaSH QP templates applied via `include` directive (experimental) | Phase 27: full `quality_profiles[]` entry generated from TRaSH JSON | Phase 27 | Operator can see and tune the full profile via Phase 26 form |
| Recyclarr templates referenced from memory / docs | Phase 27 dropdown: searchable ID list with copy button | Phase 27 | Discoverability without leaving the UI |
| TRaSH CF groups: exclude-based semantics | Include-based semantics (TRaSH PR #2590, Feb 2026) | 2026-02-20 | configarr v1.22.0+ required; affects cf-groups only, not individual CFs |

**Current configarr TRaSH resolution:** clones GitHub master at each apply run (no bundled version pinned). `recyclarrRevision` and `trashRevision` config fields allow operator to pin to a specific git ref if needed.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | QP picker generates a full `quality_profiles[]` entry (not an `include` directive). | QP Picker Insertion Mechanism | If `include + source:TRASH` is preferred, the code is simpler but the resulting config is less visible/editable. Either works; D-09 wording ("seeded from the TRaSH template") supports full-entry approach. |
| A2 | The `items` field in TRaSH QP JSON maps directly to configarr `qualities[]` shape after filtering `allowed:false` groups. | Code Examples — QP generation | If configarr requires ALL quality groups (including disabled ones) to be present in the YAML, the generation code needs to include them with enabled:false or similar. Low risk — configarr handles absent qualities gracefully. |
| A3 | `AppSection.svelte` is the right mount point for all three pickers (shared between arrconf and configarr tabs). | Architecture — AppSection extension | If arrconf sections also receive pickers accidentally, add a `configarrMode` guard prop. Planner's call on implementation detail. |

---

## Open Questions

1. **Recyclarr template path vs ID in the reference panel**
   - What we know: `includes.json` has both `id` (e.g., `sonarr-v4-quality-profile-web-1080p`) and `template` (relative path e.g., `sonarr/includes/quality-profiles/sonarr-v4-quality-profile-web-1080p.yml`)
   - What's unclear: Whether to show the template YAML path alongside the ID in the read-only panel, for operator reference
   - Recommendation: Show `id` as primary label; show `template` as a greyed subtitle or on hover. The `template` is the relative path within `recyclarr/config-templates` — useful for finding the file on GitHub.

2. **QP insert — `language` field handling**
   - What we know: Some TRaSH QP JSON files include a `"language": "French"` field; configarr `InputConfigQualityProfile` accepts a `language` field
   - What's unclear: Whether `language: "French"` in a configarr QP entry actually filters Sonarr/Radarr's language selection, or is informational only
   - Recommendation: Pass it through if present in the TRaSH JSON; operator can remove it via the Phase 26 form if Sonarr/Radarr ignores it.

3. **`FieldInput.svelte` vs separate picker mount**
   - What we know: `FieldInput.svelte` already handles `array of objects` for `custom_formats[]` and `quality_profiles[]` via the generic form. The picker is a specialized override.
   - What's unclear: Whether the picker replaces the generic `FieldInput` for those specific fields (via `x-widget: trash-picker` JSON Schema annotation), or whether it coexists as an add-on below the generic form.
   - Recommendation: Coexist as an add-on mounted in `AppSection.svelte` — avoids modifying the `FieldInput` dispatch logic and is cleaner for a single-phase delivery. The planner should decide based on UX goals (if the picker should replace the raw array editor, use x-widget; if it's supplementary, use add-on).

---

## Environment Availability

Step 2.6: SKIPPED (phase touches only `tools/arrconf-ui/**` — no new external tools; fetch script requires `curl` + `python3` available on dev workstation; both pre-exist in the project environment).

---

## Project Constraints (from CLAUDE.md)

- **No co-bump required:** Phase 27 touches only `tools/arrconf-ui/**` → NO arrconf image co-bump, NO chart auto-tag trigger (confirmed in STATE.md v0.9.0 roadmap decisions).
- **Python triade (arrconf-ui backend):** `uv run ruff format --check . && uv run ruff check . && uv run mypy .` must pass before any Python commit. Run from `tools/arrconf-ui/`.
- **Frontend CI quad:** `npm run check`, `npm run typecheck`, `npm run build` — no Vitest in CI (no `npm test` step in `tests.yml`; frontend CI is check+typecheck+build).
- **ADR-5 boundary (MANDATORY):** No Sonarr/Radarr/Prowlarr URL anywhere in arrconf-ui source. No `arrconf.reconcilers.*` import. The new metadata endpoints serve baked files from disk only.
- **No bare `except:` / silent swallow** (engineering.md).
- **No new pip/npm dependencies** — confirmed by existing research, this phase adds zero new packages.
- **ruyaml tag safety:** The existing write path is untouched by this phase; the new metadata endpoints are read-only. No tag-preservation risk introduced.
- **Renovate annotations:** No chart changes in this phase; no `# renovate: image=...` annotations affected.

---

## Sources

### Primary (HIGH confidence)
- `github.com/TRaSH-Guides/Guides` master branch — CF JSON structure, QP JSON structure, file counts, HEAD SHA `1ef7baa523a5f6585a987a4dab6e06bc96994a74` (2026-05-30T07:20:34Z). Verified live via GitHub API + raw file fetch.
- `github.com/recyclarr/config-templates` main branch — `includes.json` full structure, 64 radarr + 34 sonarr template IDs confirmed. HEAD SHA `505c1e565c08d994520c0ca46fc23dee7bf99fd9` (2026-04-30). Verified live.
- `github.com/raydak-labs/configarr` main branch — `src/trash-guide.ts` (cloneTrashRepo: `trashRevision ?? "master"`), `src/recyclarr-importer.ts` (cloneRecyclarrTemplateRepo: `recyclarrRevision ?? "master"`), `src/config.ts` (TRASH source lookup: `trash.has(current.template)`), `src/types/config.types.ts` (InputConfigQualityProfile shape). Verified live.
- `github.com/raydak-labs/configarr` releases — v1.28.0 (2026-05-04, CF groups improvement), v1.22.0 (2026-02-20, TRaSH breaking change support). Verified live.
- `github.com/TRaSH-Guides/Guides` commit `2994a7979d80` — Feb-2026 breaking change (CF group semantics + QP item order inversion). Verified live via GitHub API.
- `tools/arrconf-ui/arrconf_ui/app.py` — existing endpoint pattern, configarr endpoints already in place (no new write path needed for Phase 27).
- `tools/arrconf-ui/web/src/lib/AppSection.svelte` — confirmed `sectionName` prop available for app-context filtering.
- `tools/arrconf-ui/arrconf_ui/locator.py` — confirmed `trash_metadata_dir()` not yet present; needs addition.
- `charts/arr-stack/files/configarr.yml` — confirmed 7 local French CF definitions with `fr-*` id format.

### Secondary (MEDIUM confidence)
- `github.com/raydak-labs/configarr/docs/docs/configuration/config-file.md` — `include` with `source: TRASH` for QP templates (experimental since v1.18.0), `recyclarrRevision` config option documentation. Fetched live but docs may lag source.

### Tertiary (LOW confidence)
- A1/A2/A3 assumptions in Assumptions Log — derived from source code inspection but not integration-tested.

---

## Metadata

**Confidence breakdown:**
- TRaSH JSON structure: HIGH — verified live, multiple files inspected
- Recyclarr includes.json structure: HIGH — verified live
- configarr v1.28.0 resolution behavior: HIGH — source code inspected live
- D-08 risk assessment: HIGH — configarr source code confirms master-branch clone
- Feb-2026 breaking change impact: HIGH — commit + release notes verified
- QP generation YAML shape: MEDIUM — derived from type inspection + live QP JSON, not integration-tested
- Recyclarr template description field absence: HIGH — verified in includes.json and one template file

**Research date:** 2026-05-30
**Valid until:** 2026-07-30 (30 days for stable; TRaSH file counts will drift as new CFs are added, but structure is stable)
