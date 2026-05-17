---
phase: 07-reconciler-jellyfin
plan: "01"
subsystem: infra
tags: [jellyfin, snapshot, evidence, adr-6, put-probe, wave-0, bootstrap]

# Dependency graph
requires:
  - phase: 06-reconciler-seerr
    provides: Phase 6 snapshotting patterns, anti-leak discipline (5-file redaction), D-06-CRED-MGMT lesson (missing SEERR_API_KEY → code 2)
provides:
  - Pre-write Jellyfin snapshot baseline (ADR-6 / ROADMAP SC#2) — 9 endpoints, anti-leak clean, devices.json scoped OUT
  - Q9 PUT-probe evidence file (D-07-VALIDATE-01) — Plans 07-02..07-05 unblocked
  - JELLYFIN_API_KEY sealed into arrconf-env (REQ-bootstrap-exception) — Plan 07-06 Wave 4 cluster apply unblocked
affects: [07-02, 07-03, 07-04, 07-05, 07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Anti-leak grep before committing snapshots and evidence (inherited from Phase 5/6 discipline)"
    - "Evidence file captures live probe results with $JK/$KEY placeholders (no literal tokens)"
    - "Operator-driven Wave 0: snapshot.sh requires JELLYFIN_API_KEY + kubectl port-forward — executor cannot self-serve"
    - "Port-forward race: snapshot.sh launched in same compound command as port-forward background job loses early HTTP endpoints (HTTP 000000) — backfill required"
    - "kubeseal --raw → SealedSecret reconcile (~30s) → kubectl evidence capture — mirrors Phase 6 D-06-CRED-MGMT pattern"

key-files:
  created:
    - snapshots/before-phase-7-2026-05-17/jellyfin/ (9 files: library_virtualfolders, users, system_configuration, system_info, system_info_public, system_storage, plugins, scheduled_tasks, metadata_options_default)
    - .planning/phases/07-reconciler-jellyfin/evidence/q9-put-probe.txt
    - .planning/phases/07-reconciler-jellyfin/evidence/jellyfin-api-key-bootstrap-check.txt
  modified: []

key-decisions:
  - "D-07-VALIDATE-01 closed: Q9 PUT-probe VERIFIED live, archived in evidence/q9-put-probe.txt"
  - "Task 1.1 split across two commits: initial snapshot (5 files, port-forward race) + backfill (4 files + drop devices.json) — operationally cleaner than retrying from scratch"
  - "devices.json deleted: Phase 7 CONTEXT.md explicitly scopes /Devices OUT of reconciler (T-07-LEAK-DEVICES carry-forward — keep snapshot domain narrow)"
  - "JELLYFIN_API_KEY (44-char base64) sealed into arrconf-env: 7 keys now present (JELLYFIN_API_KEY, PROWLARR_API_KEY, QBT_PASS, QBT_USER, RADARR_API_KEY, SEERR_API_KEY, SONARR_API_KEY)"

patterns-established:
  - "Evidence file: header block + 6 content sections + anti-leak grep pattern (q9-put-probe.txt)"
  - "Bootstrap evidence: keys-array dump + value-length proof — never base64 value dump (jellyfin-api-key-bootstrap-check.txt)"
  - "Operator commit lands directly on main when checkpoint requires shell-level credentials; orchestrator merges worktree branches on top"

requirements-completed:
  - "REQ-bootstrap-exception (Phase 7 scope: JELLYFIN_API_KEY)"

# Metrics
duration: 32min (operator)
completed: "2026-05-17"
---

# Phase 7 Plan 01: Wave 0 Pre-flight Gate — COMPLETE

**3 artefacts locked: pre-write snapshot baseline + Q9 PUT-probe evidence + JELLYFIN_API_KEY bootstrap check — all anti-leak clean, all committed to main.**

## Status: COMPLETE — All 3 Tasks ✅

| Task | Type | Status | Commit(s) |
|------|------|--------|-----------|
| 1.1 — Pre-write Jellyfin snapshot | operator + auto-backfill | ✅ | `8b91abf` (initial 5 files) + `dc97214` (backfill 4 files + drop devices.json) |
| 1.2 — Q9 PUT-probe evidence | executor (auto) | ✅ | `408fa6b` (worktree-agent-af2dd8b787b044cee, merged via `479958d`) |
| 1.3 — JELLYFIN_API_KEY bootstrap | operator (human-verify) | ✅ | `cd95f08` (arr-stack evidence) + my-kluster sealed-secret commit + push |

## Accomplishments

- **Snapshot baseline** captured at `snapshots/before-phase-7-2026-05-17/jellyfin/` — 9 endpoints (ADR-6 / ROADMAP SC#2). Critical 4-file set present: `library_virtualfolders.json`, `users.json`, `system_configuration.json`, `plugins.json`. `devices.json` explicitly deleted (Phase 7 scopes /Devices OUT). Anti-leak grep on `AccessToken|Bearer|Authorization:|api_key=[a-f0-9]{8,}|MediaBrowser Token=[a-f0-9]{8,}` returned 0 hits.
- **Q9 evidence** at `.planning/phases/07-reconciler-jellyfin/evidence/q9-put-probe.txt` — 205 lines, 6 sections (auth probe + 5 pitfalls), live-probe results from `jellyfin-94f5cc54d-p4hk8` (2026-05-17 ~10:52-11:00 UTC). All literal tokens replaced with `$JK` / `$KEY` placeholders.
- **Bootstrap evidence** at `.planning/phases/07-reconciler-jellyfin/evidence/jellyfin-api-key-bootstrap-check.txt` — `kubectl get secret arrconf-env -o jsonpath='{.data}' | jq 'keys'` shows 7 keys including `JELLYFIN_API_KEY`. Length = 44 base64 chars (proves a 32-byte hex key reconciled cleanly). Both anti-leak greps returned 0 lines.
- **Sealed-secret round-trip** verified live: `kubeseal --raw` → push to my-kluster → sealed-secrets controller reconciles inside ~30s → `kubectl` sees the new key as an opaque value. Mirrors the D-06-CRED-MGMT pattern from Phase 6.

## Files Created/Modified

| File | Size | Purpose |
|------|------|---------|
| `snapshots/before-phase-7-2026-05-17/jellyfin/library_virtualfolders.json` | 6.1 KB | Wave 2 reconciler Pitfall 2/3 ground truth |
| `snapshots/before-phase-7-2026-05-17/jellyfin/users.json` | 5.1 KB | Wave 2 reconciler Pitfall 4/6 ground truth |
| `snapshots/before-phase-7-2026-05-17/jellyfin/system_configuration.json` | ~5 KB | Wave 2 reconciler Pitfall 1 ground truth |
| `snapshots/before-phase-7-2026-05-17/jellyfin/plugins.json` | 1.9 KB | Wave 2 reconciler Pitfall 5 ground truth |
| `snapshots/before-phase-7-2026-05-17/jellyfin/{system_info,system_info_public,system_storage,scheduled_tasks,metadata_options_default}.json` | — | Auxiliary diff context |
| `.planning/phases/07-reconciler-jellyfin/evidence/q9-put-probe.txt` | 205 lines | D-07-VALIDATE-01 closure artefact |
| `.planning/phases/07-reconciler-jellyfin/evidence/jellyfin-api-key-bootstrap-check.txt` | 342 B | REQ-bootstrap-exception closure |

## Decisions Made

- **D-07-VALIDATE-01 (closed):** Q9 auth strategy — `Authorization: MediaBrowser Token=` header preferred (200 reads + 204 writes), `?api_key=` confirmed fallback. Resolution archived in evidence file; reconciler code (Plan 07-04) will adopt the header form.
- **D-07-DEVICES-OUT (locked):** `/Devices` endpoint stays OUT of the reconciler scope. `devices.json` is deleted from the snapshot rather than redacted — Phase 7 has no diff need for it.
- **D-07-SNAPSHOT-RETRY (pattern):** When `snapshot.sh` is launched in the same compound command as `kubectl port-forward &`, the early endpoints race the listener and return HTTP 000000. Backfill by re-running snapshot.sh once port-forward is warm; commit both the initial capture and the backfill atomically (or as two adjacent commits).
- **D-07-BOOTSTRAP-EVIDENCE (pattern):** Evidence file dumps the `keys` array + a `wc -c` length only — never the base64 value. Anti-leak grep uses two clauses: long-base64-anywhere and inline-`data: <b64>`.

## Deviations from Plan

### Deviation 1: Port-forward race forced a 2-commit Task 1.1

- **Found during:** Task 1.1 first run (operator-driven, on main)
- **Issue:** `kubectl port-forward svc/jellyfin 8096:8096 &` was backgrounded in the same shell line as `tools/snapshot/snapshot.sh`. The first 4 endpoints (`system_info`, `system_info_public`, `system_configuration`, `system_storage`) returned HTTP 000000 before the listener bound; snapshot.sh marked the app as failed but still committed the 5 endpoints that hit after the race. `system_configuration.json` was missing — that's a hard dependency for Plan 07-04 Pitfall 1.
- **Decision:** Rather than reset/recommit, accept the partial as commit #1 (`8b91abf`) and add a follow-up backfill commit (`dc97214`) that re-runs snapshot.sh against the warm port-forward, deletes the now-emitted `devices.json` (scoped OUT), and commits with anti-leak grep clean. Pattern recorded for future Phases that snapshot through a port-forward.

### Deviation 2: `rm` / `cp` are interactively aliased (locale=fr)

- **Found during:** Backfill cleanup (Task 1.1) and worktree-merge backup logic
- **Issue:** `rm <file>` and `cp <src> <dst>` prompted "voulez-vous écraser ?" with no terminal input attached, silently no-op'ing. Same root cause as Phase 02.2 P06 RECOVERY pattern for `mv`.
- **Decision:** Use `\rm -f` / `\cp -f` (backslash-escape) in all script commands going forward. Pattern propagated to STATE.md decisions block.

## Threat Model Status

| Threat ID | Status | Evidence |
|-----------|--------|----------|
| T-07-LEAK-DEVICES | MITIGATED | `devices.json` deleted; `find snapshots/before-phase-7-2026-05-17/jellyfin/ -name 'devices.json'` = 0 hits |
| T-07-LEAK-EVIDENCE | MITIGATED | q9-put-probe.txt anti-leak grep = 0 hits |
| T-07-LEAK-SECRET-DUMP | MITIGATED | jellyfin-api-key-bootstrap-check.txt: both anti-leak greps = 0 hits, only `keys` array + length proof present |
| T-07-MISSING-BOOTSTRAP | MITIGATED | `JELLYFIN_API_KEY` present in arrconf-env keys (44 base64 chars) — verified live, evidence committed |

## Success Criteria Status

| SC | Description | Status |
|----|-------------|--------|
| SC#1 (Wave 4 prereq) | JELLYFIN_API_KEY in arrconf-env | ✅ SATISFIED (Task 1.3) |
| SC#2 | Pre-write snapshot before any cluster write | ✅ SATISFIED (Task 1.1, 2 commits) |
| SC#3 | Q9 auth strategy resolved | ✅ DOCUMENTED (Task 1.2 — code lands in Plan 07-04) |
| REQ-bootstrap-exception | Phase 7 scope closure | ✅ CLOSED |

## Wave Readiness Signal

- **Plans 07-02..07-05** (schema/code/tests/chart): UNBLOCKED since Task 1.2 landed (`408fa6b`); 07-02 + 07-03 already complete via parallel dispatch.
- **Plan 07-06** (Wave 4 cluster apply): UNBLOCKED — both Task 1.1 snapshot baseline and Task 1.3 bootstrap evidence are committed.

## Issues Encountered

- Task 1.1 required two operator-side iterations (port-forward race) — recorded as deviation pattern for future phases that snapshot through a port-forward.
- Original JELLYFIN_API_KEY value was disclosed plaintext in the orchestrator transcript during the operator-handoff sequence; operator may want to rotate the key via Jellyfin Dashboard once Wave 4 finishes.

## Self-Check

- [x] Snapshot baseline exists at `snapshots/before-phase-7-2026-05-17/jellyfin/` (9 files)
- [x] `devices.json` absent (Phase 7 scope)
- [x] Snapshot anti-leak grep = 0 hits
- [x] Q9 evidence file exists with 6 sections + Pitfalls 1-5 + 204 HTTP code
- [x] Q9 evidence anti-leak grep = 0 hits
- [x] Bootstrap evidence file exists; `JELLYFIN_API_KEY` in keys; length 44
- [x] Bootstrap anti-leak grep = 0 hits (both clauses)
- [x] All 3 tasks committed atomically on main / worktree
- [x] SUMMARY.md upgraded from partial → final

---
*Phase: 07-reconciler-jellyfin*
*Completed: 2026-05-17*
