---
phase: 05-reconciler-qbittorrent-split-tv-anime-family
plan: "07"
subsystem: chart-config
tags: [chart, arrconf-yml, configarr-yml, values-yaml, pytest, helm-lint]
dependency_graph:
  requires: [05-02, 05-06]
  provides: [declarative-phase5-chart-surface]
  affects: [cluster-configmap-arrconf, cluster-configmap-configarr, arrconf-cronjob-args]
tech_stack:
  added: [jsonschema>=4.26.0]
  patterns: [pydantic-json-schema-validation, yaml-shape-assertion, helm-lint-gate]
key_files:
  created:
    - tools/arrconf/tests/test_arrconf_yml_validates.py
    - tools/arrconf/tests/test_configarr_three_profiles.py
  modified:
    - charts/arr-stack/files/arrconf.yml
    - charts/arr-stack/files/configarr.yml
    - charts/arr-stack/values.yaml
    - tools/arrconf/pyproject.toml
    - tools/arrconf/uv.lock
decisions:
  - "YAML uses tag_labels (not tags) for string labels in download_clients — resolves to int IDs at reconcile time"
  - "Radarr Anime quality profile hand-rolled (no TRaSH French Anime template for Radarr, Q9/A6)"
  - "values.schema.json unchanged — single-line args string change does not affect structural schema"
  - "kubeconform not locally installed — helm lint + helm template (rendering 2069 lines) confirmed chart validity"
  - "jsonschema added as explicit pyproject.toml dependency (was missing from original requirements)"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-14T12:02:09Z"
  tasks: 4
  files_changed: 7
---

# Phase 5 Plan 07: Chart-Side Phase 5 Declarative Surface Summary

Phase 5 chart config shipped: arrconf.yml (6 qBit categories + Sonarr/Radarr split), configarr.yml (3 quality profiles per instance — MULTi.VF + Anime + Family), values.yaml (D-05-ARGS-01 args bump), and 2 new test modules providing CI-enforced invariant coverage.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 7.1 | Extend arrconf.yml with qbittorrent + Sonarr/Radarr Phase 5 | c96c63e | charts/arr-stack/files/arrconf.yml |
| 7.2 | Extend configarr.yml with Anime + Family profiles | c6ec4ab | charts/arr-stack/files/configarr.yml |
| 7.3 | Bump values.yaml args + regen schemas | 5a213aa + a5b4d33 | charts/arr-stack/values.yaml, schemas/arrconf-schema.json |
| 7.4 | Author test_arrconf_yml_validates.py + test_configarr_three_profiles.py | 0ce3368 | tools/arrconf/tests/test_*.py |

## Artifact Details

### arrconf.yml (341 lines, +297 from 44-line baseline)

Full Phase 5 declarative scope:
- **qbittorrent.main**: 6 categories (sonarr-tv/anime/family + radarr-movies/anime/family), each with explicit `savePath` (Pitfall 3). `preferences.enable: false` (opt-in off).
- **sonarr.main**: 3 tags (tv/anime/family), 3 root_folders (/media/series+anime+family), 3 download_clients each with `tag_labels` + `tvCategory` field, 4 remote_path_mappings (/data/complete/ + /data/series/ + /data/anime/ + /data/family/), `series_tags.default_tag: tv`.
- **radarr.main**: 3 tags (movies/anime/family), 3 root_folders (/media/films kept + /media/films-anime + /media/films-family), 3 download_clients each with `tag_labels` + `movieCategory` field, 4 remote_path_mappings (/data/complete/ + /data/films/ + /data/films-anime/ + /data/films-family/), `movie_tags.default_tag: movies`.
- **prowlarr.main**: apps block with Sonarr + Radarr app entries (preserved from Phase 3).
- D-05-PATHS-01 honored: `radarr-movies.savePath = /data/films` (not /data/movies).
- Pitfall 6 preserved: all remotePath + localPath values end with `/`.

### configarr.yml (3 profiles × 2 instances)

Per D-05-CONFIGARR-01 + D-05-FAM-01:
- **Sonarr.main**: MULTi.VF (unchanged) + Anime (hand-rolled HD 1080p scope) + Family (byte-equivalent clone of MULTi.VF).
- **Radarr.main**: Same 3 profiles — Radarr Anime is hand-rolled (no TRaSH French Anime Radarr template available, Q9/A6 resolution).
- **VOSTFR explicit-score per profile (Q5 resolution)**:
  - MULTi.VF: `score: -10000` (VOSTFR banned for TV/movies)
  - Anime: `score: 50` (VOSTFR allowed for anime — fansub quality)
  - Family: `score: -10000` (clone of MULTi.VF treatment)
- fr-vff/vfi/vfq/multi and fr-mhd/x265-hd: assigned to all 3 profiles with default scores.

### values.yaml (1-line change, D-05-ARGS-01)

```diff
-            - "sonarr,radarr,prowlarr"   # D-04-CRON-03
+            - "sonarr,radarr,prowlarr,qbittorrent"   # D-05-ARGS-01
```

### schemas/arrconf-schema.json

Regenerated via `arrconf schema-gen`. Output is idempotent — no model changes since Plan 02. `diff -q` gate passes.

### Test files (11 new tests total)

**test_arrconf_yml_validates.py** (7 tests):
- `test_files_exist` — path sanity check
- `test_arrconf_yml_validates_against_pydantic` — full RootConfig round-trip assertion
- `test_arrconf_yml_validates_against_json_schema` — JSON Schema validation via jsonschema
- `test_arrconf_yml_all_remote_path_mappings_end_with_slash` — Pitfall 6 invariant (8 RPMs total)
- `test_arrconf_yml_radarr_movies_category_uses_films_path` — D-05-PATHS-01 dispositive
- `test_arrconf_yml_all_qbit_categories_have_explicit_save_path` — Pitfall 3 invariant
- `test_arrconf_yml_prowlarr_apps_declared` — Sonarr + Radarr app entries present

**test_configarr_three_profiles.py** (4 tests):
- `test_three_profiles_per_instance` — 3 profiles per Sonarr + Radarr instance
- `test_family_clone_of_multivf` — byte-equal deep compare (name excluded)
- `test_vostfr_score_differs_per_profile` — MULTi.VF=-10000, Anime=+50, Family=-10000
- `test_no_quality_profile_named_anime_or_family_before_phase_5_baseline` — R-06 guard (PASSED: snapshot confirmed no pre-existing profiles)

## CI Gate Results

```
pytest:     196 passed (full suite)
coverage:   83.64% (threshold 70%)
ruff check: CLEAN
ruff format: 58 files already formatted
mypy:       Success: no issues found in 40 source files
helm lint:  1 chart(s) linted, 0 chart(s) failed ([INFO] Chart.yaml: icon is recommended)
helm template: renders 2069 lines (chart valid)
check-renovate-annotations.sh: OK: all repository: lines have renovate annotations
schema-gen idempotence: diff -q /tmp/s.json schemas/arrconf-schema.json (MATCH)
arrconf.yml validates against JSON schema: OK
```

kubeconform not installed locally — CI workflow runs it via GitHub Actions on every PR. Helm lint + helm template confirms structural validity of the chart.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] YAML download_clients use `tag_labels` not `tags` for string labels**
- **Found during:** Task 7.1
- **Issue:** RESEARCH.md Pattern 4 (line 578) showed `tags: [tv]` as string labels, but the pydantic model declares `tags: list[int]` (integer IDs) and `tag_labels: list[str]` (string labels, excluded from API calls). Using `tags: [tv]` would cause a pydantic validation error.
- **Fix:** Used `tag_labels: [tv]` / `[anime]` / `[family]` in the YAML as confirmed by test fixtures and the `_resolve_download_client_tag_labels` helper.
- **Files modified:** charts/arr-stack/files/arrconf.yml
- **Commit:** c96c63e

**2. [Rule 2 - Missing dependency] jsonschema not in pyproject.toml**
- **Found during:** Task 7.3
- **Issue:** `jsonschema` was listed in pyproject.toml in the Read context (already reflected post-`uv add`) but was not present in the original HEAD version. `uv add jsonschema` added it.
- **Fix:** Added `jsonschema>=4.26.0` to `[project.dependencies]` in pyproject.toml.
- **Files modified:** tools/arrconf/pyproject.toml, tools/arrconf/uv.lock
- **Commit:** a5b4d33

**3. [Rule 3 - Documentation deviation] Radarr Anime profile hand-rolled**
- **Found during:** Task 7.2
- **Issue:** Plan proposed considering `sonarr-v4-quality-profile-1080p-french-anime-multi` recyclarr template for Sonarr Anime, and Q9/A6 caveat said Radarr French Anime template may not exist. Per the research, Radarr does not have a TRaSH French Anime template.
- **Fix:** Hand-rolled Anime profile for both Sonarr AND Radarr (same HD 1080p scope as MULTi.VF). Documented in configarr.yml comments and SUMMARY. No structural difference — qualities block is identical to MULTi.VF; only the name + VOSTFR score differ.
- **Files modified:** charts/arr-stack/files/configarr.yml

## Known Stubs

None. All data sources are wired. The arrconf.yml declares the full declarative scope that the reconciler will apply on next run.

## Threat Flags

None identified beyond the plan's threat register (T-05-CATPATH, T-05-CONTENT all mitigated by tests).

## Self-Check: PASSED

- `charts/arr-stack/files/arrconf.yml` exists: FOUND
- `charts/arr-stack/files/configarr.yml` exists: FOUND
- `charts/arr-stack/values.yaml` contains `sonarr,radarr,prowlarr,qbittorrent`: FOUND
- `tools/arrconf/tests/test_arrconf_yml_validates.py` exists: FOUND
- `tools/arrconf/tests/test_configarr_three_profiles.py` exists: FOUND
- All task commits verified via `git log --oneline -8`
