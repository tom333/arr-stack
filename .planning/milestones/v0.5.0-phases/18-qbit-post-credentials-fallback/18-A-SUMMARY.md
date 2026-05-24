---
phase: 18-qbit-post-credentials-fallback
plan: A
subsystem: reconciler
tags:
  - qbittorrent
  - download_clients
  - env-injection
  - sonarr
  - radarr
  - credentials
  - secrets

# Dependency graph
requires:
  - phase: 02-2-auth-regression
    provides: differ.merge_fields_for_put + _strip_redacted_fields privacy-by-metadata strip (ADR-8.1 / D-02.2-AUTH-REGRESSION). Phase 18 SC#3 idempotence rides on this without adding new code.
  - phase: 05-sonarr-radarr-split
    provides: reconcilers/sonarr.py + reconcilers/radarr.py download_clients step (Step 6) where Phase 18 helper is wired between label resolution and managed-tag stamping.
  - phase: 10-categories-first-class
    provides: generators/categories.py emits qBit DownloadClient entries with empty username/password placeholders — the very state Phase 18 fixes at reconcile time without touching the generator (preserves generator purity).
provides:
  - _resolve_qbit_credentials_from_env helper in reconcilers/_shared.py
  - QBT_USER / QBT_PASS env-injection on qBit download_clients POST/PUT for sonarr + radarr
  - Fail-fast ConfigError when YAML empty AND env unset (D-18-FAIL-FAST-01)
  - arrconf image 0.10.1 published via co-bump (charts/arr-stack/values.yaml)
  - 5 unit tests covering SC#2 (3 cases) + ConfigError + SC#3 idempotence
  - 18-HUMAN-UAT.md operator runbook for SC#1-5 close-out
affects:
  - v0.5.0 milestone close-out
  - REQ-qbit-post-credentials (closed pending operator UAT)
  - any future reconciler that adds qBit DC fields (Prowlarr currently has no qBit DC scope; preserved by D-18-SCOPE-01)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Env-injection at reconcile time (helper between generator output and reconcile() call) — keeps generators pure-testable while letting cluster runtime substitute secrets from envFrom secretRef"
    - "Fail-fast ConfigError on missing env — exit code 2, DC name in message, no credential value disclosure (T-18-01 mitigation)"
    - "Mirror existing _resolve_download_client_tag_labels shape (list-in / list-out via model_copy) — symmetric helper pattern keeps reconciler steps composable"

key-files:
  created:
    - tools/arrconf/tests/test_qbit_credentials_env_fallback.py
    - .planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md
  modified:
    - tools/arrconf/arrconf/reconcilers/_shared.py
    - tools/arrconf/arrconf/reconcilers/sonarr.py
    - tools/arrconf/arrconf/reconcilers/radarr.py
    - tools/arrconf/tests/_arrconf_helpers.py
    - tools/arrconf/tests/test_reconcilers_sonarr.py
    - charts/arr-stack/values.yaml

key-decisions:
  - "D-18-INJECT-LOC-01 (carry-forward): helper lives in reconcilers/_shared.py and is called from Sonarr + Radarr Step 6 — between _resolve_download_client_tag_labels and _ensure_managed_tag_in_desired."
  - "D-18-FAIL-FAST-01 (carry-forward): ConfigError message format f\"download_client '{dc.name}': username is empty in YAML AND QBT_USER env is unset/empty\" pinned by both the helper and the test_yaml_empty_env_unset_raises_config_error test."
  - "D-18-SCOPE-01 (carry-forward): wired into Sonarr AND Radarr only; Prowlarr/Seerr/Jellyfin/qBittorrent-native untouched."
  - "D-18-IDEMPOTENCE-FREE (carry-forward): SC#3 idempotence reuses the existing differ._strip_redacted_fields privacy-by-metadata stripping — no new code path; explicit respx test test_second_apply_zero_drift_on_download_clients_with_env_injected_creds proves it."
  - "D-18-CHART-BUMP-01 (carry-forward): patch bump 0.10.0 → 0.10.1 in same commit as the Python code per CLAUDE.md 'Release pin co-bump pattern'."

patterns-established:
  - "Helper-between-generator-and-reconcile: pure generators emit shape-only resources, reconciler-side helpers in _shared.py inject runtime context (env, label resolution, managed-tag stamping). Phase 18 adds env-injection to this established slot."
  - "Per-call os.environ.get reads (no module-level cache, no settings.py routing): keeps pytest monkeypatch.setenv interleaving cleanly with reconcile cycles in tests."

requirements-completed:
  - REQ-qbit-post-credentials

# Metrics
duration: ~45min
completed: 2026-05-24
---

# Phase 18 Plan A: qBit POST credentials fallback Summary

**Env-injection of QBT_USER / QBT_PASS into qBit download_clients[] fields[] for Sonarr AND Radarr, with fail-fast ConfigError when YAML empty AND env unset — closes the "Sonarr can't authenticate to qBit on first CREATE" gap and the v0.5.0 milestone.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-05-24 (Phase 18 execution start)
- **Completed:** 2026-05-24
- **Tasks:** 6 / 6 (Tasks 1-4 batched into one commit per CLAUDE.md co-bump rule; Task 5 was a gate-only verification; Task 6 a separate doc commit)
- **Files modified:** 6 source + 2 created = 8

## Accomplishments

- New helper `_resolve_qbit_credentials_from_env` in `tools/arrconf/arrconf/reconcilers/_shared.py` (~65 lines incl. docstring) mirroring `_resolve_download_client_tag_labels` shape: list-in/list-out, `model_copy` for immutability, raises `ConfigError` on missing env.
- Wired into `reconcilers/sonarr.py` line 547 and `reconcilers/radarr.py` line 544, one line each, between `_resolve_download_client_tag_labels(...)` and `_ensure_managed_tag_in_desired(...)`.
- 5 unit tests in `tools/arrconf/tests/test_qbit_credentials_env_fallback.py`:
  - `test_yaml_empty_env_set_uses_env_values` (SC#2 case a)
  - `test_yaml_explicit_env_ignored` (SC#2 case b)
  - `test_yaml_partial_username_explicit_password_empty` (SC#2 case c)
  - `test_yaml_empty_env_unset_raises_config_error` (D-18-FAIL-FAST-01)
  - `test_second_apply_zero_drift_on_download_clients_with_env_injected_creds` (SC#3 dispositive respx test, full `reconcile_sonarr` cycle with masked cluster credentials)
- Chart-pin co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` `"0.10.0" → "0.10.1"`. Renovate annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` preserved verbatim above the `repository:` line.
- Operator UAT runbook `.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` documenting SC#1-5 with kubectl commands, expected outputs, pass criteria, and a result-tracking table.

## Task Commits

Phase 18 followed the project's "Release pin co-bump pattern" (CLAUDE.md): when a commit modifies files under `tools/arrconf/**`, it MUST bump `charts/arr-stack/values.yaml#arrconf.image.tag` in the same commit. Tasks 1-4 (Python helper + wiring + tests + chart bump) were therefore committed together as one atomic change. Task 5 was a verification gate (no file modifications). Task 6 (UAT doc) was committed separately because it does not touch Python.

1. **Tasks 1-4: helper + wiring + tests + chart-pin co-bump** — `e2393b8` (`fix(18-A): qBit POST credentials env-injection fallback + chart-pin 0.10.1`)
2. **Task 6: HUMAN-UAT runbook** — `9703a68` (`docs(18-A): operator UAT runbook — SC#1-5 for v0.5.0 qBit creds fallback close-out`)

## Files Created/Modified

- `tools/arrconf/arrconf/reconcilers/_shared.py` — added `_resolve_qbit_credentials_from_env(items)` helper (~65 LOC incl. docstring); added `import os`; extended exception import to `from arrconf.exceptions import ConfigError, ReconcileError`.
- `tools/arrconf/arrconf/reconcilers/sonarr.py` — added `_resolve_qbit_credentials_from_env` to the existing `arrconf.reconcilers._shared` import; one new line at 547 wiring the call between label resolution and managed-tag stamping.
- `tools/arrconf/arrconf/reconcilers/radarr.py` — symmetric edit at line 544.
- `tools/arrconf/tests/test_qbit_credentials_env_fallback.py` — new file, 5 tests, all using `monkeypatch.setenv` / `monkeypatch.delenv` for env control; SC#3 test uses `respx.mock` for the full reconcile cycle.
- `tools/arrconf/tests/_arrconf_helpers.py` — `dry_run_all_apps` now wraps its respx context with `patch.dict(os.environ, qbit_env_overrides)` so the phase10 idempotence sweep + baseline tests survive the new fail-fast helper.
- `tools/arrconf/tests/test_reconcilers_sonarr.py::test_update_omits_privacy_credential_fields_from_put_body` — refactored to reflect post-Phase-18 contract: env-injection populates desired creds → `merge_fields_for_put` CR-01 branch (rotation intent) carries them into the PUT body. Mask leak guards (`"********"`, `"***REDACTED***"`) preserved.
- `charts/arr-stack/values.yaml` — single-line bump `arrconf.image.tag: "0.10.0" → "0.10.1"`. Renovate annotation intact.
- `.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` — new runbook for SC#1-5.

## Decisions Made

All 5 Phase 18 decisions (D-18-INJECT-LOC-01, D-18-FAIL-FAST-01, D-18-SCOPE-01, D-18-IDEMPOTENCE-FREE, D-18-CHART-BUMP-01) were established in 18-CONTEXT.md and carried through the plan unchanged. No new decisions emerged during execution.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `dry_run_all_apps` test helper must patch QBT_USER / QBT_PASS env vars**
- **Found during:** Task 5 (Triade gate — initial `pytest` run after Task 2 surfaced 2 failures in `tests/test_phase10_idempotence_sweep.py`)
- **Issue:** The Phase 10 idempotence sweep test (`test_sweep` + `test_phase10_baseline_fixture_exists_or_generate`) invokes `reconcile_sonarr` and `reconcile_radarr` against the production `arrconf.yml`. Post-Phase-18 those reconcilers now call the new helper which fail-fasts when QBT_USER/QBT_PASS are unset — pytest does not pass real env vars. Without a patch the sweep aborts before producing the baseline plan.
- **Fix:** Added `patch.dict(os.environ, qbit_env_overrides)` (mirroring the existing pattern for Prowlarr's `api_key_env`) around the respx.mock context in `dry_run_all_apps`. Fake values `"fake-qbit-user-for-phase18"` / `"fake-qbit-pass-for-phase18"`.
- **Files modified:** `tools/arrconf/tests/_arrconf_helpers.py`
- **Verification:** `uv run pytest tests/test_phase10_idempotence_sweep.py -v --no-cov` → 2/2 pass.
- **Committed in:** `e2393b8`

**2. [Rule 3 - Blocking] `test_update_omits_privacy_credential_fields_from_put_body` contract update**
- **Found during:** Task 5 (Triade gate — same pytest run surfaced this third failure)
- **Issue:** The Phase 2.2 / D-02.2-AUTH-REGRESSION test asserted that when the desired DC has empty username/password and the cluster carries privacy-masked equivalents, the PUT body OMITS credential fields. Post-Phase-18, the helper injects env values into the desired BEFORE `merge_fields_for_put` runs — so desired is non-empty and hits the differ CR-01 branch "Desired has a real value: user intends credential rotation; pass through as-is". Credentials NOW appear in the PUT body with the env-injected value — which is the intended Phase 18 behavior.
- **Fix:** Refactored the test's assertions: (a) confirm `username` and `password` ARE present in the PUT body, (b) confirm their VALUES are the env-injected `"phase18-fake-user"` / `"phase18-fake-pass"` (proving the chain works), (c) preserve the mask leak defenses (no `"********"`, no `"***REDACTED***"` anywhere in the body). Added `monkeypatch` fixture and `setenv` calls. Updated the docstring to describe the new contract.
- **Files modified:** `tools/arrconf/tests/test_reconcilers_sonarr.py`
- **Verification:** `uv run pytest tests/test_reconcilers_sonarr.py::test_update_omits_privacy_credential_fields_from_put_body -v --no-cov` → 1/1 pass.
- **Committed in:** `e2393b8`

---

**Total deviations:** 2 auto-fixed (both Rule 3 — pre-existing tests blocked by the new helper's fail-fast gate).
**Impact on plan:** Both fixes are mechanical adjustments to tests that were never re-evaluated against the new Phase 18 helper's runtime contract. No production code change beyond what the plan specified. Plan scope is intact: the helper, wiring, new tests, chart-pin, and UAT doc all match the plan acceptance criteria byte-for-byte.

## Issues Encountered

- **Plan literal `uv run mypy .` includes `tests/`** — surfaces 43 pre-existing mypy errors in `tests/` (untyped fixtures, missing generic params on `dict`, etc.) that are unrelated to Phase 18 and out of scope. The CI workflow `.github/workflows/tests.yml` runs `uv run mypy arrconf` (production code only), so the CI-equivalent triad command was used as the actual gate. Confirmed clean: `Success: no issues found in 55 source files`. Pre-existing tests/ mypy debt is logged here but NOT fixed (SCOPE BOUNDARY — Phase 18 scope is REQ-qbit-post-credentials, not test-suite-wide mypy compliance).

## User Setup Required

None — qBit credentials are already provisioned in the cluster via the `arrconf-env` SealedSecret (Phase 5 baseline, confirmed in CLAUDE.md "Variables d'environnement" section and project memory `project_cluster_secrets_sealed.md`).

Post-merge operator workflow:
1. Push `main` (auto-tag CI runs → publishes new `vX.Y.Z`).
2. Wait for GHCR image build (`arrconf-image.yml`) to publish `:0.10.1`.
3. Merge Renovate PR on `my-kluster` bumping `targetRevision`.
4. ArgoCD sync completes.
5. Execute the SC#1-4 scenarios from `18-HUMAN-UAT.md` to close Phase 18.

## Self-Check

Self-verification — claims vs disk reality.

**Files exist:**
- `tools/arrconf/arrconf/reconcilers/_shared.py` — FOUND (helper at line 154)
- `tools/arrconf/tests/test_qbit_credentials_env_fallback.py` — FOUND (5 tests)
- `.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` — FOUND (5 scenarios, 197 lines)
- `charts/arr-stack/values.yaml` — FOUND with `tag: "0.10.1"` at line 451

**Commits exist:**
- `e2393b8` — FOUND in `git log --all`
- `9703a68` — FOUND in `git log --all`

**Triad gate (CI scope: mypy arrconf, not mypy .):**
- ruff format --check . → PASS (92 files already formatted)
- ruff check . → PASS (All checks passed!)
- mypy arrconf → PASS (Success: no issues found in 55 source files)
- pytest --cov-fail-under=70 → PASS (400 tests, 95.35% coverage, Required coverage of 70% reached)

**Helm gate:**
- helm dependency build → PASS
- helm lint -f examples/values-prod.yaml → PASS (0 chart(s) failed)
- schema-gen reproducibility (`uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json` + `git diff --exit-code`) → PASS (no drift)

**Scope discipline:**
- generators/categories.py: 0 occurrences of `_resolve_qbit_credentials_from_env`
- differ.py: 0 occurrences
- __main__.py: 0 occurrences
- charts/arr-stack/files/arrconf.yml: untouched (git diff HEAD~2 empty)
- .github/workflows/: untouched (git diff HEAD~2 empty)

## Self-Check: PASSED

## Next Phase Readiness

- Phase 18 code is shippable. Operator next steps documented in 18-HUMAN-UAT.md.
- Phase 19+ can proceed once the operator closes SC#1-4 in 18-HUMAN-UAT.md.
- REQ-qbit-post-credentials is implementation-complete; only operator UAT remains before marking complete in REQUIREMENTS.md (orchestrator will handle that).

---
*Phase: 18-qbit-post-credentials-fallback*
*Plan: A*
*Completed: 2026-05-24*
