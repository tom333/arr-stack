---
phase: 24-jellyfin-intro-skipper
plan: "02"
subsystem: arrconf
tags: [jellyfin, plugin-install, intro-skipper, two-run, tdd, co-bump]
dependency_graph:
  requires: [24-01]
  provides: [JFSKIP-02, JFSKIP-03]
  affects:
    - tools/arrconf/arrconf/reconcilers/jellyfin.py
    - tools/arrconf/tests/test_reconcilers_jellyfin_plugin_install.py
    - charts/arr-stack/files/arrconf.yml
    - charts/arr-stack/values.yaml
    - schemas/arrconf-schema.json
    - .planning/PROJECT.md
    - spec.md
tech_stack:
  added: []
  patterns:
    - two-run model (D-02): install fires in Run N, enable+config in Run N+1 after restart
    - PACKAGES_INSTALLED_PATH constant + POST /Packages/Installed/{name}?params (query-params only, no body)
    - plugin-config loop (GET /Plugins/{id}/Configuration → diff → POST) follows enable loop
    - "MaxParallelism field name confirmed: 'MaxParallelism' (matches IntroSkipperConfig model from plan 01)"
key_files:
  created:
    - tools/arrconf/tests/test_reconcilers_jellyfin_plugin_install.py
  modified:
    - tools/arrconf/arrconf/reconcilers/jellyfin.py
    - charts/arr-stack/files/arrconf.yml
    - charts/arr-stack/values.yaml
    - tools/arrconf/tests/test_arrconf_yml_validates.py
    - .planning/PROJECT.md
    - spec.md
decisions:
  - "co-bump arrconf.image.tag 0.16.0 → 0.17.0 (deviation override: plan 01 already claimed 0.16.0)"
  - "MaxParallelism confirmed as canonical field name for Intro Skipper concurrency cap (plan 01 model, consistent with Configuration.cs PascalCase convention)"
  - "plugin-config loop placed AFTER enable loop (same _reconcile_plugins call) — two-run respected since config only fires when Status is Active"
  - "ADR-9 records D-07-PLUGINS-01 reversal to install-capable with backward-compatibility guarantee"
metrics:
  duration: "12 minutes"
  completed_date: "2026-05-29"
  tasks_completed: 3
  files_modified: 7
  files_created: 1
---

# Phase 24 Plan 02: Intro Skipper Install + Plugin-Config Reconciler Summary

Two-run install model + plugin config logic for Jellyfin Intro Skipper: POST /Packages/Installed when absent, GET+diff+POST /Plugins/{id}/Configuration when Active; co-bumped arrconf.image.tag 0.16.0→0.17.0 and recorded ADR-9 reversing D-07-PLUGINS-01 to install-capable.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Two-run install + plugin-config logic + 7 respx tests (TDD) | 4eede10 | reconcilers/jellyfin.py, test_reconcilers_jellyfin_plugin_install.py |
| 2 | Declare Intro Skipper in arrconf.yml, co-bump tag, regenerate schema | cdaf7f6 | arrconf.yml, values.yaml, test_arrconf_yml_validates.py |
| 3 | Record ADR-9 (D-07-PLUGINS-01 reversal to install-capable) | 62823fa | PROJECT.md, spec.md |

## What Was Built

**JFSKIP-02 (D-01/D-02): Two-run install model**
- `PACKAGES_INSTALLED_PATH = "/Packages/Installed"` constant added.
- `_reconcile_plugins()` extended: when plugin absent + `install_guid`/`install_version`/`install_repo_url` all set → POST `/Packages/Installed/{name}?assemblyGuid&version&repositoryUrl`, log `plugin_install_queued` warning with `kubectl rollout restart deployment/jellyfin -n selfhost` hint, append `plugin_install_queued:{name}` action, `continue` (no enable/config same run).
- When plugin absent + no install fields → existing `plugin_missing_skip` warning path unchanged (backward-compatible).

**JFSKIP-03 (D-04/D-05): Plugin-config loop**
- After the enable loop, a second loop over `section.required`: for each entry with `config != None`, skip if plugin not present or not Active (two-run model). Otherwise GET `/Plugins/{id}/Configuration`, diff against desired, POST only on diff.
- `MaxParallelism=1` caps concurrency for single-node MicroK8s (D-05).
- `AutoSkip=False`, `AutoSkipCredits=False` per PROJECT.md Out of Scope.

**arrconf.yml block (charts/arr-stack/files/arrconf.yml):**
- Intro Skipper entry added under `jellyfin.main.plugins.required` with GUID `c83d86bb-a1e0-4c35-a113-e2101cf4ee6b`, version `1.10.11.19`, repo URL `https://intro-skipper.org/manifest.json`, and config block.

**Co-bump: 0.16.0 → 0.17.0** (deviation override — 0.16.0 was already claimed by plan 01 in parallel worktree).

**ADR-9**: PROJECT.md decisions table + spec.md §11 cross-reference documenting the install-capable reversal.

## Verification

```
cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf
→ All checks passed

cd tools/arrconf && uv run pytest tests/test_reconcilers_jellyfin_plugin_install.py -q
→ 7 passed

cd tools/arrconf && uv run pytest tests/test_reconcilers_jellyfin.py -q
→ 23 passed (no regression)

cd tools/arrconf && uv run pytest -q --ignore=tests/test_phase10_idempotence_sweep.py
→ 464 passed

RootConfig.model_validate(arrconf.yml): p.install_guid=='c83d86bb-...', p.config.MaxParallelism==1, p.config.AutoSkip is False → OK
schemas/arrconf-schema.json: valid JSON (already up to date from plan 01)
values.yaml arrconf.image.tag == "0.17.0" with renovate annotation intact
Coverage on reconcilers/jellyfin.py: 92% (gate: ≥70%)
```

## Deviations from Plan

### Deviation Override (Pre-authorized by orchestrator)

**Co-bump target: 0.15.0 → 0.16.0 (plan) → actual: 0.16.0 → 0.17.0**
- **Reason:** Plan 01 (parallel worktree, wave 1) already co-bumped `arrconf.image.tag` from `0.15.0` to `0.16.0`. When this worktree reset to the wave 1 merge point (`6d4a76e`), `values.yaml` already had `tag: "0.16.0"`. The CRITICAL_DEVIATION_OVERRIDE in the execution context explicitly instructed bumping to `0.17.0` (minor, new feature).
- **Result:** `tag: "0.17.0"` in `charts/arr-stack/values.yaml`, renovate annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` preserved.

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_arrconf_yml_validates_jellyfin for new plugin count**
- **Found during:** Task 2 full test suite run
- **Issue:** `test_arrconf_yml_validates_jellyfin` asserted `len(plugins.required) == 6`, but we added Intro Skipper bringing it to 7
- **Fix:** Updated assertion to 7 + added Intro Skipper-specific assertions (name, install_guid, MaxParallelism, AutoSkip)
- **Files modified:** `tools/arrconf/tests/test_arrconf_yml_validates.py`
- **Commit:** cdaf7f6

### MaxParallelism Field Name Confirmation

Per Task 1 step 0 (W-02 validation): the `MaxParallelism` field name was confirmed as correct against the `IntroSkipperConfig` model already committed in plan 01 (`92a8879`), which was derived from the plugin source `Configuration.cs` PascalCase convention. The STACK.md analysis (MEDIUM confidence) and the plan 01 model both converge on `MaxParallelism`. No divergence found. Field used verbatim in reconciler and arrconf.yml.

### Pre-existing Test Failures (Out of Scope)

`tests/test_phase10_idempotence_sweep.py` — pre-existing failure (unmocked qbittorrent endpoint), confirmed before any changes in this plan. Excluded from test run per established practice.

## Known Stubs

None — all install/config fields are fully wired with concrete GUID/version/URL values. `AutoSkip=False` is intentional (PROJECT.md Out of Scope: show skip button, no auto-skip).

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: T-24-04 (mitigated) | charts/arr-stack/files/arrconf.yml | Version pinned to 1.10.11.19 + GUID c83d86bb-a1e0-4c35-a113-e2101cf4ee6b; no floating latest; official intro-skipper.org manifest; PR-reviewed |
| threat_flag: T-24-05 (mitigated) | tools/arrconf/arrconf/reconcilers/jellyfin.py | Install gated on explicit install fields (absent = activation-only); NO uninstall/prune; two-run requires deliberate restart |
| threat_flag: T-24-07 (mitigated) | charts/arr-stack/files/arrconf.yml | MaxParallelism=1 caps CPU; AutoSkip=false avoids forced skip behavior |

## Self-Check: PASSED
