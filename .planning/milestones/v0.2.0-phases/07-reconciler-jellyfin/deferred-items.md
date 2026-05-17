# Deferred Items — Phase 07

## Pre-existing mypy errors in test files (out-of-scope, SCOPE BOUNDARY rule)

**Discovered during:** Plan 07-04 execution, Task 4.4–4.6 verification gate.

**Scope:** These errors exist in test files that were NOT created or modified by Plan 07-04.
Per the SCOPE BOUNDARY deviation rule, only issues directly caused by the current task's changes
are auto-fixed. Pre-existing issues in unrelated files are logged here for future resolution.

**Error count:** ~46 mypy errors across 9 pre-existing test files.

**Affected files and error categories:**

| File | Error type | Count |
|---|---|---|
| `tests/conftest.py` | `Returning Any from function declared to return "list[dict[str, Any]]"` | 26 |
| `tests/test_configarr_three_profiles.py` | Various type annotation issues | 3 |
| `tests/test_reconcilers_seerr.py` | Type annotation issues | ~3 |
| `tests/test_reconcilers_qbittorrent.py` | Type annotation issues | ~3 |
| `tests/test_reconcilers_sonarr.py` | Type annotation issues | ~2 |
| `tests/test_reconcilers_radarr.py` | Type annotation issues | ~2 |
| `tests/test_round_trip.py` | Missing return type annotations | ~2 |
| `tests/test_cli.py` | Missing return type annotations | ~2 |
| `tests/test_arrconf_yml_validates.py` | `Library stubs not installed for "jsonschema"` | 1 |

**Recommended fix:** Add explicit return type annotations to conftest.py fixture functions
(change `->` to `-> list[dict[str, Any]]` or use `cast()`), install `types-jsonschema` stub.

**Priority:** Low — pytest passes (269 tests, 84% coverage). mypy issues are in test files only,
not in production code. CI `tests.yml` should be verified to confirm whether mypy runs on
tests/ or only on arrconf/ source.
