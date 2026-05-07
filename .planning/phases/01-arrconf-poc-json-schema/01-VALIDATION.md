---
phase: 1
slug: arrconf-poc-json-schema
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-07
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 01-RESEARCH.md §"Validation Architecture" — populated by gsd-planner during planning.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-cov 7.1.0 + respx 0.23.1 |
| **Config file** | tools/arrconf/pyproject.toml (`[tool.pytest.ini_options]` + `[tool.coverage.run]`) — installed in Wave 0 |
| **Quick run command** | `cd tools/arrconf && uv run pytest -x --no-cov` |
| **Full suite command** | `cd tools/arrconf && uv run pytest --cov=arrconf.differ --cov=arrconf.reconcilers.sonarr --cov-fail-under=70` |
| **Estimated runtime** | ~5–10 seconds (all respx-mocked, no live HTTP) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (no coverage gate, fast feedback)
- **After every plan wave:** Run full suite command (with coverage gate)
- **Before `/gsd-verify-work`:** Full suite must be green AND coverage ≥ 70 %
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

> Populated during planning. Each row maps a task to its automated verification command.
> Coverage scope is locked to `arrconf.differ` + `arrconf.reconcilers.sonarr` per Pitfall 6 (pytest-cov has no per-file threshold — global average masks under-coverage).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 must scaffold the test infrastructure before any reconciler code is written. Per RESEARCH.md §"Wave 0 Gaps":

- [ ] `tools/arrconf/pyproject.toml` — pytest + coverage config (source scoped to `arrconf.differ` + `arrconf.reconcilers.sonarr`)
- [ ] `tools/arrconf/tests/conftest.py` — shared respx fixtures, base URL constants, env stubs
- [ ] `tools/arrconf/tests/fixtures/sonarr_download_clients_v3.json` — sanitised baseline capture (1 qBit client minimum)
- [ ] `tools/arrconf/tests/fixtures/sonarr_tag.json` — baseline `[]` + edge case `[{id: 1, label: "arrconf-managed"}]`
- [ ] `tools/arrconf/tests/test_differ.py` — stubs for REQ-idempotence (ADD/UPDATE/DELETE/NO_OP/PRUNE_SKIP/PRUNE_PROTECTED)
- [ ] `tools/arrconf/tests/test_sonarr.py` — stubs for REQ-app-coverage (download_clients reconcile + managed tag ordering)
- [ ] `tools/arrconf/tests/test_round_trip.py` — stub for success criteria 3-4 (dump → apply --dry-run = 0 action with respx mock)
- [ ] `tools/arrconf/tests/test_schema_gen.py` — stub for success criterion 6 (schema-gen idempotence)
- [ ] `uv sync` in CI — installs pytest + respx before any test runs

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| VS Code / code-server YAML autocomplete on `examples/baseline-sonarr.yml` | REQ-yaml-autocomplete | Editor integration cannot be unit-tested — requires GUI | 1. Open `examples/baseline-sonarr.yml` in VS Code with `redhat.vscode-yaml` ext. 2. Verify `# yaml-language-server: $schema=...` modeline resolves. 3. Type space under `download_clients:` and confirm field-name autocomplete shows pydantic-derived descriptions. 4. Trigger validation by setting an invalid field and confirm red squiggle. |
| GHCR image public visibility | REQ-app-coverage / Phase 1 success criterion 2 | Public toggle is a one-time GHCR UI action — no `gh api` endpoint as of 2026-04 (RESEARCH §Pitfall 7) | 1. After first push, visit `github.com/users/tom333/packages/container/arr-stack-arrconf/settings`. 2. Set "Package visibility" to Public. 3. Verify anonymous `docker pull ghcr.io/tom333/arr-stack-arrconf:sha-<short>` succeeds. |
| Round-trip against live Sonarr instance (success criteria 3-4) | REQ-app-coverage | Requires port-forward to my-kluster — out of CI scope | 1. `kubectl -n selfhost port-forward svc/sonarr 8989:8989`. 2. `export SONARR_API_KEY=...`. 3. `arrconf dump --apps sonarr > examples/baseline-sonarr.yml`. 4. `arrconf diff --config examples/baseline-sonarr.yml --apps sonarr` → 0 diff. 5. `arrconf apply --config examples/baseline-sonarr.yml --apps sonarr --dry-run` → "no-op" log. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags (no `pytest --watch`, no `--looponfail`)
- [ ] Feedback latency < 15 s
- [ ] `nyquist_compliant: true` set in frontmatter
- [ ] Coverage scope explicitly limited to `arrconf.differ` + `arrconf.reconcilers.sonarr` (Pitfall 6)
- [ ] Manual verifications documented with concrete reproduction steps

**Approval:** pending
