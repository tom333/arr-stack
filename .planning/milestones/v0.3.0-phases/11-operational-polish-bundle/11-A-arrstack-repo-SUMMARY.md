---
phase: "11"
plan: "A"
subsystem: ops-polish
tags: [pre-commit, ruff, chart-lint, snapshot-redaction, readme, onboarding]
dependency_graph:
  requires: [10-J]
  provides: [REQ-ruff-format-ci-gate, REQ-paths-filter-arrconf, REQ-snapshot-redaction-harden, REQ-readme-onboarding-v030]
  affects: [ci-triggers, local-dev-tooling, snapshot-security, onboarding]
tech_stack:
  added: [astral-sh/ruff-pre-commit@v0.15.7]
  patterns: [pre-commit-hooks, inline-jq-redaction, paths-filter-ci]
key_files:
  created:
    - .pre-commit-config.yaml
  modified:
    - CLAUDE.md
    - .github/workflows/chart-lint.yml
    - tools/snapshot/snapshot.sh
    - tools/snapshot/README.md
    - README.md
decisions:
  - "D-05 exception confirmed: no tools/arrconf/** changes in Plan 11-A — no chart-pin co-bump needed"
  - "ruff pin: v0.15.7 (matches pyproject.toml ruff>=0.15,<0.16 range)"
  - "nullglob guard in redaction loop to handle empty snapshot (all apps failed)"
  - "mv -f enforced in redaction loop (Phase 10 lesson: interactive alias aborts loop silently)"
  - "README: 3 stale references fixed (v0.2.x coverage, PVC phrasing, Rollback heading) — diff < 10 lines"
metrics:
  duration: "~15 minutes"
  completed: 2026-05-21
  tasks: 5
  files: 6
---

# Phase 11 Plan A: arr-stack repo operational polish — Summary

Pre-commit hook (.pre-commit-config.yaml) + CLAUDE.md triade doc + chart-lint paths filter for arrconf-only commits + baked-in jq redaction in snapshot.sh + README v0.3.0 spot-fixes — closes 4 carry-forward REQs without touching tools/arrconf/** (D-05 exception).

## Tasks Completed

| Task | Description | Status | Commit |
|------|-------------|--------|--------|
| 11-A-01 | Add .pre-commit-config.yaml + CLAUDE.md Python triade doc | Done | 9335181 |
| 11-A-02 | Extend chart-lint.yml paths filter to include tools/arrconf/** | Done | 27bcbe9 |
| 11-A-03 | Bake inline jq redaction into snapshot.sh + README note | Done | c565127 |
| 11-A-04 | README cold re-read + spot-fix 3 stale references | Done | d247928 |
| 11-A-05 | Plan 11-A SUMMARY | Done | (this file) |

## Requirements Closed

| REQ ID | Status | Evidence |
|--------|--------|----------|
| REQ-ruff-format-ci-gate | Closed | `.pre-commit-config.yaml` created; CI half was already in `tests.yml` (commit `ef7681a`, Phase 5); CLAUDE.md now documents triade command + `pre-commit install` pointer |
| REQ-paths-filter-arrconf | Closed | `grep -c 'tools/arrconf/\*\*' .github/workflows/chart-lint.yml` = 2 (push + PR paths) |
| REQ-snapshot-redaction-harden | Closed | `grep -c 'JQ_REDACT' tools/snapshot/snapshot.sh` = 2; `bash -n tools/snapshot/snapshot.sh` exits 0; README § Audit anti-leak leads with v0.3.0+ automatic redaction note |
| REQ-readme-onboarding-v030 | Closed | 3 stale references fixed; `grep -nE 'si regression post-Phase 4\|migration depuis l.*tat pr.*-Phase 4' README.md` returns 0 hits |

## Files Modified (actual diff)

- **`.pre-commit-config.yaml`** (NEW) — astral-sh/ruff-pre-commit@v0.15.7 with `ruff` (--fix) + `ruff-format` hooks, scoped to `tools/arrconf/`
- **`CLAUDE.md`** — "Conventions développement — arrconf" extended with explicit triade command + `pre-commit install` pointer
- **`.github/workflows/chart-lint.yml`** — `"tools/arrconf/**"` added to both `on.push.paths` and `on.pull_request.paths`
- **`tools/snapshot/snapshot.sh`** — inline jq redaction block inserted before final report; `mv -f` guard; `shopt -s nullglob` for empty-dir safety; `--dry-run` gate
- **`tools/snapshot/README.md`** — v0.3.0+ note at top of § Audit anti-leak: redaction is now automatic; manual Option A recipe preserved as fallback for forensic re-redaction
- **`README.md`** — 3 spot-fixes: v0.2.x→v0.3.0 in stack table, PVC phrasing de-temporalized, Rollback heading de-temporalized

## Files NOT Modified (D-05 audit)

- **`charts/arr-stack/values.yaml`** — NOT touched. `git diff --stat charts/arr-stack/values.yaml` (against pre-plan tree) is empty. D-05 exception confirmed: no `tools/arrconf/**` source code changes in this plan.
- **`tools/arrconf/**`** — NOT touched. `git diff --stat tools/arrconf/` is empty.
- **`.github/workflows/tests.yml`** — NOT touched. The `uv run ruff format --check .` line was already present (commit `ef7681a`, Phase 5). Plan 11-A pivoted to the local belt only.

## Deviations from Plan

### Discovery-pivot (no code change)

**[Pivot] tests.yml ruff format --check was already present**

- **Found during:** Pre-execution read of `.github/workflows/tests.yml`
- **Issue:** D-11-RUFF-GATE documented in CONTEXT.md noted CI half was already done (commit `ef7681a`, Phase 5). Plan 11-A correctly scoped to the local pre-commit hook only.
- **Resolution:** Created `.pre-commit-config.yaml` as the local belt-and-suspenders. REQ-ruff-format-ci-gate satisfied via "CI already present + pre-commit hook added + CLAUDE.md triade doc" — all three gates confirmed.
- **No code regression:** verified with `grep -c 'uv run ruff format --check' .github/workflows/tests.yml` = 1 (unchanged).

### Additional spot-fix (cold re-read)

**[Rule 2 - Completeness] README stack table had v0.2.x arrconf version**

- **Found during:** Task 4 cold re-read (README line 63)
- **Issue:** Stack table listed `arrconf (ce repo) | v0.2.x | Sonarr / Radarr / Prowlarr` — both the version and coverage were stale (v0.3.0 ships 6 apps).
- **Fix:** Updated to `v0.3.0 | qBit / Sonarr / Radarr / Prowlarr / Seerr / Jellyfin (6 apps)`.
- **Diff impact:** +1 line on an already-small < 10 line diff (total: 3 changed lines in README).

## Operator-side UAT Pending

The following acceptance criteria require live cluster execution and are deferred to the Phase 11 verifier:

**SC#3 — Snapshot redaction dispositive test:**
- Command: `./tools/snapshot/snapshot.sh --output snapshots/test-redaction-$(date +%F)/ && grep -rEH '"(apiKey|password|token|webhookUrl|sessionKey)"\s*:\s*"[^<"]{8,}"' snapshots/test-redaction-*/ | grep -v '"<redacted>"' | wc -l`
- Expected result: `0`
- Evidence path: `evidence/snapshot-redaction-uat-<date>.log` (to be captured by verifier or operator)

**SC#5 — README onboarding < 30 min:**
- Self-validated by author per D-11-CLAUDE'S-DISCRETION (homelab single-tenant; cold re-read by author confirms no remaining stale references). External dry-run is opt-in, deferred to v0.4.0+.

**SC#4 — arrconf-only commit triggers auto-tag (post-11-B):**
- Requires Plan 11-B-03 (Renovate App install) to complete first. Once installed: push a commit touching only `tools/arrconf/**` → verify `chart-lint.yml` triggers and auto-tag is created.

## Chart-pin Co-bump Audit

```
git diff --stat charts/arr-stack/values.yaml  →  (empty)
git diff --stat tools/arrconf/                →  (empty)
```

D-05 exception confirmed: no `tools/arrconf/**` changes → no chart-pin co-bump fired on any commit in this plan. All 4 commits touch only meta-files (CI workflows, snapshot tooling, docs).

## Known Stubs

None. This plan is ops/docs only — no data flows, no UI rendering, no placeholder values.

## Threat Flags

None new. Threat model T-11-A-01 through T-11-A-06 addressed as planned:
- T-11-A-01 (Tampering/pre-commit rev pin): mitigated by exact `rev: v0.15.7` pin
- T-11-A-02 (InfoDisc/redaction filter): mitigated by case-insensitive 5-key filter + nullglob + manual fallback in README
- T-11-A-03 (DoS/mv -f): accepted — nullglob + jq-success gate prevent destruction
- T-11-A-04 (Tampering/chart-lint paths): mitigated — additive change only, existing triggers preserved
- T-11-A-05 (Repudiation/CLAUDE.md doc): accepted — CI is enforcement layer
- T-11-A-06 (InfoDisc/cleartext window): accepted and documented in deferred — post-loop bulk redaction leaves sub-second plaintext window; mitigation deferred to v0.4.0+ (per-file redaction in snapshot_get)

## Self-Check: PASSED

- [x] `.pre-commit-config.yaml` exists: `test -f .pre-commit-config.yaml` exits 0
- [x] `grep astral-sh/ruff-pre-commit .pre-commit-config.yaml | wc -l` = 1
- [x] `grep -c 'tools/arrconf/\*\*' .github/workflows/chart-lint.yml` = 2
- [x] `grep -c 'JQ_REDACT' tools/snapshot/snapshot.sh` = 2
- [x] `bash -n tools/snapshot/snapshot.sh` exits 0 (syntax check)
- [x] `grep -c 'AUTOMATIQUEMENT' tools/snapshot/README.md` = 1
- [x] `! grep 'si regression post-Phase 4' README.md` passes
- [x] `! grep 'migration depuis.*pré-Phase 4' README.md` passes
- [x] `git diff --stat charts/arr-stack/values.yaml` is empty
- [x] Commits 9335181, 27bcbe9, c565127, d247928 exist in git log
