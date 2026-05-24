---
phase: 18-qbit-post-credentials-fallback
verified: 2026-05-24T09:10:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: 2026-05-24T09:10:00Z
uat_close: 2026-05-24T09:10:00Z
human_verification:
  - test: "SC#1 — verify rendered ConfigMap carries no live qBit credentials"
    expected: "kubectl get configmap arrconf-config returns no explicit username/password values for qBit DCs"
    result: "✓ PASS (UAT 2026-05-24): ConfigMap arrconf.yml has 0 username:/password: lines anywhere; only api_key_env: SONARR/RADARR_API_KEY entries + 3 doc comments"
  - test: "SC#2 — ArgoCD-triggered CronJob completes without ConfigError"
    expected: "kubectl create job from cronjob/arrconf; pod exits 0; logs show apply_complete for sonarr+radarr; no missing_env_vars / ConfigError in stderr"
    result: "✓ PASS (UAT 2026-05-24, pod arrconf-fix-rpm-1779613542-g4zjz): Phase=Succeeded exit 0; no ConfigError; apply_complete for sonarr+radarr+qbittorrent+seerr+jellyfin"
    note: "Initially partial-passed due to pre-existing pre-Phase-18 RPM 400 bug at Step 5 (sonarr-rpm-400-categories debug session). Resolved via 8x mkdir on qBittorrent volume; clean reconcile then completed end-to-end."
  - test: "SC#3 (dispositive) — Sonarr/Radarr UI Test button returns HTTP 200 on qBit DCs"
    expected: "All visible qBit DCs in Sonarr UI (https://sonarr.tgu.ovh/settings/downloadclients) and Radarr UI test green"
    result: "✓ PASS (UAT 2026-05-24): API equivalent — 9/9 Sonarr qBit DCs HTTP 200 on /api/v3/downloadclient/test; 9/9 Radarr qBit DCs HTTP 200. Auth confirmed against live qBittorrent for ALL 5 new Phase-18-derived DCs per side"
  - test: "SC#4 — Second CronJob run emits 0 drift on download_clients"
    expected: "2nd manual CronJob trigger logs show 0 add/update/delete plan_action on download_clients step for sonarr+radarr"
    result: "✓ PASS (UAT 2026-05-24, pod arrconf-uat-sc4-1779613679-b5rd5): 0 plan_actions on download_clients step (sonarr+radarr); no apply_complete for sonarr/radarr/qbittorrent because there were no actions to commit. Dispositive idempotence proof."
  - test: "SC#5 (optional) — Explicit YAML credentials override env"
    expected: "Operator adds explicit username/password in arrconf.yml; next reconcile emits update_field event; YAML values are forwarded byte-for-byte (Sonarr Test would now fail because explicit-pass is wrong)"
    result: "skipped (UAT 2026-05-24): optional, covered by unit test test_yaml_explicit_env_ignored"
---

# Phase 18: qBit POST credentials fallback Verification Report

**Phase Goal:** When the `username` / `password` fields of a qBit `download_clients` entry are empty (or omitted) in `arrconf.yml`, the reconciler injects `QBT_USER` / `QBT_PASS` from environment variables at POST/PUT time — idempotent, explicit values always win — so the operator can keep credentials out of the committed YAML without breaking the reconcile.

**Verified:** 2026-05-24
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (mapped to ROADMAP Success Criteria + PLAN must_haves)

| #   | Truth (SC) | Status     | Evidence       |
| --- | ---------- | ---------- | -------------- |
| 1   | **SC#1:** qBit-side `download_clients` reconciler injects `os.environ["QBT_USER"]` / `os.environ["QBT_PASS"]` when YAML field is empty/missing; uses explicit YAML otherwise; raises `ConfigError` when both YAML+env empty (fail-fast). | ✓ VERIFIED | `_resolve_qbit_credentials_from_env` exists at `_shared.py:154-239`. Reads `os.environ.get("QBT_USER","")` (line 192) + `os.environ.get("QBT_PASS","")` (line 193). Raises `ConfigError(f"download_client '{dc.name}': username is empty in YAML AND QBT_USER env is unset/empty")` at lines 215-218. Wired into `sonarr.py:547` and `radarr.py:544`, between `_resolve_download_client_tag_labels` and `_ensure_managed_tag_in_desired`. Explicit YAML wins because helper only substitutes when current is None / empty / whitespace. |
| 2   | **SC#2:** Respx unit tests cover the 3 cases: (a) YAML empty + env set, (b) YAML explicit + env ignored, (c) partial. All 3 pass in CI. | ✓ VERIFIED | `tests/test_qbit_credentials_env_fallback.py`: `test_yaml_empty_env_set_uses_env_values` (case a), `test_yaml_explicit_env_ignored` (case b), `test_yaml_partial_username_explicit_password_empty` (case c). All 3 + 9 additional tests pass: 12 tests in file. Full triad: 411 tests pass, 85.08% cov. |
| 3   | **SC#3:** Idempotence preserved: 2nd `arrconf apply` emits 0 `plan_action` on `download_clients` with env-injected creds. No spurious PUT bumps. | ✓ VERIFIED | `test_second_apply_zero_drift_on_download_clients_with_env_injected_creds` (`test_qbit_credentials_env_fallback.py:328-406`) runs full `reconcile_sonarr` flow against masked cluster GET (`"********"`/`privacy="userName"/"password"`) and asserts `put_route.call_count == 0` + `actions_for_qbit == [Action.NO_OP]`. Defense-in-depth via `test_second_apply_zero_drift_value_based_mask_strip` (lines 428-503) — exercises the value-based mask strip path (`differ.py:_credential_field_names` line-by-value inference per WR-05 fix). |
| 4   | **SC#4:** Chart-pin co-bump executed: `charts/arr-stack/values.yaml#arrconf.image.tag` bumped (committed in same patch series as the Python code). Renovate annotation preserved verbatim. | ✓ VERIFIED | `charts/arr-stack/values.yaml:451` reads `tag: "0.10.2"` (initial bump 0.10.0 → 0.10.1 in commit `e2393b8`, then 0.10.1 → 0.10.2 in WR-05 fix-batch commits `5cc40ee`+). `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` annotation at line 449 directly above `repository:` at line 450 — verbatim, unchanged. |
| 5   | **SC#5:** Operator UAT documented: `18-HUMAN-UAT.md` covers live-cluster end-to-end runbook (drift = 0 on `download_clients` after stripping creds from YAML). | ✓ VERIFIED | `.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` exists (198 lines). 5 scenarios (SC#1–SC#5) each with Pre-condition / Action / Verification / Pass criterion; 12 kubectl commands; result-tracking table; references CronJob log inspection for 0-drift confirmation. **Note:** runbook text body still says `:0.10.1` (operator-facing reference) while values.yaml is at `0.10.2` — minor staleness, does not invalidate the runbook procedure (operator inspects the live tag at runtime, not the doc literal). |

**Score:** 5 / 5 truths verified

### Required Artifacts

| Artifact | Expected    | Status | Details |
| -------- | ----------- | ------ | ------- |
| `tools/arrconf/arrconf/reconcilers/_shared.py` | Public helper `_resolve_qbit_credentials_from_env` | ✓ VERIFIED | Function defined at line 154, ~85 LOC incl. docstring (extended post-review for WR-01, WR-03). Imports: `import os` (line 13), `from arrconf.exceptions import ConfigError, ReconcileError` (line 18). Raises `ConfigError` per D-18-FAIL-FAST-01 exact message format. Gated on `implementation == "QBittorrent"` (WR-01 fix, line 204). Strips whitespace on both env and YAML (WR-03 fix, lines 213, 225). |
| `tools/arrconf/arrconf/reconcilers/sonarr.py` | Call site between label resolution and managed-tag stamping | ✓ VERIFIED | Imported in `arrconf.reconcilers._shared` import block at line 61. Called at line 547: `label_resolved = _resolve_qbit_credentials_from_env(label_resolved)` — between `_resolve_download_client_tag_labels(...)` (line 546) and `_ensure_managed_tag_in_desired(...)` (line 548). |
| `tools/arrconf/arrconf/reconcilers/radarr.py` | Symmetric call site | ✓ VERIFIED | Imported at line 72. Called at line 544: same shape as Sonarr. |
| `tools/arrconf/tests/test_qbit_credentials_env_fallback.py` | 5 unit tests covering SC#2 (3 cases) + ConfigError + SC#3 idempotence | ✓ VERIFIED+ | 12 tests defined (exceeds plan's "5 minimum"). The 5 mandated tests are all present and named per plan; 7 additional tests from code-review WR-01/WR-03/WR-04/WR-05 fixes (asymmetric env, whitespace handling, non-qBit DC pass-through, value-based mask defense-in-depth). |
| `charts/arr-stack/values.yaml` | `arrconf.image.tag` co-bump from `0.10.0` | ✓ VERIFIED | Current value `tag: "0.10.2"` (planned 0.10.1, actual 0.10.2 after WR-05 chart-pin co-bump batch). Renovate annotation preserved at line 449. |
| `.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` | Operator UAT runbook for SC#1–SC#5 | ✓ VERIFIED | 198 lines, 5 scenarios, kubectl-based runbook. |

### Key Link Verification

| From | To  | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `reconcilers/sonarr.py:547` | `_shared.py::_resolve_qbit_credentials_from_env` | function call between label resolution and reconcile() | ✓ WIRED | Reassigns `label_resolved` between `_resolve_download_client_tag_labels` and `_ensure_managed_tag_in_desired`; downstream `desired_dcs` consumes the injected values. |
| `reconcilers/radarr.py:544` | `_shared.py::_resolve_qbit_credentials_from_env` | function call between label resolution and reconcile() | ✓ WIRED | Symmetric to Sonarr; both files have grep count = 2 (1 import + 1 call site). |
| `_shared.py` | `os.environ['QBT_USER']` / `os.environ['QBT_PASS']` | `os.environ.get()` per-invocation (no module cache) | ✓ WIRED | Lines 192-193; raw values stripped for whitespace at lines 194-195 (WR-03). |
| `_shared.py` | `arrconf.exceptions.ConfigError` | `raise ConfigError(...)` when YAML+env both empty | ✓ WIRED | Imported at line 18; raised at lines 215, 227. Exact message format per D-18-FAIL-FAST-01 covered by `test_yaml_empty_env_unset_raises_config_error`. |
| `__main__.py:223-235` (apply) + `:560-572` (diff) | `_qbit_creds_required_for_sonarr_radarr(root, targets)` pre-flight gate | exit code 2 BEFORE any HTTP call when categories[] non-empty + sonarr/radarr in targets + QBT_USER/QBT_PASS empty | ✓ WIRED (post-CR-02 fix) | Predicate at `__main__.py:143-172`; tested by `test_apply_sonarr_missing_qbt_user_preflight_exit_2`, `test_apply_radarr_missing_qbt_pass_preflight_exit_2`, `test_apply_sonarr_radarr_preflight_blocks_http_calls` (dispositive — asserts 0 HTTP calls), `test_apply_sonarr_radarr_no_categories_no_preflight_gate` (gate scope). |
| `__main__.py:261-269` (sonarr apply) + `:299-302` (radarr apply) + `:587-590` (sonarr diff) + `:614-617` (radarr diff) | `except ConfigError as e: ... raise typer.Exit(code=2)` defense-in-depth handlers | catches stragglers that bypass the pre-flight gate | ✓ WIRED (post-CR-01 fix) | All 4 branches catch ConfigError ahead of `(ApiClientError, ReconcileError)` and re-raise as `typer.Exit(code=2)`. |
| `charts/arr-stack/values.yaml:451` | `ghcr.io/tom333/arr-stack-arrconf:0.10.2` | co-bump anchors next CronJob image pull | ✓ WIRED | Image tag bumped twice (0.10.0 → 0.10.1 → 0.10.2) in same commit series as Python fixes. Renovate annotation preserved at line 449. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `sonarr.py` reconcile DC POST/PUT body | `dc.fields[name=username/password].value` | env-injected via `_resolve_qbit_credentials_from_env(label_resolved)` (line 547) — substitutes `os.environ.get("QBT_USER","").strip()` and `QBT_PASS` | Yes — `os.environ.get` reads cluster-runtime env vars from `envFrom: arrconf-env` SealedSecret. SC#3 idempotence test confirms env-injected real values flow through `merge_fields_for_put` correctly. | ✓ FLOWING |
| `radarr.py` reconcile DC POST/PUT body | (same) | (same, symmetric) | Yes | ✓ FLOWING |
| `_resolve_qbit_credentials_from_env` exit branch | `ConfigError` | helper-raised exception | Caught by pre-flight gate (primary) + dedicated `except ConfigError` handlers (defense-in-depth); maps to `typer.Exit(code=2)` per CLAUDE.md exit-code contract | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Helper definition exists | `grep -c "^def _resolve_qbit_credentials_from_env" tools/arrconf/arrconf/reconcilers/_shared.py` | `1` | ✓ PASS |
| `import os` added | `grep -c "^import os" tools/arrconf/arrconf/reconcilers/_shared.py` | `1` | ✓ PASS |
| `ConfigError` imported | `grep "from arrconf.exceptions import ConfigError, ReconcileError" tools/arrconf/arrconf/reconcilers/_shared.py` | match | ✓ PASS |
| Sonarr call site (import + 1 call) | `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/reconcilers/sonarr.py` | `2` | ✓ PASS |
| Radarr call site (import + 1 call) | `grep -c "_resolve_qbit_credentials_from_env" tools/arrconf/arrconf/reconcilers/radarr.py` | `2` | ✓ PASS |
| Test count in dedicated file | `grep -c "^def test_" tools/arrconf/tests/test_qbit_credentials_env_fallback.py` | `12` (≥5 required) | ✓ PASS |
| `tag: "0.10.x"` in values.yaml | `grep 'tag: "0.10.2"' charts/arr-stack/values.yaml` | match | ✓ PASS (0.10.2 > 0.10.1 expected; bumped during fix batch — see Deviations) |
| `# renovate:` annotation preserved | `grep -B 1 "repository: ghcr.io/tom333/arr-stack-arrconf"` | `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` directly above | ✓ PASS |
| Triad gate (ruff format) | `cd tools/arrconf && uv run ruff format --check .` | `92 files already formatted` | ✓ PASS |
| Triad gate (ruff check) | `cd tools/arrconf && uv run ruff check .` | `All checks passed!` | ✓ PASS |
| Triad gate (mypy arrconf) | `cd tools/arrconf && uv run mypy arrconf` | `Success: no issues found in 55 source files` | ✓ PASS |
| Test suite + coverage | `cd tools/arrconf && uv run pytest --cov=arrconf --cov-fail-under=70` | `411 passed`, `Total coverage: 85.08%` | ✓ PASS |
| Scope discipline (no leakage to other reconcilers) | `grep -c "_resolve_qbit_credentials_from_env"` in `generators/categories.py`, `differ.py`, `reconcilers/{prowlarr,seerr,jellyfin,qbittorrent}.py` | All return 0 | ✓ PASS |
| CLI pre-flight test (CR-02 dispositive) | `pytest tests/test_cli.py::test_apply_sonarr_radarr_preflight_blocks_http_calls` | passed in suite | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| REQ-qbit-post-credentials | 18-A-PLAN.md | qBit POST `username`/`password` env-injection with explicit YAML wins, fail-fast on missing env, 3 respx cases, idempotence preserved | ✓ SATISFIED (pending operator UAT for full close-out per `requirements-completed` claim) | All 5 ROADMAP SC verified at code/test level. SC#5 operator UAT runbook complete but live-cluster validation is the remaining human step. |

No orphaned requirements: REQUIREMENTS.md maps Phase 18 → REQ-qbit-post-credentials only (line 55), and that requirement is claimed in `18-A-PLAN.md` frontmatter line 16.

### Anti-Patterns Found

Scanned files modified in this phase per SUMMARY key-files. No blocker anti-patterns found.

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `tools/arrconf/tests/test_qbit_credentials_env_fallback.py` | (various) | Tests intentionally use `monkeypatch.delenv("QBT_USER", raising=False)` to simulate missing env — this is test scaffolding, not production stub | ℹ️ Info | None — test fixture pattern |
| `.planning/phases/18-qbit-post-credentials-fallback/18-HUMAN-UAT.md` | line 6, 33 | References `:0.10.1` while values.yaml is at `0.10.2` (post WR-05 fix batch) | ℹ️ Info | Operator-facing doc has stale image tag literal but procedure (kubectl, ConfigMap inspection) still applies — operator verifies live tag at runtime |

### Human Verification Required

Five operator-driven cluster scenarios from `18-HUMAN-UAT.md` cannot be programmatically verified — they require live ArgoCD-synced cluster, kubectl access, and (for SC#3) authenticated browser UI access to Sonarr/Radarr.

#### 1. SC#1 — Generator preserves empty credential fields in arrconf.yml ConfigMap

**Test:** `kubectl -n selfhost get configmap arrconf-config -o jsonpath='{.data.arrconf\.yml}' | grep -A 2 "username" | head -20`

**Expected:** No explicit `username:`/`password:` values for qBit `download_clients` entries — generator's empty placeholders dominate (or fields[] absent). Real creds live ONLY in `arrconf-env` SealedSecret.

**Why human:** Requires live cluster access and visual confirmation of ConfigMap data.

#### 2. SC#2 — ArgoCD-triggered CronJob does NOT raise ConfigError

**Test:**
```bash
kubectl -n selfhost create job --from=cronjob/arrconf arrconf-uat-sc2-$(date +%s)
# Then:
POD=$(kubectl -n selfhost get pods -l job-name=arrconf-uat-sc2-* -o jsonpath='{.items[0].metadata.name}' --sort-by='.metadata.creationTimestamp' | tail -1)
kubectl -n selfhost logs "$POD" | grep -iE "(ConfigError|missing_env|exit code 2)"
kubectl -n selfhost logs "$POD" | grep -E "apply_complete"
```

**Expected:** Pod exits 0; no `ConfigError` / `missing_env_vars` lines; `apply_complete` events for sonarr + radarr.

**Why human:** Requires live cluster scheduled workload + log inspection.

#### 3. SC#3 (dispositive) — Sonarr/Radarr UI Test button on qBit DCs returns HTTP 200

**Test:** Open Sonarr UI (https://sonarr.tgu.ovh/settings/downloadclients) and Radarr UI; click "Test" button on each qBit DC.

**Expected:** All qBit DCs show green checkmark — qBittorrent confirms credentials Sonarr/Radarr POSTed actually authenticate.

**Why human:** Requires authenticated browser session against the live UI. This is the dispositive end-to-end proof that the env-injection chain works: SealedSecret → CronJob env → `os.environ.get("QBT_USER")` → `_resolve_qbit_credentials_from_env` → `merge_fields_for_put` → POST/PUT body → Sonarr/Radarr stored config → live qBit auth.

#### 4. SC#4 — Second CronJob run emits 0 drift on download_clients

**Test:**
```bash
kubectl -n selfhost create job --from=cronjob/arrconf arrconf-uat-sc4-$(date +%s)
POD=$(kubectl -n selfhost get pods -l job-name=arrconf-uat-sc4-* -o jsonpath='{.items[0].metadata.name}' --sort-by='.metadata.creationTimestamp' | tail -1)
kubectl -n selfhost logs "$POD" | grep -E '"step":\s*"download_clients"|plan_action' | head -20
```

**Expected:** 0 add/update/delete actions on `download_clients` for sonarr + radarr on the 2nd run.

**Why human:** Requires two sequential live CronJob firings + log diff. Unit-test equivalents (`test_second_apply_zero_drift_on_download_clients_with_env_injected_creds`, `test_second_apply_zero_drift_value_based_mask_strip`) confirm this property in respx mocks; live cluster confirmation is the SC#5 close-out signal.

#### 5. SC#5 (optional) — Explicit YAML credentials override env

**Test:** Operator edits `charts/arr-stack/files/arrconf.yml` to add explicit username/password on one qBit DC, commits, syncs ArgoCD, inspects next CronJob log.

**Expected:** Next reconcile emits `update_field` event; YAML values forwarded verbatim (Sonarr Test would now fail because explicit-pass is intentionally wrong). Proves env is ignored when YAML is explicit.

**Why human:** Operator-driven YAML edit + chart redeploy. Optional/non-blocking — covered by unit test `test_yaml_explicit_env_ignored`.

### Deviations from Plan (informational — none invalidate phase outcome)

Two deviations from the original `18-A-PLAN.md` constraints, both intentional and resolved by code review fixes:

#### Deviation 1: `__main__.py` was modified despite plan task 2 saying "Do NOT modify"

The original plan (task 2, line 397) instructed: "Do NOT modify `__main__.py` — its existing Phase 5 gate (lines 274-281) covers the qBittorrent reconciler natif's env requirements; the new helper raises ConfigError independently and propagates up through normal exception handling."

Code review (`18-REVIEW.md`, CR-01 + CR-02) flagged this as a BLOCKER:
- **CR-01:** `ConfigError` was not in the `except (ApiClientError, ReconcileError)` tuple in `__main__.py`, so the CLI crashed with an uncaught traceback (typer exit 1) instead of the documented exit 2.
- **CR-02:** The fail-fast happened at Step 6 of `reconcile_sonarr`/`reconcile_radarr`, AFTER Steps 1-5 had already issued POST `/tag` `/indexer` `/rootfolder` `/remotepathmapping` — leaving the cluster in a partially-written state when QBT env was missing.

Fixed in commit `5cc40ee` (Phase 18-A-fix) by:
1. Adding `_qbit_creds_required_for_sonarr_radarr()` predicate at `__main__.py:143-172`.
2. Pre-flight gate at `__main__.py:217-235` (apply) and `:555-572` (diff) — fires BEFORE any client construction, mirrors the existing qBittorrent gate at lines 339-346.
3. Defense-in-depth `except ConfigError` handlers at lines 261-269, 299-302, 587-590, 614-617 — catch stragglers from tests that bypass the gate.

The deviation is sound: the plan's constraint contradicted its own SC#1 contract (CLI exit code 2 on missing env), which the code review surfaced. The fix correctly addresses both BLOCKERs without expanding scope.

#### Deviation 2: Chart-pin tag bumped beyond planned `0.10.1`

Plan task 4 (D-18-CHART-BUMP-01) specified `0.10.0 → 0.10.1`. Actual final value is `0.10.2` because the WR-05 fix-batch (value-based credential name inference in `differ.py`, commits `c13d16d` / `525ec36` / `6c9579e`) included another co-bump per CLAUDE.md "Release pin co-bump pattern" since they touched `tools/arrconf/**`. This is the correct application of the project's release-pin discipline — no deviation in spirit, just numerical drift from the plan literal.

Both deviations are documented in `18-A-SUMMARY.md` lines 122-143 ("Auto-fixed Issues") and in the additional fix commits' messages.

### Gaps Summary

No code-level gaps. All 5 ROADMAP Success Criteria are satisfied at the code, test, and chart layer:

- SC#1 implementation: `_resolve_qbit_credentials_from_env` helper + Sonarr/Radarr wiring + ConfigError fail-fast (plus pre-flight gate for partial-write prevention).
- SC#2 implementation: 3 mandated respx cases present in `test_qbit_credentials_env_fallback.py` plus 9 additional regression tests from code-review fixes (411 tests total, 85.08% coverage).
- SC#3 implementation: dispositive idempotence test against masked cluster fixture, plus defense-in-depth value-based mask strip test.
- SC#4 implementation: `values.yaml` `arrconf.image.tag: "0.10.2"` (≥ planned 0.10.1), Renovate annotation preserved verbatim.
- SC#5 documentation: `18-HUMAN-UAT.md` complete with 5 scenarios and live-cluster kubectl runbook.

The remaining gap is purely the live-cluster operator UAT (SC#1–SC#5 in `18-HUMAN-UAT.md`) — by design a human task per CLAUDE.md "On ne déploie JAMAIS depuis ce repo directement. Toujours via my-kluster". The phase is implementation-complete and ready for the operator to execute the runbook against the live cluster after the next ArgoCD sync.

---

_Verified: 2026-05-24_
_Verifier: Claude (gsd-verifier)_
