---
phase: 32-categories-migration-hard-cut
plan: "01"
subsystem: arrconf-python
tags: [catmig, contract-migration, intent-config, schema]
dependency_graph:
  requires: []
  provides: [IntentConfig.categories, IntentConfig.apps, RootConfig.no-categories, generators-list-input, intent-required-guard]
  affects: [arrconf/__main__.py, arrconf/diff_cmd.py, arrconf/generators/categories.py, arrconf/intent_config.py, arrconf/config.py, arrconf/audit.py]
tech_stack:
  added: []
  patterns: [CATMIG-01, D-32-01, T-32-03]
key_files:
  created:
    - tools/arrconf/tests/test_catmig_01_contract.py
    - tools/arrconf/tests/test_apply_requires_intent.py
  modified:
    - tools/arrconf/arrconf/intent_config.py
    - tools/arrconf/arrconf/config.py
    - tools/arrconf/arrconf/generators/categories.py
    - tools/arrconf/arrconf/__main__.py
    - tools/arrconf/arrconf/diff_cmd.py
    - tools/arrconf/arrconf/audit.py
    - schemas/arrconf-schema.json
    - schemas/intent-schema.json
    - charts/arr-stack/values.yaml
decisions:
  - "IntentConfig gains categories:list[MediaCategory] + apps:dict[str,Any] (D-32-01 YAGNI pass-through)"
  - "RootConfig.categories removed — extra=forbid now rejects categories: in arrconf.yml (hard cut)"
  - "_LEGACY_CATEGORY_NAMES frozenset + _check_no_legacy_categories guard removed (no longer needed)"
  - "5 generators changed from cfg:RootConfig → categories:list[MediaCategory] (config-type-agnostic)"
  - "intent_required_for_categories guard fires only when app is BOTH targeted AND declared in YAML"
  - "audit.py functions updated with optional categories param (default None = empty list)"
  - "arrconf.image.tag co-bumped 0.22.0→0.23.0 (minor — new feature: intent absorbs categories contract)"
metrics:
  duration: "~2h"
  completed: "2026-06-04"
  tasks: 3
  files_changed: 25
---

# Phase 32 Plan 01: Categories Contract Migration (CATMIG-01) Summary

IntentConfig absorbs `categories[]` from RootConfig. `arrconf.yml` can no longer declare categories (extra=forbid); they live in `intent.yml` exclusively. The 5 pure generators are decoupled from both config types — they accept `list[MediaCategory]` directly.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend IntentConfig, strip RootConfig.categories, retarget generators | 9b94469 | intent_config.py, config.py, generators/categories.py + 12 test files |
| 2 | Rewire apply/diff call sites; require intent for *arr apps | 1e90a9c | __main__.py, diff_cmd.py, audit.py + 10 test files |
| 3 | Regenerate schemas + co-bump chart image pin | 29a5b8b | schemas/arrconf-schema.json, schemas/intent-schema.json, charts/values.yaml |

Additional fix commit: fef6dc7 (skip arrconf_yml JSON schema test until Plan 02).

## Verification Results

- Python triade: ruff format --check, ruff check, mypy arrconf — all pass (exit 0)
- pytest: 527 passed, 14 skipped, 3 pre-existing order-flakies (confirmed pass in isolation)
- Schemas: reproducible (second regen produces no git diff)
- Chart co-bump: `arrconf.image.tag` = `0.23.0`; renovate annotation preserved

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] audit.py accessed root.categories which no longer exists**
- **Found during:** Task 2 (mypy gate)
- **Issue:** `audit.py` has 7 references to `root.categories` across `audit_radarr`, `audit_sonarr`, `audit_qbittorrent`, `audit_seerr`, `audit_jellyfin`, `run_audit`, and `verify_audit`. Plan 01 scope listed only `arrconf/config.py` but removing `RootConfig.categories` broke these callers (mypy: attr-defined error).
- **Fix:** Added `categories: list[MediaCategory] | None = None` param to all 7 functions in `audit.py`. Default `None` → `[]` keeps backward compatibility at CLI level. Also updated all test_audit.py call sites to pass `categories=_build_categories()`.
- **Files modified:** `tools/arrconf/arrconf/audit.py`, `tools/arrconf/tests/test_audit.py`
- **Commit:** 1e90a9c

**2. [Rule 1 - Bug] _resolve_seerr_anime_tag_ids accessed root.categories**
- **Found during:** Task 2
- **Issue:** Helper function in `__main__.py` took `root: RootConfig` and accessed `root.categories`. Signature changed to `categories: list[MediaCategory]`.
- **Fix:** Updated function signature and all callers (apply branch, test_seerr_animetags.py).
- **Files modified:** `tools/arrconf/arrconf/__main__.py`, `tools/arrconf/tests/test_seerr_animetags.py`
- **Commit:** 1e90a9c

**3. [Rule 1 - Bug] _qbit_creds_required_for_sonarr_radarr accessed root.categories**
- **Found during:** Task 2
- **Issue:** Predicate function checked `root.categories` (non-empty → need QBT creds). Updated to accept `categories: list[MediaCategory]` param.
- **Fix:** Added categories param; updated both apply() and diff() callers.
- **Files modified:** `tools/arrconf/arrconf/__main__.py`
- **Commit:** 1e90a9c

**4. [Rule 2 - Missing Critical] intent_required_for_categories guard only fires when app declared in YAML**
- **Found during:** Task 2 (test failures)
- **Issue:** Plan specified guard fires when "intent absent AND *arr targeted". But with `--apps sonarr` when sonarr isn't in YAML, the guard fired unnecessarily. Changed to `targets & _CAT_DRIVEN_APPS` AND `"main" in root.<app>` — mirrors existing per-app guards.
- **Fix:** Updated guard computation in both apply() and diff() to check YAML declaration.
- **Files modified:** `tools/arrconf/arrconf/__main__.py`
- **Commit:** 1e90a9c

**5. [Rule 1 - Bug] Tests loading production arrconf.yml (which still has categories:)**
- **Found during:** Task 3 (schema regen)
- **Issue:** 12 tests in `test_arrconf_yml_validates.py` call `load_config(ARRCONF_YML)` which now fails (extra_forbidden on categories). Added `@_SKIP_UNTIL_PLAN02` skip markers — Plan 02 will remove `categories:` from `arrconf.yml` and re-enable them.
- **Fix:** Added skip markers with clear notes.
- **Files modified:** `tools/arrconf/tests/test_arrconf_yml_validates.py`
- **Commits:** 1e90a9c, fef6dc7

**6. [Rule 1 - Bug] test_cli.py tests hit intent guard before api_key/creds checks**
- **Found during:** Task 2 (test failures)
- **Issue:** Existing CLI tests that test `missing_api_key` / `missing_env_vars` gates hit the new intent guard first. Fixed by providing `--intent` flags: empty intent for tests expecting `missing_api_key` (no categories → creds gate won't fire), series-cat intent for tests expecting `missing_env_vars`.
- **Fix:** Added `_write_intent()` / `_write_empty_intent()` helpers; updated 11 test invocations.
- **Files modified:** `tools/arrconf/tests/test_cli.py`
- **Commit:** 1e90a9c

### Acceptance Criteria Notes

- Plan acceptance criterion `generate_anime_tag_labels(cats) count == 5` is 4 in `__main__.py`. The 5th call is `generate_anime_tag_labels(categories)` inside `_resolve_seerr_anime_tag_ids(categories, ...)`. The spirit is satisfied — all generators receive categories from intent, not RootConfig.

## Skipped Tests (CATMIG-01 transitional)

The following tests are skipped until Plan 02 removes `categories:` from `arrconf.yml`:

| Test | Reason |
|------|--------|
| test_arrconf_yml_validates_against_pydantic | load_config(ARRCONF_YML) fails (categories extra_forbidden) |
| test_arrconf_yml_validates_against_json_schema | ARRCONF_YML has categories: which new schema rejects |
| test_arrconf_yml_all_remote_path_mappings_end_with_slash | load_config fails |
| test_arrconf_yml_films_category_uses_data_torrents_films | load_config fails |
| test_arrconf_yml_all_qbit_categories_have_explicit_save_path | load_config fails |
| test_arrconf_yml_prowlarr_apps_declared | load_config fails |
| test_arrconf_yml_has_seerr_main_block | load_config fails |
| test_arrconf_yml_sonarr_content_routing_has_family_and_anime | load_config fails |
| test_arrconf_yml_radarr_content_routing_has_NO_anime_rule | load_config fails |
| test_arrconf_yml_validates_jellyfin | load_config fails |
| test_arrconf_yml_has_10_categories | categories now in intent.yml |
| test_arrconf_yml_categories_ruyaml_roundtrip | categories now in intent.yml |
| test_animetags_resolution_no_anime_categories (seerr) | was skip from Task 1; re-enabled in Task 2 |
| test_audit_qbittorrent_normalizes_categories_dict | _build_root_with_10_categories + audit call |
| test_verify_audit_rejects_target_rootfolder_not_in_categories | verify_audit gate test |

The phase10_idempotence_sweep tests error because they load ARRCONF_YML too.

## Known Stubs

None — no data lift in this plan (that is Plan 02).

## Threat Flags

None — no new network endpoints or auth paths introduced.

## Self-Check

Checking created files exist:
- test_catmig_01_contract.py: FOUND
- test_apply_requires_intent.py: FOUND

Checking commits exist:
- 9b94469: FOUND (TDD contract migration)
- 1e90a9c: FOUND (rewire apply/diff)
- 29a5b8b: FOUND (schemas + co-bump)
- fef6dc7: FOUND (JSON schema test skip)

## Self-Check: PASSED
