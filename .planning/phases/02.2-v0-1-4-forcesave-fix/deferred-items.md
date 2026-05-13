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

## D-02.2-AUTH-REGRESSION — qBit credentials wiped by v0.1.4 forceSave UPDATE PUT

**Status:** OPEN (blocking phase 02.2 closure)
**Discovered:** 2026-05-09 by operator visual UAT (Task 6.4)
**Severity:** HIGH — production credential overwrite; Phase 3 prerequisite NOT met
**Scope:** `tools/arrconf/arrconf/client_base.py` `_ArrV3Client.put()` + `tools/arrconf/arrconf/differ.py` `merge_fields_for_put`

### Symptom

Sonarr's "Test" button on the qBittorrent download client returns 401/403 (Auth failed) after the v0.1.4 reconcile completed cleanly. All Plan 06 automated dispositives passed (priority restored 5→1, `put_force_save_used` emitted, no HTTP 400, `manual_nudge_used: NO`), but the human-verify gate detected a credential-side regression that the priority-only diff did not surface.

### Hypothesis (forensic-confirmed)

The Phase 2.1 helper `merge_fields_for_put` preserves the API mask `"********"` for `privacy=password` fields when YAML carries an empty/placeholder value, by substituting cluster's stored value at the same `name` (D-31/D-32 contract). Cluster's stored value, as returned by Sonarr's GET, IS the API mask — so the helper's "preserve cluster value" semantic is circular for masked fields: it preserves the MASK, not the credential.

When v0.1.4's `_ArrV3Client.put()` injects `?forceSave=true`, Sonarr's pre-save validation is bypassed. The PUT body containing `password.value="********"` is accepted as-is and the mask token is stored as the literal password value. Sonarr's GET-side serialization continues returning `"********"` for `privacy=password` fields — making the regression invisible to snapshot diff (the GET cannot distinguish a stored-real-password from a stored-mask-literal).

The regression is detectable ONLY by behavioral test (Sonarr's "Test" button POSTs the literal `"********"` to qBit; qBit correctly rejects with 401/403) — which is precisely what the operator visual gate caught.

This is the architectural risk explicitly accepted by ADR-8. It is now realized in production.

### Forensic evidence

- **Forensic snapshot:** `snapshots/forensic-phase2.2-auth-regression-2026-05-09T0648/` (Sonarr 17 JSON + qBittorrent 8 files, redacted, anti-leak audit clean)
- **Credential diff:** `.planning/phases/02.2-v0-1-4-forcesave-fix/evidence/forensic-credentials-diff-2026-05-09T0651.txt` — diff EMPTY at GET-serialization layer (the dispositive: `password=********` BEFORE and AFTER, indistinguishable from the GET API)
- **Pod log aggregation:** `.planning/phases/02.2-v0-1-4-forcesave-fix/evidence/forensic-cronjob-logs-2026-05-09T0652.log` — both v0.1.4 PUT events (05:55Z post-deploy smoke + 06:02Z drift-demo) emitted `merge_field_preserved` for username AND password followed by `put_force_save_used` and `apply_complete`
- **Smoking-gun event sequence (from drift-demo-2026-05-09.log):**
  ```jsonl
  {"action": "update", "name": "qBittorrent", "diff_fields": ["fields", "priority"], "event": "plan_action", ...}
  {"name": "username", "event": "merge_field_preserved", ...}
  {"name": "password", "event": "merge_field_preserved", ...}
  {"path": "/downloadclient", "id": 1, "event": "put_force_save_used", ...}
  {"app": "sonarr", "actions": ["update:qBittorrent"], "event": "apply_complete", ...}
  ```

### Mitigation in place

CronJob `arrconf` in selfhost SUSPENDED at **2026-05-09T06:48:11Z** via:

```bash
kubectl patch cronjob arrconf -n selfhost -p '{"spec":{"suspend":true}}'
```

Cluster state frozen until hotfix ships. Sonarr's stored qBit password is currently the literal `"********"` and must be operator-corrected via UI before the CronJob is unsuspended.

### Required action — Phase 02.2 gap-closure plan

1. **Reproduce in test** — unit test asserting `merge_fields_for_put` behavior for `privacy=password|userName` fields cannot end with the API mask token surviving into the PUT body (or, if it does, the PUT path MUST refuse `?forceSave=true` so Sonarr's pre-save validation catches the literal mask and rejects with HTTP 400 — surfacing the bug instead of hiding it).
2. **Extend merge-field protection** — three viable strategies (planner picks):
   - **Option A (omit):** Detect `privacy=password|userName` field metadata in cluster GET response, omit those entries from the PUT body entirely. Sonarr will preserve the stored value when a field is missing from the body. Forfeits the auditable `merge_field_preserved` event for credentials (acceptable — the absence is the protection).
   - **Option B (mask-token detect):** Detect known mask tokens (`"********"`, `null`) in cluster GET, treat them as "no value to preserve" and omit from PUT body. Same end result as A, generic across `privacy` field types.
   - **Option C (scope forceSave):** Keep the mask in the PUT body but DROP `?forceSave=true` for PUTs that contain known mask tokens. Sonarr's pre-save validation will then catch the literal `"********"` and reject the PUT with HTTP 400 — re-surfacing the original bug as a loud failure, deferring credential management to operator. Reverts to Phase 2.1's "manual nudge" model for this specific subset.
3. **Ship v0.1.5** — atomic single-PR release pattern (D-37). YAML stays unchanged.
4. **Operator-driven cluster recovery** — in Sonarr UI, manually re-enter the qBit password BEFORE unsuspending the CronJob. The current stored value is `"********"` (literal), not the real password.
5. **Re-run W-04 dispositive WITH credential check** — new dispositive must include a behavioral assertion (Sonarr "Test" button success programmatically; e.g. `POST /api/v3/downloadclient/test` and assert HTTP 200), not just snapshot diff. Snapshot-only checks cannot detect this class of regression by construction.
6. **Re-open Task 6.4 visual gate** — only after all above succeed.
7. **Update ADR-8 in spec.md §11** — the accepted-risk caveat is realized; either tighten the bypass scope or document the v0.1.5 mitigation strategy as a refinement of the architectural stance.

### Cross-references

- **ADR-8** (`spec.md` §11) — accepted bypass risk; now realized
- **D-02.1-06** (`.planning/phases/02.1-field-merge-fix/deferred-items.md`) — original architectural finding from Phase 2.1; the v0.1.4 fix did NOT lock it shut
- **D-02.1-05** (Phase 2.1 deferred-items) — helper does not backfill cluster-only fields; related but distinct (this regression is about the helper preserving the mask, not about missing fields)
- **REQ-drift-detection** (`.planning/REQUIREMENTS.md`) — correction half NOT cleanly closed; Phase 02.2 closure REJECTED until this regression is fixed
- **Phase 2.1 Lessons** §"Sonarr's API masks privacy=password fields" — the underlying API behavior was documented; the mask-as-credential trap was not caught at planning time
- **Plan 06 SUMMARY** §"Operator Visual Gate FAILED" — full UAT failure write-up

---

*Created: 2026-05-09 (Plan 02.2-06 self-check audit)*
*Updated: 2026-05-09T06:55Z — added D-02.2-AUTH-REGRESSION blocker entry*
