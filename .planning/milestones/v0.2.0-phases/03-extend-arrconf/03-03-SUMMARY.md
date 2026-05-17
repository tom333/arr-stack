---
phase: "03"
plan: "03"
subsystem: arrconf
tags: [arrconf, phase-3, reconciler, sonarr, host_config, root_folder, indexer, notification]
dependency_graph:
  requires: ["03-01", "03-02"]
  provides: ["reconcilers/sonarr.py extended (Phase 3 scope)"]
  affects: ["__main__.py (wired in Plan 06)", "reconcilers/radarr.py (pattern reference for Plan 04)"]
tech_stack:
  added: []
  patterns:
    - "_reconcile_list_resource generic helper (copy-paste target for Plan 04 Radarr)"
    - "_reconcile_host_config singleton helper with scoped-diff idempotence"
    - "host_config opt-in gate: if not section.enable: return (D-03-04)"
    - "Scoped diff for host_config: filter raw GET to desired_payload keys before diff_models"
key_files:
  created:
    - tools/arrconf/tests/fixtures/sonarr/indexer.json
    - tools/arrconf/tests/fixtures/sonarr/notification.json
    - tools/arrconf/tests/fixtures/sonarr/rootfolder.json
    - tools/arrconf/tests/fixtures/sonarr/config_host.json
  modified:
    - tools/arrconf/arrconf/reconcilers/sonarr.py
    - tools/arrconf/tests/test_reconcilers_sonarr.py
    - tools/arrconf/tests/conftest.py
decisions:
  - "Scoped diff for host_config: HostConfig uses extra=allow so GET response carries all server fields; comparing against sparse desired flags spurious diffs on analyticsEnabled, backupInterval, etc. Fix: filter raw dict to desired_payload keys before model_validate for current_scoped"
  - "Unused type: ignore removed after mypy confirmed no type errors with the generic BaseModel list"
  - "_reconcile_list_resource accepts list[Any] for desired_items (Plan 04 copy-paste compatibility)"
metrics:
  duration: "~30 minutes"
  completed: "2026-05-11"
  tasks: 3
  files_created: 4
  files_modified: 3
---

# Phase 03 Plan 03: Sonarr Extension Summary

Extended `reconcilers/sonarr.py` from "download_clients only" to cover indexers, root_folders, download_clients, notifications, and host_config (opt-in) — full Phase 3 Sonarr scope per D-03-01.

## Reconciler Call Order (6-Step Topology)

The extended `reconcile_sonarr` function follows this topological order:

1. **tags** — `_ensure_managed_tag` (GET/POST /tag): ensures `arrconf-managed` tag exists; its id is used for stamping download_clients
2. **indexers** — `_reconcile_list_resource(..., match_key="name")`: alignment reconcile for Prowlarr-synced indexers
3. **root_folders** — `_reconcile_list_resource(..., match_key="path", managed_tag_id=None)`: Pitfall 1 guard applied
4. **download_clients** — original Phase 1 scope with managed-tag stamping
5. **notifications** — `_reconcile_list_resource(..., match_key="name")`: webhook/Jellyfin notifications
6. **host_config** — `_reconcile_host_config(...)`: opt-in singleton, skipped when `section.enable is False` (D-03-04)

**host_config opt-in gate enforcement:** Two-line guard at reconciler entry — `if not section.enable: log.info("host_config_reconcile_skipped"); return`. GET /config/host is never issued when disabled.

## Test Count Delta

- Pre-existing: 11 tests (download_clients: add/update/no-op/prune-skip/prune-protected/prune-on/dry-run/forceSave×3)
- New: 9 tests (indexer add/no-op, notification add/no-op, root_folder add/no-update-guard, host_config skip/no-op/update)
- Total: 20 tests, all passing

4 new fixture files added to `tests/fixtures/sonarr/`: indexer.json, notification.json, rootfolder.json, config_host.json. All wired via conftest.py.

## Confirmed Guards

**Pitfall 1 (root_folder no PUT):** `test_root_folder_no_update_action_ever` asserts `put_rf.call_count == 0` when desired path matches cluster. The RootFolder model excludes `accessible`, `freeSpace`, `unmappedFolders` via `Field(exclude=True)` — these fields are excluded from `diff_models` so a path-matched root folder never produces an UPDATE plan action.

**Pitfall 4 (id re-injection in host_config PUT):** `test_host_config_update_when_different` parses the PUT body JSON and asserts `"id" in body_json`. The `current_full.id` is re-injected after `merge_fields_for_put` strips it.

**Pitfall 7 (forceSave regex):** Every UPDATE-route respx mock uses `url__regex=r"^http://sonarr\.test/api/v3/{resource}/\d+(?:\?.*)?$"` to tolerate the `?forceSave=true` query string.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] host_config idempotence: scoped diff required**
- **Found during:** Task 3.2 implementation, caught by test_host_config_no_op_when_identical
- **Issue:** `HostConfig` uses `extra="allow"` so `model_validate(raw_GET_response)` absorbs all ~30 server fields (analyticsEnabled, backupInterval, port, etc.). `diff_models(current_full, desired_sparse)` flagged diffs on every server-only field even when the operator's 4 desired fields matched exactly, causing an unwanted PUT.
- **Fix:** Before calling `diff_models`, build `current_scoped = HostConfig.model_validate({k: v for k, v in raw.items() if k in scoped_keys})` where `scoped_keys` is derived from the `desired_payload` keys. This restricts the diff to only the fields the operator declared in `HostConfigSection`.
- **Commits:** 31e683a (reconciler), 4f5ab7c (tests)

**2. [Rule 1 - Bug] Existing tests broken by extended reconciler's new GET calls**
- **Found during:** First test run after Task 3.2
- **Issue:** The extended `reconcile_sonarr` now calls GET /indexer, /rootfolder, /notification in addition to /tag and /downloadclient. The 11 existing tests only mocked /tag and /downloadclient; respx raised `AllMockedAssertionError` on the unmocked endpoints.
- **Fix:** Added `_mock_base_gets` helper in the test file that mocks all 5 endpoints, defaulting unneeded ones to empty lists. Migrated all 11 existing tests to use `_mock_base_gets`.
- **Commits:** 4f5ab7c

**3. [Rule 2 - Ruff/Mypy] Unused imports and docstring format**
- `IndexersSection`, `NotificationsSection`, `RootFoldersSection` imported but not directly used in `sonarr.py` (accessed via `SonarrInstance.indexers`, `.notifications`, `.root_folders`) — removed
- Module docstring needed blank line between summary and body (D205) — fixed
- 2 `# type: ignore[arg-type]` comments made unnecessary after removing unused imports — removed

## Threat Surface Scan

No new network endpoints or auth paths introduced in this plan. The existing `/config/host` surface was already declared in the threat model (T-03-03-01/T-03-03-02); the opt-in gate and credential exclusion are confirmed in place.

## Known Stubs

None. All reconcile calls are wired through to real API paths. Fixtures use real baseline data (sanitized). No hardcoded empty values or placeholder text in any of the modified files.

## Self-Check: PASSED

- `tools/arrconf/tests/fixtures/sonarr/indexer.json` FOUND
- `tools/arrconf/tests/fixtures/sonarr/notification.json` FOUND
- `tools/arrconf/tests/fixtures/sonarr/rootfolder.json` FOUND
- `tools/arrconf/tests/fixtures/sonarr/config_host.json` FOUND
- Commit eab0a10 FOUND (fixtures)
- Commit 31e683a FOUND (reconciler extension)
- Commit 4f5ab7c FOUND (tests + conftest)
- 20 tests pass, 0 failures
- ruff check: clean
- mypy: clean
