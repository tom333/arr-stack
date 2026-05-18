---
phase: 9
slug: categories-data-model-chart-initcontainer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-18
revised: 2026-05-18 (B-03 — fixture moved from Wave 0 to Wave 2 intermediate outputs)
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
| 09-B-* | B (Helm Job) | 1 | REQ-filesystem-initcontainer | — | Job has `helm.sh/hook: pre-install,pre-upgrade` (Plan-B-feasible W-02 check) | integration | `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \| grep -A5 'name:.*categories-init' \| grep -E 'helm.sh/hook.*pre-(install\|upgrade)'` | ❌ Wave 0 (new chart-lint grep guard, optional) | ⬜ pending |
| 09-C-C3 | C (arrconf.yml + tests) | 2 | REQ-filesystem-initcontainer | — | Job iterates `.Files.Get \| fromYaml` over categories (20 mkdir lines rendered — W-02 reassignment from Plan B) | integration | `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml \| grep -c 'media_dir_ensured'` returns 20 (10 created + 10 existed printf branches) | ❌ Wave 2 (C3 owns; cross-plan integration) | ⬜ pending |
| 09-C-C1 | C (arrconf.yml + tests) | 2 | REQ-categories-10-target | — | 10 categories with exact production names | unit | `cd tools/arrconf && uv run pytest tests/test_arrconf_yml_validates.py::test_arrconf_yml_has_10_categories -x` | ❌ Wave 2 (extend existing) | ⬜ pending |
| 09-C-C1 | C (arrconf.yml + tests) | 2 | REQ-categories-10-target | — | All 10 entries pass pydantic validation on `arrconf apply --dry-run` | integration | `cd tools/arrconf && uv run arrconf apply --config ../../charts/arr-stack/files/arrconf.yml --dry-run` exits 0 | ❌ Wave 2 (smoke check in test) | ⬜ pending |
| 09-C-C1 | C (arrconf.yml + tests) | 2 | REQ-categories-10-target | — | ruyaml parse-roundtrip belt-and-suspenders (W-03) | unit | `cd tools/arrconf && uv run python -c "import ruyaml; from pathlib import Path; yaml = ruyaml.YAML(typ='safe'); data = yaml.load(Path('../../charts/arr-stack/files/arrconf.yml')); assert len(data['categories']) == 10; assert all(c['base_path'] == f'/media/{c[\"name\"]}' for c in data['categories'])"` exits 0 | ❌ Wave 2 (W-03 new) | ⬜ pending |
| 09-C-C2a | C (arrconf.yml + tests) | 2a (C2a output) | REQ-migration-progressive | — | Walker module imports cleanly; fixture is valid JSON with the 6 app keys + `_caveat` | unit | `cd tools/arrconf && uv run python -c "from tests._phase9_helpers import dry_run_all_apps" && python -m json.tool tools/arrconf/tests/fixtures/phase9-baseline-plans.json > /dev/null` | ❌ Wave 2a (B-02 split — walker + fixture) | ⬜ pending |
| 09-C-C2b | C (arrconf.yml + tests) | 2b (C2b consumes C2a) | REQ-migration-progressive | — | Reconcile plan output unchanged when categories[] absent (consumes Task C2a fixture) | unit | `cd tools/arrconf && uv run pytest tests/test_phase9_no_regression.py -x` | ❌ Wave 2b (B-02 split — test) | ⬜ pending |
| 09-D-* | D (CLAUDE.md + release) | 2 | REQ-filesystem-operator-migration | — | Migration runbook section exists in CLAUDE.md | unit | `grep -F '## Filesystem migration: v0.2.0 flat → v0.3.0 Categories' CLAUDE.md` exits 0 | ❌ Wave 2 | ⬜ pending |
| 09-D-* | D (CLAUDE.md + release) | 2 | REQ-filesystem-operator-migration | — | `charts/arr-stack/values.yaml#arrconf.image.tag` pre-bumped to v0.5.3 (next patch tag from v0.5.2 — CF-07-CHART-PIN-LOOP, B-01 fix) | unit | `grep -F 'tag: "0.5.3"' charts/arr-stack/values.yaml` exits 0 | ❌ Wave 2 (manual PR-review gate + grep) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

The following files MUST exist BEFORE any Wave 1 task can claim its `<automated>` verify is satisfied. These are Plan-A authored test scaffolds:

- [ ] `tools/arrconf/tests/test_categories.py` — NEW (Plan A Wave 1); parametric tests for `Category` model (valid 10-entry input + invalid permutations: wrong kind enum, wrong profile enum, base_path mismatch, duplicate name, kebab-case violations)
- [ ] `tools/arrconf/tests/test_arrconf_yml_validates.py` — EXTEND existing (Plan C Wave 2); assert the 10 production categories are present in `charts/arr-stack/files/arrconf.yml` and each parses through `RootConfig`
- [x] pytest + respx + ruff + mypy framework already installed via `uv sync --frozen` in `tests.yml`
- [x] helm lint + kubeconform already wired in `chart-lint.yml`
- [x] `test_schema_gen.py::test_schema_committed_matches_regen` already exists (no Wave 0 work needed for the staleness gate itself — only `arrconf schema-gen` regen + commit of `schemas/arrconf-schema.json` during Plan A)

**Wave 0 candidates (test scaffolds that must precede the code they verify):**
1. `tools/arrconf/tests/test_categories.py` (Plan A Wave 1) — tests Plan A's Category model
2. `tools/arrconf/tests/test_phase9_no_regression.py` (Plan C Wave 2b) — tests Phase 9 D-13 boundary; consumes Task C2a's fixture

---

## Wave 2 Intermediate Outputs

The following artifacts are generated by Plan C Task C2a (Wave 2a) and consumed by Plan C Task C2b (Wave 2b) within the same plan. They are NOT Wave 0 prerequisites because they depend on Plan A's `Category` model + `RootConfig.categories` field (Wave 1):

- [ ] `tools/arrconf/tests/_phase9_helpers.py` — NEW (Task C2a); exposes `dry_run_all_apps(cfg)` walker that enumerates the 6 reconciler callables (sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin), handles qBit auth-flow shim + Seerr D-06-SEERR-USER-FP ordering sort. Imported by Task C2b's test.
- [ ] `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` — NEW (Task C2a generates; Task C2b consumes); frozen baseline of `dry_run_all_apps` output against a categories-stripped synthetic copy of production arrconf.yml. MUST include a `_caveat` field stating: "Fixture captures Phase 9 build output for a categories-less arrconf.yml. Not 'v0.2.0 reconciler behavior' verbatim — it captures Phase-9-code-with-categories-stripped, which is functionally equivalent because reconcilers don't read RootConfig.categories (D-13)." (B-02 + B-03 split — was previously listed as Wave 0; correctly belongs here.)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/media/<name>` directories actually appear on the NFS share after first chart deploy | REQ-filesystem-initcontainer | Requires live cluster + NFS PVC binding; cannot run in CI | After Phase 9 ArgoCD sync: `kubectl exec -n selfhost <any-media-pod> -- ls /media/films-zoe /media/series-emilie /media/series-zoe` returns those dirs |
| Job is idempotent on `helm upgrade` (re-runs produce `"created":false,"existed":true` × 10) | REQ-filesystem-initcontainer | Requires live cluster + sequential install + upgrade events | After first install: `kubectl logs job/arr-stack-categories-init -n selfhost \| grep -c '"created":true'` returns 10. After `helm upgrade` (no chart change): a new Job runs (via `hook-delete-policy: before-hook-creation`); `kubectl logs job/arr-stack-categories-init` returns 10 `"created":false,"existed":true` lines. |
| Job runs as uid 1000 successfully on the actual NFS share | REQ-filesystem-initcontainer (D-12) | NFS export behavior is cluster-specific; research confirmed it works on this cluster but operator should re-verify on first deploy | `kubectl logs job/arr-stack-categories-init` shows 10 successful mkdir lines (no permission errors). If fails: rerun research item #2 fallback (run as root + chown). |
| Snapshot baseline taken BEFORE first Phase 9 cluster deploy (ADR-6) | All Phase 9 requirements | ADR-6 discipline cannot be auto-enforced | `tools/snapshot/snapshot.sh --output snapshots/before-phase-9-$(date +%F)/` before merge of the Phase 9 release tag's `targetRevision` bump in my-kluster |
| Operator filesystem migration runbook readable + complete (REQ-filesystem-operator-migration) | REQ-filesystem-operator-migration | Operator-facing documentation; quality is judgment-based | Manual PR review of new CLAUDE.md section by operator; copy-paste-walk-through one of the 6 mapping rows to confirm commands work |
| `arrconf.image.tag` pre-bump matches what `mathieudutour/github-tag-action` will produce on this push (CF-07-CHART-PIN-LOOP, B-01 fix) | REQ-chart-pin-prebump (Phase 10 but applied here) | Tag computation requires inspecting `git tag` and the action's `default_bump` config | Verified at planning time (2026-05-18): latest tag = v0.5.2, chart-lint.yml `default_bump: patch` → next tag = v0.5.3 → chart pin must be `tag: "0.5.3"`. Re-verify at execution time with `git tag --sort=-version:refname \| head -1` and `grep default_bump .github/workflows/chart-lint.yml`. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (5 cluster-time manuals documented above)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (verify in PLAN.md after planner emits)
- [ ] Wave 0 covers all MISSING references — see "Wave 0 Requirements" (2 test scaffolds: test_categories.py for Plan A, test_phase9_no_regression.py for Plan C Wave 2b)
- [ ] Wave 2 intermediate outputs documented — see "Wave 2 Intermediate Outputs" (_phase9_helpers.py + phase9-baseline-plans.json generated by Task C2a, consumed by Task C2b)
- [ ] No watch-mode flags (existing CI uses one-shot pytest + helm lint)
- [ ] Feedback latency < 60s for per-commit quick run
- [ ] `nyquist_compliant: true` set in frontmatter after Wave 0 files exist

**Approval:** pending
