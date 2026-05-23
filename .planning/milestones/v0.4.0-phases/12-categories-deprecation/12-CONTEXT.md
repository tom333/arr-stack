# Phase 12: Categories deprecation - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Rip out the v0.2.0 transition layer entirely. Concretely:

1. Delete `tools/arrconf/arrconf/reconcilers/_shared.py::merge_with_manual()` and its 24 callsites in `tools/arrconf/arrconf/__main__.py` (12 in `apply`, 12 in `diff`).
2. Delete the flat `items:` lists from `charts/arr-stack/files/arrconf.yml` for the 12 generator-derived resources: sonarr.main.{tags,root_folders,download_clients,remote_path_mappings}.items, radarr.main.{tags,root_folders,download_clients,remote_path_mappings}.items, qbittorrent.main.categories.items, seerr.main.sonarr_service.animeTags, jellyfin.main.libraries.items.
3. Simplify the pydantic Section models so the YAML and the schema reflect the simpler shape.
4. Delete the manual-path tests (helper unit tests + per-app override variants + sweep override variant).
5. Document the one-time YAML cleanup in CLAUDE.md.
6. Prove no behaviour drift on the live cluster via pre/post `arrconf apply --dry-run` snapshots committed to `snapshots/`.

After this phase, `arrconf.generators.categories` is the sole source of truth for the 12 generated resources. The toggle is gone. Operator-controlled knobs (`prune: bool`) survive on Section models.

**Categories model itself is unchanged.** This phase only removes the transition layer added in v0.3.0 — it does not modify `RootConfig.categories`, the generator functions, or the reconcilers' behaviour against generated input.

</domain>

<decisions>
## Implementation Decisions

### Pydantic / reconciler depth

- **D-01:** Remove the `items: list[...]` field from each generator-fed Section model. Affected models in `tools/arrconf/arrconf/config.py`: `TagsSection`, `RootFoldersSection`, `DownloadClientsSection`, `RemotePathMappingsSection`, `CategoriesSection` (qBittorrent), and the equivalent JellyfinLibrariesSection. Keep the Section classes — they still carry `prune: bool`.
- **D-02:** Keep `prune: bool` on every Section model. It's the only operator-tunable knob left and controls deletion semantics for cluster-side resources that aren't in the generator output. YAML stays e.g. `sonarr.main.tags: { prune: false }` with no `items:` underneath.
- **D-03:** Reconciler entry points take the generator output as a single dataclass parameter, not as scattered keyword args. Signatures:
  - `reconcile_sonarr(client, instance, derived: SonarrDerived, *, dry_run)`
  - `reconcile_radarr(client, instance, derived: RadarrDerived, *, dry_run)`
  - `reconcile_qbittorrent(client, instance, categories: list[QbitCategory], *, dry_run)`
  - `reconcile_jellyfin(client, instance, libraries: list[JellyfinLibrary], *, dry_run)`
  - Seerr animeTag labels stay resolved in `__main__.py` post-Sonarr-reconcile (resolution chain unchanged from Phase 10); the resolved `list[int]` is passed to `reconcile_seerr` directly.
- **D-04:** `__main__.py` no longer assigns to `instance.tags.items` or any other `*.items` attribute. It calls the generator, then passes the *Derived dataclass into the reconciler. The 24 `merge_with_manual` callsites collapse to 6 generator calls (one per app, shared between the apply and diff code paths via the existing function structure).
- **D-05:** Schema regen via `arrconf schema-gen --output schemas/arrconf-schema.json` is part of the PR. The committed schema MUST reflect the post-deprecation shape (no `items:` fields on the 6 Section models). CI's `tests.yml` lint step that compares the committed schema to a fresh regen blocks merge if drift.

### Test cleanup scope (broad)

- **D-06:** Delete `tools/arrconf/tests/test_merge_with_manual.py` entirely (6 tests testing the removed function).
- **D-07:** Delete the manual-override / per-resource-override test variants across the 5 per-app test files:
  - `test_sonarr_categories.py`: `test_sonarr_per_resource_override_tags_only`, `test_sonarr_per_resource_override_rpm_only`
  - `test_radarr_categories.py`: `test_radarr_per_resource_override_tags_only`
  - `test_qbittorrent_categories.py`: `test_manual_override_wins`
  - `test_jellyfin_categories.py`: `test_jellyfin_manual_override_wins`
  - `test_seerr_animetags.py`: `test_animetags_merge_manual_wins`, `test_animetags_merge_empty_manual_uses_generated`
- **D-08:** Delete `test_phase10_idempotence_sweep.py::test_sweep_manual_override_path`. Rename `test_sweep_categories_derived_path` → `test_sweep` (sole path) and update its docstring to reflect SC#3 dispositive role for Phase 12.
- **D-09:** Rename all `*_wiring_empty_manual` → `*_wiring` across the per-app categories test files (~8 renames). The "empty manual" qualifier is meaningless once manual is dead.
- **D-10:** After deleting the manual-path tests, do a `grep -r '<fixture-name>' tools/arrconf/tests/` audit on each fixture defined in `conftest.py` or inline. Delete any fixture that has zero live references. The `production_cfg` fixture stays — it's used by `test_sweep` and several generator-pure tests.

### Operator migration documentation

- **D-11:** CLAUDE.md gets a new section: `## v0.3.0 → v0.4.0 deprecation`. Contents:
  1. Why the change (transition layer ripped out; generators are sole source).
  2. Verbatim list of YAML sections being deleted from `charts/arr-stack/files/arrconf.yml`, with the line ranges from the pre-deprecation file as a forensic anchor.
  3. The exact pydantic `ValidationError` text an external operator (or the user editing an old fork) would see if they kept the flat sections under `extra="forbid"` (paste an example error from a unit test that exercises the failure path).
  4. The one-shot fix command (`git diff` instructions — operator is single-tenant, no automation needed).
- **D-12:** No helper script. The single operator (= user) edits arrconf.yml in the same PR that ships the code changes. External operators (none exist for homelab) would read CLAUDE.md and self-migrate.
- **D-13:** Pydantic `extra="forbid"` is the enforcement mechanism. No deprecation-warning cycle, no soft fallback. If the YAML still has `tags.items` after the upgrade, the next `arrconf apply` exits 2 with a clear ValidationError pointing at the dead field.
- **D-14:** SC#5 dispositive evidence lives as committed snapshots:
  - `snapshots/before-phase-12-2026-MM-DD/` — pre-merge `arrconf apply --dry-run` capture (per-app plan_action lines, secrets redacted via existing snapshot.sh redaction).
  - `snapshots/after-phase-12-2026-MM-DD/` — post-merge equivalent.
  - `diff -r before/ after/` MUST show only structural differences (e.g., removed log lines for the `merge_decision` event) and zero `plan_action` differences. The diff text is summarized in the phase VERIFICATION.md or HUMAN-UAT.md.

### Rollout / verification sequencing

- **D-15:** Single atomic PR ships everything: code (merge_with_manual removal + pydantic cleanup + reconciler signature refactor), YAML (flat-section deletion), schema (regen + commit), tests (broad cleanup), docs (CLAUDE.md deprecation section), and the pre-merge snapshot (`snapshots/before-phase-12-*`). Image co-bump 0.6.7 → 0.7.0 (minor — first internal-API change of v0.4.0; D-05 chart-pin co-bump pattern applies).
- **D-16:** After merge, the operator runs `arrconf apply --dry-run` against the live cluster, captures `snapshots/after-phase-12-*`, and opens a small PR2 that adds the after-snapshot + the diff confirmation (no code, no chart, no values changes). PR2 is evidence-only and not a release cycle; image stays on 0.7.0.
- **D-17:** SC#3 (`test_sweep` unit-level sweep against production_cfg) and SC#5 (live cluster dry-run diff) are BOTH required for VERIFICATION PASSED. SC#3 is the cheap iteration loop in CI; SC#5 is the dispositive cluster confirmation. Either failing blocks the phase from closing.
- **D-18:** No two-PR functional split (PR1 YAML-only / PR2 code-only). The user explicitly rejected this — homelab single-tenant doesn't need a halfway state, and doubling the release cycles for no functional reason adds churn.

### Claude's Discretion

- The exact pre-commit hook / CI step that catches schema drift if `arrconf schema-gen` isn't re-run. If `tests.yml` doesn't already cover this, the planner can add a `schemas/arrconf-schema.json` byte-equivalence check (mirror of the `byte-equivalence-diff.sh` pattern in `tools/scripts/`).
- The structural log lines that `merge_with_manual` was emitting (`merge_decision` events) — silently disappear from cluster logs. No log-shape contract to preserve since the events were internal.
- Whether `_shared.py` keeps its file existence after `merge_with_manual` is deleted. It still hosts `_resolve_anime_tag_labels` (the Seerr labels-to-ids helper). Keep the file unless it would be empty.
- Test directory restructure (`tests/generators/`) — the user picked the broad-flat option, not the restructure. Planner does NOT move files into subdirectories.
- Exact wording of the CLAUDE.md deprecation section — writing-with-codebase voice (French/English mix per existing CLAUDE.md style).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 12 section: goal + 5 success criteria
- `.planning/REQUIREMENTS.md` — `REQ-categories-deprecation` (single REQ for this phase)

### Source code to modify
- `tools/arrconf/arrconf/reconcilers/_shared.py` — contains `merge_with_manual()` (to delete) and `_resolve_anime_tag_labels()` (to keep)
- `tools/arrconf/arrconf/__main__.py` — 24 callsites of `merge_with_manual` (apply + diff branches)
- `tools/arrconf/arrconf/config.py` — pydantic Section models to simplify
- `tools/arrconf/arrconf/generators/categories.py` — pure generator functions (unchanged in this phase)
- `tools/arrconf/arrconf/reconcilers/{sonarr,radarr,qbittorrent,jellyfin,seerr}.py` — reconciler entry points to refactor (signature change to accept *Derived dataclass)
- `charts/arr-stack/files/arrconf.yml` — YAML flat sections to delete
- `charts/arr-stack/values.yaml` — `arrconf.image.tag` co-bump 0.6.7 → 0.7.0
- `schemas/arrconf-schema.json` — regenerated by `arrconf schema-gen`

### Tests to modify
- `tools/arrconf/tests/test_merge_with_manual.py` — DELETE entire file
- `tools/arrconf/tests/test_phase10_idempotence_sweep.py` — delete one test, rename another
- `tools/arrconf/tests/test_sonarr_categories.py` — delete 2 override tests, rename 4 wiring tests
- `tools/arrconf/tests/test_radarr_categories.py` — delete 1 override test, rename 3 wiring tests
- `tools/arrconf/tests/test_qbittorrent_categories.py` — delete 1 override test
- `tools/arrconf/tests/test_jellyfin_categories.py` — delete 1 override test, rename 1 wiring test
- `tools/arrconf/tests/test_seerr_animetags.py` — delete 2 override tests
- `tools/arrconf/tests/conftest.py` (if exists) — audit fixtures, delete unreferenced

### Documentation to modify
- `CLAUDE.md` — new `## v0.3.0 → v0.4.0 deprecation` section after current "Release pin co-bump pattern" section

### Patterns and conventions (read-only references)
- `CLAUDE.md` § "Release pin co-bump pattern" — D-05 chart-pin co-bump rule applies to this phase
- `CLAUDE.md` § "Accumulated-bumps escape hatch" — applies only if the planner accumulates ≥2 bumps without push; single-PR-single-bump path expected here
- `CLAUDE.md` § "Workflow snapshot (CRITIQUE)" — snapshot discipline (ADR-6)
- `CLAUDE.md` § "Idempotence (RÈGLE D'OR)" — reconciler invariant; the refactor MUST preserve idempotence
- `CLAUDE.md` § "Tests" — 70% coverage on differ.py + reconcilers; mock httpx via respx
- `tools/snapshot/snapshot.sh` — invoked for D-14 before/after snapshots
- `tools/scripts/byte-equivalence-diff.sh` — pattern reference for schema drift checks
- `.planning/milestones/v0.3.0-phases/10-categories-6-app-propagation/10-A-generators-categories-PLAN.md` (archived) — original generator design context if planner needs the why behind `SonarrDerived` shape
- `.planning/milestones/v0.3.0-phases/10-categories-6-app-propagation/10-CONTEXT.md` (archived) — D-01/D-02/D-03 from Phase 10 explain the `merge_with_manual` design being undone

### ADRs (frontière + invariants)
- `spec.md` ADR-5 — configarr frontière (unaffected by this phase but must be honored: no quality_profile / custom_format writes)
- `spec.md` ADR-6 — snapshot discipline (drives D-14)
- `spec.md` ADR-7 — single-instance Sonarr/Radarr + tags (unchanged)
- `spec.md` ADR-8 — forceSave (unchanged; applies to reconciler PUT semantics, not to this refactor)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `arrconf/generators/categories.py` — already-pure, mypy-strict-compliant generator module. Public functions: `generate_qbit_categories`, `generate_sonarr_resources`, `generate_radarr_resources`, `generate_jellyfin_libraries`, `generate_anime_tag_labels`. Dataclasses: `SonarrDerived`, `RadarrDerived`. These are the load-bearing API of Phase 12 — every reconciler call funnels through these. No changes needed inside the file.
- `arrconf/reconcilers/_shared.py::_resolve_anime_tag_labels` — survives the deletion of `merge_with_manual`. Keep the file alive.
- `tools/snapshot/snapshot.sh` — bash baseline-snapshot helper (no Python deps). Already wired for the SC#5 pre/post pattern; the redaction logic survives.
- `tools/scripts/byte-equivalence-diff.sh` — pattern reference for schema drift checks.

### Established Patterns

- **Idempotence (CLAUDE.md "RÈGLE D'OR"):** `arrconf apply --dry-run` MUST emit `no-op` plan_action for all 6 apps when the desired state matches the cluster. SC#5's pre/post diff exercises this on the live cluster; SC#3's `test_sweep` (renamed) exercises it on the `production_cfg` fixture.
- **Chart-pin co-bump (CLAUDE.md "Release pin co-bump pattern"):** since this PR modifies `tools/arrconf/**`, the same commit MUST bump `charts/arr-stack/values.yaml#arrconf.image.tag` 0.6.7 → 0.7.0. Minor bump because the internal Python API (reconciler signatures) changes — first such change of v0.4.0.
- **Snapshot ADR-6:** `snapshots/before-phase-N-DATE/` + `snapshots/after-phase-N-DATE/` committed to git, lossless, redacted. Phase 9 + Phase 10 set the precedent.
- **Pydantic strict + `extra="forbid"`:** existing config.py models reject unknown fields. After deletion of `items` from the 6 Section models, the operator's old YAML triggers `ValidationError` with field-path resolution — that's the natural enforcement mechanism (D-13).

### Integration Points

- `__main__.py::apply` and `__main__.py::diff` are the two top-level branches that call `merge_with_manual` (12 callsites each, mirrored). The refactor consolidates them: each app branch invokes its generator once and passes the result into the reconciler. The duplicated structure between apply and diff suggests an existing helper could be factored, but that's out of scope for this phase — keep the duplication, just simplify it.
- The reconciler signature change touches the existing `reconcile_*` entry points across `reconcilers/{sonarr,radarr,qbittorrent,jellyfin,seerr}.py`. Each reconciler currently reads `instance.tags.items` etc. internally; after the refactor, they accept the lists as a parameter and ignore the (removed) `instance.tags.items` attribute. Internal reconciler logic (POST/PUT/DELETE per resource) is unchanged.
- Schema regen produces `schemas/arrconf-schema.json`. The committed schema is referenced by the YAML language server (`# yaml-language-server: $schema=` directive at the top of arrconf.yml). After schema regen the directive still works because the path is unchanged.

</code_context>

<specifics>
## Specific Ideas

- The single arrconf.yml file lives at `charts/arr-stack/files/arrconf.yml` (verified — no `examples/dev-config.yml` exists). The deprecation edit applies to this one file.
- The `production_cfg` fixture in the categories test files mirrors the production arrconf.yml (10 categories — 5 series + 5 movies). Post-deprecation, the fixture stays as-is (it tests against the categories block, not the dead flat sections).
- Image co-bump target: `0.6.7 → 0.7.0`. Minor (not patch) because the reconciler internal API changes (signature shift = breaking for any external caller of the arrconf library, none exist). First minor of v0.4.0 milestone.
- The 24-callsite count of `merge_with_manual` decomposes as: sonarr=4, radarr=4, qbit=1, seerr=1, jellyfin=1 → 11 per code path × 2 code paths (apply, diff) = 22 explicit + 2 in the diff-only branches that mirror apply. Planner should verify the exact count via `grep -c merge_with_manual tools/arrconf/arrconf/__main__.py`.
- The `merge_decision` structlog event disappears from the cluster log stream after deprecation. No external observability contract depends on it (no Grafana dashboard, no alert, no SLO).

</specifics>

<deferred>
## Deferred Ideas

- **Refactor apply/diff into a shared inner helper** — the duplication between the two branches in `__main__.py` is real but not load-bearing for Phase 12. Could become a follow-up "polish" task in a later milestone if the structure starts causing maintenance pain. Out of scope here.
- **Tests reorganized into `tests/generators/` subdir** — user explicitly rejected the structural reorg. If a future phase introduces more generator types (e.g., for a future app like Bazarr), revisit.
- **Pydantic deprecation-warning cycle (one-cycle warning before `extra="forbid"` enforces)** — rejected as overkill for single-tenant homelab. If the project ever grows external consumers, revisit.
- **Helper migration script (`tools/scripts/migrate-arrconf-v04.sh`)** — rejected. Operator = user, edits in the PR.
- **Removing the `merge_decision` structlog event from any test that asserts on its absence** — likely none, but planner should `grep -r merge_decision tools/arrconf/tests/` to confirm before declaring the deletion clean.

</deferred>

---

*Phase: 12-categories-deprecation*
*Context gathered: 2026-05-22*
