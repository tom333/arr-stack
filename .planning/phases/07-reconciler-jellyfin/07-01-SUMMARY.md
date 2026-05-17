---
phase: 07-reconciler-jellyfin
plan: "01"
subsystem: infra
tags: [jellyfin, snapshot, evidence, adr-6, put-probe, wave-0]

# Dependency graph
requires:
  - phase: 06-reconciler-seerr
    provides: Phase 6 snapshotting patterns, anti-leak discipline (5-file redaction), D-06-CRED-MGMT lesson (missing SEERR_API_KEY → code 2)
provides:
  - Q9 PUT-probe evidence file archived (D-07-VALIDATE-01 closure artifact) — Plans 07-02..07-05 unblocked
  - Pre-write Jellyfin snapshot PENDING (Task 1.1 blocked — JELLYFIN_API_KEY not in executor env)
  - JELLYFIN_API_KEY bootstrap check PENDING (Task 1.3 operator gate)
affects: [07-02, 07-03, 07-04, 07-05, 07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Anti-leak grep before committing evidence files (inherited from Phase 5/6 discipline)"
    - "Evidence file captures live probe results with $JK/$KEY placeholders (no literal tokens)"

key-files:
  created:
    - .planning/phases/07-reconciler-jellyfin/evidence/q9-put-probe.txt
  modified: []

key-decisions:
  - "D-07-VALIDATE-01: Q9 PUT-probe VERIFIED live (MediaBrowser Token preferred, 6 pitfalls documented)"
  - "Task 1.1 BLOCKED: JELLYFIN_API_KEY not set in executor environment — operator must provide key + port-forward"
  - "Task 1.2 COMPLETED: Q9 evidence file created without cluster access (pure file creation)"
  - "Task 1.3 PENDING: JELLYFIN_API_KEY must be sealed into arrconf-env before Plan 07-06 Wave 4 can proceed"

patterns-established:
  - "Evidence file: header block + 6 content sections + anti-leak grep pattern"
  - "Partial SUMMARY: document blocked tasks with explicit operator action required"

requirements-completed: []

# Metrics
duration: partial
completed: "2026-05-17"
---

# Phase 7 Plan 01: Wave 0 Pre-flight Gate — PARTIAL SUMMARY

**Q9 PUT-probe evidence archived (6 pitfalls documented from live probe); snapshot + API-key bootstrap gate pending operator action**

## Status: PARTIAL — Checkpoint Reached

**Task 1.1:** BLOCKED — JELLYFIN_API_KEY not set in executor environment (human-action gate)
**Task 1.2:** COMPLETE — Q9 PUT-probe evidence file created and committed
**Task 1.3:** PENDING — Operator must seal JELLYFIN_API_KEY into my-kluster arrconf-env Secret

## Performance

- **Started:** 2026-05-17T01:42:00Z
- **Completed:** 2026-05-17T01:48:26Z (partial)
- **Tasks completed:** 1 of 3 (Task 1.2 only)
- **Files modified:** 1

## Accomplishments

- Task 1.2: Created `.planning/phases/07-reconciler-jellyfin/evidence/q9-put-probe.txt` — auditable trail for D-07-VALIDATE-01 with 6 sections covering all critical Jellyfin API write-semantics (auth strategies, replace vs merge, path idempotence, user policy method, plugin enable path format, required OpenAPI fields)
- Anti-leak verification passed: no literal API tokens in evidence file (only `$JK`/`$KEY` placeholders)
- Plans 07-02 through 07-05 are unblocked by Task 1.2 alone (the Q9 evidence + auth strategy is resolved)

## Task Commits

1. **Task 1.1: Capture pre-write Jellyfin snapshot** — BLOCKED (JELLYFIN_API_KEY not set)
2. **Task 1.2: Q9 PUT-probe evidence file** — `408fa6b` (evidence(07): Q9 PUT-probe live results (D-07-VALIDATE-01))
3. **Task 1.3: Operator JELLYFIN_API_KEY bootstrap checkpoint** — PENDING (operator gate)

## Files Created/Modified

- `.planning/phases/07-reconciler-jellyfin/evidence/q9-put-probe.txt` — Q9 live-probe evidence: auth strategies (3), Pitfall 1 (POST /System/Configuration full REPLACE), Pitfall 2 (POST /Library/VirtualFolders/Paths NOT idempotent), Pitfall 3 (DELETE removes ALL matching), Pitfall 4 (POST not PUT for UserPolicy), Pitfall 5 (plugin enable needs version in path), Pitfall 6 (UserPolicy required OpenAPI fields)

## Decisions Made

- Q9 auth strategy: `Authorization: MediaBrowser Token=` header preferred (HTTP 200 reads + 204 writes), `?api_key=` query param as verified fallback — both confirmed live (VERIFIED)
- Evidence file pattern: header block identifying probe target + date + placeholder disclaimer, then 6 numbered sections copying research verbatim with placeholders
- Task ordering: completed Task 1.2 (independent of cluster/env) before returning checkpoint for Task 1.1 (requires JELLYFIN_API_KEY + port-forward)

## Deviations from Plan

### Blocked Tasks

**1. [Human-Action Gate] Task 1.1 — JELLYFIN_API_KEY not set in executor environment**
- **Found during:** Task 1.1 pre-execution check
- **Issue:** snapshot.sh:389 reads `${JELLYFIN_API_KEY:?JELLYFIN_API_KEY env var is required}` — fails fast without the key. No port-forward to Jellyfin pod is active in the executor shell either.
- **Action required:** Operator must (1) export `JELLYFIN_API_KEY=<value>` in their shell, (2) start `kubectl -n selfhost port-forward svc/jellyfin 8096:8096 &`, (3) run `tools/snapshot/snapshot.sh --apps jellyfin --output snapshots/before-phase-7-2026-05-17/`, (4) run anti-leak grep, (5) commit.
- **Checkpoint type:** human-action

## Q9 Evidence Coverage

The evidence file covers all 6 mandatory sections per plan acceptance criteria:

| Section | Content | Plan required |
|---------|---------|---------------|
| Auth probe | MediaBrowser Token (200), X-Emby-Token (200), ?api_key= (200), no-auth (401) | MediaBrowser Token string present |
| Pitfall 1 | POST /System/Configuration full REPLACE, round-trip evidence, RESTORATION evidence | Contains "Pitfall 1" |
| Pitfall 2 | POST /Library/VirtualFolders/Paths NOT idempotent, HTTP 204 with duplication | Contains "Pitfall 2" + "204" |
| Pitfall 3 | DELETE removes ALL matching entries | Contains "Pitfall 3" |
| Pitfall 4 | POST /Users/{id}/Policy (not PUT — HTTP 405) | Contains "Pitfall 4" |
| Pitfall 5 | POST /Plugins/{id}/{version}/Enable — version required in path | Contains "Pitfall 5" |

Anti-leak grep result: 0 matches for `api_key=[a-f0-9]{8,}|MediaBrowser Token="[a-f0-9]{8,}"|Bearer [a-zA-Z0-9_-]{20,}` — PASSED.

## Issues Encountered

- JELLYFIN_API_KEY not available in the executor shell (worktree environment). Task 1.2 is entirely independent of cluster access and was completed first.
- The snapshot (Task 1.1) requires both the API key AND an active kubectl port-forward — neither is available in the worktree/CI environment. This is an operator-side prerequisite.

## Wave 1+ Readiness Signal

- **Plans 07-02..07-05 (schema/code/tests/chart):** UNBLOCKED by Task 1.2 (Q9 evidence committed). No dependency on the snapshot or API key bootstrap.
- **Plan 07-06 (Wave 4 cluster apply):** BLOCKED until both Task 1.1 (snapshot) and Task 1.3 (JELLYFIN_API_KEY in arrconf-env) complete.

## Threat Model Status

| Threat ID | Status |
|-----------|--------|
| T-07-LEAK-DEVICES | Deferred — Task 1.1 not yet run; anti-leak grep will be applied when snapshot is captured |
| T-07-LEAK-EVIDENCE | MITIGATED — q9-put-probe.txt anti-leak grep returned 0 hits |
| T-07-LEAK-SECRET-DUMP | Deferred — Task 1.3 not yet run |
| T-07-MISSING-BOOTSTRAP | Deferred — Operator action pending (Task 1.3) |

## Operator Actions Required (NEXT)

### Task 1.1 — Snapshot (operator shell)

```bash
export JELLYFIN_API_KEY=<your-jellyfin-api-key>
kubectl -n selfhost port-forward svc/jellyfin 8096:8096 &
cd /home/moi/projets/perso/arr-stack
tools/snapshot/snapshot.sh --apps jellyfin --output snapshots/before-phase-7-2026-05-17/
# Anti-leak grep:
grep -rE 'AccessToken|Bearer |Authorization:|api_key=[a-f0-9]{8,}|MediaBrowser Token="[a-f0-9]{8,}"' \
  snapshots/before-phase-7-2026-05-17/jellyfin/
# If any hits: redact (users.json Devices/Items[]/Id + LastAuthenticatedIpAddress)
git add snapshots/before-phase-7-2026-05-17/jellyfin/
git commit -m "snapshot(07): pre-write Jellyfin baseline (ADR-6 SC#2)"
```

### Task 1.3 — JELLYFIN_API_KEY bootstrap (my-kluster operator)

```bash
# In my-kluster repo — seal JELLYFIN_API_KEY into arrconf-env SealedSecret
# Then verify:
cd /home/moi/projets/perso/arr-stack
mkdir -p .planning/phases/07-reconciler-jellyfin/evidence/
{
  echo "# JELLYFIN_API_KEY bootstrap check (REQ-bootstrap-exception)"
  echo "# Captured: $(date -Iseconds)"
  echo "## kubectl get secret arrconf-env keys:"
  kubectl -n selfhost get secret arrconf-env -o jsonpath='{.data}' | jq 'keys'
  echo "## JELLYFIN_API_KEY length (base64 chars):"
  kubectl -n selfhost get secret arrconf-env -o jsonpath='{.data.JELLYFIN_API_KEY}' | wc -c
} > .planning/phases/07-reconciler-jellyfin/evidence/jellyfin-api-key-bootstrap-check.txt
# Anti-leak check (both must return 0 lines):
grep -E '[A-Za-z0-9+/]{40,}={0,2}' .planning/phases/07-reconciler-jellyfin/evidence/jellyfin-api-key-bootstrap-check.txt
grep -E 'data:\s*[A-Za-z0-9+/]{40,}' .planning/phases/07-reconciler-jellyfin/evidence/jellyfin-api-key-bootstrap-check.txt
# Commit:
git add .planning/phases/07-reconciler-jellyfin/evidence/jellyfin-api-key-bootstrap-check.txt
git commit -m "evidence(07): JELLYFIN_API_KEY bootstrap verified in arrconf-env (REQ-bootstrap-exception)"
```

## Self-Check

- [x] Task 1.2 evidence file exists: `.planning/phases/07-reconciler-jellyfin/evidence/q9-put-probe.txt`
- [x] Task 1.2 committed: `408fa6b`
- [x] Anti-leak grep passed (0 hits)
- [ ] Task 1.1 snapshot: PENDING (operator must provide JELLYFIN_API_KEY + port-forward)
- [ ] Task 1.3 bootstrap check: PENDING (operator must seal key into my-kluster)
- [x] SUMMARY.md committed

## Self-Check: PARTIAL — Tasks 1.1 and 1.3 pending operator action

---
*Phase: 07-reconciler-jellyfin*
*Completed (partial): 2026-05-17*
