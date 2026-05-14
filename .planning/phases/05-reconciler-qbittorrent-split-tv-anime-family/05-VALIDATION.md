---
phase: 5
slug: reconciler-qbittorrent-split-tv-anime-family
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: 05-RESEARCH.md `## Validation Architecture` section + ROADMAP Success Criteria 1–6.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + respx (httpx mocking) — established in Phase 1+ |
| **Config file** | `tools/arrconf/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cd tools/arrconf && uv run pytest -x -q tests/test_qbittorrent.py tests/test_sonarr_split.py tests/test_radarr_split.py` |
| **Full suite command** | `cd tools/arrconf && uv run pytest -v --cov=arrconf --cov-fail-under=70` |
| **Estimated runtime** | ~15–25 seconds (mocked APIs via respx) |

Cluster-side validation (post-deploy, manual-gated):

| Property | Value |
|----------|-------|
| **Snapshot tool** | `tools/snapshot/snapshot.sh --apps sonarr,radarr,qbittorrent` |
| **Idempotence proof (SC#5)** | `kubectl -n selfhost create job --from=cronjob/arrconf arrconf-idem-test && kubectl logs job/arrconf-idem-test` — must log `no-op` per resource type |
| **Diff against baseline** | `diff -r snapshots/before-phase-5-<date>/ snapshots/after-phase-5-<date>/` |

---

## Sampling Rate

- **After every task commit:** Run quick command for the touched module (`pytest tests/test_<module>.py -x`).
- **After every plan wave:** Run the full suite (`pytest -v --cov`). Coverage must remain ≥ 70% on `differ.py` and `reconcilers/`.
- **Before `/gsd-verify-work`:** Full suite green + cluster-side smoke test SC#4 + `arrconf diff` SC#5 = 0 actions.
- **Max feedback latency:** 30 seconds (unit suite) / 5 min (cluster CronJob trigger).

---

## Per-Task Verification Map

Tasks listed by expected plan layout (planner may refine). One row per acceptance-criterion bundle.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-00-01 | 00 (pre-flight) | 0 | REQ-app-coverage | — | Operator confirms `arrconf-env` Secret has 5 required keys (D-05-BOOTSTRAP-01) | checkpoint:human-action | `kubectl -n selfhost get secret arrconf-env -o json \| jq '.data \| keys'` shows `[QBT_PASS,QBT_USER,PROWLARR_API_KEY,RADARR_API_KEY,SONARR_API_KEY]` | ❌ W0 (operator action) | ⬜ pending |
| 05-00-02 | 00 | 0 | REQ-app-coverage | — | Baseline snapshot captured (ADR-6 / D-05-SNAPSHOT-01) | shell | `test -d snapshots/before-phase-5-$(date +%F)/qbittorrent && test -d snapshots/before-phase-5-$(date +%F)/sonarr && test -d snapshots/before-phase-5-$(date +%F)/radarr` | ✅ | ⬜ pending |
| 05-01-01 | 01 (schema) | 1 | REQ-app-coverage | — | `RootConfig` accepts `qbittorrent: dict[str, QbittorrentInstance]` and rejects unknown keys (`extra='forbid'`) | unit | `pytest tests/test_config.py::test_qbittorrent_schema_roundtrip -x` | ✅ W0 stub | ⬜ pending |
| 05-01-02 | 01 | 1 | REQ-app-coverage | — | `arrconf schema-gen` emits a JSON Schema covering `qbittorrent` block | unit | `pytest tests/test_schema_gen.py::test_includes_qbittorrent -x && jq -e '.properties.qbittorrent' schemas/arrconf-schema.json` | ✅ W0 stub | ⬜ pending |
| 05-01-03 | 01 | 1 | REQ-app-coverage | — | Fail-fast env-var check: `arrconf apply --apps sonarr,radarr,prowlarr,qbittorrent` exits 2 when `QBT_USER`/`QBT_PASS` missing (D-05-BOOTSTRAP-01) | unit | `pytest tests/test_main.py::test_missing_env_exits_2 -x` | ✅ W0 stub | ⬜ pending |
| 05-02-01 | 02 (qbit client) | 2 | REQ-app-coverage | T-05-AUTH | Cookie auth: `POST /api/v2/auth/login` with `Referer` header sets `SID` cookie; subsequent requests send it | unit | `pytest tests/test_qbittorrent.py::test_login_sets_cookie -x` | ✅ W0 stub | ⬜ pending |
| 05-02-02 | 02 | 2 | REQ-app-coverage | T-05-AUTH | Login retry on HTTP 403 (whitelist mismatch) raises actionable error referencing `AuthSubnetWhitelistEnabled` | unit | `pytest tests/test_qbittorrent.py::test_403_actionable_error -x` | ✅ W0 stub | ⬜ pending |
| 05-02-03 | 02 | 2 | REQ-app-coverage | — | Categories CRUD: `GET /api/v2/torrents/categories` parsed, missing categories created via `createCategory`, savePath changes trigger `editCategory`, no DELETE without `prune:true` | unit | `pytest tests/test_qbittorrent.py::TestCategories -x` | ✅ W0 stub | ⬜ pending |
| 05-02-04 | 02 | 2 | REQ-app-coverage | — | Preferences subset reconcile: only the keys declared in YAML are PUT via `setPreferences`; operator-managed keys untouched | unit | `pytest tests/test_qbittorrent.py::test_preferences_partial_diff -x` | ✅ W0 stub | ⬜ pending |
| 05-02-05 | 02 | 2 | REQ-app-coverage | — | No-op on second reconcile (idempotence) | unit | `pytest tests/test_qbittorrent.py::test_idempotent_no_op -x` | ✅ W0 stub | ⬜ pending |
| 05-03-01 | 03 (sonarr+radarr split) | 2 | REQ-app-coverage | — | tags / root_folders / download_clients / remote_path_mappings each diff/create/update idempotently | unit | `pytest tests/test_sonarr_split.py -x` | ✅ W0 stub | ⬜ pending |
| 05-03-02 | 03 | 2 | REQ-app-coverage | T-05-ORDER | Reconcile ordering invariant: tags before download_clients; series/movie editor (D-05-MIG-01) AFTER download_clients | unit | `pytest tests/test_sonarr_split.py::test_reconcile_order -x` | ✅ W0 stub | ⬜ pending |
| 05-03-03 | 03 | 2 | REQ-app-coverage | — | Path Mapping diff matches by `(host, remotePath, localPath)` tuple; existing operator-set mappings preserved | unit | `pytest tests/test_remote_path_mapping.py -x` | ✅ W0 stub | ⬜ pending |
| 05-04-01 | 04 (retroactive tag) | 2 | REQ-app-coverage | T-05-CONTENT | `series/editor` bulk PUT with `applyTags: "add"`, `moveFiles: false`, `deleteFiles: false`; existing operator tags preserved | unit | `pytest tests/test_sonarr.py::test_series_editor_bulk_tag -x` | ✅ W0 stub | ⬜ pending |
| 05-04-02 | 04 | 2 | REQ-app-coverage | T-05-CONTENT | Idempotent: re-run does not re-tag already-tagged series | unit | `pytest tests/test_sonarr.py::test_series_editor_idempotent -x` | ✅ W0 stub | ⬜ pending |
| 05-04-03 | 04 | 2 | REQ-app-coverage | T-05-CONTENT | Radarr `movie/editor` mirror of 05-04-01 + 05-04-02 with default tag `movies` | unit | `pytest tests/test_radarr.py::TestMovieEditor -x` | ✅ W0 stub | ⬜ pending |
| 05-05-01 | 05 (chart + values) | 3 | REQ-app-coverage | — | `charts/arr-stack/files/arrconf.yml` validates against generated JSON Schema | unit | `pytest tests/test_arrconf_yml_validates.py -x` | ✅ W0 stub | ⬜ pending |
| 05-05-02 | 05 | 3 | REQ-app-coverage | — | `values.yaml` alias `arrconf` args = `[..., "apply", "--apps", "sonarr,radarr,prowlarr,qbittorrent"]` (D-05-ARGS-01) | unit | `yq '.arrconf.controllers.main.containers.main.args' charts/arr-stack/values.yaml \| grep -q 'qbittorrent'` | ✅ | ⬜ pending |
| 05-05-03 | 05 | 3 | REQ-app-coverage | — | `helm lint && helm template charts/arr-stack/ -f examples/values-prod.yaml \| kubeconform -` exits 0 | integration | `bash tools/scripts/byte-equivalence-diff.sh` (Phase 4 helper) | ✅ | ⬜ pending |
| 05-06-01 | 06 (configarr) | 3 | REQ-app-coverage | — | configarr YAML lists 3 quality profiles per instance (MULTi.VF, Anime, Family) with `assign_scores_to` mapping | unit | `pytest tests/test_configarr_yml.py::test_three_profiles_per_instance -x` | ✅ W0 stub | ⬜ pending |
| 05-06-02 | 06 | 3 | REQ-app-coverage | — | Family profile scoring matches MULTi.VF byte-for-byte (D-05-FAM-01) | unit | `pytest tests/test_configarr_yml.py::test_family_clone_of_multivf -x` | ✅ W0 stub | ⬜ pending |
| 05-07-01 | 07 (cluster apply) | 4 | REQ-app-coverage | — | Manual `kubectl create job --from=cronjob/arrconf` succeeds; logs show creation of 6 qBit categories + 6 tags + 6 root folders + 6 download clients + N path mappings | checkpoint:human-action | `kubectl -n selfhost logs job/arrconf-phase5-apply \| grep -c 'created' >= 30` | ❌ W0 (cluster) | ⬜ pending |
| 05-07-02 | 07 | 4 | REQ-app-coverage | — | SC#4 end-to-end: operator adds anime series in Sonarr UI with tag `anime`; file lands in `/data/anime/<series>` then `/media/anime/<series>` (NFS copy, hardlinks impossible per pre-existing constraint) | checkpoint:human-action | Manual UI walkthrough; verify `kubectl exec deploy/sonarr -- ls /media/anime/` shows the new series dir | ❌ W0 (operator + cluster) | ⬜ pending |
| 05-07-03 | 07 | 4 | REQ-app-coverage | — | SC#5 idempotence proof: second `arrconf apply` after smoke test = 0 mutations (zero `created`/`updated` log events) | checkpoint:human-action | `kubectl logs job/arrconf-idem-test \| grep -E 'created\|updated' \| wc -l` equals `0` | ❌ W0 (cluster) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tools/arrconf/tests/test_qbittorrent.py` — fixtures for categories CRUD, preferences, login flow (mocked via respx)
- [ ] `tools/arrconf/tests/fixtures/qbittorrent_categories_v2.json` — sanitized capture of `GET /api/v2/torrents/categories` baseline
- [ ] `tools/arrconf/tests/fixtures/qbittorrent_preferences_v2.json` — sanitized capture of `GET /api/v2/app/preferences`
- [ ] `tools/arrconf/tests/fixtures/sonarr_remote_path_mapping_v3.json` — sanitized capture of `GET /api/v3/remotepathmapping`
- [ ] `tools/arrconf/tests/fixtures/sonarr_series_editor_request.json` — golden payload for `PUT /api/v3/series/editor`
- [ ] `tools/arrconf/tests/fixtures/radarr_movie_editor_request.json` — golden payload for `PUT /api/v3/movie/editor`
- [ ] `tools/arrconf/tests/test_config.py::test_qbittorrent_schema_roundtrip` — pydantic schema accepts new `qbittorrent:` block
- [ ] `tools/arrconf/tests/test_main.py::test_missing_env_exits_2` — fail-fast env-var check
- [ ] `tools/arrconf/tests/test_remote_path_mapping.py` — new resource type tests
- [ ] `tools/arrconf/tests/test_arrconf_yml_validates.py` — chart fixture validates against generated JSON Schema

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Operator adds 4 missing keys to `arrconf-env` Secret | REQ-app-coverage (D-05-BOOTSTRAP-01) | Out-of-git secret bootstrap (ESO is Phase 8 scope) | `kubectl edit -n selfhost secret/arrconf-env` then add `RADARR_API_KEY`, `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS` (base64-encoded). Operator confirms via `kubectl get secret arrconf-env -o json \| jq '.data \| keys'`. |
| SC#4 end-to-end smoke test (anime series download routing) | REQ-app-coverage (ROADMAP SC#4) | Touches real Sonarr UI + Prowlarr/indexer + live qBit download | Operator adds series tagged `anime` via Sonarr UI, monitors qBit for category `sonarr-anime`, verifies `/data/anime/<series>` appears, then `/media/anime/<series>` after Sonarr import. |
| SC#5 `arrconf diff` after smoke = 0 actions | REQ-app-coverage (ROADMAP SC#5) | Requires the smoke-test state to be live | Trigger `kubectl create job --from=cronjob/arrconf arrconf-idem` and inspect logs — no `created`/`updated` lines. |
| Recyclarr/configarr profile activation in Sonarr/Radarr | REQ-app-coverage (ROADMAP SC#6) | configarr runs out-of-band from arrconf; UI must show 3 profiles | `kubectl exec deploy/sonarr -- curl -sS -H "X-Api-Key: $SONARR_API_KEY" http://localhost:8989/api/v3/qualityprofile \| jq '.[] \| .name'` must list `MULTi.VF`, `Anime`, `Family`. Same for Radarr. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (cluster-apply tasks 05-07-* are the only manual-gated stretch and follow ≥10 automated tasks)
- [ ] Wave 0 covers all MISSING references (fixtures + schema test stubs)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s for unit suite
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
