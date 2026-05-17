---
phase: "00-bootstrap-repo-snapshot-raw"
plan: "01"
subsystem: "repo-scaffolding"
tags: [bootstrap, repo-scaffolding, renovate, gitignore]

dependency_graph:
  requires: []
  provides:
    - README.md root pointer
    - .gitignore with secret guards (no snapshots/ exclusion — ADR-6)
    - renovate.json initial config (config:recommended)
    - tools/snapshot/ directory placeholder
  affects: []

tech_stack:
  added: []
  patterns:
    - renovate config:recommended preset
    - .gitignore negation pattern (!.env.example) to preserve tracked template

key_files:
  created:
    - README.md
    - .gitignore
    - tools/snapshot/.gitkeep
    - renovate.json
  modified: []
  preserved:
    - .env.example (pre-existing, not overwritten)

decisions:
  - "config:recommended over config:base — config:base deprecated since Renovate v33+, validator warns on it"
  - "No customManagers in renovate.json Phase 0 — values.yaml does not exist yet; deferred to Phase 4"
  - ".gitignore omits snapshots/ intentionally — ADR-6 mandates snapshots versioned in Git; comment in file documents the WHY"
  - "!.env.example negation in .gitignore — template must remain tracked despite .env.* wildcard rule"

metrics:
  duration_minutes: 5
  completed_date: "2026-05-07"
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 0
---

# Phase 00 Plan 01: Repo Scaffolding (README + .gitignore + Renovate) Summary

## One-liner

Repo root scaffolded with README pointer, .gitignore with ADR-6-compliant snapshots/ non-exclusion + !.env.example negation, and renovate.json using config:recommended preset validated by the official renovate-config-validator.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Créer README.md + .gitignore + tools/snapshot/.gitkeep | dea7703 | README.md, .gitignore, tools/snapshot/.gitkeep |
| 2 | Créer renovate.json + valider via renovate-config-validator | e0e9e7e | renovate.json |

## Files Created

| File | Purpose | Key content |
|------|---------|-------------|
| `README.md` | Public entry point — Phase 0 minimal pointer | Links to spec.md, CLAUDE.md, tools/snapshot/README.md; snapshot quick-start block |
| `.gitignore` | Secret guards + intentional non-exclusion of snapshots/ | Ignores .env*/*.cookies/*.cookie-jar; !.env.example; explicit comment on snapshots/ |
| `tools/snapshot/.gitkeep` | Git directory tracking placeholder | Single-line comment pointing to Plan 02 |
| `renovate.json` | Initial Renovate configuration | `extends: ["config:recommended"]`, $schema, no customManagers (deferred Phase 4) |

## Renovate Config

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"]
}
```

Preset: `config:recommended` (current, replaces deprecated `config:base` since Renovate v33+).

No `customManagers` and no `packageRules` — `values.yaml` does not exist yet. Deferred to Phase 4 per plan specification.

Validation: renovate-config-validator output: `INFO: Config validated successfully`

## .gitignore: No snapshots/ Pattern

Confirmed: `grep -qE '^snapshots/?$' .gitignore` exits 1 (no match). The file contains an explicit comment:

```
# CRITIQUE : NE PAS ignorer snapshots/ — versionnés Git par ADR-6
# (pas de pattern snapshots/ ici — c'est volontaire, voir CLAUDE.md "ne pas faire")
```

This documents the intentional absence for future developers.

## .env.example Preservation

The `.env.example` file was pre-committed (commit b5a4038) and was NOT overwritten. It contains all 7 required env vars (SONARR_API_KEY, RADARR_API_KEY, PROWLARR_API_KEY, QBT_USER, QBT_PASS, SEERR_API_KEY, JELLYFIN_API_KEY) and 6 commented URL defaults.

The `.gitignore` contains `!.env.example` to preserve it despite the `.env.*` wildcard. Verified: `git check-ignore .env.example` exits 1 (not ignored).

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. No data flows or UI rendering involved in this scaffolding plan.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. Files are static configuration only. All threats identified in the plan's threat model (T-00-01 through T-00-03) are mitigated:

- T-00-01 (secret leak via .gitignore): .gitignore ignores .env* and *.cookies/.cookie-jar
- T-00-02 (snapshots/ accidentally ignored): verified absent + commented
- T-00-03 (renovate.json malformed): triple validation passed (jq + jq field check + renovate-config-validator)

## Next Step

Plan 02: Create `tools/snapshot/snapshot.sh` — the Bash script that performs raw API snapshots. The `tools/snapshot/` directory is now in place. Plan 02 may delete the `.gitkeep` placeholder once `snapshot.sh` and `README.md` are present.

## Self-Check

Files exist check:
- README.md: FOUND
- .gitignore: FOUND
- tools/snapshot/.gitkeep: FOUND
- renovate.json: FOUND

Commits exist check:
- dea7703: FOUND (chore(00-01): scaffold repo root files)
- e0e9e7e: FOUND (chore(00-01): ajouter renovate.json initial)

## Self-Check: PASSED
