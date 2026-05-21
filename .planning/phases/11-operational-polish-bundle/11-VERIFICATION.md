---
phase: 11-operational-polish-bundle
verified: 2026-05-21T21:00:00Z
status: human_needed
score: 4/5
overrides_applied: 0
deferred:
  - truth: "A commit touching only tools/arrconf/** triggers chart-lint.yml auto-tag and produces a new tag; the first Renovate scan after opens a PR on my-kluster bumping targetRevision"
    addressed_in: "Post-push UAT — immediately actionable after operator pushes the 12 local commits to origin/main"
    evidence: "SC#4 cross-repo half: paths-filter commit (27bcbe9) exists locally but not yet on origin/main. Once pushed, one arrconf-only commit will exercise the full chain. Renovate App is confirmed active (PRs #14 + #15 opened 2026-05-21T09:24). The paths-filter code change is verified substantive."
---

# Phase 11: Operational Polish Bundle — Verification Report

**Phase Goal:** The 7 carry-forward operational items from v0.2.0 are closed and REQ-readme-onboarding is validated — arr-stack v0.3.0 is operationally complete.
**Verified:** 2026-05-21T21:00:00Z
**Status:** human_needed (SC#4 cross-repo half requires post-push observation)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | kubectl edit drift on live arr-stack chart auto-corrects on next ArgoCD sync within 3 min; selfHeal+prune=true | VERIFIED | Evidence log `argocd-selfheal-uat-2026-05-21.log`: STEP 1 `{"prune":true,"selfHeal":true}`, STEP 4 replicas=2 (drift), STEP 6 replicas=1 (auto-corrected at 19:21:31 after 180s sleep starting 19:18:31). Verdict line: `SC#1 PASS`. |
| 2 | kubectl -n selfhost get cm lists only arrconf-config + configarr-config; legacy arrconf + configarr absent | VERIFIED | Evidence log `cm-cruft-cleanup-2026-05-21.log`: STEP 1 shows arrconf-config (7d8h) + configarr-config (7d8h) only; STEP 4 post-delete inventory identical. Verdict: `SC#2 PASS — legacy CMs absent (already pruned by ArgoCD prune:true)`. |
| 3 | tools/snapshot/snapshot.sh followed by anti-leak grep returns 0 hits on fresh snapshot without manual post-edit | VERIFIED | `grep -rEH '"(apiKey|password|token|webhookUrl|sessionKey)"\s*:\s*"[^<"]{8,}"' snapshots/before-argocd-selfheal-uat-2026-05-21/ | grep -v '"<redacted>"' | wc -l` = **0**. JQ_REDACT block found at lines 400-404 of snapshot.sh. mv -f guard at line 409. nullglob guard at lines 406+415. `bash -n snapshot.sh` exits 0. config_host.json shows `"<redacted>"` for sensitive fields. |
| 4 | A commit touching only tools/arrconf/** triggers chart-lint.yml auto-tag and produces new tag; Renovate scan opens PR on my-kluster bumping targetRevision | DEFERRED | In-repo half verified: paths-filter commit 27bcbe9 adds `"tools/arrconf/**"` to both push and pull_request paths in chart-lint.yml (2 occurrences confirmed). Renovate App active: PRs #14 + #15 opened by app/renovate at 2026-05-21T09:24. Cross-repo half (my-kluster targetRevision PR) deferred to post-push observation — commit is local-only, not yet on origin/main. |
| 5 | Fresh operator following README.md from git clone completes successful arrconf diff in <30 min | ? UNCERTAIN | README verified free of the 3 stale references (v0.2.x coverage, PVC phrasing, Rollback heading). Onboarding section present at line 173. No Phase-4 / v0.2.x stale text remains (grep confirms 0 hits). Self-validated by author per D-11-CLAUDE'S-DISCRETION. External dry-run not performed — human verification needed per CONTEXT.md decision. |

**Score:** 4/5 truths fully verified (SC#3 exact, SC#1+SC#2+SC#4-in-repo). SC#4 cross-repo deferred (post-push UAT). SC#5 uncertain (needs human).

---

### Deferred Items

Items not yet met but explicitly addressed in a post-phase operator action.

| # | Item | Addressed In | Evidence |
|---|------|-------------|---------|
| 1 | SC#4 cross-repo: my-kluster targetRevision PR from Renovate after arrconf-only commit | Post-push UAT (immediately after operator pushes 12 local commits) | Paths-filter commit 27bcbe9 verified locally. Renovate App confirmed active (PRs #14+#15). Once push lands, a no-op `tools/arrconf/**` commit completes the chain. Documented in `renovate-app-install-2026-05-21.log` STEP 4. |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.pre-commit-config.yaml` | astral-sh/ruff-pre-commit hook pinned to v0.15.7, scoped to tools/arrconf/ | VERIFIED | Exists. Rev `v0.15.7`. Hooks: `ruff` (--fix) + `ruff-format`, both with `files: ^tools/arrconf/`. Substantive (21 lines, not stub). |
| `CLAUDE.md` (Python triade section) | Triade command `uv run ruff format --check . && uv run ruff check . && uv run mypy .` + `pre-commit install` pointer | VERIFIED | Line 109: full triade command documented. `pre-commit install` referenced in same line. |
| `.github/workflows/chart-lint.yml` (paths filter) | `tools/arrconf/**` in both push and pull_request paths | VERIFIED | Lines 8 + 17: `"tools/arrconf/**"` present in both triggers with inline REQ comment. |
| `tools/snapshot/snapshot.sh` (redaction block) | JQ_REDACT variable + mv -f + nullglob + skipped in dry-run | VERIFIED | Lines 400-416: full redaction block present. JQ_REDACT at line 400. `mv -f` at line 409. `shopt -s nullglob` at line 406. Dry-run gate at line 399 (`if (( ! DRY_RUN ))`). |
| `tools/snapshot/README.md` (v0.3.0+ note) | Note that redaction is automatic in v0.3.0+; manual Option A preserved as fallback | VERIFIED | Line 140: `**Note (v0.3.0+)** : la redaction Option A est désormais appliquée AUTOMATIQUEMENT par snapshot.sh`. Manual recipe preserved below. |
| `README.md` (v0.3.0 onboarding) | No stale Phase-4 / v0.2.x references; Onboarding section present | VERIFIED | `grep -E "si regression post-Phase 4|migration depuis.*pré-Phase 4|Phase 4 cutover|Phase 4 / v0"` = 0 hits. Stack table shows `v0.3.0 | qBit / Sonarr / Radarr / Prowlarr / Seerr / Jellyfin (6 apps)`. Onboarding section at line 173 with 5-step procedure estimating 25-30 min. |
| Evidence logs (SC#1, SC#2, SC#3) | Dispositive UAT evidence for live-cluster SCs | VERIFIED | `argocd-selfheal-uat-2026-05-21.log`, `cm-cruft-cleanup-2026-05-21.log`, `renovate-app-install-2026-05-21.log` all exist and contain verdict lines. |
| `snapshots/before-argocd-selfheal-uat-2026-05-21/` | Pre-UAT ADR-6 baseline snapshot with 0 unredacted secrets | VERIFIED | 17 sonarr JSON files present. Anti-leak grep returns 0. config_host.json shows `"<redacted>"` values. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `.pre-commit-config.yaml` | `tools/arrconf/` | `files: ^tools/arrconf/` scope | WIRED | Both hooks scoped to arrconf directory only |
| `chart-lint.yml` push trigger | auto-tag job | `paths:` filter + `if: github.event_name == 'push'` | WIRED | paths filter at lines 6-13; tag job at line 148 with `needs: lint` |
| `chart-lint.yml` paths filter | `tools/arrconf/**` | lines 8 + 17 | WIRED | Both push and pull_request paths filters include the arrconf path |
| `snapshot.sh` redaction block | JQ_REDACT filter | `jq --sort-keys "$JQ_REDACT" "$f"` | WIRED | Filter is applied inside the loop, result written via `mv -f` |
| ArgoCD syncPolicy | selfHeal + prune | `kubectl -n argocd get application arr-stack` | WIRED | Live evidence: `{"prune":true,"selfHeal":true}` confirmed |

---

### Data-Flow Trace (Level 4)

Not applicable for this phase. Phase 11 delivers operational tooling (CI config, snapshot.sh, docs, cluster operator actions) — no data-rendering components or dynamic UI surfaces.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| snapshot.sh syntax valid | `bash -n tools/snapshot/snapshot.sh` | exits 0 | PASS |
| JQ_REDACT present in snapshot.sh | `grep -c 'JQ_REDACT' tools/snapshot/snapshot.sh` | 2 occurrences | PASS |
| chart-lint.yml paths filter covers arrconf | `grep -c 'tools/arrconf/\*\*' .github/workflows/chart-lint.yml` | 2 occurrences | PASS |
| Pre-UAT snapshot has 0 unredacted secrets | anti-leak grep on `snapshots/before-argocd-selfheal-uat-2026-05-21/` | 0 hits | PASS |
| tests.yml has ruff format check | `grep -n 'ruff format' .github/workflows/tests.yml` | line 42: `uv run ruff format --check .` | PASS |
| Renovate PRs active | `gh pr list --author "app/renovate"` | PRs #14 + #15 OPEN | PASS |
| No values.yaml changes in Phase 11 | `git diff origin/main..HEAD -- charts/arr-stack/values.yaml` | empty | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| REQ-04-09-argocd-selfheal | 11-B | selfHeal+prune re-enabled, drift UAT | SATISFIED | Live evidence: `{"prune":true,"selfHeal":true}` + drift auto-revert <3 min. REQUIREMENTS.md still shows "Pending" in traceability table — needs update by orchestrator. |
| REQ-cm-cruft-cleanup | 11-B | Legacy CMs arrconf + configarr removed | SATISFIED | Evidence log shows legacy CMs absent (ArgoCD-pruned path). REQUIREMENTS.md still shows "Pending" — needs update. |
| REQ-ruff-format-ci-gate | 11-A | ruff format --check in CI + pre-commit hook | SATISFIED | CI: tests.yml line 42. Local: .pre-commit-config.yaml. CLAUDE.md: triade line 109. REQUIREMENTS.md: "Complete". |
| REQ-paths-filter-arrconf | 11-A | tools/arrconf/** in chart-lint.yml paths | SATISFIED | chart-lint.yml lines 8 + 17. REQUIREMENTS.md: "Complete". (Not yet pushed to origin/main — code exists and is correct locally.) |
| REQ-renovate-app-install | 11-B | Mend Renovate App active on tom333/arr-stack | SATISFIED (partial) | UAT-stage 1 PASS: PRs #14+#15 by app/renovate. Cross-repo half (my-kluster PR) deferred. REQUIREMENTS.md still shows "Pending" — needs update. |
| REQ-snapshot-redaction-harden | 11-A | snapshot.sh inline jq redaction; 0 anti-leak hits | SATISFIED | Redaction block verified in snapshot.sh. Live snapshot confirms 0 hits. REQUIREMENTS.md: "Complete". |
| REQ-readme-onboarding-v030 | 11-A | README v0.3.0 refresh, onboarding <30 min | SATISFIED (self-validated) | 3 stale references removed. Onboarding section present. Author self-validation per D-11-CLAUDE'S-DISCRETION. External dry-run deferred. REQUIREMENTS.md: "Complete". |

**Orphaned check:** REQUIREMENTS.md traceability table shows REQ-04-09-argocd-selfheal, REQ-cm-cruft-cleanup, and REQ-renovate-app-install as "Pending" despite 11-B plan completing them. The 11-B SUMMARY commit (`94515a2`) did not update REQUIREMENTS.md (only added the SUMMARY file). This is a documentation gap — the underlying requirements are satisfied in code/cluster but the tracking table was not updated. The orchestrator should update these 3 entries to "Complete".

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/REQUIREMENTS.md` | 88-93 | REQ-04-09-argocd-selfheal, REQ-cm-cruft-cleanup, REQ-renovate-app-install marked "Pending" despite 11-B completing them | Warning | Documentation only — no code impact. 11-B SUMMARY commit did not update traceability table. |

No code anti-patterns found. All Phase 11 commits touch only tooling/docs/CI (no `return null`, no placeholder stubs, no TODOs in new code). D-05 audit clean: `git diff origin/main..HEAD -- charts/arr-stack/values.yaml` is empty.

---

### Human Verification Required

#### 1. SC#4 Cross-Repo Post-Push Observation

**Test:** After operator pushes the 12 local commits to `origin/main`:
1. Make a commit touching only `tools/arrconf/**` (e.g., a comment change in any `.py` file) — no `charts/` changes
2. Push to origin/main
3. Watch `chart-lint.yml` trigger on GitHub Actions (should trigger because `tools/arrconf/**` is now in the paths filter)
4. Confirm auto-tag job creates a new semver tag
5. Within ~1h, check `gh pr list --repo tom333/my-kluster --author "app/renovate"` for a PR bumping `targetRevision`

**Expected:** chart-lint.yml runs, auto-tag creates `vX.Y.Z+1`, Renovate on my-kluster opens a PR within one scan cycle.
**Why human:** The paths-filter commit exists locally but has not yet been pushed to origin/main. Until it is, GitHub Actions cannot observe the new paths filter. The code change is verified correct (2 occurrences in chart-lint.yml), but the E2E trigger chain requires a live push event.
**Evidence file:** Append result to `.planning/phases/11-operational-polish-bundle/evidence/renovate-app-install-2026-05-21.log`

#### 2. SC#5 README Onboarding Fresh-Eyes Dry-Run (Optional)

**Test:** Have someone unfamiliar with the project (or the author after a 1-week gap) follow `README.md` from `git clone` through a successful `arrconf diff` against the cluster.
**Expected:** Completion in under 30 minutes without asking questions or hitting dead ends.
**Why human:** Author self-validated per D-11-CLAUDE'S-DISCRETION (homelab single-tenant). The README content is verified stale-free programmatically. External dry-run cannot be automated. Accepted as soft validation per CONTEXT.md decision.
**Note:** This is opt-in per plan decision. It does not block Phase 11 closure; the author's cold re-read is the accepted validation method for this scope.

---

### D-05 Chart-Pin Co-Bump Audit

`git diff origin/main..HEAD -- charts/arr-stack/values.yaml` = empty (confirmed). None of the 12 Phase 11 commits touch `tools/arrconf/**` Python source code, so no chart-pin co-bump was required. D-05 exception applies cleanly to all Phase 11 commits.

---

### Gaps Summary

No blocking gaps. All 5 Success Criteria are either:
- **Fully verified** (SC#1, SC#2, SC#3): dispositive live-cluster evidence captured in logs
- **Verified in-repo, deferred cross-repo** (SC#4): paths-filter code is correct and committed locally; the cross-repo UAT chain activates upon push to origin/main
- **Uncertain / human-needed** (SC#5): README content is clean; completion-time validation is author self-declared per documented decision

The single actionable item before declaring v0.3.0 operationally complete is: **push the 12 local commits to origin/main** and observe SC#4's cross-repo half. This is a post-phase operator step, not a code defect.

**Minor documentation debt:** REQUIREMENTS.md traceability table still shows REQ-04-09-argocd-selfheal, REQ-cm-cruft-cleanup, REQ-renovate-app-install as "Pending". Orchestrator should update these 3 rows to "Complete" alongside the VERIFICATION.md commit.

---

_Verified: 2026-05-21T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
