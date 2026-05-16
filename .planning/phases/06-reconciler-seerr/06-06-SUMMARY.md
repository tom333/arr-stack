---
phase: 06-reconciler-seerr
plan: 06
subsystem: infra
tags: [arrconf, seerr, helm, yaml, content-routing, pydantic]

# Dependency graph
requires:
  - phase: 06-04
    provides: SeerrClient + reconcile_seerr function (consumes seerr.main config block)
  - phase: 06-05
    provides: content_tags step on Sonarr/Radarr (consumes content_routing.rules blocks)
  - phase: 06-01
    provides: anime-profile-id-lookup.txt evidence (activeAnimeProfileId=8)
  - phase: 06-02
    provides: RootConfig pydantic schema for seerr + content_routing (validated via test suite)
provides:
  - charts/arr-stack/files/arrconf.yml: seerr.main block + content_routing on sonarr.main + radarr.main
  - tools/arrconf/tests/test_arrconf_yml_validates.py: 3 Phase-6 assertions (10 total, all passing)
affects:
  - 06-07 (cluster apply — depends on this chart YAML)
  - CI helm lint + kubeconform (these gates now validate the Phase 6 additions)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Integer-ID YAML config (activeProfileId, animeTags) matched to cluster-local IDs from evidence + snapshots"
    - "Anti-leak pattern: apiKey intentionally absent from YAML schema; runtime preservation via D-06-CREDS-01"
    - "Pitfall 5 enforcement at chart layer: no Radarr anime rule, no Animation keyword in Sonarr family"

key-files:
  created: []
  modified:
    - charts/arr-stack/files/arrconf.yml
    - tools/arrconf/tests/test_arrconf_yml_validates.py

key-decisions:
  - "activeAnimeProfileId=8 from evidence/anime-profile-id-lookup.txt (Anime profile present, created by Phase 5 configarr)"
  - "Sonarr tag IDs sourced from snapshots/after-phase-5-2026-05-16: tv=2, anime=3, family=4"
  - "Radarr tag IDs from same snapshot: movies=2, anime=3, family=4"
  - "values.schema.json: Case 1 — validates Helm values.yaml only (NOT arrconf.yml); no regeneration needed"
  - "schemas/arrconf-schema.json: already current from Plan 06-02; regenerated identically (0 diff)"
  - "Radarr family keywords: ['Family'] only — TMDB taxonomy (not Kids/Children)"
  - "Sonarr family keywords: ['Family', 'Kids', 'Children'] — TVDB taxonomy"
  - "permissions=2 (ADMIN) not 8388608 (AUTO_REQUEST); defaultPermissions=32 (REQUEST)"

requirements-completed: [REQ-app-coverage]

# Metrics
duration: 30min
completed: 2026-05-16
---

# Phase 06 Plan 06: Chart YAML Summary

**Wired arrconf.yml with full Phase 6 declarative shape: seerr.main (4 resources) + content_routing on sonarr/radarr with Pitfall-5-compliant keyword lists, locked by 3 new pydantic validation tests.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-05-16T01:20Z
- **Completed:** 2026-05-16T01:50Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

### Task 6.1: Extend arrconf.yml with seerr.main + content_routing

Added to `charts/arr-stack/files/arrconf.yml`:

1. `sonarr.main.content_routing` block (lines 159-168):
   - `family` rule: keywords `["Family", "Kids", "Children"]` (Pitfall 5 — no Animation)
   - `anime` rule: keywords `["Anime"]` (TVDB first-class genre)

2. `radarr.main.content_routing` block (lines 324-331):
   - `family` rule: keywords `["Family"]` only (TMDB taxonomy)
   - NO anime rule (Pitfall 5 — TMDB has no Anime genre; Animation catches Pixar/Disney)

3. Top-level `seerr.main` block (lines 381-441):
   - `sonarr_service`: activeProfileId=6, activeAnimeProfileId=8, activeDirectory=/media/series,
     activeAnimeDirectory=/media/anime, tags=[2] (tv), animeTags=[3] (anime), tagRequests=true
   - `radarr_service`: activeProfileId=6, activeDirectory=/media/films, tags=[2] (movies),
     tagRequests=true, NO animeTags (Seerr schema absence, research-verified)
   - `users.admin`: permissions=2 (ADMIN per research bitmask, NOT 8388608=AUTO_REQUEST)
   - `main_settings`: defaultPermissions=32 (REQUEST), defaultQuotas movie+tv (7 days, 5 limit)

**Integer ID sources:**
| Field | Value | Source |
|-------|-------|--------|
| activeProfileId (Sonarr + Radarr) | 6 | snapshots/baseline-2026-05-07/seerr/settings_sonarr.json + live GET |
| activeAnimeProfileId | 8 | evidence/anime-profile-id-lookup.txt (Plan 06-01, Phase 5 configarr created) |
| sonarr_service.tags | [2] = tv | snapshots/after-phase-5-2026-05-16/sonarr/tag.json |
| sonarr_service.animeTags | [3] = anime | snapshots/after-phase-5-2026-05-16/sonarr/tag.json |
| radarr_service.tags | [2] = movies | snapshots/after-phase-5-2026-05-16/radarr/tag.json |

**Anime profile status:** FOUND. Profile id=8 "Anime" confirmed present in Sonarr
(created by Phase 5 configarr). Previous activeAnimeProfileId was 4 (HD-1080p) — now
correctly updated to 8.

### Task 6.2: Extend test_arrconf_yml_validates.py + schema check

Added 3 Phase-6 test functions to `tools/arrconf/tests/test_arrconf_yml_validates.py`:

1. `test_arrconf_yml_has_seerr_main_block`: validates seerr.main round-trips through pydantic;
   asserts permissions=2, defaultPermissions=32, activeAnimeProfileId is not None,
   activeAnimeDirectory=/media/anime, animeTags non-empty, tagRequests=True;
   asserts radarr_service has NO animeTags attribute (research-verified schema absence)

2. `test_arrconf_yml_sonarr_content_routing_has_family_and_anime`: asserts both rules present,
   no "Animation" keyword in family rule, family keywords == ["Family", "Kids", "Children"]

3. `test_arrconf_yml_radarr_content_routing_has_NO_anime_rule`: asserts no anime rule on Radarr,
   family rule present, family keywords == ["Family"]

**Test results:** 10/10 pass (7 pre-existing + 3 new Phase-6)

**values.schema.json:** Case 1 — validates Helm values.yaml chart settings only (image tags,
replicaCount, etc.); does NOT embed arrconf.yml schema. Already has a `seerr` property covering
the deployment controller. No regeneration needed.

**schemas/arrconf-schema.json:** Regenerated via `arrconf schema-gen` — output identical to HEAD
(0 diff). Plan 06-02 had already generated it with seerr + content_routing sections.

## Verification Results

| Check | Result |
|-------|--------|
| Anti-leak grep on arrconf.yml | CLEAN — 0 hits |
| top-level `seerr:` present | FOUND (line 381) |
| sonarr.main `content_routing:` | FOUND (line 159) |
| radarr.main `content_routing:` | FOUND (line 324) |
| permissions: 2 | FOUND (line 420) |
| defaultPermissions: 32 | FOUND (line 432) |
| activeAnimeProfileId: 8 | FOUND (line 390) |
| helm lint | 1 chart(s) linted, 0 chart(s) failed |
| kubeconform | Not installed locally — helm lint covers structural validation |
| pydantic RootConfig.model_validate | PASSED |
| JSON Schema validation (schemas/arrconf-schema.json) | PASSED |
| pytest tests/test_arrconf_yml_validates.py | 10/10 PASSED |
| ruff check + ruff format | CLEAN |

## Commits

| Commit | Files | Description |
|--------|-------|-------------|
| 7c97ef3 | charts/arr-stack/files/arrconf.yml, tools/arrconf/tests/test_arrconf_yml_validates.py | feat(06-06): chart YAML — seerr.main + content_routing on sonarr/radarr |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes

- The `values.schema.json` determination was Case 1 (validates Helm chart values.yaml, not
  arrconf.yml directly). No regeneration was needed or performed.
- `schemas/arrconf-schema.json` was regenerated but produced identical output — Plan 06-02
  had already generated it with the Phase 6 schema additions (seerr + content_routing).
- kubeconform is not installed in the local development environment; helm lint (which validates
  the Helm template against values.schema.json and Kubernetes API semantics) passed cleanly.
  CI runs kubeconform on PRs.
- The untracked `charts/arr-stack/charts/{alias}/` directories created during helm lint are
  local build artifacts from the multi-alias workaround (CLAUDE.md) — NOT committed (they were
  not in HEAD and are regenerated by CI).

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust
boundaries beyond what was declared in the plan's threat model (T-06-CREDS-LEAK mitigated:
apiKey absent from YAML; T-06-CONTENT mitigated: test_arrconf_yml_radarr_content_routing_has_NO_anime_rule).

## Self-Check: PASSED

- [x] charts/arr-stack/files/arrconf.yml exists with `seerr:` top-level block
- [x] tools/arrconf/tests/test_arrconf_yml_validates.py contains 3 new Phase-6 test functions
- [x] Commit 7c97ef3 exists in git log
- [x] Anti-leak: 0 apiKey hits
- [x] helm lint: 0 chart(s) failed
- [x] 10 tests pass
