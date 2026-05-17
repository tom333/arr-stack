---
phase: 07
plan: 05
subsystem: chart
tags: [jellyfin, chart, arrconf-yml, validation, wave-3]
dependency_graph:
  requires: [07-04]
  provides: [jellyfin-chart-section, jellyfin-cronjob-dispatch, jellyfin-ci-gate]
  affects: [charts/arr-stack, tools/arrconf/tests]
tech_stack:
  added: []
  patterns: [phase-comment-block, tdd-validation-test, pitfall-6-parse-gate]
key_files:
  created: []
  modified:
    - charts/arr-stack/files/arrconf.yml
    - charts/arr-stack/values.yaml
    - tools/arrconf/tests/test_arrconf_yml_validates.py
decisions:
  - "D-07-CHART-ARGS-01: extend --apps list to include jellyfin (avoids Phase 6 silent-skip repeat)"
  - "values.schema.json: NO-OP — args array has no enum constraint in Phase 4 schema"
  - "test_arrconf_yml_no_provider_ids_in_jellyfin_users: parse-level check (not raw text grep) because comment block cites field names for documentation purposes"
metrics:
  duration: "7m 31s"
  completed: "2026-05-17"
  tasks_completed: 3
  files_modified: 3
---

# Phase 7 Plan 05: Chart Cutover (Wave 3) Summary

Wave 3 chart cutover for Jellyfin reconciler — wires the arrconf YAML config, extends
the cluster CronJob `--apps` dispatch list, and installs the CI regression contract.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 5.1 | Append jellyfin.main block to arrconf.yml | 0b9f85d | charts/arr-stack/files/arrconf.yml |
| 5.2 | Extend values.yaml --apps list (D-07-CHART-ARGS-01) | 0b9f85d | charts/arr-stack/values.yaml |
| 5.3 | Add test_arrconf_yml_validates_jellyfin + Pitfall 6 gate | 0b9f85d | tools/arrconf/tests/test_arrconf_yml_validates.py |

All 3 tasks committed atomically in a single commit as specified by Task 5.3 step 6.

## What Was Built

### Task 5.1 — arrconf.yml jellyfin.main block (+106 lines)

Appended a `jellyfin:` top-level section after the `seerr:` block. The block contains:

1. **libraries** — 2 multi-path entries (Séries: tvshows + Films: movies); `prune: false`
   hardcoded per D-07-LIB-01. Paths: `/media/series`, `/media/anime`, `/media/family` and
   `/media/films`, `/media/films-anime`, `/media/films-family`.
2. **users.admin** — 27 Policy fields for the `moi` admin user; `prune: false` hardcoded
   per D-07-USERS-01. `AuthenticationProviderId` and `PasswordResetProviderId` are
   **intentionally absent** (Pitfall 6 — re-injected at reconcile-time from cluster GET).
3. **server_config** — 7-field allowlist per D-07-CONFIG-01: `ui_culture`, `metadata_country_code`,
   `preferred_metadata_language`, `activity_log_retention_days`, `log_file_retention_days`,
   `server_name`, `plugin_repositories` (1 entry: Jellyfin Stable official repo).
4. **plugins** — 6 required plugins per D-07-PLUGINS-01: TMDb, OMDb, MusicBrainz, AudioDb,
   Studio Images, Kodi Sync Queue.

**Comment block** (Phase 6 D-06-CHART-ARGS-01 + Phase 5 D-05-PATHS-01 discipline): cites
D-07-LIB-01, D-07-LIB-02, D-07-USERS-01, D-07-CONFIG-01, D-07-PLUGINS-01, D-07-ORDER-01,
Pitfalls 1, 2, 4, 5, 6, 7, and the Pitfall 6 intentional absence notice.

### Task 5.2 — values.yaml --apps list (1-line edit, D-07-CHART-ARGS-01)

Changed line 458 from:
```yaml
- "sonarr,radarr,prowlarr,qbittorrent,seerr"   # D-05-ARGS-01: ...
```
to:
```yaml
- "sonarr,radarr,prowlarr,qbittorrent,seerr,jellyfin"   # D-05-ARGS-01: ... ; Phase 7 adds jellyfin (D-07-INSTANCE-01)
```

This ensures the cluster CronJob dispatches the Jellyfin branch on next run. Without this,
the Jellyfin reconciler exists in the code but is silently skipped — exact repeat of
Phase 6 D-06-CHART-ARGS-01 which required hotfix commit `ff39507`.

### Task 5.3 — test_arrconf_yml_validates.py (+80 lines, 2 new tests)

**test_arrconf_yml_validates_jellyfin**: Full parse-through-pydantic test asserting:
- `base_url` exact value
- libraries: 2 items, names, collection_types, paths (3 each), `prune=False`
- users: `IsAdministrator=True`, `prune=False`
- server_config: `ui_culture="fr"`, `metadata_country_code="FR"`, retention days,
  plugin_repositories count and URL
- plugins: 6 required entries, TMDb + Kodi Sync Queue presence

**test_arrconf_yml_no_provider_ids_in_jellyfin_users**: Pitfall 6 parse-level gate
— loads YAML as Python dict and asserts `AuthenticationProviderId` and
`PasswordResetProviderId` do NOT appear in the `jellyfin.main.users.admin` block.

Note on implementation deviation: the plan specified a raw text grep for Pitfall 6.
However, the comment block in arrconf.yml itself cites these field names for documentation.
The raw grep would fail on the comment, not the YAML data. The fix was to use
`yaml.safe_load()` and check the parsed dict — same security guarantee, more accurate.

**values.schema.json**: NO-OP as confirmed. Phase 4 schema validates `args` as
`array[string]` with no enum constraint on content. No edit needed.

## Line Count Deltas

| File | Before | After | Delta |
|------|--------|-------|-------|
| charts/arr-stack/files/arrconf.yml | 434 | 540 | +106 |
| charts/arr-stack/values.yaml | 527 | 527 | +1 (1 line replaced) |
| tools/arrconf/tests/test_arrconf_yml_validates.py | 213 | 292 | +79 |
| charts/arr-stack/values.schema.json | unchanged | unchanged | 0 |

## Verification Results

```
helm lint charts/arr-stack/: 1 chart(s) linted, 0 chart(s) failed
pytest tests/test_arrconf_yml_validates.py: 12 passed
pytest tests/ (full suite): 271 passed
ruff check + ruff format --check: All checks passed
mypy: No issues found
```

## D-07-CHART-ARGS-01 Satisfied

`grep -E '"sonarr,radarr,prowlarr,qbittorrent,seerr,jellyfin"' charts/arr-stack/values.yaml`
returns exactly 1 match. The old 5-app line is fully replaced. Phase 6 silent-skip
pattern NOT repeated.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_arrconf_yml_no_provider_ids_in_jellyfin_users — raw text grep fails on comment**

- **Found during:** Task 5.3 test execution
- **Issue:** Plan specified `assert "AuthenticationProviderId" not in text` (raw file text).
  The comment block in arrconf.yml itself contains the string `AuthenticationProviderId`
  (to explain WHY it's absent from the YAML data). The raw text grep found the string in
  the comment and the test failed.
- **Fix:** Replaced raw text grep with `yaml.safe_load()` parse + dict key check on
  `jellyfin.main.users.admin`. This provides the same security guarantee (checks the
  actual YAML data, not comments) and is more accurate.
- **Files modified:** tools/arrconf/tests/test_arrconf_yml_validates.py
- **Commit:** 0b9f85d (folded into the same atomic commit)

## Wave 4 Readiness Signal

Plan 07-06 (cluster apply) can proceed. The chart changes in this plan are:
- `arrconf.yml`: jellyfin.main section fully wired to Plan 07-04 reconciler
- `values.yaml`: CronJob will dispatch Jellyfin on next run
- CI tests green: `test_arrconf_yml_validates_jellyfin` + Pitfall 6 gate lock in correctness

The auto-tag mechanism (mathieudutour/github-tag-action in `chart-lint.yml`) will trigger
on merge to main → new semver patch tag → my-kluster Renovate PR → ArgoCD sync.

## Known Stubs

None — all data values in the jellyfin block are concrete (real cluster URLs, real paths,
real plugin names from CONTEXT.md §26-71 canonical YAML). No placeholder text.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes beyond what the plan's threat
model covers. T-07-CHART-ARGS-MISS and T-07-CHART-YAML-INVALID mitigations are both
implemented and verified.

## Self-Check: PASSED

Files exist:
- charts/arr-stack/files/arrconf.yml: FOUND (540 lines, jellyfin: block present)
- charts/arr-stack/values.yaml: FOUND (line 458 contains seerr,jellyfin)
- tools/arrconf/tests/test_arrconf_yml_validates.py: FOUND (292 lines, 2 new tests)
- .planning/phases/07-reconciler-jellyfin/07-05-SUMMARY.md: this file

Commits exist:
- 0b9f85d: feat(07-05): jellyfin.main chart section + --apps list + validation tests
