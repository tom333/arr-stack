# Phase 17 — arrconf-ui CI coverage — HUMAN-UAT

**Phase:** 17
**Status:** Pending operator validation (post-PR-merge)
**Plan:** 17-A

## Pre-PR baseline (already confirmed by orchestrator 2026-05-24)

- ✅ `arrconf-ui` Python triad green (`ruff format --check`, `ruff check`, `mypy .`, `pytest -q` — 32 tests pass, 13 files mypy-clean)
- ✅ `arrconf-ui/web` frontend quad green (`npm ci`, `npm run check` 92 files / 0 errors, `npm run typecheck` silent, `npm run build` 866ms)
- ✅ `uv sync --frozen` works on arrconf-ui (lockfile aligned with pyproject.toml — `Audited 53 packages`)
- ✅ YAML syntax of `.github/workflows/tests.yml` valides (3 jobs: `test`, `arrconf-ui-backend`, `arrconf-ui-frontend`)
- ✅ `.github/workflows/chart-lint.yml` bit-for-bit unchanged (`git diff --stat .github/workflows/chart-lint.yml` empty)

## Scenarios

### Scenario 1 — Phase 17's own PR shows the 2 new CI jobs green (mandatory)

**When:** After pushing Phase 17 commits to `main` (or via PR if branch flow), the next CI run on the merged commit should fire the 3 jobs.

**Steps:**

1. `gh pr view <PR-number>` or browse to the PR on GitHub.
2. Click the "Checks" tab.
3. Confirm 3 jobs visible : `test` (arrconf), `arrconf-ui-backend`, `arrconf-ui-frontend`.
4. All 3 should be green ✓ before merge.

**Or, if pushed directly to main without PR:**

```bash
SSH_AUTH_SOCK=/run/user/1000/openssh_agent gh run list --workflow=tests.yml --branch=main --limit=3
```

Expected : the latest run (on the Phase 17 commit) shows `success` for the 3 jobs.

**Outcome:** ☐ PASS / ☐ FAIL

### Scenario 2 — UI-only PR does NOT trigger chart-lint or auto-tag (mandatory, architectural)

**When:** After Phase 17 is merged, the next time someone (operator or Renovate) opens a PR touching ONLY `tools/arrconf-ui/**` (no `tools/arrconf/**`, no `charts/**`).

**Steps:**

1. Identify a PR matching the criterion (or open a trivial test PR — e.g. comment-only change in `tools/arrconf-ui/web/src/App.svelte`).
2. Check workflows triggered on that PR via `gh pr checks <PR-number>` or the GitHub UI.
3. Confirm `tests.yml` ran (and ideally green).
4. Confirm `chart-lint.yml` **did NOT run** for that PR.
5. After merge, confirm `gh run list --workflow=chart-lint.yml --limit=10` does not include a run triggered by that merge commit.

**Why this matters:** SC#3 of REQ-arrconf-ui-ci is architectural — `chart-lint.yml`'s path-filter excludes `tools/arrconf-ui/**`. We do NOT want UI changes to bump the `arrconf.image.tag` chain or create churning my-kluster Renovate PRs.

**Outcome:** ☐ PASS / ☐ FAIL / ☐ DEFERRED (waiting for a UI-only PR opportunity)

### Scenario 3 — README CI matrix section reads cleanly (mandatory)

**When:** Right after Phase 17 is merged.

**Steps:**

1. Open `README.md` on GitHub (rendered Markdown view).
2. Navigate to "Stack technique" — confirm the `CI` row mentions the 3 jobs.
3. Navigate to "Local config UI → CI coverage" — confirm the 2-job matrix table reads correctly.
4. Verify the note about `chart-lint.yml` ignoring `tools/arrconf-ui/**` is present.

**Outcome:** ☐ PASS / ☐ FAIL

### Scenario 4 — Dummy UI-only PR confirms isolation (optional follow-up)

**When:** Any time post-merge if the operator wants explicit dispositive proof of Scenario 2 without waiting for a natural UI-only PR.

**Steps:**

1. Create a throwaway branch: `git switch -c test-ui-only-ci`.
2. Add a comment to any `.svelte` file: `<!-- Phase 17 SC#4 test, can be reverted -->`.
3. Commit + push + open a PR.
4. Observe GitHub Checks tab:
   - `tests.yml` runs with **only** the `arrconf-ui-frontend` job kicking off (the `test` and `arrconf-ui-backend` jobs *will* also fire because the workflow path-filter triggers them all on any matching path — this is by design D-17-WORKFLOW-01).
   - `chart-lint.yml` does NOT run for this PR (= dispositive SC#3).
5. Close PR + delete branch without merging (cleanup).

**Outcome:** ☐ PASS / ☐ FAIL / ☐ SKIPPED (Scenario 2 considered sufficient)

## Sign-off

When 3 mandatory scenarios PASS, Phase 17 is fully closed. Update `.planning/ROADMAP.md` Phase 17 entry from `[ ]` to `[x]` and propagate to `.planning/STATE.md`.

Scenario 4 (optional) can be exercised any time later if dispositive proof is desired ; not required for close.
