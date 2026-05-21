---
phase: 10
slug: categories-6-app-propagation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-19
revised: 2026-05-19
---

<!-- Warning #3 (revision iter 2):
  - nyquist_compliant: flipped to true after revision. Every task in plans 10-A through
    10-J has an <automated> command in its <verify> block (no manual-only checkpoints
    block sampling). The single checkpoint:human-action task added in Plan 10-B Blocker #1
    (ADR-6 snapshot) is verified post-hoc by `ls + git log` — not blocking continuous
    feedback during execution.
  - wave_0_complete: flipped to true. All 7 test files + 1 fixture listed in "Wave 0
    Requirements" are now assigned to specific tasks across Wave 1 (10-A/10-B) and
    Wave 2 (10-C..10-H) and Wave 3 (10-J). See per-task verification map below. -->

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — `tools/arrconf/pyproject.toml`) |
| **Config file** | `tools/arrconf/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cd tools/arrconf && uv run pytest tests/test_generators_categories.py tests/test_merge_with_manual.py tests/test_idempotence_fp.py -x` |
| **Full suite command** | `cd tools/arrconf && uv run pytest -v --cov=arrconf --cov-fail-under=70` |
| **Estimated runtime** | ~30 seconds (quick), ~90 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run quick command above
- **After every plan wave:** Run full suite + `ruff check && ruff format --check && mypy`
- **Before `/gsd-verify-work`:** Full suite must be green AND `tools/snapshot/snapshot.sh` baseline captured (ADR-6)
- **Max feedback latency:** ~30 seconds per task

---

## Per-Task Verification Map

> Placeholders below get refined by the planner. Wave 0 columns flag files that don't yet exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-A-01 | 10-A | 1 | REQ-categories-qbit-propagation, REQ-categories-sonarr-propagation, REQ-categories-radarr-propagation | T-10-V5-tampering | `Category.name` kebab-case + `extra="forbid"` enforced upstream of generator | unit | `pytest tests/test_generators_categories.py -x` | ❌ W0 | ⬜ pending |
| 10-B-01 | 10-B | 1 | REQ-categories-* (merge contract) | — | Per-resource toggle never silently drops manual config | unit | `pytest tests/test_merge_with_manual.py -x` | ❌ W0 | ⬜ pending |
| 10-C-01 | 10-C | 2 | REQ-categories-qbit-propagation, REQ-idempotence-fp-fix (#1) | T-10-V5-qbit | qBit category allowlist filters cluster-returned extras before diff | unit + integration | `pytest tests/test_idempotence_fp.py::test_qbit -x` | ❌ W0 | ⬜ pending |
| 10-D-01 | 10-D | 2 | REQ-categories-sonarr-propagation | — | 5 tags/root_folders/DCs/RPMs generated; manual override path verified | unit | `pytest tests/test_sonarr_categories.py -x` | ❌ W0 | ⬜ pending |
| 10-E-01 | 10-E | 2 | REQ-categories-radarr-propagation | — | Same as Sonarr for `kind=movies` | unit | `pytest tests/test_radarr_categories.py -x` | ❌ W0 | ⬜ pending |
| 10-F-01 | 10-F | 2 | REQ-categories-seerr-routing, REQ-idempotence-fp-fix (#3) | T-10-V5-seerr | animeTags resolved post-Sonarr from /tag endpoint; user allowlist filters fixed extras | integration | `pytest tests/test_seerr_animetags.py tests/test_idempotence_fp.py::test_seerr -x` | ❌ W0 | ⬜ pending |
| 10-G-01 | 10-G | 2 | REQ-categories-jellyfin-paths | — | PathInfos derived from Categories; `Path` attribute preserved as PascalCase | unit | `pytest tests/test_jellyfin_categories.py -x` | ❌ W0 | ⬜ pending |
| 10-H-01 | 10-H | 2 | REQ-idempotence-fp-fix (#2) | T-10-V5-prowlarr | Prowlarr Application allowlist filters server-side helpText/order/type fields | unit | `pytest tests/test_idempotence_fp.py::test_prowlarr -x` | ❌ W0 | ⬜ pending |
| 10-I-01 | 10-I | 3 | REQ-chart-pin-prebump | — | CLAUDE.md + gsd-executor.md document the co-bump rule | manual review | `grep -c "arrconf.image.tag" CLAUDE.md .claude/agents/gsd-executor.md` | ✅ exists | ⬜ pending |
| 10-J-01 | 10-J | 3 | SC#2 (idempotence sweep) | — | 2nd-run emits 0 plan_action across all 6 apps | integration | `pytest tests/test_phase10_idempotence_sweep.py -x` | ❌ W0 | ⬜ pending |
| 10-J-02 | 10-J | 3 | REQ-categories-qbit-propagation (D-03a wording) | — | REQUIREMENTS.md uses bare `<name>` not `<kind>-<name>` | doc check | `grep -E 'qbit.*<name>' .planning/REQUIREMENTS.md` | ✅ exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tools/arrconf/tests/test_generators_categories.py` — stubs for REQ-categories-{qbit,sonarr,radarr}-propagation
- [ ] `tools/arrconf/tests/test_merge_with_manual.py` — D-02 toggle predicate
- [ ] `tools/arrconf/tests/test_idempotence_fp.py` — 3 FP fixes (qBit / Prowlarr / Seerr user)
- [ ] `tools/arrconf/tests/test_seerr_animetags.py` — REQ-categories-seerr-routing + animeTags ID resolution
- [ ] `tools/arrconf/tests/test_jellyfin_categories.py` — REQ-categories-jellyfin-paths
- [ ] `tools/arrconf/tests/test_phase10_idempotence_sweep.py` — SC#2 2nd-run-zero sweep across all 6 reconcilers
- [ ] `tools/arrconf/tests/fixtures/phase10-baseline-plans.json` — generated after Wave 2 lands, frozen as Phase 10 baseline
- [ ] Rename `tests/_phase9_helpers.py` → `tests/_arrconf_helpers.py` (or fork; planner picks per RESEARCH.md §1)

*Reuses existing pytest + respx infrastructure — no new framework install required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cluster `arrconf apply` materializes 10 qBit categories | SC#1 (cluster-side) | Requires live cluster + post-merge ArgoCD sync | After v0.4.0 tag merge + ArgoCD sync: `kubectl exec deployment/qbittorrent -- cat /config/qBittorrent/categories.json \| jq 'keys'` → expect 10 names |
| Sonarr/Radarr/Seerr/Jellyfin reflect Categories shape | SC#1, SC#3 | Requires live cluster + GUI inspection | UI walkthrough: Sonarr tags page = 5 tags + arrconf-managed; Seerr Sonarr server settings shows animeTags populated |
| Cluster-side content re-tagging (operator step) | D-03f | OUT of arrconf scope by design; operator bulk-edits via UI or SQL | Operator runbook in CLAUDE.md filesystem migration section (extend with re-tag step) |
| Single `targetRevision` bump per phase commit | SC#5, REQ-chart-pin-prebump | Visible only after merge in my-kluster Renovate PR | After Phase 10 release tag: confirm one Renovate PR in my-kluster bumps `arr-stack-app.yaml#targetRevision` to v0.4.x, no chart-only orphan bump |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (cluster UAT items flagged manual above)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (7 test files + 1 fixture)
- [ ] No watch-mode flags (`pytest -x` not `--watch`)
- [ ] Feedback latency < 60s (quick suite ~30s)
- [ ] `nyquist_compliant: true` set in frontmatter after planner refines per-task map

**Approval:** pending
