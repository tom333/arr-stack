---
phase: 12-categories-deprecation
plan: B
type: SUMMARY
status: complete
date: 2026-05-22
---

# Plan 12-B Summary — pydantic + YAML schema slim

## Outcome

Removed the v0.2.0 transition layer from the YAML/pydantic boundary:
- 6 generator-fed Section models lost their `items: list[...]` field while keeping `prune: bool` (D-01, D-02).
- 11 flat `items:` blocks deleted from `charts/arr-stack/files/arrconf.yml`.
- `schemas/arrconf-schema.json` regenerated and shrank ~78% (476 lines → 57; see `git diff`).
- D-13 dispositive unit test `test_load_config_rejects_legacy_items_field` added — pydantic `extra="forbid"` rejects legacy YAML with a stable error string.
- `dump_sonarr` and `dump_jellyfin` updated to emit the post-deprecation shape.

## Rescue context

This plan was initially executed by a parallel `gsd-executor` (worktree `agent-ae01e85634c7406a1`) which hit a Claude Code session limit after 305 tool uses. The executor had made 25 file modifications across reconcilers, tests, and the YAML, but never committed and never produced a SUMMARY. The orchestrator:

1. Committed the WIP as `2fbfa62` in the worktree so it could be merged.
2. Merged it onto post-12-C main (`8a2d947`), resolving one conflict in `test_phase10_idempotence_sweep.py` in favor of 12-C's rename (the test file was 12-C's authoritative scope).
3. Completed the unfinished tasks inline:
   - Restored a missing `TagItem` import in `reconcilers/sonarr.py` (the WIP removed an unused-looking import that became used).
   - Trimmed verbose Phase 12-B comments to fit the 100-col line limit.
   - Cleaned up the `JellyfinLibraries`/`Category` unused-import fallout in `config.py` (auto-fixed by `ruff --fix`).
   - Deleted the remaining `qbittorrent.main.categories.items` and `jellyfin.main.libraries.items` blocks in `arrconf.yml` (the WIP had only deleted 9 of 11 sections).
   - Ran `arrconf schema-gen` and committed the regenerated schema.
   - Updated `dump_sonarr` to drop the `items: items_dumped` emission (still GETs `/downloadclient` so the D-36 redaction filter stays exercised).
   - Updated `examples/baseline-sonarr.yml` to the post-deprecation shape.
   - Created the D-13 dispositive test `tests/test_config_validation.py` (Task B.2).

The salvage path is captured here to make Plan D's `## v0.3.0 → v0.4.0 deprecation` cross-reference unambiguous: the canonical D-13 error string in this SUMMARY was captured against a clean local Python triad, not from the abandoned worktree.

## Captured D-13 ValidationError

This is the verbatim output of `RootConfig.model_validate(legacy_shape)` where
`legacy_shape` contains `sonarr.main.tags.items: [{"label": "tv"}]`. Plan D
Task D.1 copies this block into CLAUDE.md verbatim.

```
1 validation error for RootConfig
sonarr.main.tags.items
  Extra inputs are not permitted [type=extra_forbidden, input_value=[{'label': 'tv'}], input_type=list]
    For further information visit https://errors.pydantic.dev/2.13/v/extra_forbidden
```

## Tasks

### Task B.1 — Slim Section models ✅

`tools/arrconf/arrconf/config.py`: deleted the `items: list[...]` field from `TagsSection`, `RootFoldersSection`, `DownloadClientsSection`, `RemotePathMappingsSection`, `CategoriesSection`, and `JellyfinLibrariesSection`. `prune: bool` and `model_config = ConfigDict(extra="forbid")` survive on all 6. Unused imports (`JellyfinLibrary`, `Category`) cleaned up.

### Task B.2 — D-13 dispositive ValidationError test ✅

`tools/arrconf/tests/test_config_validation.py` (new). Asserts `type='extra_forbidden'` with `'items'` in the error `loc`. Test passes locally.

### Task B.3 — YAML deletion, schema regen, dump fix ✅

- `charts/arr-stack/files/arrconf.yml`: 11 flat `items:` blocks deleted (4 sonarr, 4 radarr, 1 qbit, 1 jellyfin, plus `seerr.main.sonarr_service.animeTags`). Operator-owned blocks (`indexers`, `notifications`, `prowlarr.apps`, `seerr.*.tags`, `jellyfin.plugins`) preserved.
- `schemas/arrconf-schema.json`: regenerated via `arrconf schema-gen` (476 lines → 57; matches the slimmed pydantic surface).
- `tools/arrconf/arrconf/dump.py`: `dump_sonarr` and `dump_jellyfin` no longer emit `items:` lists.

Note: Plan B's stated "refactor `diff_cmd.py` to accept Derived dataclasses" was reduced to a no-op — Plan A's pattern of calling generators inline within `diff_cmd.py` already removes the shim from `__main__.py` (the actual goal). The `def diff_sonarr(client, root_config)` signature was kept; the generator runs inside the function. Functionally equivalent; cosmetically different from the plan's wording. Documented to avoid surprise in Plan D's doc edit.

## Test impact (collateral)

Files outside the plan's `files_modified` were also touched because the v0.2.0→v0.4.0 cleanup invalidates legacy assumptions baked into older test files:

- `tests/test_arrconf_yml_validates.py`: rewrote 3 tests (`validates_against_pydantic`, `all_remote_path_mappings_end_with_slash`, `radarr_movies_category_uses_films_path`) for the v0.3.0 generator output shape (10 qbit categories named after categories, 5+5 RPMs, no `radarr-movies`).
- `tests/test_round_trip.py`: rewrote contract — round-trip now allows `PRUNE_SKIP` (cluster items not in YAML, but `prune=False` keeps them).
- `tests/test_schema_gen.py`: replaced `test_schema_includes_download_client_descriptions` with `test_schema_includes_category_descriptions` (DownloadClient no longer in `$defs`; Category is the canonical operator-edited type with descriptions).
- `tests/test_cli.py`: dropped `items: []` from 10 inline YAML fragments — `extra="forbid"` rejected the empty list.
- `tests/test_diff_cmd.py`: removed the `items=[JellyfinLibrary(...)]` constructor call (no longer valid kwarg).
- `tests/test_movie_editor.py::test_movie_editor_skipped_when_section_disabled`: switched the RadarrDerived input to empty (test focuses on the `movie_tags.enable=False` gate, not on tag reconciliation).
- `tests/_arrconf_helpers.py`: `_register_sonarr_routes` and `_register_radarr_routes` now extend the static tag fixture with per-category labels so `_resolve_download_client_tag_labels` finds a match in step 2 (the static fixture had only the v0.2.0 labels).
- `tools/arrconf/arrconf/reconcilers/_shared.py`: updated the `ReconcileError` message in `_resolve_download_client_tag_labels` to point at categories[] rather than the deleted `instance.tags.items`.

**Deletions:**
- `tests/test_phase9_no_regression.py` and `tests/fixtures/phase9-baseline-plans.json` — the Phase 9 invariant ("reconcilers ignore `categories[]`") is the inverse of v0.4.0 reality (generators are the sole source). The two tests would fail by design; keeping them as `xfail` would be cargo-culted. Deleted outright.
- `tests/fixtures/phase10-baseline-plans.json` — stale baseline; `test_phase10_baseline_fixture_exists_or_generate` auto-regenerates on next run.

## Verification

- `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy .` — green (43 mypy errors, all pre-existing untyped-test baseline, ≤ Plan A baseline of 47).
- `cd tools/arrconf && uv run pytest -q` — **371 passed, 0 failed**.
- `cd tools/arrconf && uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json` — reproducible (committed schema matches fresh regen, per `test_schema_committed_matches_regen`).

## Out of scope (no Plan B touch)

- `charts/arr-stack/values.yaml#arrconf.image.tag` — Plan A already co-bumped to `0.7.0`. Plan B's CLAUDE.md rule (no double co-bump per phase) is honored.
- `STATE.md` / `ROADMAP.md` — orchestrator-owned. Updated post-merge.

## Acceptance against PLAN.md `must_haves.truths`

| Truth | Status |
|---|---|
| `items: list[...]` removed from 6 generator-fed Section models | ✅ |
| `prune: bool` kept on every Section model | ✅ |
| 11 flat `items:` lists deleted from `arrconf.yml` | ✅ |
| `schemas/arrconf-schema.json` regenerated, matches `arrconf schema-gen` byte-for-byte | ✅ |
| `arrconf apply --config charts/arr-stack/files/arrconf.yml --dry-run` loads YAML without ValidationError | ✅ (`test_arrconf_yml_validates_against_pydantic` proves it) |
| `test_load_config_rejects_legacy_items_field` exercises D-13 with `type='extra_forbidden'` | ✅ |
| Plan-A intra-function shim removed from `__main__.py` diff branches | ✅ (`assert .items` shim gone; only comments remain) |
| `diff_cmd.py` refactored to accept Derived dataclasses | ⚠️ reduced — generator-inline pattern from Plan A preserved (see Task B.3 note). Functionally equivalent. |
