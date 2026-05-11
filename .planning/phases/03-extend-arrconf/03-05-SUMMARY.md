---
phase: "03"
plan: "05"
subsystem: arrconf
tags: [arrconf, phase-3, reconciler, prowlarr, app-sync]
one_liner: "Prowlarr app-sync reconciler targeting /api/v1/applications only, with fail-fast env resolution and WR-01 credential safety"
dependency_graph:
  requires:
    - 03-01 (ProwlarrClient, Application model, WR-01 merge_fields_for_put)
    - 03-02 (AppEntry, AppsSection, ProwlarrInstance config shape)
  provides:
    - reconcile_prowlarr (app sync entry point)
    - tests/fixtures/prowlarr/applications.json (sanitized baseline)
  affects:
    - tools/arrconf/arrconf/reconcilers/prowlarr.py (new)
    - tools/arrconf/tests/test_reconcilers_prowlarr.py (new)
    - tools/arrconf/tests/fixtures/prowlarr/applications.json (new)
tech_stack:
  added: []
  patterns:
    - Pitfall 3: ProwlarrClient.api_path = "/api/v1" (not /api/v3)
    - Pitfall 5: fail-fast env resolution in _build_desired_application before any HTTP call
    - WR-01 (Plan 01): merge_fields_for_put omits apiKey when desired empty; passes through on rotation (CR-01)
    - D-03-02: scope locked to applications endpoint only
key_files:
  created:
    - tools/arrconf/arrconf/reconcilers/prowlarr.py
    - tools/arrconf/tests/test_reconcilers_prowlarr.py
    - tools/arrconf/tests/fixtures/prowlarr/applications.json
  modified: []
decisions:
  - "No managed-tag pattern for Prowlarr applications (D-03-02) — Prowlarr application connections don't carry arrconf-managed tags by convention"
  - "_IMPLEMENTATION_BY_TYPE maps sonarr→(Sonarr,SonarrSettings) and radarr→(Radarr,RadarrSettings) as the single source of truth"
  - "FieldKV imported from resources/sonarr/download_client (not redeclared) — shared model as per RESEARCH.md anti-pattern"
  - "Desired apps built BEFORE the GET (Pitfall 5 fail-fast: missing env errors abort before any HTTP traffic)"
metrics:
  duration: "224s (3m 44s)"
  completed: "2026-05-11T08:24:06Z"
  tasks_completed: 3
  files_created: 3
  files_modified: 0
  tests_added: 7
---

# Phase 03 Plan 05: Prowlarr App-Sync Reconciler Summary

Implemented the Prowlarr reconciler for Phase 3, closing REQ-app-coverage. Scope locked by D-03-02 to the `applications` resource at `/api/v1/applications` only — indexer definitions remain out of scope and managed in the Prowlarr UI.

## What Was Built

### reconcilers/prowlarr.py

- `reconcile_prowlarr(client, instance, dry_run)` — main entry point
- `_build_desired_application(entry, prowlarr_base_url)` — constructs Application from AppEntry + env resolution
- `_execute(client, plan, dry_run)` — executes planned ADD/UPDATE/DELETE actions
- `_IMPLEMENTATION_BY_TYPE` — maps `"sonarr"` → `("Sonarr", "SonarrSettings")`, `"radarr"` → `("Radarr", "RadarrSettings")`
- `APPLICATIONS_PATH = "/applications"` — single string constant for the endpoint

**Scope contract:** Only `/applications` is touched. No `/indexers`, `/downloadclient`, or any other Prowlarr endpoint appears in this module.

### Fixture sanitization

Created `tests/fixtures/prowlarr/applications.json` from `snapshots/baseline-2026-05-07/prowlarr/applications.json` using a jq filter that REDACTs all `privacy == "apiKey"` field values.

- Fixture entries: 2 (Radarr id=1, Sonarr id=2 — baseline state)
- REDACTED apiKey field values: 2 (one per entry)
- Anti-leak audit: `grep -E "[a-f0-9]{30,}"` returned 0 matches outside of REDACTED values

### Test suite (7 tests)

| Test | What it verifies |
|------|-----------------|
| `test_prowlarr_uses_api_v1_path` | Pitfall 3 — actual HTTP URL contains `/api/v1/applications`, NOT `/api/v3/` |
| `test_add_new_application` | ADD path: empty cluster → 1 POST with apiKey injected, correct implementation/configContract/syncLevel |
| `test_missing_env_raises_reconcile_error_BEFORE_any_post` | Pitfall 5 — missing env → ReconcileError before GET (0 respx calls recorded) |
| `test_update_application_uses_forceSave_and_omits_apiKey` | UPDATE carries `?forceSave=true`; CR-01 rotation passthrough: non-empty desired apiKey flows through |
| `test_update_omits_apiKey_when_env_value_is_empty` | Empty env string treated as missing — ReconcileError raised |
| `test_dry_run_issues_zero_writes` | dry_run=True → 0 POST/PUT/DELETE |
| `test_multi_app_add` | 2 AppEntries (sonarr + radarr) → 2 POSTs with implementations ["Radarr", "Sonarr"] |

## Key Design Decisions

### No managed-tag pattern

Prowlarr applications don't carry the `arrconf-managed` tag by convention. The reconciler passes `managed_tag_id=None` to `reconcile()`, which means prune with `managed_tag_id=None` will classify unmatched cluster entries as `PRUNE_PROTECTED` (not deleted). This is correct default behavior — prune=False is the default per D-04.

### Pitfall 5 interaction with WR-01

The reconciler builds desired apps from `os.environ` BEFORE issuing the GET. If an env var is missing or empty, `ReconcileError` is raised immediately — no HTTP traffic is issued. This means the WR-01 omit-credential branch in `merge_fields_for_put` is only reached when the env var IS set (i.e., a legitimate rotation scenario). The defense-in-depth layering is: fail-fast first → WR-01 omit as backup for empty-string edge cases that somehow slip through.

### FieldKV reuse

`FieldKV` is imported from `arrconf.resources.sonarr.download_client` — not redeclared. This follows the RESEARCH.md anti-pattern guidance: one canonical FieldKV definition shared across all reconcilers.

### _IMPLEMENTATION_BY_TYPE table

The mapping is the single source of truth for Prowlarr's `implementation` / `configContract` field pair. AppEntry.type is `Literal["sonarr", "radarr"]` (Plan 02 Pydantic model), so any unknown type raises a Pydantic validation error at YAML parse time before reaching this table.

## Deviations from Plan

None — plan executed exactly as written.

- Task 5.1: Fixture created with jq pipeline as specified; baseline had 2 entries (Radarr + Sonarr) — synthetic fallback not needed
- Task 5.2: Module written as specified; auto-fixed one Rule 1 issue: unused `from typing import Any` import removed (ruff F401)
- Task 5.3: Test file written as specified; auto-fixed one Rule 1 issue: E501 line-too-long on mock response in test_update (split onto multiple lines, ruff format applied)

## Known Stubs

None — the reconciler is fully wired to the ProwlarrClient and Application model. All fields in the desired Application objects are resolved from live YAML + env at reconcile time.

## Threat Flags

No new security surface beyond what was modeled in the plan's threat register.

## Self-Check: PASSED
