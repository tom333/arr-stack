---
phase: 14-suggestarr-implementation
plan: "03"
subsystem: tests + uat
tags:
  - tests
  - uat
  - integration-test
  - chart-artifacts
  - web-ui-config
dependency_graph:
  requires:
    - 14-02 (values.yaml SuggestArr block + evidence files)
  provides:
    - chart-artifacts integration test (CI-blocking regression guard)
    - operator UAT runbook for Phase 14 close
  affects:
    - tools/arrconf/tests/ (new test file)
    - .planning/phases/14-suggestarr-implementation/ (new UAT doc)
tech_stack:
  added:
    - ruyaml (existing dep reused for YAML parsing in the test — no new dep added)
  patterns:
    - yaml-parse-only integration test (no arrconf runtime exercised — D-11 no co-bump)
    - subprocess helm template for rendered-manifest assertions
    - pytest.skip guard for helm-absent environments
key_files:
  created:
    - tools/arrconf/tests/test_suggestarr_chart_artifacts.py
    - .planning/phases/14-suggestarr-implementation/14-HUMAN-UAT.md
  modified: []
decisions:
  - "D-10 revision-2 narrowed scope: test asserts chart-side mechanics only (env remap,
    Renovate annotation, no Ingress, alias listed, dep unpacked, no ConfigMap, PVC 1Gi)"
  - "D-11 no co-bump: test-only addition under tools/arrconf/tests/ does not touch
    arrconf runtime — arrconf.image.tag stays at 0.7.0"
  - "D-13 ordering rule: UAT Pre-deploy gate documents that my-kluster SealedSecret
    TMDB_API_KEY PR must merge BEFORE arr-stack PR"
  - "SC#3 verification moves from CI (deleted ConfigMap test surface) to operator
    UAT (Scenario 3 web-UI paste from derived-routing-values.md)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 14 Plan 03: Chart Artifacts Test + Human UAT Summary

**One-liner:** Integration test for SuggestArr chart-side mechanics (15 pytest functions,
all green) + operator UAT runbook covering Pre-deploy gate (D-13), 5 SC scenarios, and
Scenario 3 web-UI routing-config configuration step from `derived-routing-values.md`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 3.1 | Chart-artifacts integration test | `354a27c` | `tools/arrconf/tests/test_suggestarr_chart_artifacts.py` |
| 3.2 | 14-HUMAN-UAT.md operator runbook | `f51adaa` | `.planning/phases/14-suggestarr-implementation/14-HUMAN-UAT.md` |

## Task 3.1 — Chart-artifacts integration test

**File:** `tools/arrconf/tests/test_suggestarr_chart_artifacts.py`
**Test count:** 15 `def test_*` functions (exceeds ≥12 minimum)
**Test result:** 15 passed, 0 failed, 0 skipped (helm is on PATH, so all helm-template
tests ran — none skipped)
**Lines:** 331 (exceeds ≥100 minimum)

### Test coverage per D-10 scope

| Scope | Tests | What is asserted |
|-------|-------|-----------------|
| (a) D-01 env remap | 4 tests | JELLYFIN_TOKEN→JELLYFIN_API_KEY, SEER_TOKEN→SEERR_API_KEY, TMDB_API_KEY direct; all secretKeyRef target arrconf-env |
| (b) D-09 Renovate annotation | 1 test | Annotation `# renovate: image=docker.io/ciuse99/suggestarr` is on the line immediately above `repository:` |
| (c) D-14 no ingress | 1 test | `ingress` key absent from suggestarr: block |
| (d) Alias listed | 2 tests | `suggestarr` in Chart.yaml deps; exactly 11 total aliases |
| (e) Dep dir unpacked | 1 test | `charts/arr-stack/charts/suggestarr/Chart.yaml` exists + has name=app-template |
| (f) helm template kinds | 5 tests | Deployment present (with ciuse99/suggestarr image), PVC present, Service present; no ConfigMap named suggestarr-config; no configmap template or source file in repo |
| (g) PVC 1Gi | 1 test | type=persistentVolumeClaim, size=1Gi, accessMode=ReadWriteOnce |

### Technical notes

- **YAML parsing**: uses `ruyaml` (existing project dependency) — no new dep or
  `co-bump` (D-11).
- **helm template tests**: use `subprocess.run(["helm", "template", ...])` with
  `pytest.skip` guard when `helm` is absent. On this machine helm 4.2.0 was on PATH,
  so all 5 helm-template tests ran.
- **mypy**: passes strict mode. Two `# type: ignore` annotations needed:
  `dict` with `type-arg` (ruyaml return type) and `no-any-return` for `.load()`.
- **ruff**: passes with zero warnings after resolving E501 line-length violations.

## Task 3.2 — 14-HUMAN-UAT.md operator runbook

**File:** `.planning/phases/14-suggestarr-implementation/14-HUMAN-UAT.md`
**Word count:** 1656 (exceeds ≥900 minimum)
**Sections:**

1. **Pre-deploy gate (D-13)** — TMDB_API_KEY SealedSecret add in my-kluster repo.
   Step 1: Obtain TMDB key. Step 2: kubeseal re-seal + PR. Step 3: merge FIRST with
   cluster-verification commands. Explicit blocker: "Only proceed AFTER secret verified."
2. **SC#1 (Scenario 1)** — Deployment/PVC/Service presence + negative ConfigMap check.
3. **SC#2 (Scenario 2)** — Jellyfin + Seerr connectivity via log observation.
4. **SC#3 (Scenario 3)** — Canonical web-UI routing-config configuration (revision-2):
   - 3a.i: Settings → Jellyfin → Libraries (paste from `derived-routing-values.md`)
   - 3a.ii: Settings → Seer Integration → Profile Config (paste SEER_ANIME_PROFILE_CONFIG
     JSON — included verbatim with profileId/rootFolder values from `derived-routing-values.md`)
   - 3b: Trigger scan, observe routed Seerr requests, D-08 family-bucket caveat
5. **SC#4 (Scenario 4)** — ArgoCD sync verification.
6. **SC#5 (Scenario 5)** — D-11 co-bump N/A documented.
7. **Post-UAT** — STATE.md + ROADMAP.md update procedure.
8. **Rollback procedure** — replica=0 + targetRevision revert path.

### Key design decisions captured

- **D-08 family-bucket limitation**: documented in SC#3 Scenario 3b dispositive checklist.
  Watch events from `/media/series-garcons`, `/media/films-enfants` etc. route to
  `default_tv`/`default_movie` — accepted limitation, not a Phase 14 defect.
- **Revision-2 no-ConfigMap**: SC#1 includes a negative check for `suggestarr-config`
  ConfigMap (must return NotFound). The UAT does NOT reference `files/suggestarr-config.yml`
  as a chart artifact.
- **Scenario 3 as canonical SC#3**: routing-config correctness is now operator-UAT only
  (not CI), because SuggestArr silently ignores file-based config injection — only the
  web UI persistence layer works. The SEER_ANIME_PROFILE_CONFIG JSON is pasted verbatim
  from `derived-routing-values.md` into the web UI post-deploy.

## Deviations from Plan

None — plan executed exactly as written. The only adaptation was switching from `import yaml`
(PyYAML, not installed) to `from ruyaml import YAML` (already a project dependency) to avoid
adding a new dev dep. This is purely an implementation detail of Task 3.1 — no semantic
deviation from the test scope.

## Verification

### Python triad (tools/arrconf/)

- `uv run ruff format --check tests/test_suggestarr_chart_artifacts.py` — passed (1 file already formatted)
- `uv run ruff check tests/test_suggestarr_chart_artifacts.py` — passed (All checks passed!)
- `uv run mypy tests/test_suggestarr_chart_artifacts.py` — passed (Success: no issues found)

### Test run

```
tests/test_suggestarr_chart_artifacts.py::test_d01_env_remap_jellyfin_token_to_jellyfin_api_key PASSED
tests/test_suggestarr_chart_artifacts.py::test_d01_env_remap_seer_token_to_seerr_api_key PASSED
tests/test_suggestarr_chart_artifacts.py::test_d01_env_remap_tmdb_api_key_direct PASSED
tests/test_suggestarr_chart_artifacts.py::test_all_secret_refs_target_arrconf_env_with_expected_keys PASSED
tests/test_suggestarr_chart_artifacts.py::test_d09_renovate_annotation_present_and_correctly_formatted PASSED
tests/test_suggestarr_chart_artifacts.py::test_d14_no_ingress_block_under_suggestarr PASSED
tests/test_suggestarr_chart_artifacts.py::test_d_suggestarr_alias_listed_in_chart_yaml PASSED
tests/test_suggestarr_chart_artifacts.py::test_d_chart_yaml_has_exactly_11_aliases PASSED
tests/test_suggestarr_chart_artifacts.py::test_e_suggestarr_dep_dir_unpacked PASSED
tests/test_suggestarr_chart_artifacts.py::test_f_helm_template_emits_suggestarr_deployment PASSED
tests/test_suggestarr_chart_artifacts.py::test_f_helm_template_emits_suggestarr_pvc PASSED
tests/test_suggestarr_chart_artifacts.py::test_f_helm_template_emits_suggestarr_service PASSED
tests/test_suggestarr_chart_artifacts.py::test_f_helm_template_does_not_emit_suggestarr_config_configmap PASSED
tests/test_suggestarr_chart_artifacts.py::test_f_no_suggestarr_configmap_template_file_in_repo PASSED
tests/test_suggestarr_chart_artifacts.py::test_g_pvc_declared_1gi PASSED
15 passed in 7.86s
```

### Full test suite (no regressions)

`uv run pytest tests/ -x -q` — 385 passed, 1 skipped (16.27s).
Prior baseline: 370 tests. New tests: +15. Regression: 0.

### Negative checks

- `tools/arrconf/tests/test_suggestarr_routing_config.py` — does NOT exist (revision-2 rename)
- `charts/arr-stack/templates/suggestarr-configmap.yaml` — does NOT exist
- `charts/arr-stack/files/suggestarr-config.yml` — does NOT exist
- `charts/arr-stack/values.yaml#arrconf.image.tag` — unchanged at `0.7.0` (D-11)
- No `tools/arrconf/arrconf/` production code touched

## Phase 14 Closure Handoff

Phase 14 is now code-complete (Plans 01+02+03 executed). The remaining steps to close
Phase 14 are all operator-driven:

1. **Pre-deploy gate** (blocking): open my-kluster PR to add `TMDB_API_KEY` to
   `arrconf-env` SealedSecret (per `14-HUMAN-UAT.md` §"Pre-deploy gate").
2. **arr-stack PR merge**: after my-kluster PR is merged and secret is cluster-verified,
   merge the arr-stack Phase 14 branch. Auto-tag creates `v0.7.x`.
3. **my-kluster Renovate PR**: bumps `targetRevision` to the new `v0.7.x` tag. Merge.
4. **ArgoCD sync**: SuggestArr pod starts (SC#4 green once sync completes without
   `CreateContainerConfigError`).
5. **Scenario 3 web-UI configuration**: operator port-forwards to SuggestArr web UI
   and pastes JELLYFIN_LIBRARIES + SEER_ANIME_PROFILE_CONFIG from
   `.planning/phases/14-suggestarr-implementation/evidence/derived-routing-values.md`.
6. **SC#3 live observation**: trigger a watch event in Jellyfin, observe a routed
   Seerr request within 60 minutes.
7. **Phase close**: update STATE.md + ROADMAP.md once all 5 SC checklists in
   `14-HUMAN-UAT.md` are checked off.

## Known Stubs

None. The test file and UAT document contain no stubs. The evidence file
`derived-routing-values.md` (Plan 02 Task 2.1 output) contains real live-cluster values
(Jellyfin ItemIds, Sonarr/Radarr profile IDs) — not placeholders.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes
were introduced in this plan. The test file is read-only (parses YAML + calls helm
template); the UAT doc is documentation only.

## Self-Check: PASSED

- `tools/arrconf/tests/test_suggestarr_chart_artifacts.py` — FOUND
- `.planning/phases/14-suggestarr-implementation/14-HUMAN-UAT.md` — FOUND
- Commit `354a27c` (Task 3.1) — FOUND
- Commit `f51adaa` (Task 3.2) — FOUND
- arrconf.image.tag=0.7.0 — CONFIRMED
- No tools/arrconf/arrconf/ production code touched — CONFIRMED
