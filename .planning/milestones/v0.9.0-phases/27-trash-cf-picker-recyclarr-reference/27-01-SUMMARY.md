---
phase: 27-trash-cf-picker-recyclarr-reference
plan: "01"
subsystem: arrconf-ui/assets
tags: [trash-guides, recyclarr, baked-catalog, static-assets, dev-tooling]
dependency_graph:
  requires: []
  provides:
    - tools/arrconf-ui/web/src/assets/trash-metadata/ (6 catalog JSON + manifest)
    - tools/scripts/fetch-trash-metadata.sh (dev-time fetch script)
  affects:
    - plans/27-02 (CF picker reads sonarr-cf.json / radarr-cf.json)
    - plans/27-03 (Recyclarr reference reads recyclarr-{sonarr,radarr}.json)
    - plans/27-04 (QP picker reads sonarr-qp.json / radarr-qp.json)
tech_stack:
  added: []
  patterns:
    - bash + python3 urllib heredoc for dev-time catalog production (no new deps)
    - committed static JSON assets as build-time catalog (SC#2 pattern)
    - OUT_DIR passed via shell export to python3 heredoc (not __file__)
key_files:
  created:
    - tools/scripts/fetch-trash-metadata.sh
    - tools/arrconf-ui/web/src/assets/trash-metadata/sonarr-cf.json
    - tools/arrconf-ui/web/src/assets/trash-metadata/radarr-cf.json
    - tools/arrconf-ui/web/src/assets/trash-metadata/sonarr-qp.json
    - tools/arrconf-ui/web/src/assets/trash-metadata/radarr-qp.json
    - tools/arrconf-ui/web/src/assets/trash-metadata/recyclarr-sonarr.json
    - tools/arrconf-ui/web/src/assets/trash-metadata/recyclarr-radarr.json
    - tools/arrconf-ui/web/src/assets/trash-metadata/manifest.json
    - tools/arrconf-ui/web/src/assets/trash-metadata/README.md
  modified: []
decisions:
  - "D-07/D-08: Baked catalog approach confirmed — no runtime GitHub calls; SHAs pinned in script and recorded in manifest"
  - "Python OUT_DIR path via shell export (not __file__) — correct pattern for python3 stdin heredoc"
metrics:
  duration_seconds: 488
  completed_date: "2026-05-30"
  tasks_completed: 2
  files_created: 9
  files_modified: 0
---

# Phase 27 Plan 01: TRaSH/Recyclarr Baked Catalog — Summary

**One-liner:** Committed TRaSH CF/QP + Recyclarr static JSON catalog (235+240 CFs, 19+36 QPs, 34+64 Recyclarr templates) at pinned SHAs via a reproducible dev-time fetch script.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write fetch-trash-metadata.sh dev-time script | 5023f26 | tools/scripts/fetch-trash-metadata.sh |
| 1-fix | Fix OUT_DIR env pass to python3 heredoc | 0f43e5f | tools/scripts/fetch-trash-metadata.sh |
| 2 | Run fetch script + commit baked catalog + README | f3b9bc2 | 8 files in trash-metadata/ |

## What Was Built

A dev-time shell script (`tools/scripts/fetch-trash-metadata.sh`) that:
- Fetches TRaSH-Guides CF/QP files from `raw.githubusercontent.com` at a pinned 40-char SHA (no full clone)
- Fetches Recyclarr `includes.json` at a pinned SHA
- Transforms CF entries to `{trash_id, name, default_score}`, QP entries to full baked shape with `items[]`, Recyclarr entries verbatim `{id, template}`
- Writes 6 catalog JSON files + `manifest.json` (SHA + counts + timestamp) to `tools/arrconf-ui/web/src/assets/trash-metadata/`
- Supports `--dry-run`, tool guards for `curl`+`python3`, exit codes 0/1/2

The 7 JSON assets are now committed (SHA-pinned, ~160 KB total) and ready for Phase 27 Plans 02-04 picker components.

## Baked Catalog Counts (at TRaSH SHA `1ef7baa5`, Recyclarr SHA `505c1e56`)

| Catalog | Count | Verification |
|---------|-------|-------------|
| sonarr-cf.json | 235 | >= 200 required |
| radarr-cf.json | 240 | >= 200 required |
| sonarr-qp.json | 19 | >= 15 required |
| radarr-qp.json | 36 | >= 30 required |
| recyclarr-sonarr.json | 34 | == 34 expected |
| recyclarr-radarr.json | 64 | == 64 expected |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `__file__` undefined in `python3 - <<'PY'` heredoc**
- **Found during:** Task 2 (first run of fetch script produced empty trash-metadata/ dir)
- **Issue:** `os.path.abspath(__file__)` fails in stdin-mode Python heredoc — `__file__` is not set; the script computed `out_dir` incorrectly (based on non-existent `__file__`) and the mkdir + writes silently went to the wrong path.
- **Fix:** Added `export TRASH_SHA RECYCLARR_SHA OUT_DIR` before the heredoc; Python script reads `os.environ["OUT_DIR"]` directly instead of deriving from `__file__`.
- **Files modified:** `tools/scripts/fetch-trash-metadata.sh`
- **Commit:** `0f43e5f`

## Validation Results

All acceptance criteria pass:
- `bash -n` on script: OK
- Both pinned SHAs in script: OK
- `command -v curl` and `command -v python3` guards: OK
- No `git clone` in script: OK
- Executable bit set: OK
- All 7 JSON files parse: OK
- `manifest.counts.radarr_recyclarr == 64` and `sonarr_recyclarr == 34`: OK
- `sonarr-cf.json` structure (trash_id, name, default_score on all entries): OK
- `sonarr-qp.json` structure (trash_id, items on all entries): OK
- `fr-vff` not in sonarr-cf.json (local CFs not baked): OK
- No `description` field in recyclarr-sonarr.json (research correction #1): OK
- `README.md` exists and mentions `fetch-trash-metadata.sh`: OK
- `charts/arr-stack/values.yaml` unchanged: OK (co-bump exception for this phase)

## Threat Surface Scan

No new threat surface beyond what the plan's threat model already documents:
- T-27-01 mitigated: both SHAs pinned as 40-char literals in script + manifest
- T-27-03 mitigated: per-file fetch via raw URLs, no full clone
- T-27-04 mitigated: `json.load` validates parse; transform whitelists fields; unknown keys dropped
- No runtime GitHub calls — all files are committed static assets

## Self-Check: PASSED

Files exist:
- tools/scripts/fetch-trash-metadata.sh — FOUND (commit 5023f26 + 0f43e5f)
- tools/arrconf-ui/web/src/assets/trash-metadata/sonarr-cf.json — FOUND (commit f3b9bc2)
- tools/arrconf-ui/web/src/assets/trash-metadata/radarr-cf.json — FOUND (commit f3b9bc2)
- tools/arrconf-ui/web/src/assets/trash-metadata/sonarr-qp.json — FOUND (commit f3b9bc2)
- tools/arrconf-ui/web/src/assets/trash-metadata/radarr-qp.json — FOUND (commit f3b9bc2)
- tools/arrconf-ui/web/src/assets/trash-metadata/recyclarr-sonarr.json — FOUND (commit f3b9bc2)
- tools/arrconf-ui/web/src/assets/trash-metadata/recyclarr-radarr.json — FOUND (commit f3b9bc2)
- tools/arrconf-ui/web/src/assets/trash-metadata/manifest.json — FOUND (commit f3b9bc2)
- tools/arrconf-ui/web/src/assets/trash-metadata/README.md — FOUND (commit f3b9bc2)
