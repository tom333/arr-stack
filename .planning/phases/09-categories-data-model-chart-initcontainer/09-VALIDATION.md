---
phase: 9
slug: categories-data-model-chart-initcontainer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-18
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `09-RESEARCH.md` §Validation Architecture. Refine during execute-phase.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (Python)** | pytest 9.0 + respx 0.23 + ruff + mypy strict (existing) |
| **Framework (Helm)** | helm 3.18 + kubeconform 1.33 + 5 in-CI guard scripts |
| **Config file** | `tools/arrconf/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd tools/arrconf && uv run pytest tests/test_categories.py tests/test_schema_gen.py tests/test_arrconf_yml_validates.py -x` |
| **Full suite command (Python)** | `cd tools/arrconf && uv run ruff check . && uv run ruff format --check . && uv run mypy arrconf && uv run pytest --cov --cov-report=term-missing --cov-fail-under=70` |
| **Full suite command (Helm)** | `helm lint charts/arr-stack/ -f examples/values-prod.yaml && helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \| kubeconform -strict -ignore-missing-schemas` |
| **Estimated runtime** | ~30 sec quick run; ~3 min full Python suite; ~1 min Helm |

---

## Sampling Rate

- **After every task commit:** Run `cd tools/arrconf && uv run pytest tests/test_categories.py tests/test_schema_gen.py -x` (~5 sec)
- **After every plan wave:** Full `pytest` suite + `helm lint` + `kubeconform`
- **Before `/gsd-verify-work`:** Full `tests.yml` + `chart-lint.yml` green; SC#4 dispositive pytest green
- **Max feedback latency:** 60 sec for quick run; 5 min for full suite

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-A-* | A (Python schema) | 1 | REQ-categories-schema | — | pydantic `extra='forbid'` rejects unknown fields; `base_path` invariant enforced | unit | `cd tools/arrconf && uv run pytest tests/test_categories.py -x` | ❌ Wave 0 (NEW) | ⬜ pending |
| 09-A-* | A (Python schema) | 1 | REQ-categories-schema | — | Schema regen reproducible; CI fails on stale | unit | `cd tools/arrconf && uv run pytest tests/test_schema_gen.py::test_schema_committed_matches_regen -x` | ✅ EXISTING | ⬜ pending |
| 09-A-* | A (Python schema) | 1 | REQ-categories-schema | — | `RootConfig.categories: list[Category]` field present | unit | `cd tools/arrconf && uv run python -c 'from arrconf.config import RootConfig; assert "categories" in RootConfig.model_fields'` | ❌ Wave 0 (covered by Wave 0 import) | ⬜ pending |
| 09-B-* | B (Helm Job) | 1 | REQ-filesystem-initcontainer | — | Job template renders valid K8s manifest | integration | `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \| kubeconform -strict -ignore-missing-schemas` | ✅ EXISTING (chart-lint.yml) | ⬜ pending |
| 09-B-* | B (Helm Job) | 1 | REQ-filesystem-initcontainer | — | Job has `helm.sh/hook: pre-install,pre-upgrade` | integration | `helm template ... \| grep -A2 'helm.sh/hook' \| grep -E 'pre-(install\|upgrade)'` | ❌ Wave 0 (new chart-lint grep guard, optional) | ⬜ pending |
| 09-B-* | B (Helm Job) | 1 | REQ-filesystem-initcontainer | — | Job iterates `.Files.Get \| fromYaml` over categories (10 mkdir lines rendered) | integration | `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \| grep -c 'media_dir_ensured'` returns 20 (10 created + 10 existed printf branches) | ❌ Wave 1 | ⬜ pending |
| 09-C-* | C (arrconf.yml + tests) | 2 | REQ-categories-10-target | — | 10 categories with exact production names | unit | `cd tools/arrconf && uv run pytest tests/test_arrconf_yml_validates.py::test_arrconf_yml_has_10_categories -x` | ❌ Wave 2 (extend existing) | ⬜ pending |
| 09-C-* | C (arrconf.yml + tests) | 2 | REQ-categories-10-target | — | All 10 entries pass pydantic validation on `arrconf apply --dry-run` | integration | `cd tools/arrconf && uv run arrconf apply --config ../../charts/arr-stack/files/arrconf.yml --dry-run` exits 0 | ❌ Wave 2 (smoke check in test) | ⬜ pending |
| 09-C-* | C (arrconf.yml + tests) | 2 | REQ-migration-progressive | — | Reconcile plan output unchanged when categories[] absent | unit | `cd tools/arrconf && uv run pytest tests/test_phase9_no_regression.py -x` | ❌ Wave 2 (NEW) | ⬜ pending |
| 09-D-* | D (CLAUDE.md + release) | 2 | REQ-filesystem-operator-migration | — | Migration runbook section exists in CLAUDE.md | unit | `grep -F '## Filesystem migration: v0.2.0 flat → v0.3.0 Categories' CLAUDE.md` exits 0 | ❌ Wave 2 | ⬜ pending |
| 09-D-* | D (CLAUDE.md + release) | 2 | REQ-filesystem-operator-migration | — | `charts/arr-stack/values.yaml#arrconf.image.tag` pre-bumped to upcoming auto-tag (CF-07-CHART-PIN-LOOP) | unit | `git diff HEAD~1 charts/arr-stack/values.yaml \| grep -E 'arrconf.*tag'` shows change | ❌ Wave 2 (manual PR-review gate) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tools/arrconf/tests/test_categories.py` — NEW; parametric tests for `Category` model (valid 10-entry input + invalid permutations: wrong kind enum, wrong profile enum, base_path mismatch, duplicate name, kebab-case violations)
- [ ] `tools/arrconf/tests/test_phase9_no_regression.py` — NEW; reconciler-plan byte-equivalence test (SC#4 dispositive). Uses a frozen fixture (see below) + respx mocks.
- [ ] `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` — NEW; frozen reconciler plan output captured by Plan C engineer for diff baseline
- [ ] `tools/arrconf/tests/test_arrconf_yml_validates.py` — EXTEND existing (if present) or NEW; assert the 10 production categories are present in `charts/arr-stack/files/arrconf.yml` and each parses through `RootConfig`
- [x] pytest + respx + ruff + mypy framework already installed via `uv sync --frozen` in `tests.yml`
- [x] helm lint + kubeconform already wired in `chart-lint.yml`
- [x] `test_schema_gen.py::test_schema_committed_matches_regen` already exists (no Wave 0 work needed for the staleness gate itself — only `arrconf schema-gen` regen + commit of `schemas/arrconf-schema.json` during Plan A)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/media/<name>` directories actually appear on the NFS share after first chart deploy | REQ-filesystem-initcontainer | Requires live cluster + NFS PVC binding; cannot run in CI | After Phase 9 ArgoCD sync: `kubectl exec -n selfhost <any-media-pod> -- ls /media/films-zoe /media/series-emilie /media/series-zoe` returns those dirs |
| Job is idempotent on `helm upgrade` (re-runs produce `"created":false,"existed":true` × 10) | REQ-filesystem-initcontainer | Requires live cluster + sequential install + upgrade events | After first install: `kubectl logs job/arr-stack-categories-init -n selfhost \| grep -c '"created":true'` returns 10. After `helm upgrade` (no chart change): a new Job runs (via `hook-delete-policy: before-hook-creation`); `kubectl logs job/arr-stack-categories-init` returns 10 `"created":false,"existed":true` lines. |
| Job runs as uid 1000 successfully on the actual NFS share | REQ-filesystem-initcontainer (D-12) | NFS export behavior is cluster-specific; research confirmed it works on this cluster but operator should re-verify on first deploy | `kubectl logs job/arr-stack-categories-init` shows 10 successful mkdir lines (no permission errors). If fails: rerun research item #2 fallback (run as root + chown). |
| Snapshot baseline taken BEFORE first Phase 9 cluster deploy (ADR-6) | All Phase 9 requirements | ADR-6 discipline cannot be auto-enforced | `tools/snapshot/snapshot.sh --output snapshots/before-phase-9-$(date +%F)/` before merge of the Phase 9 release tag's `targetRevision` bump in my-kluster |
| Operator filesystem migration runbook readable + complete (REQ-filesystem-operator-migration) | REQ-filesystem-operator-migration | Operator-facing documentation; quality is judgment-based | Manual PR review of new CLAUDE.md section by operator; copy-paste-walk-through one of the 6 mapping rows to confirm commands work |
| `arrconf.image.tag` pre-bump matches what `mathieudutour/github-tag-action` will produce on this push (CF-07-CHART-PIN-LOOP) | REQ-chart-pin-prebump (Phase 10 but applied here) | Tag computation requires inspecting `git log` and the action's bump logic | Read `git log --tags` for the last tag; compute next patch tag; verify `charts/arr-stack/values.yaml#arrconf.image.tag` matches |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (5 cluster-time manuals documented above)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (verify in PLAN.md after planner emits)
- [ ] Wave 0 covers all MISSING references (4 new files + 1 fixture identified above)
- [ ] No watch-mode flags (existing CI uses one-shot pytest + helm lint)
- [ ] Feedback latency < 60s for per-commit quick run
- [ ] `nyquist_compliant: true` set in frontmatter after Wave 0 files exist

**Approval:** pending
