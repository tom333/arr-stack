---
phase: 10-categories-6-app-propagation
plan: 10-D-sonarr-wiring
subsystem: arrconf/__main__.py Sonarr dispatch + chart values
tags:
  - python
  - reconciler-wiring
  - sonarr
  - chart-pin-cobump
  - phase10

dependency_graph:
  requires:
    - 10-A-generators-categories (generate_sonarr_resources -- consumed here)
    - 10-B-merge-with-manual (merge_with_manual helper -- consumed here)
    - 10-C-qbit-wiring-fp (dispatch pattern template; chart bumped to 0.6.0 there)
  provides:
    - Sonarr pre-merge dispatch in __main__.py apply + diff branches (4 resources)
    - arrconf.image.tag bumped to 0.6.1 in charts/arr-stack/values.yaml (D-05)
  affects:
    - 10-E-radarr-wiring (byte-equivalent Radarr plan -- same pattern)
    - reconcile_sonarr (receives merged tags/root_folders/download_clients/rpms from __main__.py)

tech_stack:
  added: []
  patterns:
    - "Pitfall 5 fix: generate_sonarr_resources called in both apply AND diff __main__.py branches"
    - "D-02 per-resource toggle: 4 independent merge_with_manual calls -- one per Sonarr resource"
    - "D-05 chart-pin co-bump: values.yaml 0.6.0->0.6.1 co-committed with behavioral arrconf change"
    - "Dump branch: no pre-merge needed -- dump reads cluster state not intended config"
    - "TDD RED/GREEN: test file committed separately (19a2df7) then implementation (18451c6)"

key_files:
  created:
    - tools/arrconf/tests/test_sonarr_categories.py
  modified:
    - tools/arrconf/arrconf/__main__.py (generate_sonarr_resources import + 4x pre-merge in apply + diff)
    - charts/arr-stack/values.yaml (arrconf.image.tag 0.6.0 -> 0.6.1)

key-decisions:
  - "Pitfall 5 honored: generate_sonarr_resources called in both apply (line 129) and diff (line 424) branches of __main__.py -- identical pre-merge shape prevents false drift between the two commands."
  - "Dump branch: no Sonarr pre-merge needed. dump_sonarr reads current cluster state from the API and exports it to YAML. It does NOT reconcile -- there is no instance.tags.items mutation that would affect what gets read. Pre-merge in dump would alter the YAML target but dump never uses the target."
  - "Import block: generate_sonarr_resources added inline to the existing generate_qbit_categories import on a single line. ruff sorted alphabetically within the block."
  - "D-05 chart-pin co-bump: arrconf.image.tag bumped from 0.6.0 to 0.6.1 in the same feat commit as the __main__.py behavioral change. TDD test commit (19a2df7) is a separate RED commit; feat commit (18451c6) bundles both __main__.py and values.yaml."

requirements-completed:
  - REQ-categories-sonarr-propagation

duration: "~20 minutes"
completed: "2026-05-19"
---

# Phase 10 Plan D: Sonarr Wiring + Chart-pin 0.6.0->0.6.1 Summary

**Sonarr pre-merge wired for 4 resources (tags, root_folders, download_clients, remote_path_mappings) in `__main__.py` apply + diff branches, with chart-pin co-bumped to 0.6.1 (D-05).**

## Performance

- **Duration:** ~20 minutes
- **Completed:** 2026-05-19
- **Tasks:** 2 completed (bundled in single feat commit per D-05)
- **Files modified:** 3 (1 new test file, 1 modified source, 1 modified chart)

## Accomplishments

### Task 10-D-01: Pre-merge Sonarr 4 resources in `__main__.py` (apply + diff + dump)

- Extended import: `from arrconf.generators.categories import generate_qbit_categories, generate_sonarr_resources`
- Injected 4-call pre-merge block in the **apply** branch after `instance = root.sonarr["main"]` and before `SonarrClient(...)` construction:
  - `instance.tags.items = merge_with_manual(instance.tags.items, sonarr_derived.tags, ...)`
  - `instance.root_folders.items = merge_with_manual(instance.root_folders.items, sonarr_derived.root_folders, ...)`
  - `instance.download_clients.items = merge_with_manual(instance.download_clients.items, sonarr_derived.download_clients, ...)`
  - `instance.remote_path_mappings.items = merge_with_manual(instance.remote_path_mappings.items, sonarr_derived.remote_path_mappings, ...)`
- Injected identical 4-call pre-merge block in the **diff** branch (Pitfall 5 -- diff must use the same merged shape as apply to avoid false drift).
- **Dump branch**: No pre-merge needed. `dump_sonarr` reads current cluster state from the Sonarr API and exports it to YAML. It does not use `instance.tags.items` etc. at all -- those fields are the reconciliation target, not the source for dump.
- Created `tests/test_sonarr_categories.py` with 6 tests:
  - `test_sonarr_tags_wiring_empty_manual` -- 5 series tags generated when manual empty
  - `test_sonarr_root_folders_wiring_empty_manual` -- 5 root folders at /media/series* paths
  - `test_sonarr_download_clients_wiring_empty_manual` -- 5 QBittorrent DCs with tag_labels
  - `test_sonarr_rpm_wiring_empty_manual` -- 5 RPMs with trailing slashes + qbit host
  - `test_sonarr_per_resource_override_tags_only` -- manual tags wins; generated root_folders wins
  - `test_sonarr_per_resource_override_rpm_only` -- manual RPM wins; generated DCs win

### Task 10-D-02: Chart-pin co-bump -- values.yaml arrconf.image.tag 0.6.0 -> 0.6.1

- Bumped `arrconf.image.tag` from `"0.6.0"` to `"0.6.1"` in `charts/arr-stack/values.yaml` (line 451).
- Renovate annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` preserved unchanged.
- YAML validates cleanly.
- Committed in the same feat commit as `__main__.py` changes (18451c6).

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 10-D-01 (RED) | Add Sonarr 4-resource wiring tests | `19a2df7` | tests/test_sonarr_categories.py |
| 10-D-01 (GREEN) + 10-D-02 | Wire Sonarr pre-merge + chart-pin 0.6.1 | `18451c6` | __main__.py, values.yaml |

## Pitfall 5 Verification

`generate_sonarr_resources` is called in BOTH the `apply` AND `diff` branches of `__main__.py`:
- apply: line 129 (`sonarr_derived = generate_sonarr_resources(root)`)
- diff: line 424 (`sonarr_diff_derived = generate_sonarr_resources(root)`)

Count: `grep -c 'generate_sonarr_resources' tools/arrconf/arrconf/__main__.py` → 3 (import line + 2 call sites). Pitfall 5 satisfied.

## D-05 Chart-pin Co-bump Evidence

```
git show 18451c6 --stat
 charts/arr-stack/values.yaml      |  2 +-
 tools/arrconf/arrconf/__main__.py | 57 ++++++++++++++++++++++++++++++++++++++-
 2 files changed, 57 insertions(+), 2 deletions(-) 
```

Both `tools/arrconf/arrconf/__main__.py` AND `charts/arr-stack/values.yaml` are in the SAME commit (18451c6). D-05 satisfied.

## Acceptance Criteria Verification

- `grep "generate_sonarr_resources" tools/arrconf/arrconf/__main__.py` -- exits 0 (3 matches: import + 2 call sites)
- `grep -c 'app="sonarr"' tools/arrconf/arrconf/__main__.py` -- returns 16 (≥ 4)
- `grep -c 'resource="tags"\|resource="root_folders"\|resource="download_clients"\|resource="remote_path_mappings"' tools/arrconf/arrconf/__main__.py` -- returns 8 (≥ 4)
- `grep -c 'generate_sonarr_resources' tools/arrconf/arrconf/__main__.py` -- returns 3 (≥ 2; Pitfall 5)
- `test -f tools/arrconf/tests/test_sonarr_categories.py` -- exits 0
- `grep -c "^def test_" tools/arrconf/tests/test_sonarr_categories.py` -- returns 6 (≥ 6)
- All 6 tests pass + Phase 9 no-regression intact + 332/332 tests pass (3 pre-existing isolation failures unchanged)

## Phase 9 No-regression

`test_phase9_no_regression.py` passes:
- `test_phase9_no_regression`: confirms Phase 9 plan (flat sections with categories[] present) still produces the same plan output (D-13 invariant: when manual sections are non-empty, generated is skipped)
- `test_dry_run_plan_unchanged_without_categories`: confirms no-op when categories[] is empty

## Note for Downstream Wave 2 Plans

- Plan 10-E (Radarr): byte-equivalent shape to Plan 10-D. Use `generate_radarr_resources` instead of `generate_sonarr_resources`. Bump chart-pin to 0.6.2. Same 4-resource pre-merge pattern.
- The established pattern: inject after `instance = root.<app>["main"]`, before `<App>Client(...)`, in both apply AND diff branches.
- Dump branch: no pre-merge needed for any app that only dumps cluster state (sonarr, jellyfin).

## Deviations from Plan

None. Plan executed exactly as written.

## Known Stubs

None. All code is fully implemented and production-correct.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes. `generate_sonarr_resources` is pure Python with no I/O. `merge_with_manual` is pure Python.

## Self-Check: PASSED

- `tools/arrconf/arrconf/__main__.py` -- FOUND (contains `generate_sonarr_resources` + 8 resource= call sites)
- `tools/arrconf/tests/test_sonarr_categories.py` -- FOUND (6 tests, all pass)
- `charts/arr-stack/values.yaml` -- FOUND (`tag: "0.6.1"`, renovate annotation preserved)
- Commit `19a2df7` -- FOUND (test(10-D): add Sonarr 4-resource wiring tests (TDD RED))
- Commit `18451c6` -- FOUND (feat(10-D): wire Sonarr 4-resource pre-merge in __main__.py + chart-pin 0.6.1)
- Both __main__.py AND values.yaml in commit 18451c6 -- CONFIRMED (D-05 satisfied)
- 6 Sonarr wiring tests pass + Phase 9 no-regression intact
