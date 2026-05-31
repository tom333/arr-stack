---
phase: 28-generate-foundation
plan: "06"
subsystem: docs
tags: [adr, intention-layer, boundary, documentation]
dependency_graph:
  requires: []
  provides: [ADR-10]
  affects: [spec.md, .planning/PROJECT.md]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - spec.md
    - .planning/PROJECT.md
decisions:
  - "ADR-10: couche d'intention au-dessus d'arrconf+configarr; absorber vs déployer-seulement boundary; ADR-5 extension (configarr seul appliqueur TRaSH)"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-31T02:50:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 28 Plan 06: ADR-10 — Intention Layer Boundary Summary

ADR-10 written in spec.md §11 and PROJECT.md decisions table — formalizes the intention layer above arrconf+configarr, the absorber/déployer-seulement boundary, and the ADR-5 extension (configarr remains sole TRaSH applier).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write ADR-10 block in spec.md §11 | 1700d28 | spec.md |
| 2 | Add ADR-10 entry to PROJECT.md decisions table | a7ff5ff | .planning/PROJECT.md |

## What Was Done

### Task 1 — ADR-10 in spec.md §11

Inserted ADR-10 block immediately after the ADR-9 block (line 954) and before `## 12. Références` (line 970 post-insert). The block covers all three mandatory D-12 points:

- **(a) Layer:** intention layer sits above both arrconf and configarr. Flow: `intent.yml` → `arrconf generate` (pure fn) → committed verbose configs → `arrconf apply` / configarr (unchanged). Generalizes the `categories[]` pattern.
- **(b) Absorber/déployer boundary:** absorber = tools with declarative file/API config (cross-seed, qbit_manage) → config generated from `intent.yml`. Déployer-seulement = DB/UI-only tools (autobrr, cleanuparr) → Helm alias only, no intention-layer config.
- **(c) ADR-5 extension:** configarr remains sole TRaSH applier. Intention layer never touches `quality_profiles` / `custom_formats` / `quality_definitions` / `media_naming`. Hard boundary ADR-5 unchanged.

Also documents G1 model (generate locally + commit) with G2/G3 rejections, and consequences (Git diff preserved, generate/apply decoupled, CI idempotence gate INTENT-03).

### Task 2 — PROJECT.md decisions table

Added ADR-10 row after ADR-9 with summary covering: absorber/déployer boundary, ADR-5 extension, cross-reference to spec.md §11 ADR-10.

## Decisions Made

- ADR-10 authored in spec.md §11 as the canonical INTENT-04 decision record
- ADR-10 extends (not replaces) ADR-5: same hard boundary, intention layer sits above both tools
- G1 model (local generate + commit) is the architectural choice over G2 (in-cluster) and G3 (auto-commit)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — documentation-only plan, no code stubs.

## Threat Flags

No new threat surface. Documentation-only change; no code, no inputs, no execution surface.

## Self-Check: PASSED

- `spec.md` contains `### ADR-10 — Couche d'intention` at line 956 (before `## 12` at line 970) ✓
- `spec.md` contains `seul appliqueur TRaSH` (ADR-5 extension point) ✓
- `spec.md` references `ADR-5` near ADR-10 block ✓
- `spec.md` contains `quality_profiles` in ADR-10 block ✓
- `.planning/PROJECT.md` contains `ADR-10` and `absorber` ✓
- Commits 1700d28 and a7ff5ff exist ✓
- No `tools/arrconf/**` files modified → no arrconf.image.tag bump required ✓
