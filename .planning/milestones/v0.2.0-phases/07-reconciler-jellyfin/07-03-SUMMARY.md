---
phase: 07
plan: 03
subsystem: arrconf-tests
tags: [jellyfin, fixtures, conftest, sanitization, phase7, wave1]
dependency_graph:
  requires: [07-01]
  provides: [jellyfin-test-fixtures, jellyfin-conftest-loaders]
  affects: [07-04]
tech_stack:
  added: []
  patterns: [fixture-sanitize-from-baseline, anti-leak-audit, conftest-fixture-loader]
key_files:
  created:
    - tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders.json
    - tools/arrconf/tests/fixtures/jellyfin/users.json
    - tools/arrconf/tests/fixtures/jellyfin/user_moi_full.json
    - tools/arrconf/tests/fixtures/jellyfin/system_configuration.json
    - tools/arrconf/tests/fixtures/jellyfin/plugins.json
  modified:
    - tools/arrconf/tests/conftest.py
decisions:
  - "library_virtualfolders.json sliced with jq to keep only Name/ItemId/CollectionType/Locations/LibraryOptions.PathInfos/RefreshStatus — TypeOptions arrays stripped (D-07-LIB-02 out-of-scope)"
  - "users.json stripped of Configuration block, LastLoginDate, LastActivityDate, LastAuthenticatedIpAddress, EnableAutoLogin — Policy kept verbatim (Plan 07-04 reconciler only touches Policy)"
  - "user_moi_full.json is a NEW synthetic fixture (no baseline analog) — jq-extracted from users.json baseline moi user with explicit ProviderIds set to Jellyfin default class names (Pitfall 6 contract)"
  - "system_configuration.json copied verbatim — 53 top-level keys preserved including all 7 allowlist keys + 46 non-allowlist keys for Pitfall 1 preservation test"
  - "plugins.json copied verbatim — 6 plugins, all Status=Active baseline; Plan 07-04 tests will mutate copies per test case"
  - "IP sniff matched plugin version strings (10.11.8.0 pattern) — confirmed false positives (Version field context), no real IPs present"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-17T01:49:25Z"
  tasks_completed: 2
  files_created: 5
  files_modified: 1
---

# Phase 7 Plan 03: Jellyfin Test Fixtures + conftest Loaders Summary

Wave 1 of Phase 7 — produced 5 sanitized JSON test fixtures from the `snapshots/baseline-2026-05-07/jellyfin/` baseline and wired 5 pytest fixture loaders in `tests/conftest.py`. No pydantic models, no reconciler logic — pure fixture infrastructure for Plan 07-04 to consume via respx mocks.

## What Was Built

### 5 Sanitized JSON Fixtures

| File | Size | Source | Key Sanitization |
|------|------|--------|-----------------|
| `library_virtualfolders.json` | 608 B | baseline slice | jq filter: Name/ItemId/CollectionType/Locations/LibraryOptions.PathInfos/RefreshStatus — TypeOptions arrays stripped |
| `users.json` | 3.7 KB | baseline slice | Configuration block removed; LastLoginDate/LastActivityDate/LastAuthenticatedIpAddress/PrimaryImageItemId/PrimaryImageTag/EnableAutoLogin stripped; Policy kept |
| `user_moi_full.json` | 1.7 KB | NEW (synthesized) | Extracted moi user from baseline; explicit Pitfall 6 ProviderIds set to Jellyfin default class names |
| `system_configuration.json` | 4.7 KB | baseline verbatim | Copied as-is — 53 keys preserved for Pitfall 1 full-replace preservation test |
| `plugins.json` | 1.9 KB | baseline verbatim | Copied as-is — 6 plugins all Status=Active |

### Sanitization Decisions Per File

**library_virtualfolders.json** — `jq` slice retains only the fields Plan 07-04 reconciler accesses: `Name` (match key), `ItemId` (read-only reference), `CollectionType` (read-only D-07-LIB-02), `Locations` (Pitfall 8 — reconciler IGNORES this field, test asserts PathInfos is used instead), `LibraryOptions.PathInfos` (source-of-truth for set-membership Pitfall 2 test), `RefreshStatus`. TypeOptions arrays were stripped — they bloat the fixture and are out of reconciler scope.

**users.json** — Dropped: `Configuration` (UI prefs — D-07-USERS-01 excludes), `LastLoginDate`/`LastActivityDate` (fixture rot + unnecessary timestamps), `LastAuthenticatedIpAddress` (PII — T-07-FIXTURE-PII mitigation), `PrimaryImageItemId`/`PrimaryImageTag` (avatar references — out of scope), `EnableAutoLogin` (not present in stripped shape). Kept: `Name`, `Id`, `ServerId`, `HasPassword`, `HasConfiguredPassword`, `HasConfiguredEasyPassword`, `Policy` (full — Plan 07-04 reconciler only touches Policy).

**user_moi_full.json (NEW)** — Synthesized from baseline `users.json` moi user (Id `82fd95db72904569b08d83271823ceaa`). The `Policy.AuthenticationProviderId` and `Policy.PasswordResetProviderId` fields are set to the literal Jellyfin default class names (`Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider` / `Jellyfin.Server.Implementations.Users.DefaultPasswordResetProvider`). These are class names in the Jellyfin codebase, NOT secrets. This establishes the Pitfall 6 re-injection test contract: Plan 07-04 reconciler test asserts these two values from the GET response appear VERBATIM in the POST body.

**system_configuration.json** — Copied verbatim. The baseline already has no secrets (no API keys, no tokens, no IPs). All 53 top-level keys preserved including: 7 allowlist keys (`UICulture`, `MetadataCountryCode`, `PreferredMetadataLanguage`, `ActivityLogRetentionDays`, `LogFileRetentionDays`, `ServerName`, `PluginRepositories`) + 46 non-allowlist keys. Pitfall 1 test contract requires these non-allowlist keys to be preserved in the merged POST body.

**plugins.json** — Copied verbatim. 6 plugins all `Status: "Active"` (AudioDB, Kodi Sync Queue, MusicBrainz, OMDb, Studio Images, TMDb). Baseline state. Plan 07-04 tests will create copies with one plugin's Status flipped to `"Disabled"` per test case to assert the Enable POST hits the correct URL.

### 5 pytest Fixture Loaders

Appended to `tests/conftest.py` after the existing Seerr block (line 244), mirroring the `seerr_*_fixture` pattern exactly:

```python
jellyfin_library_virtualfolders_fixture() -> list[dict[str, Any]]
jellyfin_users_fixture() -> list[dict[str, Any]]
jellyfin_user_moi_full_fixture() -> dict[str, Any]
jellyfin_system_configuration_fixture() -> dict[str, Any]
jellyfin_plugins_fixture() -> list[dict[str, Any]]
```

Each calls `_load_fixture("jellyfin/<file>.json")` and has a docstring referencing the relevant Pitfall (Pitfall 2 / 6 / 1 / 5).

## Anti-Leak Audit Output

```
# AccessToken / Bearer / api_key / MediaBrowser Token
$ grep -rE 'AccessToken|Bearer |...' tools/arrconf/tests/fixtures/jellyfin/
(0 hits)

# Long base64 strings
$ grep -rE '"[A-Za-z0-9+/]{40,}={0,2}"' tools/arrconf/tests/fixtures/jellyfin/ | grep -vE ...
(0 hits)

# IP-PII sniff
$ grep -rE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' tools/arrconf/tests/fixtures/jellyfin/
plugins.json: "Version": "10.11.8.0"  (and 5 similar — all version strings)
```

**Assessment: CLEAN.** The IP regex matched plugin version strings (e.g., `10.11.8.0`, `15.0.0.0`) which follow IP-like dotted-quad syntax. Confirmed as false positives — all matches are in `"Version"` fields, not IP-bearing fields (`CorsHosts`, `LastAuthenticatedIpAddress`, etc.). No real IPs present.

T-07-FIXTURE-LEAK mitigated: no AccessToken/Bearer/api_key patterns.
T-07-FIXTURE-PII mitigated: LastAuthenticatedIpAddress stripped from users.json, no real IPs in any fixture.

## Pitfall 6 Re-injection Contract

Established in `user_moi_full.json`:

```json
{
  "Policy": {
    "AuthenticationProviderId": "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider",
    "PasswordResetProviderId": "Jellyfin.Server.Implementations.Users.DefaultPasswordResetProvider",
    ...
  }
}
```

Verification:
```bash
jq -e '.Policy.AuthenticationProviderId | startswith("Jellyfin.Server")' user_moi_full.json  # true
jq -e '.Policy.PasswordResetProviderId | startswith("Jellyfin.Server")' user_moi_full.json   # true
```

Plan 07-04 reconciler test will: (1) mock GET /Users/{id} to return this fixture, (2) assert the POST /Users/{id}/Policy body contains `AuthenticationProviderId` and `PasswordResetProviderId` re-injected verbatim from the GET response. This validates the Pitfall 6 fix — pydantic `exclude=True` fields from the cluster GET must be re-injected into write bodies, not silently dropped.

## Pitfall 1 Preservation Test Contract

Established in `system_configuration.json` (53 top-level keys):

Plan 07-04 test will: (1) mock GET /System/Configuration to return this fixture, (2) build a merged body with 7-field YAML override, (3) assert POST /System/Configuration body contains BOTH the 7 overridden values AND the 46 non-allowlist keys from the GET response. This validates the Pitfall 1 fix — full-replace endpoints must preserve cluster fields outside the managed allowlist.

## Wave 2 Readiness Signal

Plan 07-04 reconciler tests now have:
- **Type contracts** (from Plan 07-02, parallel wave): pydantic models for all Jellyfin resource types
- **respx mock data** (this plan): 5 sanitized JSON fixtures covering all 4 GET endpoints Plan 07-04 mocks

Plan 07-04 is unblocked from both its wave 1 dependencies (07-02 + 07-03).

## Deviations from Plan

None — plan executed exactly as written. The IP-sniff false positive (version strings matching dotted-quad regex) was anticipated in the plan's threat model commentary and resolved without code changes.

## Self-Check

- `tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders.json` — FOUND
- `tools/arrconf/tests/fixtures/jellyfin/users.json` — FOUND
- `tools/arrconf/tests/fixtures/jellyfin/user_moi_full.json` — FOUND
- `tools/arrconf/tests/fixtures/jellyfin/system_configuration.json` — FOUND
- `tools/arrconf/tests/fixtures/jellyfin/plugins.json` — FOUND
- Commit `913340a` — FOUND

## Self-Check: PASSED
