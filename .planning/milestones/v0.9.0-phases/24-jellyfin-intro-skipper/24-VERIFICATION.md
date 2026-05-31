---
phase: 24-jellyfin-intro-skipper
verified: 2026-05-31T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 24: Jellyfin Intro Skipper Verification Report

**Phase Goal:** The Jellyfin server can detect and skip intros, credits, and outros for web/app/Swiftfin users, with chapter markers benefiting all clients including Kodi; the entire setup is declared in `arrconf.yml` and reconciled idempotently by arrconf
**Verified:** 2026-05-31
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC#1 | `arrconf apply` logs Intro Skipper repo registered + plugin install queued; idempotent on second run | VERIFIED | `PACKAGES_INSTALLED_PATH` constant at reconciler line 64; `plugin_install_queued` warning at line 551; `_server_config_equivalent()` set-by-URL diff ensures idempotence; operator attestation in 24-03-SUMMARY.md: SC#1 PASS |
| SC#2 | After operator restart + second run, plugin Active in `GET /Plugins`, single intro-skipper.org repo (no dupes) | VERIFIED (operator-attested) | Two-run model enforced in `_reconcile_plugins()` — install `continue`s with no enable/config on same run; enable only when `Status not in _ACTIVE_PLUGIN_STATUSES`; `_server_config_equivalent()` set-by-URL prevents duplicate repo entries. Operator attestation: SC#2 PASS (2026-05-31) |
| SC#3 | Jellyfin web UI shows skip-intro/skip-credits button during playback on at least one series episode (dispositive) | VERIFIED (operator-attested) | Runtime behavior; not machine-checkable. RUNBOOK.md SC#3 result block filled: "Skip Intro button appeared: [x] YES / Skip Credits button appeared: [x] YES / Result: [x] PASS" (2026-05-31). 24-03-SUMMARY.md SC#3: PASS |
| SC#4 | `EnableChapterImageExtraction: true` on all 10 libraries via `GET /Library/VirtualFolders` | VERIFIED (operator-attested) | Code chain: `generate_jellyfin_libraries()` emits `enable_chapter_image_extraction=True` on all 10 libs (categories.py line 222); flows to `_create_library()` body (reconciler lines 141-145) and `_update_library_options()` helper (lines 252-281, called at line 376). Operator attestation: SC#4 PASS (2026-05-31) |
| SC#5 | Kodi spike result documented with binary accept/reject before phase declared complete (non-gating) | VERIFIED | INTRO-SKIPPER-RUNBOOK.md Step 11 SC#5 decision block filled: "DECISION: [x] ACCEPT — service.jellyskip works on this LibreELEC + Jellyfin 10.11.8 setup." (2026-05-31) |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected (from PLAN must_haves) | Status | Details |
|----------|---------------------------------|--------|---------|
| `tools/arrconf/arrconf/resources/jellyfin/plugin.py` | `install_guid` + `IntroSkipperConfig` model | VERIFIED | `install_guid: str | None = Field(default=None)` at line 46; `class IntroSkipperConfig` with `MaxParallelism: int = Field(default=1)` at line 20 |
| `tools/arrconf/arrconf/config.py` | `JellyfinLibrariesSection.enable_chapter_image_extraction` | VERIFIED | `enable_chapter_image_extraction: bool = Field(default=False, ...)` at line 544 |
| `tools/arrconf/arrconf/reconcilers/jellyfin.py` | `_update_library_options` helper + `plugin_install_queued` + `plugin_config_applied` + `PACKAGES_INSTALLED_PATH` | VERIFIED | `PACKAGES_INSTALLED_PATH = "/Packages/Installed"` at line 64; `def _update_library_options` at line 252; `plugin_install_queued` warning at line 551; `plugin_config_applied` at line 622; kubectl hint at line 557 |
| `charts/arr-stack/files/arrconf.yml` | Intro Skipper repo entry + GUID `c83d86bb-...` + `enable_chapter_image_extraction: true` | VERIFIED | GUID at line 310; version `1.10.11.19` at line 311; repo URL at line 312; `MaxParallelism: 1` at line 316; `enable_chapter_image_extraction: true` at line 251; repo `Intro Skipper` entry at lines 296-298 |
| `charts/arr-stack/values.yaml` | `arrconf.image.tag: "0.17.0"` (co-bump) | VERIFIED | `"0.17.0"` at line 451; renovate annotation `# renovate: image=ghcr.io/tom333/arr-stack-arrconf` preserved |
| `.planning/PROJECT.md` | ADR-9 — `install-capable` reversal of D-07-PLUGINS-01 | VERIFIED | `install-capable` appears at line 227; `D-07-PLUGINS-01` referenced; `Packages/Installed` mechanism documented |
| `.planning/phases/24-jellyfin-intro-skipper/INTRO-SKIPPER-RUNBOOK.md` | Two-run runbook with `kubectl rollout restart deployment/jellyfin` + `plugin_install_queued` + `EnableChapterImageExtraction` + `service.jellyskip` + `c83d86bb-...` | VERIFIED | All 5 acceptance-criteria patterns confirmed present (1, 7, 5, 5, 10 hits respectively); SC#3 and SC#5 result blocks filled with operator attestation |
| `tools/arrconf/tests/test_reconcilers_jellyfin_chapter_extraction.py` | 4 respx tests (create, update, no-op, dry-run) | VERIFIED | File exists (13.7 KB); 4 test functions confirmed: `test_chapter_extraction_enabled_on_library_create`, `test_chapter_extraction_update_existing_library`, `test_chapter_extraction_no_op_when_already_enabled`, `test_chapter_extraction_dry_run_no_post` |
| `tools/arrconf/tests/test_reconcilers_jellyfin_plugin_install.py` | 7 respx tests (install-queued, idempotent, no-install-fields, dry-run, config-applied, config-no-op, config-skipped-not-active) | VERIFIED | File exists (20.0 KB); all 7 test functions confirmed present |
| `schemas/arrconf-schema.json` | Valid JSON (regenerated after model changes) | VERIFIED | `python3 -c "import json; json.load(open('schemas/arrconf-schema.json'))"` exits 0 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `generators/categories.py` | `reconcilers/jellyfin.py` | `enable_chapter_image_extraction=True` → `_create_library()` body + `_update_library_options()` | WIRED | `generate_jellyfin_libraries()` emits flag at line 222; `_create_library()` reads `desired_lib.enable_chapter_image_extraction` at line 143; `_update_library_options()` called at line 376 |
| `arrconf.yml` plugin block | `reconcilers/jellyfin.py` `_reconcile_plugins()` | `PluginEntry.install_guid` drives `POST /Packages/Installed`; `PluginEntry.config` drives `POST /Plugins/{id}/Configuration` | WIRED | `entry.install_guid and entry.install_version and entry.install_repo_url` gate at line 536; `f"{PACKAGES_INSTALLED_PATH}/{entry.name}"` at line 543; config POST at line 621 |
| `arrconf.yml` server_config block | `reconcilers/jellyfin.py` `_reconcile_server_config()` | `plugin_repositories` (including Intro Skipper URL) serialized via `_server_config_equivalent()` set-by-URL | WIRED | `merged["PluginRepositories"] = [r.model_dump() for r in section.plugin_repositories]` at line 476; set-by-URL diff at lines 97-109 |
| Run N (`plugin_install_queued`) | Run N+1 (enable + config) | Manual operator restart documented in INTRO-SKIPPER-RUNBOOK.md; code enforces separation via `continue` after install | WIRED | `actions.append(f"plugin_install_queued:{entry.name}")` then `continue` at lines 560-572; config loop checks `cluster.get("Status") not in _ACTIVE_PLUGIN_STATUSES` at line 610 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `reconcilers/jellyfin.py _create_library()` | `desired_lib.enable_chapter_image_extraction` | `generate_jellyfin_libraries()` via `JellyfinLibrary` pydantic model | Yes — generator always emits `True`; flows to POST body | FLOWING |
| `reconcilers/jellyfin.py _update_library_options()` | `cluster_lib.get("LibraryOptions")` | `client.get(LIBRARY_VIRTUALFOLDERS_PATH)` — live cluster GET | Yes — diffs against real cluster value | FLOWING |
| `reconcilers/jellyfin.py _reconcile_plugins()` install path | `entry.install_guid/install_version/install_repo_url` | `arrconf.yml` → pydantic `PluginEntry` | Yes — concrete values `c83d86bb-a1e0-4c35-a113-e2101cf4ee6b` / `1.10.11.19` / `https://intro-skipper.org/manifest.json` | FLOWING |
| `reconcilers/jellyfin.py _reconcile_plugins()` config path | `cluster_config` | `client.get(f"{PLUGINS_PATH}/{plugin_id}/Configuration")` — live cluster GET | Yes — diffs against real cluster plugin config | FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED for live cluster behavior (SC#2, SC#3, SC#4) — requires running Jellyfin server; operator attestation is the applicable evidence. The following code-level checks were run:

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `schemas/arrconf-schema.json` is valid JSON | `python3 -c "import json; json.load(open('schemas/arrconf-schema.json'))"` | exit 0 | PASS |
| `_update_library_options` appears ≥2 times (def + call) | `grep -c _update_library_options reconcilers/jellyfin.py` | 2 | PASS |
| `PACKAGES_INSTALLED_PATH` appears ≥2 times (const + use) | `grep -c PACKAGES_INSTALLED_PATH reconcilers/jellyfin.py` | 2 (lines 64, 543) | PASS |
| `plugin_install_queued` in reconciler code | `grep -c plugin_install_queued reconcilers/jellyfin.py` | 1 | PASS |
| `plugin_config_applied` in reconciler code | `grep -c plugin_config_applied reconcilers/jellyfin.py` | 1 | PASS |
| 4 chapter-extraction tests exist | `grep -c "def test_" test_reconcilers_jellyfin_chapter_extraction.py` | 4 | PASS |
| 7 plugin-install tests exist | `grep -c "def test_" test_reconcilers_jellyfin_plugin_install.py` | 7 | PASS |
| kubectl hint embedded in reconciler code (not just comment) | `grep -c 'rollout restart deployment/jellyfin' reconcilers/jellyfin.py` | 1 (line 557) | PASS |
| Co-bump: values.yaml tag `0.17.0` | `grep '0\.17\.0' charts/arr-stack/values.yaml` | found at line 451 | PASS |
| `install-capable` in PROJECT.md (ADR-9) | `grep -c install-capable .planning/PROJECT.md` | 1 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| JFSKIP-01 | 24-01 | arrconf registers Intro Skipper plugin repo declaratively in Jellyfin `plugin_repositories`, idempotent | SATISFIED | Repo entry in `arrconf.yml` lines 295-298; `_server_config_equivalent()` set-by-URL idempotence (reconciler lines 97-109); operator SC#1 PASS (no duplicate repos confirmed) |
| JFSKIP-02 | 24-02 | arrconf installs plugin when absent via `POST /Packages/Installed`; distinguishes queued-install vs active; runbook documents the single restart | SATISFIED | `PACKAGES_INSTALLED_PATH` constant + install branch (reconciler lines 536-560); `plugin_install_queued` action + warning with kubectl hint; INTRO-SKIPPER-RUNBOOK.md Step 4 documents the single manual `kubectl rollout restart deployment/jellyfin -n selfhost`; operator SC#2 PASS |
| JFSKIP-03 | 24-02 | Intro + credits detection activated via plugin config; off-peak fingerprint scheduling with concurrency capped (`MaxParallelism`) | SATISFIED | Config loop in `_reconcile_plugins()` (lines 606-623); `IntroSkipperConfig(AutoSkip=False, AutoSkipCredits=False, MaxParallelism=1)` in `plugin.py`; arrconf.yml config block with `MaxParallelism: 1`; RUNBOOK.md Step 6 documents off-peak Scheduled Tasks configuration. Note: REQUIREMENTS.md uses `MaxConcurrentTasks` but actual Jellyfin plugin field (confirmed from Configuration.cs PascalCase convention) is `MaxParallelism` — confirmed in 24-02-SUMMARY.md and consistent with implementation |
| JFSKIP-04 | 24-01 | `EnableChapterImageExtraction` via LibraryOptions activated on all 10 category libraries | SATISFIED | Generator emits `enable_chapter_image_extraction=True` on all 10 libs (categories.py line 222); `_create_library()` posts `{"LibraryOptions": {"EnableChapterImageExtraction": True}}` (reconciler lines 141-145); `_update_library_options()` handles existing libraries (lines 252-281, called at line 376); operator SC#4 PASS |
| JFSKIP-05 | 24-03 | Skip-intro works on web/app/Swiftfin (committed); Kodi service.jellyskip spike documented with binary accept/reject before phase complete | SATISFIED | RUNBOOK.md SC#3 block: Skip Intro YES, Skip Credits YES, PASS (web client, 2026-05-31); RUNBOOK.md SC#5 block: "DECISION: [x] ACCEPT — service.jellyskip works on this LibreELEC + Jellyfin 10.11.8 setup." (2026-05-31) |

**Note on REQUIREMENTS.md traceability table:** The JFSKIP-01..05 rows still show `Pending` and `[ ]` checkboxes in REQUIREMENTS.md. This is a documentation-only gap (the table was not updated after phase completion). The underlying requirements are fully satisfied in code and by operator attestation. This is tracked as a WARNING below but does not block the phase goal.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `reconcilers/jellyfin.py` docstring line 24 | 24 | Docstring still says "activation-only: no install, no uninstall, no prune" for D-07-PLUGINS-01 — refers to old behavior before Phase 24 reversal | INFO | Documentation drift only; reconciler code correctly implements install-capable behavior. No behavioral impact |
| `.planning/REQUIREMENTS.md` | 69-73 | JFSKIP-01..05 traceability rows still show `Pending` status; `[ ]` checkboxes not updated to `[x]` | WARNING | Documentation gap; does not affect code correctness or goal achievement |
| `.planning/ROADMAP.md` | 118, 138 | Phase 24 row shows `[ ]` (incomplete); plan 24-03 shows `[ ]` — not updated after live verification closed | WARNING | Documentation gap; does not affect code correctness |
| `snapshots/` | — | No `before-phase-24-*/` or `after-phase-24-*/` snapshot directories committed (ADR-6 deviation) | WARNING | Documented deviation in 24-03-SUMMARY.md: "operator performed the live two-run verification against the production cluster directly; no snapshot directories were committed." Third dry-run idempotence confirmed operator-side. Risk assessed as low (install-only, no destructive ops) |

---

### Human Verification Required

The following were verified by operator attestation on 2026-05-31 and are documented in INTRO-SKIPPER-RUNBOOK.md and 24-03-SUMMARY.md. No further human verification required:

- **SC#2 (plugin Active, no duplicate repos):** Operator confirmed via `GET /Plugins` and `GET /System/Configuration` curl checks on live cluster.
- **SC#3 (skip button during playback):** Operator confirmed Skip Intro + Skip Credits buttons appeared in Jellyfin web client. This is the dispositive success criterion.
- **SC#4 (EnableChapterImageExtraction on all 10 libraries):** Operator confirmed via `GET /Library/VirtualFolders` against production Jellyfin 10.11.8.
- **SC#5 (Kodi service.jellyskip spike):** Operator recorded ACCEPT decision (service.jellyskip worked on LibreELEC salon box).

No items remain pending human verification.

---

### Gaps Summary

No blocking gaps found. Three WARNING-level documentation gaps exist:

1. **REQUIREMENTS.md traceability table:** JFSKIP-01..05 rows show `Pending` / `[ ]` — not updated post-completion. Documentation only; no behavioral impact.
2. **ROADMAP.md plan/phase markers:** Phase 24 and plan 24-03 show `[ ]` — not updated post-completion. Documentation only.
3. **ADR-6 snapshots:** `snapshots/before-phase-24-*/` and `after-phase-24-*/` not committed to repo. Accepted deviation: install-only writes, idempotence confirmed on third dry-run, forensic risk assessed as low.

These are cosmetic tracking gaps from the documentation layer, not code gaps. All 5 JFSKIP requirements are satisfied in the codebase and confirmed live on production. The phase goal is achieved.

---

### Observations

**MaxConcurrentTasks vs MaxParallelism (JFSKIP-03):** REQUIREMENTS.md uses `MaxConcurrentTasks` in the requirement description, but the actual Intro Skipper plugin configuration field is `MaxParallelism` (confirmed from plugin source Configuration.cs PascalCase convention, documented in 24-02-SUMMARY.md). The implementation uses the correct field name. The REQUIREMENTS.md wording is a documentation imprecision, not a gap.

**Co-bump deviation (0.15.0 → 0.17.0 instead of 0.16.0):** Plan 02 SUMMARY documents this as a pre-authorized deviation override — Plan 01 already consumed `0.16.0` in a parallel worktree. Final tag `0.17.0` is correct and confirmed in `values.yaml`. The ROADMAP plan 24-02 description still says "co-bump 0.16.0" but the actual tag is `0.17.0`.

---

_Verified: 2026-05-31_
_Verifier: Claude (gsd-verifier)_
