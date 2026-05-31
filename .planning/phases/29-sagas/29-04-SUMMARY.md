---
phase: 29-sagas
plan: "04"
subsystem: arrconf-config
tags: [jellyfin, plugins, tmdbboxsets, sagas, two-run]
dependency_graph:
  requires: []
  provides: [jellyfin-tmdbboxsets-plugin-entry]
  affects: [charts/arr-stack/files/arrconf.yml]
tech_stack:
  added: []
  patterns: [two-run-plugin-install-ADR-9]
key_files:
  created: []
  modified:
    - charts/arr-stack/files/arrconf.yml
decisions:
  - "No config block added: tmdbboxsets auto-configures via defaults (MinimumNumberOfMovies=2, StripCollectionKeywords=false)"
  - "No new plugin_repositories entry: Jellyfin Stable manifest already covers the repo URL"
  - "No arrconf.image.tag co-bump: arrconf.yml-only change per CLAUDE.md exception clause"
metrics:
  duration: "3 minutes"
  completed: "2026-05-31"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 1
requirements: [SAGAS-03]
---

# Phase 29 Plan 04: Add tmdbboxsets plugin entry — Summary

TMDb Box Sets plugin entry wired into `jellyfin.main.plugins.required` via the existing ADR-9 two-run install model; movie BoxSets auto-created from TMDB collection metadata once the plugin is active after two arrconf runs.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add tmdbboxsets plugin entry to arrconf.yml | 86cd714 | charts/arr-stack/files/arrconf.yml |

## What Was Done

Added the `TMDb Box Sets` plugin entry to `jellyfin.main.plugins.required` in `charts/arr-stack/files/arrconf.yml`:

- **GUID:** `bc4aad2e-d3d0-4725-a5e2-fd07949e5b42`
- **Version:** `13.0.0.0`
- **Repo URL:** `https://repo.jellyfin.org/files/plugin/manifest.json` (matches existing "Jellyfin Stable" `plugin_repositories` entry — no new repo entry added)
- **No config block:** plugin auto-configures via defaults (`MinimumNumberOfMovies=2`, `StripCollectionKeywords=false`)
- **No arrconf.image.tag co-bump:** `arrconf.yml` ConfigMap-only change — outside `tools/arrconf/**`, CLAUDE.md exception applies

The entry shape mirrors the Intro Skipper install entry (the established analog for ADR-9 two-run plugin installs): `name` + `install_guid` + `install_version` + `install_repo_url`.

## Verification Results

- `grep -q 'bc4aad2e-d3d0-4725-a5e2-fd07949e5b42'` — PASSED
- `grep -q 'TMDb Box Sets'` — PASSED
- Jellyfin repo URL count `>= 2` (Jellyfin Stable entry + new install entry) — PASSED (count=2)
- `plugin_repositories` key count == 1 (no new repo section added) — PASSED
- YAML parses cleanly (`python3 -c "import yaml; yaml.safe_load(...)"`) — PASSED
- `git diff --name-only HEAD` shows only `charts/arr-stack/files/arrconf.yml` — PASSED

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The plugin entry is complete and wired; tmdbboxsets will install and enable via the existing `_reconcile_plugins` two-run model on next arrconf run.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The change is declarative config only — plugin entry references the already-trusted Jellyfin Stable manifest URL.

## Self-Check: PASSED

- File `charts/arr-stack/files/arrconf.yml` — exists and contains the GUID
- Commit `86cd714` — present in git log
- No values.yaml modification — confirmed via `git diff --name-only HEAD~1 HEAD`
