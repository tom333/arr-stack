# Phase 12: Categories deprecation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `12-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** 12-categories-deprecation
**Areas discussed:** Pydantic / reconciler depth, Test cleanup scope, Operator migration doc shape, Rollout / verification sequencing

---

## Pydantic / reconciler depth

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic cleanup | Remove `items` from 6 Section models. Reconciler takes generator output as parameter. Schema regen reflects simpler shape (SC#2 dispositive). | ✓ |
| Minimal (keep items=[]) | Models unchanged. `items=[]` dead fields survive. Smallest diff but SC#2 "simplified shape" is questionable. | |
| model_validator materialization | RootConfig populates instance.tags.items at parse time. Reconcilers see populated object, no signature change. Magical YAML→config boundary, makes `arrconf dump` confusing. | |

**User's choice:** Pydantic cleanup.

### Sub-question A: Prune field

| Option | Description | Selected |
|--------|-------------|----------|
| Keep `prune` on each Section | Operator controls deletion. YAML: `sonarr.main.tags: { prune: false }` with no items. | ✓ |
| Drop `prune` too | Collapse Sections into bare bools or remove entirely. Max simplification, loses operator override. | |
| Keep `prune` + default it false so Section can be omitted | Optional with default. Cleanest YAML. | |

**User's choice:** Keep prune.

### Sub-question B: Reconciler signature

| Option | Description | Selected |
|--------|-------------|----------|
| Pass the *Derived dataclass directly | `reconcile_sonarr(client, instance, derived: SonarrDerived)`. Same for radarr. Single arg per reconciler. | ✓ |
| Flatten to keyword args per resource | Explicit per-resource named kwargs. More verbose but less coupling. | |
| Mutate instance.* attributes in __main__.py | Keep signature, add new pydantic fields (`tags_derived`). Bridges approaches but adds dead fields. | |

**User's choice:** Pass *Derived dataclass directly.

**Notes:** This decision sets the architectural shape for Phase 12. All 24 `merge_with_manual` callsites collapse into 6 generator calls; reconcilers now declare what they consume in their signature.

---

## Test cleanup scope

| Option | Description | Selected |
|--------|-------------|----------|
| Broad | Delete test_merge_with_manual.py entire, delete all *_manual_override_* / *_per_resource_override_* variants, delete test_sweep_manual_override_path, rename *_wiring_empty_manual → *_wiring (~14 deleted, ~8 renamed). | ✓ |
| Minimal per ROADMAP letter | Only delete test_sweep_manual_override_path + rename test_sweep_categories_derived_path → test_sweep. Leaves broken test_merge_with_manual.py behind. | |
| Broad + tests/generators/ subdir reorg | Broad cleanup + reorganize categories tests into a subdirectory. Bigger structural change. | |

**User's choice:** Broad.

### Sub-question: Fixtures

| Option | Description | Selected |
|--------|-------------|----------|
| Delete fixtures that became unreachable | Grep audit each fixture post-deletion; remove unreferenced. | ✓ |
| Keep all fixtures — cheap | Defer fixture cleanup. | |
| Audit + document each survivor | A + docstring each survivor. Adds doc cost. | |

**User's choice:** Delete unreachable.

**Notes:** Discussion confirmed the rename pattern (`*_wiring_empty_manual` → `*_wiring`) is the right hygiene move once manual is dead. `production_cfg` fixture stays — it's used by the surviving `test_sweep` and generator-pure tests.

---

## Operator migration doc shape

| Option | Description | Selected |
|--------|-------------|----------|
| CLAUDE.md text-only | New `## v0.3.0 → v0.4.0 deprecation` section: what to delete, why, exact error if forgotten, how to fix. Operator = user reads CLAUDE.md before pulling. | ✓ |
| CLAUDE.md + helper script | + `tools/scripts/migrate-arrconf-v04.sh` yq-based stripper. Belt-and-suspenders for a one-shot run. | |
| CLAUDE.md + pydantic deprecation-warning cycle | One-cycle warning before extra="forbid" enforces removal. Safer but doubles release work. | |

**User's choice:** CLAUDE.md text-only.

### Sub-question: SC#5 dispositive evidence location

| Option | Description | Selected |
|--------|-------------|----------|
| Commit pre/post snapshots to snapshots/before-phase-12-* and snapshots/after-phase-12-* | Phase 9/10 precedent. Forensic baseline preserved. | ✓ |
| HUMAN-UAT.md narrative only, no commit | Cheaper but no forensic trail. | |
| Both — snapshots + HUMAN-UAT narrative | Belt-and-suspenders. | |

**User's choice:** Commit pre/post snapshots.

**Notes:** Homelab single-tenant context: no external operator audience means no need for helper script or warning cycle. `extra="forbid"` enforces the cleanup naturally via clear ValidationError if forgotten.

---

## Rollout / verification sequencing

| Option | Description | Selected |
|--------|-------------|----------|
| Single atomic PR | All code/YAML/schema/test/doc changes + pre-snapshot in one PR. Image co-bump 0.6.7→0.7.0. After-snapshot via PR2 (evidence-only). | ✓ |
| Two functional PRs | PR1 deletes YAML only (with merge_with_manual still in place). PR2 removes the code. Two cluster gates, two release cycles. | |
| Single PR + pre-merge live-cluster dry-run as HUMAN-UAT | Same as A but operator runs dry-run from PR branch before merging. | |

**User's choice:** Single atomic PR.

### Sub-question: SC#3 vs SC#5 relationship

| Option | Description | Selected |
|--------|-------------|----------|
| SC#3 = unit dispositive, SC#5 = cluster dispositive, BOTH required | Two layers of evidence. Either failing blocks the phase. | ✓ |
| SC#3 sufficient, SC#5 informational | If unit sweep passes, math implies cluster diff is stable. | |
| SC#5 primary, SC#3 cheap iteration | Cluster dry-run is the only thing that matters. | |

**User's choice:** Both required.

**Notes:** The two-PR variant was explicitly rejected as adding release cycles for no functional reason. Cluster post-merge dry-run + after-snapshot via PR2 keeps the evidence loop tight without inflating the release cadence.

---

## Claude's Discretion

- Exact pre-commit / CI step shape for the schema drift check (mirror byte-equivalence-diff.sh pattern if not already present)
- Survival of `_shared.py` (depends on whether `_resolve_anime_tag_labels` is the only thing left — keep file unless empty)
- Wording of CLAUDE.md deprecation section (French/English mix per existing style)
- Test file restructure depth — flat structure preferred (user rejected `tests/generators/` subdir)

## Deferred Ideas

- Refactor apply/diff duplication in `__main__.py` into a shared inner helper — future polish phase
- `tests/generators/` subdirectory reorg — revisit if more generator types appear (e.g., future Bazarr addition)
- Pydantic deprecation-warning cycle — out of scope; `extra="forbid"` is the enforcement
- Helper migration script `tools/scripts/migrate-arrconf-v04.sh` — out of scope; user = operator
