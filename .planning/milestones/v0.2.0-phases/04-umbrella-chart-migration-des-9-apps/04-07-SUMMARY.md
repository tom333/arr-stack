---
phase: 04-umbrella-chart-migration-des-9-apps
plan: "07"
subsystem: docs
tags: [readme, claude-md, onboarding, documentation, post-phase-4]
dependency_graph:
  requires:
    - phase: 04-05
      provides: umbrella values.yaml + chart structure (source of truth for Structure actuelle)
    - phase: 04-06
      provides: chart-lint.yml + renovate.json (documented in README Renovate flow)
  provides:
    - README.md (onboarding entry point — < 30 min)
    - CLAUDE.md (convention guide — post-Phase-4 ground truth)
  affects:
    - REQ-readme-onboarding (addressed)
    - D-04-DOCS-01 (fulfilled)
tech_stack:
  added: []
  patterns:
    - "README as operator-facing reference: ASCII diagram + Renovate flow + 4 runbook sub-sections"
    - "CLAUDE.md surgical edits: 4 targeted sections updated, all other sections preserved verbatim"
key_files:
  created: []
  modified:
    - README.md
    - CLAUDE.md
decisions:
  - "README fully rewritten end-to-end (29-line stub → 195-line substantive doc) per D-04-DOCS-01"
  - "CLAUDE.md surgical edits only — 4 sections updated, every other section preserved exactly"
  - "Helm 4 multi-alias workaround documented both in README and in CLAUDE.md Dependencies section"
  - "Release section in CLAUDE.md updated to reflect auto-tag (mathieudutour/github-tag-action B3) rather than the stale Phase 0/1 open question"
metrics:
  duration_minutes: 25
  completed_date: "2026-05-13"
  tasks_completed: 2
  files_created: 0
  files_modified: 2
---

# Phase 04 Plan 07: README + CLAUDE.md refresh Summary

README.md rewritten end-to-end with 8 sections and < 30 min onboarding flow; CLAUDE.md refreshed on 4 target sections to reflect post-Phase-4 ground truth (umbrella chart, app-template 5.0.0, single ArgoCD App, Replace=true).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 7.1 | Rewrite README.md end-to-end | 8146ca2 | README.md |
| 7.2 | Refresh CLAUDE.md (4 sections) | 93749cd | CLAUDE.md |
| 7.3 | Operator verifies onboarding flow | PENDING | — |

## Task 7.1 — README.md Final Structure

README.md rewritten from a 29-line Phase 0 stub to a 195-line substantive document with 8 top-level sections:

| Section | Content |
|---------|---------|
| Vue d'ensemble | 2-component description (arrconf + umbrella chart) + configarr boundary |
| Architecture | ASCII diagram: arr-stack → arr-stack-app.yaml → selfhost namespace; Renovate flow; Replace=true note |
| Stack technique | 10-row table: app-template 5.0.0, Helm 4.1.4, Python 3.13, GHCR image, ArgoCD, Renovate |
| Déploiement | Prerequisites + local chart verification (helm dependency build + Helm 4 multi-alias tar workaround) + premier déploiement + Renovate bump flow (7 steps) |
| Operator runbook | 4 sub-runbooks: snapshot, force-run, drift-diagnose, rollback |
| Onboarding (< 30 min) | 5 steps, target 25-30 min without touching cluster |
| Documentation | Links to spec.md, CLAUDE.md, .planning/, tools/snapshot, tools/arrconf, charts/arr-stack, my-kluster |
| Licence | Single-tenant homelab |

**Acceptance criteria — all PASS:**
- Line count: 195 (>= 100)
- All 7 required sections present
- app-template 5.0.0 referenced (5 occurrences)
- No 4.6.2 stale references
- Renovate flow: 8 occurrences
- Links to spec.md and CLAUDE.md present
- Snapshot section present
- No [TBD]/[FIXME] placeholders

## Task 7.2 — CLAUDE.md Section Updates

4 sections updated surgically. All other sections (Conventions développement — arrconf, Idempotence, Tests, CLI, Variables d'environnement, Frontière arrconf/configarr, Pattern single-instance, Comment ajouter une nouvelle app, Comment ajouter un nouveau resource type, Ce que tu NE dois PAS faire, GSD intégration, Références) preserved verbatim.

### Section 1: Structure cible → Structure actuelle (post-Phase 4)

- Heading changed from "Structure cible" to "Structure actuelle (post-Phase 4)"
- Tree now reflects actual post-Phase-4 layout:
  - Added `tools/scripts/` with 2 helper scripts
  - Added `Chart.lock`, `schemas/`, `snapshots/`
  - Removed `arrconf-cronjob.yaml` + `configarr-cronjob.yaml` (D-04-CRON-01)
  - Added `merge.py` to arrconf module listing
  - `examples/values-prod.yaml` annotated with D-04-VALUES-03 reference
- Historical note explaining the CronJob template removal

### Section 2: Stack technique table

- Helm row updated: `Helm 3 + chart bjw-s/app-template en deps` → `Helm 3 (≥ 3.18 requis par app-template 5.0.0) + chart bjw-s/app-template@5.0.0 en deps`

### Section 3: Intégration avec my-kluster

- Rewritten for single-App pattern (post-Phase 4)
- Added `Replace=true` syncOption with D-04-CUTOVER-05 rationale (Deployment selector immutability)
- Updated deletion list from 5 unit Apps (Phase 3 anticipation) to 10 unit Apps (Phase 4 reality) + charts/arrconf/ + charts/configarr/
- Renamed secrets to `arrconf-env` / `configarr-env` (production Secret names)
- Added Renovate argocd manager tracking `targetRevision`

### Section 4: Bootstrap (état actuel — 2026-05-07) → Historical bootstrap (Phase 0-3)

- Heading renamed
- Archival note added pointing readers to current sections
- Body preserved for historical traceability

**Bonus: Dependencies section in Conventions Helm**
- Version examples updated 4.6.2 → 5.0.0 (removes last stale 4.6.2 reference)
- Helm 4 multi-alias workaround documented as a code block

**Bonus: Release section in Workflow de développement**
- Updated from "open question Phase 0/1" to actual B3 auto-tag mechanism (mathieudutour/github-tag-action)

**Acceptance criteria — all PASS:**
- "Structure actuelle" present, "Structure cible" absent
- "Historical bootstrap" present, "Bootstrap (état actuel" absent
- arr-stack-app.yaml referenced, Replace=true documented
- app-template@5.0.0 referenced, no 4.6.2 stale references
- No arrconf-cronjob.yaml / configarr-cronjob.yaml in file
- All preserved sections intact: Conventions développement, Pattern single-instance, Ce que tu NE dois PAS faire
- File length: 430 lines (>= 400)

## Task 7.3 — Operator walkthrough (PENDING)

Task 7.3 is a `checkpoint:human-verify` gate requiring the operator to perform a wall-clock timed onboarding run (< 30 min budget per REQ-readme-onboarding). This task cannot be automated.

**Resume signal**: operator types `approved <minutes-spent>` (e.g., `approved 22`) to unblock Wave 6, or `needs-edit: <what is missing>` to trigger a Task 7.1/7.2 tightening pass.

## Deviations from Plan

### Minor deviation: Release section updated (Rule 2)

- **Found during:** Task 7.2 review of CLAUDE.md
- **Issue:** The "Release" subsection under "Workflow de développement" still referenced an open question from Phase 0/1 ("À arbitrer Phase 0/1") when auto-tagging is now implemented in chart-lint.yml (Plan 04-06).
- **Fix:** Rewrote Release subsection to document the actual B3 auto-tag mechanism.
- **Files modified:** CLAUDE.md
- **Rule applied:** Rule 2 (missing correctness — doc claiming something is undecided when it is decided)

### Minor deviation: Dependencies example version + workaround documented

- **Found during:** Task 7.2 — Dependencies code block in Conventions Helm still showed `version: 4.6.2`
- **Fix:** Updated to `5.0.0`; added Helm 4 multi-alias workaround block (this is a critical developer workflow step, undocumented in CLAUDE.md prior)
- **Rule applied:** Rule 1 (stale version reference = incorrect documentation)

## Known Stubs

Task 7.3 operator walkthrough is pending. The SUMMARY notes "pending operator walkthrough" for this task. Once the operator completes the timed read and returns the resume signal, Wave 6 plans can proceed.

## Threat Flags

None. Documentation-only changes — no new network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| README.md (195 lines, 8 sections) | FOUND |
| CLAUDE.md (430 lines, 4 sections updated) | FOUND |
| Commit 8146ca2 (Task 7.1) | FOUND |
| Commit 93749cd (Task 7.2) | FOUND |
| All README acceptance criteria | PASS |
| All CLAUDE.md acceptance criteria | PASS |
