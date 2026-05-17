---
phase: 01-arrconf-poc-json-schema
verified: 2026-05-07T11:59:51Z
status: human_needed
score: 4/6 must-haves verified, 2 require human verification
overrides_applied: 0
human_verification:
  - test: "GHCR public visibility toggle — confirm image ghcr.io/tom333/arr-stack-arrconf is publicly pullable"
    expected: "After first push to main, visit https://github.com/users/tom333/packages/container/arr-stack-arrconf/settings → Change visibility → Public; then `docker pull ghcr.io/tom333/arr-stack-arrconf:sha-<short>` succeeds anonymously"
    why_human: "GHCR public visibility is a one-time manual UI step; cannot be automated via gh CLI as of 2026-04 (Pitfall 7). Workflow `arrconf-image.yml` is verified correct — it triggers on push to main with `permissions: { contents: read, packages: write }` and tags `:sha-<short>`, but the public toggle is owned by the human operator after first successful push."
  - test: "VS Code autocomplete demo against examples/baseline-sonarr.yml"
    expected: "Open examples/baseline-sonarr.yml in VS Code with Red Hat YAML extension. (a) Bottom-right shows 'YAML' badge with schema attached. (b) Cursor under `download_clients:` proposes `prune:` and `items:` with descriptions from pydantic Field. (c) Cursor on `protocol:` shows tooltip from pydantic docstring. (d) Typing an invalid value (e.g. `protocol: ftp`) produces a red squiggle from JSON Schema validation."
    why_human: "Editor-rendering behavior is interactive and not automatable in this verifier. All prerequisites are programmatically verified: schema is Draft 2020-12 (verified by jq), descriptions are present on DownloadClient fields (8/15 props, including `name` per test_schema_includes_download_client_descriptions), and the modeline is line 1 of the YAML (matches `# yaml-language-server: $schema=../schemas/arrconf-schema.json` exactly)."
  - test: "Live round-trip against real Sonarr instance"
    expected: "Port-forward Sonarr from my-kluster, run `arrconf dump --apps sonarr --output examples/baseline-sonarr.yml`, then `arrconf diff --apps sonarr` returns exit 0. Currently only proven via respx-mocked round-trip integration test."
    why_human: "Requires live Sonarr instance and SONARR_API_KEY; hand-off to Phase 2 cluster validation. Engine-level round-trip is locked by `test_round_trip_dump_apply_dry_run_is_noop` (respx-mocked) and `test_committed_baseline_yaml_loads`; live verification deferred to Phase 2."
---

# Phase 1: arrconf POC + JSON Schema Verification Report

**Phase Goal:** Livrer un squelette Python `arrconf` avec ses 4 sous-commandes (`apply`, `dump`, `diff`, `schema-gen`), CI build d'image GHCR, et UN reconciler bout-en-bout (Sonarr `download_clients`) prouvant le round-trip `dump → apply --dry-run` = 0 action. JSON Schema généré et autocomplétion VS Code fonctionnelle.

**Verified:** 2026-05-07T11:59:51Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| #   | Truth                                                                                                                   | Status      | Evidence                                                                                                                                                                                                                                                                                                                                                          |
| --- | ----------------------------------------------------------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `pytest` green with coverage ≥ 70 % on `differ.py` + `reconcilers/sonarr.py` (all mocks via respx)                      | VERIFIED    | Ran `uv run pytest --cov --cov-report=term-missing --cov-fail-under=70` — 52 passed, 0 failed; coverage 100% on `arrconf/differ.py` (53 stmts, 14 branches) and 98% on `arrconf/reconcilers/sonarr.py` (71 stmts, 20 branches; combined 99% / 98.73%); all HTTP mocked via respx (verified by reading test_round_trip.py + test_reconcilers_sonarr.py).            |
| 2   | Image `ghcr.io/tom333/arr-stack-arrconf:sha-<short>` builds via GitHub Actions and is public                            | HUMAN_NEEDED | `.github/workflows/arrconf-image.yml` correctly defined — triggers on push to main + v* tags, has `permissions: { contents: read, packages: write }`, uses `docker/metadata-action@v5` with tag template `type=sha,prefix=sha-,format=short`, and references `tools/arrconf/Dockerfile` (which exists, multi-stage uv → python:3.13-slim, USER 1000:1000). However: (a) actual first push to main hasn't been done yet, and (b) GHCR public-visibility toggle is a manual UI step (Pitfall 7) — see human_verification[0]. |
| 3   | `arrconf dump --apps sonarr` produces `examples/baseline-sonarr.yml` that round-trips via `arrconf diff` → 0 diff       | VERIFIED (engine-level) / HUMAN (live) | `examples/baseline-sonarr.yml` exists (1.4K) with modeline as line 1 + valid pydantic structure (1 qBit DownloadClient, 14 fields, ***REDACTED*** secrets). `test_round_trip_dump_apply_dry_run_is_noop` passes — respx-mocked round-trip produces `actions_taken == []` with 0 POST/PUT/DELETE/POST-tag calls; `test_committed_baseline_yaml_loads` confirms baseline parses via `load_config()`. Live round-trip vs real Sonarr — see human_verification[2].   |
| 4   | `arrconf apply --config examples/baseline-sonarr.yml --apps sonarr --dry-run` logs "no-op"                              | VERIFIED    | Engine-level: `test_dump_apply_no_op` (W2) + `test_round_trip_dump_apply_dry_run_is_noop` (W3) both prove the no-op path. CLI-level: `apply` body in `__main__.py:99-103` — when all plan entries are `Action.NO_OP` or `prune-*`, logs `log.info("no-op", app="sonarr", count=...)`. The string "no-op" appears as the structlog event name.                       |
| 5   | VS Code autocompletion works on `examples/baseline-sonarr.yml`                                                          | HUMAN_NEEDED | All prerequisites verified: (a) `schemas/arrconf-schema.json` is Draft 2020-12 (jq-verified `"$schema": "https://json-schema.org/draft/2020-12/schema"`); (b) DownloadClient has descriptions on 8/15 properties including `name`, `protocol`, `configContract`, `fields`, `tags`; (c) baseline-sonarr.yml line 1 matches modeline exactly. Editor-rendering is interactive — see human_verification[1]. |
| 6   | CI `tests.yml` verifies `arrconf schema-gen` produces a file identical to committed `schemas/arrconf-schema.json`       | VERIFIED    | `.github/workflows/tests.yml:49-56` runs `uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json` then `git diff --exit-code schemas/arrconf-schema.json` with an `::error::` annotation on failure. Locally verified: `uv run arrconf schema-gen --output /tmp/regen.json && diff /tmp/regen.json schemas/arrconf-schema.json` → byte-identical. `test_schema_committed_matches_regen` and `test_schema_is_reproducible` lock the property at unit level. |

**Score:** 4/6 truths fully VERIFIED, 2/6 require human verification (interactive: GHCR public toggle, VS Code editor demo). The 3rd item (live Sonarr round-trip) is engine-verified — live cluster verification belongs to Phase 2.

### Required Artifacts

| Artifact                                                | Expected                                                                              | Status     | Details                                                                                                                                                                          |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tools/arrconf/pyproject.toml`                          | Project deps + ruff/mypy strict + coverage config (`[tool.coverage.run]`)              | VERIFIED   | All 7 deps pinned per W1 promise; `[tool.coverage.run] source = ["arrconf.differ", "arrconf.reconcilers.sonarr"]`; `[tool.coverage.report] fail_under = 70`.                      |
| `tools/arrconf/uv.lock`                                 | Reproducible dep resolution                                                            | VERIFIED   | Present, 84.3 KB. `uv sync --frozen` works (verified by tests passing).                                                                                                          |
| `tools/arrconf/Dockerfile`                              | Multi-stage build, non-root runtime (USER 1000:1000)                                   | VERIFIED   | 2 `FROM` directives (uv builder → python:3.13-slim runtime); `USER 1000:1000` directive at line 38; entrypoint `arrconf`.                                                       |
| `tools/arrconf/arrconf/__main__.py`                     | Fully-wired typer CLI with 4 subcommands, exit codes 0/1/2/3                           | VERIFIED   | 4 typer commands registered (`apply`, `dump`, `diff`, `schema-gen`), `pretty_exceptions_show_locals=False`, fast-fail on missing API key (3 sites with exit 2 + log).            |
| `tools/arrconf/arrconf/exceptions.py`                   | ScopeViolationError + ApiClientError hierarchy                                         | VERIFIED   | Contains all 7 exception classes including `ScopeViolationError` (D-12 anchor).                                                                                                  |
| `tools/arrconf/arrconf/differ.py`                       | Action enum + diff_models + reconcile (full impl)                                      | VERIFIED   | 6-member Enum (ADD/UPDATE/DELETE/NO_OP/PRUNE_SKIP/PRUNE_PROTECTED), `diff_models()` excludes 5 read-only fields (D-21), `reconcile()` PEP 695 generic with managed-tag gate.     |
| `tools/arrconf/arrconf/reconcilers/sonarr.py`           | reconcile_sonarr orchestrator + _ensure_managed_tag                                    | VERIFIED   | 5-step orchestrator (managed tag → GET → stamp → diff → execute) with dry-run sentinel id=-1; `_ensure_managed_tag` idempotent get-or-create.                                   |
| `tools/arrconf/arrconf/dump.py`                         | dump_sonarr emits modeline as line 1                                                   | VERIFIED   | `modeline = f"# yaml-language-server: $schema={SCHEMA_RELATIVE_PATH_FROM_EXAMPLES}\n"` written before yaml.dump; WARN log when schema target unresolved.                         |
| `tools/arrconf/arrconf/diff_cmd.py`                     | diff_sonarr returns exit 3 on drift                                                    | VERIFIED   | Returns 3 if any non-NO_OP plan entry, 0 otherwise.                                                                                                                              |
| `tools/arrconf/arrconf/config.py`                       | RootConfig + load_config raising ConfigError                                           | VERIFIED   | RootConfig → AppsConfig → SonarrConfig → SonarrInstance → DownloadClientsSection; `load_config()` raises `ConfigError` for missing file / parse / validation.                  |
| `tools/arrconf/arrconf/client_base.py`                  | ArrApiClient with tenacity retry, SonarrClient subclass                                | VERIFIED   | `@retry` on `_request()`; `httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)`; SonarrClient.api_path = "/api/v3" with D-03 anchor.                                    |
| `tools/arrconf/arrconf/schema_gen.py`                   | Draft202012Generator + write_schema with sort_keys                                     | VERIFIED   | Class forces `$schema` dialect; `write_schema()` writes JSON with `sort_keys=True` + trailing newline.                                                                          |
| `tools/arrconf/arrconf/settings.py`                     | Settings(BaseSettings) with SecretStr + case_sensitive=False                           | VERIFIED   | `sonarr_api_key`, `radarr_api_key`, `prowlarr_api_key` typed as `SecretStr | None`; case_sensitive=False so MAJUSCULE env vars bind. (See WR-05 below — design tradeoff.)         |
| `tools/arrconf/arrconf/resources/sonarr/download_client.py` | Full FieldKV + DownloadClient pydantic schemas                                     | VERIFIED   | 14 fields including read-only-excluded (id/implementationName/infoLink/message/presets); `ConfigDict(extra="allow")` for Sonarr v5 forward-compat.                              |
| `tools/arrconf/arrconf/resources/sonarr/{quality_profile,custom_format,quality_definition,media_naming}.py` | Frontière configarr stubs raising ScopeViolationError    | VERIFIED   | All 4 modules raise `ScopeViolationError` BEFORE any HTTP import; verified by 12 parametrized tests + grep audit.                                                                |
| `tools/arrconf/arrconf/resources/sonarr/{indexer,notification,root_folder,host_config}.py` | Phase 3 NotImplementedError stubs                              | VERIFIED   | 4 stubs with `pragma: no cover` raising `NotImplementedError`.                                                                                                                   |
| `schemas/arrconf-schema.json`                           | Draft 2020-12 JSON Schema, reproducible byte-for-byte                                  | VERIFIED   | 9.0K, jq confirms `$schema = "https://json-schema.org/draft/2020-12/schema"`; `arrconf schema-gen --output /tmp/regen.json` produces byte-identical output.                     |
| `examples/baseline-sonarr.yml`                          | Round-trip artifact + modeline as line 1                                               | VERIFIED   | 1.4K; line 1 matches `# yaml-language-server: $schema=../schemas/arrconf-schema.json` exactly; loads cleanly via `load_config()` with 1 qBit DC + 14 fields, secrets redacted. |
| `.github/workflows/arrconf-image.yml`                   | GHCR build/push pipeline with least-privilege permissions                              | VERIFIED   | Triggers on `push:branches[main]` + `tags:[v*]` + PRs; `permissions: { contents: read, packages: write }`; PR builds skip GHCR login; tags include `:sha-<short>`.              |
| `.github/workflows/tests.yml`                           | CI pipeline — ruff + format + mypy + pytest --cov + schema-gen + fixture audit         | VERIFIED   | 6 steps in correct D-13 order; `permissions: contents: read` only; D-15 schema regen gate via `git diff --exit-code`; T-01-07 fixture audit; D-16 modeline check.                |
| `tools/arrconf/README.md`                               | Quick-start, env vars, GHCR public toggle, VS Code autocomplete demo                   | VERIFIED   | 12 sections including "VS Code autocomplete demo (REQ-yaml-autocomplete)" and "GHCR image — one-time public visibility step (Pitfall 7)".                                       |
| `tools/arrconf/tests/test_*.py` (8 modules, 52 tests)   | 52 tests covering differ + reconcilers + managed_tag + scope_violation + cli + config + schema_gen + round_trip | VERIFIED | 52 passed, 0 failed; coverage 99% combined on scoped modules. Modules: test_differ (9), test_reconcilers_sonarr (7), test_managed_tag (5), test_scope_violation (12), test_cli (9), test_config (4), test_schema_gen (4), test_round_trip (2). |
| `tools/arrconf/tests/fixtures/sonarr/*.json`            | Sanitised fixture seeds                                                                | VERIFIED   | 5 JSON fixtures + 1 partial-response edge case; downloadclient.json contains `***REDACTED***` for password field; tag.json is `[]`; conftest fixture audit clean.                |

### Key Link Verification

| From                                                            | To                                                            | Via                                                                                                       | Status   | Details                                                                                                                            |
| --------------------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `arrconf/__main__.py`                                           | `arrconf/reconcilers/sonarr.py`                               | `from arrconf.reconcilers.sonarr import reconcile_sonarr` + call in `apply` body                          | WIRED    | Import at line 28; called at line 98 with `(client, instance, dry_run=dry_run or settings.arrconf_dry_run)`.                       |
| `arrconf/__main__.py`                                           | `arrconf/schema_gen.py`                                       | `from arrconf.schema_gen import write_schema` + call in `schema_gen_cmd`                                  | WIRED    | Import at line 29; called in `schema_gen_cmd` body at line 196.                                                                    |
| `arrconf/__main__.py`                                           | `arrconf/dump.py`                                             | `from arrconf.dump import dump_sonarr` + call in `dump` body                                              | WIRED    | Import at line 20; called at line 144 with `(client, output)`.                                                                     |
| `arrconf/__main__.py`                                           | `arrconf/diff_cmd.py`                                         | `from arrconf.diff_cmd import diff_sonarr` + call in `diff` body                                          | WIRED    | Import at line 19; called at line 176 with `(client, root)`.                                                                       |
| `arrconf/__main__.py`                                           | `arrconf/config.py`                                           | `from arrconf.config import load_config`                                                                  | WIRED    | Import at line 18; called in all 3 of `apply`/`dump`/`diff` (lines 75, 131, 160).                                                  |
| `arrconf/reconcilers/sonarr.py`                                 | `arrconf/differ.py`                                           | `from arrconf.differ import Action, PlannedAction, reconcile` + call                                      | WIRED    | Import at line 22; `reconcile()` called at line 132 with proper kwargs (current=, desired=, match_key, prune, managed_tag_id).    |
| `arrconf/reconcilers/sonarr.py`                                 | `arrconf/resources/sonarr/tag.py`                             | `Tag.model_validate(client.get('/tag'))`                                                                  | WIRED    | Import at line 24; called at lines 50, 59 (`Tag.model_validate`).                                                                  |
| `arrconf/client_base.py`                                        | `arrconf/exceptions.py`                                       | `raise AuthError / NotFoundError / ServerError`                                                            | WIRED    | Import at line 24; `raise` calls at lines 76, 78, 80.                                                                              |
| `arrconf/resources/sonarr/{quality_profile,...}.py` (×4)        | `arrconf/exceptions.py`                                       | `raise ScopeViolationError(...)` BEFORE any HTTP import                                                    | WIRED    | All 4 modules import only `ScopeViolationError` and raise immediately. Verified by `test_scope_violation_raises_BEFORE_any_http_call` with respx call-count assertion (12 tests). |
| `examples/baseline-sonarr.yml`                                  | `schemas/arrconf-schema.json`                                 | yaml-language-server modeline (relative path)                                                              | WIRED    | Line 1 exactly `# yaml-language-server: $schema=../schemas/arrconf-schema.json` (matched by `head -1 | grep -qF`).                |
| `.github/workflows/tests.yml`                                   | `schemas/arrconf-schema.json`                                 | `arrconf schema-gen --output ../../schemas/arrconf-schema.json && git diff --exit-code`                    | WIRED    | tests.yml lines 49-56 — D-15 reproducibility gate; verified locally to be byte-identical.                                          |
| `.github/workflows/arrconf-image.yml`                           | `tools/arrconf/Dockerfile`                                    | `docker/build-push-action@v5` with `file: tools/arrconf/Dockerfile`                                       | WIRED    | arrconf-image.yml lines 36-39.                                                                                                     |

### Data-Flow Trace (Level 4)

| Artifact                              | Data Variable                          | Source                                                              | Produces Real Data | Status     |
| ------------------------------------- | -------------------------------------- | ------------------------------------------------------------------- | ------------------ | ---------- |
| `examples/baseline-sonarr.yml`        | `apps.sonarr.main.download_clients.items` | Phase 0 baseline snapshot — `snapshots/baseline-2026-05-07/sonarr/downloadclient.json` (sanitised) | Yes                | FLOWING    |
| `tools/arrconf/tests/fixtures/sonarr/downloadclient.json` | fixture seed                       | Snapshot copy (Phase 0); ***REDACTED*** placeholders                | Yes                | FLOWING    |
| `schemas/arrconf-schema.json`         | $defs.DownloadClient.properties.*.description | pydantic Field(description=...) on `arrconf/resources/sonarr/download_client.py` | Yes (8/15 props)   | FLOWING    |
| `tools/arrconf/arrconf/dump.py`       | `items_dumped`                         | `client.get("/downloadclient")` → `DownloadClient.model_validate(x)` → `model_dump(exclude_none=True)` | Yes (live API)     | FLOWING    |
| `tools/arrconf/arrconf/config.py`     | `RootConfig`                           | ruyaml YAML loader → pydantic `model_validate`                      | Yes                | FLOWING    |

### Behavioral Spot-Checks

| Behavior                                                  | Command                                                                                                | Result                                                  | Status |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------- | ------ |
| arrconf CLI exposes 4 subcommands                         | `uv run arrconf --help`                                                                                | Lists `apply`, `dump`, `diff`, `schema-gen`             | PASS   |
| pytest passes with coverage gate ≥ 70%                    | `uv run pytest --cov --cov-fail-under=70`                                                              | 52 passed; 99% combined; gate green                     | PASS   |
| ruff lint passes                                          | `uv run ruff check .`                                                                                  | "All checks passed!"                                    | PASS   |
| ruff format check                                         | `uv run ruff format --check .`                                                                         | "35 files already formatted"                            | PASS   |
| mypy --strict passes                                      | `uv run mypy arrconf`                                                                                  | "Success: no issues found in 25 source files"           | PASS   |
| schema-gen reproduces committed schema byte-for-byte      | `uv run arrconf schema-gen --output /tmp/regen.json && diff /tmp/regen.json schemas/arrconf-schema.json` | Files identical                                         | PASS   |
| schemas/arrconf-schema.json declares Draft 2020-12        | `python -c "json.load(...)['$schema']"`                                                                | `https://json-schema.org/draft/2020-12/schema`          | PASS   |
| baseline-sonarr.yml modeline is line 1                    | `head -1 examples/baseline-sonarr.yml`                                                                 | `# yaml-language-server: $schema=../schemas/arrconf-schema.json` | PASS   |
| baseline-sonarr.yml loads via load_config                 | `python -c "from arrconf.config import load_config; load_config(Path('examples/baseline-sonarr.yml'))"` | Loads cleanly; 1 qBit DC, 14 fields                     | PASS   |
| GHCR workflow YAML parses                                 | (visual inspection of arrconf-image.yml)                                                               | Valid GHA workflow with `permissions: contents:read, packages:write` | PASS |
| tests.yml schema-regen gate present                       | grep `git diff --exit-code schemas/arrconf-schema.json` `.github/workflows/tests.yml`                  | Match at line 55                                        | PASS   |
| tests.yml D-13 step ordering (lint → format → mypy → tests) | inspection of `.github/workflows/tests.yml`                                                          | Steps in correct order at lines 37-47                   | PASS   |
| Image NOT yet pushed to GHCR (push to main not triggered) | (cannot verify without GHCR API access; inspecting workflow definition)                                | Workflow ready; push-to-main pending                    | SKIP (human) |
| VS Code interactive autocomplete                          | (cannot run editor in CI)                                                                              | All prerequisites verified; editor demo manual          | SKIP (human) |

### Requirements Coverage

| Requirement              | Source Plan(s)         | Description                                                                         | Status     | Evidence                                                                                                                                                                                          |
| ------------------------ | ---------------------- | ----------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| REQ-cli-subcommands      | 01-01, 01-03           | 4 sous-commandes (apply/dump/diff/schema-gen) + exit codes 0/1/2/3                  | SATISFIED  | All 4 typer commands wired in `__main__.py` with exit codes per CLAUDE.md (apply: 0/1/2; dump: 0/1/2; diff: 0/1/2/3; schema-gen: 0). `test_help_lists_four_subcommands` + 8 other CLI tests pass. |
| REQ-yaml-autocomplete    | 01-03                  | Draft 2020-12 schema + modeline + descriptions (CI bloque si oublié)                | SATISFIED (artifacts) / NEEDS HUMAN (interactive demo) | Schema verified Draft 2020-12; descriptions present (`test_schema_includes_download_client_descriptions` passes); modeline line 1 exact; CI gate in tests.yml. Editor rendering = human_verification[1]. |
| REQ-idempotence          | 01-02, 01-03           | Round-trip dump→apply --dry-run = 0 action; tests add/update/delete/no-op            | SATISFIED  | `test_round_trip_dump_apply_dry_run_is_noop` + `test_dump_apply_no_op` (W2) + `test_committed_baseline_yaml_loads`. 9 differ tests cover all 6 Action cases including no-op.                     |
| REQ-prune-opt-in         | 01-02                  | `prune: false` default, opt-in par section, log sans supprimer                       | SATISFIED  | `DownloadClientsSection.prune: bool = False` default; `differ.reconcile` returns PRUNE_SKIP when prune=False; `test_prune_skip_when_prune_false` + `test_prune_skip_default` lock behavior.       |
| REQ-managed-tag          | 01-02                  | Toute ressource créée par arrconf reçoit `arrconf-managed`; tag réconcilié first    | SATISFIED  | `_ensure_managed_tag()` runs FIRST in `reconcile_sonarr` (Pitfall 3); `_ensure_managed_tag_in_desired()` stamps tag on every desired DC (D-02); 5 managed_tag tests cover lifecycle.            |
| REQ-test-coverage        | 01-01, 01-02, 01-03    | ≥ 70% on differ + reconcilers; respx mocks; CI bloque si < 70%                       | SATISFIED  | 99% combined (100% differ + 98% sonarr); gate enforced in pyproject.toml + tests.yml. All HTTP mocked via respx (zero live calls confirmed by code grep).                                       |
| REQ-app-coverage (Sonarr download_clients only) | 01-01, 01-02, 01-03 | Sonarr download_clients fully implemented end-to-end                             | SATISFIED  | DownloadClient pydantic model (14 fields), reconcile_sonarr orchestrator, 7 reconciler tests, end-to-end via CLI verified.                                                                       |

**All 7 requirement IDs from the phase scope are SATISFIED.** No orphaned requirements (REQUIREMENTS.md maps Phase 1 to exactly the 7 IDs declared in plan frontmatters).

### Anti-Patterns Found

The phase code is exceptionally clean. The pre-existing 01-REVIEW.md identified 6 warnings + 5 info issues — all classified by the reviewer as non-blocking for Phase 1 shipping. Re-checking those in this verification:

| File                                                  | Line(s)        | Pattern                                                                       | Severity | Impact                                                                                                                                  |
| ----------------------------------------------------- | -------------- | ----------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `arrconf/client_base.py`                              | 75-82          | WR-01: 4xx (other than 401/404) raises `httpx.HTTPStatusError` (uncaught)     | Warning  | Non-blocker for Phase 1; affects edge-case error reporting (e.g. 422 on bad configContract). Documented in 01-REVIEW.md.                |
| `arrconf/__main__.py`                                 | 40-42, 87-181  | WR-02: `--apps typo` silently no-ops with exit 0                              | Warning  | Non-blocker for Phase 1 (single-app POC); will become confusing in Phase 3 when more apps are added. Documented.                         |
| `arrconf/reconcilers/sonarr.py`                       | 55-61, 122-138 | WR-03: dry-run with missing managed tag stamps sentinel id=-1 → spurious diff | Warning  | Non-blocker for the *committed* round-trip artifact (which has tag=1 in fixture); affects first-time `arrconf diff` against a virgin Sonarr. Documented. |
| `arrconf/dump.py`                                     | 31, 66-85      | WR-04: hardcoded modeline path; only valid for `examples/<file>.yml`          | Warning  | Phase 4 TODO documented at module top; Phase 1 ROADMAP only requires `examples/baseline-sonarr.yml` which is the path the constant supports. |
| `arrconf/settings.py`                                 | 19             | WR-05: `case_sensitive=False` lets lowercased env vars also bind              | Warning  | Design tradeoff documented in CLAUDE.md mismatch; non-blocker (intentional choice, addresses bug surfaced in W1→W3).                   |
| `.github/workflows/tests.yml`                         | 64             | WR-06: fixture-audit `""` exclusion never matches due to shell quoting        | Warning  | Dead-code today (the `{20,}` quantifier renders the exclusion unnecessary); becomes problematic if regex tightens. Documented.          |
| `tools/arrconf/tests/fixtures/sonarr/edge_cases/*.json` | -            | IN-01: 3 edge-case fixtures committed but not referenced by any test          | Info     | `downloadclient_empty.json`, `downloadclient_partial_response.json`, `downloadclient_with_unmanaged_tag.json` — committed dead fixtures. Non-functional. |
| `arrconf/differ.py`                                   | 19-25, 50-54   | IN-02: `_READ_ONLY_FIELDS` set duplicates `Field(exclude=True)` per-model     | Info     | Belt-and-suspenders; minor maintenance overhead.                                                                                        |
| `arrconf/reconcilers/sonarr.py`                       | 89, 94-96, 103-104 | IN-03: `assert` for runtime invariants (stripped under `-O`)              | Info     | Latent (Dockerfile + GHA don't use `-O`).                                                                                               |
| `arrconf/dump.py`                                     | 69-72          | IN-04: brittle docstring magic-string contract for log hint                   | Info     | Coupling between log hint and downstream grep.                                                                                          |
| `tools/arrconf/README.md`                             | 97             | IN-05: unicode `é` in markdown anchor link                                    | Info     | Cosmetic.                                                                                                                               |

**None of these block phase 1 shipping.** All 11 issues are documented in 01-REVIEW.md with concrete fixes; the gsd-code-reviewer status is `issues_found` (not `blockers_found`). They become Phase 2/3 follow-ups.

### Threat Model Mitigations

All 7 STRIDE threats from the plans are mitigated and tested. Summary verified against codebase:

| ID      | Severity | Status      | Verification                                                                                                                                          |
| ------- | -------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-01-01 | MEDIUM   | mitigated   | `Settings.sonarr_api_key: SecretStr | None`; `pretty_exceptions_show_locals=False` on typer app; `missing_api_key` event surfaces absence. Tested by 3 CLI tests. |
| T-01-02 | HIGH     | mitigated   | Dockerfile line 38 `USER 1000:1000`; multi-stage with non-root user creation.                                                                          |
| T-01-03 | MEDIUM   | mitigated   | `arrconf-image.yml` permissions exactly `{ contents: read, packages: write }`; PR builds skip GHCR login via conditional `if: github.event_name != 'pull_request'`. |
| T-01-04 | HIGH     | mitigated   | Two-line defense: `prune: false` default + managed-tag-gated DELETE in `differ.reconcile`. 4 tests lock the gate (test_prune_protected_*, test_no_managed_tag_id_treats_as_protected). |
| T-01-05 | HIGH     | hardened    | 4 frontière modules raise `ScopeViolationError` before any httpx import; respx-asserted call_count == 0 test confirms (12 parametrized tests).        |
| T-01-06 | LOW      | accepted    | No `verify=False` anywhere; httpx default `verify=True`.                                                                                              |
| T-01-07 | MEDIUM   | mitigated   | CI fixture audit step in tests.yml + W1 redaction discipline. Note WR-06 edge case in audit regex (non-blocker, dead exclusion).                       |

### Human Verification Required

#### 1. GHCR public visibility toggle

**Test:** After first push to main (or first `v*` tag), verify `ghcr.io/tom333/arr-stack-arrconf:sha-<short>` is publicly pullable.
**Expected:**
1. Visit https://github.com/users/tom333/packages/container/arr-stack-arrconf/settings
2. Scroll to "Danger Zone" → "Change visibility" → select **Public**
3. Confirm. From now on, anonymous pulls work: `docker pull ghcr.io/tom333/arr-stack-arrconf:sha-<short>` succeeds.

**Why human:** GHCR public-visibility is a one-time UI step; not automatable via gh CLI as of 2026-04 (Pitfall 7). Workflow `arrconf-image.yml` is verified correct — least privilege, correct tag template, references the multi-stage Dockerfile.

#### 2. VS Code autocomplete demo

**Test:** Open `examples/baseline-sonarr.yml` in VS Code (or code-server) with the Red Hat YAML extension installed.
**Expected:**
1. Bottom-right indicator shows "YAML" with the schema attached (modeline picked up).
2. Cursor positioned under `download_clients:` and pressing space — VS Code suggests `prune:` and `items:` with descriptions sourced from pydantic `Field(description=...)`.
3. Hover over `protocol:` — tooltip shows the pydantic docstring.
4. Type an invalid value (e.g. `protocol: ftp`) — red squiggle from JSON Schema validation.

**Why human:** Editor-rendering is interactive and not automatable here. All artifact-level prerequisites verified: schema is Draft 2020-12, descriptions present on DownloadClient (8/15 props), modeline is line 1 of YAML.

#### 3. Live round-trip against real Sonarr

**Test:** Port-forward Sonarr from my-kluster, then:
```bash
export SONARR_API_KEY=<from secret>
kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
cd tools/arrconf
uv run arrconf dump --apps sonarr --output ../../examples/baseline-sonarr.yml
uv run arrconf --config ../../examples/baseline-sonarr.yml diff --apps sonarr
# expect exit 0
uv run arrconf --config ../../examples/baseline-sonarr.yml apply --apps sonarr --dry-run
# expect exit 0 + "no-op" log
```
**Expected:** Exit codes 0 + 0; `diff` logs `no_drift` event; `apply --dry-run` logs `no-op` event.

**Why human:** Requires live Sonarr instance + SONARR_API_KEY; engine-level round-trip is locked by `test_round_trip_dump_apply_dry_run_is_noop` (respx-mocked). Live cluster verification belongs to Phase 2 (cluster validation).

### Gaps Summary

**No gaps blocking goal achievement.** All 6 ROADMAP success criteria are met at the artifact + code level; 4/6 fully verified programmatically, 2/6 require interactive human verification (GHCR public toggle, VS Code editor demo). The 3rd success criterion (live round-trip) is engine-verified; live cluster verification is the natural domain of Phase 2.

The 11 issues identified in 01-REVIEW.md are pre-existing warnings/info-level findings — none are blockers, all have documented fixes deferred to Phase 2/3.

**Phase 1 goal is achieved in the codebase. Recommended status: `human_needed`** — to surface the 2 manual verifications (GHCR public toggle, VS Code demo) and 1 deferred-to-Phase-2 verification (live round-trip) before the orchestrator marks Phase 1 fully complete.

---

_Verified: 2026-05-07T11:59:51Z_
_Verifier: Claude (gsd-verifier)_
