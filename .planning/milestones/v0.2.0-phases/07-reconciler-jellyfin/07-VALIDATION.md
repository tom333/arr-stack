---
phase: 7
slug: reconciler-jellyfin
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-17
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + respx (httpx mock) |
| **Config file** | `tools/arrconf/pyproject.toml` (existing — Phases 2-6) |
| **Quick run command** | `cd tools/arrconf && pytest -x tests/test_reconcilers_jellyfin.py` |
| **Full suite command** | `cd tools/arrconf && ruff check && ruff format --check && mypy . && pytest -v --cov=arrconf --cov-fail-under=70` |
| **Estimated runtime** | ~15-25 seconds (quick) ; ~60-90 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd tools/arrconf && pytest -x tests/test_reconcilers_jellyfin.py` (or scoped test file for that wave)
- **After every plan wave:** Run `cd tools/arrconf && ruff check && mypy . && pytest -v --cov=arrconf`
- **Before `/gsd-verify-work`:** Full suite must be green AND `helm lint charts/arr-stack/` AND `helm template ... | kubeconform -`
- **Max feedback latency:** 90 seconds (pytest unit tests with respx) / 5 seconds for any single test

---

## Per-Task Verification Map

> Filled by `/gsd-execute-phase` as tasks emerge from plans. Skeleton below reflects expected coverage from RESEARCH §"Validation Architecture" — planner will materialize concrete task IDs.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-00-01 | 00 | 0 | REQ-bootstrap-exception | — | JELLYFIN_API_KEY present in arrconf-env sealed-secret OR explicit operator override flag | manual | `kubectl -n selfhost get secret arrconf-env -o jsonpath='{.data.JELLYFIN_API_KEY}'` | ❌ W0 | ⬜ pending |
| 07-00-02 | 00 | 0 | REQ-app-coverage | — | Snapshot baseline captured before any write | manual | `tools/snapshot/snapshot.sh --apps jellyfin --output snapshots/before-phase-7-$(date +%F)/` | ❌ W0 | ⬜ pending |
| 07-00-03 | 00 | 0 | REQ-app-coverage | — | Q9 auth probe evidence captured | manual | `cat evidence/q9-put-probe.txt` (file exists + contains all 3 strategy outputs) | ❌ W0 | ⬜ pending |
| 07-01-XX | 01 | 1 | REQ-app-coverage | — | Pydantic schema parses sample jellyfin YAML | unit | `pytest tests/test_config.py::test_root_config_parses_jellyfin` | ❌ W0 | ⬜ pending |
| 07-01-XX | 01 | 1 | REQ-yaml-autocomplete | — | JSON Schema regenerated, contains jellyfin section | unit | `python -m arrconf schema-gen --output /tmp/s.json && jq '.properties.jellyfin' /tmp/s.json` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | JellyfinClient uses MediaBrowser auth header | unit | `pytest tests/test_reconcilers_jellyfin.py::test_auth_header_mediabrowser` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Libraries reconcile: add new library | unit | `pytest tests/test_reconcilers_jellyfin.py::test_libraries_add` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Libraries reconcile: add path (Pitfall 2 idempotence — skip if already present) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_libraries_path_idempotent` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Libraries reconcile: remove obsolete path | unit | `pytest tests/test_reconcilers_jellyfin.py::test_libraries_path_remove` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Server config: GET → merge allowlist → POST entire body (Pitfall 1 destructive replace) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_server_config_get_merge_post` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Server config: required fields (none per OpenAPI) preserved | unit | `pytest tests/test_reconcilers_jellyfin.py::test_server_config_required_preserved` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Users: POST /Users/{id}/Policy (NOT PUT) with AuthenticationProviderId + PasswordResetProviderId preserved | unit | `pytest tests/test_reconcilers_jellyfin.py::test_user_policy_post_required_fields_preserved` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Users: emilie NOT touched (hardcoded admin-only scope D-07-USERS-01) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_user_emilie_untouched` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Plugins: Enable endpoint POST /Plugins/{id}/{version}/Enable (version REQUIRED) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_plugin_enable_endpoint_uses_version` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Plugins: skip if already Active | unit | `pytest tests/test_reconcilers_jellyfin.py::test_plugin_active_noop` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Plugins: no install / no uninstall (scope guard) | unit | `pytest tests/test_reconcilers_jellyfin.py::test_plugin_install_uninstall_forbidden` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-prune-opt-in | — | Libraries prune=false default → log warn, no DELETE | unit | `pytest tests/test_reconcilers_jellyfin.py::test_libraries_prune_false_default` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | CLI: `arrconf apply --apps jellyfin --dry-run` exits 0 with action plan | unit | `pytest tests/test_main.py::test_apply_jellyfin_dry_run` | ❌ W0 | ⬜ pending |
| 07-04-04 | 04 | 2 | REQ-app-coverage (SC#4) | — | `dump_jellyfin(client, path)` emits round-trippable YAML with `# yaml-language-server` modeline | unit | `pytest tests/test_dump.py -k jellyfin` | ❌ W0 | ⬜ pending |
| 07-04-04 | 04 | 2 | REQ-app-coverage (SC#4) | — | dump → load_config → JellyfinInstance round-trip preserves semantic state | unit | `pytest tests/test_dump.py::test_dump_jellyfin_round_trip_via_load_config` | ❌ W0 | ⬜ pending |
| 07-04-05 | 04 | 2 | REQ-app-coverage (SC#4) | — | `diff_jellyfin(client, root_config)` returns 0 when desired matches cluster | unit | `pytest tests/test_diff_cmd.py -k jellyfin` | ❌ W0 | ⬜ pending |
| 07-04-05 | 04 | 2 | REQ-app-coverage (SC#4) | — | SC#4 unit-layer mirror: dump → load_config → diff returns exit code 0 | unit | `pytest tests/test_diff_cmd.py::test_diff_jellyfin_round_trip_with_dump` | ❌ W0 | ⬜ pending |
| 07-04-06 | 04 | 2 | REQ-app-coverage (SC#4) | — | `arrconf dump --apps jellyfin` CLI dispatches to dump_jellyfin | smoke | `python -m arrconf --help \| grep dump` AND grep `from arrconf.dump import dump_jellyfin` in __main__.py | ❌ W0 | ⬜ pending |
| 07-04-06 | 04 | 2 | REQ-app-coverage (SC#4) | — | `arrconf diff --apps jellyfin` CLI dispatches to diff_jellyfin | smoke | `python -m arrconf --help \| grep diff` AND grep `from arrconf.diff_cmd import diff_jellyfin` in __main__.py | ❌ W0 | ⬜ pending |
| 07-03-XX | 03 | 3 | REQ-app-coverage | — | chart values.schema validates jellyfin section | smoke | `helm template charts/arr-stack/ -f examples/values-prod.yaml \| kubeconform -` | — | ⬜ pending |
| 07-03-XX | 03 | 3 | REQ-app-coverage | — | chart-lint CI green (auto-tag, kubeconform) | integration | `gh workflow run chart-lint.yml` then verify success | — | ⬜ pending |
| 07-04-XX | 04 | 4 | REQ-app-coverage | — | Cluster: dry-run on live jellyfin shows zero-diff after first apply | manual | `kubectl -n selfhost create job --from=cronjob/arrconf manual-jellyfin-1 && kubectl -n selfhost logs job/manual-jellyfin-1` | — | ⬜ pending |
| 07-06-02 | 06 | 4 | REQ-app-coverage (SC#4 LIVE) | — | SC#4 literal contract: `arrconf dump --apps jellyfin -o /tmp/jelly.yml && arrconf --config /tmp/jelly.yml diff --apps jellyfin` returns exit 0 (no drift) against the live cluster | manual | See Plan 07-06 Task 6.2 — Pattern A (in-cluster Job) or Pattern B (port-forward + local arrconf). Evidence: `evidence/sc4-roundtrip-idempotence.txt` must contain `DIFF_EXIT=0` | — | ⬜ pending |
| 07-04-XX | 04 | 4 | REQ-app-coverage | — | Post-apply snapshot diff vs baseline shows only intentional changes | manual | `tools/snapshot/snapshot.sh --apps jellyfin --output snapshots/after-phase-7-$(date +%F)/ && diff -r snapshots/before-phase-7-*/jellyfin/ snapshots/after-phase-7-*/jellyfin/` | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Mapping: "REQ-app-coverage" covers SC#1-#6 of Phase 7 (Bootstrap, snapshot, Q9, round-trip idempotence, libraries on NFS, admin+1 user managed). The mapping per task is materialized by the planner during plan generation; the per-task IDs above are placeholders that planner replaces with concrete `<task_id>` values from the PLAN.md files.*

---

## Wave 0 Requirements

- [ ] `tools/arrconf/tests/test_reconcilers_jellyfin.py` — new test file, ≥10 (target 13) respx tests for REQ-app-coverage (Plan 07-04 Task 4.3)
- [ ] `tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders.json` — sanitized slice from `snapshots/baseline-2026-05-07/jellyfin/library_virtualfolders.json` (subdir convention per Plan 07-03)
- [ ] `tools/arrconf/tests/fixtures/jellyfin/users.json` — sanitized slice (admin "moi" only — no real DeviceId/AccessToken)
- [ ] `tools/arrconf/tests/fixtures/jellyfin/user_moi_full.json` — per-user GET sample (needed for Pitfall 6 re-injection test)
- [ ] `tools/arrconf/tests/fixtures/jellyfin/system_configuration.json` — sanitized slice (56 fields baseline, allowlist 7)
- [ ] `tools/arrconf/tests/fixtures/jellyfin/plugins.json` — sanitized slice (6 plugins active)
- [ ] `tools/arrconf/tests/conftest.py` — extend with 5 jellyfin_*_fixture loader functions (Plan 07-03)
- [ ] `tools/arrconf/tests/test_config.py` — extend with `test_root_config_accepts_jellyfin_block` (Plan 07-02)
- [ ] `tools/arrconf/tests/test_dump.py` — extend with ≥3 dump_jellyfin tests (Plan 07-04 Task 4.4)
- [ ] `tools/arrconf/tests/test_diff_cmd.py` — extend with ≥3 diff_jellyfin tests incl. round-trip-with-dump (Plan 07-04 Task 4.5)
- [ ] `snapshots/before-phase-7-2026-05-17/jellyfin/` — fresh raw baseline (operator-run via `tools/snapshot/snapshot.sh --apps jellyfin`, Plan 07-01 Task 1.1)
- [ ] `evidence/q9-put-probe.txt` — pre-Wave 1 evidence file with curl outputs from the 3 auth strategies (Plan 07-01 Task 1.2)
- [ ] `evidence/jellyfin-api-key-bootstrap-check.txt` — operator gate confirming JELLYFIN_API_KEY in arrconf-env sealed-secret (Plan 07-01 Task 1.3, REQ-bootstrap-exception)

*If none of these exist at execute time, the corresponding Wave 1+ tasks block until they do.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bootstrap admin Jellyfin via UI + generate API Key | REQ-bootstrap-exception | Pre-cluster human action ; chicken-and-egg (no API key = no API access) | Open Jellyfin Dashboard → Users → admin "moi" exists ; Dashboard → API Keys → "Add" → name="arrconf" ; copy key into sealed-secret patch |
| `JELLYFIN_API_KEY` in `arrconf-env` sealed-secret | REQ-bootstrap-exception | Cluster secrets handled by sister repo (my-kluster) ; not committed in this repo | `kubectl -n selfhost get secret arrconf-env -o jsonpath='{.data.JELLYFIN_API_KEY}' \| base64 -d \| wc -c` returns non-zero |
| Q9 PUT probe live evidence captured (D-07-VALIDATE-01) | REQ-app-coverage | Live API probe ; not repeatable in CI (no real Jellyfin) | Operator runs the 3 curl commands documented in RESEARCH §"Q9 PUT Probe", redacts api_key, commits to `evidence/q9-put-probe.txt` |
| Post-apply round-trip idempotence (SC#4 LIVE) | REQ-app-coverage | Requires live cluster — the unit-test mirror (`test_diff_jellyfin_round_trip_with_dump` in Plan 07-04 Task 4.5) already proves the round-trip at fixture level; the LIVE cluster dispositive is Plan 07-06 Task 6.2 | After ArgoCD sync of v0.5.x: either (a) `kubectl apply` a yq-mutated Job that runs `arrconf dump --apps jellyfin --output /tmp/jelly.yml && arrconf --config /tmp/jelly.yml diff --apps jellyfin` or (b) operator port-forwards and runs the same locally. `diff` exit code MUST be 0. Evidence file: `evidence/sc4-roundtrip-idempotence.txt`. |
| Post-apply snapshot diff (SC#5, SC#6) | REQ-app-coverage | Requires live cluster state | `tools/snapshot/snapshot.sh --apps jellyfin --output snapshots/after-phase-7-<date>/ && diff -r snapshots/before-phase-7-*/jellyfin snapshots/after-phase-7-*/jellyfin` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (Wave 0 manual tasks are bookended by Wave 1 unit tests)
- [ ] Wave 0 covers all MISSING references (fixtures, snapshot, evidence, sealed-secret)
- [ ] No watch-mode flags (pytest runs single-shot)
- [ ] Feedback latency < 90s (full suite) / 5s (single test)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
