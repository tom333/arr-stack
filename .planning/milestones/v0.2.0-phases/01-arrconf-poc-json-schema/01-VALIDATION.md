---
phase: 1
slug: arrconf-poc-json-schema
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-07
last_updated: 2026-05-07
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 01-RESEARCH.md §"Validation Architecture" — populated by gsd-planner during planning.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-cov 7.1.0 + respx 0.23.1 |
| **Config file** | tools/arrconf/pyproject.toml (`[tool.pytest.ini_options]` + `[tool.coverage.run]`) — installed in W1 Plan 01 Task 1 |
| **Quick run command** | `cd tools/arrconf && uv run pytest -x --no-cov` |
| **Full suite command** | `cd tools/arrconf && uv run pytest --cov --cov-fail-under=70` (coverage scoped to `arrconf.differ` + `arrconf.reconcilers.sonarr` per Pitfall 6) |
| **Estimated runtime** | ~5–10 seconds (all respx-mocked, no live HTTP) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (no coverage gate, fast feedback)
- **After every plan wave:** Run full suite command (with coverage gate)
- **Before `/gsd-verify-work`:** Full suite must be green AND coverage ≥ 70 %
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

> Populated during planning (gsd-plan-phase). Each row maps a task to its automated verification command.
> Coverage scope is locked to `arrconf.differ` + `arrconf.reconcilers.sonarr` per Pitfall 6 (pytest-cov has no per-file threshold — global average masks under-coverage).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01-01 | 1 | REQ-test-coverage, REQ-app-coverage | T-01-02, T-01-07 | Multi-stage Dockerfile non-root + redacted fixture seeds | smoke (build + grep) | `cd tools/arrconf && uv sync --frozen && grep -q 'fail_under = 70' pyproject.toml && grep -q 'USER 1000:1000' Dockerfile && test -f tests/fixtures/sonarr/downloadclient.json` | ❌ W1 | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | REQ-test-coverage, REQ-app-coverage | T-01-01, T-01-05 | SecretStr in Settings + scope-violation pre-network in stubs | smoke (import + introspect) | `cd tools/arrconf && uv run python -c 'from arrconf.differ import Action; assert len(list(Action))==6' && uv run mypy arrconf && uv run ruff check . && for m in quality_profile custom_format quality_definition media_naming; do uv run python -c "from arrconf.resources.sonarr import $m; from arrconf.exceptions import ScopeViolationError; \\ntry:\\n    $m.reconcile()\\nexcept ScopeViolationError: pass"; done` | ❌ W1 | ⬜ pending |
| 01-01-T3 | 01-01 | 1 | REQ-cli-subcommands | T-01-03 | GHCR token least-privilege scope | yaml-lint (config) | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/arrconf-image.yml'))" && grep -q 'packages: write' .github/workflows/arrconf-image.yml && ! grep -E '(id-token: write\|actions: write\|write-all)' .github/workflows/arrconf-image.yml` | ❌ W1 | ⬜ pending |
| 01-02-T1 | 01-02 | 2 | REQ-idempotence, REQ-prune-opt-in | T-01-04 | prune-protected when no managed tag (3 dedicated tests) | unit (TDD) | `cd tools/arrconf && uv run pytest tests/test_differ.py -x && uv run pytest --cov=arrconf.differ tests/test_differ.py --cov-fail-under=70` | ❌ W2 | ⬜ pending |
| 01-02-T2 | 01-02 | 2 | REQ-idempotence, REQ-managed-tag, REQ-app-coverage | T-01-04 | Managed-tag-first ordering + tag-IDs-not-names + DELETE only on managed-tagged | unit + integration (respx, TDD) | `cd tools/arrconf && uv run pytest tests/test_reconcilers_sonarr.py tests/test_managed_tag.py -x && uv run pytest --cov --cov-fail-under=70` | ❌ W2 | ⬜ pending |
| 01-02-T3 | 01-02 | 2 | (anchor for REQ-configarr-coexistence Phase 3) | T-01-05 | ScopeViolationError raises BEFORE any httpx call (respx asserts 0 calls) | unit (parametrized × 4 modules) | `cd tools/arrconf && uv run pytest tests/test_scope_violation.py -x -v` | ❌ W2 | ⬜ pending |
| 01-03-T1 | 01-03 | 3 | REQ-cli-subcommands | T-01-01 | typer pretty_exceptions_show_locals=False + SecretStr through Settings + load_config error paths + missing-api-key fast-fail | unit + smoke (typer.CliRunner) | `cd tools/arrconf && uv run pytest tests/test_cli.py tests/test_config.py -x && uv run arrconf --help \| grep -E '(apply\|dump\|diff\|schema-gen)' \| wc -l \| grep -q 4 && grep -q 'missing_api_key' tools/arrconf/arrconf/__main__.py && grep -q 'TODO Phase 4: replace with .os.path.relpath' tools/arrconf/arrconf/dump.py` | ❌ W3 | ⬜ pending |
| 01-03-T2 | 01-03 | 3 | REQ-yaml-autocomplete, REQ-idempotence | (none — quality gate) | Round-trip property + JSON Schema reproducibility | unit + integration (respx) | `cd tools/arrconf && uv run pytest tests/test_round_trip.py tests/test_schema_gen.py -x && jq -e '."\$schema" == "https://json-schema.org/draft/2020-12/schema"' ../../schemas/arrconf-schema.json && head -1 ../../examples/baseline-sonarr.yml \| grep -qF '\$schema=../schemas/arrconf-schema.json'` | ❌ W3 | ⬜ pending |
| 01-03-T3 | 01-03 | 3 | REQ-cli-subcommands, REQ-test-coverage | T-01-07 | CI fixture-secret audit + schema-gen idempotence gate | yaml-lint + grep | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/tests.yml'))" && grep -q 'cov-fail-under=70' .github/workflows/tests.yml && grep -q 'git diff --exit-code schemas/arrconf-schema.json' .github/workflows/tests.yml && grep -q 'tests/fixtures/' .github/workflows/tests.yml && grep -q 'GHCR image' tools/arrconf/README.md` | ❌ W3 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Coverage policy:** All entries in this map respect Pitfall 6 — coverage is scoped to `arrconf.differ` + `arrconf.reconcilers.sonarr` only via `[tool.coverage.run] source = [...]` in `pyproject.toml`. The `--cov-fail-under=70` gate therefore behaves as a per-module threshold for those two modules, while CLI / config / schema-gen modules are not measured (their bugs surface via integration tests).

---

## Wave 0 Requirements

Wave 0 (= Plan 01-01 in this plan) must scaffold the test infrastructure before any reconciler code is written. Per RESEARCH.md §"Wave 0 Gaps":

- [ ] `tools/arrconf/pyproject.toml` — pytest + coverage config (source scoped to `arrconf.differ` + `arrconf.reconcilers.sonarr`) — **W1 Plan 01-01 Task 1**
- [ ] `tools/arrconf/tests/conftest.py` — shared respx fixtures, base URL constants, env stubs — **W1 Plan 01-01 Task 1**
- [ ] `tools/arrconf/tests/fixtures/sonarr/downloadclient.json` — sanitised baseline capture (1 qBit client minimum) — **W1 Plan 01-01 Task 1**
- [ ] `tools/arrconf/tests/fixtures/sonarr/tag.json` — baseline `[]` + edge case `tag_with_arrconf_managed.json` — **W1 Plan 01-01 Task 1**
- [ ] `tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_empty.json`, `downloadclient_with_unmanaged_tag.json` — **W1 Plan 01-01 Task 1**
- [ ] `tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_partial_response.json` — **W3 Plan 01-03 Task 2**
- [ ] `tools/arrconf/tests/test_differ.py` — REQ-idempotence (ADD/UPDATE/DELETE/NO_OP/PRUNE_SKIP/PRUNE_PROTECTED) — **W2 Plan 01-02 Task 1 (TDD)**
- [ ] `tools/arrconf/tests/test_reconcilers_sonarr.py` — REQ-app-coverage (download_clients reconcile + managed tag ordering) — **W2 Plan 01-02 Task 2 (TDD)**
- [ ] `tools/arrconf/tests/test_managed_tag.py` — REQ-managed-tag — **W2 Plan 01-02 Task 2 (TDD)**
- [ ] `tools/arrconf/tests/test_scope_violation.py` — D-12 anchor + T-01-05 hardening — **W2 Plan 01-02 Task 3**
- [ ] `tools/arrconf/tests/test_round_trip.py` — success criteria 3-4 (dump → apply --dry-run = 0 action with respx mock) — **W3 Plan 01-03 Task 2**
- [ ] `tools/arrconf/tests/test_schema_gen.py` — success criterion 6 (schema-gen idempotence) — **W3 Plan 01-03 Task 2**
- [ ] `tools/arrconf/tests/test_cli.py` — REQ-cli-subcommands smoke — **W3 Plan 01-03 Task 1**
- [ ] `tools/arrconf/tests/test_config.py` — load_config() unit tests (happy path + validation + YAML syntax + missing file) — **W3 Plan 01-03 Task 1**
- [ ] `uv sync` in CI — installs pytest + respx before any test runs — **W3 Plan 01-03 Task 3**

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| VS Code / code-server YAML autocomplete on `examples/baseline-sonarr.yml` | REQ-yaml-autocomplete | Editor integration cannot be unit-tested — requires GUI | 1. Open `examples/baseline-sonarr.yml` in VS Code with `redhat.vscode-yaml` ext. 2. Verify `# yaml-language-server: $schema=../schemas/arrconf-schema.json` modeline resolves (bottom-right shows YAML schema badge). 3. Type space under `download_clients:` and confirm field-name autocomplete shows pydantic-derived descriptions. 4. Trigger validation by setting `protocol: ftp` and confirm red squiggle. |
| GHCR image public visibility | REQ-app-coverage / Phase 1 success criterion 2 | Public toggle is a one-time GHCR UI action — no `gh api` endpoint as of 2026-04 (RESEARCH §Pitfall 7) | 1. After first push, visit `github.com/users/tom333/packages/container/arr-stack-arrconf/settings`. 2. Set "Package visibility" to Public. 3. Verify anonymous `docker pull ghcr.io/tom333/arr-stack-arrconf:sha-<short>` succeeds. |
| Round-trip against live Sonarr instance (success criteria 3-4) | REQ-app-coverage | Requires port-forward to my-kluster — out of CI scope | 1. `kubectl -n selfhost port-forward svc/sonarr 8989:8989`. 2. `export SONARR_API_KEY=...`. 3. `arrconf --config /tmp/seed.yml dump --apps sonarr --output examples/baseline-sonarr.yml`. 4. `arrconf --config examples/baseline-sonarr.yml diff --apps sonarr` → exit 0 (no drift). 5. `arrconf --config examples/baseline-sonarr.yml apply --apps sonarr --dry-run` → "no-op" log + exit 0. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (per per-task map)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (split across W1 Task 1 + W2 + W3)
- [x] No watch-mode flags (no `pytest --watch`, no `--looponfail`)
- [x] Feedback latency < 15 s (all tests respx-mocked)
- [x] `nyquist_compliant: true` set in frontmatter
- [x] Coverage scope explicitly limited to `arrconf.differ` + `arrconf.reconcilers.sonarr` (Pitfall 6)
- [x] Manual verifications documented with concrete reproduction steps

**Approval:** approved by gsd-plan-phase 2026-05-07
