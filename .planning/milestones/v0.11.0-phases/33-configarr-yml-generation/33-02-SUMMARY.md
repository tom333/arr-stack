---
phase: 33-configarr-yml-generation
plan: "02"
subsystem: generators
tags: [configarr, generator, intent, quality-profiles, custom-formats, hard-cut, adr-5, cfgarr-01, cfgarr-02, cfgarr-03, cfgarr-04]
dependency_graph:
  requires:
    - 33-01 (generate_configarr_yml pure function + ProfileDefinition/CustomFormatRef models)
  provides:
    - intent.yml: profile_definitions (3 profiles) + configarr pass-through skeleton
    - configarr.yml: GENERATED read-only artifact from intent.yml
    - CI guard extended to cover configarr.yml drift
    - test_configarr_three_profiles.py docstring updated
  affects:
    - configarr.yml is now single-sourced from intent.yml (hard cut, no double-source)
    - charts/arr-stack/values.yaml: arrconf.image.tag already at 0.24.0 from 33-01
tech_stack:
  added: []
  patterns:
    - "Hard cut: configarr.yml goes from hand-edited to 100% GENERATED (Phase 32 precedent)"
    - "D-33-04 Option B: categories profile values stay general/anime/family; generator maps to configarr names"
    - "CFGARR-03 / T-33-01: api_key stored as quoted string in intent.yml; bare !env tag in generated file"
    - "D-33-07: configarr: block carries pass-through skeleton (no quality_profiles/custom_formats)"
    - "Co-bump already at 0.24.0 from 33-01 (minor: new generator feature)"
key_files:
  created: []
  modified:
    - charts/arr-stack/files/intent.yml (profile_definitions + configarr blocks added)
    - charts/arr-stack/files/configarr.yml (replaced by GENERATED version)
    - tools/arrconf/tests/test_configarr_three_profiles.py (docstring updated)
    - .github/workflows/tests.yml (CI guard message extended)
decisions:
  - "co-bump 0.24.0 already done in 33-01 (minor: new generator feature) — no additional bump needed"
  - "acceptance criteria profile:general count discrepancy: plan said 4 but original intent.yml had 5 (series, series-emilie, series-thomas, films, nouveaux-films); categories UNCHANGED"
  - "acceptance criteria name:MULTi.VF count discrepancy: plan said 2 but 8 in generated file (assign_scores_to entries also have name: MULTi.VF); structural tests all pass"
metrics:
  duration: "~20 minutes"
  completed_date: "2026-06-06"
  tasks_completed: 3
  files_created: 0
  files_modified: 4
---

# Phase 33 Plan 02: configarr.yml migration to GENERATED artifact Summary

**One-liner:** Hard cut from hand-edited configarr.yml to GENERATED read-only artifact via intent.yml profile_definitions + configarr pass-through skeleton, CI-gated against drift.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add profile_definitions + configarr blocks to intent.yml | 42b5478 | `charts/arr-stack/files/intent.yml` |
| 2 | Regenerate configarr.yml (hard cut), extend CI guard | bd8142f | `charts/arr-stack/files/configarr.yml`, `.github/workflows/tests.yml`, `tools/arrconf/tests/test_configarr_three_profiles.py` |
| 3 | Co-bump + triade + full suite | (already done in 33-01 commit 42543bf) | `charts/arr-stack/values.yaml` |

## What Was Built

### Task 1 — intent.yml profile_definitions + configarr blocks

Added two new top-level blocks to `charts/arr-stack/files/intent.yml`:

**`profile_definitions:`** — 3 profiles keyed by configarr names (MULTi.VF / Anime / Family):
- Each profile has a `body:` dict with QP fields (language: Any, reset_unmatched_scores, upgrade, min_format_score, quality_sort, qualities — identical across all 3)
- Each profile has `custom_formats:` with 3 groups: fr-vff/vfi/vfq/fr-multi (no score), fr-vostfr (score: -10000/50/-10000 per profile), fr-mhd/fr-x265-hd (no score)
- Family is an independent complete definition (D-33-03), not an alias

**`configarr:`** — pass-through skeleton:
- trashGuideUrl + recyclarrConfigUrl
- 7 customFormatDefinitions lifted verbatim from the prior configarr.yml
- sonarr.main: base_url, `api_key: "!env SONARR_API_KEY"` (quoted — safe loader), media_naming, quality_definition (8 tiers)
- radarr.main: same structure with RADARR_API_KEY and movie-specific quality_definition

Categories block UNCHANGED (D-33-04 Option B: profile values stay `general`/`anime`/`family`).

Verified: `load_intent()` parses clean; 3 profile_definitions; Anime VOSTFR score=50; MULTi.VF/Family score=-10000; 7 CFs; api_key == `"!env SONARR_API_KEY"`.

### Task 2 — GENERATED configarr.yml (hard cut)

Regenerated `charts/arr-stack/files/configarr.yml` via `arrconf generate`:
- GENERATED header on line 1
- Bare `!env SONARR_API_KEY` / `!env RADARR_API_KEY` tags (no quoted/expanded secrets — T-33-05 mitigated)
- 3 quality_profiles per instance (Anime / Family / MULTi.VF — alphabetically sorted)
- 3 custom_formats groups per instance matching the hand-edited structure
- `generate --check` exits 0 immediately after (idempotent — T-33-06/07 mitigated)

Structural equivalence confirmed: all 4 tests in `test_configarr_three_profiles.py` pass (3-profiles-per-instance, Family clone of MULTi.VF, VOSTFR per-profile scores, R-06 guard).

Updated `test_configarr_three_profiles.py` docstring to note the file is now a GENERATED artifact (Phase 33 hard cut) and that these tests validate the generated output.

Extended CI guard error message in `.github/workflows/tests.yml` to include `configarr.yml` in the drift error file list.

### Task 3 — Co-bump + triade + full suite

Co-bump was already performed by Plan 01 commit (42543bf): `0.23.0 → 0.24.0` (minor). The 33-01 SUMMARY explicitly frames it as "minor: new generator feature", so `0.24.0` is the correct final tag. The `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` annotation is intact.

Triade (from `tools/arrconf/`): `ruff format --check` (114 files clean) + `ruff check` (all clean) + `mypy arrconf` (no issues in 61 source files) — all pass.

Full suite: 554 passed, 2 skipped, 3 known flaky (pre-existing order-flakiness):
- `test_client_base_4xx_logging.py::test_4xx_emits_client_4xx_warning_with_body_excerpt`
- `test_client_base_4xx_logging.py::test_4xx_body_excerpt_truncated_at_500_chars`
- `test_reconcilers_jellyfin.py::test_reconcile_jellyfin_step_order_invariant`

All 3 pass in isolation (confirmed). Pre-existing respx state leakage, not a regression.

## Deviations from Plan

### Plan Acceptance Criteria Discrepancies (not bugs)

**1. [Note] profile:general count was 5, not 4**
- Plan acceptance criteria: `grep -c 'profile: general' == 4`
- Actual: 5 (series, series-emilie, series-thomas, films, nouveaux-films)
- Root cause: plan author miscounted; the original intent.yml (pre-plan-02) already had 5
- Fix: categories block UNCHANGED — no action needed, criteria was incorrect

**2. [Note] name:MULTi.VF count was 8, not 2**
- Plan acceptance criteria: `grep -v '^#' configarr.yml | grep -c 'name: MULTi.VF' == 2`
- Actual: 8 (2 in quality_profiles + 6 in assign_scores_to entries)
- Root cause: criteria was written expecting only profile names but assign_scores_to lists also use `name:` key
- Fix: structural tests pass (3 profiles per instance verified); no action needed

## Known Stubs

None. configarr.yml is fully populated from intent.yml; api_keys are bare `!env` tags (not stubs — intentionally unresolved at generate time, resolved at configarr apply time by K8s env injection).

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. Relevant threat mitigations from plan:
- T-33-05 (Information Disclosure — api_key leaked): MITIGATED. Generated file has bare `!env` tags; acceptance criteria grep confirms no `'!env` or `"!env` quoted forms.
- T-33-06 (Tampering — intent/configarr drift): MITIGATED. CI `generate --check` gate now explicitly lists `configarr.yml` in drift error message.
- T-33-07 (Repudiation — hand-edits to GENERATED file): MITIGATED. GENERATED header + CI drift gate; hard cut removes double-source ambiguity.

## Self-Check: PASSED
