# Phase 02.2 — Deferred Items

Items discovered during execution that are out of scope for this phase but worth tracking.

---

## D-02.2-DEFERRED-LEAK-CARRY-FORWARD

**Discovered:** Plan 02.2-06 self-check (Task 6.4 phase, post-summary anti-leak audit)
**Severity:** Low — historical snapshots, pre-dating current redaction discipline
**Scope:** Pre-existing snapshot dirs in `snapshots/`

### Finding

Three historical snapshot directories contain unredacted occurrences of the known qBittorrent
tracker passkey hex literal `feed603a98de65f6e580d4bfa71ada68`:

- `snapshots/baseline-2026-05-07/qbittorrent/torrents_info.json`
- `snapshots/before-phase-2-2026-05-08/qbittorrent/torrents_info.json`
- `snapshots/before-phase-2.2-2026-05-09/qbittorrent/torrents_info.json` (Phase 2.2 Plan 01 baseline)

The all-three-snapshots leak originates from `tools/snapshot/snapshot.sh` lacking
URL-encoded passkey redaction (D-02.1-02 carry-forward — already documented in
Phase 2.1 deferred-items.md, slated for a dedicated snapshot.sh hardening pass).

### Why deferred

- **Out of scope per executor SCOPE BOUNDARY** — Phase 02.2 Plan 06 only modifies
  `evidence/` and `snapshots/post-phase2.2-*` and `snapshots/drift-test-phase2.2-*`.
  The pre-existing leaks were committed by earlier phases (Phase 0 / Phase 2 / Phase 2.2 Plan 01).
- **Already-tracked deferred work** — D-02.1-02 (snapshot.sh redaction enhancement)
  is the durable home for this fix. The snapshot.sh hardening pass will rewrite
  history-with-care, OR introduce a one-off `redact-historical-snapshots.sh` utility.
- **Threat model accept** — these snapshots are committed to a git history that's
  visible to the maintainer; the passkey is already considered compromised
  (was used in development cluster); rotation is the proper response, not git rewrites.

### Verification of NEW snapshots (this plan's deliverables)

`snapshots/post-phase2.2-2026-05-09/` and `snapshots/drift-test-phase2.2-2026-05-09/`
were both audited (anti-leak grep across raw and URL-encoded forms) — clean.

### Resolution path

1. Phase that hardens `tools/snapshot/snapshot.sh` (likely Phase 5 or a dedicated
   hardening phase) closes D-02.1-02 — script natively redacts both raw and URL-encoded
   passkey forms before write-out.
2. Decision needed on whether to retro-redact the 3 historical snapshots:
   - **Option A** — leave as-is (acknowledge in deferred-items, rotate the passkey upstream)
   - **Option B** — `git filter-repo` rewrite to redact the literal in history
     (impact: rewrites SHAs of every commit touching the file; requires force-push;
     coordinate with all collaborators)
   - **Option C** — single rewrite commit that overwrites the files in-place; preserves history
     of the redaction event but leaves the literal recoverable via `git log -p`
     (rejected — same accessibility as Option A with extra commit noise)

Recommendation: **Option A + passkey rotation** is the lowest-risk path; the
hardening pass is forward-looking, not retroactive.

---

*Created: 2026-05-09 (Plan 02.2-06 self-check audit)*
