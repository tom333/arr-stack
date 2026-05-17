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
| **Quick run command** | `cd tools/arrconf && pytest -x tests/test_jellyfin.py` |
| **Full suite command** | `cd tools/arrconf && ruff check && ruff format --check && mypy . && pytest -v --cov=arrconf --cov-fail-under=70` |
| **Estimated runtime** | ~15-25 seconds (quick) ; ~60-90 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd tools/arrconf && pytest -x tests/test_jellyfin.py` (or scoped test file for that wave)
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
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | JellyfinClient uses MediaBrowser auth header | unit | `pytest tests/test_jellyfin.py::test_auth_header_mediabrowser` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Libraries reconcile: add new library | unit | `pytest tests/test_jellyfin.py::test_libraries_add` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Libraries reconcile: add path (Pitfall 2 idempotence — skip if already present) | unit | `pytest tests/test_jellyfin.py::test_libraries_path_idempotent` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Libraries reconcile: remove obsolete path | unit | `pytest tests/test_jellyfin.py::test_libraries_path_remove` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Server config: GET → merge allowlist → POST entire body (Pitfall 1 destructive replace) | unit | `pytest tests/test_jellyfin.py::test_server_config_get_merge_post` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Server config: required fields (none per OpenAPI) preserved | unit | `pytest tests/test_jellyfin.py::test_server_config_required_preserved` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Users: POST /Users/{id}/Policy (NOT PUT) with AuthenticationProviderId + PasswordResetProviderId preserved | unit | `pytest tests/test_jellyfin.py::test_user_policy_post_required_fields_preserved` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Users: emilie NOT touched (hardcoded admin-only scope D-07-USERS-01) | unit | `pytest tests/test_jellyfin.py::test_user_emilie_untouched` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Plugins: Enable endpoint POST /Plugins/{id}/{version}/Enable (version REQUIRED) | unit | `pytest tests/test_jellyfin.py::test_plugin_enable_endpoint_uses_version` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Plugins: skip if already Active | unit | `pytest tests/test_jellyfin.py::test_plugin_active_noop` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | Plugins: no install / no uninstall (scope guard) | unit | `pytest tests/test_jellyfin.py::test_plugin_install_uninstall_forbidden` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-prune-opt-in | — | Libraries prune=false default → log warn, no DELETE | unit | `pytest tests/test_jellyfin.py::test_libraries_prune_false_default` | ❌ W0 | ⬜ pending |
| 07-02-XX | 02 | 2 | REQ-app-coverage | — | CLI: `arrconf apply --apps jellyfin --dry-run` exits 0 with action plan | unit | `pytest tests/test_main.py::test_apply_jellyfin_dry_run` | ❌ W0 | ⬜ pending |
| 07-03-XX | 03 | 3 | REQ-app-coverage | — | chart values.schema validates jellyfin section | smoke | `helm template charts/arr-stack/ -f examples/values-prod.yaml \| kubeconform -` | — | ⬜ pending |
| 07-03-XX | 03 | 3 | REQ-app-coverage | — | chart-lint CI green (auto-tag, kubeconform) | integration | `gh workflow run chart-lint.yml` then verify success | — | ⬜ pending |
| 07-04-XX | 04 | 4 | REQ-app-coverage | — | Cluster: dry-run on live jellyfin shows zero-diff after first apply | manual | `kubectl -n selfhost create job --from=cronjob/arrconf manual-jellyfin-1 && kubectl -n selfhost logs job/manual-jellyfin-1` | — | ⬜ pending |
| 07-04-XX | 04 | 4 | REQ-app-coverage | — | Round-trip idempotence: `dump` then `diff` returns 0 changes | manual | `arrconf dump --apps jellyfin -o /tmp/r.yml && arrconf diff --config /tmp/r.yml --apps jellyfin` | — | ⬜ pending |
| 07-04-XX | 04 | 4 | REQ-app-coverage | — | Post-apply snapshot diff vs baseline shows only intentional changes | manual | `tools/snapshot/snapshot.sh --apps jellyfin --output snapshots/after-phase-7-$(date +%F)/ && diff -r snapshots/before-phase-7-*/jellyfin/ snapshots/after-phase-7-*/jellyfin/` | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Mapping: "REQ-app-coverage" covers SC#1-#6 of Phase 7 (Bootstrap, snapshot, Q9, round-trip idempotence, libraries on NFS, admin+1 user managed). The mapping per task is materialized by the planner during plan generation; the per-task IDs above are placeholders that planner replaces with concrete `<task_id>` values from the PLAN.md files.*

---

## Wave 0 Requirements

- [ ] `tools/arrconf/tests/test_jellyfin.py` — new test file, stubs for REQ-app-coverage (12+ test cases per the map above)
- [ ] `tools/arrconf/tests/fixtures/jellyfin_library_virtualfolders.json` — sanitized slice from `snapshots/baseline-2026-05-07/jellyfin/library_virtualfolders.json`
- [ ] `tools/arrconf/tests/fixtures/jellyfin_users.json` — sanitized slice (admin "moi" only — no real DeviceId/AccessToken)
- [ ] `tools/arrconf/tests/fixtures/jellyfin_system_configuration.json` — sanitized slice (50 fields baseline, allowlist 7)
- [ ] `tools/arrconf/tests/fixtures/jellyfin_plugins.json` — sanitized slice (6 plugins active)
- [ ] `tools/arrconf/tests/test_config.py` — extend with `test_root_config_parses_jellyfin` (verifies RootConfig accepts jellyfin section)
- [ ] `snapshots/before-phase-7-<date>/jellyfin/` — fresh raw baseline (operator-run via `tools/snapshot/snapshot.sh --apps jellyfin`)
- [ ] `evidence/q9-put-probe.txt` — pre-Wave 1 evidence file with curl outputs from the 3 auth strategies (copy-pasteable from RESEARCH.md §"Q9 PUT Probe — VERIFIED Results")
- [ ] `JELLYFIN_API_KEY` provisioned in `arrconf-env` sealed-secret (manual operator step, REQ-bootstrap-exception)

*If none of these exist at execute time, the corresponding Wave 1+ tasks block until they do.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bootstrap admin Jellyfin via UI + generate API Key | REQ-bootstrap-exception | Pre-cluster human action ; chicken-and-egg (no API key = no API access) | Open Jellyfin Dashboard → Users → admin "moi" exists ; Dashboard → API Keys → "Add" → name="arrconf" ; copy key into sealed-secret patch |
| `JELLYFIN_API_KEY` in `arrconf-env` sealed-secret | REQ-bootstrap-exception | Cluster secrets handled by sister repo (my-kluster) ; not committed in this repo | `kubectl -n selfhost get secret arrconf-env -o jsonpath='{.data.JELLYFIN_API_KEY}' \| base64 -d \| wc -c` returns non-zero |
| Q9 PUT probe live evidence captured (D-07-VALIDATE-01) | REQ-app-coverage | Live API probe ; not repeatable in CI (no real Jellyfin) | Operator runs the 3 curl commands documented in RESEARCH §"Q9 PUT Probe", redacts api_key, commits to `evidence/q9-put-probe.txt` |
| Post-apply round-trip idempotence (SC#4) | REQ-app-coverage | Requires live cluster ; CronJob run on real Jellyfin | After ArgoCD sync of v0.7.x, manual `kubectl create job --from=cronjob/arrconf` ; run `arrconf dump --apps jellyfin \| diff` ; expect zero changes |
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
