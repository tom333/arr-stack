---
phase: "07"
plan: "02"
subsystem: arrconf
tags: [pydantic, config, jellyfin, json-schema, phase7]
dependency_graph:
  requires: [07-01]
  provides: [07-02]
  affects: [07-04, 07-05]
tech_stack:
  added: []
  patterns:
    - "JellyfinUserPolicy with Field(exclude=True) on 2 OpenAPI-required provider IDs (Pitfall 6)"
    - "JellyfinServerConfiguration 7-field allowlist with extra=allow for full-replace safety"
    - "4 Jellyfin Section models with extra=forbid for YAML typo detection"
    - "RootConfig.jellyfin: dict[str, JellyfinInstance] flat-root convention"
key_files:
  created:
    - tools/arrconf/arrconf/resources/jellyfin/__init__.py
    - tools/arrconf/arrconf/resources/jellyfin/library.py
    - tools/arrconf/arrconf/resources/jellyfin/user_policy.py
    - tools/arrconf/arrconf/resources/jellyfin/server_config.py
    - tools/arrconf/arrconf/resources/jellyfin/plugin.py
  modified:
    - tools/arrconf/arrconf/config.py
    - tools/arrconf/arrconf/settings.py
    - tools/arrconf/tests/test_config.py
    - schemas/arrconf-schema.json
decisions:
  - "JellyfinUserPolicy.BlockedChannels + BlockedMediaFolders + EnableLyricManagement + IsDisabled + IsHidden added from live baseline (users.json) beyond the research-time allowlist — extra=allow already covered forward-compat but explicit fields are cleaner"
  - "JellyfinServerConfigSection stores snake_case fields (ui_culture, metadata_country_code, etc.) while JellyfinServerConfiguration stores PascalCase (UICulture, etc.) — they are separate models: one for YAML parsing, one for API body generation. Plan 07-04 maps between them."
  - "JellyfinServerConfiguration not imported in config.py — it is a resource model used by the reconciler (Plan 07-04), not needed at the config layer. Import removed to avoid F401."
metrics:
  duration: "~9 minutes"
  completed_date: "2026-05-17"
  tasks_completed: 3
  files_created: 5
  files_modified: 4
  tests_added: 2
  tests_total: 23
---

# Phase 7 Plan 02: Jellyfin Pydantic Models + Config Integration + JSON Schema Summary

Pydantic type-layer foundation for Plan 07-04 (reconciler) and Plan 07-05 (chart YAML wiring). 4 resource modules under `arrconf/resources/jellyfin/` + 4 Section models + `JellyfinInstance` in `config.py` + `JELLYFIN_API_KEY` in `settings.py` + JSON Schema regenerated.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 2.1 | Create 4 pydantic resource modules | 6c050c5 | `resources/jellyfin/{__init__,library,user_policy,server_config,plugin}.py` |
| 2.2 | Extend config.py + settings.py | 6c050c5 | `arrconf/config.py`, `arrconf/settings.py` |
| 2.3 | Tests + JSON Schema regen | 6c050c5 | `tests/test_config.py`, `schemas/arrconf-schema.json` |

## Pydantic Models Created

### 1. JellyfinLibrary (`resources/jellyfin/library.py`)

Writable allowlist (D-07-LIB-02 scope):
- `name: str` — match key (NOT ItemId)
- `collection_type: str` — "tvshows" | "movies"
- `paths: list[str]` — PathInfos[].Path desired set

Associated: `PathInfo(Path: str)` — nested model for POST body shape.

`extra="allow"` for forward-compat.

### 2. JellyfinUserPolicy (`resources/jellyfin/user_policy.py`)

**2 excluded fields (Pitfall 6 / D-07-CREDS-01):**
- `AuthenticationProviderId: str | None = Field(default=None, exclude=True)` — OpenAPI-required but NEVER from YAML
- `PasswordResetProviderId: str | None = Field(default=None, exclude=True)` — idem

**~35 writable fields from baseline** (including baseline-discovered additions):
- `IsAdministrator`, `IsDisabled`, `IsHidden`, `EnableContentDeletion`, `EnableRemoteAccess`
- `EnableLiveTvManagement`, `EnableLiveTvAccess`, `EnableMediaPlayback`
- `EnableAudioPlaybackTranscoding`, `EnableVideoPlaybackTranscoding`, `EnablePlaybackRemuxing`
- `ForceRemoteSourceTranscoding`, `EnableContentDownloading`, `EnableSyncTranscoding`
- `EnableMediaConversion`, `EnableLyricManagement`, `EnabledDevices`, `EnableAllDevices`
- `EnabledChannels`, `EnableAllChannels`, `EnabledFolders`, `EnableAllFolders`
- `InvalidLoginAttemptCount`, `LoginAttemptsBeforeLockout`, `MaxActiveSessions`
- `EnablePublicSharing`, `BlockedTags`, `AllowedTags`, `BlockedChannels`, `BlockedMediaFolders`
- `EnableUserPreferenceAccess`, `AccessSchedules`, `BlockUnratedItems`
- `EnableRemoteControlOfOtherUsers`, `EnableSharedDeviceControl`
- `EnableCollectionManagement`, `EnableSubtitleManagement`
- `SyncPlayAccess`, `RemoteClientBitrateLimit`

`extra="allow"` for forward-compat.

### 3. JellyfinServerConfiguration (`resources/jellyfin/server_config.py`)

**7-field allowlist (D-07-CONFIG-01):**
- `UICulture: str = "fr"`
- `MetadataCountryCode: str = "FR"`
- `PreferredMetadataLanguage: str = "fr"`
- `ActivityLogRetentionDays: int = 30`
- `LogFileRetentionDays: int = 3`
- `ServerName: str = "jellyfin"`
- `PluginRepositories: list[PluginRepository] = []`

`extra="allow"` — 49 non-allowlist fields flow through the reconciler-side GET→merge→POST (Pitfall 1).

Associated: `PluginRepository(Name, Url, Enabled=True)`.

### 4. PluginEntry (`resources/jellyfin/plugin.py`)

- `name: str` — match key (D-07-PLUGINS-01)
- `id: str | None = None` — operator fallback when Name ambiguous

`extra="allow"`.

## Config Models Added

### config.py additions

4 new Section models (all with `extra="forbid"` for YAML typo detection — T-07-MODEL-TYPO):

| Model | Fields |
|-------|--------|
| `JellyfinLibrariesSection` | `enable=True`, `prune=False`, `items: list[JellyfinLibrary]` |
| `JellyfinUsersSection` | `enable=True`, `prune=False`, `admin: JellyfinUserPolicy` |
| `JellyfinServerConfigSection` | `enable=True`, 7 snake_case fields, `plugin_repositories` |
| `JellyfinPluginsSection` | `enable=True`, `required: list[PluginEntry]` |

`JellyfinInstance(extra="forbid")`: `base_url` + 4 sections.

`RootConfig.jellyfin: dict[str, JellyfinInstance] = Field(default_factory=dict)`.

### settings.py additions

```python
jellyfin_api_key: SecretStr | None = None  # JELLYFIN_API_KEY (Phase 7, D-07-AUTH-01)
```

## Reconciler Re-injection Contract (Pitfall 6)

The `Field(exclude=True)` on `AuthenticationProviderId` + `PasswordResetProviderId` is the **FIRST line of defense** — operator-authored values in YAML cannot leak into the POST body.

Plan 07-04 (reconciler) implements the **SECOND line of defense**: before calling `POST /Users/{id}/Policy`, it fetches `GET /Users/{id}` from the cluster and re-injects:
```python
cluster_policy["AuthenticationProviderId"]  # preserved from server
cluster_policy["PasswordResetProviderId"]   # preserved from server
```

This mirrors the Seerr `apiKey` pattern (D-06-CREDS-01, `seerr.py:132-149`).

## Tests Added

| Test | What it asserts |
|------|-----------------|
| `test_root_config_accepts_jellyfin_block` | Full canonical YAML parses to correct RootConfig structure (all 4 sections) |
| `test_jellyfin_user_policy_excludes_required_providerids_from_dump` | AuthenticationProviderId + PasswordResetProviderId NOT in model_dump() — Pitfall 6 enforcement |

All 23 test_config.py tests pass. 4 test_schema_gen.py tests pass including the CI drift gate.

## JSON Schema Regen

Schema regenerated: `schemas/arrconf-schema.json`.

New definitions in `$defs`: `JellyfinInstance`, `JellyfinLibrariesSection`, `JellyfinLibrary`, `JellyfinPluginsSection`, `JellyfinServerConfigSection`, `JellyfinUserPolicy`, `JellyfinUsersSection`, `PluginEntry`, `PluginRepository`, `PathInfo`.

New top-level property: `properties.jellyfin.additionalProperties.$ref: "#/$defs/JellyfinInstance"`.

REQ-yaml-autocomplete satisfied — VS Code will offer `jellyfin:` completion with all fields documented.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Additional Policy fields from live baseline**
- **Found during:** Task 2.1
- **Issue:** The RESEARCH §716-729 allowlist was missing some Policy fields present in `snapshots/baseline-2026-05-07/jellyfin/users.json`: `BlockedChannels`, `BlockedMediaFolders`, `EnableLyricManagement`, `IsDisabled`, `IsHidden`.
- **Fix:** Added these 5 fields to `JellyfinUserPolicy` with appropriate defaults. `extra="allow"` already covered forward-compat but explicit fields are better for documentation and type safety.
- **Files modified:** `tools/arrconf/arrconf/resources/jellyfin/user_policy.py`
- **Commit:** 6c050c5

**2. [Rule 1 - Bug] Unused import JellyfinServerConfiguration in config.py**
- **Found during:** Task 2.2
- **Issue:** The plan instructed importing `JellyfinServerConfiguration` in `config.py` but it's not used there (it's a resource model for Plan 07-04, not needed at the config layer). Ruff F401 caught this.
- **Fix:** Removed the unused import — `JellyfinServerConfigSection` in config.py stores the 7 fields directly in snake_case (the YAML schema), while `JellyfinServerConfiguration` (resource model) is only used by the reconciler in Plan 07-04.
- **Files modified:** `tools/arrconf/arrconf/config.py`
- **Commit:** 6c050c5

**3. [Rule 2 - Missing] Import ordering**
- **Found during:** Task 2.2
- **Issue:** Ruff I001 flagged the jellyfin import block was placed AFTER qbittorrent imports (should be alphabetical: jellyfin before qbittorrent).
- **Fix:** Reordered imports alphabetically as per ruff requirements.
- **Files modified:** `tools/arrconf/arrconf/config.py`
- **Commit:** 6c050c5

## Known Stubs

None — all models are fully specified with concrete fields and defaults. No placeholder values.

## Threat Flags

No new security-relevant surface introduced (all pydantic models, no new network endpoints, no file access patterns).

## Wave 2 Readiness Signal

Plan 07-04 (reconciler implementation) has the type contracts it needs:
- `JellyfinLibrary` — name/collection_type/paths scope
- `JellyfinUserPolicy` — 35+ writable fields, 2 exclude=True provider IDs
- `JellyfinServerConfiguration` — 7-field allowlist with extra=allow pass-through
- `PluginEntry` — name + id fallback
- `JellyfinInstance` / `JellyfinServerConfigSection` — YAML-to-API mapping layer
- `Settings.jellyfin_api_key` — auth secret

Plan 07-03 (test fixtures) runs in parallel with no file overlap — both 07-02 and 07-03 must complete before 07-04 starts.

## Self-Check: PASSED

Files verified:
- FOUND: tools/arrconf/arrconf/resources/jellyfin/__init__.py
- FOUND: tools/arrconf/arrconf/resources/jellyfin/library.py
- FOUND: tools/arrconf/arrconf/resources/jellyfin/user_policy.py
- FOUND: tools/arrconf/arrconf/resources/jellyfin/server_config.py
- FOUND: tools/arrconf/arrconf/resources/jellyfin/plugin.py
- FOUND: tools/arrconf/arrconf/config.py (modified)
- FOUND: tools/arrconf/arrconf/settings.py (modified)
- FOUND: tools/arrconf/tests/test_config.py (modified)
- FOUND: schemas/arrconf-schema.json (regenerated)

Commits verified:
- FOUND: 6c050c5 feat(07-02): Jellyfin pydantic models + RootConfig.jellyfin + JSON Schema regen
