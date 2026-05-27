---
phase: 21-filesystem-metadata-migration
verified: 2026-05-27T00:00:00Z
status: human_needed
score: 5/5 truths verified (SC2/SC3 with a partial-pass caveat — see below)
verdict: PASS-WITH-CONCERNS
overrides_applied: 0
human_verification:
  - test: "Radarr UI / GET /api/v3/movie + /api/v3/wanted/missing — enumerate the 10 both_missing items (movies + series) that point at a Category root folder with NO file on disk"
    expected: "10 records show as MISSING on disk; operator decides per-item (re-download via monitored search OR remove from the *arr). 1 item (Winx Club 2004) has a real file."
    why_human: "Cluster no longer reachable (port-forwards torn down); the committed snapshots capture rootfolder.json + config, NOT the per-movie file-present state. Live curl required."
  - test: "Jellyfin GET /Library/VirtualFolders — confirm each of the 10 Category libs reports ItemCount > 0"
    expected: "No lib went empty post-refresh. ItemCount populates async after /Library/Refresh."
    why_human: "library_virtualfolders.json in the post-snapshot lists the 10 libs but ItemCount is async/best-effort; SC5 'ItemCount > 0' is a live-state assertion that can drift if the 10 missing-on-disk items emptied a lib."
  - test: "qBit re-hash sanity — confirm the 37 relocated torrents did not enter an errored/re-checking state after setLocation"
    expected: "torrent state preserved (downloading/seeding/stalled); no re-hashing failure (SC4 sub-clause)."
    why_human: "torrents_info.json post-snapshot confirms save_path+category for all 37, but a transient post-setLocation re-check state would not be captured; SUMMARY records 'no halt' which implies success but state-preservation is a live observation."
concerns_for_phase_22:
  - "10 both_missing Radarr/Sonarr records now point at Category root folders with no file on disk — will surface as MISSING. Phase 22 / operator must decide per-item (re-download or remove). Tracked in STATE.md close-out notes."
  - "Leftover bare `series-zoe/Winx Club` (no year) dir beside the moved `Winx Club (2004)` — harmless, operator may prune."
  - "3 PRUNE_PHASE_22 orphan torrents still on /data/complete — Phase 22 owns the prune-vs-unsorted decision (confirmed still present in post-snapshot)."
---

# Phase 21: Filesystem + metadata migration — Verification Report

**Phase Goal:** Move every item identified in Phase 20 audit to its Category target — filesystem `mv` on the Jellyfin NFS volume + qBit `setLocation` + Radarr/Sonarr API mutations + post-migration re-scans — leaving the cluster functional throughout.
**Verified:** 2026-05-27
**Status:** human_needed
**Verdict:** PASS-WITH-CONCERNS
**Re-verification:** No — initial verification

## Verdict

**PASS-WITH-CONCERNS.** The migration *mechanism* worked end-to-end with no halt: all 21 *arr API PUTs succeeded, all 37 qBit torrents were relocated + recategorized, the Jellyfin global refresh dispatched, and ADR-6 pre/post snapshots are committed with a bounded diff. The script and its 3 mid-run deviation fixes are present, Triade-green, and honor every locked D-21-* decision. **However**, an audit-vs-disk drift discovered at apply time means 10 of 11 filesystem-move items were `both_missing` (files removed between the 2026-05-25 audit and the 2026-05-27 run). Per operator decision, the script soft-skipped the missing files and synced the DB anyway. So SC2/SC3's "file present on disk at the new path" sub-clause is only true for 1 of 11 FS-move items (Winx Club). The DB is correctly Category-anchored; the *catalog* now has a chunk of missing-on-disk records needing operator follow-up. This is a real, honestly-disclosed gap — not a clean PASS, not a FAIL.

## Goal Achievement — Observable Truths (ROADMAP SC1–SC5)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | ADR-6 pre + post snapshots committed; diff confirms only expected mutations | ✓ VERIFIED | `git log --grep="snapshot(21)"` → `0dad89c` (pre) + `bfdd8a2` (post). Both dirs on disk, 54 files each, `git ls-files` confirms committed. `diff -rq` bounded to exactly 4 files: qBit torrents_info, Jellyfin scheduled_tasks + system_storage (refresh ran), Radarr rootfolder (freeSpace + unmappedFolders cleared). 0 secret leaks. **Independently verified from committed artifacts.** |
| SC2 | Radarr movies on Category rootFolderPath + path + tag, file on disk, no monitored regression | ⚠ PARTIAL PASS | rootFolderPath/tag/path API mutations: 21 `put_force_save_used` recorded (live), audit count = 11 movies confirmed. Radarr rootfolder diff corroborates (unmappedFolders cleared). **Caveat:** "file present on disk" true for only 1 of the FS-move items; the rest are `both_missing` → MISSING on disk. Per-movie distribution (5+3+2+1) was live-curl-only — not in committed snapshots. |
| SC3 | Sonarr series on Category root folder + series tag, episodes re-detected | ⚠ PARTIAL PASS | Same shape as SC2: 10 series audit count confirmed, API PUTs succeeded (live), RefreshSeries batched. **Same both_missing caveat** — "episode files re-detected" only holds where files survived. Per-series distribution (6+4) was live-curl-only. |
| SC4 | qBit torrents on Category save_path + category, state preserved, no re-hash failure | ✓ VERIFIED (snapshot-corroborated) | **Strongest independent evidence:** post-snapshot `torrents_info.json` shows exactly 3 torrents on `/data/complete` (the PRUNE_PHASE_22 orphans) + 37 on `/data/torrents/<cat>/` — matching audit (40 total, 3 orphans, 37 relocate) exactly. 638-line diff confirms the 37 mutations. "State preserved / no re-hash" is a live observation (routed to human verify). |
| SC5 | Jellyfin /Library/Refresh completes; 10 Category libs ItemCount > 0; none emptied | ⚠ PARTIAL PASS | Refresh dispatched 204 (Jellyfin scheduled_tasks + system_storage timestamps changed in snapshot — confirms refresh ran). `library_virtualfolders.json` post-snapshot lists the 10 Category libs. **Caveat:** "ItemCount > 0" is async/best-effort and a live assertion; with 10 items now missing-on-disk, a lib could thin out — routed to human verify. |

**Score:** 5/5 truths mechanically achieved; SC2/SC3/SC5 carry a partial-pass caveat (the both_missing drift + async ItemCount).

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/scripts/migrate-categories.py` | One-shot migration script, hors arrconf, 350+ lines | ✓ VERIFIED | 749 lines; all 14 required functions present; sys.path injection + arrconf client reuse + ruyaml + argparse (no Typer/Click); Triade green. |
| `.gitignore` | `.migration-state.json` + tempfile pattern | ✓ VERIFIED | Lines 43-44; `.migration-state.json` NOT in `git ls-files` (correctly uncommitted). |
| `21-RUNBOOK.md` | French operator runbook, Étapes 1-5 + Troubleshooting + Rollback | ✓ VERIFIED | 159 lines, all sections present, mirrors CLAUDE.md FS-migration shape; references `--media-root`, snapshot.sh, port-forwards. |
| `snapshots/before-categories-cleanup-2026-05-27/` | ADR-6 pre-baseline, committed | ✓ VERIFIED | 54 files (4 apps), committed `0dad89c`. |
| `snapshots/after-categories-cleanup-2026-05-27/` | ADR-6 post-baseline, committed | ✓ VERIFIED | 54 files, committed `bfdd8a2`. |

## Key Decision / Invariant Verification

| Decision | Expected | Status | Evidence |
|----------|----------|--------|----------|
| D-21-TOOL-02 (no chart-pin co-bump) | `values.yaml` tag unchanged | ✓ | `git diff 1cf1da0 HEAD -- charts/arr-stack/values.yaml` → 0 tag changes (empty diff). |
| D-21-ORDER-01 (no moveFiles=true) | absent | ✓ | `grep -c moveFiles` → 0. |
| D-21-QBIT-01 (no pause/resume) | absent | ✓ | `grep -c 'torrents/pause\|torrents/resume\|setForcePause'` → 0. |
| D-21-TOOL-01 (hors arrconf) | under tools/scripts/ | ✓ | File at `tools/scripts/`, not under `tools/arrconf/`. |
| No `--resume-from` flag | absent | ✓ | `grep -c resume-from` → 0; resume is state.json-only. |
| Deviation fix 80d2b20 (`_to_host_path`) | present | ✓ | Defined lines 183-198; `--media-root` flag wired. |
| Deviation fix f6c34bb (`_maybe_rename`) | disk-state-keyed | ✓ | Defined lines 201-292; 4-way src/dst existence switch. |
| Deviation fix 62a3d30 (`both_missing` soft-skip) | logs + proceeds to PUT, no raise | ✓ | Lines 276-287: `both_missing` branch logs `fs_move_skip_file_missing` warning and falls through (only `both_exist` raises). |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Triade ruff format | `uv run ruff format --check ../scripts/migrate-categories.py` | "1 file already formatted" | ✓ PASS |
| Triade ruff check | `uv run ruff check ../scripts/migrate-categories.py` | "All checks passed!" | ✓ PASS |
| Triade mypy | `uv run mypy ../scripts/migrate-categories.py` | "Success: no issues found" | ✓ PASS |
| Audit counts match | parse 20-AUDIT.md YAML | radarr=11, sonarr=10, qbit=40 (3 orphan + 37 relocate) | ✓ PASS |
| qBit post-snapshot distribution | count save_path in torrents_info.json | 3 on /data/complete, 37 on /data/torrents | ✓ PASS |

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CAT-CLEANUP-02 | 21-01 | Filesystem + metadata migration to Category targets | ✓ SATISFIED (with caveat) | Migration mechanism executed live, no halt; DB Category-anchored. File-on-disk sub-clause partial due to both_missing drift. |

## Anti-Patterns Found

None. No `moveFiles=true`, no pause/resume, no `--resume-from`, no chart bump in the script, no Typer/Click, no audit-module import. The script has no stubs (every function fully implemented).

## The both_missing Caveat — called out explicitly

The Phase 20 audit (2026-05-25) assumed disk matched the API-reported paths. At apply (2026-05-27) the disk had drifted: **10 of 11 FS-move items were `both_missing`** — neither source nor destination file existed on the host NFS mount. The operator chose (commit `62a3d30`) to soft-skip the missing file and still issue the API PUT, syncing the Radarr/Sonarr DB record to its Category root folder.

**Consequence:** those 10 records now point at a Category rootFolderPath with **no file on disk** → they will display as MISSING in Radarr/Sonarr. The Radarr rootfolder diff (BEFORE had unmappedFolders for Now You See Me 2, Spy Kids 2, Snow White, Spirit; AFTER → empty) corroborates that disk content had been partially cleaned independently of the script.

**Recommended follow-up (operator / Phase 22):** for each of the 10 missing-on-disk records, decide per-item — re-download via monitored search, or remove from the *arr. This is already captured in STATE.md close-out notes. It does NOT undo the migration (the DB is correctly Category-anchored and qBit is fully relocated) but it leaves catalog hygiene work outstanding.

## Gaps Summary

No blocking gaps. The phase goal — "move every item to its Category target, leaving the cluster functional" — is mechanically achieved: zero halt, all API/qBit mutations applied, snapshots bounded, decisions honored, Triade green. The single material concern is the file-on-disk sub-clause of SC2/SC3, partially unmet due to pre-existing disk drift the script could not control (it adapted correctly via the operator-approved soft-skip rather than hard-failing). SC4 and SC1 are independently verifiable from committed artifacts; SC2/SC3/SC5 live assertions are routed to human verification since the cluster is no longer reachable.

---

_Verified: 2026-05-27_
_Verifier: Claude (gsd-verifier)_
