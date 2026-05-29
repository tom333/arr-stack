---
phase: 24-jellyfin-intro-skipper
plan: "01"
subsystem: arrconf
tags: [jellyfin, reconciler, chapter-extraction, plugin, pydantic, tdd]
dependency_graph:
  requires: []
  provides: [JFSKIP-01, JFSKIP-04]
  affects: [tools/arrconf/arrconf/reconcilers/jellyfin.py, charts/arr-stack/files/arrconf.yml]
tech_stack:
  added: []
  patterns:
    - _update_library_options() helper (mirrors _add_missing_paths() pattern)
    - IntroSkipperConfig model (extra="allow" leaf, PascalCase fields)
    - enable_chapter_image_extraction field propagation (generator → model → reconciler)
key_files:
  created:
    - tools/arrconf/tests/test_reconcilers_jellyfin_chapter_extraction.py
  modified:
    - tools/arrconf/arrconf/resources/jellyfin/plugin.py
    - tools/arrconf/arrconf/resources/jellyfin/library.py
    - tools/arrconf/arrconf/resources/jellyfin/__init__.py
    - tools/arrconf/arrconf/config.py
    - tools/arrconf/arrconf/generators/categories.py
    - tools/arrconf/arrconf/reconcilers/jellyfin.py
    - charts/arr-stack/files/arrconf.yml
    - charts/arr-stack/values.yaml
    - schemas/arrconf-schema.json
    - tools/arrconf/tests/test_arrconf_yml_validates.py
decisions:
  - "co-bump arrconf.image.tag 0.15.0 → 0.16.0 (minor: new feature per CLAUDE.md)"
  - "IntroSkipperConfig uses extra='allow' (forward-compat for new Jellyfin API fields)"
  - "_update_library_options() follows _add_missing_paths() pattern exactly (consistent helper shape)"
  - "enable_chapter_image_extraction defaults False in config/model, True in generator (uniform all 10 libs)"
metrics:
  duration: "8 minutes"
  completed_date: "2026-05-29"
  tasks_completed: 3
  files_modified: 10
  files_created: 1
---

# Phase 24 Plan 01: Jellyfin Intro Skipper Foundation Summary

Extended pydantic models + reconciler for chapter image extraction (JFSKIP-04) and registered Intro Skipper plugin repository in arrconf.yml (JFSKIP-01), with IntroSkipperConfig and PluginEntry install fields for Plan 02.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend pydantic models + categories generator | 92a8879 | plugin.py, library.py, config.py, generators/categories.py, __init__.py |
| 2 | Chapter-extraction reconciler logic + respx tests | 92a8879 | reconcilers/jellyfin.py, test_reconcilers_jellyfin_chapter_extraction.py |
| 3 | Register Intro Skipper plugin repo + chapter flag in arrconf.yml | 92a8879 | arrconf.yml, values.yaml, schemas/arrconf-schema.json |

## What Was Built

**JFSKIP-01 (D-03):** Intro Skipper plugin repository registered in `arrconf.yml` under `jellyfin.main.server_config.plugin_repositories`. Uses the existing set-by-URL path (`_server_config_equivalent`), fully idempotent on second run. No new reconciler code needed.

**JFSKIP-04 (D-06):** `EnableChapterImageExtraction=true` flows through the full chain:
1. `generate_jellyfin_libraries()` emits `enable_chapter_image_extraction=True` on all 10 Category libraries.
2. `_create_library()` POST body now carries `{"LibraryOptions": {"EnableChapterImageExtraction": True}}` when the flag is set.
3. New `_update_library_options()` helper handles existing libraries via `POST /Library/VirtualFolders/LibraryOptions` when the cluster value drifts from desired (idempotent no-op when already correct, dry-run safe).

**Model extensions:**
- `IntroSkipperConfig` model: `AutoSkip=False`, `AutoSkipCredits=False`, `MaxParallelism=1` (respects PROJECT.md Out of Scope).
- `PluginEntry` gains `install_guid`, `install_version`, `install_repo_url`, `config` fields (all optional, backward-compatible).
- `JellyfinLibrary.enable_chapter_image_extraction` (default False, extra="allow").
- `JellyfinLibrariesSection.enable_chapter_image_extraction` (default False, extra="forbid").

## Verification

```
cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf
→ All checks passed

cd tools/arrconf && uv run pytest tests/test_reconcilers_jellyfin_chapter_extraction.py -q
→ 4 passed

cd tools/arrconf && uv run pytest tests/test_reconcilers_jellyfin.py -q
→ 23 passed (no regression)

cd tools/arrconf && uv run pytest -q --ignore=tests/test_phase10_idempotence_sweep.py
→ 457 passed (test_phase10_idempotence_sweep is pre-existing failure, unrelated)

RootConfig.model_validate(arrconf.yml) → parses cleanly with 2 plugin repos and chapter flag
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_arrconf_yml_validates_jellyfin to match new plugin_repositories count**
- **Found during:** Task 3 verification (full test suite run)
- **Issue:** `test_arrconf_yml_validates_jellyfin` asserted `len(plugin_repositories) == 1`, but we now have 2 entries (Jellyfin Stable + Intro Skipper)
- **Fix:** Updated assertion to check `len == 2` and verify both URLs are present; added `enable_chapter_image_extraction is True` assertion
- **Files modified:** `tools/arrconf/tests/test_arrconf_yml_validates.py`
- **Commit:** 92a8879

**2. [Rule 2 - Missing critical update] Regenerated schemas/arrconf-schema.json**
- **Found during:** Task 3 verification (full test suite run)
- **Issue:** `test_schema_committed_matches_regen` enforces schema is always regenerated after model changes
- **Fix:** Ran `arrconf schema-gen --output ../../schemas/arrconf-schema.json`
- **Files modified:** `schemas/arrconf-schema.json`
- **Commit:** 92a8879

### Pre-existing Test Failures (Out of Scope)

`tests/test_phase10_idempotence_sweep.py` (2 tests) — confirmed pre-existing failures before any changes in this plan (unmocked `qbittorrent` endpoint). Logged to deferred-items.

## Known Stubs

None — all model fields are fully wired. `enable_chapter_image_extraction=False` default in config/library model is intentional (generator always emits True, config default only matters for direct instantiation without generator).

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: T-24-01 (mitigated) | charts/arr-stack/files/arrconf.yml | Intro Skipper manifest URL committed as literal HTTPS string; set-by-URL idempotence prevents drift |
| threat_flag: T-24-03 (mitigated) | tools/arrconf/arrconf/reconcilers/jellyfin.py | LibraryOptions POST body contains only cluster GET ItemId + EnableChapterImageExtraction bool; respx tests assert exact shape |

## Self-Check: PASSED
