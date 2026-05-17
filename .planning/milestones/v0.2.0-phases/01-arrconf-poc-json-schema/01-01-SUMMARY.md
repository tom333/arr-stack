---
phase: 01-arrconf-poc-json-schema
plan: 01
subsystem: infra
tags: [python, uv, typer, pydantic, httpx, tenacity, structlog, docker, ghcr, github-actions]

# Dependency graph
requires:
  - phase: 00-baseline-snapshot
    provides: snapshots/baseline-2026-05-07/sonarr/{downloadclient,tag}.json (already redacted, used as fixture seeds)
provides:
  - tools/arrconf/ Python package skeleton (12 modules + 9 resources)
  - pyproject.toml with deps pinned + ruff/mypy/coverage config (Pitfall 6 workaround for per-file coverage gate)
  - uv.lock (40 packages, reproducible)
  - Multi-stage Dockerfile uv → python:3.13-slim with USER 1000:1000 (T-01-02)
  - .github/workflows/arrconf-image.yml — GHCR build/push pipeline (T-01-03 least privilege)
  - tests/conftest.py with shared respx fixtures + 5 fixture seeds (downloadclient, tag, 3 edge cases)
  - exceptions.ScopeViolationError frontière configarr (D-12 anchor) — 4 stub modules raise BEFORE any HTTP call (T-01-05)
  - differ.Action enum (6 cases: ADD/UPDATE/DELETE/NO_OP/PRUNE_SKIP/PRUNE_PROTECTED) for W2 to fill in
  - client_base.ArrApiClient + SonarrClient with tenacity retry (NOT httpx.HTTPTransport.retries per Pitfall 8); explicit "D-03: Sonarr v4+ only" anchor in code
  - settings.Settings with pydantic-settings BaseSettings + SecretStr (T-01-01 secret masking)
  - typer CLI scaffold with 4 subcommands (apply / dump / diff / schema-gen) — bodies are W3 placeholders
affects: [01-02-PLAN.md (Wave 2 reconciler), 01-03-PLAN.md (Wave 3 CLI wiring + tests.yml workflow), 02-arrconf-cluster-validation, 03-arrconf-extension]

# Tech tracking
tech-stack:
  added: [uv 0.11, typer 0.25, httpx 0.28, pydantic 2.13, pydantic-settings 2.14, ruyaml 0.91, structlog 25.5, tenacity 9.1, pytest 9.0, pytest-cov 7.1, respx 0.23, ruff 0.15, mypy 2.0, hatchling]
  patterns:
    - "Multi-stage Dockerfile: uv builder layer (cached) → python:3.13-slim runtime + non-root USER 1000:1000 (T-01-02)"
    - "tenacity @retry on _request method classifying 401/404/5xx into typed exceptions (Pitfall 8 — NOT httpx.HTTPTransport.retries which only handles connection errors)"
    - "ScopeViolationError stubs raise BEFORE httpx import — frontière configarr enforced statically (T-01-05)"
    - "pydantic Field(exclude=True) for read-only API metadata (D-21) — neutralised in diffs and YAML round-trip"
    - "PEP 695 generic syntax for differ.PlannedAction[T: BaseModel] and reconcile[T: BaseModel](...) — Python 3.13 native"
    - "Coverage scoped to differ + reconcilers.sonarr in pyproject.toml [tool.coverage.run] source — turns global fail_under=70 into a per-module gate (Pitfall 6 workaround)"
    - "GitHub Actions least privilege: { contents: read, packages: write } only; PR builds skip GHCR login (T-01-03)"
    - "structlog TTY/JSON detection: ConsoleRenderer for dev, JSONRenderer for CronJob log pipeline (D-07)"

key-files:
  created:
    - tools/arrconf/pyproject.toml
    - tools/arrconf/uv.lock
    - tools/arrconf/Dockerfile
    - tools/arrconf/.dockerignore
    - tools/arrconf/arrconf/__init__.py
    - tools/arrconf/arrconf/__main__.py
    - tools/arrconf/arrconf/exceptions.py
    - tools/arrconf/arrconf/logging.py
    - tools/arrconf/arrconf/settings.py
    - tools/arrconf/arrconf/config.py
    - tools/arrconf/arrconf/client_base.py
    - tools/arrconf/arrconf/differ.py
    - tools/arrconf/arrconf/schema_gen.py
    - tools/arrconf/arrconf/reconcilers/__init__.py
    - tools/arrconf/arrconf/reconcilers/sonarr.py
    - tools/arrconf/arrconf/resources/__init__.py
    - tools/arrconf/arrconf/resources/sonarr/__init__.py
    - tools/arrconf/arrconf/resources/sonarr/download_client.py
    - tools/arrconf/arrconf/resources/sonarr/tag.py
    - tools/arrconf/arrconf/resources/sonarr/indexer.py
    - tools/arrconf/arrconf/resources/sonarr/notification.py
    - tools/arrconf/arrconf/resources/sonarr/root_folder.py
    - tools/arrconf/arrconf/resources/sonarr/host_config.py
    - tools/arrconf/arrconf/resources/sonarr/quality_profile.py
    - tools/arrconf/arrconf/resources/sonarr/custom_format.py
    - tools/arrconf/arrconf/resources/sonarr/quality_definition.py
    - tools/arrconf/arrconf/resources/sonarr/media_naming.py
    - tools/arrconf/tests/__init__.py
    - tools/arrconf/tests/conftest.py
    - tools/arrconf/tests/fixtures/sonarr/downloadclient.json
    - tools/arrconf/tests/fixtures/sonarr/tag.json
    - tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_empty.json
    - tools/arrconf/tests/fixtures/sonarr/edge_cases/tag_with_arrconf_managed.json
    - tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_with_unmanaged_tag.json
    - .github/workflows/arrconf-image.yml
  modified: []

key-decisions:
  - "Adopt PEP 695 generic syntax (PlannedAction[T: BaseModel], reconcile[T: BaseModel](...)) instead of TypeVar+Generic[T] — Python 3.13 native, eliminates UP046/UP047 ruff hits without exceptions"
  - "Suppress N815 (mixedCase) only in arrconf/resources/** — Sonarr API contract requires camelCase (implementationName, configContract, removeCompletedDownloads, ...) and pydantic round-trip mandates field names match"
  - "Suppress B008 (function call in argument default) only in __main__.py — typer.Option(...) in argument defaults is the canonical typer CLI pattern, not a real bug"
  - "Use ConfigDict(extra=\"allow\") on DownloadClient (RESEARCH lines 1127 forward-compat note) — accepted Phase 1 simplification trade-off; W2 may add explicit allow-list if Sonarr v5 introduces problematic fields"
  - "Module docstring on client_base.py mentions Pitfall 8 (do NOT use httpx.HTTPTransport(retries=N)) — keeps the rationale visible at point-of-use; AST-level check confirms no actual usage"

patterns-established:
  - "Pattern A: Resource pydantic schema layout — model_config + required fields + read-only Field(default=None, exclude=True) excluded from diffs and YAML dumps (D-21)"
  - "Pattern B: ScopeViolationError frontière stubs — function-level raise that imports the exception but no httpx, no requests, no urllib (T-01-05 raise-before-network)"
  - "Pattern C: Phase 3 stub modules — function bodies raise NotImplementedError with explicit '# pragma: no cover' so coverage gate ignores them"
  - "Pattern D: typer entrypoint — pretty_exceptions_show_locals=False on app() construction + log structlog event before raising typer.Exit(code=N)"
  - "Pattern E: tenacity @retry decorator on _request method, classifying status codes into typed exceptions BEFORE retry condition evaluates"

requirements-completed:
  - REQ-cli-subcommands  # 4 subcommands wired (apply/dump/diff/schema-gen) — bodies are W3 placeholders but skeleton meets the contract
  - REQ-test-coverage    # coverage gate configured (fail_under=70, source scoped to differ + reconcilers.sonarr); actual % measured in W2 once tests land
  - REQ-app-coverage     # Sonarr scaffolding shipped (download_client + tag fully modeled; 4 Phase 3 stubs + 4 frontière configarr stubs); other apps deferred to Phases 3/5/6/7

# Metrics
duration: 35min
completed: 2026-05-07
---

# Phase 1 Plan 01: arrconf POC Wave 1 — Plumbing Summary

**Buildable Python package skeleton (12 modules + 9 Sonarr resource models + 4 frontière configarr stubs) with pinned deps, multi-stage non-root Dockerfile, GHCR build pipeline, and respx fixture seeds — all green under mypy --strict + ruff lint/format.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-05-07T10:55:00Z (approximate)
- **Completed:** 2026-05-07T11:08:24Z
- **Tasks:** 3
- **Files created:** 35
- **Files modified:** 0

## Accomplishments

- `tools/arrconf/` package compiles cleanly: `python -c 'import arrconf'` → 0 ; `mypy arrconf` → 0 errors in 23 source files ; `ruff check .` and `ruff format --check .` → all green.
- 6-member `differ.Action` enum (ADD/UPDATE/DELETE/NO_OP/PRUNE_SKIP/PRUNE_PROTECTED) shipped — Wave 2 fills the algorithm without touching this contract.
- 4 frontière configarr stubs (`quality_profile`, `custom_format`, `quality_definition`, `media_naming`) raise `ScopeViolationError` with `configarr.yml` in the message **BEFORE any HTTP import** — verified by AST-level grep + runtime test in Task 2 verification (T-01-05).
- `client_base.ArrApiClient` uses tenacity `@retry` on `_request` (3 attempts, exponential backoff, retries on `httpx.NetworkError`/`TimeoutException`/`ServerError`) — Pitfall 8 sidestepped (no `httpx.HTTPTransport(retries=N)`).
- 4 typer subcommands (`apply`/`dump`/`diff`/`schema-gen`) registered with `pretty_exceptions_show_locals=False` — `arrconf --help` lists all 4 (T-01-01 traceback masking).
- Multi-stage Dockerfile builds with uv 0.11 builder layer + cache-mount + cleans into `python:3.13-slim` runtime ; `USER 1000:1000` enforced on entrypoint (T-01-02).
- `.github/workflows/arrconf-image.yml` ships with `permissions: { contents: read, packages: write }` only (T-01-03 least privilege) and PR builds skipping the GHCR login step.
- Fixture seeds for Sonarr `downloadclient.json` + `tag.json` copied verbatim from Phase 0 baseline ; anti-leak grep over `tests/fixtures/` returns no real-secret matches (only `***REDACTED***` placeholders, T-01-07).

## Task Commits

1. **Task 1: pyproject.toml + Dockerfile + fixture seeds + conftest.py** — `f851c61` (feat)
2. **Task 2: arrconf package skeleton (12 modules + 9 resources + 4 frontière stubs)** — `ae615ea` (feat)
3. **Task 3: GHCR build/push workflow** — `f637ca5` (feat)

## Files Created/Modified

### Configuration & build
- `tools/arrconf/pyproject.toml` — project metadata, deps pinned (typer 0.25, httpx 0.28, pydantic 2.13, pydantic-settings 2.14, ruyaml 0.91, structlog 25.5, tenacity 9.1), ruff/mypy strict, coverage scoped to differ+reconcilers.sonarr (Pitfall 6 workaround) with fail_under=70.
- `tools/arrconf/uv.lock` — 40 packages resolved, reproducible.
- `tools/arrconf/.dockerignore` — excludes tests/, caches.
- `tools/arrconf/Dockerfile` — multi-stage (uv builder → python:3.13-slim runtime), `USER 1000:1000` (T-01-02), entrypoint `arrconf`.

### Python package
- `arrconf/__init__.py` — package docstring marker.
- `arrconf/__main__.py` — typer app, 4 subcommand skeletons, `pretty_exceptions_show_locals=False` (T-01-01).
- `arrconf/exceptions.py` — `ApiClientError` / `AuthError` / `NotFoundError` / `ServerError` / `ConfigError` / `ReconcileError` / `ScopeViolationError` (D-12 anchor).
- `arrconf/logging.py` — `configure_logging(level)` with TTY/JSON branching (D-07).
- `arrconf/settings.py` — `Settings(BaseSettings)` with `SecretStr` for `*_api_key` fields (T-01-01).
- `arrconf/config.py` — `RootConfig` → `AppsConfig` → `SonarrConfig` → `SonarrInstance` → `DownloadClientsSection` ; `load_config()` is a W3 stub.
- `arrconf/client_base.py` — `ArrApiClient` + `SonarrClient` (with explicit `# D-03: Sonarr v4+ only` anchor on `api_path = "/api/v3"`).
- `arrconf/differ.py` — `Action` enum (6 members) + `PlannedAction[T: BaseModel]` dataclass + `diff_models()`/`reconcile[T: BaseModel]()` skeletons (W2 fills bodies).
- `arrconf/schema_gen.py` — `Draft202012Generator` + `write_schema(path)` with `sort_keys=True` for D-15 reproducibility.
- `arrconf/reconcilers/__init__.py` + `arrconf/reconcilers/sonarr.py` — `SonarrResult` dataclass + `reconcile_sonarr()` skeleton.

### Sonarr resources
- `arrconf/resources/sonarr/download_client.py` — full `FieldKV` + `DownloadClient` pydantic schemas with 14 fields, `id`/`implementationName`/`infoLink`/`message`/`presets` excluded from diffs (D-21).
- `arrconf/resources/sonarr/tag.py` — `Tag` schema (id excluded, label as matching key).
- `arrconf/resources/sonarr/{indexer,notification,root_folder,host_config}.py` — Phase 3 `NotImplementedError` stubs.
- `arrconf/resources/sonarr/{quality_profile,custom_format,quality_definition,media_naming}.py` — frontière configarr stubs raising `ScopeViolationError` BEFORE any HTTP import (T-01-05).

### Tests + fixtures
- `tests/__init__.py` — empty.
- `tests/conftest.py` — 4 shared fixtures (`sonarr_downloadclient_fixture`, `sonarr_tag_managed_fixture`, `sonarr_tag_empty_fixture`, `sonarr_base_url`).
- `tests/fixtures/sonarr/downloadclient.json` — 1 qBit client, copied from snapshot (already redacted).
- `tests/fixtures/sonarr/tag.json` — `[]` (matches snapshot).
- `tests/fixtures/sonarr/edge_cases/downloadclient_empty.json` — `[]` (no clients).
- `tests/fixtures/sonarr/edge_cases/tag_with_arrconf_managed.json` — `[{"id": 1, "label": "arrconf-managed"}]`.
- `tests/fixtures/sonarr/edge_cases/downloadclient_with_unmanaged_tag.json` — 1 client tagged `[5]` (W2 prune-protection seed).

### CI
- `.github/workflows/arrconf-image.yml` — GHCR build/push, `permissions: { contents: read, packages: write }`, `linux/amd64` only, tag policy `:sha-<short>` / `:branch-<name>` / `:vX.Y.Z` / `:latest` on tag.

## Decisions Made

1. **PEP 695 generic syntax for differ.py.** Plan template suggested `TypeVar("T", bound=BaseModel)` + `Generic[T]`. Ruff `UP046`/`UP047` flagged these as outdated in Python 3.13 ; I switched to native `class PlannedAction[T: BaseModel]` and `def reconcile[T: BaseModel]()`. Same semantics, less syntax, no per-rule ignore needed. The contract documented in PLAN.md `<interfaces>` is preserved (the type parameter is still bound to `BaseModel`).
2. **Per-file ruff ignores in pyproject.toml.** Added `arrconf/resources/** = ["N815"]` (camelCase API contract) and `arrconf/__main__.py = ["B008"]` (typer canonical pattern). Both are surgical — they do not relax style rules elsewhere in the codebase.
3. **`DownloadClient.model_config = ConfigDict(extra="allow")`.** Plan said "Pattern 4 forward-compat note" — I followed the RESEARCH.md line 1127 trade-off explicitly. Future Sonarr versions can add fields without breaking parsing. W2 can switch to `extra="forbid"` per-field if drift becomes a concern.
4. **`schema_gen.Draft202012Generator.generate()` typed `mode: Literal["validation", "serialization"]`.** Plan inherited the RESEARCH.md sample with `mode: str = "validation"` ; mypy --strict rightly flagged the override return-type mismatch with the parent class. Used `Literal[...]` to match `pydantic.json_schema.GenerateJsonSchema.generate` signature exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] mypy strict failed on `schema_gen.py` mode parameter type**
- **Found during:** Task 2 verification (`uv run mypy arrconf`).
- **Issue:** The `Draft202012Generator.generate()` override declared `mode: str = "validation"` but the parent class `GenerateJsonSchema.generate()` types it as `Literal["validation", "serialization"]`. Strict mypy correctly rejected the broader signature.
- **Fix:** Imported `Literal` and changed the parameter to `mode: Literal["validation", "serialization"] = "validation"`.
- **Files modified:** `tools/arrconf/arrconf/schema_gen.py`.
- **Verification:** `uv run mypy arrconf` → `Success: no issues found in 23 source files`.
- **Committed in:** `ae615ea` (part of Task 2).

**2. [Rule 2 — Missing critical] Per-file ruff ignores for legitimate API-contract / framework patterns**
- **Found during:** Task 2 verification (`uv run ruff check .` produced 22 errors initially, including 9 `N815` mixedCase warnings on Sonarr API field names and 3 `B008` warnings on typer.Option defaults).
- **Issue:** The plan template did not address ruff's strict-mode false positives on (a) `camelCase` field names that MUST match the Sonarr API contract for round-trip serialisation, and (b) typer's canonical `def cmd(arg: T = typer.Option(...))` pattern. Without these per-file ignores, no agent could ever land a green ruff check on the resource models or the CLI entrypoint — this would silently push the burden onto W2.
- **Fix:** Added two surgical `[tool.ruff.lint.per-file-ignores]` entries: `"arrconf/resources/**" = ["N815"]` and `"arrconf/__main__.py" = ["B008"]`. Documented the rationale in inline comments above each entry.
- **Files modified:** `tools/arrconf/pyproject.toml`.
- **Verification:** `uv run ruff check .` → `All checks passed!` ; `uv run ruff format --check .` → 25 files already formatted.
- **Committed in:** `ae615ea` (part of Task 2).

**3. [Rule 1 — Bug] Docstring lint hits on `__init__.py`s and exceptions/client_base/differ**
- **Found during:** Task 2 verification (`uv run ruff check .` produced D104/D105/D107/D205/D401/E501 hits).
- **Issue:** Several module-level `__init__.py` files were empty (D104), `__init__`/`__enter__`/`__exit__` lacked docstrings (D105/D107), one `ScopeViolationError` docstring violated D205 (no blank line between summary and details), `reconcile()` docstring used "Generic" as a noun in the imperative-mood slot (D401), and one `Field(description="...")` line was 102 chars (E501).
- **Fix:** Added concise docstrings to all `__init__.py` and dunder methods ; reformatted `ScopeViolationError` docstring with summary line + blank line + body ; rephrased `reconcile()` docstring imperatively ; wrapped the long `description` argument across 2 lines.
- **Files modified:** `arrconf/__init__.py`, `arrconf/reconcilers/__init__.py`, `arrconf/resources/__init__.py`, `arrconf/exceptions.py`, `arrconf/client_base.py`, `arrconf/differ.py`, `arrconf/resources/sonarr/download_client.py`.
- **Verification:** `uv run ruff check .` → `All checks passed!`.
- **Committed in:** `ae615ea` (part of Task 2).

---

**Total deviations:** 3 auto-fixed (1 typing bug, 1 framework-conventions config gap, 1 docstring lint cleanup)
**Impact on plan:** All deviations were surgical lint/type fixes required to pass the plan's own acceptance criteria (`uv run mypy arrconf` and `uv run ruff check .` both must exit 0). No scope expansion, no behavior change, no architectural impact.

## Issues Encountered

- **Initial `uv sync` required `arrconf/__init__.py` to exist** before `[project.scripts] arrconf = "arrconf.__main__:app"` could resolve. Created the package marker file as the first action of Task 2 — same operation order suggested by the plan, so not a true deviation.
- **`grep "HTTPTransport(retries"` against `client_base.py` returns a match** because the module docstring explicitly cites the Pitfall-8 anti-pattern as "do not use this". The acceptance criterion is satisfied at the AST level — `client_base.py` does not actually call `httpx.HTTPTransport(retries=N)`, only references the name in a `do-not-do-this` warning string. Verified via `ast.NodeVisitor` walk in the verification script.

## Threat Model Mitigations Applied

| Threat ID | Severity | Status | Verification |
|-----------|----------|--------|--------------|
| T-01-01 (API key leak) | HIGH | mitigated | `settings.py` imports `SecretStr` ; `__main__.py` constructs `Typer(pretty_exceptions_show_locals=False)` |
| T-01-02 (root container) | HIGH | mitigated | `Dockerfile` line `USER 1000:1000` present + 2-stage build verified by `grep -c '^FROM '` returning 2 |
| T-01-03 (GHCR token scope) | MEDIUM | mitigated | `arrconf-image.yml` `permissions: { contents: read, packages: write }` exactly ; PR builds skip `docker/login-action@v3` step ; no `id-token: write`, no `write-all` |
| T-01-05 (scope-guard bypass) | HIGH | mitigated | 4 frontière modules raise `ScopeViolationError` BEFORE any `httpx`/`requests`/`urllib` import — verified by `grep -E '(httpx|requests|urllib)' arrconf/resources/sonarr/{quality_profile,custom_format,quality_definition,media_naming}.py` returning no matches ; runtime check in verification script confirms `configarr.yml` in error message |
| T-01-06 (TLS bypass) | LOW | accepted | `! grep "verify=False" arrconf/` — no `verify=False` anywhere ; httpx default `verify=True` enforced |
| T-01-07 (fixture leak) | HIGH | mitigated | `tests/fixtures/sonarr/downloadclient.json` byte-identical to `snapshots/baseline-2026-05-07/sonarr/downloadclient.json` (Phase 0 redaction preserved) ; anti-leak grep returns no real-secret matches |

## Decisions Surfaced for W2 Attention

1. **Final dep versions resolved by `uv.lock`** — review when starting W2 implementation (especially `pydantic-core==2.46.4` vs `pydantic==2.13.4` patch alignment if W2 hits a JSON Schema generation surprise).
2. **`DownloadClient.model_config = ConfigDict(extra="allow")`** — W2's diff_models() correctly excludes read-only fields ; ensure W2 handles unknown extra fields without flagging spurious diffs (Pitfall 4 trade-off).
3. **`differ.PlannedAction[T: BaseModel]`** uses PEP 695 syntax — W2 unit tests should construct concrete instances like `PlannedAction[DownloadClient](Action.ADD, "qbit", None, dc, [])`.
4. **`SonarrClient.api_path = "/api/v3"`** has explicit `# D-03: Sonarr v4+ only` anchor — W2 should NOT add multi-version dispatch (would require an ADR per CONTEXT.md).

## User Setup Required

None — no external service configuration required for Wave 1. The GHCR public-visibility one-time step (Pitfall 7) is documented in PLAN.md and will become a `tools/arrconf/README.md` note in Wave 3.

## Next Phase Readiness

- **W2 (reconciler)** can start immediately. All interfaces in PLAN.md `<interfaces>` are concrete: `Action` enum populated, `PlannedAction` dataclass complete, `client_base.ArrApiClient`/`SonarrClient` ready to mock with respx, exceptions defined, fixtures seeded. The `differ.diff_models()` and `differ.reconcile()` bodies are the only stubs to fill ; the contracts are pinned.
- **W3 (CLI wiring + tests.yml)** can also start in parallel with W2 — depends only on `schema_gen.write_schema()` (already implementable) and the W2 reconcile dispatch (depends on W2 completion before `apply` can do real work, but `dump`/`diff`/`schema-gen` skeletons are ready to wire).

## Self-Check: PASSED

- All 35 files exist on disk and are tracked by git (verified via `git diff --name-only 328ba7b..HEAD | wc -l`).
- All 3 task commits exist (`f851c61`, `ae615ea`, `f637ca5`) — verified via `git log --oneline 328ba7b..HEAD`.
- Plan-level verification script (8 steps) passes:
  1. `uv sync --frozen` → `Audited 40 packages`
  2. Package compiles (no errors on import)
  3. `ruff check .` → All checks passed ; `ruff format --check .` → 25 files already formatted ; `mypy arrconf` → Success in 23 source files
  4. `arrconf --help` lists all 4 subcommands
  5. 4 frontière configarr stubs all raise `ScopeViolationError` with `configarr.yml` in message
  6. `Action` enum has exactly 6 members
  7. `arrconf-image.yml` parses as valid YAML
  8. Fixtures contain no real secrets

---
*Phase: 01-arrconf-poc-json-schema*
*Plan: 01 (Wave 1 — Plumbing)*
*Completed: 2026-05-07*
