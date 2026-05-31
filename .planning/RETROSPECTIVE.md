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

## Milestone: v0.6.0 — arrconf observability — 4xx body logging

**Shipped:** 2026-05-25
**Phases:** 1 (Phase 19) | **Plans:** 1/1 (via `/gsd-quick` instead of `/gsd-execute-phase`) | **Commits:** 5

### What Was Built

`client_4xx` structlog warning event in `ArrApiClient._request` between the 404 NotFoundError fast-path and the 5xx ServerError block. Payload: `client`, `method`, `path`, `status_code`, `body_excerpt=response.text[:500]`. Preserves `raise_for_status()` behavior — no new exception type. 5 respx tests cover the matrix (400 verbatim, 422 truncation, 401/404 short-circuit, 500 no cross-fire). Chart-pin 0.12.1 → 0.14.0 (initial 0.13.0 then rescue alignment with v0.14.0 auto-tag). v0.5.0's Sonarr `PathExistsValidator` 400 incident class can no longer hide for 3 image versions.

### What Worked

- **`/gsd-quick` as the right tool for micro-milestones.** Phase 19's full plan was overhead for a 2-line code change. The quick task bypassed discuss/plan/execute and went straight to atomic-commit execution with TDD discipline (5 tests RED → 9-line implementation GREEN). End-to-end (planner spawn → executor merge → milestone close) ran ~30 minutes. Pattern validated: when a milestone is sized as a single requirement / single phase / single deliverable, `/gsd-quick` is the natural path and the milestone close folds the quick task into the phase via a `[x] ... shipped via /gsd-quick <slug>` annotation in ROADMAP.md.
- **Same-session multi-skill chain stayed coherent.** Within a single session: `/gsd-execute-phase 18` → `/gsd-verify-work 18` → `/gsd-debug sonarr-rpm-400-categories` (resolved mid-UAT) → resume UAT → `/gsd-complete-milestone v0.5.0` → `/gsd-new-milestone v0.6.0` → `/gsd-quick "client_base 4xx logging"` → `/gsd-complete-milestone v0.6.0`. 2 milestones shipped from a single conversation, with every handoff via planning artifacts (no implicit context carry-over). Skills compose cleanly when each writes structured state to disk.

### What Was Inefficient

- **`milestone.complete` accomplishments extractor pulled garbage.** Same issue as v0.5.0 close, but worse this time because v0.6.0's "phases" list (per the SDK's view) included stale Phase 9/10/11 v0.3.0 carry-forward directories. SDK reported "3 phases, 16 plans, 14 tasks" for a milestone that was 1 phase / 1 plan / 1 quick task. MILESTONES.md had to be rewritten from scratch. **Same recurring inefficiency from v0.5.0 — confirms this is a real SDK gap, not a one-off.**
- **Auto-tag train mismatch happened AGAIN.** v0.5.0 had v0.13.0 vs values.yaml 0.12.1; v0.6.0 has v0.14.0 vs values.yaml 0.13.0. Both fixed in one extra commit each, but recurring across consecutive milestones means the CLAUDE.md "Accumulated-bumps escape hatch" runbook is being used every milestone close. Process candidate: standardize the rescue commit as the LAST commit of every milestone close cycle, OR automate it via a post-push hook.
- **Untracked PLAN.md blocked the worktree merge.** During /gsd-quick orchestration, the planner wrote PLAN.md to the main tree (uncommitted); the executor in the worktree ALSO created/committed the same path; the worktree merge then refused to overwrite the untracked file. Resolved by `rm -f` of the main-tree copy, but worth either (a) committing PLAN.md to main BEFORE spawning the executor (`pre-dispatch plan commit` per workflow step 5.6 — which was skipped because we're on a main-branch quick task, not a feature branch), or (b) having the planner write PLAN.md directly to the worktree's path namespace.

### Patterns Established

- **Micro-milestone via `/gsd-quick` close-out pattern:** when ROADMAP.md describes a milestone as "1 phase, 1 plan", `/gsd-quick` is the right execution path. At milestone close, mark the phase `[x]` in ROADMAP with a `shipped via /gsd-quick <slug>` note, archive the `.planning/quick/<slug>/` directory to `.planning/milestones/v<X.Y>-quick/`. Quick artifacts coexist with phase artifacts in archives — no migration friction.
- **MILESTONES.md manual rewrite is a workflow step, not a fix.** Given the SDK extractor's recurring miss, treat the auto-generated entry as a placeholder and immediately follow the SDK call with a structured rewrite mirroring the previous milestone's quality. This is now a known step, not an exception.

### Key Lessons

- **Tag train alignment is a process problem, not a one-off bug.** v0.5.0 and v0.6.0 both required rescue commits. The fix is procedural (push intermediate tags between phases) OR automated (post-push hook that verifies values.yaml matches the latest auto-tag and emits a rescue commit). Worth scoping in v0.7.0 if it bites a third time.
- **The planner's "single atomic commit" rule for tiny tasks is correct.** Phase 19's plan explicitly said "ALL changes in ONE commit per CLAUDE.md co-bump pattern" — the executor honored it (commit `9726d81` has code + test + chart pin together). For micro-tasks, batching is the right granularity; per-task commits would have added 3× the release-chain ceremony for no review value.

### Cost Observations

- **Smallest milestone in project history.** 1 day (started 2026-05-24, shipped 2026-05-25), 1 requirement, 1 deliverable, ~30 min execution, 5 commits. Worth keeping as the model for future observability / 2-line micro-plans.
- **Model mix unchanged from v0.5.0.** orchestrator opus-4-7; planner/executor sonnet-4-6. No changes warranted.

---

## Milestone: v0.7.0 — Media stack scope closure

**Shipped:** 2026-05-25
**Phases:** 0 (doc-only, no `/gsd-execute-phase`) | **Plans:** 0 | **Commits:** 2 (492d28a doc edits + 9b3f815 STATE.md)

### What Was Built

A **decision**, not code. Declared the media stack complete and closed at 9 apps + arrconf + configarr (Sonarr, Radarr, Prowlarr, qBittorrent, Seerr, Jellyfin, FlareSolverr, Cleanuparr, SuggestArr). Removed Bazarr from arrconf's intent surface in 4 files (CLAUDE.md, spec.md, PROJECT.md, ROADMAP.md). Declared Bazarr (subtitles), Lidarr (music), Whisparr (adult), Readarr (books) explicitly **out of scope** with rationale documented in PROJECT.md "Out of Scope" section. Three decisions captured: D-19-CLOSURE-01 (stack-is-closed), D-19-RATIONALE-01 (Bazarr-specifically-not-needed), D-19-VIDEO-ONLY-01 (siblings-cover-different-domains-not-bolt-ons).

Total change footprint: ~30 lines edited across 5 files. No code, no tests, no chart bump, no auto-tag.

### What Worked

- **"The milestone IS the decision, the artifact IS the doc edit" pattern.** This was a structural decision that warranted milestone-level traceability (future grep for "why no Bazarr" lands on the v0.7.0 entry in MILESTONES.md) without the scaffolding cost of `/gsd-new-milestone v0.7.0` → `/gsd-discuss-phase 20` → `/gsd-plan-phase 20` → `/gsd-execute-phase 20`. Inline edits + MILESTONES.md entry + git tag = 5 minutes total, full provenance preserved. Pattern documented inline in MILESTONES.md v0.7.0 entry so it's discoverable for future analogous decisions ("REQ-X retired", "ADR-Y reversed", "ecosystem-Z deprecated").
- **Asking WHY before HOW.** The Out of Scope section explicitly requires reasoning ("*Includes reasoning to prevent re-adding*"). Asking the operator "why is Bazarr out?" *before* writing the entry gave 4 concrete options ("no real need" / "maintenance cost" / "workflow manuel" / "Categories made it redundant") — the chosen rationale ("pas de besoin réel — burned-in subs OR Jellyfin/Kodi native search") is now stable scope-defense rather than an ambivalent "v2 potentiel".
- **Two-question scope expansion.** Asked separately: "while we're at it, also close Lidarr/Whisparr/Readarr?" The answer (yes — declare stack complete) turned a 1-app cleanup into a 4-decision scope closure, but cost the same effort. Worth keeping the pattern: when cleaning up one "ambivalent maybe" item, audit adjacent ambivalent items in the same pass.

### What Was Inefficient

- **No automated detection of stale doc references.** README.md and CLAUDE.md "État actuel" sections were stale (referenced v0.3.0 / `:0.6.7` / "6 apps couvertes en v0.3.0" / "10 aliases") — drift that built up across v0.4.0, v0.5.0, v0.6.0 closes. None of the milestone-close workflows caught this. Worth adding a "doc drift check" step to `/gsd-complete-milestone` that greps for known-stale tokens (previous milestone version mentions, previous image tag, previous alias count). Surfaced and fixed during this v0.7.0 close as a sweep — added to the v0.7.0 commit batch.

### Patterns Established

- **Zero-phase milestone for structural scope decisions.** New pattern documented in MILESTONES.md v0.7.0 entry: structural scope decisions (declaring out, retiring, deprecating) are valid milestone material even with zero phases — the milestone IS the decision, the artifact IS the doc edit. Future analogous milestones should follow inline-edit + MILESTONES-entry + tag pattern; do NOT run `/gsd-new-milestone` scaffold for these.
- **"Out of Scope" reasoning as a stop-discussion artifact.** PROJECT.md "Out of Scope" section is now load-bearing — its reasoning is what prevents the same scope-creep conversation from happening at every milestone close. The v0.6.0 close had a v0.7.0+ candidate list that included REQ-bazarr-addition; v0.7.0 removed it explicitly. The next milestone close should NOT re-surface it because the rationale is documented to prevent re-adding.

### Key Lessons

- **Saying "no" is a release.** Three milestones (v0.5.0 v0.6.0 v0.7.0) shipped in the same session, but the third had zero code. The discipline of recording a structural "no" with the same ceremony as a feature shipment prevents the project's intent surface from quietly expanding. Worth keeping.
- **"V2 potential" is decision debt, not flexibility.** The previous PROJECT.md text said "Bazarr / Lidarr / Whisparr / Readarr — v2 potentiel, ajoutables sans repenser l'architecture". That phrasing was deliberately ambivalent (signaling "maybe later" without committing). v0.7.0 converted that to explicit out-of-scope — clarity is worth more than optionality at this project stage. Future projects: be wary of "v2 potential" lists; they accumulate and dilute scope without ever shipping.

### Cost Observations

- **Smallest milestone in project history (by code).** v0.7.0 = 0 lines of code, 30 lines of docs. v0.6.0 was 2 lines of code (smallest by code+tests). The pattern of micro/zero-code milestones validates that GSD scales down to the smallest meaningful unit of project-state change.
- **Session total: 3 milestones / 0 phases for v0.7.0 / 1 phase for v0.6.0 / 3 phases for v0.5.0 = 4 phases total + 1 quick task + 1 debug session.** All shipped in one continuous session (~6 hours wall clock). Possible because each milestone was small enough to fit within a single context window without compaction. The "small milestones win" hypothesis is reinforced.

---

## Milestone: v0.8.0 — Categories cleanup — v0.2.0 legacy migration close-out

**Shipped:** 2026-05-27
**Phases:** 4 (20-23) | **Plans:** 5/5 | **Commits:** 60 | **Duration:** ~3 days (operator-paced, destructive)

### What Was Built

Closed the half-applied v0.2.0→v0.3.0 Categories migration at the config level: read-only audit CLI (`arrconf audit`/`audit-verify`, P20) → one-shot live migration script `migrate-categories.py` (21 *arr PUTs + 37 torrents relocated, P21) → `differ.force_prune` + pydantic legacy-path guard shipped as `arrconf:0.15.0` with live cleanup of 4 legacy roots + catch-all DC id=1 + 3 orphan torrents (P22) → live operator UAT proving durability, SC#1-4 PASS (P23).

### What Worked

- **Audit-then-migrate separation.** Splitting the read-only inventory (P20, GET-only, zero mutation invariant grep-enforced) from the destructive apply (P21) meant the dangerous step ran against a reviewed, operator-edited plan with no ambiguous runtime decisions. The `audit-verify` gate (rejects unresolved `?`/`TBD` cells) forced every per-item decision to be made before any mutation.
- **Cross-phase verification as a real safety net.** Phase 22 shipped without its own VERIFICATION.md, but Phase 23's live UAT (legacy roots absent + idempotent apply ×2) transitively proved the prune deliverable. A live end-to-end UAT is stronger evidence than a retroactive per-phase verification doc.
- **ADR-6 pre/post snapshots on every destructive phase.** Bounded diffs (P21: exactly 4 files changed; P23: zero root_folder drift) gave independent, committed proof of what actually changed — invaluable when the cluster is later unreachable for live re-verification.

### What Was Inefficient

- **Audit-to-apply drift window.** The Phase 20 audit ran 2026-05-25; Phase 21 applied 2026-05-27. Disk drifted in between → 10 of 11 filesystem moves were `both_missing`, soft-skipped, leaving 10 DB records pointing at Category paths with no file on disk. **Lesson: re-audit immediately before a destructive apply, not days earlier.**
- **A prune feature too risky to run live is half-delivered.** Phase 22 built + tested (455 respx) `force_prune=true`, then did NOT use it for the live cleanup — the mixed legacy+Category tag state would have over-deleted, so the operator used surgical id-targeted API DELETEs instead. The reconciler DELETE branch has zero production proof. **Lesson: a feature whose live path you don't dare exercise should be flagged as unexercised debt (it was — re-verify before `prune:true`), and ideally its activation precondition (full Category-tag migration) should be in the same milestone or explicitly sequenced.**
- **Phase 22 skipped its VERIFICATION.md.** A process gap — the milestone audit had to manually override the 3-source matrix using a code audit + integration checker. Cheap to avoid: write the VERIFICATION even for human-action phases.

### Patterns Established

- **"Cleanup milestone" pattern.** A milestone whose entire scope is "finish what a prior milestone applied only halfway" — no new features, only audit + migrate + lock-in (prune) + UAT. Scope discipline (explicit "no new Category, no new reconciler step") kept it from creeping into a feature milestone.
- **Operator-live destructive phases** (P21/P23 `human-action`) bracketed by committed ADR-6 snapshots + a French runbook (`21-RUNBOOK.md`).

### Key Lessons

- Re-audit right before destructive apply — drift windows are real and silent.
- Built-but-unexercised live paths are debt; record the activation precondition.
- Cross-phase live UAT can substitute for a missing per-phase VERIFICATION, but don't skip the VERIFICATION on purpose.
- **Milestone tag vs chart tag collision:** this repo auto-tags chart releases (`v0.1.0`…`v0.15.0`) on every push; milestone versions reuse the same `vX.Y.Z` space and so cannot get dedicated git tags. Milestone versioning is planning-only here — `/gsd-complete-milestone`'s git-tag step is inapplicable.

### Cost Observations

- Mostly operator wall-clock (live cluster, port-forwards, per-item decisions), not model time. Planning on opus; milestone integration check delegated to a sonnet `gsd-integration-checker` subagent (~65k tokens, isolated).
- One quick task absorbed inline (260527-jfk autoTMM `preferences.enable`) rather than a phase — micro-fix discipline held.

---

## Milestone: v0.9.0 — configarr-in-UI + Jellyfin skip-intro

**Shipped:** 2026-05-31
**Phases:** 4 (24-27) | **Plans:** 13/13 | **Requirements:** 13/13 validated (8 CFGUI + 5 JFSKIP)

### What Was Built

Two heterogeneous features. **Jellyfin Intro Skipper** (Phase 24, arrconf `:0.17.0`): reconciler extended to register the Intro Skipper plugin repo, install via the two-run model (Run N queues + logs the single operator `kubectl rollout restart`, Run N+1 enables + configures `MaxParallelism=1`), and set `EnableChapterImageExtraction` on all 10 libraries; ADR-9 reverses D-07-PLUGINS-01 to install-capable. **configarr-in-UI** (Phases 25-27): `arrconf-ui` now edits `configarr.yml` via a schema-driven form (`ConfigarrRootConfig` pydantic, 4 endpoints, task-zero anti-leak round-trip preserving `!env`/`!secret`), with TRaSH CF picker (name→trash_id, multi-id-safe), append-only TRaSH QP picker (collision-blocked), and read-only Recyclarr reference; TRaSH catalog baked at build time (pinned SHAs, zero runtime GitHub HTTP).

### What Worked

- **Independent parallelizable features.** Phase 24 (arrconf Python) and Phases 25-27 (arrconf-ui) had zero code dependency — documented up front, so the Jellyfin reconciler could ship and reach prod (`:0.17.0`) while the UI chain progressed separately.
- **Task-zero anti-leak test.** Shipping the `!env`/`!secret` byte-preservation round-trip test BEFORE any configarr write-path code (CFGUI-01) meant the secret-leak risk was gated from commit one, not retrofitted.
- **Build-time-baked TRaSH catalog.** Pinned-SHA static assets removed all runtime GitHub HTTP from both backend and frontend — deterministic, offline-safe, ADR-5-clean (SC#2).
- **Strict scope boundary on the Recyclarr picker.** Read-only reference with zero `include:` insertion (CFGUI-06) avoided the merge-hazard with the 6 hand-rolled French CFs — deferred the write path to v1.x deliberately rather than half-building it.

### What Was Inefficient

- **Milestone closed while a blocking checkpoint was still open.** Phase 24's plan 24-03 (operator live-verify, `autonomous: false`) paused at its blocking human-verify checkpoint and never got a SUMMARY, yet STATE.md was marked `milestone_complete` (13/13) with ROADMAP still showing Phase 24 `[ ]`. The drift surfaced only when `/gsd-execute-phase 24` was re-run later. **Lesson: a blocking human-verify checkpoint must gate milestone-complete; don't let phases 25-27 completing flip the milestone flag while an earlier phase's operator gate is unresolved.**
- **ADR-6 snapshots ran operator-side, never committed.** Phase 24's required before/after Jellyfin snapshots were taken against the live cluster but not committed to the repo — accepted as a documented deviation, but it weakens the forensic trail ADR-6 exists to provide.

### Patterns Established

- **Two-run plugin install model (D-02).** Jellyfin loads plugins only at boot, so arrconf splits install (Run N, logs `plugin_install_queued` + restart hint) from enable+config (Run N+1) across a deliberate operator restart — install-only, never uninstall/prune.
- **UI edits the file, engine still applies (ADR-5 reaffirmed).** `arrconf-ui` learned the configarr model and edits `configarr.yml`, but configarr remains the sole applier and no *arr API URL ever enters arrconf-ui — the boundary held across 3 UI phases.

### Key Lessons

- Blocking operator checkpoints must hard-gate milestone completion — a late-discovered open checkpoint is a tracking-integrity failure.
- Commit ADR-6 snapshots even when verification is operator-driven; an uncommitted snapshot is not a forensic record.
- **Milestone tag vs chart tag collision (recurring):** `v0.9.0` already existed as a chart auto-release tag, so `/gsd-complete-milestone`'s git-tag step was skipped again — milestone versioning here is planning-archive only.

### Cost Observations

- Phase 24 closure + milestone archive run on opus inline; verifier delegated to a sonnet `gsd-verifier` subagent (~95k tokens, isolated).
- Most of Phase 24's cost was operator wall-clock (live two-run verify + Kodi spike), not model time.

---

## Cross-Milestone Trends

| Metric | v0.2.0 | v0.3.0 | v0.4.0 | v0.5.0 | v0.6.0 | v0.7.0 | v0.8.0 | v0.9.0 |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| Phases shipped | 11 | 3 | 4 | 3 | 1 | 0 | 4 | 4 |
| Plans shipped | 65/66 | 16/16 | 11/11 | 3/3 | 1/1 (via /gsd-quick) | 0/0 (doc-only) | 5/5 | 13/13 |
| Validated requirements | 17/19 | — | — | 3/3 | 1/1 (OBS-01) | 0/0 (no new req, removed REQ-bazarr-addition) | 4/4 (CAT-CLEANUP 1-4; 2 w/ caveats) | 13/13 (8 CFGUI + 5 JFSKIP) |
| Out-of-scope decisions recorded | 8 | — | — | — | — | 3 (D-19-CLOSURE/RATIONALE/VIDEO-ONLY) | — (cleanup scope, explicit no-new-Category) | 2 (Recyclarr include: deferred v1.x; Jellyfin native subs out) |
| Deferred items at close | 16 | — | — | 6 | 6 | 5 (REQ-bazarr-addition retired, 1 less carry-forward) | 8 (incl. no-22-VERIFICATION + unexercised force_prune) | 5 (P27 UAT/verification operator-pending + carry-forwards) |
| Major mid-flight pivots | 2 (Phase 2.1 + 2.2 inserts) | — | — | 1 (Phase 18 plan task 6 override) | 0 | 0 | 1 (P21 both_missing soft-skip; P22 surgical-vs-force_prune) | 1 (24-03 checkpoint left open at milestone-complete; reconciled later) |
| Production cutover successes | 1 (Phase 7 chain ~45 min) | — | — | 1 (Phase 18 v0.12.1 rescue ~5 min) | 1 (Phase 19 v0.14.0 rescue ~5 min) | — (no chart change) | 1 (:0.15.0 deployed + P23 live UAT) | 1 (:0.17.0 deployed + P24 live two-run UAT) |
| Side-quest debug sessions | — | — | — | 1 (sonarr-rpm-400-categories) | 0 | 0 | 0 (1 quick task 260527-jfk) | 0 |
| Milestone duration | weeks | — | — | 1 day intensive | 1 day micro | <30 min (same-session w/ v0.6.0) | ~3 days (operator-paced, destructive) | ~4 days (24 first, then 25-27 chain) |
| Auto-tag train rescue needed | — | — | — | 1 (v0.12.1 manual) | 1 (values.yaml co-bump to v0.14.0) | 0 (no code change) | 0 (clean co-bump 0.14.1→0.15.0) | 0 (P24 co-bump to 0.17.0; P25-27 UI-only, no co-bump) |
| Code change footprint | 7044 ins (v0.5.0 net) | — | — | 7044 ins | 91 ins (4xx logging + 5 tests + co-bump) | 30 ins (5 doc files) | ~2.5k LOC (audit.py 997 + migrate 749 + prune/guard + tests; excl. snapshots) | reconciler + ConfigarrRootConfig + 4 endpoints + 3 trash endpoints + 3 Svelte pickers + baked catalog |
| Milestone audit verdict | — | passed_with_caveats | — | — | — | — | tech_debt (no blockers) | no formal audit (5 items acknowledged at close) |

**Recurring themes to watch in v0.3.0:**

- Does pre-bumping `arrconf.image.tag` actually eliminate the 2-bump cycle? (D-07-CHART-PIN-LOOP)
- Does the worktree-branch-vs-main commit anomaly recur? (Phase 7 Wave 2 single-occurrence)
- Does `ruff format --check` make it into CLAUDE.md / gsd-executor reliably? (D-07-RUFF-FORMAT-CI)
- Is the `milestone-*` tag prefix the right convention for logical milestones vs chart auto-tags?
- Do the 16 deferred items get bundled into a single v0.3.0 cleanup phase, or distributed across feature phases?

---

*Created: 2026-05-17 at v0.2.0 milestone close.*
