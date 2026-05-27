# Phase 22: arrconf prune reconciler — lock the cleanup in - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend arrconf so the legacy v0.2.0 paths/tags **cannot drift back** after the Phase 21 migration. Three code deliverables + one operator cleanup step:

1. **Prune steps** on Sonarr/Radarr `root_folders` + `tags`, and on the qBit download-clients set — filtered to the Categories allowlist, deleting legacy entries.
2. **Pydantic fail-fast guard** refusing legacy paths/names in config (exit 2 / `ConfigError`).
3. **Chart-pin co-bump** `0.14.1 → 0.15.0` in the same commit that lands the Python code (CLAUDE.md §"Release pin co-bump pattern").
4. **Operator cleanup step** (live, human-action — folded in by user decision D-10/D-11): remove the 3 PRUNE_PHASE_22 orphan torrents + reconcile the 10 missing-on-disk *arr records left by Phase 21.

**Stays a Categories-cleanup, not a feature.** No new Category, no new reconciler step, no new app/resource type (per REQUIREMENTS.md "Out of Scope (v0.8.0)").
</domain>

<decisions>
## Implementation Decisions

### DC catch-all qBittorrent (ROADMAP-mandated decision — CAT-CLEANUP-03c)
- **D-01:** **Full prune** of the legacy catch-all download client `qBittorrent` (id=1, no tags, priority=1). End state = only the per-Category DCs remain; every series/film routes through its Category-tagged DC. This is the DC that caused the "La Planète des Alphas" mis-route incident (intercepts at priority=1 before Category DCs match). NOT the `unsorted`-fallback option.
- **D-02:** Mechanism nuance the planner MUST handle: arrconf does **not generate** this catch-all today (it's a legacy v0.2.0 cluster artifact), and it carries **no `arrconf-managed` tag** → under the current `differ.reconcile()` logic an untagged resource with `prune=true` is classified `PRUNE_PROTECTED` (never deleted). A deliberate prune path is required to delete untagged legacy resources (see D-04).

### Prune safety model (CAT-CLEANUP-03a/b)
- **D-03:** **Allowlist = `categories[]`.** The desired set is generated from the 10 declared Categories. Any in-cluster `root_folder` / `tag` / download-client NOT in the generated set is pruned when `prune: true`. Matches REQUIREMENTS CAT-CLEANUP-03(a).
- **D-04:** `differ.reconcile()`'s managed-tag protection (delete only resources carrying `arrconf-managed`) does **not** apply to untaggable resources — root_folders have no tags, tags ARE the resource, and the catch-all DC is untagged. Planner must add a deliberate "untagged prune" path for these (the allowlist set is the safety boundary, not the managed tag). The `arrconf-managed` **tag itself is never pruned** (existing D-02 invariant, `_ensure_managed_tag` — preserve it).
- **D-05:** True legacy root folders to prune (ground-truth from post-P21 snapshot — exactly 4):
  - Radarr: `/media/films-anime`, `/media/films-family`
  - Sonarr: `/media/anime`, `/media/family`
  - `/media/films` and `/media/series` are **valid default Categories — KEEP them** (`/media/series` still holds 6 series).
- **D-06:** Safety relies on the pydantic guard (D-07) keeping config clean + **`--dry-run` mandatory before first apply** + the fact P21 already aligned the cluster (Phase 22 SC#2 = dry-run shows 0 plan_action).

### Pydantic legacy-path guard (CAT-CLEANUP-03d)
- **D-07:** **Denylist of the 4 true legacy names** `{films-anime, films-family, anime, family}`. The guard rejects any `categories[]` entry (or path-bearing field) whose name/base_path matches a legacy bucket. `films` / `series` stay valid. Satisfies SC#3 (synthetic config with `/media/films-family` → exit 2).
- **D-08:** Guard lives in **`load_config()` post-instantiation** (per scout: `categories[]` is only available after `RootConfig.model_validate()`; Section-level validators can't see it). Hard fail: exit code 2 with `ConfigError`/pydantic `ValidationError` naming the offending path.

### Phase 21 leftovers — folded INTO Phase 22 scope (operator cleanup step)
- **D-09:** User chose to **include a live operator cleanup step** in Phase 22 (overriding the "defer to operator" recommendation). This re-introduces a human-action step like Phase 21 — Phase 22 is no longer pure code. Planner must add an operator runbook step alongside the arrconf code + tests.
- **D-10:** **10 missing-on-disk *arr records** (point at Category roots, no file — left by P21 `both_missing` soft-skip): default disposition **re-monitor + trigger search** (RefreshMovie/RefreshSeries + MissingMoviesSearch / missing-episode search). Not-yet-released 2026 titles (Mario Galaxy, Hoppers, etc.) stay monitored pending availability. Rationale: kids' content, mostly Seerr-requested → worth re-acquiring.
- **D-11:** **3 orphan torrents** on `/data/complete` (Zelda ROM, Home Alone 1990, Spy Kids 2001 — flagged PRUNE_PHASE_22, match no *arr item): **delete torrent + data** from qBit. Cleans `/data/complete` entirely. Irreversible (re-download if ever wanted).

### Claude's Discretion
- Exact respx test layout (which fixtures, edge-case dir) — planner/executor decide, following existing `test_reconcilers_{sonarr,radarr}.py` + `test_differ.py` patterns.
- Whether the operator cleanup step is one runbook or folded into the dry-run/apply runbook — planner decides.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` §CAT-CLEANUP-03 — the locked requirement (prune steps a-b, DC catch-all c, pydantic guard d, tests e, chart bump f) + risk register.
- `.planning/ROADMAP.md` §"Phase 22" — 5 success criteria (Triade+pytest green, dry-run 0 plan_action, synthetic legacy path → exit 2, DC decision implemented+tested, chart co-bump 0.15.0).
- `.planning/phases/21-filesystem-metadata-migration/21-01-SUMMARY.md` §Deviations — the both_missing drift + the 10 missing items + 3 orphans (carry-forward source for D-09/10/11).
- `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md` — orphan torrent hashes (PRUNE_PHASE_22) + legacy inventory.

### Conventions
- `CLAUDE.md` §"Release pin co-bump pattern" — chart-pin co-bump rule (0.14.1 → 0.15.0 in the SAME commit as the Python code); §"Annotations Renovate" (preserve `# renovate: image=...` verbatim); §"Conventions développement — arrconf" (Triade Python obligatoire, ≥70% coverage, respx mocks, no real API in CI); §"Idempotence (RÈGLE D'OR)" (diff-before-PUT, prune opt-in per section).
- `CLAUDE.md` §"Frontière arrconf / configarr" — prune must not touch quality_profiles/custom_formats (configarr-owned).

### Code anchors (from scout)
- `tools/arrconf/arrconf/differ.py:250-299` — `reconcile()` 6-case classifier (ADD/UPDATE/DELETE/NO_OP/PRUNE_SKIP/PRUNE_PROTECTED); the managed-tag gate that D-04 must work around.
- `tools/arrconf/arrconf/reconcilers/sonarr.py` (root_folders ~516-528 match by `path`; tags ~271-309 match by `label`; download_clients ~554) + `radarr.py` mirror.
- `tools/arrconf/arrconf/generators/categories.py:125-196` — `generate_sonarr_resources` / radarr; generates 5 Category DCs per kind (priority=1, tag_labels=[category]); does NOT generate a catch-all.
- `tools/arrconf/arrconf/config.py` — `ConfigDict(extra="forbid")` on all sections; `load_config()` ~664-681 (the D-08 guard hook); `resources/categories.py:43-51` (Category.base_path == /media/{name} validator).
- `charts/arr-stack/files/arrconf.yml:3-53` — the 10 Category declarations (source of truth for the allowlist).
- `charts/arr-stack/values.yaml:451` — `tag: "0.14.1"` (co-bump target → 0.15.0).
- Tests: `tools/arrconf/tests/test_differ.py` (action classifier), `test_reconcilers_sonarr.py` / `test_reconcilers_radarr.py` (respx), `conftest.py` fixtures + `fixtures/sonarr/edge_cases/`.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `differ.reconcile()` already classifies prune cases — extend it (or add a sibling path) for untagged-resource prune (D-04), don't rewrite.
- Per-section `prune: bool = Field(default=False)` already exists on every Section model (`config.py`) — the knob is there; root_folders/tags just need the prune to actually delete (today they hit PRUNE_PROTECTED).
- Generators already produce the canonical desired set from `categories[]` — the allowlist (D-03) is literally the generator output; reuse it.

### Established Patterns
- root_folders matched by `path`, tags by `label`, download_clients by `name` — keep these match keys.
- `extra="forbid"` everywhere → adding a legacy `.items` field already errors (v0.4.0 deprecation). The D-07 guard adds semantic (name-denylist) validation on top of structural.
- Chart-pin co-bump in the SAME commit as Python code (CLAUDE.md) — Phase 22 IS a co-bump trigger (touches `tools/arrconf/**`).

### Integration Points
- `load_config()` is the validation seam for D-08 (categories available post-instantiation).
- The operator cleanup step (D-09/10/11) talks to live Radarr/Sonarr (RefreshMovie/RefreshSeries + missing search) and qBit (`/api/v2/torrents/delete` with `deleteFiles=true`) — reuse the `arrconf.client_base` clients + the Phase 21 port-forward/sealed-secret pattern.
</code_context>

<specifics>
## Specific Ideas

- DC prune end-state mockup (user-approved): only Category DCs remain, catch-all removed (see D-01 preview).
- The pydantic guard's concrete test (SC#3): a synthetic config with a `films-family` category (base_path `/media/films-family`) must exit 2 with the offending path named.
</specifics>

<deferred>
## Deferred Ideas

- **ROADMAP Phase 23 SC#1/SC#2 correction (NOT this phase, but flag for Phase 23):** the roadmap lists `/media/films` and `/media/series` as "legacy absent" — that is WRONG; they are valid default Categories (`/media/series` holds 6 series post-migration). Phase 23 SC must be corrected to list only the 4 true legacy paths (`/media/films-anime`, `/media/films-family`, `/media/anime`, `/media/family`) as the ones that must be absent. Recorded here so it isn't lost.
- Re-import historique / watch-state recovery — explicitly out of scope (REQUIREMENTS v0.8.0 "Aucun re-import historique"; single-user accepts best-effort).
- `unsorted` low-priority fallback DC — rejected in favor of full prune (D-01); could revisit if a future non-Category routing need appears.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.
</deferred>

---

*Phase: 22-arrconf-prune-reconciler-lock-the-cleanup-in*
*Context gathered: 2026-05-27*
