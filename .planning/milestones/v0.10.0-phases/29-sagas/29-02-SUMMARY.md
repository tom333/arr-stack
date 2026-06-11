---
phase: 29-sagas
plan: "02"
subsystem: arrconf/reconcilers/radarr
tags: [sagas, radarr, collections, reconciler, idempotence]
dependency_graph:
  requires: [29-01]
  provides: [reconcile_radarr_collections, CollectionResource]
  affects: [tools/arrconf/arrconf/reconcilers/radarr.py, tools/arrconf/arrconf/__main__.py]
tech_stack:
  added: []
  patterns: [GET-match-by-tmdbId, PUT-on-drift, log-skip-absent, profile-name-resolution, ConfigError-on-unknown-profile]
key_files:
  created:
    - tools/arrconf/arrconf/resources/radarr/collection.py
    - tools/arrconf/tests/fixtures/radarr/collection.json
    - tools/arrconf/tests/test_reconcilers_radarr_collections.py
  modified:
    - tools/arrconf/arrconf/resources/radarr/__init__.py
    - tools/arrconf/arrconf/reconcilers/radarr.py
    - tools/arrconf/arrconf/__main__.py
decisions:
  - "SAGAS-02: GET /api/v3/collection indexed by tmdbId; PUT-on-drift; absent→log-skip (no POST-create)"
  - "D-07: strict idempotence — 2nd run with no drift produces 0 plan_actions"
  - "D-06: profile→qualityProfileId via read-only GET /qualityprofile; ConfigError if not found"
  - "T-29-04: body['id'] = cluster['id'] re-inject before PUT (Pitfall 1 mitigation)"
  - "A1/Pitfall 6: minimumAvailability default 'released'; body = dict(cluster) preserves cluster casing for non-overridden fields"
  - "ADR-5 boundary: GET /qualityprofile read-only only; no writes to quality_profiles"
  - "Saga branch wired after Jellyfin block (D-07 ordering: quality profiles must exist)"
  - "ConfigError in saga branch raises typer.Exit(code=2) — not appended to failures"
metrics:
  duration: "5 minutes"
  completed: "2026-05-31"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 3
---

# Phase 29 Plan 02: Radarr Collections Reconciler Summary

Radarr Collections reconciler (SAGAS-02): GET-match by `tmdbId`, PUT-on-drift idempotent reconcile from `kind=movies` SagaEntry list. Absent collections log-skip. Profile name resolved to `qualityProfileId` via read-only GET. Wired into `apply` saga branch with ConfigError exit-2 guard.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | CollectionResource schema + reconcile_radarr_collections | f01ebd0 | collection.py, radarr.py, test_reconcilers_radarr_collections.py |
| 2 | Wire Radarr Collections saga branch into apply | 6b975c8 | __main__.py |

## What Was Built

### CollectionResource (resources/radarr/collection.py)

Pydantic schema with `model_config = ConfigDict(extra="allow")`:
- Match key: `tmdbId: int`
- Reconciled fields: `monitored`, `qualityProfileId`, `rootFolderPath`, `searchOnAdd`, `minimumAvailability`
- Read-only excludes: `id`, `title`, `sortTitle`, `missingMovies`, `movies`, `images`, `tags` — all `Field(default=None, exclude=True)`

### reconcile_radarr_collections (reconcilers/radarr.py)

New function added with path constants `COLLECTION_PATH = "/collection"` and `QUALITY_PROFILE_PATH = "/qualityprofile"`:

1. Filters `kind=movies` sagas early-exit if none
2. `GET /qualityprofile` → `qp_by_name: dict[str, int]` (read-only, ADR-5 safe)
3. `GET /collection` → `by_tmdb_id: dict[int, dict]` (bulk fetch)
4. For each movie saga: lookup by `tmdb_collection` — if None: `log.warning("collection_absent_skip")` + continue
5. Profile name → id resolution: `ConfigError` if not found
6. Desired dict: `monitored=True, qualityProfileId, rootFolderPath, searchOnAdd=True, minimumAvailability="released"`
7. Drift check: `{k for k, v in desired.items() if cluster.get(k) != v}`
8. No drift → `log.info("collection_no_op")` + continue
9. dry_run → `log.info("dry_run_skip")` + `actions.append(f"collection:dry_run:{saga.name}")`
10. PUT: `body = dict(cluster); body.update(desired); body["id"] = cluster["id"]` then `client._request("PUT", ...)`

### apply wiring (__main__.py)

- Removed `log.debug("intent_loaded", ...)` placeholder (intent_cfg now genuinely consumed)
- Added saga branch after Jellyfin block (before `if failures:`):
  - Guard: `intent_cfg is not None and intent_cfg.sagas`
  - Radarr sub-guard: `"radarr" in targets and "main" in root.radarr and settings.radarr_api_key`
  - Lazy import `reconcile_radarr_collections`
  - `ConfigError` → `raise typer.Exit(code=2)` (not added to failures — config error class)
  - `ApiClientError | ReconcileError` → `failures.append("radarr_collections")`

### Tests (test_reconcilers_radarr_collections.py)

8 respx tests, all passing:
1. `test_collection_no_op_when_fields_match` — 0 PUT when all fields match
2. `test_collection_put_on_drift_monitored` — PUT fires once; body["id"] verified (Pitfall 1)
3. `test_collection_absent_skip_no_put` — absent collection → no PUT, returns []
4. `test_collection_profile_missing_raises_config_error` — ConfigError with profile name in message
5. `test_collection_idempotence_two_runs` — first=[], second=[] (strict D-07 idempotence)
6. `test_collection_dry_run_no_put` — dry_run=True → no PUT; action contains "dry_run"
7. `test_kind_series_ignored_no_radarr_calls` — series-only saga list → 0 GET calls
8. `test_collection_multiple_sagas_only_drifted_puts` — only drifted saga triggers PUT

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints introduced. The implementation:
- PUT /api/v3/collection/{id}: already in the plan's threat model (T-29-04 mitigated by body["id"] re-inject)
- GET /api/v3/qualityprofile: read-only, ADR-5 explicitly allows this for name→id resolution (T-29-05 accepted)
- No new endpoints beyond what the plan declared

## Known Stubs

None. The reconciler is fully implemented:
- `reconcile_radarr_collections` makes real HTTP calls (mocked in tests)
- All desired fields are correctly overridden
- The `apply` saga branch is fully wired with ConfigError and failure tracking

## Self-Check

- [x] `tools/arrconf/arrconf/resources/radarr/collection.py` — CollectionResource class present
- [x] `tools/arrconf/arrconf/reconcilers/radarr.py` — reconcile_radarr_collections + body["id"] re-inject present
- [x] `tools/arrconf/tests/test_reconcilers_radarr_collections.py` — 8 tests pass
- [x] `tools/arrconf/arrconf/__main__.py` — saga branch with apply_complete + failures.append
- [x] `charts/arr-stack/values.yaml` tag 0.19.0 confirmed (co-bump from 29-01)
- [x] Commits f01ebd0 and 6b975c8 in git log

## Self-Check: PASSED
