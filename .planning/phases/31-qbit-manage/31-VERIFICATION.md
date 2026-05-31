---
phase: 31-qbit-manage
verified: 2026-05-31T07:40:00Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Deploy qbit_manage CronJob to cluster via ArgoCD sync and observe a completed pod run"
    expected: "CronJob pod runs to completion (exit 0), no ImagePullBackOff, no daemon-hang; qbit_manage log shows share_limits applied without touching categories; kubectl get cronjob -n selfhost qbit-manage shows ACTIVE=0 after run"
    why_human: "Run-once pod lifecycle (QBT_RUN=true + QBT_SCHEDULE=0) and live qBit category non-interference cannot be verified without a real cluster; the config.yml cat_update:false is enforced in the generated artifact but runtime behaviour of qbit_manage v4.6.6 honouring that flag requires an actual run"
  - test: "Verify !ENV QBT_USER / !ENV QBT_PASS tags in config.yml are resolved at runtime by qbit_manage"
    expected: "qbit_manage connects to qBittorrent WebUI successfully (no auth error in pod logs); credentials are injected via arrconf-env envFrom and resolved from the !ENV tags in the mounted ConfigMap"
    why_human: "The !ENV tag resolution is a qbit_manage-specific runtime behaviour — the committed config.yml contains the tags literally; resolution requires the running pod with the real arrconf-env SealedSecret"
---

# Phase 31: qbit_manage Verification Report

**Phase Goal:** qbit_manage est déployé en CronJob avec sa config entièrement générée depuis `intent.yml`, sans jamais entrer en conflit avec arrconf sur la propriété des catégories qBit
**Verified:** 2026-05-31T07:40:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Operator declares `tools.qbit_manage` in `intent.yml`; `arrconf generate` emits `qbit_manage/config.yml`; `QbitManageConfig` has `extra="forbid"` | ✓ VERIFIED | `charts/arr-stack/files/intent.yml` line 14 has `qbit_manage:` block; `charts/arr-stack/files/qbit_manage/config.yml` exists and is generated; `intent_config.py` line 80 has `model_config = ConfigDict(extra="forbid")` on `QbitManageConfig` |
| 2 | Generated `config.yml` always sets `cat_update: false` AND `cat: {}` unconditionally; generator emits them via hardcoded string literals (no conditional path); test asserts this | ✓ VERIFIED | `generators/intent.py` line 83: `"  cat_update: false            # QBM-02: ..."`; line 97: `lines += ["cat: {}", ""]` — hardcoded, no `cfg.` reference; `test_generate_qbit_manage_cat_update_false` + `_cat_empty` + `_yaml_valid` all pass (10/10 tests green); `arrconf generate --check` exits 0 |
| 3 | qbit_manage deployed as 13th app-template CronJob alias; config.yml mounted read-only; arrconf-env injects credentials; run-once env set; CI updated | ✓ VERIFIED | `Chart.yaml` has 13 aliases including `qbit-manage`; `qbit-manage-configmap.yaml` uses `.Files.Get "files/qbit_manage/config.yml"`; `values.yaml` lines 735-779 have CronJob block with `QBT_RUN: "true"`, `QBT_SCHEDULE: "0"`, `envFrom: arrconf-env`, `/config/config.yml` mount; `chart-lint.yml` alias loop ends with `qbit-manage`; annotation guard at `>= 14` |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/arrconf/arrconf/intent_config.py` | `QbitManageConfig`, `ShareLimitGroup`, `TrackerTagEntry` with `extra="forbid"`; `ToolsConfig.qbit_manage` wired | ✓ VERIFIED | Lines 54-120: all three models defined with `model_config = ConfigDict(extra="forbid")`; `ToolsConfig.qbit_manage: QbitManageConfig | None = Field(default=None)` at line 117 |
| `tools/arrconf/arrconf/generators/intent.py` | `generate_qbit_manage()` pure function | ✓ VERIFIED | Lines 52-129: `_QBM_HEADER` constant + `generate_qbit_manage(cfg: QbitManageConfig) -> str` function; `QbitManageConfig` imported at line 21 |
| `tools/arrconf/arrconf/__main__.py` | `generate_qbit_manage` imported and dispatched | ✓ VERIFIED | Line 36: `from arrconf.generators.intent import generate_cross_seed, generate_qbit_manage`; lines 1046-1059: dispatch block `if intent_cfg.tools.qbit_manage is not None:` |
| `charts/arr-stack/files/qbit_manage/config.yml` | Generated artifact with `cat_update: false`, `cat: {}`, `!ENV` tags, no plaintext creds | ✓ VERIFIED | Line 10: `cat_update: false`; line 23: `cat: {}`; lines 5-6: `user: !ENV QBT_USER` / `pass: !ENV QBT_PASS`; no plaintext password found |
| `schemas/intent-schema.json` | Contains `QbitManageConfig` definition | ✓ VERIFIED | Line 233 contains `"#/$defs/QbitManageConfig"` reference |
| `tools/arrconf/tests/test_generate_qbit_manage.py` | 10 tests including `test_generate_qbit_manage_yaml_valid` | ✓ VERIFIED | 10 test functions present; all pass (`10 passed in 0.18s`); `test_generate_qbit_manage_yaml_valid` at line 90 asserts `parsed["settings"]["cat_update"] is False` and `parsed["cat"] == {}` |
| `charts/arr-stack/Chart.yaml` | 13th alias `qbit-manage` | ✓ VERIFIED | Line 59: `alias: qbit-manage`; 13 total `alias:` entries confirmed |
| `charts/arr-stack/templates/qbit-manage-configmap.yaml` | ConfigMap rendering `files/qbit_manage/config.yml` | ✓ VERIFIED | File exists (255B); line 4: `name: qbit-manage-config`; line 10: `.Files.Get "files/qbit_manage/config.yml"` |
| `charts/arr-stack/values.yaml` (qbit-manage block) | CronJob block with schedule, envFrom, run-once env, config mount | ✓ VERIFIED | Lines 735-779: complete block with `schedule: "0 */4 * * *"`, `QBT_RUN: "true"`, `QBT_SCHEDULE: "0"`, `envFrom: arrconf-env`, `/config/config.yml` mount, Renovate annotation |
| `.github/workflows/chart-lint.yml` | `qbit-manage` in unpack loop; annotation guard `>= 14`; step name updated | ✓ VERIFIED | Line 48: loop ends with `cross-seed qbit-manage`; line 111: step name `customManagers regex synthetic test (>= 14 matches in values.yaml)`; lines 132-135: guard/messages use `14`; no stale `12` references |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `charts/arr-stack/files/intent.yml` | `charts/arr-stack/files/qbit_manage/config.yml` | `arrconf generate` dispatch in `__main__.py` | ✓ WIRED | `arrconf generate --check` exits 0; `generate_ok` log for `qbit_manage/config.yml` confirmed at runtime |
| `tools/arrconf/arrconf/__main__.py` | `intent_cfg.tools.qbit_manage` | dispatch branch | ✓ WIRED | Line 1046: `if intent_cfg.tools.qbit_manage is not None:` calls `generate_qbit_manage(intent_cfg.tools.qbit_manage)` |
| `charts/arr-stack/templates/qbit-manage-configmap.yaml` | `charts/arr-stack/files/qbit_manage/config.yml` | `.Files.Get` | ✓ WIRED | Line 10: `.Files.Get "files/qbit_manage/config.yml"` — path matches the generated artifact directory |
| `charts/arr-stack/values.yaml` qbit-manage block | `qbit-manage-config` ConfigMap | `persistence.config configMap mount` | ✓ WIRED | Line 775: `name: qbit-manage-config`; ConfigMap template `metadata.name: qbit-manage-config` |
| `charts/arr-stack/values.yaml` qbit-manage block | `arrconf-env` SealedSecret | `envFrom secretRef` | ✓ WIRED | Line 764: `name: arrconf-env` under `envFrom.secretRef` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `generators/intent.py:generate_qbit_manage` | `cfg.rem_orphaned`, `cfg.rem_unregistered`, `cfg.recyclebin_days`, `cfg.share_limits`, `cfg.tracker_tags` | `QbitManageConfig` pydantic model loaded from `intent.yml` | Yes — pure function with no static returns; all config values flow from `cfg.*` parameters | ✓ FLOWING |
| `qbit_manage/config.yml` | `cat_update`, `cat` | Hardcoded in `generate_qbit_manage` string literals (lines 83, 97) | Yes — hardcoded unconditionally, confirmed no `cfg.cat_update` reference exists | ✓ FLOWING |
| `qbt credentials in config.yml` | `user`, `pass` | Hardcoded `!ENV QBT_USER` / `!ENV QBT_PASS` literals; runtime resolution via `arrconf-env` | Yes — `!ENV` tag resolution by qbit_manage at runtime using env injected by `envFrom: arrconf-env` | ? UNVERIFIED (runtime only — see human verification) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `arrconf generate --check` idempotence | `cd tools/arrconf && uv run arrconf generate --check --intent ../../charts/arr-stack/files/intent.yml --output-dir ../../charts/arr-stack/files/` | Exit 0; `generate_ok` for both `cross-seed/config.js` and `qbit_manage/config.yml` | ✓ PASS |
| All qbit_manage tests pass | `cd tools/arrconf && uv run pytest tests/test_generate_qbit_manage.py -q` | 10 passed in 0.18s | ✓ PASS |
| CLI dispatch test passes | `cd tools/arrconf && uv run pytest tests/test_generate_cmd.py -q` | 7 passed in 0.30s | ✓ PASS |
| Full suite (no new regressions) | `cd tools/arrconf && uv run pytest -q` | 520 passed, 3 pre-existing flaky failures (documented in MEMORY.md: respx state leak in test_phase10_idempotence_sweep.py + jellyfin step-order) | ✓ PASS |
| Triade (ruff + mypy) | `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf` | All pass, exit 0 | ✓ PASS |
| `cat_update: false` hardcoded unconditionally | `grep -n "cat_update" generators/intent.py` | Only hardcoded literal at line 83; no `cfg.cat_update` reference exists | ✓ PASS |
| No plaintext credentials in committed config.yml | `grep "'.*password\|\".*password\|passwd:" config.yml` | No matches | ✓ PASS |
| arrconf image tag co-bumped to 0.20.0 | `grep 'tag: "0.20.0"' charts/arr-stack/values.yaml` | Confirmed at line 451 | ✓ PASS |
| values.schema.json has qbit-manage entry | `grep '"qbit-manage"' values.schema.json` | Line 1704: `"qbit-manage": {"type": "object", "additionalProperties": true}` | ✓ PASS |
| chart-lint.yml: no stale `>= 12` guard | `grep "total_matches < 12\|>= 12 " chart-lint.yml` | No matches | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| QBM-01 | 31-01-PLAN.md | L'opérateur déclare `tools.qbit_manage` (share_limits/ratio, recyclebin, tracker_tags, orphaned) dans `intent.yml` | ✓ SATISFIED | `QbitManageConfig` schema in `intent_config.py` with all required fields; `intent.yml` seeded with `tools.qbit_manage` block; `arrconf generate` dispatches to `generate_qbit_manage()` |
| QBM-02 | 31-01-PLAN.md | `arrconf generate` émet `qbit_manage/config.yml` avec `cat_update: False` + `cat: {}` impératifs | ✓ SATISFIED | `generate_qbit_manage()` hardcodes both unconditionally (no conditional path); 3 tests assert this (`_cat_update_false`, `_cat_empty`, `_yaml_valid`); CI `generate --check` blocks any drift |
| QBM-03 | 31-02-PLAN.md | qbit_manage est déployé en CronJob via un alias Helm `app-template` | ✓ SATISFIED | 13th `app-template@5.0.0` alias `qbit-manage` in `Chart.yaml`; CronJob block in `values.yaml` with run-once env, configMap mount, arrconf-env injection; `qbit-manage-configmap.yaml` template wires `files/qbit_manage/config.yml` |

All three requirements covered. No orphaned requirements found — REQUIREMENTS.md traceability table maps QBM-01, QBM-02, QBM-03 exclusively to Phase 31.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `generators/intent.py` line 114-116 | Comment | `UNVERIFIED for qbit_manage v4.6.6: verify post-deploy that untagged torrents actually match this group` (RESEARCH.md A1 — default catch-all `share_limits` group omits `include_all_tags`) | ℹ️ Info | The default catch-all share_limits group emitted by the generator omits `include_all_tags` key, relying on qbit_manage treating absent key as "match all". This is documented as unverified and needs operator confirmation after first cluster run. Not a blocking code defect — the generator produces valid YAML. |

No TODO/FIXME, no stub `return null`/`return {}`, no placeholder patterns in any new files.

### Human Verification Required

#### 1. CronJob Run-Once Lifecycle in Cluster

**Test:** Deploy the chart to the cluster (via ArgoCD sync after Renovate bumps `targetRevision` to the new tag), then observe:
- `kubectl get cronjob -n selfhost qbit-manage` shows the cronjob exists
- Trigger a manual run: `kubectl create job -n selfhost --from=cronjob/qbit-manage qbit-manage-manual-test`
- `kubectl logs -n selfhost job/qbit-manage-manual-test` — verify qbit_manage runs to completion and exits (no daemon hang)
- `kubectl get pod -n selfhost -l job-name=qbit-manage-manual-test` shows `Completed` status

**Expected:** Pod exits with code 0. Logs show qbit_manage processed share_limits, tracker_tags, recyclebin — and explicitly does NOT log any category write operations.

**Why human:** The run-once behaviour (`QBT_RUN=true` + `QBT_SCHEDULE=0`) and qBit category non-interference require a real cluster execution. The committed `config.yml` enforces `cat_update: false` but the runtime honoring of that flag by qbit_manage v4.6.6 cannot be proven without running the actual image.

#### 2. Credential Resolution via !ENV Tags

**Test:** In the cluster pod logs from the test run above, verify:
- No auth error (401/403) connecting to qBittorrent at `http://qbittorrent.selfhost.svc.cluster.local:8080`
- The `arrconf-env` SealedSecret contains `QBT_USER` and `QBT_PASS` keys (check via `kubectl get secret -n selfhost arrconf-env -o jsonpath='{.data}' | jq 'keys'`)

**Expected:** qbit_manage connects to qBittorrent successfully. The `!ENV QBT_USER` / `!ENV QBT_PASS` literals in the ConfigMap are resolved at runtime to the real credentials injected by `envFrom: secretRef: name: arrconf-env`.

**Why human:** The `!ENV` YAML tag is a qbit_manage-specific extension. The committed config.yml contains the tags literally — only a running pod with the real SealedSecret can confirm that qbit_manage v4.6.6 parses and resolves these tags correctly via the environment.

### Gaps Summary

No technical gaps found. All three requirements are implemented and verified:
- QBM-01: `QbitManageConfig` schema + `generate_qbit_manage()` generator + CLI dispatch + seeded `intent.yml` — all wired and tested.
- QBM-02: `cat_update: false` + `cat: {}` hardcoded unconditionally in the generator; 3 dedicated tests confirm; `arrconf generate --check` enforces idempotence.
- QBM-03: 13th Helm alias, ConfigMap template, CronJob values block, CI updates — all present and correctly wired.

Two items require human verification before the phase can be considered fully operational: cluster deployment validation (run-once lifecycle) and credential resolution (runtime `!ENV` tag expansion). These are inherently cluster-runtime concerns that cannot be verified statically.

---

_Verified: 2026-05-31T07:40:00Z_
_Verifier: Claude (gsd-verifier)_
