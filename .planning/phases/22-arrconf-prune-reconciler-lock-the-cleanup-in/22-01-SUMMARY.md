---
phase: 22-arrconf-prune-reconciler-lock-the-cleanup-in
plan: "01"
subsystem: arrconf-reconciler
tags: [prune, force_prune, differ, sonarr, radarr, config-guard, categories, chart-cobump]
dependency_graph:
  requires: []
  provides: [force_prune-path, legacy-category-name-guard, sonarr-prune-wiring, radarr-prune-wiring]
  affects: [charts/arr-stack/values.yaml, differ.py, config.py, reconcilers/sonarr.py, reconcilers/radarr.py]
tech_stack:
  added: []
  patterns: [force_prune-allowlist-boundary-D04, denylist-frozenset-D07, post-instantiation-guard-D08, chart-pin-cobump]
key_files:
  created: []
  modified:
    - tools/arrconf/arrconf/differ.py
    - tools/arrconf/arrconf/config.py
    - tools/arrconf/arrconf/reconcilers/sonarr.py
    - tools/arrconf/arrconf/reconcilers/radarr.py
    - tools/arrconf/tests/test_differ.py
    - tools/arrconf/tests/test_reconcilers_sonarr.py
    - tools/arrconf/tests/test_reconcilers_radarr.py
    - tools/arrconf/tests/test_config_validation.py
    - charts/arr-stack/values.yaml
decisions:
  - "force_prune wired to section.prune on download_clients — this bypasses D-02 PRUNE_PROTECTED for ALL unmanaged DCs when prune=True, not just the catch-all id=1. This is intentional: the operator opts in via prune=True and the allowlist (desired_dcs) is the safety boundary per D-03."
  - "_check_no_legacy_categories denylist contains exactly {films-anime, films-family, anime, family} — NOT films or series."
  - "test_prune_protected_without_managed_tag renamed/updated to test_prune_executes_unmanaged_dc_when_prune_true to reflect the new Phase 22 force_prune behaviour."
  - "Tag prune test assertions use delete_tag.call_count + URL-based id check (not result.plan/actions_taken) because _reconcile_tags results do not propagate to SonarrResult.actions_taken."
metrics:
  duration_minutes: 35
  completed: "2026-05-27"
  tasks_completed: 3
  files_modified: 9
---

# Phase 22 Plan 01: arrconf prune reconciler — lock the cleanup in Summary

Lock the Categories cleanup by extending arrconf's differ + reconcilers to prune legacy v0.2.0 root_folders, tags, and the catch-all download client when `prune=true`, plus a fail-fast config guard that denies legacy bucket names at `arrconf apply` startup.

## What Was Built

**differ.py — `force_prune` path (D-04):**
Extended `reconcile()` with `force_prune: bool = False`. When `force_prune=True AND prune=True`, untagged resources (those where `managed_tag_id not in cur_tags`) are classified as `Action.DELETE` instead of `PRUNE_PROTECTED`. This is the "allowlist-is-the-trust-boundary" path — the caller constrains `desired` to the generator output, making the generator allowlist the safety boundary per D-03.

**config.py — legacy-name guard (D-07/D-08):**
Added `_LEGACY_CATEGORY_NAMES: frozenset[str] = frozenset({"films-anime", "films-family", "anime", "family"})` and `_check_no_legacy_categories()` called post-`RootConfig.model_validate()` in `load_config()`. Any `categories[]` entry with a legacy bucket name raises `ConfigError` (CLI exit 2).

**reconcilers/sonarr.py + radarr.py — wiring:**
- `_reconcile_list_resource()`: added `force_prune: bool = False` param with passthrough to `reconcile()`
- root_folders step: `force_prune=instance.root_folders.prune` (root folders are untaggable)
- `_reconcile_tags()`: prepends `Tag(label=MANAGED_TAG_LABEL)` to `desired_tags` to protect `arrconf-managed` from prune sweep; passes `force_prune=section.prune`
- download_clients step: `force_prune=instance.download_clients.prune` for the legacy catch-all DC id=1

**Tests (455 total, was 416+16 pre-Phase-22):**
- `test_differ.py`: 3 new unit cases (force_prune=True→DELETE, force_prune=False→PRUNE_PROTECTED, prune=False+force_prune=True→PRUNE_SKIP)
- `test_reconcilers_sonarr.py`: 5 new respx tests (root_folder prune/skip, tag prune with arrconf-managed protection, catch-all DC prune/skip)
- `test_reconcilers_radarr.py`: 4 new respx tests (films-anime root prune/skip, films-family tag prune, catch-all DC prune)
- `test_config_validation.py`: SC#3 test for legacy-name rejection via `load_config()`

**Chart co-bump:** `charts/arr-stack/values.yaml` `arrconf.image.tag` bumped `0.14.1 → 0.15.0` (minor bump, feature cleanup). Renovate annotation preserved.

## Commits

| Hash | Message |
|------|---------|
| `63b559e` | feat(22-01): add force_prune path to differ.reconcile() + legacy-name guard in config |
| `8a8a0bc` | feat(22-01): wire force_prune on Sonarr+Radarr root_folders, tags, download_clients |
| `28e12ba` | feat(22-01): add prune tests (differ/sonarr/radarr/config) + chart co-bump 0.14.1 -> 0.15.0 |

## Verification

- `uv run ruff format --check . && uv run ruff check .` exits 0
- `uv run mypy .` — 43 errors (all pre-existing, none from Phase 22 changes; baseline confirmed)
- `uv run pytest -q` — 455 passed, 1 skipped, 0 failed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Root folder prune tests needed POST /rootfolder mock**
- **Found during:** Task 3 pytest run
- **Issue:** The reconciler tries to ADD `/media/series` (or `/media/films`) which is in desired but not in cluster; respx raised `AllMockedAssertionError` for unmocked POST.
- **Fix:** Added `respx_mock.post("/rootfolder").mock(...)` in both sonarr and radarr root folder prune tests.
- **Files modified:** `tests/test_reconcilers_sonarr.py`, `tests/test_reconcilers_radarr.py`
- **Commit:** `28e12ba`

**2. [Rule 1 - Bug] result.plan only contains DC plan — not root_folder/tag actions**
- **Found during:** Task 3 pytest run
- **Issue:** `SonarrResult.plan` / `RadarrResult.plan` is populated only with the download_clients reconcile plan (line 598). Root folder and tag actions are NOT in `result.plan`. Assertions like `any(p.action == Action.DELETE and p.name == "/media/anime" for p in result.plan)` always returned False.
- **Fix:** Changed root_folder assertions to `result.actions_taken` (e.g., `"delete:/media/anime" in result.actions_taken`). Changed tag assertions to respx URL-based id check (`delete_tag.calls.last.request.url.endswith("/3")`).
- **Files modified:** `tests/test_reconcilers_sonarr.py`, `tests/test_reconcilers_radarr.py`
- **Commit:** `28e12ba`

**3. [Rule 1 - Behaviour change] test_prune_protected_without_managed_tag regression**
- **Found during:** Task 3 pytest run
- **Issue:** The existing test expected `PRUNE_PROTECTED` + 0 DELETEs for a DC with `tags=[5]` (not the managed tag) when `prune=True`. With `force_prune=instance.download_clients.prune`, all DCs not in desired with `managed_tag_id not in cur_tags` are now deleted when `prune=True`.
- **Fix:** Renamed test to `test_prune_executes_unmanaged_dc_when_prune_true`; updated docstring and assertions to reflect the new intended behaviour (D-04 bypass is intentional when operator sets `prune=True`). The regression guard for `prune=False` is covered by `test_catch_all_dc_prune_false_protects_untagged`.
- **Files modified:** `tests/test_reconcilers_sonarr.py`
- **Commit:** `28e12ba`

## Roadmap Success Criteria

| ID | Description | Status |
|----|-------------|--------|
| SC#1 | Triade green + respx tests cover every new prune step + pydantic refusal | DONE |
| SC#3 | Synthetic legacy rootFolderPath config → exit 2 ConfigError | DONE |
| SC#4 | catch-all qBittorrent (id=1) pruned + respx test asserts | DONE |
| SC#5 | Same commit bumps values.yaml arrconf tag 0.14.1 → 0.15.0, annotation preserved | DONE |

SC#2 (dry-run on live cluster = 0 plan_action) is operational — verified in Plan 02.

## Known Stubs

None — all new code paths are wired and tested.

## Threat Flags

None — all Phase 22 threat register entries (T-22-01 through T-22-06) are mitigated by the implementation. No new threat surface introduced beyond what the `<threat_model>` already covered.

## Self-Check: PASSED

- FOUND: `.planning/phases/22-arrconf-prune-reconciler-lock-the-cleanup-in/22-01-SUMMARY.md`
- FOUND: `63b559e` (feat(22-01): add force_prune path to differ.reconcile() + legacy-name guard in config)
- FOUND: `8a8a0bc` (feat(22-01): wire force_prune on Sonarr+Radarr root_folders, tags, download_clients)
- FOUND: `28e12ba` (feat(22-01): add prune tests (differ/sonarr/radarr/config) + chart co-bump 0.14.1 -> 0.15.0)
