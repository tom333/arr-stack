---
phase: 15-local-config-ui
plan: 15-A
subsystem: arrconf-ui-backend
tags: [python, fastapi, pydantic, ruyaml, typer, uvicorn]
dependency_graph:
  requires: []
  provides: [arrconf-ui-backend-package, fastapi-4-endpoints, cli-launcher]
  affects: []
tech_stack:
  added: [fastapi>=0.115, uvicorn[standard]>=0.32, typer>=0.25, ruyaml>=0.91, structlog>=25.5]
  patterns: [app-factory-pattern, atomic-write-tempfile, ruyaml-round-trip, monkeypatch-locator]
key_files:
  created:
    - tools/arrconf-ui/pyproject.toml
    - tools/arrconf-ui/arrconf_ui/__init__.py
    - tools/arrconf-ui/arrconf_ui/__main__.py
    - tools/arrconf-ui/arrconf_ui/app.py
    - tools/arrconf-ui/arrconf_ui/io.py
    - tools/arrconf-ui/arrconf_ui/diff.py
    - tools/arrconf-ui/arrconf_ui/locator.py
    - tools/arrconf-ui/tests/__init__.py
    - tools/arrconf-ui/tests/conftest.py
    - tools/arrconf-ui/tests/test_io_roundtrip.py
    - tools/arrconf-ui/tests/test_diff.py
    - tools/arrconf-ui/tests/test_app_endpoints.py
    - tools/arrconf-ui/tests/test_locator.py
    - tools/arrconf-ui/tests/test_cli.py
  modified: []
decisions:
  - "Used json.loads(json.dumps(e.errors(), default=str)) to normalize pydantic ValidationError ctx values before JSONResponse — pydantic model_validators can embed ValueError objects in ctx that are not JSON-serializable"
  - "Category.base_path has a D-04 strict invariant (must equal /media/{name}) enforced by @model_validator — test_phase_14_suggestarr_coupled_fields_remain_editable only tests seerr.* fields, not categories[].base_path"
  - "Added [[tool.mypy.overrides]] for arrconf.* (no py.typed marker) alongside ruyaml.* override"
  - "Removed '0.0.0.0' from source code comments to pass grep acceptance check; D-04 is enforced by HOST = '127.0.0.1' constant"
metrics:
  duration: "9m 26s"
  completed_date: "2026-05-23"
  tasks_completed: 3
  files_created: 14
  tests_passed: 29
---

# Phase 15 Plan A: Backend FastAPI Package Summary

FastAPI backend for the local config UI: sibling Python package `tools/arrconf-ui/` with 4 REST endpoints, pydantic validation via imported arrconf models, ruyaml round-trip with atomic write, semantic diff comparator, and Typer CLI launcher binding 127.0.0.1:8765.

## Files Created (14 total)

| File | Lines | Purpose |
|------|-------|---------|
| `tools/arrconf-ui/pyproject.toml` | 62 | Package definition; `arrconf = { path = "../arrconf", editable = true }` sibling dep; ruff/mypy/pytest config mirroring arrconf |
| `tools/arrconf-ui/arrconf_ui/__init__.py` | 1 | Package marker |
| `tools/arrconf-ui/arrconf_ui/locator.py` | 34 | `repo_root()`, `arrconf_yml_path()`, `schema_json_path()` — walks `parents[3]` from package file |
| `tools/arrconf-ui/arrconf_ui/io.py` | 81 | `read_yaml()`, `dump_yaml_to_str()`, `write_yaml_atomic()` — ruyaml round-trip with `YAML(typ="rt")` + atomic `tempfile.NamedTemporaryFile + os.replace` |
| `tools/arrconf-ui/arrconf_ui/diff.py` | 112 | `diff_configs()`, `has_changes()` — semantic diff: categories matched by `name`, app instances matched by instance key, fields flattened to dotted paths |
| `tools/arrconf-ui/arrconf_ui/app.py` | 166 | FastAPI `create_app()` factory: GET/PUT `/api/config`, GET `/api/schema`, POST `/api/diff`; StaticFiles mount placeholder for Plan 15-B |
| `tools/arrconf-ui/arrconf_ui/__main__.py` | 107 | Typer CLI: `arrconf-ui [--port 8765] [--no-browser]`; `DEFAULT_PORT=8765`, `HOST="127.0.0.1"` (D-04); `webbrowser.open()` on daemon thread (D-12) |
| `tools/arrconf-ui/tests/__init__.py` | 0 | Package marker |
| `tools/arrconf-ui/tests/conftest.py` | 44 | `sandboxed_arrconf_yml` + `sandboxed_schema` fixtures with monkeypatched locators |
| `tools/arrconf-ui/tests/test_io_roundtrip.py` | 58 | 4 tests: modeline preserved, Phase 6 comments preserved, atomic write no-corruption, UTF-8 accents |
| `tools/arrconf-ui/tests/test_diff.py` | 107 | 7 tests: empty diff, category added/removed/modified, sonarr field changed, categories reordered (no change), new section added |
| `tools/arrconf-ui/tests/test_app_endpoints.py` | 141 | 6 tests: GET config 200, GET schema 200, PUT valid (writes+diff), PUT invalid 422, POST diff (no write), D-09 seerr fields editable |
| `tools/arrconf-ui/tests/test_locator.py` | 31 | 4 tests: repo_root dirs, arrconf.yml exists, schema.json exists, all paths absolute |
| `tools/arrconf-ui/tests/test_cli.py` | 68 | 8 tests: DEFAULT_PORT=8765, HOST=127.0.0.1, port resolution (flag/env/invalid/default), --help, exit-2 on missing yml |

## Triad Exit Codes

| Step | Exit Code |
|------|-----------|
| `uv run ruff format --check .` | 0 |
| `uv run ruff check .` | 0 |
| `uv run mypy .` | 0 |
| `uv run pytest -v` | 0 |

## pytest Summary

```
29 passed in 0.98s
```

Collected across 5 test files: `test_io_roundtrip.py` (4), `test_diff.py` (7), `test_app_endpoints.py` (6), `test_locator.py` (4), `test_cli.py` (8).

## Commits

| Hash | Description |
|------|-------------|
| `4a4346f` | feat(15-A): bootstrap tools/arrconf-ui package skeleton |
| `1e7ff25` | feat(15-A): FastAPI app + 4 endpoints + pytest contract tests (21 tests) |
| `9eccec1` | feat(15-A): Typer CLI launcher + bind/browser test + triad passes (29 tests) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pydantic ValidationError ctx not JSON-serializable**
- **Found during:** Task 2 — `test_put_config_with_invalid_payload_returns_422`
- **Issue:** `e.errors()` returns a list where `ctx["error"]` holds a `ValueError` object (from `@model_validator`). Passing this directly to `JSONResponse(content={"detail": e.errors()})` raised `TypeError: Object of type ValueError is not JSON serializable`.
- **Fix:** Normalize with `json.loads(json.dumps(e.errors(), default=str))` before building the JSONResponse in both PUT and GET handlers.
- **Files modified:** `tools/arrconf-ui/arrconf_ui/app.py`
- **Commit:** `1e7ff25`

**2. [Rule 1 - Bug] Category.base_path has D-04 strict invariant**
- **Found during:** Task 2 — `test_phase_14_suggestarr_coupled_fields_remain_editable`
- **Issue:** The plan's test attempted `categories[name="films-zoe"].base_path = "/media/films-zoe-new"` but `arrconf.resources.categories.Category` has a `@model_validator` that enforces `base_path == f"/media/{name}"`. This is a correct production constraint — the test was wrong about what D-09 means for `films-zoe.base_path`.
- **Fix:** Revised the test to only modify the seerr `activeAnimeProfileId`, `activeProfileId`, `activeAnimeDirectory`, `activeDirectory`, `radarr_service.activeProfileId`, `radarr_service.activeDirectory` fields (which have no such invariant). Added docstring explaining the Category invariant.
- **Files modified:** `tools/arrconf-ui/tests/test_app_endpoints.py`
- **Commit:** `1e7ff25`

**3. [Rule 1 - Bug] Removed 0.0.0.0 from source comments**
- **Found during:** Task 3 — acceptance criteria grep check
- **Issue:** The plan's action block for `__main__.py` included `# D-04 — NEVER change to 0.0.0.0` comment in the inline code. The acceptance criteria says `grep -rn "0.0.0.0" arrconf_ui/ tests/` must return 0 matches.
- **Fix:** Replaced "NEVER 0.0.0.0" comments with "loopback only" equivalents. The D-04 constraint is still enforced by `HOST = "127.0.0.1"` constant and the test `assert HOST == "127.0.0.1"`.
- **Files modified:** `tools/arrconf-ui/arrconf_ui/__main__.py`, `tools/arrconf-ui/tests/test_cli.py`
- **Commit:** `9eccec1`

**4. [Rule 1 - Bug] Fixed test_cli_help_works assertion**
- **Found during:** Task 3 — `uv run pytest tests/test_cli.py`
- **Issue:** The test had `"config UI" in result.output.lower()` but `.lower()` was the method object, not a string. Also Typer shows `@app.command()` docstring, not `app.help=`, so "Local web UI" wasn't in the output.
- **Fix:** Called `result.output.lower()` correctly and checked for `"config ui"` (lowercase) from the docstring text.
- **Files modified:** `tools/arrconf-ui/tests/test_cli.py`
- **Commit:** `9eccec1`

**5. [Rule 2 - Missing Critical Functionality] Added arrconf.* mypy override**
- **Found during:** Task 2 — `uv run mypy .`
- **Issue:** arrconf package has no `py.typed` marker, so mypy strict mode errored with `Skipping analyzing "arrconf.config": module is installed, but missing library stubs or py.typed marker`.
- **Fix:** Added `[[tool.mypy.overrides]] module = ["arrconf.*"] ignore_missing_imports = true` to `pyproject.toml`.
- **Files modified:** `tools/arrconf-ui/pyproject.toml`
- **Commit:** `1e7ff25`

## Acceptance Criteria Verification

- [x] `tools/arrconf-ui/pyproject.toml` exists with `arrconf-ui = arrconf_ui.__main__:app` console script
- [x] All 14 files created under `tools/arrconf-ui/`
- [x] `uv sync` from `tools/arrconf-ui/` succeeds (arrconf editable sibling resolves)
- [x] `from arrconf_ui.app import app; print(app.title)` → `arrconf-ui`
- [x] `grep -E 'HOST\s*=\s*"127\.0\.0\.1"' tools/arrconf-ui/arrconf_ui/__main__.py` → 1 match
- [x] `grep -rn --include="*.py" "0\.0\.0\.0" tools/arrconf-ui/arrconf_ui/ tools/arrconf-ui/tests/` → 0 matches
- [x] `charts/arr-stack/values.yaml` unmodified (arrconf.image.tag = 0.7.0 unchanged)
- [x] `tools/arrconf/arrconf/` unmodified (git diff shows no changes)
- [x] 29 pytest tests passing (>= 25 required)
- [x] Full triad green: ruff format/check/mypy all exit 0

## git diff --stat (production code, read-only boundary)

```
tools/arrconf/ — 0 files modified
charts/        — 0 files modified
schemas/       — 0 files modified
```

## D-11 Confirmation

`charts/arr-stack/values.yaml#arrconf.image.tag` = `"0.7.0"` — unchanged. Phase 15 is a sibling package, no arrconf image co-bump (D-11 explicit).

## Hand-off Note to Plan 15-B

Backend running on 127.0.0.1:8765, endpoint contract validated. Plan 15-B can `npm run dev` with Vite proxy targeting `:8765` per CONTEXT Claude's Discretion.

API endpoints ready for frontend consumption:
- `GET /api/config` → validated RootConfig JSON (all 7 top-level keys)
- `PUT /api/config` → validates via pydantic, atomic write, returns `{diff, has_changes}`
- `POST /api/diff` → stateless preview, returns `{diff, has_changes}` WITHOUT writing
- `GET /api/schema` → `schemas/arrconf-schema.json` content (Draft 2020-12, drives D-13 schema-driven form)

StaticFiles mount at `/` is a no-op until `tools/arrconf-ui/web/dist/` exists (Plan 15-B builds it).

## Known Stubs

None. All endpoints return real data from the on-disk `charts/arr-stack/files/arrconf.yml`.

## Threat Flags

None new. All 8 STRIDE threats from the plan are addressed per the threat register:
- T-15-A-02 (atomic write) mitigated via `write_yaml_atomic` + `test_atomic_write_no_corruption_on_failure`
- T-15-A-06 (StaticFiles mount) mitigated via last-mounted route + existence check

## Self-Check: PASSED

All 14 created files verified present on disk. All 3 task commits verified in git history.

| Check | Result |
|-------|--------|
| 14 source files exist on disk | PASSED |
| Commit 4a4346f exists | PASSED |
| Commit 1e7ff25 exists | PASSED |
| Commit 9eccec1 exists | PASSED |
| SUMMARY.md created | PASSED |
