---
phase: 26-configarr-in-ui-frontend
reviewed: 2026-05-30T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - tools/arrconf-ui/web/src/App.svelte
  - tools/arrconf-ui/web/src/api.ts
  - tools/arrconf-ui/web/src/constants.ts
  - tools/arrconf-ui/web/src/i18n/fr.ts
  - tools/arrconf-ui/web/src/lib/FieldInput.svelte
  - tools/arrconf-ui/web/src/lib/HeaderBar.svelte
  - tools/arrconf-ui/web/src/types.ts
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 26: Code Review Report

**Reviewed:** 2026-05-30
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 26 wires `configarr.yml` editing into the existing schema-driven Svelte 5
frontend: a tab selector, an active-config-parametrized load/diff/save pipeline,
readOnly field rendering, and an unsaved-switch confirm gate. The ADR-5 boundary
holds (no *arr API URL is constructed anywhere in the frontend — all traffic goes
through `/api/*` and `/api/configarr/*`), and the `{@html}` rendering in
`SectionDoc` is safe (HTML-escaped before markdown substitution, fed only static
FR literals).

However, the central SC#2 / D-02 guarantee — that `media_naming` and
`quality_definition` render **read-only** — is broken by an interaction between
`effectiveNode()`'s `anyOf` narrowing and where the `readOnly` marker sits in the
generated JSON Schema. Those two subtrees render fully editable, defeating the
phase's primary read-only requirement. There are no frontend unit tests, so this
regressed silently past `npm run check` / `typecheck` / `build` and the human
checkpoint (which would have to manually attempt to edit a deeply-nested naming
field to notice).

## Critical Issues

### CR-01: `media_naming` and `quality_definition` are NOT read-only — `effectiveNode()` strips the `readOnly` marker via `anyOf` narrowing

**File:** `tools/arrconf-ui/web/src/lib/FieldInput.svelte:46,87`
**Issue:**
`isReadOnly` is derived from the **resolved** node only:

```js
const effective = $derived(effectiveNode(schema, root));
const isReadOnly = $derived(readOnly || (effective as { readOnly?: boolean }).readOnly === true);
```

In the generated schema (`schemas/configarr-schema.json`), `media_naming` and
`quality_definition` carry `readOnly: true` on an **`anyOf` wrapper node**:

```json
"media_naming": {
  "anyOf": [ { "$ref": "#/$defs/MediaNaming" }, { "type": "null" } ],
  "default": null,
  "readOnly": true
}
```

`effectiveNode()` runs `pickAnyOf()` first, which **discards the wrapper** and
returns the inner `$ref` branch, then resolves it to the `MediaNaming` /
`QualityDefinition` def. Neither the inner branch nor the resolved def carries
`readOnly`. So for these two fields `effective.readOnly` is `undefined`, the
`readOnly` prop arriving from `AppSection` is `false` (AppSection does not pass
`readOnly`), and `isReadOnly` evaluates to `false`.

Result: the entire `media_naming` and `quality_definition` subtrees render as
**editable** widgets with no lock badge — a direct violation of SC#2 and D-02.
`api_key` is unaffected because it is a plain `{ readOnly: true, type: "string" }`
node with no `anyOf`, so `effectiveNode()` returns it unchanged. This asymmetry
is exactly why a manual checkpoint that only spot-checked `api_key` would pass.

(The SUMMARY claim "This makes `media_naming` and `quality_definition` object
subtrees render fully disabled at all leaf levels" is incorrect — the prop only
propagates downward *once a parent is already read-only*, which never happens
here because the marker is lost at the top of the subtree.)

**Fix:** Check the raw `schema` node for the marker too, before `anyOf`
narrowing discards it:

```js
const isReadOnly = $derived(
  readOnly
    || schema.readOnly === true
    || (effective as { readOnly?: boolean }).readOnly === true,
);
```

`schema.readOnly` is already typed (`JsonSchemaNode.readOnly?: boolean` in
`types.ts`), so no cast is needed for that term. Add a frontend unit/render test
that asserts `media_naming` and `quality_definition` leaf inputs receive
`disabled` (none exist today — see WR-04).

## Warnings

### WR-01: Diff-preview failure silently degrades to an empty diff, hiding real save risk

**File:** `tools/arrconf-ui/web/src/App.svelte:80-85`
**Issue:** When `postDiff` / `postConfigarrDiff` throws (backend down, 5xx,
validation error), `openDiffPanel` swallows the error to `console.error` and
opens `DiffPanel` with `pendingDiff = {}`. The operator then sees an empty diff
("no changes") and clicks confirm, which proceeds to `PUT` the full config. For
a config-file editor whose entire value proposition is "preview before you write
the file", presenting a blank diff on backend error is misleading and can lead to
an unintended overwrite of `configarr.yml` / `arrconf.yml`.
**Fix:** Surface the diff failure to the operator instead of fabricating an empty
diff — e.g., set `loadError`/a banner and do **not** open the panel, or open it in
an explicit "diff unavailable — proceed at your own risk" state. Do not present an
empty object as "no changes".

### WR-02: `confirmSave` error path leaves the user without feedback on non-validation failures

**File:** `tools/arrconf-ui/web/src/App.svelte:101-108`
**Issue:** On save failure, only pydantic-style errors (`ApiError` with array
`detail`) populate `validationErrors` / the banner. Any other failure (network
error, 500, plain-string `detail`) sets `saveStatus = 'error'` and logs to the
console only — no visible UI signal. The save button re-enables and the operator
has no indication the write failed; they may assume the file was written. The
`saveStatus = 'error'` state is not rendered anywhere visible.
**Fix:** Render a non-validation error message (reuse `loadError`-style banner or a
toast) when `saveStatus === 'error'` and `validationErrors` is empty, including the
`ApiError.message` / string detail.

### WR-03: Confirm-dialog `pendingSwitch` guard makes "Changer" silently no-op on a lost edge

**File:** `tools/arrconf-ui/web/src/App.svelte:143`
**Issue:** The confirm button calls `() => pendingSwitch && void doSwitch(pendingSwitch)`.
If `pendingSwitch` is ever `null` when the dialog is open, the click is a silent
no-op and the modal stays up with no feedback. More importantly, the dialog
provides no keyboard affordances: `role="dialog" aria-modal="true"` is set but
there is no focus trap, no `Escape`-to-cancel, and no autofocus — so an operator
who hits Escape or Enter expecting the native-`confirm()` behavior (the rejected
alternative in D-04) gets nothing. For a destructive "your unsaved edits will be
lost" gate this is a robustness gap.
**Fix:** Wire `onkeydown` on the overlay to cancel on `Escape` and confirm on
`Enter`, autofocus the cancel button, and trap focus within the dialog. The
`pendingSwitch` null-guard can stay but should not be the only path — the dialog
should never be openable with `pendingSwitch === null` (it isn't today, but the
guard masks that invariant rather than asserting it).

### WR-04: No frontend tests cover any Phase 26 behavior

**File:** `tools/arrconf-ui/web/` (no `*.test.ts` / `*.spec.ts` present)
**Issue:** The phase adds readOnly threading, an `additionalProperties` section
filter, an active-config dispatch, and a confirm gate — all pure, testable logic —
yet there is zero frontend test coverage. `npm run check` (svelte-check),
`typecheck`, and `build` are type/compile gates only; none of them can catch
CR-01 (a runtime reactivity bug that type-checks cleanly). The project CLAUDE.md
mandates ≥70% coverage on reconcilers but the UI has no equivalent gate, so
correctness rests entirely on a one-time human checkpoint.
**Fix:** Add at least: (a) a render test asserting `disabled` on `api_key`,
`media_naming.*`, and `quality_definition.*` leaves (guards CR-01); (b) a unit
test for the `additionalProperties != null` section filter against
`configarr-schema.json` (asserts `sonarr`+`radarr` selected, scalars excluded);
(c) a test for the `diffCount > 0` switch gate. This is the regression net CR-01
proves is missing.

## Info

### IN-01: `additionalProperties` section filter is fragile to schema shape changes

**File:** `tools/arrconf-ui/web/src/App.svelte:182-184`
**Issue:** The configarr section list is computed as
`Object.keys(schema.properties).filter(k => properties[k].additionalProperties != null)`.
This works today because only `sonarr`/`radarr` are maps and the scalar keys
(`trashGuideUrl`, `recyclarrConfigUrl`, `customFormatDefinitions`) lack
`additionalProperties`. But the predicate is structural coincidence, not intent:
if a future configarr field is modeled as an object with `additionalProperties`,
it would silently appear as an editable section, and `customFormatDefinitions`
(an array the operator may well want to see) is silently dropped. The inline
double-cast `(schema!.properties[k] as { additionalProperties?: unknown })`
inside the template also duplicates work the typed `JsonSchemaNode` already
supports.
**Fix:** Prefer an explicit allowlist constant (mirroring `APP_SECTIONS`) or a
helper that documents "instance-map sections only", and drop the inline cast by
reading the typed `additionalProperties` field. Low priority — current behavior
is correct for the shipped schema.

### IN-02: `diffCount` is a 0/1 boolean masquerading as a count

**File:** `tools/arrconf-ui/web/src/App.svelte:37-41`
**Issue:** `diffCount` returns `0` or `1` (`stringify(a) === stringify(b) ? 0 : 1`),
but `HeaderBar.svelte:38` renders it as a count: `{diffCount} modification(s)`.
The chip therefore always reads "1 modification en attente" regardless of how
many fields changed. Functionally fine for the dirty-gate (D-04), but the label
is misleading. (Pre-existing pattern, surfaced here because the chip is now shared
across two configs.)
**Fix:** Either rename to `isDirty`/render a generic "modifications non
enregistrées" label, or compute a real changed-field count if the number matters.

### IN-03: `addArrayItem` blank-object builder ignores `anyOf`-typed fields

**File:** `tools/arrconf-ui/web/src/lib/FieldInput.svelte:127-135`
**Issue:** When adding a new array entry (e.g., a new `quality_profiles[]` or
`assign_scores_to[]` row), the blank object is seeded from `sub.type`. But most
configarr leaf fields are `anyOf: [{type}, {null}]` with no top-level `type`
(see `QualityProfile.*`, `AssignScoresTo.score`). For those, none of the
`type === 'array'|'boolean'|'integer'` branches match and the field defaults to
`''` (empty string) — which is the wrong shape for an integer/boolean field and
may produce a pydantic validation error on save until the operator edits it.
**Fix:** Run the sub-schema through `effectiveNode`/`pickAnyOf` before switching
on `.type` so `anyOf`-wrapped optionals seed with the correct blank
(`null`/`false`/`[]`). Low impact (only affects newly-added rows, and the operator
typically fills them in before saving), hence Info.

---

_Reviewed: 2026-05-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
