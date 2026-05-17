---
phase: "05-reconciler-qbittorrent-split-tv-anime-family"
plan: "02"
subsystem: "arrconf-config-schema"
tags: ["pydantic", "schema", "qbittorrent", "sonarr", "radarr", "tdd", "fail-fast"]
dependency_graph:
  requires: ["05-01"]
  provides: ["05-03", "05-04", "05-05", "05-06"]
  affects: ["tools/arrconf/arrconf/config.py", "schemas/arrconf-schema.json"]
tech_stack:
  added: []
  patterns:
    - "TDD RED/GREEN for all new schema tests and CLI tests"
    - "Pydantic extra=forbid on all new Phase 5 config sections (T-05-CONTENT mitigation)"
    - "Plan 02 stub classes for Plan 04 forward compatibility (QbittorrentClient, diff_qbittorrent)"
    - "mypy override for not-yet-existing reconcilers.qbittorrent module"
key_files:
  created:
    - "tools/arrconf/arrconf/resources/qbittorrent/__init__.py"
    - "tools/arrconf/arrconf/resources/qbittorrent/category.py"
    - "tools/arrconf/arrconf/resources/qbittorrent/preferences.py"
    - "tools/arrconf/arrconf/resources/sonarr/remote_path_mapping.py"
  modified:
    - "tools/arrconf/arrconf/config.py"
    - "tools/arrconf/arrconf/settings.py"
    - "tools/arrconf/arrconf/__main__.py"
    - "tools/arrconf/arrconf/client_base.py"
    - "tools/arrconf/arrconf/diff_cmd.py"
    - "tools/arrconf/pyproject.toml"
    - "tools/arrconf/tests/test_config.py"
    - "tools/arrconf/tests/test_cli.py"
    - "schemas/arrconf-schema.json"
decisions:
  - "Mypy override in pyproject.toml for arrconf.reconcilers.qbittorrent (Plan 04 removes it)"
  - "QbittorrentClient stub in client_base.py raises NotImplementedError (Plan 04 replaces with cookie-auth impl)"
  - "diff_qbittorrent stub in diff_cmd.py raises NotImplementedError (Plan 04 replaces)"
  - "importlib avoided in favor of try/except ImportError with real stub classes to satisfy mypy strict mode"
  - "SeriesTagsSection.enable defaults to True per D-05-MIG-01 (default-ON retroactive tagging)"
  - "MovieTagsSection.default_tag='movies' per D-05-SPLIT-02 (Radarr tag convention)"
metrics:
  duration: "~45 minutes"
  completed_date: "2026-05-14"
  tasks_completed: 3
  files_modified: 13
---

# Phase 5 Plan 02: Config Schema Extension + Fail-Fast Gate Summary

**One-liner:** Pydantic schema extended with 8 new section classes for qBittorrent/Sonarr/Radarr Phase 5 surface area; D-05-BOOTSTRAP-01 fail-fast gate #2 coded + tested; JSON Schema regenerated with `qbittorrent` top-level property.

## What Was Built

### Task 2.1: 3 new pydantic resource models + qbittorrent package

- `arrconf/resources/qbittorrent/category.py`: `Category(name, savePath)` with `extra="allow"` for forward-compat qBit 5.1+ `download_path` field.
- `arrconf/resources/qbittorrent/preferences.py`: `QbitPreferences` with `extra="forbid"` enforcing the 4-key allowlist (T-05-CONTENT threat mitigation). Keys: `category_changed_tmm_enabled`, `torrent_changed_tmm_enabled`, `auto_tmm_enabled`, `save_path`.
- `arrconf/resources/sonarr/remote_path_mapping.py`: `RemotePathMapping(host, remotePath, localPath, id=None excluded)` with `extra="allow"`. Shared by Sonarr and Radarr per PATTERNS.md.
- `arrconf/resources/qbittorrent/__init__.py`: Package marker exporting `Category` and `QbitPreferences`.

### Task 2.2: Config schema + Settings extension (TDD)

**8 new classes added to `config.py`:**

| Class | Role | extra |
|-------|------|-------|
| `TagItem` | Single tag label | forbid |
| `TagsSection` | Tags list with prune flag | forbid |
| `RemotePathMappingsSection` | Path mappings list with prune | forbid |
| `SeriesTagsSection` | Retroactive default-tag config (enable=True, default_tag="tv") | forbid |
| `MovieTagsSection` | Radarr mirror (enable=True, default_tag="movies") | forbid |
| `CategoriesSection` | qBit categories list (prune=False, docstring notes R-04) | forbid |
| `PreferencesSection` | qBit preferences opt-in (enable=False) | forbid |
| `QbittorrentInstance` | Per-instance qBit config (base_url + 2 sections) | forbid |

**Extensions to existing models:**
- `SonarrInstance` gains: `tags`, `remote_path_mappings`, `series_tags`
- `RadarrInstance` gains: `tags`, `remote_path_mappings`, `movie_tags`
- `RootConfig` gains: `qbittorrent: dict[str, QbittorrentInstance]` (extra=forbid preserved)

**Settings:** `qbt_user: SecretStr | None` and `qbt_pass: SecretStr | None` added (env: `QBT_USER` / `QBT_PASS`).

**Test count:** 17 tests in `test_config.py` (7 pre-existing + 10 new). All pass.

### Task 2.3: __main__ wiring + JSON Schema regeneration (TDD)

- `_VALID_APPS` expanded to include `"qbittorrent"`.
- `apply` command: qBittorrent branch with D-05-BOOTSTRAP-01 gate #2 — checks `settings.qbt_user` and `settings.qbt_pass`; logs `missing_env_vars` with key list and raises `typer.Exit(code=2)` before any client construction. Lazy imports of `QbittorrentClient` + `reconcile_qbittorrent` inside try/except ImportError.
- `diff` command: mirror of apply's qBittorrent branch.
- `schemas/arrconf-schema.json` regenerated — top-level `qbittorrent` property added, `sonarr`/`radarr` models extended with `tags`, `remote_path_mappings`, `series_tags`/`movie_tags`.

**Test count:** 20 tests in `test_cli.py` (15 pre-existing + 5 new). All pass.

**Full suite:** 143 tests across all test files — all pass.

## Class Hierarchy (new in Plan 02)

```
RootConfig
├── sonarr: dict[str, SonarrInstance]
│   └── SonarrInstance: base_url, download_clients, host_config, indexers,
│       notifications, remote_path_mappings, root_folders, series_tags, tags
├── radarr: dict[str, RadarrInstance]
│   └── RadarrInstance: base_url, download_clients, host_config, indexers,
│       movie_tags, notifications, remote_path_mappings, root_folders, tags
├── prowlarr: dict[str, ProwlarrInstance]  (unchanged)
└── qbittorrent: dict[str, QbittorrentInstance]  ← NEW
    └── QbittorrentInstance: base_url, categories, preferences
        ├── CategoriesSection: prune=False, items: list[Category]
        │   └── Category: name, savePath  (extra="allow")
        └── PreferencesSection: enable=False, values: QbitPreferences
            └── QbitPreferences: 4-key allowlist (extra="forbid")

SonarrInstance (extended):
├── TagsSection: prune=False, items: list[TagItem]
│   └── TagItem: label
├── RemotePathMappingsSection: prune=False, items: list[RemotePathMapping]
│   └── RemotePathMapping: host, remotePath, localPath, id=None (excluded)
└── SeriesTagsSection: enable=True, default_tag="tv"  ← D-05-MIG-01 default-ON

RadarrInstance (extended):
├── TagsSection (same as Sonarr)
├── RemotePathMappingsSection (same as Sonarr)
└── MovieTagsSection: enable=True, default_tag="movies"  ← D-05-SPLIT-02
```

## JSON Schema Delta

The `schemas/arrconf-schema.json` top-level `properties` now has 4 keys: `prowlarr`, `qbittorrent`, `radarr`, `sonarr`. The `qbittorrent` property points to a `dict[str, QbittorrentInstance]` pydantic JSON Schema (additionalProperties with $ref to the instance $defs). Sonarr and Radarr $defs extended with new section schemas.

Schema idempotence verified: `arrconf schema-gen` output is byte-equivalent to committed file.

## Known Stubs (Intentional — Plan 04 wires these)

| Stub | File | Line | Reason |
|------|------|------|--------|
| `QbittorrentClient.__init__` raises `NotImplementedError` | `client_base.py` | ~175 | Plan 04 adds full cookie-auth impl (D-05-QBT-01) |
| `diff_qbittorrent` raises `NotImplementedError` | `diff_cmd.py` | ~85 | Plan 04 wires real diff logic |
| `[[tool.mypy.overrides]] module = ["arrconf.reconcilers.qbittorrent"]` | `pyproject.toml` | ~58 | Plan 04 creates the real module; remove override then |

These stubs do not prevent Plan 02's goal (schema + gate). The apply branch catches `ImportError` from the lazy import of `arrconf.reconcilers.qbittorrent` (which doesn't exist until Plan 04) and appends `"qbittorrent"` to `failures` → exit 1 (app failure), which is correct behavior for this plan state.

## Mypy Suppression Notes

One `[[tool.mypy.overrides]]` section added to `pyproject.toml` to suppress `import-missing` for `arrconf.reconcilers.qbittorrent`. No `# type: ignore` comments were added anywhere — the stub classes satisfy mypy's strict type checking fully.

## Deviations from Plan

### Auto-added: Plan 02 stubs for `QbittorrentClient` and `diff_qbittorrent`

**Found during:** Task 2.3
**Issue:** The plan called for lazy imports of `QbittorrentClient` from `client_base` and `reconcile_qbittorrent` from `reconcilers.qbittorrent`. Both don't exist yet (Plan 04). Mypy strict mode + `warn_unused_ignores = true` made it impossible to use `# type: ignore[attr-defined]` (the ignores become "unused" once stubs exist, and mypy strict rejects them with different errors once stubs are absent).
**Fix:** Added minimal stub classes (`QbittorrentClient` in `client_base.py` + `diff_qbittorrent` in `diff_cmd.py`) that raise `NotImplementedError`. This satisfies mypy without any `# type: ignore` comments. Added `[[tool.mypy.overrides]]` for the not-yet-existing reconciler module. Plan 04 replaces these stubs with real implementations.
**Files modified:** `tools/arrconf/arrconf/client_base.py`, `tools/arrconf/arrconf/diff_cmd.py`, `tools/arrconf/pyproject.toml`
**Commits:** included in `efc4f71`

## TDD Gate Compliance

All three tasks were executed with proper TDD discipline:

| Gate | Commit | Note |
|------|--------|------|
| RED (config tests) | `726f494` | 10 new config tests fail before schema extension |
| GREEN (config + settings) | `e63882f` | All 17 config tests pass after schema extension |
| RED (CLI tests) | `fc24d0a` | 5 new CLI tests fail before __main__ wiring |
| GREEN (__main__ + stubs + schema) | `efc4f71` | All 20 CLI tests pass |

## Self-Check: PASSED

All key files exist:
- FOUND: tools/arrconf/arrconf/resources/qbittorrent/__init__.py
- FOUND: tools/arrconf/arrconf/resources/qbittorrent/category.py
- FOUND: tools/arrconf/arrconf/resources/qbittorrent/preferences.py
- FOUND: tools/arrconf/arrconf/resources/sonarr/remote_path_mapping.py
- FOUND: tools/arrconf/arrconf/config.py (extended)
- FOUND: tools/arrconf/arrconf/settings.py (extended)
- FOUND: tools/arrconf/arrconf/__main__.py (extended)
- FOUND: schemas/arrconf-schema.json (regenerated)

All commits exist:
- FOUND: d579c80 (feat: resource models)
- FOUND: 726f494 (test: failing config tests — RED)
- FOUND: e63882f (feat: config schema + settings — GREEN)
- FOUND: fc24d0a (test: failing CLI tests — RED)
- FOUND: efc4f71 (feat: __main__ + stubs + schema — GREEN)
