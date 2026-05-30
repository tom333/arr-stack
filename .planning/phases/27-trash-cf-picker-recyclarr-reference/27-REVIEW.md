---
phase: 27-trash-cf-picker-recyclarr-reference
reviewed: 2026-05-31T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - tools/scripts/fetch-trash-metadata.sh
  - tools/arrconf-ui/arrconf_ui/locator.py
  - tools/arrconf-ui/arrconf_ui/app.py
  - tools/arrconf-ui/tests/test_trash_endpoints.py
  - tools/arrconf-ui/web/src/types.ts
  - tools/arrconf-ui/web/src/api.ts
  - tools/arrconf-ui/web/src/i18n/fr.ts
  - tools/arrconf-ui/web/src/lib/TrashCFPicker.svelte
  - tools/arrconf-ui/web/src/lib/TrashQPPicker.svelte
  - tools/arrconf-ui/web/src/lib/RecyclarrReferencePicker.svelte
  - tools/arrconf-ui/web/src/lib/AppSection.svelte
  - tools/arrconf-ui/web/src/App.svelte
findings:
  critical: 2
  warning: 6
  info: 4
  total: 12
status: issues_found
---

# Phase 27: Code Review Report

**Reviewed:** 2026-05-31
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the Phase 27 TRaSH CF picker / QP picker / Recyclarr reference picker
plus the supporting baked-asset fetch script, FastAPI metadata endpoints, and
the AppSection wiring.

**Verdict against the named guardrails:**

- **ADR-5 boundary (no *arr URL, no runtime GitHub HTTP):** HELD. The three
  `/api/trash/*` handlers read only baked disk assets from `trash_metadata_dir()`;
  no Sonarr/Radarr/Prowlarr URL is constructed, and no GitHub call happens at
  runtime. GitHub HTTP is isolated to `fetch-trash-metadata.sh`, a build-time
  script.
- **Path traversal:** HELD. The `app` query param is enum-gated to
  `("sonarr","radarr")` before any filesystem interpolation, with a regression
  test (Test 6).
- **RecyclarrReferencePicker read-only:** HELD. It only fetches the list and
  copies an id to clipboard; no config write, no `include:` insertion.

However, two **BLOCKER** correctness bugs exist in the CF picker's data model
(it assumes one trash_id per custom_formats entry, which is false against the
shipped `configarr.yml`), and the QP picker emits a hardcoded `min_format_score`
that overwrites TRaSH's real value. Several WARNINGs cover collision-check gaps,
the append-only invariant, and a contradictory test assumption.

## Critical Issues

### CR-01: CF picker assumes one `trash_id` per entry — silently hides and destroys multi-id entries

**File:** `tools/arrconf-ui/web/src/lib/TrashCFPicker.svelte:63,96-108,123`
**Issue:** The picker treats every `custom_formats` entry as having exactly one
trash_id and only ever reads `entry.trash_ids[0]`:

- `confirmAdd` dedup key: `existingCustomFormats.map((e) => e.trash_ids[0])` (line 63)
- existing-chip render: `{@const id = entry.trash_ids[0]}` (line 97)
- already-added check: `e.trash_ids[0] === cf.trash_id` (line 123)
- `removeEntry(idx)` deletes the whole entry.

But the shipped `charts/arr-stack/files/configarr.yml` bundles multiple ids in a
single entry — verbatim at line 272:

```yaml
custom_formats:
  - trash_ids:
      - fr-vff
      - fr-vfi
      - fr-vfq
      - fr-multi
    assign_scores_to: ...
```

Consequences against real data:
1. That 4-id bundle renders as a **single chip labelled only `fr-vff`** — the
   other three ids are invisible to the operator.
2. The dedup/already-added logic only registers `fr-vff` as "present"; if the
   operator searches for `fr-multi` in the catalog it appears addable, producing
   a **duplicate scoring** of the same trash_id across two entries.
3. Clicking the single ✕ on that chip silently deletes **all four** ids at once
   — data loss the operator did not intend.

This is the inverse of the stated "preserve unknown trash_ids verbatim" goal:
known ids in multi-id entries are dropped from view and at risk.

**Fix:** Flatten on read and reconstruct on write, or render every id in an
entry as its own chip. Minimum viable fix — iterate all ids for classification,
dedup, and chip rendering:

```svelte
{#each existingCustomFormats as entry, idx}
  {#each entry.trash_ids as id, idIdx}
    {@const cls = classify(id)}
    <div class="cf-chip">
      <span class="cf-label">{labelFor(id)}</span>
      ...
      <button onclick={() => removeId(idx, idIdx)} ...>✕</button>
    </div>
  {/each}
{/each}
```

and build the dedup set from the flattened union:

```ts
const existingIds = new Set(existingCustomFormats.flatMap((e) => e.trash_ids));
```

### CR-02: QP picker hardcodes `min_format_score: 1` inside `upgrade`, discarding the TRaSH `minFormatScore`

**File:** `tools/arrconf-ui/web/src/lib/TrashQPPicker.svelte:52-60`
**Issue:** `generateQPEntry` writes two conflicting/incorrect score fields:

```ts
upgrade: {
  allowed: qp.upgradeAllowed,
  until_quality: qp.cutoff,
  until_score: qp.cutoffFormatScore ?? 10000,
  min_format_score: 1,              // ← hardcoded, ignores qp.minFormatScore
},
min_format_score: qp.minFormatScore ?? 0,
```

The TRaSH catalog already carries the authoritative `minFormatScore` (surfaced
in `TrashQPEntry`), yet `upgrade.min_format_score` is hardcoded to `1`. This
silently overrides the TRaSH-recommended minimum-acceptable score with `1` for
every inserted profile, which changes acceptance behavior in Sonarr/Radarr (a
release with format score 0 is now rejected where the profile may have intended
0). The picker's own NOTE comment (lines 40-42) flags the field mapping as only
MEDIUM-confidence and "Flag for human verification" — that checkpoint did not
catch the hardcoded literal. Recyclarr's `upgrade` block does not even take a
`min_format_score` key (it lives at profile top level), so this key is likely
both wrong-valued and wrong-placed.

**Fix:** Drop the hardcoded `min_format_score` from the `upgrade` block and rely
on the top-level field already derived from the catalog:

```ts
upgrade: {
  allowed: qp.upgradeAllowed,
  until_quality: qp.cutoff,
  until_score: qp.cutoffFormatScore ?? 10000,
},
min_format_score: qp.minFormatScore ?? 0,
```

Confirm the target schema for the correct `upgrade` shape before shipping; the
MEDIUM-confidence mapping warrants a fixture-based unit test on `generateQPEntry`.

## Warnings

### WR-01: QP collision check is name-only and case/whitespace-sensitive — append-only invariant is fragile

**File:** `tools/arrconf-ui/web/src/lib/TrashQPPicker.svelte:34-38,65-68`
**Issue:** The "never mutate the 3 hand-rolled profiles" guarantee rests entirely
on `hasCollision`, an exact-string `name` comparison. It is correct for exact
duplicates but:
- A name differing only by case (`MULTi.VF` vs `multi.vf`) or trailing space
  passes the gate and creates a second profile Sonarr/Radarr will treat as
  distinct, defeating the operator's intent and polluting the config.
- The insert is genuinely append-only (`[...existingProfiles, newEntry]`), which
  is good, but there is no positive test asserting the hand-rolled profiles are
  byte-identical after an insert.

**Fix:** Normalize before comparing (`collisionName.trim().toLowerCase()` vs each
existing name normalized the same way) and add a regression test that inserts a
profile and asserts the pre-existing entries are untouched.

### WR-02: `descriptionAsText` only strips `<br>` — other HTML/entities render as literal text, and `trash_score_set` typing mismatch

**File:** `tools/arrconf-ui/web/src/lib/TrashQPPicker.svelte:73-76`, `tools/arrconf-ui/web/src/types.ts:90`
**Issue:** Two smaller issues in the QP display path:
1. `descriptionAsText` replaces only `<br>` tags. TRaSH `trash_description`
   fields can contain other markup or HTML entities (`&amp;`, `<b>`); those
   render verbatim. This is *safe* (rendered as text in a `<pre>`, no XSS — the
   T-27-10 concern is correctly avoided), but cosmetically degraded. Acceptable
   as-is; noted for awareness.
2. `TrashQPEntry.trash_score_set` is typed `string`, but the fetch script copies
   `raw["trash_score_set"]` verbatim (`fetch-trash-metadata.sh:126-127`). In the
   TRaSH QP JSON `trash_score_set` is a string, so this is fine — but the script
   does no validation, so a schema drift upstream would surface as a silent type
   mismatch in the UI rather than a build error.

**Fix:** Low priority. If markup quality matters, expand the sanitizer to strip
all tags and decode entities. Otherwise leave the text-render (safe) as-is.

### WR-03: `confirmInsert` button disabled condition is redundant but the name-only insert can produce empty names

**File:** `tools/arrconf-ui/web/src/lib/TrashQPPicker.svelte:65-71,131-138`
**Issue:** `collisionName = nameOverride || (selectedQP?.name ?? '')`. If the
operator clears `nameOverride` the placeholder shows `selectedQP.name`, but the
*value* falls back to `selectedQP.name` correctly. However nothing blocks a
whitespace-only `nameOverride` (e.g. `"   "`) — `confirmInsert` would emit a
profile with `name: "   "`, and since trim() is not applied, `hasCollision`
won't match an existing trimmed name either. A profile with a blank/whitespace
name is invalid downstream.

**Fix:** Trim `collisionName` before use and disable insert when the trimmed
result is empty: `disabled={hasCollision || !selectedQP || !collisionName.trim()}`.

### WR-04: `error = String(e)` surfaces raw error objects to the operator in all three pickers

**File:** `tools/arrconf-ui/web/src/lib/TrashCFPicker.svelte:35`, `TrashQPPicker.svelte:29`, `RecyclarrReferencePicker.svelte:29`
**Issue:** On fetch failure each picker sets `error = String(e)` and renders it
in a `role="alert"` div. For an `ApiError` this yields the full
`API 404: Catalog not found at /abs/path... — run tools/scripts/...` string,
leaking an absolute server filesystem path into the UI. Even though this is a
LAN-trusted tool, surfacing the absolute repo path is noise and a minor info
disclosure. It is also not actionable to a non-developer operator.

**Fix:** Map known statuses to friendly messages (e.g. 404 → "Catalogue TRaSH
absent — exécutez fetch-trash-metadata.sh") and log the raw error to console
rather than rendering it.

### WR-05: `copyId` has no fallback when `navigator.clipboard` is unavailable (HTTP / non-secure context)

**File:** `tools/arrconf-ui/web/src/lib/RecyclarrReferencePicker.svelte:32-36`
**Issue:** `navigator.clipboard` is `undefined` outside secure contexts
(plain `http://` on a non-localhost LAN host — exactly the deployment model
described in CLAUDE.md as "LAN-trusted"). `await navigator.clipboard.writeText`
will throw `TypeError: Cannot read properties of undefined`, the promise
rejects, and because `copyId` is an unawaited `onclick` handler the rejection is
unhandled and the "✓ Copié" feedback never shows — the copy silently fails.

**Fix:** Guard and provide a fallback / error state:

```ts
async function copyId(id: string) {
  try {
    if (!navigator.clipboard) throw new Error('clipboard unavailable');
    await navigator.clipboard.writeText(id);
    copied = true;
    setTimeout(() => { copied = false; }, 1500);
  } catch {
    error = 'Copie impossible — copiez le nom manuellement.';
  }
}
```

### WR-06: `fetch-trash-metadata.sh` fetches the git tree twice and discards the first (shell) fetch

**File:** `tools/scripts/fetch-trash-metadata.sh:42-54,68-80,137-140`
**Issue:** The shell layer fetches the TRaSH git tree (lines 42-45) and the
Recyclarr includes.json (lines 47-50) into `TREE_JSON` / `RECYCLARR_JSON`, then
the embedded Python re-fetches **both** URLs via urllib (lines 79-80, 139-140).
`TREE_JSON` and `RECYCLARR_JSON` are never read. This means:
- Two network round-trips per resource (wasteful, doubles GitHub API rate-limit
  consumption — relevant since the unauthenticated git/trees endpoint is rate
  limited to 60 req/h).
- A TOCTOU window: if the upstream ref moves between the shell fetch and the
  Python fetch the two could disagree (mitigated by pinned SHAs, but the
  duplication is still dead work). The comment at line 68 acknowledges "Read the
  shell-fetched data via stdin is not possible here" — but the cleaner fix is to
  drop the shell fetches entirely since Python re-fetches anyway.

**Fix:** Either remove the shell `curl` fetches (lines 42-50) and rely solely on
Python, or pass the already-fetched JSON to Python via stdin/temp file and drop
the urllib re-fetch. The script also has no GitHub auth header, so a developer
running it twice in an hour can hit the 60 req/h limit given ~470 CF + ~55 QP
per-file fetches.

## Info

### IN-01: Test 4 asserts `"description" not in entry` but the type and data carry `template`, not `description` — assertion is trivially true and misleading

**File:** `tools/arrconf-ui/tests/test_trash_endpoints.py:84-86`
**Issue:** The recyclarr entries are `{id, template}` (confirmed in
`recyclarr-radarr.json` and `RecyclarrTemplateEntry`). The test asserts
`"description" not in entry`, which can never fail because nothing ever produces
a `description` key. The intent (per the docstring "id, no description") was
probably to assert `"template" in entry`. As written the test gives false
confidence.

**Fix:** Assert the real contract: `assert "template" in entry`.

### IN-02: `fetch-trash-metadata.sh` `--dry-run` claims "7 files + manifest" but writes 6 catalogs + 1 manifest

**File:** `tools/scripts/fetch-trash-metadata.sh:36`, lines 153-174
**Issue:** Dry-run prints "would write 7 files + manifest" but the write path
emits 6 catalog files (sonarr/radarr × cf/qp + recyclarr × 2) plus 1 manifest =
7 total. The "7 files + manifest" wording double-counts and will confuse anyone
reconciling output. The README/manifest counts (`manifest.json`) are correct.

**Fix:** Reword to "would write 6 catalogs + manifest to ...".

### IN-03: `write_json` `len(data)` log cast comment masks a real edge — manifest logs "object" correctly but the type:ignore hides intent

**File:** `tools/scripts/fetch-trash-metadata.sh:151`
**Issue:** The `# type: ignore[arg-type]` on the f-string `len(data)` call is
applied even though the code already guards with `isinstance(data, list)`. The
ignore is unnecessary noise and suppresses a category of error that the guard
already handles. Minor.

**Fix:** Remove the `# type: ignore` — the conditional already narrows the type.

### IN-04: AppSection picker `localDefinitions` plumbing assumes `customFormatDefinitions[].trash_id`/`name` shape without validation

**File:** `tools/arrconf-ui/web/src/App.svelte:196`, `tools/arrconf-ui/web/src/lib/AppSection.svelte:23`
**Issue:** App.svelte casts
`configState.customFormatDefinitions as { trash_id: string; name: string }[]`.
configarr's `customFormatDefinitions` entries are richer (they contain a
`trash_id`, `name`, and `specifications`), so the cast is a lossy narrowing that
happens to expose the two fields the picker needs. It works, but a malformed
local definition (missing `trash_id`) would make `classify()` mis-label a local
CF as `unknown`. Low impact (display-only badge), noted for awareness.

**Fix:** None required for correctness; consider a runtime filter
`.filter(d => d?.trash_id)` when building `localDefinitions` to harden the badge
classification.

---

_Reviewed: 2026-05-31_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
