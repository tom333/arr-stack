# Phase 27: TRaSH CF picker + Recyclarr reference + QP picker - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-30
**Phase:** 27-trash-cf-picker-recyclarr-reference
**Areas discussed:** Local-CF vs unknown-ID (SC#4), Insertion semantics, Baked catalog scope + SHA, Recyclarr dropdown UX

---

## Local-CF vs unknown-ID (SC#4)

| Option | Description | Selected |
|--------|-------------|----------|
| Known-custom badge | Resolve against BOTH catalog + local customFormatDefinitions; local-defined = name + "custom" badge; only neither-source IDs warn | ✓ |
| Warning on all non-catalog | Anything not in catalog warns, incl. the 6 French CFs (noisy) | |
| Hide local, warn unknown | Don't surface local IDs in picker; only catalog pickable | |

**User's choice:** Known-custom badge.

| Option | Description | Selected |
|--------|-------------|----------|
| Warn + preserve verbatim | Warn icon+tooltip, keep raw ID, write back untouched | ✓ |
| Warn + offer remove | Same + one-click remove (risk: nuke stale-snapshot ID) | |
| Block save until resolved | Unknown ID = blocking validation error (too aggressive) | |

**User's choice:** Warn + preserve verbatim.
**Notes:** The live configarr.yml's trash_ids are ALL hand-rolled customFormatDefinitions (fr-vff…), not TRaSH hex — this drove the both-sources resolution.

---

## Insertion semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Own entry, all profiles default | Each picked CF = own custom_formats[] entry, assign_scores_to all profiles, no explicit score | ✓ |
| Own entry, operator picks profiles | Second step to choose target profiles (more clicks) | |
| Append to a single shared entry | Add to one catch-all trash_ids list (couples unrelated CFs) | |

**User's choice:** Own entry, all profiles default.

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-select add, per-entry remove | Searchable multi-select; per-entry remove control | ✓ |
| One-at-a-time add, per-entry remove | Single CF per interaction | |
| Replace-set editor | Tick/untick full set, rewrite whole list (reorder risk) | |

**User's choice:** Multi-select add, per-entry remove.

---

## Baked catalog scope + SHA

| Option | Description | Selected |
|--------|-------------|----------|
| Name + trash_id + default score + app | Minimal pickable set, split by app | |
| Add category/group + description | Richer browsing, bigger asset | |
| Also bake quality-profiles catalog | Include TRaSH QP templates too | ✓ |

**User's choice:** Also bake quality-profiles catalog → triggered scope-expansion sub-discussion.

| Option | Description | Selected |
|--------|-------------|----------|
| Bake data now, reference-only UI | QP names read-only, no apply | |
| Bake data only, no UI this phase | Asset only, UI later | |
| Full QP picker (apply to quality_profiles) | Operator picks QP → writes quality_profiles | ✓ |

**User's choice:** Full QP picker — flagged as new capability beyond CFGUI-05.

| Option | Description | Selected |
|--------|-------------|----------|
| Expand Phase 27 (add CFGUI-08) | Fold QP picker into this phase + new requirement + SC#5 | ✓ |
| New phase 28 | Keep 27 small, roadmap dedicated QP phase | |
| Reference-only this phase | Bake + read-only names, defer write | |

**User's choice:** Expand Phase 27 (add CFGUI-08).

| Option | Description | Selected |
|--------|-------------|----------|
| Add-as-new, never touch existing | Append-only; collision → warn + rename | ✓ |
| Add-or-overwrite by name | Overwrite on name match (clobber hazard) | |
| Seed-into-form, operator edits before save | Pre-fill, commit on review | |

**User's choice:** Add-as-new, never touch existing (QP write semantics).

| Option | Description | Selected |
|--------|-------------|----------|
| Match configarr's compat baseline | Pin to configarr v1.28.0 / Recyclarr v7.4.0 compatible SHAs | |
| Latest stable HEAD | Pin to current HEAD (divergence risk stated) | ✓ |
| You decide (planner) | Constraint: configarr-compatible + recorded SHAs | |

**User's choice:** Latest stable HEAD.
**Notes:** Operator accepts that a HEAD-only ID surfaces as a configarr apply error (catalog is name→ID lookup only; configarr resolves at apply). Planner must document mitigation.

---

## Recyclarr dropdown UX

| Option | Description | Selected |
|--------|-------------|----------|
| Per-app section, name + description | Inside each app section, filtered, read-only description panel | ✓ |
| Global reference panel | One collapsible area, both apps | |
| You decide (planner) | Constraint: read-only, name+description, no include: | |

**User's choice:** Per-app section, name + description.

| Option | Description | Selected |
|--------|-------------|----------|
| Copy template name only | Clipboard copy button, no config mutation | ✓ |
| Pure display, no actions | Name+description only | |
| Link to docs | + external docs link | |

**User's choice:** Copy template name only.

---

## Claude's Discretion

- Component names (TrashPicker / RecyclarrTemplatePicker / QP picker), endpoint shapes, picker search/styling, default-score display, badge/chip visuals, diff-preview grouping, FR i18n keys, exact pinned SHAs + manifest format.

## Deferred Ideas

- Recyclarr `include:` insertion (CFGUI-F1 / v1.x).
- Live catalog refresh + trash_id drift detection (CFGUI-F2 / v1.x).
- QP picker overwrite/merge mode (rejected for Phase 27; add-as-new only).
