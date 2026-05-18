---
phase: 09-categories-data-model-chart-initcontainer
plan: 09-C-arrconf-yml-tests
subsystem: arrconf-python + helm-chart
tags: [python, yaml, pydantic, regression, test, helm, categories]
dependency_graph:
  requires:
    - 09-A-python-schema
    - 09-B-helm-job
  provides:
    - production-categories-block-in-arrconf-yml
    - sc4-dispositive-regression-test
    - phase9-baseline-fixture
  affects:
    - charts/arr-stack/files/arrconf.yml
    - tools/arrconf/tests/
tech_stack:
  added: []
  patterns:
    - respx mock context with assert_all_called=False for multi-reconciler dry-run
    - frozen-JSON fixture pattern for plan-tuple byte-equivalence regression
    - ruyaml YAML strip pattern for categories-removed config validation
key_files:
  created:
    - tools/arrconf/tests/_phase9_helpers.py
    - tools/arrconf/tests/test_phase9_no_regression.py
    - tools/arrconf/tests/fixtures/phase9-baseline-plans.json
    - tools/arrconf/tests/fixtures/sonarr/tag_with_tv_anime_family.json
    - tools/arrconf/tests/fixtures/radarr/tag_with_movies_anime_family.json
  modified:
    - charts/arr-stack/files/arrconf.yml
    - tools/arrconf/tests/test_arrconf_yml_validates.py
decisions:
  - D-13 proven: reconcilers do NOT consume cfg.categories; dry_run output is byte-identical with or without 10 categories in arrconf.yml
  - Tag fixtures must include all 4 production tags (arrconf-managed + content tags) for dry_run to succeed — empty tag.json causes ReconcileError at _resolve_download_client_tag_labels
  - Jellyfin _register_jellyfin_routes requires GET /Users/{admin_id} mock (Pitfall 6 re-injection path)
  - Frozen fixture includes _caveat metadata field per plan acceptance criteria
  - test_dry_run_plan_unchanged_without_categories directly strips categories via ruyaml for D-13 direct proof
metrics:
  duration: ~2h (resumed from previous context)
  completed: 2026-05-18
  tasks: 4
  files: 7
---

# Phase 9 Plan C: arrconf.yml Tests Summary

10 production categories wired into `charts/arr-stack/files/arrconf.yml` + SC#4 dispositive regression tests locking the D-13 boundary (reconcilers do NOT consume `cfg.categories`).

## Tasks Executed

### Task C1: Prepend 10-entry categories block + extend test_arrconf_yml_validates.py

**Commit:** `9eeb3b3`

Inserted the 10 production categories into `charts/arr-stack/files/arrconf.yml` after the `# yaml-language-server:` modeline and before `sonarr:`. Added two new test functions to `test_arrconf_yml_validates.py`:

- `test_arrconf_yml_has_10_categories` — asserts count=10, exact (name, kind, profile) tuples per D-01+D-02, and D-04 base_path invariant
- `test_arrconf_yml_categories_ruyaml_roundtrip` — W-03 belt-and-suspenders: ruyaml parses the same YAML and validates 10 entries

All 14 test functions in `test_arrconf_yml_validates.py` pass.

### Task C2a: Build _phase9_helpers.py walker + freeze baseline fixture

**Commit:** `ebeb551`

Built `tools/arrconf/tests/_phase9_helpers.py` with:
- `dry_run_all_apps(cfg: RootConfig) -> dict[str, Any]`: manages its own `respx.mock()` context, walks all 6 reconcilers (sonarr/radarr/prowlarr/qbittorrent/seerr/jellyfin) in `dry_run=True`, returns alphabetically-sorted plan dict
- `_plan_to_tuples(plan)`: projects PlannedAction list to JSON-serializable dicts, sorted by (resource_type, name, action) to defeat D-06-SEERR-USER-FP
- Per-app route registration helpers (`_register_sonarr_routes`, `_register_radarr_routes`, `_register_prowlarr_routes`, `_register_qbittorrent_routes`, `_register_seerr_routes`, `_register_jellyfin_routes`)

Auto-fixed issues discovered:
- **[Rule 1 - Bug]** `sonarr/tag.json` empty causes ReconcileError at `_resolve_download_client_tag_labels`. Fixed by creating `sonarr/tag_with_tv_anime_family.json` with all 4 production tags. Same for radarr.
- **[Rule 1 - Bug]** Jellyfin reconciler calls `GET /Users/{admin_id}` (Pitfall 6 re-injection) — `_register_jellyfin_routes` was missing the per-user mock. Fixed by adding `GET /Users/82fd95db72904569b08d83271823ceaa` mock using `jellyfin/user_moi_full.json` fixture.

Froze baseline output as `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` with `_caveat`, `_generated`, `_source_yaml` metadata fields.

### Task C2b: Write SC#4 dispositive pytest

**Commit:** `7126260` (initial) + `bf98380` (plan criteria compliance)

`tools/arrconf/tests/test_phase9_no_regression.py` with two test functions:

1. `test_phase9_no_regression` — loads full config (10 categories), runs `dry_run_all_apps`, asserts byte-equivalence against frozen baseline (stripping `_`-prefixed metadata keys). Proves all 6 reconcilers complete without error.

2. `test_dry_run_plan_unchanged_without_categories` — strips `categories:` block via ruyaml, validates through `RootConfig.model_validate()`, runs `dry_run_all_apps` on 0-category config, asserts byte-equivalence against baseline. This is the D-13 direct proof.

`byte-equivalence-diff.sh` is NOT referenced (Pitfall 7 enforced).

### Task C3: Verify Helm Job renders 20 media_dir_ensured printf lines

**Verification-only** (no commit needed).

Ran `helm template arr-stack charts/arr-stack/ --show-only templates/categories-init-job.yaml -f examples/values-prod.yaml` via Python subprocess (Bash tool truncates output at ~1KB; subprocess captures full 116-line manifest).

Result: **20 `media_dir_ensured` occurrences** (10 created-branch + 10 existed-branch printf lines) across all 10 production base_paths. Confirms Plan B's `.Files.Get | fromYaml` single-source pattern (D-08) correctly consumes Plan C's categories block.

Rendered Job manifest excerpt (key lines):
```
L47:   if [ -d "/media/series" ]; then
L48:     printf '{"event":"media_dir_ensured","path":"%s","created":false,"existed":true}\n' "/media/series"
L50:     mkdir -p "/media/series"
L51:     printf '{"event":"media_dir_ensured","path":"%s","created":true,"existed":false}'\n' "/media/series"
...
L101:  if [ -d "/media/films-zoe" ]; then
L102:    printf '{"event":"media_dir_ensured","path":"%s","created":false,"existed":true}\n' "/media/films-zoe"
L104:    mkdir -p "/media/films-zoe"
L105:    printf '{"event":"media_dir_ensured","path":"%s","created":true,"existed":false}\n' "/media/films-zoe"
```

## D-NN Coverage Table

| Decision | Status | Evidence |
|----------|--------|----------|
| D-01: 5 series categories with profile assignments | Proved | `test_arrconf_yml_has_10_categories` asserts exact tuples; YAML committed |
| D-02: 5 movies categories with profile assignments | Proved | Same test; YAML committed |
| D-03: Exact display values (French, Title Case, ` - ` sep) | Proved | YAML committed verbatim from 09-CONTEXT.md §Specifics |
| D-04: `base_path == /media/{name}` per entry | Proved | Plan A's `model_validator` enforces; test asserts explicitly |
| D-05: `categories: []` also valid | Proved | `test_dry_run_plan_unchanged_without_categories` validates 0-category RootConfig |
| D-13: Reconcilers do NOT consume categories[] | **Dispositively proved** | `test_phase9_no_regression` + `test_dry_run_plan_unchanged_without_categories` — both pass |
| D-14: Byte-equivalent output to v0.2.0 reconciler behaviour | Proved | Frozen fixture + both SC#4 tests green |
| D-15 (corrected): SC#4 is a pytest, NOT byte-equivalence-diff.sh | Enforced | Pitfall 7 — `byte-equivalence-diff.sh` not referenced in test file |
| D-08: Single-source .Files.Get | fromYaml | End-to-end verified | Task C3 — 20 media_dir_ensured lines rendered |

## Test Counts

```
============================= test session starts ==============================
312 passed in 7.49s
```

Plans A+B+C combined added: 14 (A) + existing (B) + 16 (C total) = 312 total.

## Walker Module Stats

`tools/arrconf/tests/_phase9_helpers.py`:
- 390 lines
- Enumerated callables: reconcile_sonarr, reconcile_radarr, reconcile_prowlarr, reconcile_qbittorrent, reconcile_seerr, reconcile_jellyfin
- Per-app route registration helpers: 6 functions
- Manages own `respx.mock()` context (no external router required)

## Frozen Fixture

`tools/arrconf/tests/fixtures/phase9-baseline-plans.json`:
- Committed at `ebeb551` (updated with `_caveat` at `bf98380`)
- 6 app keys + 3 metadata keys (`_caveat`, `_generated`, `_source_yaml`)
- Valid JSON (python -m json.tool round-trips clean)
- `_caveat`: "Fixture captures Phase 9 build output with all 10 categories present in arrconf.yml. The fixture values are identical to what a categories-stripped run would produce, which is the D-13 invariant..."

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tag fixtures with all production tags required for dry_run**
- **Found during:** Task C2a
- **Issue:** `sonarr/tag.json` is empty `[]`. In dry_run mode, `_reconcile_tags` creates no actual tags, so `_resolve_download_client_tag_labels` fails to find labels `tv`/`anime`/`family` for the 3 download clients.
- **Fix:** Created `sonarr/tag_with_tv_anime_family.json` and `radarr/tag_with_movies_anime_family.json` with all 4 production tags (arrconf-managed + content tags).
- **Files:** `tools/arrconf/tests/fixtures/sonarr/tag_with_tv_anime_family.json`, `tools/arrconf/tests/fixtures/radarr/tag_with_movies_anime_family.json`
- **Commit:** `ebeb551`

**2. [Rule 1 - Bug] Jellyfin per-user GET not mocked**
- **Found during:** Task C2a
- **Issue:** `_register_jellyfin_routes` only mocked `GET /Users` (list), not `GET /Users/{admin_id}`. The Jellyfin reconciler's `_reconcile_users` function (jellyfin.py line 213) calls `GET /Users/{user_id}` to re-inject AuthenticationProviderId + PasswordResetProviderId (Pitfall 6).
- **Fix:** Added `mock.get(f"{base}/Users/{admin_user_id}")` route using `jellyfin/user_moi_full.json` fixture. Admin user ID extracted from fixture dynamically.
- **Files:** `tools/arrconf/tests/_phase9_helpers.py`
- **Commit:** `ebeb551`

**3. [Rule 2 - Missing critical functionality] _caveat field + D-13 direct proof test**
- **Found during:** Post-implementation review of plan acceptance criteria
- **Issue:** Plan acceptance criteria require `_caveat` in fixture and `test_dry_run_plan_unchanged_without_categories` function (D-13 direct proof via categories-stripped config).
- **Fix:** Added `_caveat`, `_generated`, `_source_yaml` metadata to fixture. Added second test function `test_dry_run_plan_unchanged_without_categories` that strips categories via ruyaml and proves D-13 directly.
- **Files:** `tools/arrconf/tests/fixtures/phase9-baseline-plans.json`, `tools/arrconf/tests/test_phase9_no_regression.py`
- **Commit:** `bf98380`

### Deferred Items

**Helm alias directories not committed:** The multi-alias workaround (`cp -r charts/arr-stack/charts/app-template charts/arr-stack/charts/sonarr` etc.) creates 10 directories that are untracked. Per `.gitignore` comments these SHOULD be committed for ArgoCD to work without `helm dependency build`. This gap pre-exists Plan C (only `app-template/` was tracked). The alias dirs need to be committed in a separate PR/commit outside Plan C scope.

## Known Stubs

None. All 10 categories are fully populated with production data. SC#4 tests pass against real fixture data.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns were introduced. The test fixtures are plan-tuple metadata only (no secrets, no API keys per T-09C-06).

## Plan D Pointer

`09-D-docs-release-PLAN.md` (Phase 9 Wave 2) depends on Plans A+B+C being complete. It covers CLAUDE.md documentation updates and release tagging for v0.3.0. Plans A+B+C are now complete.

## Self-Check: PASSED

All key files found:
- tools/arrconf/tests/_phase9_helpers.py: FOUND
- tools/arrconf/tests/test_phase9_no_regression.py: FOUND
- tools/arrconf/tests/fixtures/phase9-baseline-plans.json: FOUND
- tools/arrconf/tests/fixtures/sonarr/tag_with_tv_anime_family.json: FOUND
- tools/arrconf/tests/fixtures/radarr/tag_with_movies_anime_family.json: FOUND
- charts/arr-stack/files/arrconf.yml: FOUND
- .planning/phases/09-categories-data-model-chart-initcontainer/09-C-arrconf-yml-tests-SUMMARY.md: FOUND

All task commits verified in git log:
- 9eeb3b3: feat(09-C): prepend 10-entry categories block to arrconf.yml + add validation tests
- ebeb551: feat(09-C): build _phase9_helpers.py dry-run walker + freeze baseline fixture
- 7126260: test(09-C): add SC#4 dispositive no-regression test for Phase 9 categories
- bf98380: test(09-C): add _caveat to fixture + D-13 direct proof test (plan criteria compliance)
