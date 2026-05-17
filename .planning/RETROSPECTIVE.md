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

## Cross-Milestone Trends

| Metric | v0.2.0 | (next milestones append here) |
|--------|--------|-------------------------------|
| Phases shipped | 11 | — |
| Plans shipped | 65/66 | — |
| Validated requirements | 17/19 | — |
| Deferred items at close | 16 | — |
| Major mid-flight pivots | 2 (Phase 2.1 + 2.2 inserts) | — |
| Production cutover successes | 1 (Phase 7 chain dispositive in ~45 min) | — |

**Recurring themes to watch in v0.3.0:**

- Does pre-bumping `arrconf.image.tag` actually eliminate the 2-bump cycle? (D-07-CHART-PIN-LOOP)
- Does the worktree-branch-vs-main commit anomaly recur? (Phase 7 Wave 2 single-occurrence)
- Does `ruff format --check` make it into CLAUDE.md / gsd-executor reliably? (D-07-RUFF-FORMAT-CI)
- Is the `milestone-*` tag prefix the right convention for logical milestones vs chart auto-tags?
- Do the 16 deferred items get bundled into a single v0.3.0 cleanup phase, or distributed across feature phases?

---

*Created: 2026-05-17 at v0.2.0 milestone close.*
