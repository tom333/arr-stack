# arr-stack Retrospective (Living Document)

Cross-milestone learnings, patterns, and observations. Append a new section at each milestone close.

---

## Milestone: v0.2.0 — forceSave fix

**Shipped:** 2026-05-17
**Phases:** 11 (Phase 0–7 + 2.1/2.2/5.1) | **Plans:** 65/66 | **Tasks:** ~109

### What Was Built

- 6-app declarative reconciler (Sonarr / Radarr / Prowlarr / qBittorrent / Seerr / Jellyfin) operating from a single 540-line `arrconf.yml`
- Helm umbrella chart with 10 `bjw-s/app-template@5.0.0` aliases deployed to MicroK8s via 1 ArgoCD Application
- CI auto-tag → GHCR build → ArgoCD sync loop bridging arr-stack and my-kluster
- `arrconf dump | arrconf diff` round-trip idempotence proven for every reconciler at SC#4-level evidence

### What Worked

- **ADR-6 snapshot discipline before every cluster write.** The pre-write `snapshots/before-phase-N-*` directory pattern + matching post-apply snapshot made every Phase's behavioral diff inspectable in 30 seconds. When Phase 2.2 hit `D-02.2-AUTH-REGRESSION`, the forensic snapshot directory had the dispositive evidence on file before the user even returned to the terminal.
- **D-07-VALIDATE-01 / D-06-VALIDATE-01 live-probe-before-code.** Phases 6 and 7 ran a hand-rolled curl probe against the live API to discover write semantics (Pitfall 1: full-replace; Pitfall 2: not-idempotent; Pitfall 4: POST-not-PUT; Pitfall 5: version-in-path; etc.) BEFORE writing the reconciler. This eliminated most of the "first apply explodes" failure mode that Phase 2's blind reconcile hit.
- **Pitfall numbering convention.** Each phase exits with a numbered Pitfall catalog (q9-put-probe.txt, 9-pitfalls Jellyfin, OpenAPI Pitfall 6). Future operators reading the SUMMARY can grep for the exact gotcha. Phase 7's `D-06-OPENAPI-01 carry-forward` is a great example — Pitfall 6 was the same architectural issue Phase 6 hit.
- **Composite dispositive evidence.** Phase 2.2 closure used `merge_field_omitted_credential + Sonarr Test API HTTP 200 + manual_nudge_used=NO` as a triple-witness instead of a single grep. Made the closure unimpeachable. Pattern reused in Phase 7 SC#4 (DIFF_EXIT=0 + no_drift + 0 plan_actions + per-step no-op counts).
- **Wave parallelization with worktrees.** Phase 7 Wave 1 dispatched 07-01 + 07-02 + 07-03 in parallel git worktrees. Wave 2 took ~5h serially (07-04 is large). Without parallelization Wave 1 would have been 25 min serial; was ~8 min wall-clock with parallel.

### What Was Inefficient

- **D-07-CHART-PIN-LOOP (the 2-bump cycle).** When arrconf code changes, the auto-tag chain tags v(N+1) BEFORE the chart's `arrconf.image.tag` is updated to point at v(N+1)'s image. Result: 2 arr-stack commits + 2 my-kluster targetRevision bumps per phase. Fix: pre-bump `arrconf.image.tag` in the SAME commit that adds the reconciler code (collapse to 1 my-kluster bump). v0.3.0 should test this.
- **`ruff format --check` is not the same as `ruff check`.** Plan 07-04 executor ran the lint but not the format check; first push to main FAILED tests workflow. Cost: 1 extra commit + 1 extra CI cycle. Fix: gsd-executor agent prompt + CLAUDE.md must enumerate both commands.
- **Project-aliased `rm`/`cp` (locale=fr).** `rm file` and `cp src dst` prompt interactively when running over previously-existing targets; without an answer they silently no-op. Bit us in Phase 7's snapshot cleanup (devices.json not deleted) and the worktree-merge STATE.md restore. Fix: scripts should use `\rm -f` / `\cp -f` (backslash-escape bypasses the alias). Pattern recorded by Phase 02.2 P06 RECOVERY but had to be re-learned in Phase 7.
- **gsd-sdk `roadmap.update-plan-progress` lag.** Only Phase 7 plans went through the SDK call after each plan closed; Phases 0/1/2/2.2/3/4/5/5.1/6 progress table rows stayed stale ("Not started" / "0/TBD") for the entire milestone. Fix: either run the SDK after every plan completion automatically, or treat the table as advisory and rebuild at milestone close (what we did).
- **Worktree branch divergence (Wave 2 anomaly).** Plan 07-04 agent's 5 commits ended up on `main` directly instead of on the worktree branch — root cause unclear (possibly the `<worktree_branch_check>` block bailed on a `main` checkout in the worktree path, and the agent retried somehow). Functional outcome was fine but the worktree-merge logic was bypassed for that wave. Worth investigating before v0.3.0 if parallel-worktree dispatch is reused heavily.

### Patterns Established

- **Pre-write baseline → pre-write code → live-probe → reconciler → post-apply baseline → SC dispositive evidence** (Phase 7 canonical execution pattern, mirrored from Phase 6)
- **Anti-leak grep at 3 stages** (snapshot output, evidence text, ConfigMap dump): `AccessToken|Bearer |Authorization:|api_key=[a-f0-9]{8,}|MediaBrowser Token="[a-f0-9]{8,}"` + base64-blob detection
- **D-XX-XX deviation IDs** (per-phase namespace) recorded inline in SUMMARY + carry-forward in STATE.md
- **Sealed-secret hot-add for bootstrap API keys** (Phase 6 D-06-CRED-MGMT, reused in Phase 7): kubeseal --raw → push to my-kluster → ~30s sealed-secrets-controller reconcile → kubectl-jq-keys evidence file
- **Field(exclude=True) + cluster GET re-injection** for OpenAPI-required-but-operator-never-configured fields (Seerr apiKey D-06-CREDS-01, Jellyfin AuthenticationProviderId/PasswordResetProviderId Pitfall 6)
- **`prune: false` hardcoded in reconciler, not just YAML default** (D-07-LIB-01, D-07-USERS-01) — protects when YAML is operator-modified

### Key Lessons

1. **Production-deployed ≠ ROADMAP says complete.** Phase 4 was in production for ~weeks but ROADMAP still showed `[ ]`. Audit-open caught this at milestone close. Lesson: keep ROADMAP marks in sync with reality; don't leave them as "TODO".
2. **The semver of the chart can diverge from the semver of the milestone.** Milestone "v0.2.0 forceSave fix" was named when v0.2.0 was the upcoming target; by close, the chart was at v0.5.2. Future milestones should be named without version pinning (e.g., "milestone-jellyfin-coverage" rather than "milestone-v0.2.0") OR explicitly accept the divergence and use a `milestone-*` tag prefix.
3. **Operator-driven Wave 0 + Wave N work best with explicit checkpoints.** Phase 7's `autonomous: false` plans (07-01, 07-06) had clear human-action gates with structured return contracts. The executor agent returned a checkpoint state, orchestrator presented to operator, operator drove the kubectl-side work, orchestrator merged the partial work and continued. Smooth UX.
4. **Cluster-side evidence is the truth, not local tests.** Phase 7 had ≥10 respx tests for the AudioDb plugin path, but only the live `cluster-apply-log.txt` revealed `plugin_missing_skip` for the YAML "AudioDb" vs cluster "AudioDB" casing mismatch. Production runs catch what unit tests miss. Lesson: SC#1 dispositive (live apply event log) is non-negotiable.
5. **Operator transparency on credentials matters.** The JELLYFIN_API_KEY value was disclosed plaintext in the chat during the bootstrap handoff. Documented as a deviation; operator advised to rotate. Future: orchestrator should never echo a key value to its own Bash; have the operator drive `kubeseal --raw` in their own shell so the secret never crosses session boundaries.

### Cost Observations

- Total commits in milestone range: ~140 on arr-stack `main` + ~12 on my-kluster `main`
- Total tags created: ~15 chart auto-tags (v0.2.0 through v0.5.2) + 1 milestone tag (`milestone-v0.2.0`)
- Subagent sessions in Phase 7 alone: ~8 (5 executor + 1 verifier + 1 phase-researcher + 1 plan-checker carried from `/gsd-plan-phase 7`)
- Model mix: orchestrator opus-4-7; executor/verifier sonnet-4-6 (per config.json)
- Worktree parallelization saved ~30 min wall-clock in Phase 7 Wave 1 vs serial

---

## Milestone: v0.5.0 — Jellyfin Categories-as-libs + CI/UX hardening

**Shipped:** 2026-05-24
**Phases:** 3 (16-18) | **Plans:** 3/3 | **Commits:** 31 since v0.4.0 close (1-day intensive)

### What Was Built

- **Phase 16** — `generate_jellyfin()` refactored to emit 10 `VirtualFolder` libs (1 per Category) replacing the 2 super-libs. D-07-LIB-01 reversed by D-16-PRUNE-01. `_reconcile_libraries()` extended with CREATE + prune-gated DELETE. Cluster UAT: 10 libs visible in web UI, 12 paths pruned from legacy super-libs, prune re-locked false.
- **Phase 17** — `tests.yml` path-filter extended to cover `tools/arrconf-ui/**` + 2 new jobs (`arrconf-ui-backend` triad + `arrconf-ui-frontend` quad). `chart-lint.yml` intentionally UNCHANGED — UI-only PRs do not trigger auto-tag (architectural SC#3 dispositive).
- **Phase 18** — qBit POST credentials env-injection (`QBT_USER` / `QBT_PASS`) for Sonarr+Radarr download_clients with pre-flight gate in `__main__.py` and fail-fast `ConfigError`. 12 respx tests; 95.38% coverage. Cluster UAT dispositive: 9/9 + 9/9 qBit DCs HTTP 200 on `/api/v3/downloadclient/test`; 0 plan_actions on 2nd run.
- **Side-quest unblock** — Pre-existing Sonarr `PathExistsValidator` 400 bug (pre-dated Phase 18 by ≥3 image versions) surfaced and resolved via `/gsd-debug sonarr-rpm-400-categories`; fix was 8× `mkdir -p` on the qBittorrent volume.

### What Worked

- **Code review auto-fix loop after first execution** — `/gsd-code-review` then `--fix` caught 2 BLOCKERs (CR-01 `ConfigError` not in caught exception tuple → wrong exit code; CR-02 fail-fast happened AFTER partial reconcile) that would have shipped untreated. Both required relaxing the plan's "do not touch `__main__.py`" rule mid-execution — the user's authorization for the deviation was clear, the fix was self-contained, and Triade Python stayed green throughout. Pattern worth keeping: always run `/gsd-code-review` immediately after `/gsd-execute-phase` and before declaring "shipping ready".
- **Skill chaining stayed shallow** — `/gsd-execute-phase 18` → `/gsd-verify-work 18` → `/gsd-debug` (mid-UAT) → resume `/gsd-verify-work 18` → `/gsd-complete-milestone` all in one session, with each skill cleanly handing off state via planning artifacts (no implicit context). The debug session was opened, resolved, and archived without polluting Phase 18's scope.
- **CLAUDE.md "Accumulated-bumps escape hatch" runbook paid off** — the chart pin diverged from the auto-tag train (v0.10.x in values.yaml vs v0.13.0 auto-tag), and the explicit `git tag v0.12.1 HEAD && git push origin v0.12.1` rescue was already documented as a known pattern from Phase 10. Worth keeping the pattern as a recurring footgun reference.

### What Was Inefficient

- **`gsd-sdk milestone.complete` accomplishments extraction is shallow** — it pulled the first SUMMARY.md bullets verbatim including a "Rule 1 - Bug" boilerplate fragment that wasn't a real accomplishment. Required manual rewriting of the v0.5.0 MILESTONES.md entry to bring it up to v0.4.0's quality. Worth either improving the extractor or making the manual rewrite an explicit step in the workflow.
- **Phase 17 had no SUMMARY.md at the time of milestone close** — executed inline pre-`/gsd-execute-phase` worktree convention; a retroactive SUMMARY.md had to be authored from commits + ROADMAP closure note to satisfy the formal close. Worth establishing a project convention: even inline-executed phases get a SUMMARY.md at close.
- **HUMAN-UAT format vs verify-work UAT.md format** — the project uses Markdown `**Status:**` headers in HUMAN-UAT.md (operator runbooks) while `audit-open` reads YAML frontmatter `status:`. Resulted in 3 "unknown" false-positives during pre-close audit. Worth standardizing on frontmatter-style metadata across all UAT artifacts.

### Patterns Established

- **`/gsd-debug` mid-UAT side-quest pattern** — A UAT may surface a pre-existing bug unrelated to the current phase. Opening a `/gsd-debug` session within the UAT context (instead of failing the UAT or scoping a new phase) keeps the bug investigation atomic, archives it to `.planning/debug/resolved/`, and lets the UAT resume cleanly once the side-quest closes. Phase 18 used this pattern; recommend codifying.
- **Pre-flight gate vs in-reconcile gate (D-18 fix-batch lesson)** — When a reconciler step depends on external state (env vars, filesystem, secrets), the validation MUST run as a pre-flight gate BEFORE any side-effecting POSTs. CR-02 caught this: validating mid-reconcile means a partial cluster write on failure. The fix added a parallel pre-flight gate to the existing qBittorrent `__main__.py:269-281` gate. Worth extending to other reconcilers as a defense-in-depth audit.

### Key Lessons

- **Don't block "do not touch X" rules dogmatically** — Phase 18's plan said "do not touch `__main__.py`" but the code review revealed that constraint contradicted SC#1 (CLI exit code 2 on missing env). The right call was to override the constraint when it conflicted with success criteria, not to relax SC#1.
- **Observability tech debt compounds silently** — `client_base.py:80` logs `response.text[:200]` for 5xx but not 4xx; this is why the Sonarr `PathExistsValidator` 400 went unsurfaced for 3 image versions. A 2-line change. Worth scoping as a v0.6.0 micro-plan to prevent the next silent 4xx from biting.
- **Auto-tag train aggregates ALL unreleased commits** — Phase 17's `feat(17)` was unreleased between v0.12.0 (Phase 16 SC#3) and the Phase 18 push, so `mathieudutour/github-tag-action` minor-bumped on the combined diff (v0.13.0, not the patch I expected). The CLAUDE.md escape hatch handled it, but the underlying issue should become a process note: **push intermediate tags between phases or accept the minor bump.**

### Cost Observations

- **Single-day milestone close-out** — Phase 16 planned 2026-05-22, executed 2026-05-23–24, Phases 17-18 executed 2026-05-24 in succession. The intensive close-out worked because each phase was a small, well-scoped change (1 plan, 1 SUMMARY) and the test/lint infrastructure was already solid from v0.4.0. Worth keeping milestones small (3 phases ≈ 1-2 days) rather than dragging them across weeks.
- **Cluster UAT efficiency** — Using port-forward + local curl + Python `urllib.request` for the 18-DC `/test` endpoint sweeps (Sonarr + Radarr, 18 total) ran in ~10s and was scriptable. Worth keeping this pattern (vs UI-click sweep) for future dispositive auth tests.
- Model mix: orchestrator opus-4-7; executor/verifier/code-reviewer/code-fixer/debugger sonnet-4-6 (per config.json). No model changes from v0.4.0.

---

## Cross-Milestone Trends

| Metric | v0.2.0 | v0.3.0 | v0.4.0 | v0.5.0 |
|--------|--------|--------|--------|--------|
| Phases shipped | 11 | 3 | 4 | 3 |
| Plans shipped | 65/66 | 16/16 | 11/11 | 3/3 |
| Validated requirements | 17/19 | — | — | 3/3 (REQ-jellyfin-categories-as-libs, REQ-arrconf-ui-ci, REQ-qbit-post-credentials) |
| Deferred items at close | 16 | — | — | 6 (5 v0.3-4 carry-forward + 1 v0.5 new: client_base.py 4xx logging) |
| Major mid-flight pivots | 2 (Phase 2.1 + 2.2 inserts) | — | — | 1 (Phase 18 plan task 6 override after code review) |
| Production cutover successes | 1 (Phase 7 chain in ~45 min) | — | — | 1 (Phase 18 v0.12.1 rescue tag in ~5 min) |
| Side-quest debug sessions | — | — | — | 1 (sonarr-rpm-400-categories, pre-Phase-18 bug surfaced + resolved mid-UAT) |

**Recurring themes to watch in v0.3.0:**

- Does pre-bumping `arrconf.image.tag` actually eliminate the 2-bump cycle? (D-07-CHART-PIN-LOOP)
- Does the worktree-branch-vs-main commit anomaly recur? (Phase 7 Wave 2 single-occurrence)
- Does `ruff format --check` make it into CLAUDE.md / gsd-executor reliably? (D-07-RUFF-FORMAT-CI)
- Is the `milestone-*` tag prefix the right convention for logical milestones vs chart auto-tags?
- Do the 16 deferred items get bundled into a single v0.3.0 cleanup phase, or distributed across feature phases?

---

*Created: 2026-05-17 at v0.2.0 milestone close.*
