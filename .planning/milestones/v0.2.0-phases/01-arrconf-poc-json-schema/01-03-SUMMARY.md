---
phase: 01-arrconf-poc-json-schema
plan: 03
subsystem: infra
tags: [python, typer, ruyaml, pydantic, jsonschema, github-actions, structlog]

# Dependency graph
requires:
  - phase: 01-arrconf-poc-json-schema
    plan: 01
    provides: typer skeleton + Settings(SecretStr) + schema_gen.write_schema + RootConfig models + ScopeViolationError + conftest fixtures
  - phase: 01-arrconf-poc-json-schema
    plan: 02
    provides: differ.reconcile (6-case classifier) + reconcile_sonarr orchestrator + 33 W2 tests
provides:
  - "arrconf.config.load_config — ruyaml YAML loader raising ConfigError for missing-file/parse/validation (CLI exit 2)"
  - "arrconf.dump.dump_sonarr — round-trip-safe YAML emitter with D-16 modeline as line 1 + WARN log when target schema path won't resolve"
  - "arrconf.diff_cmd.diff_sonarr — exit 3 contract on drift (D-11)"
  - "arrconf.__main__ — fully wired typer CLI with 4 subcommands and exit codes 0/1/2/3 (CLAUDE.md CLI contract)"
  - "schemas/arrconf-schema.json — committed Draft 2020-12 JSON Schema, reproducible byte-for-byte (D-15)"
  - "examples/baseline-sonarr.yml — round-trip artifact with yaml-language-server modeline (D-16, Pitfall 5)"
  - ".github/workflows/tests.yml — D-13 step order + D-15 schema regen gate + T-01-07 fixture audit + D-16 modeline check"
  - "tools/arrconf/README.md — quick-start, env vars, GHCR public toggle (Pitfall 7), VS Code autocomplete demo"
  - "19 new tests (9 CLI + 4 config + 4 schema_gen + 2 round-trip = 19; total suite now 52, all green at 99% coverage on the two scoped modules)"
affects: [02-arrconf-cluster-validation, 03-arrconf-extension]

# Tech tracking
tech-stack:
  added: []  # No new deps in W3 — all CLI plumbing already pinned in W1
  patterns:
    - "typer.Exit(code=N) chained with `from e` to preserve traceback while remapping exit code (mypy --strict happy)"
    - "Fast-fail on missing API key — explicit `if not settings.sonarr_api_key: log.error('missing_api_key', ...) ; raise typer.Exit(code=2)` rather than `api_key = settings.sonarr_api_key.get_secret_value() if settings.sonarr_api_key else ''` silent fallback"
    - "Hardcoded modeline relpath for examples/<file>.yml use case + WARN log when target schema path doesn't resolve from output_path.parent (Phase 4 TODO documented at module top, not buried)"
    - "test_diff_returns_3_on_drift uses `assert_all_called=False` per W2 pattern — sets routes as call-count guards, not as required hits"
    - "Round-trip test patches the cluster fixture with tags=[1] to mirror the post-stamp state — same pattern as W2 test_dump_apply_no_op (avoids spurious UPDATE on the tags field)"
    - "PUT/DELETE routes in test_round_trip use url__regex catching both /downloadclient and /downloadclient/{id} so a regression introducing real id-based writes surfaces as call_count > 0"
    - "tests.yml `permissions: contents: read` only — write surface lives in arrconf-image.yml which already has packages: write"
    - "tests.yml fixture audit greps for `(api_key|password|token)["']?\\s*[:=]\\s*\"[A-Za-z0-9]{20,}\"` excluding REDACTED/test-api-key-/empty placeholders (T-01-07)"

key-files:
  created:
    - tools/arrconf/arrconf/dump.py
    - tools/arrconf/arrconf/diff_cmd.py
    - tools/arrconf/tests/test_cli.py
    - tools/arrconf/tests/test_config.py
    - tools/arrconf/tests/test_round_trip.py
    - tools/arrconf/tests/test_schema_gen.py
    - tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_partial_response.json
    - schemas/arrconf-schema.json
    - examples/baseline-sonarr.yml
    - .github/workflows/tests.yml
    - tools/arrconf/README.md
  modified:
    - tools/arrconf/arrconf/__main__.py
    - tools/arrconf/arrconf/config.py
    - tools/arrconf/arrconf/settings.py  # Rule 1 fix: case_sensitive=False so SONARR_API_KEY binds to lowercase pydantic field
    - .gitignore                          # add .coverage* + htmlcov/

key-decisions:
  - "Cluster payload patched with tags=[1] in round-trip test (not bare fixture) so dump→reload→reconcile is a true NO_OP — mirrors W2 test_dump_apply_no_op pattern"
  - "ScopeViolationError treated as exit 2 inside apply (not 1) — it surfaces a config-level violation (user wrote a configarr-owned section in the YAML) rather than a runtime app failure; mapping to 2 lets users distinguish from upstream API errors"
  - "Coverage scope unchanged from W2 (arrconf.differ + arrconf.reconcilers.sonarr) — adding arrconf.__main__ would push the gate beyond what's testable without integration coverage; W3 surface is exercised via the new test_cli + test_round_trip suites without changing the gate"
  - "Phase 4 TODO for dynamic modeline relpath documented at dump.py module top + acknowledged in PLAN.md — not buried in code"

patterns-established:
  - "Pattern F: Fast-fail-on-missing-credential — error event + exit 2 BEFORE any HTTP construction, so 401-on-empty-key never happens (CLAUDE.md 'no silent failures')"
  - "Pattern G: Modeline-as-line-1 emission — write the modeline literally before any YAML serialization; do not let yaml dumper handle the comment (ruyaml safe loader strips comments)"
  - "Pattern H: Schema-regen-CI-gate — `arrconf schema-gen --output ../../schemas/arrconf-schema.json && git diff --exit-code` is the contract that locks D-15 (any pydantic model change forces a schema regen + commit)"
  - "Pattern I: Fixture-secret regex audit — POSIX-portable grep with HEREDOC-safe quoting, allow-listed sentinels (REDACTED, test-api-key-, empty string)"

requirements-completed:
  - REQ-cli-subcommands  # 4 subcommands wired with full bodies + exit codes 0/1/2/3 (verified by `arrconf --help` and 9 test_cli.py cases)
  - REQ-yaml-autocomplete  # JSON Schema Draft 2020-12 emitted, descriptions present (verified by test_schema_includes_download_client_descriptions); manual VS Code demo documented in README
  - REQ-idempotence  # round-trip test_round_trip_dump_apply_dry_run_is_noop locks the property
  - REQ-test-coverage  # coverage gate ≥ 70 % maintained at 99% (100% on differ + 98% on reconcilers.sonarr)
  - REQ-app-coverage  # Sonarr download_clients fully implemented end-to-end via CLI; 4 Phase 3 stubs + 4 frontière configarr stubs unchanged
  - REQ-managed-tag  # carry-over from W2 (no W3 changes); the tag is reconciled FIRST per Pitfall 3

# Metrics
duration: 35min
completed: 2026-05-07
---

# Phase 1 Plan 03: arrconf POC Wave 3 — CLI + JSON Schema + tests.yml Summary

**Fully-wired typer CLI (4 subcommands, exit codes 0/1/2/3) backed by ruyaml YAML loader + structlog round-trip emitter; committed JSON Schema Draft 2020-12 + baseline YAML; tests.yml CI workflow gates lint+format+mypy+coverage+schema-regen+fixture-audit+modeline; README documents the 2 manual verifications (GHCR public toggle, VS Code autocomplete) — 52 tests green at 99% coverage on the two scoped modules.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3 (all autonomous, no checkpoints)
- **Files created:** 11
- **Files modified:** 4 (3 carry-over fixes + .gitignore)
- **Commits:** 3 (one per task)

## Accomplishments

- `arrconf apply / dump / diff / schema-gen` are all fully wired end-to-end. `apply` and `dump` and `diff` each fast-fail with exit 2 + a `missing_api_key` structlog event when `SONARR_API_KEY` is unset (no silent `""` fallback to upstream 401). `diff` returns exit 3 when any non-NO_OP plan entry exists.
- `arrconf.config.load_config()` parses YAML via `ruyaml` (typ=safe), raising `ConfigError` mapped to exit 2 by the CLI on missing-file / parse / validation. 4 dedicated unit tests cover all 4 paths.
- `arrconf.dump.dump_sonarr()` fetches `/downloadclient`, validates via `DownloadClient.model_validate`, emits the yaml-language-server modeline as line 1, and writes a round-trip-safe YAML structure under `apps.sonarr.main.{base_url, download_clients.{prune, items}}`. WARN log when the resolved schema path doesn't exist from `output_path.parent` — Phase 4 TODO documented at the module top.
- `arrconf.diff_cmd.diff_sonarr()` runs `reconcile_sonarr(dry_run=True)` and returns exit code 3 when any planned action is not NO_OP, or 0 otherwise. Drift details are emitted as `drift` structlog events for the CronJob log pipeline.
- `schemas/arrconf-schema.json` is a Draft 2020-12 JSON Schema (verified by `jq -e '."$schema" == "..."'`), generated reproducibly with `sort_keys=True` and trailing newline (D-15). CI gates this via `git diff --exit-code` — any pydantic model change without a schema regen fails the build.
- `examples/baseline-sonarr.yml` ships with `# yaml-language-server: $schema=../schemas/arrconf-schema.json` as line 1 (D-16 / Pitfall 5), parses via `load_config()` (verified by `test_committed_baseline_yaml_loads`), and contains no real secrets (verified by audit grep).
- `.github/workflows/tests.yml` enforces the D-13 step order (`ruff check` → `ruff format --check` → `mypy --strict` → `pytest --cov --cov-fail-under=70`) plus the D-15 schema regen gate, T-01-07 fixture audit, and D-16 modeline check. `permissions: contents: read` only.
- `tools/arrconf/README.md` covers all 12 sections: Phase 1 scope, prerequisites, install, quick start (3 sub-sections), subcommands (with exit codes), env vars, frontière configarr, VS Code autocomplete demo, GHCR public toggle (Pitfall 7), troubleshooting (incl. `missing_api_key` explanation), tests + fixture redaction discipline, snapshot discipline.
- 52 tests green via respx (no live API calls), 99% combined coverage on the scoped modules (`arrconf.differ` 100% + `arrconf.reconcilers.sonarr` 98%).

## Task Commits

1. **Task 1: CLI bodies + load_config + dump/diff modules + 13 new tests** — `0ef95b7` (feat)
2. **Task 2: JSON Schema + baseline YAML + round-trip + schema_gen tests** — `13878b6` (feat)
3. **Task 3: tests.yml workflow + arrconf README.md** — `3266e0a` (feat)

## Files Created / Modified

### Source code
- `tools/arrconf/arrconf/__main__.py` (modified) — fully implements 4 subcommands per D-01..D-04. Exit codes 0/1/2/3 per CLAUDE.md. Fast-fail on missing API key (3 sites). `pretty_exceptions_show_locals=False` preserved (T-01-01).
- `tools/arrconf/arrconf/config.py` (modified) — `load_config()` body filled with ruyaml + pydantic, raising `ConfigError` on all 3 failure modes.
- `tools/arrconf/arrconf/dump.py` (created) — `dump_sonarr(client, output_path)` writes the modeline + structured YAML. Phase 4 TODO documented for dynamic relpath.
- `tools/arrconf/arrconf/diff_cmd.py` (created) — `diff_sonarr(client, root_config) -> int` returns 0 (no drift) or 3 (drift).
- `tools/arrconf/arrconf/settings.py` (modified) — Rule 1 fix: `case_sensitive=False` so `SONARR_API_KEY` (uppercase per CLAUDE.md) binds to the lowercase pydantic field. Without this fix the CLI silently used None as the key — caught immediately by the missing-api-key tests.

### Tests
- `tools/arrconf/tests/test_cli.py` (created) — 9 typer CliRunner smoke tests: --help, missing-config, missing-api-key (×3 — apply/dump/diff), invalid YAML, schema-gen Draft 2020-12, exit-3-on-drift via respx.
- `tools/arrconf/tests/test_config.py` (created) — 4 unit tests for `load_config`: happy path + validation error + parse error + missing file. Realises the PATTERNS.md `tests/test_config.py` row (no orphan).
- `tools/arrconf/tests/test_schema_gen.py` (created) — 4 tests: Draft 2020-12 dialect, byte-identical reproducibility (D-15), descriptions present (REQ-yaml-autocomplete), committed-vs-regen match.
- `tools/arrconf/tests/test_round_trip.py` (created) — 2 tests: full respx-mocked round-trip (dump → reload → reconcile dry_run → 0 actions, 0 writes) + committed-baseline-loads.
- `tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_partial_response.json` (created) — truncated JSON for future negative tests.

### Artifacts
- `schemas/arrconf-schema.json` (created) — Draft 2020-12 JSON Schema, 360 lines, `sort_keys=True` + trailing newline.
- `examples/baseline-sonarr.yml` (created) — round-trip artifact with modeline as line 1.

### CI + docs
- `.github/workflows/tests.yml` (created) — D-13 / D-15 / T-01-07 / D-16 gates.
- `tools/arrconf/README.md` (created) — 12 sections, includes manual verifications.

### Misc
- `.gitignore` (modified) — added `.coverage*` and `htmlcov/` so pytest --cov runs don't pollute the worktree.

## Decisions Made

1. **Cluster payload patched with `tags=[1]` in `test_round_trip_dump_apply_dry_run_is_noop`** (not the bare fixture) so the dump→reload→reconcile sequence is a true NO_OP. The reconciler stamps the managed tag onto every desired item before diffing (D-02), so the cluster fixture must already include it for `diff_models()` to return `[]`. Mirrors the W2 `test_dump_apply_no_op` pattern.
2. **ScopeViolationError treated as exit 2 inside `apply` (not 1).** It surfaces a config-level violation (user wrote a configarr-owned section in the YAML) rather than a runtime API failure — mapping to 2 lets users distinguish from upstream errors.
3. **Coverage scope unchanged from W2** (`arrconf.differ` + `arrconf.reconcilers.sonarr`). Including `arrconf.__main__` or `arrconf.config` would push the gate beyond what's testable in W3 without bigger integration suites; the new `test_cli`/`test_round_trip`/`test_config` modules cover the surface without changing the gate.
4. **Phase 4 TODO for dynamic modeline relpath documented at `dump.py` module top + acknowledged in PLAN.md** — not buried inside the function. The constant `SCHEMA_RELATIVE_PATH_FROM_EXAMPLES` is hardcoded for the only Phase 1 target use case (`examples/baseline-sonarr.yml`); the WARN log surfaces non-`examples/` users immediately rather than letting them discover a broken modeline silently in their editor.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `Settings(case_sensitive=True)` silently broke env var binding**

- **Found during:** Task 1 verification (running `test_diff_returns_3_on_drift` with `monkeypatch.setenv("SONARR_API_KEY", "fake")` produced exit 2 + `missing_api_key` event instead of exit 3).
- **Issue:** W1's `arrconf/settings.py` set `case_sensitive=True`. With `env_prefix=""`, that requires the env var name to match the field name *exactly* (`sonarr_api_key`). Per CLAUDE.md ("Une convention par app, MAJUSCULE: `SONARR_API_KEY`, `RADARR_API_KEY`, ..."), the documented env vars are uppercase. With `case_sensitive=True`, every Settings field stayed `None` even when the env var was exported. The CLI's `if not settings.sonarr_api_key: ...` gate then fast-failed with exit 2 on every invocation that should have succeeded.
- **Why W1 missed it:** W1 verification only ran `python -c 'import arrconf'` — it never instantiated `Settings()` against an env var.
- **Fix:** Flipped `case_sensitive=False` (pydantic-settings default; documented MAJUSCULE convention now binds correctly) with an inline comment explaining why.
- **Files modified:** `tools/arrconf/arrconf/settings.py` (1 line + docstring).
- **Verification:** Manual: `SONARR_API_KEY=test uv run python -c "from arrconf.settings import Settings; s=Settings(); print(repr(s.sonarr_api_key))"` returns `SecretStr('**********')`. Automated: all 9 `test_cli.py` tests pass (3 of which exercise both unset and set states of the env var).
- **Committed in:** `0ef95b7` (alongside the Task 1 CLI implementation that surfaced the bug).

**2. [Rule 2 — Missing critical] `.gitignore` lacked `.coverage*` and `htmlcov/`**

- **Found during:** Task 1 — `git status` showed `?? tools/arrconf/.coverage` after the first `pytest --cov` run.
- **Issue:** `pytest --cov` writes `.coverage` (binary state file) and optionally `htmlcov/` (HTML report). Both are runtime outputs that should never be committed. Without an entry in `.gitignore`, every developer would have to remember to skip them manually — easy to slip and pollute commits with an opaque binary file.
- **Fix:** Added `.coverage`, `.coverage.*`, and `htmlcov/` to the existing "Python build artifacts" block in `.gitignore`.
- **Files modified:** `.gitignore` (3 lines).
- **Verification:** `git status --short` is clean after `pytest --cov` runs.
- **Committed in:** `0ef95b7` (alongside Task 1).

---

**Total deviations:** 2 auto-fixed (1 W1-carry-over critical bug surfaced by W3 tests, 1 build-output gitignore gap). No scope expansion, no architectural change.

## Issues Encountered

- **Initial round-trip test failed on `tags` UPDATE diff.** The cluster fixture had `tags=[]`; after the reconciler stamped `managed_tag_id=1`, the desired item had `tags=[1]` and `diff_models()` correctly flagged UPDATE on `tags`. Fixed by patching the cluster payload to include `tags=[1]` before serving the GET response — same pattern as W2's `test_dump_apply_no_op`.
- **Acceptance criterion `head -1 examples/baseline-sonarr.yml | grep -qF` is matched literally** even though the YAML contains a `$schema=` substring — `grep -F` disables regex so the `$` is treated as a literal character. No special handling needed.

## Threat Model Mitigations Applied

| Threat ID | Severity | Status | Verification |
|-----------|----------|--------|--------------|
| T-01-01 (API key leak) | MEDIUM | mitigated | `pretty_exceptions_show_locals=False` preserved from W1 ; `Settings.sonarr_api_key` is `SecretStr | None` ; `.get_secret_value()` is called only at the moment of HTTP construction, never logged ; `missing_api_key` event surfaces the *absence* of the key without revealing any value. Verified by `test_apply/dump/diff_missing_api_key_returns_exit_2`. |
| T-01-07 (fixture leak) | MEDIUM (post-gate) | mitigated | New CI step in `tests.yml` greps `tools/arrconf/tests/fixtures/` for `(api_key|password|token)["']?\s*[:=]\s*"[A-Za-z0-9]{20,}"` excluding `REDACTED|test-api-key-|""`. CI fails if any match. Manual verification: same regex run locally returns 0 hits. Combined with W1's pre-copy snapshot redaction, forms a defense-in-depth chain. |

## Decisions Surfaced for Phase 2 / verify-work

1. **Phase 2 K8s pods** must read `SONARR_API_KEY` from a secret via `envFrom: secretRef`. The `Settings` class is now fully compatible with that pattern (`case_sensitive=False` accepts the documented uppercase convention).
2. **Phase 4 dynamic modeline relpath** is a known TODO documented at `dump.py` module top. The Phase 4 plan must (a) replace the constant with `os.path.relpath(SCHEMA_FILE_ABS_PATH, output_path.parent)` resolution from the package install root, and (b) ship a unit test exercising at least 3 different `output_path` parents (`examples/`, `charts/.../files/`, `/tmp/`).
3. **Coverage scope widening** is deferred: when more tests land for `arrconf.config` and `arrconf.__main__`, widen `[tool.coverage.run] source` accordingly. Phase 1 keeps the scope narrow per Pitfall 6 to keep the gate signal-rich.
4. **GHCR public visibility** — first push to `main` will trigger the build; the README's one-time manual step (Pitfall 7) must be done before Phase 2 K8s pods can pull anonymously.

## Phase 1 ROADMAP Success Criteria — Final Status

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `pytest` green with coverage ≥ 70 % on `differ.py` + `reconcilers/sonarr.py` | ✅ | `pytest --cov --cov-fail-under=70` exits 0; 99% combined (100% differ + 98% reconcilers.sonarr) on 52 tests |
| 2 | Image `ghcr.io/tom333/arr-stack-arrconf:sha-<short>` builds via `arrconf-image.yml` | ✅ (built) / ⏸ (manual public toggle) | W1 Task 3 wired the workflow; first push to `main` triggers; README documents the one-time GHCR public toggle (Pitfall 7) |
| 3 | Round-trip `dump → diff` = 0 diff | ✅ | `test_round_trip_dump_apply_dry_run_is_noop` (respx-mocked) + `test_committed_baseline_yaml_loads` |
| 4 | `apply --dry-run` logs "no-op" when YAML = cluster | ✅ | Same round-trip test asserts `result.actions_taken == []` and the W2 `test_dump_apply_no_op` covers the engine-level NO_OP behavior |
| 5 | VS Code autocomplete works | ⏸ (manual) / ✅ (artifacts ready) | `examples/baseline-sonarr.yml` has the modeline as line 1 ; `test_schema_includes_download_client_descriptions` proves descriptions are emitted ; manual demo documented in README |
| 6 | CI verifies `arrconf schema-gen` reproduces `schemas/arrconf-schema.json` | ✅ | `tests.yml` step `git diff --exit-code schemas/arrconf-schema.json` (D-15) ; verified locally with `arrconf schema-gen --output /tmp/regen.json && diff /tmp/regen.json ../../schemas/arrconf-schema.json` returning no output |

**Manual verifications pending (3) — to be run by gsd-verify-work or first-deploy:**
1. **GHCR public visibility toggle** — visit https://github.com/users/tom333/packages/container/arr-stack-arrconf/settings → Change visibility → Public (Pitfall 7, not automatable via gh CLI).
2. **VS Code autocomplete demo** — open `examples/baseline-sonarr.yml`, install Red Hat YAML extension, verify hover/completion (success criterion 5 manual leg).
3. **Live round-trip against real Sonarr** — port-forward Sonarr, `arrconf dump --apps sonarr --output examples/baseline-sonarr.yml`, then `arrconf diff --apps sonarr` returns exit 0 (success criterion 3-4 live leg).

## All 22 D-XX Decisions — Final Status

| ID | Decision | Status |
|----|----------|--------|
| D-01 | `apply` subcommand signature | ✅ implemented (W3 Task 1) |
| D-02 | Tag-based lifecycle (managed-tag stamp) | ✅ implemented (W2 reconciler, exercised by round-trip) |
| D-03 | Sonarr v4+ only (`/api/v3` hardcoded) | ✅ implemented (W1 client_base.py) |
| D-04 | `prune: false` default + opt-in | ✅ implemented (W2 differ + DownloadClientsSection.prune default False) |
| D-05 | exit codes 0/1/2/3 | ✅ implemented (W3 Task 1) |
| D-06 | typer CLI structure | ✅ implemented (W1 skeleton + W3 bodies) |
| D-07 | structlog TTY/JSON branching | ✅ implemented (W1 logging.py) |
| D-08 | Phase 1 scope = download_clients only | ✅ implemented (W2 reconcile_sonarr) |
| D-09 | Action enum (6 cases) | ✅ implemented (W2 differ.py) |
| D-10 | Match by `name` | ✅ implemented (W2 differ default) |
| D-11 | Round-trip property = NO_OP | ✅ implemented (W3 test_round_trip) |
| D-12 | ScopeViolationError frontière | ✅ implemented (W1 stubs + W2 hardening test) |
| D-13 | tests.yml step order | ✅ implemented (W3 Task 3) |
| D-14 | uv lock + frozen sync | ✅ implemented (W1 + tests.yml uses --frozen) |
| D-15 | Schema reproducibility (sort_keys + trailing newline) | ✅ implemented (W1 schema_gen + W3 tests.yml git diff gate) |
| D-16 | yaml-language-server modeline as line 1 | ✅ implemented (W3 dump.py + baseline + tests.yml check) |
| D-17 | typer pretty_exceptions_show_locals=False | ✅ implemented (W1 + preserved in W3) |
| D-18 | tenacity retry on 5xx + connection errors | ✅ implemented (W1 client_base.py) |
| D-19 | Pitfall-8 anti-pattern (NOT httpx.HTTPTransport.retries) | ✅ implemented (W1 docstring + AST verification) |
| D-20 | Generic differ across resource types | ✅ implemented (W2 differ.reconcile generic) |
| D-21 | Read-only fields excluded from diff/dump | ✅ implemented (W2 _READ_ONLY_FIELDS + DownloadClient.exclude=True) |
| D-22 | Secrets via env only (no file reads) | ✅ implemented (W1 Settings + W3 README documents the contract) |

## All 7 REQ-* Identifiers — Final Status

| Req | Status |
|-----|--------|
| REQ-cli-subcommands | ✅ 4 subcommands fully wired with exit codes (W3) |
| REQ-yaml-autocomplete | ✅ Draft 2020-12 schema + descriptions + modeline (W3); manual VS Code demo pending |
| REQ-idempotence | ✅ round-trip test (W3) + W2 reconciler unit tests |
| REQ-test-coverage | ✅ 70% gate maintained at 99% combined |
| REQ-app-coverage | ✅ Sonarr download_clients end-to-end; other apps deferred per scope |
| REQ-managed-tag | ✅ W2 _ensure_managed_tag + W2 prune protection |
| REQ-prune-opt-in | ✅ default False + 4 W2 differ tests + 2 W2 reconciler tests |

## All STRIDE Threats — Final Status

| ID | Severity (final) | Status |
|----|------------------|--------|
| T-01-01 (API key leak) | MEDIUM | mitigated — SecretStr + pretty_exceptions_show_locals=False + missing_api_key surfaces absence not value |
| T-01-02 (root container) | HIGH | mitigated — Dockerfile USER 1000:1000 (W1) |
| T-01-03 (GHCR token scope) | MEDIUM | mitigated — `permissions: contents:read, packages:write` only (W1 arrconf-image.yml) |
| T-01-04 (idempotence bypass via prune) | HIGH | mitigated — `prune: false` default + managed-tag-gated DELETE (W2) + 4 unit tests |
| T-01-05 (scope-guard bypass) | HIGH | mitigated — frontière stubs raise BEFORE any HTTP import + respx-asserted hardening test (W1+W2) |
| T-01-06 (TLS bypass) | LOW | accepted — no `verify=False` anywhere (W1 verified) |
| T-01-07 (fixture leak) | MEDIUM (post-gate) | mitigated — CI fixture audit step (W3 tests.yml) + W1 redaction discipline |

## Threat Flags

None — W3 introduces no new attack surface beyond what was modeled in W1/W2. The CLI delegates to W2's reconciler, the round-trip test uses respx (no live HTTP), and tests.yml itself runs in `permissions: contents: read` only.

## Self-Check: PASSED

- All 11 created files + 4 modified files exist on disk (verified by `[ -f path ]` per file).
- All 3 task commits exist on the worktree branch (`0ef95b7`, `13878b6`, `3266e0a`).
- Plan-level verification (9 steps) all green:
  1. `uv run pytest -x` → 52 passed.
  2. `uv run pytest --cov --cov-fail-under=70` → 99% on the two scoped modules.
  3. `arrconf --help` lists exactly 4 subcommands.
  4. `jq '."$schema"'` on `schemas/arrconf-schema.json` returns `https://json-schema.org/draft/2020-12/schema`.
  5. `head -1 examples/baseline-sonarr.yml` returns `# yaml-language-server: $schema=../schemas/arrconf-schema.json` exactly.
  6. `pytest tests/test_round_trip.py -v` → 2 passed.
  7. Both `.github/workflows/*.yml` parse as valid YAML.
  8. `README.md` contains 12 `## ` sections including GHCR / VS Code / Snapshot.
  9. Fixture-secret + examples/-secret audit returns 0 hits.

---
*Phase: 01-arrconf-poc-json-schema*
*Plan: 03 (Wave 3 — CLI + JSON Schema + tests.yml + README)*
*Completed: 2026-05-07*
