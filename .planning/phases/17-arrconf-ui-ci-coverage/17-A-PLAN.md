---
phase: 17-arrconf-ui-ci-coverage
plan: A
type: execute
wave: 1
depends_on: []
autonomous: false
requirements:
  - REQ-arrconf-ui-ci
files_modified:
  - .github/workflows/tests.yml
  - README.md
  - .planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md
tags:
  - ci
  - github-actions
  - arrconf-ui
must_haves:
  truths:
    - "`.github/workflows/tests.yml` has both `on.pull_request.paths` AND `on.push.paths` extended to include `tools/arrconf-ui/**` (D-17-WORKFLOW-01 path-filter union)."
    - "`.github/workflows/tests.yml` defines a new job `arrconf-ui-backend` (working-directory `tools/arrconf-ui`) running uv sync + ruff format check + ruff check + mypy + pytest -q — withOUT `--cov-fail-under` (D-17-COVERAGE-01)."
    - "`.github/workflows/tests.yml` defines a new job `arrconf-ui-frontend` (working-directory `tools/arrconf-ui/web`) running `npm ci` + `npm run check` + `npm run typecheck` + `npm run build` — all 4 commands per D-17-FRONTEND-01."
    - "Frontend job uses `actions/setup-node@v6` with `node-version: '22'` hardcoded (D-17-NODE-01) and `cache: 'npm'` + `cache-dependency-path: tools/arrconf-ui/web/package-lock.json` per setup-node official docs."
    - "`.github/workflows/chart-lint.yml` is BIT-FOR-BIT IDENTICAL to its pre-Phase-17 state: `git diff <pre-phase17-sha> HEAD -- .github/workflows/chart-lint.yml` produces zero output (D-17-NO-CHART-LINT-CHANGE → architectural guarantee for SC#3)."
    - "No file under `tools/arrconf/**`, `tools/arrconf-ui/**`, or `charts/**` is modified by Phase 17 commits (CI-only change — no chart-pin co-bump)."
    - "`README.md` Stack technique row mentioning `tests.yml` is updated, OR a new short section documents the 3 CI jobs (`test`, `arrconf-ui-backend`, `arrconf-ui-frontend`) and their path-filter triggers."
    - "`.planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md` exists with the 4 scenarios from the planning context (SC#1-4)."
  artifacts:
    - path: ".github/workflows/tests.yml"
      provides: "Extended workflow — 3 jobs total (existing `test` for arrconf + 2 new arrconf-ui jobs); path-filter union includes `tools/arrconf-ui/**`"
      contains: "arrconf-ui-backend"
    - path: ".github/workflows/tests.yml"
      provides: "Frontend job pinned to Node 22 with npm cache"
      contains: "node-version: '22'"
    - path: "README.md"
      provides: "CI matrix doc — 3 jobs in `tests.yml` (test + arrconf-ui-backend + arrconf-ui-frontend)"
      contains: "arrconf-ui-frontend"
    - path: ".planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md"
      provides: "4 UAT scenarios for operator close-out (PR Checks green, chart-lint untriggered post-merge, README clean, optional follow-up UI-only PR)"
  key_links:
    - from: ".github/workflows/tests.yml on.{push,pull_request}.paths"
      to: "tools/arrconf-ui/**"
      via: "path-filter union (existing `tools/arrconf/**`, `schemas/**`, `examples/**` PRESERVED)"
      pattern: "tools/arrconf-ui/\\*\\*"
    - from: ".github/workflows/tests.yml::arrconf-ui-backend"
      to: "tools/arrconf-ui/pyproject.toml"
      via: "working-directory: tools/arrconf-ui + setup-uv + uv sync"
      pattern: "working-directory: tools/arrconf-ui$"
    - from: ".github/workflows/tests.yml::arrconf-ui-frontend"
      to: "tools/arrconf-ui/web/package.json"
      via: "working-directory: tools/arrconf-ui/web + setup-node@v6 + npm ci"
      pattern: "working-directory: tools/arrconf-ui/web"
    - from: ".github/workflows/chart-lint.yml"
      to: "(unchanged)"
      via: "Phase 17 commits MUST NOT touch this file (D-17-NO-CHART-LINT-CHANGE)"
      pattern: "tools/arrconf-ui"  # MUST NOT appear in chart-lint.yml
---

<objective>
Extend `.github/workflows/tests.yml` with 2 new jobs (`arrconf-ui-backend` Python triad + pytest, `arrconf-ui-frontend` Svelte quad) so that any PR touching `tools/arrconf-ui/**` is gated by the same quality bar as `tools/arrconf/**`. `.github/workflows/chart-lint.yml` is preserved intact — this architectural separation IS what guarantees SC#3 (UI-only PRs do not trigger the auto-tag step).

Purpose: Pay the v0.4.0 CI dette (arrconf-ui was outside the path-filter since it shipped in Phase 15) without changing chart release behavior. Phase 17 is CI-only — no `tools/arrconf/**` change → no arrconf image rebuild → no `charts/arr-stack/values.yaml#arrconf.image.tag` co-bump.

Output:
- `.github/workflows/tests.yml` extended (path-filter union + 2 new jobs).
- `README.md` CI matrix section updated.
- `.planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md` written with 4 scenarios.
- The Phase 17 PR itself demonstrates the 2 new jobs running green on the GitHub Checks tab (SC#4 self-validates).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/17-arrconf-ui-ci-coverage/17-CONTEXT.md
@CLAUDE.md
@.github/workflows/tests.yml
@.github/workflows/chart-lint.yml
@tools/arrconf-ui/pyproject.toml
@tools/arrconf-ui/web/package.json
@README.md

<interfaces>
<!-- Key contracts extracted from current artifacts — executor uses these directly, no exploration needed -->

From `.github/workflows/tests.yml` (current state — single `test` job, path-filter excludes `tools/arrconf-ui/**`):

```yaml
on:
  pull_request:
    paths:
      - 'tools/arrconf/**'
      - 'schemas/**'
      - 'examples/**'
      - '.github/workflows/tests.yml'
  push:
    branches: [main]
    paths:
      - 'tools/arrconf/**'
      - 'schemas/**'
      - 'examples/**'

jobs:
  test:
    runs-on: ubuntu-24.04
    permissions:
      contents: read
    defaults:
      run:
        working-directory: tools/arrconf
    steps:
      - uses: actions/checkout@v4
      - name: Setup uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "0.11.x"
          python-version: "3.13"
          enable-cache: true
      - name: Install dependencies
        run: uv sync --frozen
      - name: Lint (ruff)
        run: uv run ruff check .
      - name: Format check (ruff)
        run: uv run ruff format --check .
      - name: Type check (mypy strict)
        run: uv run mypy arrconf
      - name: Run tests with coverage
        run: uv run pytest --cov --cov-report=term-missing --cov-fail-under=70
      # … 3 additional repo-root steps (schema reproducibility, fixture audit, baseline modeline)
```

From `tools/arrconf-ui/pyproject.toml`:
- Python 3.13 + uv + ruff (E/F/I/B/UP/N/D, ignore D203/D213) + mypy strict + pytest
- `[tool.uv.sources]` declares editable sibling `arrconf = { path = "../arrconf", editable = true }` — uv sync MUST find sibling checkout
- Dev group: pytest, pytest-cov, httpx, ruff, mypy
- Source layout: `arrconf_ui/` package (8-13 files) + `tests/` (32 tests)

From `tools/arrconf-ui/web/package.json`:
- Scripts: `dev`, `build` (vite), `preview`, `check` (svelte-check --tsconfig ./tsconfig.json), `typecheck` (tsc --noEmit)
- DevDeps: svelte ^5, svelte-check ^4, vite ^6, typescript ^5.6
- Lockfile: `tools/arrconf-ui/web/package-lock.json`

From `.github/workflows/chart-lint.yml` (PRESERVE INTACT per D-17-NO-CHART-LINT-CHANGE):
- Path-filter is `charts/**` + `tools/arrconf/**` + `examples/values-prod.yaml` + `.github/workflows/chart-lint.yml` + `.github/workflows/arrconf-image.yml` + `renovate.json` + `tools/scripts/**`
- `tools/arrconf-ui/**` is NOT in this filter and MUST stay that way — it is the architectural guarantee for SC#3.
- `tag` job uses `mathieudutour/github-tag-action@v6.2` — runs only on push to main when `lint` succeeds. Excluding `tools/arrconf-ui/**` from the path-filter means UI-only PRs never trigger this job → no auto-tag pollution.

Baseline verification (orchestrator pre-flight 2026-05-24):
- arrconf-ui Python triad: 13 files formatted ✓ / ruff check pass ✓ / mypy "no issues in 13 source files" ✓ / 32 tests pass ✓
- arrconf-ui frontend: `npm run check` 92 files 0 errors 0 warnings ✓ / `npm run typecheck` silent (success) ✓ / `npm run build` 866ms 0 errors ✓
- **No preexisting errors to fix** — Phase 17 wires CI around an already-clean baseline.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Baseline spot-check — confirm triad + frontend quad green locally</name>
  <read_first>
    - tools/arrconf-ui/pyproject.toml (confirms triad commands)
    - tools/arrconf-ui/web/package.json (confirms scripts: check, typecheck, build)
  </read_first>
  <files>(none — read-only verification)</files>
  <action>
    Before editing `tests.yml`, re-confirm the exact command sequence works locally so the workflow file mirrors what the executor knows passes. Run BOTH halves from a clean shell (`pwd` resets between Bash calls — use absolute paths).

    Backend (run from `/data/projets/perso/arr-stack/tools/arrconf-ui`):
    ```bash
    cd /data/projets/perso/arr-stack/tools/arrconf-ui && \
      uv sync --frozen && \
      uv run ruff format --check . && \
      uv run ruff check . && \
      uv run mypy . && \
      uv run pytest -q
    ```

    Frontend (run from `/data/projets/perso/arr-stack/tools/arrconf-ui/web`):
    ```bash
    cd /data/projets/perso/arr-stack/tools/arrconf-ui/web && \
      npm ci && \
      npm run check && \
      npm run typecheck && \
      npm run build
    ```

    Capture pass/fail per command. **If ANY command fails** (regression since orchestrator's 2026-05-24 baseline), STOP and surface to operator — do NOT proceed to Task 2. Phase 17 must NOT mask regressions by shipping a workflow that fails on first run; baseline must be clean.

    **Mypy invocation note:** the existing `test` job for arrconf calls `uv run mypy arrconf` (positional package argument). For arrconf-ui we use `uv run mypy .` because `pyproject.toml` already sets `strict = true` + `disallow_untyped_defs = true` and the project root is canonical (the package dir is `arrconf_ui/`, sibling `tests/`, `arrconf-ui` global config). Both conventions are valid; we deliberately mirror the developer-local triad documented in CLAUDE.md ("Triade Python") which uses `mypy .`.

    **Note on `uv sync --frozen` for arrconf-ui:** the sibling `arrconf` editable source dependency may require a `uv.lock` regen if it's drifted since 15-A. If `--frozen` fails on lockfile mismatch, fall back to `uv sync` (without `--frozen`) for the spot-check AND for the CI workflow — this is consistent with the editable-sibling pattern. Document the choice in the workflow step name.
  </action>
  <verify>
    <automated>cd /data/projets/perso/arr-stack/tools/arrconf-ui && uv sync && uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest -q && cd web && npm ci && npm run check && npm run typecheck && npm run build</automated>
  </verify>
  <acceptance_criteria>
    - All 5 backend commands exit 0 (uv sync, ruff format check, ruff check, mypy, pytest)
    - All 4 frontend commands exit 0 (npm ci, check, typecheck, build)
    - Decision recorded: `uv sync --frozen` viable OR fall back to `uv sync` documented for Task 2
  </acceptance_criteria>
  <done>
    Local baseline confirmed green. The exact command sequence to embed in `tests.yml` Task 2 is now known to work (or the fallback `uv sync` form is justified). Operator notified ONLY if regression discovered.
  </done>
</task>

<task type="auto">
  <name>Task 2: Extend `tests.yml` — path-filter union + 2 new jobs (backend + frontend)</name>
  <read_first>
    - .github/workflows/tests.yml (current state — extend, do NOT rewrite the existing `test` job)
    - tools/arrconf-ui/pyproject.toml (triad + pytest config)
    - tools/arrconf-ui/web/package.json (scripts: check, typecheck, build)
  </read_first>
  <files>.github/workflows/tests.yml</files>
  <action>
    Edit `.github/workflows/tests.yml` to add path-filter entries and 2 new jobs. **PRESERVE the existing `test` job verbatim** — do NOT touch its steps, only the top-level `on.*.paths` lists and the `jobs:` block (extension).

    **Step 2.1 — Extend path-filters (D-17-WORKFLOW-01):**

    In `on.pull_request.paths`, ADD line:
    ```yaml
          - 'tools/arrconf-ui/**'
    ```

    In `on.push.paths`, ADD line:
    ```yaml
          - 'tools/arrconf-ui/**'
    ```

    Preserve all existing entries (`tools/arrconf/**`, `schemas/**`, `examples/**`, `.github/workflows/tests.yml`). Order: place `tools/arrconf-ui/**` immediately after `tools/arrconf/**` for grouping. Do NOT alphabetize the entire list — minimal diff.

    **Step 2.2 — Add `arrconf-ui-backend` job (D-17-COVERAGE-01: NO `--cov-fail-under`):**

    Append AFTER the existing `test` job (sibling at the same indentation under `jobs:`):

    ```yaml
      arrconf-ui-backend:
        runs-on: ubuntu-24.04
        permissions:
          contents: read
        defaults:
          run:
            working-directory: tools/arrconf-ui
        steps:
          - uses: actions/checkout@v4

          - name: Setup uv
            uses: astral-sh/setup-uv@v4
            with:
              version: "0.11.x"
              python-version: "3.13"
              enable-cache: true

          - name: Install dependencies (sibling arrconf editable via tool.uv.sources)
            run: uv sync

          - name: Format check (ruff)
            run: uv run ruff format --check .

          - name: Lint (ruff E/F/I/B/UP/N/D)
            run: uv run ruff check .

          - name: Type check (mypy strict)
            run: uv run mypy .

          - name: Run tests (no coverage threshold — D-17-COVERAGE-01)
            run: uv run pytest -q
    ```

    Notes on choices, per CONTEXT.md decisions:
    - `uv sync` WITHOUT `--frozen` — the editable sibling `arrconf` in `tool.uv.sources` makes `--frozen` brittle if arrconf's `pyproject.toml` shifts. Task 1 confirmed this works locally. If Task 1 demonstrated `--frozen` ALSO works, you MAY add it back — but `uv sync` plain is the safer default.
    - `mypy .` (not `mypy arrconf_ui`) mirrors CLAUDE.md "Triade Python" convention.
    - `pytest -q` WITHOUT `--cov-fail-under` per D-17-COVERAGE-01. Do NOT add `--cov` either — the dev group has `pytest-cov` but coverage reporting is not the goal here; just pass/fail.
    - Step names: deliberately use shorter prose than the `test` job for arrconf (no schema-gen, no fixture audit, no modeline check — those are arrconf-specific guards).

    **Step 2.3 — Add `arrconf-ui-frontend` job (D-17-FRONTEND-01: full quad ci+check+typecheck+build, D-17-NODE-01: hardcoded Node 22):**

    Append AFTER the `arrconf-ui-backend` job:

    ```yaml
      arrconf-ui-frontend:
        runs-on: ubuntu-24.04
        permissions:
          contents: read
        defaults:
          run:
            working-directory: tools/arrconf-ui/web
        steps:
          - uses: actions/checkout@v4

          - name: Setup Node 22 (LTS — D-17-NODE-01 hardcoded)
            uses: actions/setup-node@v6
            with:
              node-version: '22'
              cache: 'npm'
              cache-dependency-path: tools/arrconf-ui/web/package-lock.json

          - name: Install dependencies (npm ci — deterministic from lockfile)
            run: npm ci

          - name: Svelte check (svelte-check + TS for .svelte files)
            run: npm run check

          - name: TS check (tsc --noEmit — covers pure .ts files outside .svelte)
            run: npm run typecheck

          - name: Build (Vite — confirms bundle compiles)
            run: npm run build
    ```

    Notes:
    - `actions/setup-node@v6` (NOT @v4 like `chart-lint.yml` uses — Phase 17 newer pin, decision-of-record D-17-NODE-01). The cache parameter syntax with `cache-dependency-path` is standard for sub-folder lockfiles.
    - All 4 commands per D-17-FRONTEND-01 — including `typecheck` for pure `.ts` files (`i18n/fr.ts`, `theme.ts`, etc.) that svelte-check doesn't cover.
    - No `permissions:` upgrade beyond `contents: read` — frontend build is a sandbox, no need for `id-token` or `packages:`.

    **Step 2.4 — Validate YAML syntax** locally before commit:
    ```bash
    python3 -c "import yaml; yaml.safe_load(open('/data/projets/perso/arr-stack/.github/workflows/tests.yml'))" && echo OK
    ```
    If `actionlint` is installed (`which actionlint`), additionally run:
    ```bash
    actionlint /data/projets/perso/arr-stack/.github/workflows/tests.yml
    ```
    Optional — graceful skip if not installed. Do NOT require operator to install actionlint just for this.

    **Self-invalidating-grep gate caution:** when verifying with grep, this PLAN.md itself contains the strings `tools/arrconf-ui/**` and `arrconf-ui-backend` as quoted snippets — do NOT grep the planning tree, ONLY `.github/workflows/tests.yml`.
  </action>
  <verify>
    <automated>python3 -c "import yaml; yaml.safe_load(open('/data/projets/perso/arr-stack/.github/workflows/tests.yml'))" && grep -c 'tools/arrconf-ui/\*\*' /data/projets/perso/arr-stack/.github/workflows/tests.yml | grep -qE '^2$' && grep -q '^  arrconf-ui-backend:$' /data/projets/perso/arr-stack/.github/workflows/tests.yml && grep -q '^  arrconf-ui-frontend:$' /data/projets/perso/arr-stack/.github/workflows/tests.yml && grep -q "node-version: '22'" /data/projets/perso/arr-stack/.github/workflows/tests.yml && ! grep -q 'cov-fail-under' <(awk '/^  arrconf-ui-backend:/,/^  [a-z]/' /data/projets/perso/arr-stack/.github/workflows/tests.yml) && echo "tests.yml OK"</automated>
  </verify>
  <acceptance_criteria>
    - `.github/workflows/tests.yml` parses as valid YAML
    - `grep -c 'tools/arrconf-ui/\*\*' .github/workflows/tests.yml` returns **exactly 2** (one in `pull_request.paths`, one in `push.paths`)
    - `grep -E '^  arrconf-ui-backend:$' .github/workflows/tests.yml` matches (job header at canonical indent)
    - `grep -E '^  arrconf-ui-frontend:$' .github/workflows/tests.yml` matches
    - `grep "node-version: '22'" .github/workflows/tests.yml` matches (D-17-NODE-01)
    - Within the `arrconf-ui-backend` job block (between its header and the next sibling job), NO line contains `cov-fail-under` (D-17-COVERAGE-01)
    - Within the `arrconf-ui-frontend` job block, all 4 commands present: `npm ci`, `npm run check`, `npm run typecheck`, `npm run build`
    - Existing `test` job body BIT-PERFECT preserved (compare with `git diff` — only `on.*.paths` adds 2 lines, jobs block adds 2 new top-level keys, `test:` block unchanged)
    - `actions/setup-node@v6` present (not @v4)
    - `cache: 'npm'` + `cache-dependency-path: tools/arrconf-ui/web/package-lock.json` both present in frontend job
  </acceptance_criteria>
  <done>
    `tests.yml` has the 2 new jobs plus extended path-filter, YAML is valid, existing `test` job is untouched, all D-17 decisions encoded (D-17-WORKFLOW-01 single workflow file, D-17-FRONTEND-01 quad commands, D-17-COVERAGE-01 no threshold, D-17-NODE-01 Node 22 hardcoded).
  </done>
</task>

<task type="auto">
  <name>Task 3: Update README.md — document the 3 jobs in `tests.yml` + path-filter triggers</name>
  <read_first>
    - README.md (focus: line 138 "CI" row in Stack technique table; also the "Mise à jour d'image" flow at line 195+ which mentions `tests.yml`)
  </read_first>
  <files>README.md</files>
  <action>
    Update README.md to document the new CI matrix. Two options — pick whichever creates the smallest, cleanest diff:

    **Option A (preferred — extend existing Stack technique row):**

    Find line ~138:
    ```
    | CI | GitHub Actions | — | `chart-lint.yml` + `arrconf-image.yml` + `tests.yml` |
    ```

    Replace with:
    ```
    | CI | GitHub Actions | — | `chart-lint.yml` (chart + arrconf code) + `arrconf-image.yml` (GHCR build) + `tests.yml` (3 jobs: `test` arrconf, `arrconf-ui-backend`, `arrconf-ui-frontend`) |
    ```

    THEN add a short subsection AFTER the "Stack technique" table (around line 145, before `## Déploiement`):

    ```markdown
    ### CI matrix

    Two workflows gate PRs at different scopes:

    | Workflow | Trigger paths | Jobs | Auto-tag on push to main? |
    |----------|---------------|------|----------------------------|
    | `chart-lint.yml` | `charts/**`, `tools/arrconf/**`, `examples/values-prod.yaml`, `renovate.json`, `tools/scripts/**`, workflow self-edits | `lint` (helm + kubeconform + guards), `tag` (mathieudutour/github-tag-action) | **Yes** — patch bump on every push-to-main passing `lint` |
    | `tests.yml` | `tools/arrconf/**`, `tools/arrconf-ui/**`, `schemas/**`, `examples/**`, workflow self-edits | `test` (arrconf — uv triad + pytest --cov-fail-under=70 + schema/fixture/modeline guards), `arrconf-ui-backend` (arrconf-ui — uv triad + pytest -q), `arrconf-ui-frontend` (Svelte — npm ci + check + typecheck + build) | No |

    **Architectural separation:** `chart-lint.yml` triggers the auto-tag chain (which Renovate-on-my-kluster picks up to bump `targetRevision`). `tests.yml` is gates-only — no tag side-effects. A PR touching ONLY `tools/arrconf-ui/**` runs `tests.yml` (both UI jobs) but does NOT trigger `chart-lint.yml` → no spurious version bump for UI-only changes. See [`CLAUDE.md`](./CLAUDE.md) "Release pin co-bump pattern" for the chart-pin discipline.
    ```

    **Option B (alternative — only edit Stack technique row, skip CI matrix subsection):**

    If the README is getting too long, JUST update the existing row at line 138 to mention the 3 jobs. No new subsection. This is acceptable if Option A creates too much noise.

    **Pick Option A** as the default (better operator onboarding). Use Option B only if you find the README has already become unwieldy in subsequent edits.

    Do NOT touch other sections of README.md. Do NOT add emojis. Do NOT rewrite the existing "Local config UI" section.

    Optional bonus: in the "Local config UI" section around line 50-75 (specifically the "Dev mode" or "Building the static bundle" subsection), append ONE sentence noting that `npm run check && npm run typecheck && npm run build` mirrors what CI runs on PR. This is a tiny developer-quality-of-life note. Skip if it adds friction.
  </action>
  <verify>
    <automated>grep -q 'arrconf-ui-frontend' /data/projets/perso/arr-stack/README.md && grep -q 'arrconf-ui-backend' /data/projets/perso/arr-stack/README.md && grep -q 'tests.yml' /data/projets/perso/arr-stack/README.md</automated>
  </verify>
  <acceptance_criteria>
    - README.md contains the strings `arrconf-ui-backend` AND `arrconf-ui-frontend`
    - README.md mentions the 3-job structure of `tests.yml`
    - README.md still contains the existing "Local config UI" section verbatim (no accidental rewrites)
    - README.md has no broken markdown tables (manual eyeball OR `grep -E '^\|.*\|.*\|$' README.md | wc -l` for table sanity)
    - No emoji added (project convention)
  </acceptance_criteria>
  <done>
    README.md documents the new CI matrix. Operator reading README sees the 3 jobs + their path-filter triggers + the architectural separation note (chart-lint = auto-tag chain, tests.yml = gates-only).
  </done>
</task>

<task type="auto">
  <name>Task 4: Write `17-HUMAN-UAT.md` — 4 operator scenarios</name>
  <read_first>
    - .planning/phases/17-arrconf-ui-ci-coverage/17-CONTEXT.md (HUMAN-UAT Scenarios section)
    - .planning/phases/16-jellyfin-categories-as-libs/16-HUMAN-UAT.md (format reference — same milestone, same operator)
  </read_first>
  <files>.planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md</files>
  <action>
    Create `17-HUMAN-UAT.md` covering the 4 mandatory scenarios from the planning context. Mirror the format from `16-HUMAN-UAT.md` (same milestone v0.5.0, same operator).

    Structure:
    ```markdown
    # Phase 17 — arrconf-ui CI coverage — HUMAN-UAT

    **Phase:** 17
    **Date opened:** 2026-05-24
    **Status:** Pending operator close-out
    **Closes:** REQ-arrconf-ui-ci (SC#1, SC#2, SC#3, SC#4, SC#5 from ROADMAP)

    ## Pre-flight

    - [ ] Phase 17 PR opened on GitHub against `main`
    - [ ] PR description references this file
    - [ ] At least 1 commit on the PR touches `.github/workflows/tests.yml` (else the 2 new jobs won't run on this PR — they're path-filtered)

    ## Scenarios

    ### Scenario 1 (MANDATORY — SC#4) — Phase 17 PR shows new CI jobs green

    On the Phase 17 PR's "Checks" tab on GitHub:

    1. Locate the `tests` workflow run.
    2. Confirm 3 jobs listed: `test`, `arrconf-ui-backend`, `arrconf-ui-frontend`.
    3. Confirm `arrconf-ui-backend` is **green** (steps: Setup uv, Install dependencies, Format check, Lint, Type check, Run tests — all pass).
    4. Confirm `arrconf-ui-frontend` is **green** (steps: Setup Node 22, Install dependencies, Svelte check, TS check, Build — all pass).
    5. Confirm `test` (the existing arrconf job) is **green** (regression check — Phase 17 must not break the existing pipeline).

    ✅ All 3 jobs green → SC#4 met → scenario passes.

    ### Scenario 2 (MANDATORY — SC#3) — chart-lint.yml NOT triggered by UI-only commits after merge

    After Phase 17 PR is merged:

    1. Wait ~1 min for GitHub to register the merge.
    2. Run:
       ```bash
       gh run list --workflow=chart-lint.yml --branch main --limit 10 --json conclusion,headSha,event,createdAt
       ```
    3. Verify: the most recent runs of `chart-lint.yml` correspond to commits that touched `charts/**` or `tools/arrconf/**` (NOT the Phase 17 merge commit if Phase 17 only touched `.github/workflows/tests.yml` + README + .planning/**).
    4. **Edge case:** If Phase 17 PR itself touched `.github/workflows/tests.yml` (path-filter union edit), `chart-lint.yml` DOES include `.github/workflows/chart-lint.yml` in its filter — but we did NOT touch chart-lint.yml. The Phase 17 merge commit must therefore NOT show in `chart-lint.yml` runs (it only shows in `tests.yml` runs).
    5. Confirm via `git show <phase17-merge-sha> --stat`: no files under `charts/**`, `tools/arrconf/**`, `tools/scripts/**`, `examples/values-prod.yaml`, or `renovate.json` were touched.

    ✅ No `chart-lint.yml` run triggered by Phase 17 merge commit → SC#3 architecturally validated.

    ### Scenario 3 (MANDATORY — SC#5) — README CI matrix section reads cleanly

    1. Open the merged `README.md` on GitHub (https://github.com/tom333/arr-stack/blob/main/README.md).
    2. Locate the "CI matrix" subsection (or the updated row in the Stack technique table).
    3. Confirm the 3 jobs are mentioned by name: `test`, `arrconf-ui-backend`, `arrconf-ui-frontend`.
    4. Confirm the architectural-separation note (chart-lint = auto-tag chain, tests.yml = gates-only) is present.
    5. Markdown renders correctly (table not broken, no orphaned `|` chars).

    ✅ README clean → SC#5 met → scenario passes.

    ### Scenario 4 (OPTIONAL — follow-up validation) — Trivial UI-only PR exercises path-filter

    AFTER Phase 17 merges, open a throwaway PR that touches ONLY a comment or whitespace in `tools/arrconf-ui/web/src/App.svelte`:

    1. Branch from `main`:
       ```bash
       git checkout -b throwaway/test-phase17-pathfilter
       # Add a trivial change: e.g. echo "<!-- ci-test -->" >> tools/arrconf-ui/web/src/App.svelte
       git commit -am "test: trivial UI change for Phase 17 path-filter verification"
       git push -u origin throwaway/test-phase17-pathfilter
       gh pr create --title "test: phase 17 path-filter sanity" --body "Throwaway — close without merging."
       ```
    2. On the PR's Checks tab, confirm:
       - `tests` workflow runs → `arrconf-ui-frontend` is among its jobs → green or red (red is OK if the trivial change broke a check; the point is the **trigger** worked).
       - `chart-lint` workflow does NOT appear in the Checks tab → path-filter correctly excluded UI-only change.
    3. Close PR without merging (`gh pr close N`).
    4. Delete throwaway branch.

    ✅ Confirmed end-to-end. Can be skipped if Scenarios 1-3 already gave high confidence.

    ## Closure

    Once Scenarios 1-3 (mandatory) pass:
    - [ ] Append a closure note to `.planning/STATE.md` (Phase 17 closed, REQ-arrconf-ui-ci satisfied)
    - [ ] Update `.planning/ROADMAP.md` Phase 17 checkbox from `[ ]` to `[x]` with closure date
    - [ ] (Scenario 4 result optional) Note in STATE.md if executed

    ## Rollback

    If `arrconf-ui-backend` or `arrconf-ui-frontend` reveal real issues post-merge (not the workflow's fault, but a missed regression):
    1. Open a follow-up PR fixing the issue under `tools/arrconf-ui/**`.
    2. Phase 17 itself does NOT need rollback — the workflow file is correct; the code drift is what failed. Pull `git revert` only if `tests.yml` itself has a YAML parse error or jobs hang indefinitely (neither expected).
    ```

    Save to `.planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md`.
  </action>
  <verify>
    <automated>test -f /data/projets/perso/arr-stack/.planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md && grep -q 'Scenario 1' /data/projets/perso/arr-stack/.planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md && grep -q 'Scenario 2' /data/projets/perso/arr-stack/.planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md && grep -q 'Scenario 3' /data/projets/perso/arr-stack/.planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md && grep -q 'Scenario 4' /data/projets/perso/arr-stack/.planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md && grep -q 'SC#3' /data/projets/perso/arr-stack/.planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md</automated>
  </verify>
  <acceptance_criteria>
    - File exists at expected path
    - All 4 scenarios labeled (1, 2, 3, 4) with mandatory/optional flags
    - References to SC#3, SC#4, SC#5 from ROADMAP map cleanly to scenarios
    - Pre-flight checklist present
    - Closure section present (links to STATE.md + ROADMAP checkbox)
    - Rollback note present
  </acceptance_criteria>
  <done>
    Operator has a runbook to close Phase 17 post-merge. The 4 scenarios cover all 5 ROADMAP SCs (SC#1 + SC#2 → Scenario 1 ; SC#3 → Scenario 2 ; SC#4 → Scenario 1 ; SC#5 → Scenario 3 ; Scenario 4 is bonus end-to-end).
  </done>
</task>

<task type="auto">
  <name>Task 5: Guard — verify chart-lint.yml is bit-for-bit unchanged (D-17-NO-CHART-LINT-CHANGE)</name>
  <read_first>
    - .github/workflows/chart-lint.yml (current state — must match HEAD pre-Phase-17)
  </read_first>
  <files>(none — read-only invariant check)</files>
  <action>
    Before declaring the plan done, run a paranoid check that `.github/workflows/chart-lint.yml` is byte-identical to its state at the parent commit of the Phase 17 work. This is the architectural guarantee for SC#3 — if chart-lint.yml somehow got touched (e.g., editor auto-reformatted on save, indentation drift, trailing newline added), SC#3 is silently broken.

    Run from `/data/projets/perso/arr-stack`:
    ```bash
    # Find the commit BEFORE Phase 17 started (the merge of Phase 16 or the latest main pre-Phase-17)
    PHASE17_BASE_SHA=$(git log --format='%H' --diff-filter=A -- .planning/phases/17-arrconf-ui-ci-coverage/17-CONTEXT.md | tail -1)
    # That returns the commit that ADDED 17-CONTEXT.md. The parent of that is pre-Phase-17.
    BASELINE_SHA=$(git rev-parse "${PHASE17_BASE_SHA}^")
    echo "Comparing chart-lint.yml: ${BASELINE_SHA} (pre-Phase-17) → HEAD"
    git diff "${BASELINE_SHA}" HEAD -- .github/workflows/chart-lint.yml
    # Expected: ZERO output.
    ```

    If output is non-empty, **STOP** — the plan has accidentally touched chart-lint.yml. Either:
    1. Revert the file: `git checkout "${BASELINE_SHA}" -- .github/workflows/chart-lint.yml` and re-stage
    2. Surface to operator if the diff was intentional (e.g. you found a typo and fixed it) — but Phase 17 explicitly excludes this per D-17-NO-CHART-LINT-CHANGE; defer the fix to a separate PR.

    Also verify chart-lint.yml does NOT contain `tools/arrconf-ui` anywhere (path-filter must stay scoped):
    ```bash
    if grep -q 'tools/arrconf-ui' /data/projets/perso/arr-stack/.github/workflows/chart-lint.yml; then
      echo "ERROR: chart-lint.yml mentions tools/arrconf-ui — D-17-NO-CHART-LINT-CHANGE violated"
      exit 1
    fi
    echo "OK: chart-lint.yml does NOT reference tools/arrconf-ui"
    ```

    Note on the SHA-finding heuristic: if `git log --diff-filter=A` returns nothing (e.g. 17-CONTEXT.md was committed before Phase 17 work started, in a setup commit), fall back to comparing the workflow file against the file content known at the start of Phase 17 — operator can confirm interactively if needed. The grep guard (no `tools/arrconf-ui` string) is the more robust invariant and should always pass.
  </action>
  <verify>
    <automated>! grep -q 'tools/arrconf-ui' /data/projets/perso/arr-stack/.github/workflows/chart-lint.yml && echo "chart-lint.yml clean"</automated>
  </verify>
  <acceptance_criteria>
    - `git diff <pre-phase17-sha> HEAD -- .github/workflows/chart-lint.yml` produces NO output (preferred — strong invariant) OR
    - As a fallback: `chart-lint.yml` does NOT contain the string `tools/arrconf-ui` (architectural property — path-filter scope unchanged)
    - chart-lint.yml `on.push.paths` still contains exactly: `charts/**`, `tools/arrconf/**`, `examples/values-prod.yaml`, `.github/workflows/chart-lint.yml`, `.github/workflows/arrconf-image.yml`, `renovate.json`, `tools/scripts/**` — no additions or removals
    - chart-lint.yml `tag` job still uses `mathieudutour/github-tag-action@v6.2` (not bumped — Phase 17 ignores chart workflow entirely)
  </acceptance_criteria>
  <done>
    SC#3 architectural guarantee verified: `chart-lint.yml` is bit-for-bit unchanged, its path-filter does NOT include `tools/arrconf-ui/**`, the auto-tag chain is therefore inert for UI-only PRs by construction.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 6: Operator checkpoint — review local diff before PR</name>
  <what-built>
    - `.github/workflows/tests.yml` extended (path-filter + 2 new jobs: `arrconf-ui-backend`, `arrconf-ui-frontend`)
    - `README.md` CI matrix subsection added (or Stack technique row updated)
    - `.planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md` written (4 scenarios)
    - `.github/workflows/chart-lint.yml` confirmed bit-for-bit unchanged
    - No files under `tools/arrconf/**`, `tools/arrconf-ui/**`, `charts/**` touched
  </what-built>
  <how-to-verify>
    1. Inspect the diff:
       ```bash
       cd /data/projets/perso/arr-stack
       git status
       git diff --stat .github/workflows/tests.yml README.md
       git diff .github/workflows/tests.yml | head -120
       ```
       Expected files changed:
       - `.github/workflows/tests.yml` (~50-60 lines added — 2 path entries + 2 new jobs)
       - `README.md` (~10-30 lines depending on Option A vs B)
       - `.planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md` (new file, ~80 lines)

       Expected files NOT changed (anti-list — confirm absence):
       ```bash
       git status --porcelain | grep -E '^(M|A)\s+\.github/workflows/chart-lint\.yml' && echo "ERROR: chart-lint.yml modified — STOP" || echo "OK: chart-lint.yml clean"
       git status --porcelain | grep -E '^(M|A)\s+tools/arrconf/' && echo "ERROR: arrconf code touched — STOP" || echo "OK: arrconf code clean"
       git status --porcelain | grep -E '^(M|A)\s+tools/arrconf-ui/' && echo "ERROR: UI code touched — STOP" || echo "OK: UI code clean"
       git status --porcelain | grep -E '^(M|A)\s+charts/' && echo "ERROR: chart touched — STOP" || echo "OK: chart clean"
       ```

    2. YAML sanity:
       ```bash
       python3 -c "import yaml; cfg = yaml.safe_load(open('.github/workflows/tests.yml')); print('Jobs:', list(cfg['jobs'].keys()))"
       ```
       Expected output: `Jobs: ['test', 'arrconf-ui-backend', 'arrconf-ui-frontend']`

    3. README rendering: open `README.md` in your editor or `gh markdown render README.md | head -80` (if gh has the markdown extension) — confirm the CI matrix table renders cleanly.

    4. Open the `17-HUMAN-UAT.md`:
       ```bash
       cat .planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md | head -40
       ```
       Confirm Scenarios 1-4 listed, mandatory flags present.

    5. **Critical** — the chart-pin SHALL NOT bump. Confirm:
       ```bash
       git diff charts/arr-stack/values.yaml
       ```
       Expected: empty output (no diff).

    Once satisfied:
    - Confirm "approved" → executor proceeds to stage + commit + push + open PR
    - OR describe issues for revision

    Note: the actual GitHub Checks tab validation (SC#4, Scenarios 1-3 of HUMAN-UAT.md) happens AFTER the PR is opened, NOT in this checkpoint. This checkpoint is a pre-PR sanity gate only.
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Phase 17 commit → GitHub Actions runner | Workflow file change is interpreted by GitHub-hosted runners; tampering here could exfiltrate `secrets.GITHUB_TOKEN` |
| npm registry → CI runner | `npm ci` pulls Svelte/Vite/svelte-check tarballs from npmjs.com — supply-chain surface |
| uv → PyPI | `uv sync` pulls FastAPI/uvicorn/ruyaml/etc. — supply-chain surface (same as existing `test` job) |
| chart-lint.yml path-filter | Architectural guarantee: UI-only changes don't trigger auto-tag. Breakage means a spurious chart version → my-kluster Renovate PR → potentially deploys arrconf code that wasn't UI-related. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-17-01 | Tampering | `.github/workflows/tests.yml` | mitigate | `permissions: contents: read` on both new jobs (no write capability). No `secrets.*` referenced in the new jobs — they don't need GHCR push or anything similar. |
| T-17-02 | Spoofing | `actions/setup-uv@v4`, `actions/setup-node@v6`, `actions/checkout@v4` | accept | Standard GitHub Marketplace actions, version-pinned (not `@latest`). Same trust model as the existing `test` job for arrconf which uses identical setup-uv@v4 and checkout@v4. Renovate updates these via `helmv3`-equivalent for actions. |
| T-17-03 | Tampering | `tools/arrconf-ui/web/package-lock.json` | mitigate | `npm ci` is deterministic — refuses to run if lockfile drifts from package.json. Lock-step guard. |
| T-17-04 | Tampering | `tools/arrconf-ui/uv.lock` (if `--frozen` used) | accept | Phase 17 uses `uv sync` WITHOUT `--frozen` (Task 1 decision). Editable sibling `arrconf` makes `--frozen` brittle. Trade-off accepted: marginally less reproducibility for higher reliability on the sibling-editable pattern. The existing `test` job for arrconf DOES use `--frozen`, but that's a standalone package with no editable siblings. |
| T-17-05 | Repudiation | Auto-tag bypass | mitigate | D-17-NO-CHART-LINT-CHANGE — chart-lint.yml path-filter unchanged → UI-only changes can NEVER trigger auto-tag chain. Verified by Task 5 grep guard. |
| T-17-06 | Information Disclosure | Workflow logs | accept | New jobs only emit triad output (ruff/mypy/pytest/svelte-check/vite). No secret env vars referenced. Standard logging, no sensitive data. |
| T-17-07 | Denial of Service | Runner minutes | accept | 2 new jobs run in parallel with existing `test` job. Backend ~1 min, frontend <1 min. GitHub free-tier private repo: 2000 min/month — additional ~2 min per PR is negligible. |
| T-17-08 | Elevation of Privilege | `npm install -g` or similar | mitigate | NO global installs in either new job. `npm ci` is project-local; `uv sync` is project-local. Existing `chart-lint.yml` uses `npm install -g renovate@39` — Phase 17 does NOT touch that workflow. |
| T-17-09 | Tampering (process-level) | Cache poisoning via setup-uv/setup-node cache | accept | GitHub Actions cache is keyed on lockfile hash + OS + version. Poisoning would require lockfile tampering (T-17-03) which is itself mitigated. Cache miss is non-fatal — falls back to fresh download. |
</threat_model>

<verification>

## Post-execution verification (full phase check)

Run from `/data/projets/perso/arr-stack`:

```bash
# 1. tests.yml has 2 new jobs + path-filter union
python3 -c "
import yaml
cfg = yaml.safe_load(open('.github/workflows/tests.yml'))
jobs = list(cfg['jobs'].keys())
assert jobs == ['test', 'arrconf-ui-backend', 'arrconf-ui-frontend'], f'Wrong jobs: {jobs}'
pr_paths = cfg['on']['pull_request']['paths']
push_paths = cfg['on']['push']['paths']
assert 'tools/arrconf-ui/**' in pr_paths, 'Missing tools/arrconf-ui/** in pull_request.paths'
assert 'tools/arrconf-ui/**' in push_paths, 'Missing tools/arrconf-ui/** in push.paths'
print('OK: tests.yml structure valid')
"

# 2. chart-lint.yml UNCHANGED (no UI string anywhere)
! grep -q 'tools/arrconf-ui' .github/workflows/chart-lint.yml && echo "OK: chart-lint.yml does not reference UI"

# 3. README mentions the 3 jobs
grep -q 'arrconf-ui-backend' README.md && grep -q 'arrconf-ui-frontend' README.md && echo "OK: README updated"

# 4. HUMAN-UAT exists with 4 scenarios
test -f .planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md && \
  [ $(grep -c '^### Scenario' .planning/phases/17-arrconf-ui-ci-coverage/17-HUMAN-UAT.md) -ge 4 ] && \
  echo "OK: HUMAN-UAT has 4+ scenarios"

# 5. No chart-pin co-bump
[ -z "$(git diff charts/arr-stack/values.yaml)" ] && echo "OK: values.yaml unchanged (no co-bump)"

# 6. No application code touched
[ -z "$(git status --porcelain | grep -E '^(M|A)\s+tools/arrconf/')" ] && echo "OK: arrconf code not touched"
[ -z "$(git status --porcelain | grep -E '^(M|A)\s+tools/arrconf-ui/')" ] && echo "OK: arrconf-ui code not touched"
[ -z "$(git status --porcelain | grep -E '^(M|A)\s+charts/')" ] && echo "OK: chart not touched"

# 7. Local baseline (re-confirm before pushing)
cd tools/arrconf-ui && \
  uv sync && \
  uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest -q && \
  cd web && npm ci && npm run check && npm run typecheck && npm run build && \
  echo "OK: local baseline green"
```

</verification>

<success_criteria>

Phase 17 complete when:
- [ ] `.github/workflows/tests.yml` has 3 jobs (`test`, `arrconf-ui-backend`, `arrconf-ui-frontend`)
- [ ] `tools/arrconf-ui/**` appears in BOTH `on.pull_request.paths` AND `on.push.paths` (D-17-WORKFLOW-01)
- [ ] `arrconf-ui-backend` job runs the full triad + pytest WITHOUT `--cov-fail-under` (D-17-COVERAGE-01)
- [ ] `arrconf-ui-frontend` job runs all 4 commands: `npm ci`, `npm run check`, `npm run typecheck`, `npm run build` (D-17-FRONTEND-01)
- [ ] Frontend job uses `actions/setup-node@v6` with `node-version: '22'` hardcoded (D-17-NODE-01)
- [ ] `.github/workflows/chart-lint.yml` is bit-for-bit unchanged — `tools/arrconf-ui` does not appear anywhere in it (D-17-NO-CHART-LINT-CHANGE → architectural SC#3 guarantee)
- [ ] `README.md` documents the 3 jobs + their path-filter triggers + the architectural separation note
- [ ] `17-HUMAN-UAT.md` written with 4 scenarios covering ROADMAP SC#1-5
- [ ] No file under `tools/arrconf/**`, `tools/arrconf-ui/**`, or `charts/**` modified (CI-only — no chart-pin co-bump per ROADMAP SC#5)
- [ ] Local baseline (Python triad + frontend quad) confirmed green by Task 1 and re-verified by Task 6 checkpoint
- [ ] Operator approved the diff at Task 6 checkpoint before PR open
- [ ] After PR opened: Scenario 1 of HUMAN-UAT confirms the 2 new jobs run green on the PR's Checks tab (SC#4) — this is THE acceptance test that REQ-arrconf-ui-ci is satisfied

</success_criteria>

<output>
After completion, create `.planning/phases/17-arrconf-ui-ci-coverage/17-A-SUMMARY.md` per template:
- Files changed: tests.yml + README.md + 17-HUMAN-UAT.md (3 files total)
- Files explicitly preserved: chart-lint.yml + all code dirs
- Local verify steps re-run + result
- Operator checkpoint outcome
- Next step: open PR + observe Checks tab → run HUMAN-UAT Scenarios 1-3
</output>
