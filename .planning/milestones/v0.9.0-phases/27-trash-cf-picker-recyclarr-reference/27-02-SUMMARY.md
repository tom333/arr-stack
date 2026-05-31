---
phase: 27-trash-cf-picker-recyclarr-reference
plan: "02"
subsystem: arrconf-ui/backend
tags: [trash-guides, recyclarr, fastapi, metadata-endpoints, disk-serve, security]
dependency_graph:
  requires:
    - plans/27-01 (baked catalog JSON files in trash-metadata/)
  provides:
    - GET /api/trash/custom-formats?app= (sonarr|radarr)
    - GET /api/trash/quality-profiles?app= (sonarr|radarr)
    - GET /api/trash/recyclarr-templates?app= (sonarr|radarr)
    - trash_metadata_dir() path resolver in locator.py
  affects:
    - plans/27-03 (CF picker reads /api/trash/custom-formats)
    - plans/27-04 (QP picker reads /api/trash/quality-profiles)
tech_stack:
  added: []
  patterns:
    - disk-serve static JSON endpoint (mirrors get_configarr_schema() pattern)
    - enum allow-list gate for path-traversal prevention (T-27-05)
    - no-respx test pattern (pure disk reads — no HTTP mock needed)
key_files:
  created:
    - tools/arrconf-ui/tests/test_trash_endpoints.py
  modified:
    - tools/arrconf-ui/arrconf_ui/locator.py
    - tools/arrconf-ui/arrconf_ui/app.py
decisions:
  - "Enum allow-list (sonarr|radarr) before path construction: single gate prevents both 400 and path-traversal (T-27-05)"
  - "No respx in tests: endpoints are pure disk reads, no HTTP mock needed — simpler and faster"
  - "app parameter named 'app' (not 'target_app'): mirrors plan spec; FastAPI reads as required query param without Query(...)"
metrics:
  duration_seconds: 420
  completed_date: "2026-05-30"
  tasks_completed: 2
  files_created: 1
  files_modified: 2
---

# Phase 27 Plan 02: TRaSH Metadata FastAPI Endpoints — Summary

**One-liner:** Three read-only FastAPI disk-serve endpoints (CF, QP, Recyclarr templates) with enum 400 gate, 404 on missing catalog, and 8 endpoint tests against real baked assets.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add trash_metadata_dir() + 3 metadata endpoints | 92045eb | locator.py, app.py |
| 2 | Backend test module for 3 metadata endpoints | 1e13a7d | tests/test_trash_endpoints.py |

## What Was Built

**locator.py:** `trash_metadata_dir()` appended following existing resolver pattern — single docstring + boundary note; resolves to `repo_root() / tools / arrconf-ui / web / src / assets / trash-metadata`.

**app.py:** Three endpoints inside `create_app()`, inserted after `get_configarr_schema()` and before the StaticFiles mount (correct insertion site):

- `GET /api/trash/custom-formats?app=` → reads `{app}-cf.json`
- `GET /api/trash/quality-profiles?app=` → reads `{app}-qp.json`
- `GET /api/trash/recyclarr-templates?app=` → reads `recyclarr-{app}.json`

Each handler: enum gate (`app not in ("sonarr", "radarr") → 400`), then `path.exists()` check (→ 404), then `json.loads(path.read_text())`. ADR-5 section header comment precedes all three.

**tests/test_trash_endpoints.py:** 8 tests, no respx, against real baked assets from Plan 01:
- Happy path: sonarr/radarr CF, sonarr QP, radarr Recyclarr templates
- Structure assertions: trash_id/name/default_score on CFs; trash_id/items on QPs; id-only (no description) on Recyclarr
- Error paths: 400 for bogus app, 400 for `../../etc/passwd` (T-27-05), 422 for missing param
- Locator: `trash_metadata_dir()` resolves absolutely under expected suffix and exists

## Deviations from Plan

None — plan executed exactly as written.

## Validation Results

All acceptance criteria pass:

- `grep -c 'def trash_metadata_dir' locator.py` = 1
- All 3 routes present in app.py (`/api/trash/custom-formats`, `/quality-profiles`, `/recyclarr-templates`)
- 3 × `app must be 'sonarr' or 'radarr'` guards in app.py
- Triade (ruff format --check, ruff check, mypy arrconf_ui): all pass
- SC#2: no httpx/requests/urllib/github in trash handler bodies
- ADR-5: no `8989|7878|9696|sonarr.selfhost|radarr.selfhost|prowlarr.` in arrconf_ui/
- 8 tests pass: `uv run pytest tests/test_trash_endpoints.py -v` → 8 passed in 0.45s
- `grep -c 'path_traversal' test_trash_endpoints.py` = 1
- `grep -c 'respx\|httpx.mock\|github' test_trash_endpoints.py` = 0

## Threat Surface Scan

No new surface beyond plan's threat model. Threats mitigated as designed:

| Flag | File | Description |
|------|------|-------------|
| T-27-05 mitigated | app.py | Enum gate before path construction; tested by test_path_traversal_app_returns_400 |
| T-27-06 mitigated | app.py | Disk-only read; no httpx/requests/urllib in handlers |
| T-27-07 mitigated | arrconf_ui/ | No *arr URL anywhere in arrconf_ui/ package |

## Self-Check: PASSED

Files exist:
- tools/arrconf-ui/arrconf_ui/locator.py — FOUND (commit 92045eb)
- tools/arrconf-ui/arrconf_ui/app.py — FOUND (commit 92045eb)
- tools/arrconf-ui/tests/test_trash_endpoints.py — FOUND (commit 1e13a7d)

Commits exist: `git log --oneline | grep -E '92045eb|1e13a7d'` — both present on main.
