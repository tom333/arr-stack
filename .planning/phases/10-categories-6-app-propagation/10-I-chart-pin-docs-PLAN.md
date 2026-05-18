---
phase: 10-categories-6-app-propagation
plan: 10-I-chart-pin-docs
type: execute
wave: 3
depends_on:
  - 10-C-qbit-wiring-fp
  - 10-D-sonarr-wiring
  - 10-E-radarr-wiring
  - 10-F-seerr-animetags-fp
  - 10-G-jellyfin-wiring
  - 10-H-prowlarr-fp
files_modified:
  - CLAUDE.md
  - /home/moi/.claude/agents/gsd-executor.md
autonomous: true
requirements:
  - REQ-chart-pin-prebump
requirements_addressed:
  - REQ-chart-pin-prebump (documentation surface — D-05 D-07-CHART-PIN-LOOP closure)
tags:
  - documentation
  - executor-agent
  - chart-pin-pattern

must_haves:
  truths:
    - "`CLAUDE.md` contains a new subsection under \"Conventions développement — arrconf\" titled \"Release pin co-bump pattern\" explaining: whenever a reconciler/arrconf-code change ships, bump `charts/arr-stack/values.yaml#arrconf.image.tag` to the expected new semver in the SAME commit. References the Phase 9-D pilot (de904c9, 0.5.0→0.5.3) and the Phase 10 series (0.5.3 → 0.6.0 → 0.6.1 … → 0.6.5)."
    - "`/home/moi/.claude/agents/gsd-executor.md` contains a one-line convention rule (under an appropriate existing conventions section) stating: \"When modifying files under `tools/arrconf/**`, also stage `charts/arr-stack/values.yaml` with an incremented `arrconf.image.tag` (patch bump for code-only changes; minor bump for new features) in the SAME commit. See CLAUDE.md 'Release pin co-bump pattern'.\""
    - "Both documentation surfaces reference D-07-CHART-PIN-LOOP closure (the original carry-forward issue from STATE.md §\"Phase 7 deviations\")."
    - "No arrconf code changes in this plan — pure docs."
    - "**NO chart-pin co-bump on THIS plan's commit** — this plan IS the doc that defines the rule; it doesn't trigger the rule because nothing in `tools/arrconf/**` is modified."
  artifacts:
    - path: "CLAUDE.md"
      provides: "New 'Release pin co-bump pattern' subsection under Conventions développement — arrconf"
      contains: "Release pin co-bump pattern"
    - path: "/home/moi/.claude/agents/gsd-executor.md"
      provides: "One-line chart-pin co-bump rule in conventions section"
      contains: "charts/arr-stack/values.yaml"
  key_links:
    - from: "CLAUDE.md \"Release pin co-bump pattern\" subsection"
      to: "charts/arr-stack/values.yaml#arrconf.image.tag"
      via: "Documented pattern referencing values.yaml location + Phase 9-D pilot commit de904c9"
      pattern: "arrconf\\.image\\.tag|values\\.yaml"
    - from: "/home/moi/.claude/agents/gsd-executor.md conventions block"
      to: "CLAUDE.md 'Release pin co-bump pattern'"
      via: "Reference link/quote pointing executors to the project rulebook"
      pattern: "Release pin co-bump pattern|CLAUDE\\.md"
---

<objective>
Document the chart-pin co-bump pattern on the two surfaces that govern executor behaviour: project-level `CLAUDE.md` (the rulebook) and global `/home/moi/.claude/agents/gsd-executor.md` (the agent prompt). Closes REQ-chart-pin-prebump.

Purpose: D-05 documents the pattern that Plans 10-C through 10-H all already demonstrate in their commits. With these docs in place, future Phase 11+ executors automatically apply the rule without needing explicit per-plan instructions.

Output: Two doc files updated. NO chart-pin co-bump on THIS plan's commit — this plan defines the rule but doesn't modify `tools/arrconf/**`, so the rule doesn't apply to its own commits.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/10-categories-6-app-propagation/10-CONTEXT.md
@.planning/phases/10-categories-6-app-propagation/10-RESEARCH.md
@.planning/STATE.md
@CLAUDE.md
@/home/moi/.claude/agents/gsd-executor.md

<interfaces>
<!-- CLAUDE.md target section: "Conventions développement — arrconf" subsections -->
<!-- gsd-executor.md target: existing conventions section (executor must locate via grep before editing) -->
<!-- Phase 9-D pilot context: commit de904c9 bumped 0.5.0 → 0.5.3 (CF-07-1 closure pilot) -->
<!-- Phase 10 cumulative bumps: 0.5.3 → 0.6.0 (10-C) → 0.6.1 (10-D) → 0.6.2 (10-E) → 0.6.3 (10-F) → 0.6.4 (10-G) → 0.6.5 (10-H) -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 10-I-01: Add "Release pin co-bump pattern" section to CLAUDE.md</name>
  <files>CLAUDE.md</files>
  <read_first>
    - CLAUDE.md (full file — locate the "Conventions développement — arrconf" top-level section)
    - .planning/STATE.md §"Phase 7 deviations + follow-ups" item 12 (CF-07-1 — D-07-CHART-PIN-LOOP context)
    - .planning/phases/10-categories-6-app-propagation/10-C-qbit-wiring-fp-PLAN.md (precedent — Plan 10-C bumped 0.5.3 → 0.6.0)
    - 10-CONTEXT.md §"Chart-pin pre-bump pattern documentation surface (D-05)"
    - 10-RESEARCH.md §"Chart-Pin Co-Bump Documentation Surfaces"
  </read_first>
  <behavior>
    - CLAUDE.md gains a new subsection (most likely a new `###` heading under the existing "Conventions développement — arrconf" `##` section).
    - The section explains WHY (post-merge auto-tag chain creates a release tag BEFORE values.yaml is bumped, so without the co-bump my-kluster gets two `targetRevision` PRs per phase instead of one).
    - The section explains HOW (modify `tools/arrconf/**` AND `charts/arr-stack/values.yaml` line `arrconf.image.tag` in the same commit; patch bump for fixes, minor for new features).
    - References the Phase 9-D pilot commit `de904c9` (0.5.0 → 0.5.3) and the Phase 10 series cumulative bumps.
    - References D-07-CHART-PIN-LOOP closure (CF-07-1 from STATE.md).
  </behavior>
  <action>
1. Read `CLAUDE.md` and locate the section header `## Conventions développement — arrconf`. The current structure has subsections like `### Code style`, `### Idempotence (RÈGLE D'OR)`, `### Tests`, `### CLI`, `### Variables d'environnement`.

2. **Append a new `### Release pin co-bump pattern` subsection** at the end of `## Conventions développement — arrconf` (after `### Variables d'environnement`). The content explains:

   - **Rule:** when modifying `tools/arrconf/**`, you MUST also bump `charts/arr-stack/values.yaml#arrconf.image.tag` in the SAME commit (closes D-07-CHART-PIN-LOOP, see Phase 7 deviations CF-07-1).
   - **Semver guidance:** patch bump (e.g. 0.6.5 → 0.6.6) for a bug fix or FP fix; minor bump (e.g. 0.6.x → 0.7.0) for a new feature or new phase; major bump (e.g. 0.x → 1.0) for a major milestone.
   - **Why:** after merge to `main`, `chart-lint.yml` creates an auto tag via `mathieudutour/github-tag-action` BEFORE the chart values are re-evaluated. Without the co-bump, the release chain becomes (1) push → auto-tag `vX.Y.(Z+1)`, (2) Renovate on my-kluster opens PR `targetRevision: vX.Y.(Z+1)`, but ArgoCD sees `values.yaml#arrconf.image.tag` still points to `vX.Y.Z` → the arrconf pod stays on the old version → a 2nd commit on arr-stack is needed to bump `values.yaml`, then a 2nd Renovate PR on my-kluster → **2 cycles** instead of 1. With the co-bump, the new image is already pinned when the auto-tag drops → single release cycle.
   - **Reference:** Phase 9-D commit `de904c9` (0.5.0 → 0.5.3) — pilot. Phase 10 chains `0.5.3 → 0.6.0 → 0.6.1 → 0.6.2 → 0.6.3 → 0.6.4 → 0.6.5` (one patch bump per arrconf-code-touching plan).
   - **Exception:** a pure-doc commit (only `.md` changes, no Python files under `tools/arrconf/`) must NOT bump `values.yaml` — the tag does not need to evolve.
   - **Critical:** NEVER touch the `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` annotation (line 449 of `values.yaml`) — it is required for Renovate's image tracking.

3. Use French for the section heading and prose (matches the rest of CLAUDE.md). The technical terms (`tag`, `values.yaml`, `D-07-CHART-PIN-LOOP`, the commit SHA, the version strings) stay in English.

4. Verify the edit by re-reading CLAUDE.md and confirming the new subsection is present.

5. **NO values.yaml changes in this commit** — this plan IS the doc, not a code change.
  </action>
  <verify>
    <automated>grep -c "Release pin co-bump pattern" CLAUDE.md &amp;&amp; grep -c "D-07-CHART-PIN-LOOP" CLAUDE.md &amp;&amp; grep -c "de904c9" CLAUDE.md &amp;&amp; ! git diff HEAD -- charts/arr-stack/values.yaml | grep -E '^\+.*tag:' &amp;&amp; echo "OK"</automated>
  </verify>
  <acceptance_criteria>
    - `grep "Release pin co-bump pattern" CLAUDE.md` exits 0
    - `grep "D-07-CHART-PIN-LOOP" CLAUDE.md` exits 0 (D-07 closure reference)
    - `grep "de904c9" CLAUDE.md` exits 0 (Phase 9-D pilot commit reference)
    - `grep "0\.5\.3" CLAUDE.md | wc -l` ≥ 1 (Phase 10 starting tag referenced)
    - `git diff HEAD -- charts/arr-stack/values.yaml` returns empty (no tag bump in this plan)
    - The verify command exits 0
  </acceptance_criteria>
  <done>"Release pin co-bump pattern" subsection added to CLAUDE.md with D-07-CHART-PIN-LOOP closure references; no values.yaml change.</done>
</task>

<task type="auto">
  <name>Task 10-I-02: Inject chart-pin rule into /home/moi/.claude/agents/gsd-executor.md</name>
  <files>/home/moi/.claude/agents/gsd-executor.md</files>
  <read_first>
    - /home/moi/.claude/agents/gsd-executor.md lines 54-65 (Project instructions / CLAUDE.md enforcement block)
    - CLAUDE.md "Release pin co-bump pattern" section just added in Task 10-I-01 (target of the cross-reference)
    - 10-CONTEXT.md §"Chart-pin pre-bump pattern documentation surface (D-05)"
  </read_first>
  <behavior>
    - The gsd-executor agent prompt gains a paragraph or one-line rule about chart-pin co-bump in or right after the existing "CLAUDE.md enforcement" block.
    - The rule is project-agnostic in framing (this agent file is global) but references the project-specific `arr-stack` pattern as the concrete example.
    - The rule references CLAUDE.md's "Release pin co-bump pattern" section.
    - **No other content in gsd-executor.md changes.**
  </behavior>
  <action>
1. Read the agent file. The "Project instructions" + "CLAUDE.md enforcement" block is at lines 54-60.

2. **Append a new paragraph** right after the existing "CLAUDE.md enforcement" content. The paragraph:

   - Opens with a sentence framing the rule as project-agnostic: "Some projects pin a runtime image inside a Helm chart that lives in the same repo as the code producing that image."
   - Instructs: "If `./CLAUDE.md` documents a 'Release pin co-bump pattern' (or similar), follow it strictly: when your task modifies source files that the image is built from, also stage the chart values file with the incremented image tag in the SAME commit."
   - Calls out the `arr-stack` specifics: "For the `arr-stack` repo specifically: changes to `tools/arrconf/**` MUST be paired with a `charts/arr-stack/values.yaml#arrconf.image.tag` bump in the same commit (patch for fixes, minor for features)."
   - Closes with: "Preserve the `# renovate: image=...` annotation above the `repository:` line — Renovate watches it."

   Use the label `**Release-pin co-bump rule (project-agnostic pattern when a project defines it):**` at the start of the paragraph for grep-ability.

3. Do not modify any other section of the agent file. Use the Edit tool for a surgical insertion (NOT Write — preserves all other content).

4. **Critical:** this file lives OUTSIDE the project repo (`/home/moi/.claude/agents/`). It is not under this repo's `.git`. The executor still edits it as a configuration file. Document the edit in the plan SUMMARY with a `grep -A 3 "Release-pin co-bump rule" /home/moi/.claude/agents/gsd-executor.md` evidence snippet.
  </action>
  <verify>
    <automated>grep "Release-pin co-bump rule" /home/moi/.claude/agents/gsd-executor.md &amp;&amp; grep "charts/arr-stack/values.yaml" /home/moi/.claude/agents/gsd-executor.md &amp;&amp; grep "renovate: image=" /home/moi/.claude/agents/gsd-executor.md &amp;&amp; echo "OK"</automated>
  </verify>
  <acceptance_criteria>
    - `grep "Release-pin co-bump rule" /home/moi/.claude/agents/gsd-executor.md` exits 0
    - `grep "charts/arr-stack/values.yaml" /home/moi/.claude/agents/gsd-executor.md` exits 0
    - `grep "renovate: image=" /home/moi/.claude/agents/gsd-executor.md` exits 0
    - `grep "tools/arrconf/" /home/moi/.claude/agents/gsd-executor.md` exits 0
    - The verify command exits 0
  </acceptance_criteria>
  <done>Project-agnostic chart-pin rule injected into gsd-executor.md with project-specific arr-stack reference + values.yaml + renovate annotation guidance.</done>
</task>

</tasks>

<verification>
End-to-end:
```bash
grep "Release pin co-bump pattern" CLAUDE.md
grep "Release-pin co-bump rule" /home/moi/.claude/agents/gsd-executor.md
git diff HEAD -- charts/arr-stack/values.yaml   # MUST be empty
```

This plan ships docs ONLY. No values.yaml change. The arrconf image stays at 0.6.5 (Plan 10-H's final bump). Plan 10-J handles the next decision on co-bump (it's mostly tests + REQUIREMENTS.md edit — see 10-J for its own co-bump decision).
</verification>

<success_criteria>
- CLAUDE.md has the new "Release pin co-bump pattern" subsection with D-07-CHART-PIN-LOOP closure references and Phase 9-D pilot commit `de904c9` reference.
- `/home/moi/.claude/agents/gsd-executor.md` has the project-agnostic chart-pin rule with arr-stack-specific example.
- `git diff HEAD -- charts/arr-stack/values.yaml` returns empty (no values.yaml change).
- Single commit on the arr-stack repo modifying ONLY `CLAUDE.md`. The gsd-executor.md edit is on a global file outside the repo, but the executor commit summary documents it.
</success_criteria>

<output>
After completion, create `.planning/phases/10-categories-6-app-propagation/10-I-chart-pin-docs-SUMMARY.md` with:
- Commit SHA for the arr-stack-side CLAUDE.md commit
- A grep snippet showing the new CLAUDE.md subsection content
- A grep snippet showing the new gsd-executor.md rule (this file is outside the repo, so just document via grep output, no commit SHA)
- Confirmation that no values.yaml change was made (D-05 exception for pure-doc commits)
- Pointer to Plan 10-J as the final Phase 10 plan
</output>
