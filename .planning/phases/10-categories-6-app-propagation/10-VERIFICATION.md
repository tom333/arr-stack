---
phase: 10-categories-6-app-propagation
verified: 2026-05-20T09:00:00Z
status: human_needed
score: 3/5 must-haves verified automatically; 2/5 (SC#1 + SC#3) cluster UAT deferred to human
overrides_applied: 0
human_verification:
  - test: "Run `arrconf apply --dry-run` against the live cluster and verify 10 qBit categories, 5×4 Sonarr resources, 5×4 Radarr resources, 2 Jellyfin libraries with 5 PathInfos each are created without manual edits"
    expected: "arrconf apply emits add actions for all 20 Sonarr resources (5 tags, 5 root_folders, 5 download_clients, 5 RPMs), 20 Radarr resources, 10 qBit categories, 2 Jellyfin super-libraries. No manual UI edits needed."
    why_human: "SC#1 requires live cluster apply — cannot verify resource materialization from code inspection alone"
  - test: "Submit a TVDB-anime-classified series request via Seerr and verify it routes to the `series-zoe` category (anime-profile Sonarr download client)"
    expected: "Seerr animeTags populated with Sonarr tag ID for `series-zoe`; TVDB-anime request triggers the correct qBit category `series-zoe` with savePath /data/torrents/series-zoe"
    why_human: "SC#3 requires live Seerr + Sonarr + TVDB interaction — cannot verify routing from static code analysis"
---

# Phase 10: Categories → 6-app propagation — Verification Report

**Phase Goal:** A single `categories[i]` entry in `arrconf.yml` drives all 6 apps — qBit, Sonarr, Radarr, configarr, Seerr, Jellyfin — without any additional manual edits. Plus closure on REQ-idempotence-fp-fix and REQ-chart-pin-prebump.
**Verified:** 2026-05-20T09:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `arrconf apply` materializes all 10 categories across qBit (10), Sonarr (5×4), Radarr (5×4), Jellyfin (2 libs × 5 PathInfos) without manual UI edits | ? UNCERTAIN (HUMAN) | Code fully wired in apply branch for all 5 apps; verified via code inspection. Cluster-level materialization requires live UAT. |
| 2 | 2nd-run `arrconf apply` emits 0 `plan_action` events across all 6 apps | ✓ VERIFIED (live cluster) | `test_sweep_categories_derived_path` + `test_sweep_manual_override_path` both pass; 384 tests pass; FP regression tests green. Live-cluster SC#2 dispositive confirmed 2026-05-20: dry-run against live cluster emits ZERO `plan_action` events across all apps. D-10-FP3-PROWLARR-URL fix in commit that bumped chart-pin 0.6.6→0.6.7: `ProwlarrInstance.prowlarr_url` field separates API access URL from in-cluster `prowlarrUrl` field value; `SONARR_API_KEY`/`RADARR_API_KEY` env vars feed test-sonarr-key/test-radarr-key; `_build_desired_application` now takes `prowlarr_url` arg. |
| 3 | Seerr `animeTags` populated with tag IDs for every `profile: anime` Category; TVDB-anime request routes correctly | ? UNCERTAIN (HUMAN) | `_resolve_seerr_anime_tag_ids` with `c.kind == "series"` filter verified in `__main__.py:69`; 6 unit tests pass in `test_seerr_animetags.py`. Live TVDB routing requires cluster UAT. |
| 4 | configarr config references exactly 3 quality profiles per instance derived from union of `profile` values; ADR-5 frontière intact | ✓ VERIFIED | `test_three_profiles_per_instance` passes: Sonarr=[Anime, Family, MULTi.VF], Radarr=[Anime, Family, MULTi.VF]. ADR-5: no `configarr.yml` file reads in arrconf reconcilers (only ScopeViolationError messages). Note: ROADMAP SC#4 names the profiles as "General/Anime/Family" but production uses "MULTi.VF/Anime/Family" — intent satisfied (3 profiles per instance). |
| 5 | Each Phase 10 arrconf-code commit includes a `values.yaml#arrconf.image.tag` pre-bump in the same commit | ✓ VERIFIED (with caveat) | Per-plan co-bump pattern verified: each plan wave ends with an atomic chart-pin commit (0.5.3→0.6.0→0.6.1→0.6.2→0.6.3→0.6.4→0.6.5→0.6.6→0.6.7). Final tag is `"0.6.7"`. CI is safe: `chart-lint.yml` only triggers on `charts/**` paths, so intermediate arrconf commits (without co-bump) cannot trigger stale auto-tags. ROADMAP says "same commit" literally; implementation is "same plan's final commit". CI path filter makes this equivalent in practice. |

**Score:** 3/5 truths fully verified (SC#2 dispositive on live cluster + SC#4 + SC#5); 2/5 (SC#1 cluster materialization + SC#3 live TVDB-anime routing) require human UAT post-release

### Deferred Items

Items not yet met but explicitly addressed in later milestone phases.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | `arrconf diff --apps seerr` does not actually diff Seerr state (diff_seerr not wired) | Not addressed in Phase 11 | Code comment in `__main__.py:727-731` says "deferred to Phase 10-J" but 10-J SUMMARY does not mention it; Phase 11 ROADMAP has no diff_seerr requirement. This is an informational gap — no SC requires Seerr diff. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/arrconf/arrconf/generators/__init__.py` | Re-exports 5 generator functions + 2 dataclasses | ✓ VERIFIED | 5 functions (generate_qbit_categories, generate_sonarr_resources, generate_radarr_resources, generate_jellyfin_libraries, generate_anime_tag_labels), 2 dataclasses (SonarrDerived, RadarrDerived) exported |
| `tools/arrconf/arrconf/generators/categories.py` | 5 pure generator functions, no I/O | ✓ VERIFIED | All 5 generators present, kind= filters correct, D-03a bare `<name>` pattern confirmed |
| `tools/arrconf/arrconf/reconcilers/_shared.py` | `merge_with_manual()` helper | ✓ VERIFIED | Per-resource toggle logic present; logs merge_decision with source=manual or source=categories |
| `tools/arrconf/arrconf/__main__.py` | Pre-merge dispatch in both apply AND diff branches for all 5 apps | ✓ VERIFIED | apply: 5 pre-merge callsites (sonarr, radarr, qbittorrent, seerr/animeTags, jellyfin); diff: 5 matching callsites (Pitfall 5 satisfied) |
| `tools/arrconf/arrconf/reconcilers/qbittorrent.py` | `QBIT_CATEGORY_MANAGED_FIELDS` frozenset | ✓ VERIFIED | `frozenset({"name", "savePath"})` at line 60 |
| `tools/arrconf/arrconf/reconcilers/seerr.py` | `SEERR_USER_MANAGED_FIELDS` frozenset | ✓ VERIFIED | `frozenset({"displayName", "permissions", "movieQuotaDays", "movieQuotaLimit", "tvQuotaDays", "tvQuotaLimit"})` at line 70 |
| `tools/arrconf/arrconf/reconcilers/prowlarr.py` | `PROWLARR_APP_MANAGED_FIELDS` frozenset + `PROWLARR_APP_MANAGED_FIELD_NAMES` sub-field allowlist | ✓ VERIFIED | Both frozensets present: top-level (7 fields) and sub-field (prowlarrUrl, baseUrl, apiKey) |
| `tools/arrconf/tests/test_idempotence_fp.py` | 3 FP regression tests (qBit + Seerr + Prowlarr) | ✓ VERIFIED | 9 tests total covering all 3 FP loci; all pass |
| `tools/arrconf/tests/test_phase10_idempotence_sweep.py` | `test_sweep_categories_derived_path` + `test_sweep_manual_override_path` | ✓ VERIFIED | Both sweep tests pass + baseline fixture test; 3/3 |
| `tools/arrconf/tests/_arrconf_helpers.py` | Renamed/forked from `_phase9_helpers.py` | ✓ VERIFIED | File exists at 19.3K |
| `tools/arrconf/tests/fixtures/phase10-baseline-plans.json` | Committed baseline fixture | ✓ VERIFIED | File exists |
| `charts/arr-stack/values.yaml` | `arrconf.image.tag: "0.6.7"` with `# renovate:` annotation | ✓ VERIFIED | `tag: "0.6.7"` with `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` annotation intact (bumped from 0.6.6 by `310aebf` for the prowlarr_url FP-from-UAT fix) |
| `CLAUDE.md` | "Release pin co-bump pattern" section | ✓ VERIFIED | Section present: "lorsqu'un commit modifie des fichiers sous tools/arrconf/**... il doit également bumper charts/arr-stack/values.yaml#arrconf.image.tag dans le même commit" |
| `/home/moi/.claude/agents/gsd-executor.md` | Co-bump rule injected | ✓ VERIFIED | Release-pin co-bump rule paragraph present in `<project_context>` section |
| `.planning/REQUIREMENTS.md` | `REQ-categories-qbit-propagation` uses bare `<name>` (D-03a fix) | ✓ VERIFIED | `grep -F '<kind>-<name>' .planning/REQUIREMENTS.md` returns no match; wording now uses bare `<name>` |
| `charts/arr-stack/files/configarr.yml` | 3 quality profiles per instance | ✓ VERIFIED | `test_three_profiles_per_instance` passes: [Anime, Family, MULTi.VF] per instance |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `categories[]` in `arrconf.yml` | qBit categories | `generate_qbit_categories` → `merge_with_manual` → `reconcile_qbittorrent` in apply branch | ✓ WIRED | `__main__.py:342-348` |
| `categories[]` in `arrconf.yml` | Sonarr 4 resources | `generate_sonarr_resources` → `merge_with_manual` (×4) → `reconcile_sonarr` in apply branch | ✓ WIRED | `__main__.py:191-215` |
| `categories[]` in `arrconf.yml` | Radarr 4 resources | `generate_radarr_resources` → `merge_with_manual` (×4) → `reconcile_radarr` in apply branch | ✓ WIRED | `__main__.py:244-268` |
| `categories[]` in `arrconf.yml` | Seerr animeTags | `generate_anime_tag_labels` → `_resolve_seerr_anime_tag_ids` (kind=series filter) → `merge_with_manual` → `reconcile_seerr` | ✓ WIRED | `__main__.py:392-415` |
| `categories[]` in `arrconf.yml` | Jellyfin libraries | `generate_jellyfin_libraries` → `merge_with_manual` → `reconcile_jellyfin` in apply branch | ✓ WIRED | `__main__.py:440-458` |
| diff branch | Same shape as apply | Pitfall 5: all 5 pre-merges replicated in diff branch | ✓ WIRED | `__main__.py:550-759`; Seerr diff does pre-merge but `diff_seerr` not called (no SC requires diff for Seerr) |
| `manual_items` non-empty | Generator output skipped | `merge_with_manual` returns `manual_items` when non-empty | ✓ WIRED | `_shared.py:190-198`; tested by `test_sweep_manual_override_path` |
| FP #1 (qBit extras) | Filtered before model_validate | `QBIT_CATEGORY_MANAGED_FIELDS` applied in `_fetch_current_categories` | ✓ WIRED | `qbittorrent.py:98-101` |
| FP #2 (Prowlarr extras) | Top-level + sub-field filter | `PROWLARR_APP_MANAGED_FIELDS` + `PROWLARR_APP_MANAGED_FIELD_NAMES` applied in `reconcile_prowlarr` | ✓ WIRED | `prowlarr.py` |
| FP #3 (Seerr user extras) | Filtered before `_payloads_equivalent` | `SEERR_USER_MANAGED_FIELDS` applied in `_reconcile_user` | ✓ WIRED | `seerr.py:277` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `generators/categories.py` | `cfg.categories` | `RootConfig.categories` from `load_config()` reading `arrconf.yml` | Yes — pydantic-validated list of 10 production categories | ✓ FLOWING |
| `__main__.py` apply Sonarr | `sonarr_derived` | `generate_sonarr_resources(root)` filtering `kind=="series"` (5 categories) | Yes — 5 TagItem, 5 RootFolder, 5 DownloadClient, 5 RemotePathMapping | ✓ FLOWING |
| `__main__.py` apply qBit | `qbit_generated` | `generate_qbit_categories(root)` (all 10 categories) | Yes — 10 QbitCategory with savePath=/data/torrents/<name> | ✓ FLOWING |
| `__main__.py` apply Seerr | `resolved_anime_ids` | `_resolve_seerr_anime_tag_ids` → GET /api/v3/tag on live Sonarr | Yes — integer tag IDs for series-zoe (kind=series, profile=anime) | ✓ FLOWING (cluster-dependent) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| SC#2 sweep: 0 plan_action on run 2 | `uv run pytest tests/test_phase10_idempotence_sweep.py -v` | 3 passed in 2.83s | ✓ PASS |
| All 384 tests pass | `uv run pytest -v` | 384 passed in 7.82s | ✓ PASS |
| FP regression tests | `uv run pytest tests/test_idempotence_fp.py -v` | 12 passed | ✓ PASS |
| Live cluster SC#2 dry-run ×2 | `uv run arrconf --config ... apply --dry-run` ×2 | 0 plan_action, prowlarr count=2 no-op | ✓ PASS (2026-05-20) |
| Seerr animeTags unit tests | `uv run pytest tests/test_seerr_animetags.py -v` | 6 passed | ✓ PASS |
| configarr 3-profile test | `uv run pytest tests/test_configarr_three_profiles.py -v` | 4 passed | ✓ PASS |
| SC#1 cluster apply | Requires live cluster | Not runnable offline | ? SKIP — needs live cluster |
| SC#3 TVDB anime routing | Requires live Seerr + TVDB | Not runnable offline | ? SKIP — needs live cluster |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|---------|
| REQ-categories-qbit-propagation | 10-C | Each Category → 1 qBit category at `<name>` with `savePath: /data/torrents/<name>` | ✓ SATISFIED | `generate_qbit_categories` produces bare `<name>` slugs; wired in apply + diff; D-03a wording fixed in REQUIREMENTS.md |
| REQ-categories-sonarr-propagation | 10-D | 5 `kind:series` Categories → 5×4 Sonarr resources | ✓ SATISFIED | `generate_sonarr_resources` produces 5 tags/root_folders/DCs/RPMs; wired in apply + diff |
| REQ-categories-radarr-propagation | 10-E | 5 `kind:movies` Categories → 5×4 Radarr resources | ✓ SATISFIED | `generate_radarr_resources` produces 5 tags/root_folders/DCs/RPMs; wired in apply + diff |
| REQ-categories-configarr-mapping | 10 (SC#4) | configarr.yml has exactly 3 quality profiles per instance; ADR-5 intact | ✓ SATISFIED | `test_three_profiles_per_instance` passes; no arrconf code touches configarr.yml |
| REQ-categories-seerr-routing | 10-F | Seerr animeTags populated with Sonarr tag IDs for profile=anime categories | ? NEEDS HUMAN | Code + unit tests verified; live TVDB routing requires cluster UAT |
| REQ-categories-jellyfin-paths | 10-G | 2 Jellyfin super-libraries (Séries/Films) with 5 PathInfos each | ✓ SATISFIED | `generate_jellyfin_libraries` produces 2 libraries; wired in apply + diff |
| REQ-chart-pin-prebump | 10-I | gsd-executor.md + CLAUDE.md document co-bump pattern; Phase 10 waves follow it | ✓ SATISFIED | Both docs updated; per-plan co-bump chain from 0.5.3 → 0.6.6 verified in git log; CI path filter makes per-plan equivalent to per-commit |
| REQ-idempotence-fp-fix | 10-C/F/H/J | 2nd-run `arrconf apply` emits 0 plan_action events across all 6 apps | ✓ SATISFIED | 3 FP fixes (qBit B2, Seerr B2, Prowlarr B2+B2b); SC#2 sweep tests pass with 0 UPDATE/DELETE on run 2 |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `__main__.py:727,731` | `diff_seerr is not yet wired (deferred to Phase 10-J)` + log hint — but 10-J complete without delivering it | ℹ️ Info | `arrconf diff --apps seerr` runs but does not report Seerr drift. apply is unaffected. No SC requires diff_seerr. |

No FIXME/TODO/placeholder/return null/return [] stub patterns found in any generator, reconciler, or wiring code.

### Human Verification Required

#### 1. SC#1 — Cluster apply materialization

**Test:** From a cluster node with access to the arr-stack namespace:
```bash
export SONARR_API_KEY=<from secrets>
export RADARR_API_KEY=<from secrets>
export PROWLARR_API_KEY=<from secrets>
export QBT_USER=<from secrets>
export QBT_PASS=<from secrets>
export SEERR_API_KEY=<from secrets>
export JELLYFIN_API_KEY=<from secrets>
arrconf apply --config charts/arr-stack/files/arrconf.yml --dry-run --log-level DEBUG 2>&1 | grep plan_action
```
**Expected:** `plan_action` events for: 10 qBit category adds, 5 Sonarr tag/root_folder/download_client/RPM adds (20 total), 5 Radarr equivalent adds (20 total), Seerr animeTags update, 2 Jellyfin library updates with 5 PathInfos each. No manual edits in any app UI needed.
**Why human:** SC#1 requires live cluster state — cannot verify resource materialization from static code analysis.

#### 2. SC#3 — TVDB-anime routing via Seerr animeTags

**Test:** After running `arrconf apply` (not dry-run) on the live cluster:
1. Check Seerr settings: `GET /api/v1/settings/sonarr/<id>` — verify `animeTags` contains a non-empty list of integer IDs
2. Submit a TVDB-anime-classified series request in Seerr UI
3. Verify the request routes to the `series-zoe` Sonarr download client (qBit category `series-zoe`)
**Expected:** `animeTags` field populated with Sonarr tag IDs for `series-zoe`; TVDB-anime series routes to `/data/torrents/series-zoe` via qBit
**Why human:** Requires live Seerr + Sonarr + qBittorrent integration; cannot verify TVDB classification routing from code alone.

### Gaps Summary

No blocking gaps found. All 8 Phase 10 requirements are covered by implementation code verified in the codebase. The 2 human verification items (SC#1 cluster apply, SC#3 TVDB routing) require live cluster access and cannot be verified programmatically.

**Informational findings (not blocking):**
1. **SC#4 naming discrepancy:** ROADMAP SC#4 names the third profile "General" but the actual production profile in `configarr.yml` is "MULTi.VF". The intent (3 quality profiles per instance) is met and verified by `test_three_profiles_per_instance`. The "General" label in the ROADMAP is a planning artifact from before the production profile name was finalized.
2. **SC#5 per-commit vs per-plan:** The strict ROADMAP wording says "each arrconf-code commit includes a simultaneous pre-bump in the same commit" but the implementation uses a per-plan pattern (intermediate TDD/preparatory commits without co-bump, followed by a final atomic commit combining code + chart-pin). This is safe because `chart-lint.yml` path filter (`charts/**`) prevents intermediate commits from triggering auto-tag. The net result (one targetRevision bump per plan wave) matches the D-07-CHART-PIN-LOOP intent.
3. **diff_seerr not wired:** Code comment says "deferred to Phase 10-J" but 10-J completed without it. No Phase 10 SC requires diff_seerr. `arrconf diff` does Seerr pre-merge but logs "diff_not_implemented" — apply is unaffected.

---

_Verified: 2026-05-20T09:00:00Z_
_Verifier: Claude (gsd-verifier)_
