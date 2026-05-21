---
phase: 10-categories-6-app-propagation
plan: 10-I-chart-pin-docs
subsystem: documentation
tags:
  - documentation
  - executor-agent
  - chart-pin-pattern
  - D-07-CHART-PIN-LOOP

dependency_graph:
  requires:
    - 10-C-qbit-wiring-fp
    - 10-D-sonarr-wiring
    - 10-E-radarr-wiring
    - 10-F-seerr-animetags-fp
    - 10-G-jellyfin-wiring
    - 10-H-prowlarr-fp
  provides:
    - REQ-chart-pin-prebump (documentation)
    - D-07-CHART-PIN-LOOP closure (CF-07-1)
  affects:
    - CLAUDE.md (project rulebook)
    - /home/moi/.claude/agents/gsd-executor.md (global agent prompt)

tech_stack:
  added: []
  patterns:
    - Release pin co-bump pattern (chart image tag bump in same commit as arrconf code change)

key_files:
  created: []
  modified:
    - CLAUDE.md
    - /home/moi/.claude/agents/gsd-executor.md (outside repo — no git commit)

decisions:
  - "D-07-CHART-PIN-LOOP (CF-07-1): documented as permanent project convention in CLAUDE.md; Phase 9-D pilot commit de904c9 is the canonical reference; Phase 10 chain (0.5.3→0.6.5) is the live demonstration"
  - "gsd-executor.md rule is project-agnostic in framing (applies to any project with a chart-pin pattern) but arr-stack-specific in its concrete example"

metrics:
  duration: "~8 minutes"
  completed: "2026-05-19T20:36:10Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 10 Plan I: chart-pin-docs Summary

**One-liner:** Documented the Release pin co-bump pattern in CLAUDE.md and gsd-executor.md, closing D-07-CHART-PIN-LOOP (CF-07-1) that had been carried forward since Phase 7.

## What Was Done

### Task 10-I-01: CLAUDE.md — "Release pin co-bump pattern" subsection

Added a new `### Release pin co-bump pattern` subsection at the end of `## Conventions développement — arrconf`, immediately before the `## Conventions Helm` section.

**Commit:** `6ed8ea0` — `docs(10-I): add Release pin co-bump pattern section to CLAUDE.md`

**Content grep evidence:**

```
### Release pin co-bump pattern

**Règle :** lorsqu'un commit modifie des fichiers sous `tools/arrconf/**` (code Python,
Dockerfile, pyproject.toml), il doit **également** bumper
`charts/arr-stack/values.yaml#arrconf.image.tag` dans **le même commit**.
Clôture D-07-CHART-PIN-LOOP (CF-07-1, STATE.md §"Phase 7 deviations").
```

Section covers:
- WHY: auto-tag chain fires before values.yaml re-eval → 2 Renovate cycles without co-bump
- HOW: patch bump for fixes, minor for features, in same commit
- Historical reference table (de904c9 pilot + Phase 10 chain 0.5.3→0.6.5)
- Exception: pure-doc commits must NOT bump values.yaml
- Renovate annotation preservation reminder

### Task 10-I-02: gsd-executor.md — chart-pin co-bump rule injected

Added a project-agnostic `**Release-pin co-bump rule**` paragraph right after the `**CLAUDE.md enforcement:**` paragraph inside `<project_context>`, before the closing `</project_context>` tag.

**File:** `/home/moi/.claude/agents/gsd-executor.md` (outside repo — no git commit, global agent config)

**Content grep evidence:**

```
**Release-pin co-bump rule (project-agnostic pattern when a project defines it):**
Some projects pin a runtime image inside a Helm chart that lives in the same repo as
the code producing that image. If `./CLAUDE.md` documents a 'Release pin co-bump pattern'
(or similar), follow it strictly: when your task modifies source files that the image is
built from, also stage the chart values file with the incremented image tag in the SAME
commit. For the `arr-stack` repo specifically: changes to `tools/arrconf/**` MUST be
paired with a `charts/arr-stack/values.yaml#arrconf.image.tag` bump in the same commit
(patch for fixes, minor for features). Preserve the `# renovate: image=...` annotation
above the `repository:` line — Renovate watches it. See CLAUDE.md 'Release pin co-bump
pattern'.
```

## Commits

| Task | Commit | Files | Description |
|------|--------|-------|-------------|
| 10-I-01 | `6ed8ea0` | `CLAUDE.md` | Add Release pin co-bump pattern subsection |
| 10-I-02 | *(no repo commit — out-of-repo file)* | `/home/moi/.claude/agents/gsd-executor.md` | Inject project-agnostic chart-pin rule |

## No values.yaml Change — D-05 Exception Confirmed

```
$ git diff HEAD -- charts/arr-stack/values.yaml
(empty)
```

This plan IS the documentation of the rule; it does not modify `tools/arrconf/**`, so the rule does not apply to its own commits. The `arrconf.image.tag` stays at `0.6.5` (Plan 10-H's final bump). Plan 10-J handles the next phase decision.

## Requirements Closed

- **REQ-chart-pin-prebump** — documentation surface complete

## Pointer to Next Plan

**Plan 10-J** is the final Phase 10 plan. See `.planning/phases/10-categories-6-app-propagation/` for `10-J-*-PLAN.md`.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `grep "Release pin co-bump pattern" CLAUDE.md` → 1 match (line 149) ✓
- `grep "D-07-CHART-PIN-LOOP" CLAUDE.md` → 2 matches ✓
- `grep "de904c9" CLAUDE.md` → 1 match ✓
- `grep "0.5.3" CLAUDE.md` → 2 matches ✓
- `git diff HEAD -- charts/arr-stack/values.yaml` → empty ✓
- `grep "Release-pin co-bump rule" /home/moi/.claude/agents/gsd-executor.md` → 1 match ✓
- `grep "charts/arr-stack/values.yaml" /home/moi/.claude/agents/gsd-executor.md` → 1 match ✓
- `grep "renovate: image=" /home/moi/.claude/agents/gsd-executor.md` → 1 match ✓
- `grep "tools/arrconf/" /home/moi/.claude/agents/gsd-executor.md` → 1 match ✓
- Commit `6ed8ea0` exists in git log ✓
