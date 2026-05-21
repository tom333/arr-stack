---
phase: 09-categories-data-model-chart-initcontainer
verified: 2026-05-18T12:00:00Z
status: human_needed
score: 4/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Deploy arr-stack chart upgrade to the actual cluster (my-kluster); run 'kubectl logs job/arr-stack-categories-init -n selfhost' and verify 10 media_dir_ensured JSON lines are emitted; then run 'kubectl exec -n selfhost deployment/jellyfin -- ls /media/' and verify all 10 /media/<name> directories exist."
    expected: "All 10 directories (series, series-emilie, series-thomas, series-garcons, series-zoe, films, nouveaux-films, films-enfants, films-animation-enfants, films-zoe) are present; Job emits exactly 10 JSON-line events; re-running the upgrade (helm upgrade a second time) produces 0 new created dirs (idempotent)."
    why_human: "ROADMAP SC#3 is a cluster-time gate — the Helm pre-install/pre-upgrade Job's actual execution against the NFS PVC (media-nas-pvc) and NFS root_squash behavior cannot be verified programmatically from the repo without a running cluster. Code review CR-01 also raised a legitimate question about whether the NFS export is chowned to uid 1000 — this must be observed at cluster time."
  - test: "Observe that CR-01 (NFS root_squash / fsGroup interaction) does NOT block the first helm upgrade. If the Job fails, check the pod log for EPERM and validate the NAS export is accessible to uid 1000."
    expected: "Job pod runs as uid 1000, mkdir -p on /media succeeds, all 10 dirs created without EPERM. If it fails, the pre-install hook blocks the chart install and the operator sees 'hook failed' from ArgoCD — recoverable by fixing the NAS export."
    why_human: "CR-01 from the code review is an operational/runtime concern about NFS semantics that cannot be resolved by static analysis. Whether the specific cluster's NAS export allows writes from uid 1000 is a cluster-time observable, not a codebase observable."
---

# Phase 9: Categories Data Model + Chart InitContainer — Verification Report

**Phase Goal:** The `categories[]` data model is declared, schema-validated, and the chart creates the matching filesystem layout — all 6-app propagation code can now be written against a stable contract.
**Verified:** 2026-05-18
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `arrconf schema-gen` produces an updated `schemas/arrconf-schema.json` that validates `categories[]` with required fields; CI fails if schema is stale | VERIFIED | `schemas/arrconf-schema.json` contains `"Category"` type definition and `"categories"` field. `test_schema_committed_matches_regen` passes in live test run (40/40 tests). |
| 2 | `charts/arr-stack/files/arrconf.yml` declares all 10 production categories and passes `arrconf apply --dry-run` | VERIFIED | File has 10-entry `categories:` block with exact (name, kind, profile, display, base_path) tuples. `test_arrconf_yml_has_10_categories` passes. `test_arrconf_yml_categories_ruyaml_roundtrip` passes. |
| 3 | A chart upgrade on the cluster creates `/media/<name>` for each category's `base_path`; re-running is idempotent | UNCERTAIN | Helm Job template renders 20 `media_dir_ensured` printf lines against the 10-entry block (verified by Plan C Task C3 output in SUMMARY.md). The Job CANNOT be verified without a running cluster. See Human Verification section. |
| 4 | An `arrconf.yml` omitting `categories[]` and retaining v0.2.0 flat sections produces identical reconciliation output — no regression | VERIFIED | `test_dry_run_plan_unchanged_without_categories` passes: ruyaml strips the categories block, validates through `RootConfig.model_validate()`, runs all 6 reconcilers, asserts byte-equivalence against frozen baseline. D-13 proven dispositively. |
| 5 | `CLAUDE.md` contains a documented operator procedure for manually `mv`-ing content from v0.2.0 flat dirs to the 10-bucket Categories layout | VERIFIED | `## Filesystem migration: v0.2.0 flat → v0.3.0 Categories` section exists at line 339, correctly placed between `## Pattern single-instance + tags` and `## Intégration avec my-kluster`. Contains 6-row mapping table (7 table rows including header) and 4-step runbook with `tools/snapshot/snapshot.sh`, `kubectl exec deployment/jellyfin`, `RescanSeries`, `RescanMovie`. |

**Score:** 4/5 truths verified (1 requires cluster-time human verification)

### Requirements-Level Must-Haves

| REQ ID | Status | Evidence |
|--------|--------|----------|
| REQ-categories-schema | VERIFIED | `Category` model in `tools/arrconf/arrconf/resources/categories.py`: `extra='forbid'`, kebab-case `name` regex, `Kind`/`Profile` Literal enums, `model_validator(mode='after')` enforcing `base_path == /media/{name}`. Import alias `Category as MediaCategory` in `config.py`. `RootConfig.categories: list[MediaCategory] = Field(default_factory=list)` at line 641. Schema regenerated, `"Category"` and `"categories"` in `schemas/arrconf-schema.json`. 37 parametric tests (7 groups) all passing. |
| REQ-categories-10-target | VERIFIED | `charts/arr-stack/files/arrconf.yml` has 10-entry `categories:` block. Exact (name, kind, profile) tuples match D-01+D-02. `test_arrconf_yml_has_10_categories` asserting count=10, order, tuples, and D-04 base_path invariant — passes. |
| REQ-migration-progressive | VERIFIED | `test_dry_run_plan_unchanged_without_categories` (SC#4 dispositive) passes: categories-stripped arrconf.yml produces byte-equivalent reconciler plan output across all 6 apps. `byte-equivalence-diff.sh` NOT referenced (Pitfall 7 enforced). |
| REQ-filesystem-initcontainer | UNCERTAIN | Helm Job template exists at `charts/arr-stack/templates/categories-init-job.yaml` (75 lines), substantive, wired via `.Files.Get "files/arrconf.yml" | fromYaml`. Renders 20 `media_dir_ensured` lines. Hook annotations, securityContext, image pin, PVC mount all verified in rendered manifest. Cluster-time execution cannot be verified without a running cluster — see CR-01 in code review (NFS root_squash / fsGroup risk). |
| REQ-filesystem-operator-migration | VERIFIED | `CLAUDE.md` section `## Filesystem migration: v0.2.0 flat → v0.3.0 Categories` added at correct position. Contains 6-row v0.2.0→v0.3.0 mapping table, Pre-check (snapshot.sh), Execution (kubectl exec jellyfin), Post-check (RescanSeries/RescanMovie + snapshot diff), Rollback. No `tools/scripts/migrate-to-categories.sh` bash helper (explicitly deferred). |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/arrconf/arrconf/resources/categories.py` | Category model + Kind/Profile enums + base_path invariant | VERIFIED | 51 lines, `class Category(BaseModel)`, `extra="forbid"`, `model_validator(mode="after")`, D-04 enforcement confirmed by test runs. |
| `tools/arrconf/arrconf/config.py` | `RootConfig.categories` field + import alias | VERIFIED | Import `from arrconf.resources.categories import Category as MediaCategory` at line 22. Field `categories: list[MediaCategory] = Field(default_factory=list)` at line 641 (first field in RootConfig). qBit Category import preserved at line 29. |
| `tools/arrconf/tests/test_categories.py` | Parametric pydantic tests, min 80 lines | VERIFIED | 190 lines, 7 test functions covering all invariants (10 happy-path, 8 kebab violations, 5 kind violations, 4 profile violations, 4 base_path violations, 1 extra-forbid, 5 missing-field). |
| `schemas/arrconf-schema.json` | Regenerated JSON Schema with Category type | VERIFIED | Contains `"Category"` type and `"categories"` field. `test_schema_committed_matches_regen` byte-equality gate passes. |
| `charts/arr-stack/templates/categories-init-job.yaml` | Helm-hooked Job, min 50 lines, contains `media_dir_ensured` | VERIFIED | 75 lines, hook annotations, `.Files.Get | fromYaml`, securityContext 1000:1000, `busybox:1.36.1`, `# renovate: image=docker.io/busybox`, `claimName: media-nas-pvc`, `media_dir_ensured` present. |
| `charts/arr-stack/files/arrconf.yml` | 10-entry `categories:` block | VERIFIED | 10 entries in exact order before `sonarr:`, each with correct (name, kind, profile, display, base_path). |
| `tools/arrconf/tests/test_arrconf_yml_validates.py` | `test_arrconf_yml_has_10_categories` function | VERIFIED | Function at line 270, asserts count=10, order, tuples, D-04 base_path. W-03 ruyaml roundtrip test also present at line 301. |
| `tools/arrconf/tests/_phase9_helpers.py` | `dry_run_all_apps` walker, 6 reconcilers | VERIFIED | 389 lines, `def dry_run_all_apps` function present, imports all 6 reconcile_* callables, manages own `respx.mock()` context. |
| `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` | Frozen baseline, `_caveat` field, valid JSON | VERIFIED | 6 app keys + `_caveat`, `_generated`, `_source_yaml` metadata. Valid JSON. |
| `tools/arrconf/tests/test_phase9_no_regression.py` | SC#4 dispositive, min 40 lines, references fixture | VERIFIED | 139 lines, 2 test functions (`test_phase9_no_regression` + `test_dry_run_plan_unchanged_without_categories`), imports `dry_run_all_apps`, references `phase9-baseline-plans.json`. Both pass in live test run. |
| `CLAUDE.md` | Migration runbook section | VERIFIED | Section `## Filesystem migration: v0.2.0 flat → v0.3.0 Categories` at line 339, 7 table rows (1 header + 6 data), 4-step runbook present. |
| `charts/arr-stack/values.yaml` | `arrconf.image.tag` pre-bumped to `"0.5.3"` | VERIFIED | `tag: "0.5.3"` at line 451, under `repository: ghcr.io/tom333/arr-stack-arrconf`, `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` annotation preserved. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tools/arrconf/arrconf/config.py` | `tools/arrconf/arrconf/resources/categories.py` | `from arrconf.resources.categories import Category as MediaCategory` (line 22) | VERIFIED | Import present; `categories: list[MediaCategory]` at line 641. qBit `Category` import preserved at line 29. |
| `charts/arr-stack/templates/categories-init-job.yaml` | `charts/arr-stack/files/arrconf.yml` | `{{- $cfg := .Files.Get "files/arrconf.yml" | fromYaml -}}` (line 20) | VERIFIED | Pattern `\.Files\.Get "files/arrconf\.yml"` present. Plan C Task C3 confirmed 20 `media_dir_ensured` lines rendered against the 10-entry block. |
| `charts/arr-stack/templates/categories-init-job.yaml` | `media-nas-pvc` | `claimName: media-nas-pvc` in Job spec volumes | VERIFIED | `claimName: media-nas-pvc` present at line 75. |
| `tools/arrconf/tests/test_phase9_no_regression.py` | `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` | `json.loads(_BASELINE_FIXTURE.read_text())` | VERIFIED | `phase9-baseline-plans.json` referenced and loaded. Both SC#4 tests pass. |
| `tools/arrconf/tests/test_phase9_no_regression.py` | `tools/arrconf/tests/_phase9_helpers.py` | `from tests._phase9_helpers import dry_run_all_apps` (line 27) | VERIFIED | Import present. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `categories-init-job.yaml` | `$cfg.categories` | `.Files.Get "files/arrconf.yml" | fromYaml` at render time | Yes — 10 entries from committed `arrconf.yml` | FLOWING |
| `config.py:RootConfig.categories` | `MediaCategory` instances | `ruyaml` parse of `arrconf.yml` → `RootConfig.model_validate()` | Yes — 10 entries verified by test | FLOWING |
| `test_phase9_no_regression.py` | `live_output` | `dry_run_all_apps(cfg)` with all 6 reconcilers + respx mocks | Yes — real reconciler plan output frozen in fixture | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Category model rejects bad base_path | `pytest tests/test_categories.py::test_base_path_invariant_violations -x` | 4 PASSED | PASS |
| 10 categories parse from arrconf.yml | `pytest tests/test_arrconf_yml_validates.py::test_arrconf_yml_has_10_categories` | PASSED | PASS |
| SC#4 no-regression dispositive | `pytest tests/test_phase9_no_regression.py -x` | 2 PASSED | PASS |
| Schema CI gate | `pytest tests/test_schema_gen.py::test_schema_committed_matches_regen` | PASSED | PASS |
| Full schema regen byte-equality | `arrconf schema-gen --output /tmp/regen.json && diff schemas/arrconf-schema.json /tmp/regen.json` | Confirmed in SUMMARY (exit 0) | PASS |
| Helm Job renders 20 printf lines | `helm template ... | grep -c 'media_dir_ensured'` | 20 (confirmed in 09-C-SUMMARY.md Task C3) | PASS |
| Cluster-time Job execution | Requires live cluster | Cannot run without cluster | SKIP — routes to human verification |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REQ-categories-schema | 09-A-python-schema-PLAN.md | Category pydantic model + schema regen + CI gate | SATISFIED | categories.py, config.py field, schemas/arrconf-schema.json, test_categories.py (37 tests passing) |
| REQ-categories-10-target | 09-C-arrconf-yml-tests-PLAN.md | 10 production categories in arrconf.yml | SATISFIED | arrconf.yml 10-entry block, test_arrconf_yml_has_10_categories passing |
| REQ-migration-progressive | 09-C-arrconf-yml-tests-PLAN.md | v0.2.0 flat sections unaffected when categories absent | SATISFIED | test_dry_run_plan_unchanged_without_categories passing, D-13 proven |
| REQ-filesystem-initcontainer | 09-B-helm-job-PLAN.md | Helm Job creates /media/<name> dirs | PARTIAL | Code verified; cluster-time execution requires human verification (CR-01 NFS risk) |
| REQ-filesystem-operator-migration | 09-D-docs-release-PLAN.md | CLAUDE.md migration runbook | SATISFIED | Section exists, 6-row table, 4-step runbook, snapshot/kubectl commands present |

**Orphaned requirements check:** All Phase 9 requirements from REQUIREMENTS.md are claimed by the plans above. No orphaned requirements detected. Phase 10 and 11 requirements (propagation, operational polish) are correctly mapped to later phases and not expected here.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `categories-init-job.yaml` | 62-67 | Redundant `[ -d ]` guard before `mkdir -p` (WR-01 from code review) | Warning | Produces union-type structured log events; cosmetic for Phase 9 |
| `categories-init-job.yaml` | 60 | `set -e` causes silent partial-success on multi-dir failures (WR-02) | Warning | Operator sees fewer log events if one mkdir fails; addressable in Phase 10 if needed |
| `categories.py` | 31 | Kebab-case regex `^[a-z0-9]+(-[a-z0-9]+)*$` permits all-digit names like `"42"` (WR-04) | Info | No production category uses all-digits; not a Phase 9 blocker |
| `_phase9_helpers.py` | 82 | `p.read_text()` without `encoding="utf-8"` (IN-02) | Info | CI is Linux/utf-8; no immediate impact |

None of the above are blockers for the Phase 9 goal. WR-01 and WR-02 are quality improvements, WR-04 and IN-02 are info-level. CR-01 (NFS root_squash runtime risk) is the only potential blocker and is handled by the human verification gate.

### Human Verification Required

#### 1. Cluster-time Helm Job execution (ROADMAP SC#3)

**Test:** Trigger `helm upgrade arr-stack` on the production cluster (via my-kluster Renovate PR bumping `targetRevision` to `v0.5.3`). After ArgoCD sync:
1. `kubectl logs job/arr-stack-categories-init -n selfhost` — check for 10 JSON lines with `"event":"media_dir_ensured"`
2. `kubectl exec -n selfhost deployment/jellyfin -- ls /media/ | sort` — verify all 10 directory names appear
3. Trigger a second `helm upgrade` (or ArgoCD re-sync) — verify 0 new `created:true` events (idempotent)

**Expected:** 10 `media_dir_ensured` JSON events on first run. All 10 `/media/<name>` dirs visible under `/media/`. Second run emits 10 `existed:true` events, 0 `created:true` (idempotent).

**Why human:** Cluster-time gate. The NFS PVC `media-nas-pvc` backed by NAS NFS share must be accessible to uid 1000. Code review CR-01 identified a potential EPERM risk if the NFS export is not chowned to uid 1000:1000 or the server's `root_squash` doesn't map correctly. Static analysis confirms the Job template is correct; runtime behavior depends on actual NAS configuration.

#### 2. CR-01 NFS operability validation

**Test:** Before running the cluster upgrade, verify NFS write access from uid 1000: `kubectl run --rm -it --image=busybox:1.36.1 --overrides='{"spec":{"securityContext":{"runAsUser":1000,"runAsGroup":1000}}}' nfs-probe -- sh -c "touch /media/.arrconf-write-probe && echo OK && rm /media/.arrconf-write-probe"` (with appropriate volume mount overrides for `media-nas-pvc`).

**Expected:** Command prints `OK` without EPERM.

**Why human:** The NAS NFS export configuration (ownership, `root_squash`, ID mapping) is a cluster-environment observable. The SUMMARY notes (Plan B) that 09-RESEARCH.md Q2 showed NFS accessible=true for uid 1000 from existing snapshots, but this was inferential, not a direct write-test. CR-01 rates this as a potential deploy blocker. Confirming before the first production helm upgrade reduces rollback risk.

### Code Review Integration

The code review at `09-REVIEW.md` identified **1 BLOCKER (CR-01)** and 5 WARNINGs + 5 INFO items.

**CR-01 disposition:** CR-01 is classified as an **operational/runtime concern**, not a phase-goal code failure. The phase goal is "data model declared, schema-validated, chart creates filesystem layout" — the chart Job template is correctly authored. Whether `mkdir -p` succeeds at cluster time depends on NAS configuration that is outside the codebase. This is a UAT gate, not a code defect. The finding is surfaced as a human verification item above rather than a BLOCKER for `status: gaps_found`.

**WR-01, WR-02, WR-03, WR-04 disposition:** All are quality improvements with no impact on Phase 9 goal achievement. They are noted in Anti-Patterns above and can be addressed in Phase 10 if desired.

**IN-01 through IN-05:** Info-level; no impact on goal.

### Gaps Summary

No code-level gaps found. The five Phase 9 requirements are either fully satisfied (4) or pending cluster-time verification (1 — REQ-filesystem-initcontainer, ROADMAP SC#3). All artifacts exist, are substantive, and are correctly wired. The SC#4 no-regression test provides dispositive evidence for D-13 (reconcilers don't consume categories[]). The schema CI gate is in place and passing. The CLAUDE.md migration runbook is complete.

The only outstanding item is the cluster-time execution of the Helm pre-install/pre-upgrade Job — this cannot be verified from the codebase alone and requires the operator to complete the ADR-6 pre-deploy snapshot then merge the Renovate PR in my-kluster.

---

_Verified: 2026-05-18_
_Verifier: Claude (gsd-verifier)_
