---
phase: 11-operational-polish-bundle
plan: A
type: execute
wave: 1
depends_on: []
files_modified:
  - .pre-commit-config.yaml
  - CLAUDE.md
  - tools/snapshot/snapshot.sh
  - tools/snapshot/README.md
  - README.md
autonomous: true
requirements:
  - REQ-ruff-format-ci-gate
  - REQ-paths-filter-arrconf
  - REQ-snapshot-redaction-harden
  - REQ-readme-onboarding-v030

must_haves:
  truths:
    - "A pre-commit hook config exists at repo root pinning ruff + ruff-format from astral-sh/ruff-pre-commit; running `pre-commit run --all-files` finishes 0 on a clean tree."
    - "chart-lint.yml's push+pull_request `paths:` filter includes `tools/arrconf/**`, so a commit that touches only arrconf code (no charts/ change) triggers the lint+tag chain."
    - "tools/snapshot/snapshot.sh applies an inline jq redaction step (apiKey/password/token/webhookUrl/sessionKey case-insensitive) to all *.json files in OUT_DIR before exit; a fresh snapshot's anti-leak grep returns 0 hits without manual post-edit."
    - "tools/snapshot/README.md notes redaction is now baked-in by default and points to the canonical jq expression for forensic re-redaction."
    - "README.md has no stale v0.2.0 references that contradict the v0.3.0 reality (`8 apps + configarr-cache PVC` and `Rollback post-Phase 4` are clarified or removed); the existing Onboarding < 30 min checklist remains accurate after a cold re-read."
    - "CLAUDE.md 'Conventions développement — arrconf' explicitly lists the Python triade `uv run ruff format --check . && uv run ruff check . && uv run mypy .` and points to .pre-commit-config.yaml for local enforcement."
  artifacts:
    - path: ".pre-commit-config.yaml"
      provides: "Pre-commit hook config (ruff + ruff-format)"
      contains: "astral-sh/ruff-pre-commit"
    - path: ".github/workflows/chart-lint.yml"
      provides: "Auto-tag chain trigger on arrconf-only commits"
      contains: "tools/arrconf/**"
    - path: "tools/snapshot/snapshot.sh"
      provides: "Inline redaction loop"
      contains: "JQ_REDACT"
    - path: "tools/snapshot/README.md"
      provides: "Doc note: redaction now baked-in"
      contains: "redaction now baked-in"
    - path: "CLAUDE.md"
      provides: "Python triade gate doc + .pre-commit-config.yaml pointer"
      contains: "ruff format --check"
    - path: "README.md"
      provides: "v0.3.0-faithful onboarding entry"
      min_lines: 180
  key_links:
    - from: ".pre-commit-config.yaml"
      to: "astral-sh/ruff-pre-commit@v0.6.x"
      via: "repos[].repo URL pin"
      pattern: "github.com/astral-sh/ruff-pre-commit"
    - from: "tools/snapshot/snapshot.sh"
      to: "OUT_DIR/*/*.json"
      via: "for-loop with jq --sort-keys + mv -f"
      pattern: "jq --sort-keys.*JQ_REDACT.*mv -f"
    - from: ".github/workflows/chart-lint.yml"
      to: "tag job (mathieudutour/github-tag-action)"
      via: "push.paths filter must include tools/arrconf/**"
      pattern: "tools/arrconf/\\*\\*"
---

<objective>
Close the four arr-stack-repo carry-forward operational items from v0.2.0 in a single autonomous plan:

1. **REQ-ruff-format-ci-gate** — add `.pre-commit-config.yaml` (CI already has `ruff format --check`; double-down with a local belt-and-suspenders hook) + extend CLAUDE.md doc.
2. **REQ-paths-filter-arrconf** — extend `.github/workflows/chart-lint.yml`'s `paths:` filter to include `tools/arrconf/**` so arrconf-only commits trigger the auto-tag chain (closes Phase 5.1 F1 / D-07-CRONJOB drift).
3. **REQ-snapshot-redaction-harden** — bake the existing manual Option A jq redaction loop from `tools/snapshot/README.md` into `snapshot.sh` itself; document in README.md note + preserve manual recipe as fallback.
4. **REQ-readme-onboarding-v030** — soft validation: re-read README.md cold, spot-fix 2 known stale Phase-4-era lines (PVC line 79 + Rollback line 164), keep the rest (Phase 10 commit cb25640 already refreshed the bulk).

Purpose: clear the 4 arr-stack-repo items in the v0.3.0 closeout polish bundle without touching `tools/arrconf/**` (so D-05 chart-pin co-bump does NOT fire on this commit — see CLAUDE.md "Release pin co-bump pattern" + D-11-CONTEXT.md).
Output: one commit (or sequence of small commits) bumping the 5 files listed in `files_modified`, no `charts/arr-stack/values.yaml` change.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/11-operational-polish-bundle/11-CONTEXT.md
@CLAUDE.md
@README.md
@tools/snapshot/snapshot.sh
@tools/snapshot/README.md
@.github/workflows/tests.yml
@.github/workflows/chart-lint.yml

<interfaces>
<!-- Key existing patterns. Executor uses these verbatim — no exploration needed. -->

From `.github/workflows/tests.yml` (lines 38-42, CONFIRMED already present in repo as of 2026-05-21):
```yaml
- name: Lint (ruff)
  run: uv run ruff check .

- name: Format check (ruff)
  run: uv run ruff format --check .
```
**NOTE:** The CI ruff-format gate is ALREADY in `tests.yml` (commit ef7681a, Phase 5). REQ-ruff-format-ci-gate's CI half is DONE. This plan adds the missing local belt: `.pre-commit-config.yaml`.

From `tools/snapshot/README.md` § "Audit anti-leak Option A" (lines 162-166):
```bash
JQ_REDACT='walk(if type == "object" then with_entries(if (.key | test("(?i)apiKey|password|token|webhookUrl|sessionKey")) and .value != null and .value != "" then .value = "<redacted>" else . end) else . end)'
for f in snapshots/baseline-2026-05-07/*/*.json; do
  jq --sort-keys "$JQ_REDACT" "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done
```
**MUST use `mv -f`** (not bare `mv`) when copy-pasting into snapshot.sh — Phase 10 lesson recorded in STATE.md "Phase 02.2 P06 RECOVERY" (interactive mv alias prompts → silent redaction failure).

From `tools/snapshot/snapshot.sh` (lines 396-406, final report section — redaction loop goes BEFORE this final report):
```bash
local_ok=$((TOTAL_APPS - FAILED_APPS))
log "snapshot complete : ${local_ok}/${TOTAL_APPS} app(s) OK, ${FAILED_APPS} with warnings"
log "output: ${OUTPUT_DIR}"
log ""
log "next: review for secret leaks before commit (see tools/snapshot/README.md § 'Audit anti-leak')"
exit 0
```

From `.github/workflows/chart-lint.yml` (lines 1-21, push/PR paths block):
```yaml
on:
  push:
    branches: [main]
    paths:
      - "charts/**"
      - "examples/values-prod.yaml"
      - ".github/workflows/chart-lint.yml"
      - ".github/workflows/arrconf-image.yml"
      - "renovate.json"
      - "tools/scripts/**"
  pull_request:
    paths:
      # ... same list ...
```
Need to inject `"tools/arrconf/**"` into BOTH the `push.paths` and `pull_request.paths` lists.

From `README.md` lines 78-79 and 164 (the 2 stale Phase-4-era references to fix):
```
Line 79: - PVCs existants pour les 8 apps + `configarr-cache` (déjà présents si migration depuis l'état pré-Phase 4)
Line 164: ### Rollback du cutover (si regression post-Phase 4)
```
Action: keep line 79 (it's still accurate — 8 media apps + configarr-cache PVC). Update line 164 to neutral wording ("Rollback umbrella → 10 individual ArgoCD Apps" — no temporal "post-Phase 4" since Phase 4 shipped 2026-05 and we're at v0.3.0 now).

From `CLAUDE.md` line 108:
```
- **`ruff check` et `ruff format`** doivent passer avant commit. CI bloque sinon.
```
Already present. Extend to explicitly mention the triade + `.pre-commit-config.yaml` (1-2 lines).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add .pre-commit-config.yaml + CLAUDE.md doc</name>
  <files>.pre-commit-config.yaml, CLAUDE.md</files>
  <read_first>
    - `tools/arrconf/pyproject.toml` to confirm ruff version range expected
    - `CLAUDE.md` § "Conventions développement — arrconf" (lines 105-115)
    - `.planning/phases/11-operational-polish-bundle/11-CONTEXT.md` § Specific Ideas (the pre-commit YAML snippet)
  </read_first>
  <action>
    Create `.pre-commit-config.yaml` at repo root with the astral-sh/ruff-pre-commit hooks pinned to the latest stable rev (planner notes: at time of writing, `v0.6.x` is the right window — verify against `tools/arrconf/pyproject.toml`'s ruff dep range and pin to a matching ruff-pre-commit rev; if the project pins ruff 0.6.x in pyproject, use `rev: v0.6.9` or the most recent v0.6.x tag). Two hooks: `id: ruff` with `args: [--fix]` and `id: ruff-format`. Add a top-level `files: ^tools/arrconf/` pattern so the hooks only run against arrconf Python sources (mirrors the CI scope).

    Then extend `CLAUDE.md` § "Conventions développement — arrconf" to add 2 lines under the existing line 108 bullet:
    - Add the explicit triade command: `uv run ruff format --check . && uv run ruff check . && uv run mypy .` (this is the EXACT command the gsd-executor should run before declaring a Python edit complete — closes D-07-RUFF-FORMAT-CI per CONTEXT.md D-11-RUFF-GATE).
    - Add a 1-line pointer: "Local enforcement via `pre-commit install` (uses repo-root `.pre-commit-config.yaml`)."

    No bump to `charts/arr-stack/values.yaml` — this commit does NOT touch `tools/arrconf/**` (D-05 exception per CLAUDE.md "Release pin co-bump pattern").
  </action>
  <verify>
    <automated>test -f .pre-commit-config.yaml && grep -c 'astral-sh/ruff-pre-commit' .pre-commit-config.yaml | grep -q '^[1-9]' && grep -c 'id: ruff-format' .pre-commit-config.yaml | grep -q '^[1-9]' && grep -c 'uv run ruff format --check' CLAUDE.md | grep -q '^[1-9]'</automated>
  </verify>
  <done>
    - `.pre-commit-config.yaml` exists at repo root.
    - File contains exactly one repo entry pointing to `https://github.com/astral-sh/ruff-pre-commit` with a v0.6.x rev pin.
    - Both hooks `id: ruff` (with `args: [--fix]`) and `id: ruff-format` are declared.
    - CLAUDE.md "Conventions développement — arrconf" now contains the explicit triade command line + the .pre-commit-config.yaml pointer.
    - No change to `charts/arr-stack/values.yaml` in the diff (verify with `git diff --stat charts/arr-stack/values.yaml` → empty).
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Extend chart-lint.yml paths filter to include tools/arrconf/**</name>
  <files>.github/workflows/chart-lint.yml</files>
  <read_first>
    - `.github/workflows/chart-lint.yml` (lines 1-21, the on.push.paths + on.pull_request.paths block)
    - `.planning/phases/11-operational-polish-bundle/11-CONTEXT.md` § Specific Ideas (chart-lint.yml paths filter snippet)
    - STATE.md "Phase 5 deviations + follow-ups" item #7 (this REQ's origin)
  </read_first>
  <action>
    Edit `.github/workflows/chart-lint.yml` to add `"tools/arrconf/**"` to BOTH the `on.push.paths` and `on.pull_request.paths` lists. Place it right after `"charts/**"` in each list so the diff is minimal and the intent is clear (chart-or-reconciler-code triggers the chain).

    Exact diff shape:
    ```yaml
    on:
      push:
        branches: [main]
        paths:
          - "charts/**"
          - "tools/arrconf/**"          # NEW — REQ-paths-filter-arrconf / Phase 5.1 F1
          - "examples/values-prod.yaml"
          # ... rest unchanged ...
      pull_request:
        paths:
          - "charts/**"
          - "tools/arrconf/**"          # NEW — REQ-paths-filter-arrconf / Phase 5.1 F1
          - "examples/values-prod.yaml"
          # ... rest unchanged ...
    ```

    No bump to `charts/arr-stack/values.yaml` — this commit does NOT touch `tools/arrconf/**` source code (D-05 exception per CLAUDE.md). The CI workflow itself is meta-config, not arrconf code.

    **Implication for SC#4 UAT:** after this task lands, the verification trigger ("commit touching only `tools/arrconf/**` triggers auto-tag") works. Plan 11-B-03 (Renovate App install) depends on this being merged FIRST for its SC#4 UAT to be testable — note this dependency in Plan 11-B-03's action block.
  </action>
  <verify>
    <automated>grep -c 'tools/arrconf/\*\*' .github/workflows/chart-lint.yml | grep -q '^[2-9]$\|^[1-9][0-9]\+'</automated>
  </verify>
  <done>
    - `.github/workflows/chart-lint.yml` has `"tools/arrconf/**"` in BOTH the `on.push.paths` list and `on.pull_request.paths` list (grep count ≥ 2).
    - `helm lint` and `kubeconform` steps below are unchanged.
    - `tag` job (mathieudutour/github-tag-action) trigger condition unchanged (still gated on `github.event_name == 'push' && github.ref == 'refs/heads/main'`).
    - No change to `charts/arr-stack/values.yaml`.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Bake inline redaction into tools/snapshot/snapshot.sh + README note</name>
  <files>tools/snapshot/snapshot.sh, tools/snapshot/README.md</files>
  <read_first>
    - `tools/snapshot/snapshot.sh` (lines 360-407, the final loop + report section)
    - `tools/snapshot/README.md` § "Audit anti-leak (CRITIQUE...)" (lines 138-172)
    - `.planning/phases/11-operational-polish-bundle/11-CONTEXT.md` § Specific Ideas (snapshot.sh redaction step snippet — EXACT verbatim copy)
    - STATE.md "Phase 02.2 P06 RECOVERY" (the `mv -f` gotcha — must use `-f` flag)
  </read_first>
  <action>
    Edit `tools/snapshot/snapshot.sh` to insert the redaction loop just BEFORE the final report block (between the `for app in "${TARGET_APPS[@]}"` loop closing `done` at line ~392 and the `# ─── Final report ───` line at ~394). The exact snippet to insert (verbatim from CONTEXT.md):

    ```bash
    # ─── REQ-snapshot-redaction-harden ────────────────────────────────────────
    if (( ! DRY_RUN )); then
      JQ_REDACT='walk(if type == "object" then with_entries(
        if (.key | test("(?i)apiKey|password|token|webhookUrl|sessionKey"))
           and .value != null and .value != ""
        then .value = "<redacted>"
        else . end) else . end)'

      shopt -s nullglob
      for f in "${OUTPUT_DIR}"/*/*.json; do
        if jq --sort-keys "$JQ_REDACT" "$f" > "${f}.tmp" 2>/dev/null; then
          mv -f "${f}.tmp" "$f"
        else
          rm -f "${f}.tmp"
          warn "  ✗ redaction skipped (invalid JSON?): $f"
        fi
      done
      shopt -u nullglob
      log "  ✓ redaction applied (apiKey/password/token/webhookUrl/sessionKey → <redacted>)"
    fi
    ```

    Notes for the executor:
    - Variable name is `OUTPUT_DIR` in snapshot.sh (not `OUT_DIR`) — CONTEXT.md snippet used the wrong name; correct it to `OUTPUT_DIR` (line 87 of snapshot.sh).
    - The variable is global (top-level script scope), so do NOT use `local` keyword (only valid inside functions). The CONTEXT.md snippet says `local JQ_REDACT=...` — that's a typo: drop `local`.
    - `shopt -s nullglob` guards against the case where no `.json` files were produced (e.g., all 6 apps failed) — without it, the loop body runs once on the literal pattern.
    - Use `mv -f` (NOT bare `mv`). Phase 02.2 P06 lesson: interactive `mv` alias prompts confirmation and the redaction silently fails.
    - Place BEFORE the final report block so the report log lines still come last in stdout.

    Then edit `tools/snapshot/README.md` § "Audit anti-leak (CRITIQUE...)" to add a 2-line note at the TOP of that section:
    ```markdown
    > **Note (v0.3.0+)** : la redaction Option A est désormais appliquée AUTOMATIQUEMENT par `snapshot.sh` à la fin de chaque run (sauf en `--dry-run`). Le script ci-dessous reste documenté comme recette manuelle pour les snapshots forensic / re-redaction d'un snapshot existant.
    ```
    Keep the existing Option A / Option B / Option C explanations intact below — they remain useful for manual re-redaction.

    No bump to `charts/arr-stack/values.yaml` — `tools/snapshot/**` is OUT of `tools/arrconf/**` scope (D-05 exception confirmed).

    **Verification step (operator side-only, documented in done):** the redaction CANNOT be unit-tested in this repo (no bash test framework — see CONTEXT.md "Claude's Discretion"). The dispositive test is: operator runs `snapshot.sh` against a live cluster, then runs the anti-leak grep. Document this in the done section.
  </action>
  <verify>
    <automated>grep -c 'JQ_REDACT' tools/snapshot/snapshot.sh | grep -q '^[2-9]$\|^[1-9][0-9]\+' && grep -c 'mv -f' tools/snapshot/snapshot.sh | grep -q '^[1-9]' && bash -n tools/snapshot/snapshot.sh && grep -c 'redaction est désormais appliquée AUTOMATIQUEMENT\|redaction now baked-in' tools/snapshot/README.md | grep -q '^[1-9]'</automated>
  </verify>
  <done>
    - `tools/snapshot/snapshot.sh` contains the redaction block with `JQ_REDACT` variable, the `for f in "${OUTPUT_DIR}"/*/*.json` loop, AND `mv -f` (not bare `mv`).
    - `bash -n tools/snapshot/snapshot.sh` (syntax check) exits 0.
    - The redaction block is positioned BEFORE the final report (`log "snapshot complete..."`).
    - `--dry-run` gate is present so the redaction is skipped in dry-run mode (no fake .tmp files created).
    - `tools/snapshot/README.md` § "Audit anti-leak" leads with the 2-line note about automatic redaction.
    - **Operator-side acceptance criterion** (Phase 11 verifier captures evidence, NOT this task): a fresh `snapshot.sh` run + `grep -rEH '"(apiKey|password|token|webhookUrl|sessionKey)"\s*:\s*"[^<"]{8,}"' snapshots/<fresh>/ | grep -v '"<redacted>"' | wc -l` returns `0`. Document the expected evidence path in the SUMMARY (`evidence/snapshot-redaction-uat-<date>.log`).
    - No change to `charts/arr-stack/values.yaml`.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 4: README.md cold re-read + spot-fix 2 stale references</name>
  <files>README.md</files>
  <read_first>
    - `README.md` from the top, cold (do NOT search for known-stale lines — read the whole file as a fresh operator would)
    - `.planning/phases/11-operational-polish-bundle/11-CONTEXT.md` § decisions § Claude's Discretion ("README onboarding validation = self-validation by the operator")
    - `.planning/ROADMAP.md` Phase 11 SC#5 ("fresh operator following README.md ... completes a successful arrconf diff in < 30 min")
    - Prior refresh commit `cb25640` (Phase 10 follow-up) — confirm what was already updated to avoid re-doing work
  </read_first>
  <action>
    1. Read `README.md` in full ONCE, cold. Note every claim that is stale relative to the 2026-05-21 reality (v0.3.0 shipped, Phase 10 closed, Phase 11 in progress).

    2. Specifically inspect the 2 KNOWN-STALE references identified during planning:
       - **Line 79**: `- PVCs existants pour les 8 apps + \`configarr-cache\` (déjà présents si migration depuis l'état pré-Phase 4)`. Decision: KEEP the substance (8 media apps + configarr-cache PVC is still accurate) but soften the temporal anchor — change "(déjà présents si migration depuis l'état pré-Phase 4)" to "(provisionnés au premier sync ArgoCD ; persistent storage `Retain` policy assure leur survie cross-cutover)". Removes the Phase-4-specific framing without losing information.
       - **Line 164**: `### Rollback du cutover (si regression post-Phase 4)`. Decision: rename to `### Rollback umbrella → ArgoCD Apps individuelles (si regression majeure)`. Drops the temporal "post-Phase 4" anchor; the rollback procedure remains valid going forward.

    3. After fixing these 2 lines, re-read the full README.md ONCE MORE cold. If any OTHER stale references are spotted (e.g., "8 apps" used where "6-app reconciler coverage" would be correct, references to "Phase X" as a future event when it shipped, references to v0.2.x as current when v0.3.0 is shipped), spot-fix them inline. Keep the diff small — do NOT rewrite paragraphs unless a paragraph contains a factual error.

    4. Verify the Onboarding < 30 min checklist (lines 173-183) is still actionable: it claims "Lire ce fichier (5 min) — aperçu architecture + flux Renovate". This is reasonable. Don't touch it unless a step refers to a non-existent file.

    5. Do NOT add new sections. Do NOT rewrite paragraphs that are already correct. The goal is a TARGETED spot-fix, not a refresh.

    No bump to `charts/arr-stack/values.yaml` (README.md is docs-only, D-05 exception applies).
  </action>
  <verify>
    <automated>! grep -nE 'si regression post-Phase 4|si migration depuis l..tat pr.-Phase 4' README.md</automated>
  </verify>
  <done>
    - The 2 KNOWN-STALE lines (79 + 164) have been updated as specified.
    - A cold-re-read of README.md by the executor produces no further stale Phase-4-era / v0.2.x-as-current references.
    - The Onboarding < 30 min checklist (current lines ~173-183) is unchanged.
    - The diff is < 10 lines (small surgical changes only).
    - No change to `charts/arr-stack/values.yaml`.
    - SC#5 readiness statement appended to SUMMARY: "Fresh operator dry-run validation deferred to Phase 11 verifier — cold re-read by author confirms no remaining stale references." (per CONTEXT.md D-11-CLAUDE'S-DISCRETION — self-validation is acceptable for homelab single-tenant.)
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 5: Plan 11-A SUMMARY</name>
  <files>.planning/phases/11-operational-polish-bundle/11-A-SUMMARY.md</files>
  <read_first>
    - `$HOME/.claude/get-shit-done/templates/summary.md` template
    - Prior plan summary `.planning/phases/10-categories-6-app-propagation/10-J-SUMMARY.md` for format reference
    - All 4 task outcomes from Tasks 1-4 above
  </read_first>
  <action>
    Write `.planning/phases/11-operational-polish-bundle/11-A-SUMMARY.md` following the standard summary template. Capture:

    - **Requirements closed** (4): REQ-ruff-format-ci-gate, REQ-paths-filter-arrconf, REQ-snapshot-redaction-harden, REQ-readme-onboarding-v030
    - **Files modified** (5): `.pre-commit-config.yaml` (NEW), `CLAUDE.md`, `.github/workflows/chart-lint.yml`, `tools/snapshot/snapshot.sh`, `tools/snapshot/README.md`, `README.md`
    - **Files NOT modified** (asserted): `charts/arr-stack/values.yaml#arrconf.image.tag` — D-05 exception applied (no `tools/arrconf/**` changes in this plan).
    - **Acceptance criteria status** per task (4 checkmarks).
    - **Operator-side UAT pending** (for the verifier):
      - SC#3 dispositive: `tools/snapshot/snapshot.sh` run on a fresh cluster + anti-leak grep returns `0`. Evidence path: `evidence/snapshot-redaction-uat-<date>.log` (to be captured by the verifier or operator).
      - SC#5 dispositive: fresh operator dry-run < 30 min — self-validated by author per D-11-CLAUDE'S-DISCRETION; external dry-run is opt-in deferred to v0.4.0+.
    - **Deviations** (if any): the planner expected `tests.yml` to need a `ruff format --check` addition, but the line was already present (committed in Phase 5 via commit ef7681a). Plan 11-A pivoted to the local belt (.pre-commit-config.yaml) instead, satisfying REQ-ruff-format-ci-gate via the "documented in CLAUDE.md + pre-commit hook" rationale of D-11-RUFF-GATE.
    - **Chart-pin co-bump audit**: explicit grep `git diff --stat charts/arr-stack/values.yaml` on the commit(s) — must be empty. Confirms D-05 exception was respected.
    - **Carry-forward**: nothing new. Plan 11-B (cross-repo operator actions) runs in parallel (Wave 1).

    Commit the SUMMARY in the same wave but as a separate commit if the executor prefers atomicity. ALWAYS use the Write tool to create the file (never `cat << EOF`).
  </action>
  <verify>
    <automated>test -f .planning/phases/11-operational-polish-bundle/11-A-SUMMARY.md && grep -c 'REQ-ruff-format-ci-gate\|REQ-paths-filter-arrconf\|REQ-snapshot-redaction-harden\|REQ-readme-onboarding-v030' .planning/phases/11-operational-polish-bundle/11-A-SUMMARY.md | grep -q '^[4-9]$\|^[1-9][0-9]\+'</automated>
  </verify>
  <done>
    - `11-A-SUMMARY.md` exists.
    - All 4 REQ IDs mentioned at least once.
    - Files-modified list matches the actual git diff.
    - D-05 chart-pin co-bump exception explicitly affirmed (no `values.yaml` change).
    - Operator-side UAT pending items documented for the verifier.
    - Deviations section documents the `tests.yml` pre-existing state pivot.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| repo → CI | `.github/workflows/*.yml` edits run with `GITHUB_TOKEN`; mis-configured `paths:` filter could trigger CI loop or skip required checks |
| local dev → repo | `.pre-commit-config.yaml` runs locally with developer-level FS access; ruff hooks invoke a downloaded binary from pypi via uv |
| snapshot.sh → snapshots/ | redaction loop overwrites JSON files in place (`mv -f`); a buggy jq filter could destroy snapshot data |
| repo → public GHCR | none in this plan (no image build, no tag bump, no D-05 co-bump) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-11-A-01 | Tampering | `.pre-commit-config.yaml` ruff-pre-commit rev pin | mitigate | Pin exact `rev:` (e.g., `v0.6.9`) — no floating versions; Renovate will track via `pre-commit` manager (already configured in `renovate.json`). |
| T-11-A-02 | Information Disclosure | `tools/snapshot/snapshot.sh` redaction loop | mitigate | jq filter is case-insensitive (`(?i)`) and covers 5 known sensitive keys (`apiKey|password|token|webhookUrl|sessionKey`); fail-safe with `nullglob` guard; manual Option A in README remains as fallback for novel key names. |
| T-11-A-03 | Denial of Service | `mv -f` in redaction loop | accept | If the redaction loop runs on a partial snapshot (qBit text-endpoint .txt files, raw .json from a failed app), `nullglob` + the jq-success gate prevent destruction; falls back to a `warn` log line. |
| T-11-A-04 | Tampering | `chart-lint.yml` `paths:` filter expansion | mitigate | The change is additive only; existing `charts/**` trigger remains, so chart-only commits still fire as before. No removal of any existing path entry. |
| T-11-A-05 | Repudiation | CLAUDE.md "triade" doc claim | accept | The doc claim is informational; the CI in `tests.yml` is the enforcement layer. CLAUDE.md doc cannot be relied on as a security control. |
| T-11-A-06 | Information Disclosure | redaction loop applied AFTER all apps fetched | accept | A snapshot is in plaintext in `${OUTPUT_DIR}` between the curl writes and the redaction loop. Window is sub-second on a successful run, but a SIGKILL during this window leaves cleartext on disk. Trap handler at line 19 cleans `${WORK_DIR}` (curl tampons) but NOT `${OUTPUT_DIR}`. Mitigation deferred to v0.4.0+ (would require per-file redaction in the snapshot_get function, vs. post-loop bulk). Documented in deferred items. |
</threat_model>

<verification>
- All 5 `<verify>` automated commands pass on the final tree.
- `git diff --stat charts/arr-stack/values.yaml` returns empty after all commits (D-05 audit).
- `git diff --stat tools/arrconf/` returns empty (this plan doesn't touch arrconf code).
- Pre-commit hook ergonomic check (optional, not blocking): `pre-commit run --all-files --config .pre-commit-config.yaml` exits 0 on the post-plan tree (it should, since tests.yml's `ruff format --check` is already passing on main).
</verification>

<success_criteria>
1. `.pre-commit-config.yaml` exists at repo root and `grep astral-sh/ruff-pre-commit .pre-commit-config.yaml | wc -l` ≥ 1.
2. `grep -c 'tools/arrconf/\*\*' .github/workflows/chart-lint.yml` ≥ 2 (push + PR paths block).
3. `grep -c 'JQ_REDACT' tools/snapshot/snapshot.sh` ≥ 2 (variable assignment + redaction-loop ref) AND `bash -n tools/snapshot/snapshot.sh` exits 0.
4. `grep -c 'redaction est désormais appliquée AUTOMATIQUEMENT\|redaction now baked-in' tools/snapshot/README.md` ≥ 1.
5. README.md no longer contains "si regression post-Phase 4" nor "migration depuis l'état pré-Phase 4".
6. `git diff --stat charts/arr-stack/values.yaml` (against pre-plan tree) is empty — D-05 audit confirmed.
7. `11-A-SUMMARY.md` exists and references all 4 REQ IDs.
</success_criteria>

<output>
After completion, create `.planning/phases/11-operational-polish-bundle/11-A-SUMMARY.md` (Task 5 produces this).
</output>
