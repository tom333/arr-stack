---
phase: 06
plan: 02
subsystem: arrconf/schema
tags: [pydantic, seerr, config-schema, json-schema, content-routing]
dependency_graph:
  requires: [06-01]
  provides: [seerr-pydantic-models, content-routing-config, rootconfig-seerr-field]
  affects: [06-03, 06-04, 06-05, 06-06]
tech_stack:
  added: []
  patterns: [pydantic-v2-field-exclusion, extra-allow-forward-compat, opt-in-enable-sections]
key_files:
  created:
    - tools/arrconf/arrconf/resources/seerr/__init__.py
    - tools/arrconf/arrconf/resources/seerr/sonarr_service.py
    - tools/arrconf/arrconf/resources/seerr/radarr_service.py
    - tools/arrconf/arrconf/resources/seerr/user.py
    - tools/arrconf/arrconf/resources/seerr/main_settings.py
  modified:
    - tools/arrconf/arrconf/config.py
    - tools/arrconf/tests/test_config.py
    - schemas/arrconf-schema.json
decisions:
  - "Field(exclude=True) on id, apiKey, activeProfileName, activeAnimeProfileName on all 4 Seerr models (T-06-Q1-COMPAT + T-06-CREDS-LEAK)"
  - "SeerrRadarrService has NO animeTags/activeAnimeDirectory/activeAnimeProfileId — research-verified Radarr absence (scope_directive #6)"
  - "permissions default=2 (ADMIN per research correction; 8388608 is AUTO_REQUEST not admin)"
  - "ContentRoutingSection.enable defaults to False (opt-in, matches HostConfigSection pattern D-03-04)"
  - "SeerrInstance has two required fields (sonarr_service, radarr_service); users + main_settings have defaults"
  - "SeerrSonarrServiceSection/SeerrRadarrServiceSection use extra=forbid (YAML typo guard); resource models use extra=allow (forward-compat)"
metrics:
  duration: 18m
  completed: "2026-05-16"
  tasks_completed: 3
  files_changed: 8
---

# Phase 6 Plan 02: Config Schema — Seerr + content_routing

4 Seerr pydantic resource models + SeerrInstance config class + ContentRoutingSection on Sonarr/Radarr + RootConfig.seerr dict + 4 tests + regenerated JSON Schema with ~640 lines added.

## What Was Built

### Task 2.1: 4 Seerr Pydantic Resource Models

**`SeerrSonarrService`** (20 fields):
- Excluded from `model_dump()`: `id`, `apiKey`, `activeProfileName`, `activeAnimeProfileName`
- Includes `animeTags: list[int]`, `activeAnimeProfileId`, `activeAnimeDirectory` (D-06-Q10-01 Sonarr-specific fields)

**`SeerrRadarrService`** (16 fields):
- Excluded from `model_dump()`: `id`, `apiKey`, `activeProfileName`
- NO `animeTags`/`activeAnime*` — research-verified absence on Seerr's Radarr-side settings

**`SeerrUser`** (7 writable + 16 excluded):
- Writable: `displayName`, `permissions`, `movieQuotaDays`, `movieQuotaLimit`, `tvQuotaDays`, `tvQuotaLimit`
- 16 read-only excluded fields: `id`, `email`, `plexUsername`, `jellyfinUsername`, `username`, `userType`, `plexId`, `jellyfinUserId`, `avatar`, `avatarETag`, `avatarVersion`, `createdAt`, `updatedAt`, `requestCount`, `warnings`, `recoveryLinkExpirationDate`, `settings`
- `permissions` default = `2` (ADMIN — research correction from CONTEXT.md's incorrect `8388608`)

**`SeerrMainSettings`** (scoped subset):
- `apiKey` excluded (Seerr's own API key, never to be written by arrconf)
- `DefaultQuota` + `DefaultQuotas` sub-models with `extra="forbid"`
- Scoped to `defaultPermissions` (default=32, REQUEST) + `defaultQuotas`

All 4 models: `extra="allow"` for forward-compat with Seerr minor releases.

### Task 2.2: config.py Extensions

**ContentRoutingRule + ContentRoutingSection** added (D-06-RETAG-01):
- `ContentRoutingSection.enable` defaults to `False` (opt-in, mirrors D-03-04 HostConfigSection pattern)
- Added to `SonarrInstance` and `RadarrInstance` (alphabetically before `download_clients`)

**SeerrSonarrServiceSection + SeerrRadarrServiceSection** (YAML-facing config sections):
- `extra="forbid"` for typo guard on arrconf.yml
- `apiKey` intentionally absent (D-06-CREDS-01: operator bootstraps once via Seerr UI)
- `SeerrSonarrServiceSection` has `animeTags`, `activeAnimeProfileId`, `activeAnimeDirectory`; `SeerrRadarrServiceSection` does NOT

**SeerrUsersSection + SeerrMainSettingsSection + SeerrInstance**:
- `SeerrInstance` requires `sonarr_service` + `radarr_service`; `users` + `main_settings` optional with defaults
- `SeerrUsersSection.enable` defaults to `True` (admin user reconciliation default-ON)
- `SeerrMainSettingsSection.enable` defaults to `True`

**RootConfig** extended:
- `seerr: dict[str, SeerrInstance] = Field(default_factory=dict)` added

### Task 2.3: Tests + JSON Schema

**4 new tests in `test_config.py`**:
1. `test_root_config_accepts_seerr_block` — full YAML load validation
2. `test_seerr_models_exclude_id_from_dump` — T-06-Q1-COMPAT + T-06-CREDS-LEAK assertion
3. `test_content_routing_section_defaults_disabled` — D-06-RETAG-01 opt-in default
4. `test_root_config_rejects_seerr_typo` — `extra="forbid"` typo guard

**`schemas/arrconf-schema.json`** regenerated:
- Added ~641 lines (1806 total vs ~1165 before)
- Contains `"seerr"` at root level and `"content_routing"` on Sonarr/Radarr instances
- VS Code autocomplete now covers `seerr.*` + `content_routing.*` fields

All 200 tests pass.

## Commits

| Task | Hash | Message |
|------|------|---------|
| 2.1 | 60b6ce2 | feat(06-02): add 4 Seerr pydantic resource models (Task 2.1) |
| 2.2 | 46559e5 | feat(06-02): extend config.py with SeerrInstance + ContentRoutingSection (Task 2.2) |
| 2.3 | ff10356 | feat(06-02): extend test_config.py + regenerate JSON Schema (Task 2.3) |

## Deviations from Plan

None — plan executed exactly as written.

The import line was slightly adjusted by ruff (split across lines for line length), but the logical content is identical.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes at trust boundaries beyond those already in the plan's `<threat_model>`. Both T-06-Q1-COMPAT and T-06-CREDS-LEAK mitigations are implemented at the pydantic type layer.

## Known Stubs

None — this plan is schema-only. No reconciler logic, no data sources, no UI rendering. All models are correctly structured for consumption by Plans 06-04 (SeerrClient) and 06-05 (content_tags step).

## Self-Check: PASSED
