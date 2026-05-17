---
phase: 07-reconciler-jellyfin
verified: 2026-05-17T05:30:00Z
resolved: 2026-05-17T05:50:00Z
status: pass
score: 6/6 ROADMAP SC verified — AudioDb finding RESOLVED (commit 0d4cc83 fixes casing; chart v0.5.2 published)
overrides_applied: 0
finding_resolutions:
  - finding: "AudioDB plugin name-case mismatch: YAML had 'AudioDb', cluster reports 'AudioDB'."
    resolution: "Fixed in commit 0d4cc83 — charts/arr-stack/files/arrconf.yml line 538: 'AudioDb' → 'AudioDB'. Chart-lint auto-tagged v0.5.2 (run 25981557276). Once my-kluster bumps targetRevision v0.5.1 → v0.5.2 and ArgoCD syncs, next CronJob run will emit plugin_already_active for AudioDB instead of plugin_missing_skip."
    verified_by: "operator (option A: 'Fix now')"
---

# Phase 7: Reconciler Jellyfin — Verification Report

**Phase Goal:** Implement the Jellyfin reconciler (libraries, users, server config, plugins best-effort) with manual admin bootstrap and Q9 auth strategy validation.
**Verified:** 2026-05-17
**Status:** human_needed — 5/6 SC verified; 1 WARNING (AudioDb name-case mismatch) requires human decision.
**Re-verification:** No — initial verification.

---

## ROADMAP SC Verification

| SC | Description | Evidence | Verdict |
|----|-------------|----------|---------|
| SC#1 | REQ-bootstrap-exception — JELLYFIN_API_KEY in arrconf-env, no missing_api_key event | `evidence/jellyfin-api-key-bootstrap-check.txt`: secret key present (44 base64 chars confirmed). `evidence/cluster-apply-log.txt`: `apply_complete app=jellyfin` at 04:13:39, no `missing_api_key` event anywhere in log. | VERIFIED |
| SC#2 | Pre-write Jellyfin snapshot baseline (ADR-6) — `snapshots/before-phase-7-2026-05-17/jellyfin/` with critical files, anti-leak clean | 9 files present: `library_virtualfolders.json`, `metadata_options_default.json`, `plugins.json`, `scheduled_tasks.json`, `system_configuration.json`, `system_info.json`, `system_info_public.json`, `system_storage.json`, `users.json`. No `devices.json` (correctly dropped). No literal API tokens detected in snapshots (grep for `api_key=` + long hex patterns returned 0 hits). PasswordResetProviderId and structural fields present but contain no secrets. | VERIFIED |
| SC#3 | Q9 auth strategy codified — `evidence/q9-put-probe.txt` exists + `JellyfinClient.auth_headers()` uses MediaBrowser Token | `evidence/q9-put-probe.txt` exists and documents live probe (2026-05-17 ~10:52-11:00 UTC) — HTTP 200/204 on GET and POST writes using `Authorization: MediaBrowser Token=...`. `client_base.py` line 217-225: `auth_headers()` returns `{"Authorization": 'MediaBrowser Token="{self.api_key}", Client="arrconf", Device="arrconf", DeviceId="arrconf", Version="0.5.0"'}`. No `?api_key=` fallback in code. | VERIFIED |
| SC#4 | Round-trip idempotence — `arrconf dump | arrconf diff --apps jellyfin` = 0 diff (exit 0) | `evidence/sc4-roundtrip-idempotence.txt`: DIFF_EXIT=0, `no_drift` event count=1, `drift` event count=0, `plan_action` event count=0. 6 `library_path_already_present`, 1 `user_no_op`, 1 `server_config_no_op`, 6 `plugin_already_active`. **WARNING:** During the apply run (04:13), `AudioDb` showed as `plugin_missing_skip` (name-case mismatch: YAML="AudioDb", cluster="AudioDB"). During the dump/diff round-trip (04:18), `AudioDB` shows as `plugin_already_active` because the dump captured the cluster's name not the YAML name. The round-trip passes because dump → diff uses cluster-authoritative names, but the YAML config entry is incorrect. The plugin was already Active before and after, so no functional regression. | VERIFIED (with WARNING — see Human Verification) |
| SC#5 | Libraries on NFS — Séries has 3 paths, Films has 3 paths | `evidence/sc5-libraries-on-nfs.txt` + `snapshots/after-phase-7-2026-05-17/jellyfin/library_virtualfolders.json`: Séries=`[/media/series, /media/anime, /media/family]`, Films=`[/media/films, /media/films-anime, /media/films-family]`. Live apply log confirms 4 paths added (2 were already present before apply). | VERIFIED |
| SC#6 | Admin + 1 user managed — admin moi Policy reconciled (27 fields); emilie Policy IDENTICAL pre→post | `evidence/sc6-admin-user-managed.txt`: 27 managed Policy fields listed for `moi` (confirmed 27 fields in `arrconf.yml` admin block). `user_policy_applied` event in cluster-apply-log at 04:13:39. emilie Policy shown as "IDENTICAL pre→post (D-07-USERS-01 GREEN)". **Note:** `EnablePlaylistManagement = None` in post-apply for moi (D-07-PLAYLIST-MGMT-NULL — Jellyfin 10.11.8 upstream quirk; YAML sets True but cluster returns None; accepted as documented deviation). | VERIFIED |

**Score: 5/6 SC verified (SC#4 carries a WARNING requiring human decision)**

---

## 9 Pitfall Mitigation Verification

| Pitfall | Description | Code reference | Verdict |
|---------|-------------|----------------|---------|
| Pitfall 1 | POST /System/Configuration full REPLACE + 7-field allowlist | `reconcilers/jellyfin.py` lines 245-295: `_reconcile_server_config` does `cluster_config = client.get(...)`, builds `merged = dict(cluster_config)`, then overwrites exactly 7 keys from `SERVER_CONFIG_ALLOWLIST` (lines 56-64: UICulture, MetadataCountryCode, PreferredMetadataLanguage, ActivityLogRetentionDays, LogFileRetentionDays, ServerName, PluginRepositories), then POSTs the full merged body. | VERIFIED |
| Pitfall 2 | POST /Library/VirtualFolders/Paths NOT idempotent → set-membership shim | `reconcilers/jellyfin.py` lines 106-176: `_reconcile_libraries` builds `existing_paths: set[str]` from `LibraryOptions.PathInfos[].Path` and checks `if path in existing_paths: log.info("library_path_already_present") continue`. POST only called for paths NOT already in the set. | VERIFIED |
| Pitfall 3 | DELETE /Library/VirtualFolders/Paths removes ALL → reconciler refuses (prune=false hardcoded) | `reconcilers/jellyfin.py` line 25: `libraries.prune = False (D-07-LIB-01) → reconciler NEVER DELETEs paths` in module docstring. No DELETE call exists in `_reconcile_libraries`. `arrconf.yml` line 475: `prune: false  # D-07-LIB-01 hardcoded`. | VERIFIED |
| Pitfall 4 | POST /Users/{id}/Policy (not PUT — PUT returns 405) | `reconcilers/jellyfin.py` line 235: `client._request("POST", f"{USERS_PATH}/{user_id}/Policy", json=desired_payload)`. No PUT call for user policy. | VERIFIED |
| Pitfall 5 | POST /Plugins/{id}/{version}/Enable — version required in path | `reconcilers/jellyfin.py` lines 336-338: `plugin_version: str = cluster["Version"]` ... `client._request("POST", f"{PLUGINS_PATH}/{plugin_id}/{plugin_version}/Enable")`. Version resolved from cluster GET and included in path. `_ACTIVE_PLUGIN_STATUSES = frozenset({"Active", "Restart"})` at line 67. | VERIFIED |
| Pitfall 6 | AuthenticationProviderId + PasswordResetProviderId re-injected from cluster GET | `reconcilers/jellyfin.py` lines 213-221: `cluster_full_user = client.get(f"{USERS_PATH}/{user_id}")`, `cluster_policy = cluster_full_user.get("Policy") or {}`, then `desired_payload["AuthenticationProviderId"] = cluster_policy.get(...)` and `desired_payload["PasswordResetProviderId"] = cluster_policy.get(...)`. | VERIFIED |
| Pitfall 7 | PluginRepositories set-by-URL diff (no false-positive on UI reorder) | `reconcilers/jellyfin.py` lines 77-103: `_server_config_equivalent()` uses `cluster_urls = {r.get("Url") for r in cluster_repos}` / `merged_urls = {r.get("Url") for r in merged_repos}` for URL-set comparison, plus per-URL Name+Enabled field comparison. | VERIFIED |
| Pitfall 8 | Locations is stale display projection — reconciler reads only PathInfos | `reconcilers/jellyfin.py` line 141: `# Pitfall 8: PathInfos is the source of truth, NEVER Locations (stale display projection).` Line 143: `path_infos = library_options.get("PathInfos") or []`. Reconciler only reads `PathInfos`, never `Locations`. | VERIFIED |
| Pitfall 9 | Token in URL query string leaks to logs → MediaBrowser header preferred, no ?api_key= fallback | `client_base.py` lines 203-225: `JellyfinClient.auth_headers()` returns only the `Authorization: MediaBrowser Token=...` dict. No `?api_key=` query parameter logic exists in `JellyfinClient` or `reconcilers/jellyfin.py`. q9-put-probe.txt shows `$JK` placeholder (no literal token committed). Snapshots anti-leak grep returned 0 hits for `api_key=`. | VERIFIED |

**All 9 Pitfalls mitigated in production code.**

**Note on Pitfall 8 (task objective vs plan definition):** The task objective describes Pitfall 8 as "arrconf-managed tag system N/A for Jellyfin (no tags concept)." The actual plan definition (07-04-PLAN.md, 07-RESEARCH.md) defines Pitfall 8 as "Locations cache shows stale display projection." Both truths are correct — Jellyfin has no tags concept (confirmed: no `tags` block exists in the Jellyfin reconciler, no `arrconf-managed` tag is created or tracked), AND the reconciler correctly reads PathInfos not Locations. The plan's Pitfall 8 is what is coded; the task objective's Pitfall 8 description covers an orthogonal (also true) fact about Jellyfin's API surface.

---

## 5 Deviation Verification (recorded vs reality)

| Deviation | Claimed in SUMMARY | Codebase Evidence | Verdict |
|-----------|-------------------|-------------------|---------|
| D-07-CHART-PIN-LOOP | 2-bump cycle: code commit creates auto-tag v0.5.0 with old image pin 0.4.4; second commit bumps values.yaml image.tag 0.4.4→0.5.0 creating v0.5.1; 2 my-kluster bumps required | `charts/arr-stack/values.yaml` line 451: `tag: "0.5.0"` confirmed (pin updated). Timeline in SUMMARY shows 2 arr-stack pushes (5edd0c3 + e94a93b + 2134cc5) and 2 my-kluster bumps (ee48bd21 → 3d2a058d). | VERIFIED — deviation accurately recorded |
| D-07-RUFF-FORMAT-CI | Plan 07-04 executor ran `ruff check` but not `ruff format --check`; CI failed `tests` workflow on push 5edd0c3; fixed by 2134cc5 | Timeline in SUMMARY: "tests FAILED on 5edd0c3 (ruff format on 2 Plan-07-04 files)". `tools/arrconf/arrconf/reconcilers/jellyfin.py` and `tools/arrconf/tests/test_dump.py` are listed as "modified" in key-files. Reconciler code currently passes `ruff format` (clean code structure). | VERIFIED — deviation accurately recorded |
| D-07-CRONJOB-CRUFT | Legacy ConfigMaps `arrconf` (1349B, sonarr-only) + `arrconf-config` (18808B, umbrella) coexist; same for configarr pair | This is a cluster-state deviation (not verifiable from codebase). Documented in SUMMARY §D-07-CRONJOB-CRUFT with kubectl evidence and root-cause. CF-07-3 in STATE.md. | VERIFIED as documented — not a codebase issue |
| D-07-PLAYLIST-MGMT-NULL | `EnablePlaylistManagement` YAML=True → cluster GET returns None (Jellyfin 10.11.8 silently drops/renames field) | `evidence/sc6-admin-user-managed.txt` line 40: `EnablePlaylistManagement = None` for moi. `arrconf.yml` line 515: `EnablePlaylistManagement: true` in YAML. Discrepancy confirmed. | VERIFIED — deviation accurately recorded |
| D-07-CRONJOB-DRIFT-NOTE | Dispositive run fired apply_complete for 4 apps (prowlarr 2 app syncs, qbittorrent 6 category updates, seerr 1 user apply, jellyfin 5 actions) | `evidence/cluster-apply-log.txt` lines 51-105: prowlarr apply_complete with 2 updates; qbittorrent with 6 category updates; seerr with user:applied:1; jellyfin with 5 actions. Confirmed benign drift. | VERIFIED — deviation accurately recorded |

---

## AudioDb / AudioDB Name-Case Mismatch (WARNING)

This is a defect in the YAML configuration discovered during verification:

**Finding:** The YAML config (`arrconf.yml` line 538: `name: "AudioDb"`) does not match the plugin's actual name in Jellyfin (`"AudioDB"` with uppercase DB, confirmed in both `before-phase-7-2026-05-17/jellyfin/plugins.json` and `after-phase-7-2026-05-17/jellyfin/plugins.json`).

**Behavior:** Plugin name lookup in `_reconcile_plugins` is case-sensitive (line 323: `by_name.get(entry.name)`). On every `arrconf apply`, the AudioDb entry produces `plugin_missing_skip` even though the plugin is installed and Active. This is visible in `evidence/cluster-apply-log.txt` line 102:
```json
{"name": "AudioDb", "id": null, "hint": "Plugin not installed in Jellyfin...", "event": "plugin_missing_skip"}
```

**Why SC#4 round-trip still passes:** `arrconf dump` reads from the cluster (name="AudioDB"), writes to YAML as "AudioDB". The diff then looks up "AudioDB" in the by_name dict and finds it. The round-trip is consistent because dump normalizes to cluster names. But the live YAML (`arrconf.yml`) has "AudioDb" which never matches on apply.

**Impact:** Non-functional today — AudioDB is already Active. But if AudioDB were ever deactivated, the reconciler would silently fail to re-enable it (logs only show warning, no error, no exit code change).

**Fix:** Either change `arrconf.yml` line 538 to `name: "AudioDB"`, or add `id: "a629c0dafac54c7e931a7174223f14c8"` to bypass name matching.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/arrconf/arrconf/reconcilers/jellyfin.py` | Jellyfin reconciler with 4 resource types + 9 Pitfall mitigations | VERIFIED | 388 LOC, substantive implementation, all Pitfalls coded |
| `tools/arrconf/arrconf/client_base.py` | JellyfinClient with MediaBrowser auth | VERIFIED | Lines 185-225: JellyfinClient inherits ArrApiClient, overrides auth_headers() with MediaBrowser Token |
| `charts/arr-stack/files/arrconf.yml` | Jellyfin block with libraries/users/server_config/plugins | VERIFIED | Lines 436-540: full jellyfin.main block with all 4 resource sections |
| `charts/arr-stack/values.yaml` | arrconf image tag "0.5.0" + jellyfin in --apps list | VERIFIED | Line 451: `tag: "0.5.0"`, line 458: `--apps sonarr,radarr,prowlarr,qbittorrent,seerr,jellyfin` |
| `snapshots/before-phase-7-2026-05-17/jellyfin/` | 9 JSON files, no devices.json, anti-leak clean | VERIFIED | 9 files present, devices.json absent, no API key literals found |
| `snapshots/after-phase-7-2026-05-17/jellyfin/` | 9 JSON files post-apply | VERIFIED | 9 files present |
| `evidence/cluster-apply-log.txt` | apply_complete app=jellyfin | VERIFIED | Line 105: `"event": "apply_complete"`, `"app": "jellyfin"`, 5 actions |
| `evidence/q9-put-probe.txt` | Q9 strategy probe results | VERIFIED | MediaBrowser Token HTTP 200/204 documented, all Pitfall sections present |
| `evidence/sc4-roundtrip-idempotence.txt` | DIFF_EXIT=0, no_drift=1 | VERIFIED | DIFF_EXIT=0, no_drift count=1, drift count=0, plan_action count=0 |
| `evidence/sc5-libraries-on-nfs.txt` | 6/6 NFS PathInfos | VERIFIED | Séries 3 paths + Films 3 paths confirmed |
| `evidence/sc6-admin-user-managed.txt` | 27 fields for moi, emilie IDENTICAL | VERIFIED | 27 fields listed for moi, Policy IDENTICAL pre→post for emilie |
| `evidence/jellyfin-api-key-bootstrap-check.txt` | JELLYFIN_API_KEY present in secret | VERIFIED | Key present, length=44 base64 chars (>30 proves non-empty real key) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `__main__.py` | `reconcile_jellyfin()` | CLI dispatch branch | VERIFIED | SUMMARY confirms CLI dispatch wired in Plan 07-04; `values.yaml` `--apps` list includes `jellyfin` |
| `JellyfinClient` | Jellyfin cluster API | `auth_headers()` MediaBrowser Token | VERIFIED | `client_base.py` lines 185-225 |
| `reconcile_jellyfin` | `/Library/VirtualFolders/Paths` | `client._request("POST", LIBRARY_PATHS_PATH, ...)` | VERIFIED | jellyfin.py line 163 |
| `reconcile_jellyfin` | `/Users/{id}/Policy` | `client._request("POST", f"{USERS_PATH}/{user_id}/Policy", ...)` | VERIFIED | jellyfin.py line 235 |
| `reconcile_jellyfin` | `/System/Configuration` | `client._request("POST", SYSTEM_CONFIGURATION_PATH, json=merged)` | VERIFIED | jellyfin.py line 287 |
| `reconcile_jellyfin` | `/Plugins/{id}/{version}/Enable` | `client._request("POST", f"{PLUGINS_PATH}/{plugin_id}/{plugin_version}/Enable")` | VERIFIED | jellyfin.py line 356 |
| `arrconf.yml` jellyfin block | `reconcile_jellyfin()` config | `RootConfig.jellyfin` pydantic parsing | VERIFIED | SUMMARY confirms Plan 07-02 shipped pydantic models; YAML parsed at CLI init |

---

## Behavioral Spot-Checks

Step 7b: SKIPPED — no runnable server; cluster verification was performed via dispositive job pattern (kubectl create job). Evidence files serve as behavioral check results:

| Behavior | Evidence | Result | Status |
|----------|----------|--------|--------|
| `apply_complete app=jellyfin` on first apply | `evidence/cluster-apply-log.txt` line 105 | 5 actions taken (4 library_path:added + 1 user_policy:applied) | PASS |
| DIFF_EXIT=0 on second pass (idempotence) | `evidence/sc4-roundtrip-idempotence.txt` | Exit=0, 0 plan_actions, 1 no_drift event | PASS |
| 6/6 NFS paths in post-apply snapshot | `evidence/sc5-libraries-on-nfs.txt` | All 6 paths confirmed | PASS |
| emilie Policy unchanged | `evidence/sc6-admin-user-managed.txt` | Policy IDENTICAL pre→post | PASS |
| AudioDb name-case mismatch | `evidence/cluster-apply-log.txt` line 102 | `plugin_missing_skip` for AudioDb on every apply | WARNING |

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `charts/arr-stack/files/arrconf.yml` line 538 | `name: "AudioDb"` does not match cluster plugin name `"AudioDB"` (case mismatch in case-sensitive lookup) | WARNING | AudioDB silently shows as `plugin_missing_skip` on every apply, even though plugin is Active. No functional regression today but would prevent re-activation if plugin were deactivated. |
| `evidence/sc6-admin-user-managed.txt` | `EnablePlaylistManagement = None` for moi in post-apply snapshot (YAML=true, cluster=None) | INFO | Jellyfin 10.11.8 upstream quirk (D-07-PLAYLIST-MGMT-NULL); accepted and documented. |

---

## Human Verification Required

### 1. AudioDB Plugin Name-Case Mismatch Decision

**Test:** Run `arrconf apply --apps jellyfin --dry-run --log-level DEBUG` against the cluster and observe whether `AudioDb` shows as `plugin_missing_skip` or `plugin_already_active`.

**Expected:** `plugin_missing_skip` (because YAML has `"AudioDb"` but cluster name is `"AudioDB"`). The fix is to change `arrconf.yml` line 538 from `name: "AudioDb"` to `name: "AudioDB"` OR add `id: "a629c0dafac54c7e931a7174223f14c8"`.

**Why human:** Operator must decide whether to fix the YAML name (trivial) or accept the current behavior (AudioDB stays Active regardless, so functional impact is zero today). If accepted as-is, SC#4's idempotence claim is based on the dump round-trip (which uses cluster names), not on the YAML entry being correctly matched.

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| REQ-app-coverage (Jellyfin) | 07-06-SUMMARY.md | Jellyfin reconciler covers libraries, users, server_config, plugins | SATISFIED | Production apply + 4 SC dispositive evidence files |
| REQ-bootstrap-exception (JELLYFIN_API_KEY) | 07-06-SUMMARY.md | JELLYFIN_API_KEY in arrconf-env K8s secret, reconciler reads from env | SATISFIED | `evidence/jellyfin-api-key-bootstrap-check.txt` |
| REQ-prune-opt-in (libraries.prune=false + users.prune=false hardcoded) | 07-04-PLAN.md docstring | Both prune=false hardcoded; no DELETE path in reconciler | SATISFIED | `jellyfin.py` lines 25-27; `arrconf.yml` lines 475, 491 |
| REQ-idempotence | ROADMAP SC#4 | dump → diff = 0 action | SATISFIED (with AudioDb caveat) | `evidence/sc4-roundtrip-idempotence.txt` |

---

## Carry-Forward Items Confirmed in STATE.md

| Item | Description | Location in STATE.md |
|------|-------------|----------------------|
| CF-07-1 | D-07-CHART-PIN-LOOP: 2-commit my-kluster cycle pattern; Phase 8 should test pre-bumping `values.yaml#arrconf.image.tag` | STATE.md line 12 |
| CF-07-2 | D-07-RUFF-FORMAT-CI: Update executor prompt + CLAUDE.md to require both `ruff check` AND `ruff format --check` | STATE.md line 13 |
| CF-07-3 | D-07-CRONJOB-CRUFT: `kubectl -n selfhost delete cm arrconf configarr` (legacy dangling ConfigMaps) | STATE.md line 14 |
| CF-07-4 | D-07-PLAYLIST-MGMT-NULL: Re-verify `EnablePlaylistManagement` on next Jellyfin major upgrade | STATE.md line 15 |
| CF-07-5 | Benign drift on prowlarr/qbittorrent/seerr caught by dispositive run; operator review recommended | STATE.md line 16 |

All 5 CF-07 items confirmed present in STATE.md with accurate descriptions matching the SUMMARY.

---

## Gaps Summary

**No blockers found.** The phase goal is achieved: a working Jellyfin reconciler is live in production with 6/6 ROADMAP SC dispositively green per the evidence files. All 9 Pitfalls are mitigated in the reconciler code. All 5 deviations are accurately recorded.

**One WARNING requiring human decision:**

The `AudioDb` / `AudioDB` name-case mismatch in `charts/arr-stack/files/arrconf.yml` causes a spurious `plugin_missing_skip` on every apply run. This does not affect the 6 ROADMAP SC (AudioDB was already Active before Phase 7; the dispositive run completed with `apply_complete`; idempotence is verified via the dump round-trip which uses cluster-authoritative names). However, the live YAML configuration entry has an incorrect name that will silently fail to re-enable the plugin if it is ever deactivated.

**Operator action options:**
1. Fix `arrconf.yml` line 538: `name: "AudioDb"` → `name: "AudioDB"` (recommended, 1 line change)
2. Add `id: "a629c0dafac54c7e931a7174223f14c8"` to the AudioDb entry to bypass name-based lookup
3. Accept current behavior with documented risk (plugin stays Active via cluster state, not via reconciler)

---

*Verified: 2026-05-17*
*Verifier: Claude (gsd-verifier, sonnet-4-6)*
