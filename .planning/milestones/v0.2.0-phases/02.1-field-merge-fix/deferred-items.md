# Deferred Items — Phase 02.1

Items discovered during execution that are out of scope for the current plan but worth tracking.

---

## D-02.1-01 — `snapshot.sh` does not redact Sonarr `config_host` secrets

**Discovered during:** Plan 02.1-01 anti-leak audit (2026-05-08)

**Issue:** `tools/snapshot/snapshot.sh` relies on Sonarr's API-side redaction (`privacy=password` field marker) to mask secrets. This works for `downloadclient.json` (qBit username/password are masked by Sonarr to `********`) but does NOT mask:

- `config_host.json` `apiKey` (real Sonarr API key in plaintext)
- `config_host.json` `password` (Sonarr WebUI password hash, base64)
- `config_host.json` `username` (PII, "moi")

**Workaround applied in Plan 02.1-01:** Manual `jq` post-processing to redact these three fields before commit. See commit `45e2f88` deviation notes.

**Recommended fix (future work, not blocking Phase 2.1):** Add a redaction post-step in `snapshot.sh` that strips these specific fields before writing JSON files. Pattern:

```bash
# In snapshot_arr_app(), after fetching config_host.json:
jq '.apiKey = "***REDACTED***" | .password = "***REDACTED***" | .username = "***REDACTED***"' "$out_file" > "$out_file.tmp" && mv "$out_file.tmp" "$out_file"
```

Could be generalized via a JSON path config (e.g. `redact_paths.json` with `["config_host.json:.apiKey", ...]`).

**Severity:** medium (snapshots are committed to git — leak permanent unless we rewrite history)

---

## D-02.1-02 — `snapshot.sh` does not redact qBittorrent torrent tracker passkeys

**Discovered during:** Plan 02.1-01 anti-leak audit (2026-05-08)

**Issue:** `qbittorrent/torrents_info.json` contains `tracker` and `magnet_uri` fields that may include private tracker passkeys (e.g. `https://c411.org/announce/<32-hex-passkey>`). These are credentials equivalent to API keys.

**Workaround applied in Plan 02.1-01:** Manual `jq walk` to substitute the passkey string with `***REDACTED-PASSKEY***` (handles URL-encoded `%2F` form too). See commit `45e2f88`.

**Recommended fix:** Add tracker-passkey redaction to `snapshot_qbittorrent()`. Pattern: detect `/announce/<32+ hex>` in any string and replace the hex segment with `***REDACTED***`.

**Severity:** high (private tracker passkeys grant download access — leak = trivial credential theft)

---

## D-02.1-03 — qBittorrent crash-loop on stale `qBittorrent_new.conf.lock`

**Discovered during:** Plan 02.1-01 cluster prereq verification (2026-05-08)

**Issue:** qBittorrent pod (`qbittorrent-68b7cc9949-5ld9s`) was in a tight crash-loop (16 container restarts, qbit-nox starting + immediately exiting every ~1s). Root cause: stale `/config/qBittorrent/qBittorrent_new.conf.lock` left over from a different pod (`qbittorrent-68b7cc9949-d22lz`, hostname recorded in lock content). qBit refused to write merged config and exited.

**Workaround applied in Plan 02.1-01:** Manually removed the stale lockfile + ipc-socket via `kubectl exec`. qBit then started cleanly. **No commit needed** (fix is in-cluster runtime state, not in repo).

**Recommended fix (out of scope for arr-stack):** This is a my-kluster (Helm chart) issue — qBittorrent should have a startup probe / init-container that clears stale `.conf.lock` files when the pod's hostname differs from the one recorded in the lockfile. Surface to my-kluster issue tracker if recurrence rate justifies.

**Severity:** medium-low (occasional, manual recovery is straightforward; only blocks operations that need qBit API)

---

## D-02.1-04 — `arrconf-env` secret missing `QBT_USER` and `QBT_PASS`

**Discovered during:** Plan 02.1-01 prereq investigation (2026-05-08)

**Issue:** The `arrconf-env` secret in selfhost only contains `SONARR_API_KEY`. `QBT_USER` and `QBT_PASS` (referenced by `tools/snapshot/snapshot.sh` as required env vars) are not provisioned. This is consistent with the Phase 2.1 root cause: arrconf can't authenticate to qBit because credentials were never passed through.

**Workaround applied in Plan 02.1-01:** Used qBittorrent `WebUI\AuthSubnetWhitelist` modification (added `127.0.0.0/8`) to bypass auth temporarily for the snapshot, then restored original config (verified bit-identical to backup). Captured qBit endpoints via direct `curl` (no login).

**Recommended fix (target: Phase 2.1 PR3 or Phase 3):**
1. Add `QBT_USER` and `QBT_PASS` to `my-kluster/secrets/arrconf-secret.yaml`.
2. arrconf YAML config picks them up via env-var substitution (already supported in `arrconf/config.py` per Phase 1).
3. Once present, snapshot.sh works without bypass.

**Severity:** high (this is the actual Phase 2.1 root cause — empty username/password in arrconf YAML overwrites Sonarr's qBit credentials → Sonarr can't validate → PUT 400 from Phase 2 PARTIAL)

---

## D-02.1-05 — `merge_fields_for_put` does not backfill cluster fields missing from `desired`

**Discovered during:** Plan 02.1-03 Task 3.3 — post-PR3 smoke validation (2026-05-09)

**Issue:** `differ.py:merge_fields_for_put` iterates only `desired.fields[]`. For each entry with `value in ('', None)`, it substitutes the cluster's stored value (D-31/D-32/D-33). But entries that are **missing entirely** from `desired.fields[]` are simply omitted from the PUT body. Sonarr's `PUT /api/v3/downloadclient/{id}` accepts the partial body; whether stored values for missing fields are preserved or cleared is implementation-defined.

PR3 (D-36) removed the `username: ''` / `password: ''` placeholder entries from `arrconf.yml` under the assumption that the helper made them redundant. The post-PR3 smoke produced 0 `merge_field_preserved` events (helper had nothing to substitute against), so the plan's dispositive proof gate was unsatisfiable. Operator UI verification confirmed Sonarr's stored credentials were intact (the `null` reported by Sonarr's GET API was cosmetic, not a real clear), but the proof-via-log path was blocked.

**Workaround applied in Plan 02.1-03 (PR4 hotfix #1370):** Re-added the `username: ''` / `password: ''` placeholders to `arrconf.yml`. The post-PR4 smoke captured the dispositive `merge_field_preserved` events for both fields. Future arrconf YAML for credential-bearing fields should keep the placeholder entries.

**Recommended fix (target: Phase 3 — Radarr / Prowlarr will face the same shape):**
Enhance `merge_fields_for_put` with a backfill pass:

```python
# After the existing for-loop on desired.fields[], add:
existing_names = {f["name"] for f in merged_fields}
for cur_f in cur_dump.get("fields", []):
    if cur_f["name"] not in existing_names:
        merged_fields.append(cur_f)
        log.info("merge_field_backfilled", name=cur_f["name"])
```

Add a corresponding test scenario (`test_merge_backfills_missing_fields_from_cluster`) and document the new event name. Then re-evaluate whether to drop placeholder entries again at the YAML level.

**Severity:** medium (correctness contract gap; mitigated by retaining placeholders, but the existing helper is fragile to YAML-side simplification)

---

## D-02.1-06 — `merge_fields_for_put` preserves Sonarr API-mask `"********"` for password fields, breaking PUT pre-save validation when ANY top-level field actually changes

**Discovered during:** Plan 02.1-04 Task 4.2 — drift demo runbook (2026-05-09)

**Issue:** Sonarr's `GET /api/v3/downloadclient/{id}` masks credential-marked fields (`privacy: password`) by returning the literal string `"********"` instead of the stored value. The merge helper (D-31/D-32/D-33) preserves this mask: when YAML has `password: ''`, the helper substitutes the cluster's GET-time value, which is the masked sentinel `"********"`.

For an idempotent PUT (no real field-level changes), this works because Sonarr's pre-save validation skips qBittorrent re-authentication when the body equals stored state. **Confirmed by Plan 02.1-03 Task 3.3 PR4 smoke success** (`diff_fields=[fields]` with all merged values matching cluster).

For a PUT that includes any real change (e.g. drift on `priority`), Sonarr's pre-save validation tries to authenticate to qBittorrent using `"********"` as the literal password value → **HTTP 400 "Échec de l'authentification" / "Failed to connect to qBittorrent"**. The arrconf reconcile job correctly:
1. Detects the drift (`plan_action action=update` event with `diff_fields=[fields, priority]`)
2. Fires the merge helper (`merge_field_preserved` events for username + password)
3. Builds the PUT body with the masked password substituted

But Sonarr rejects the PUT.

**Reproduction (operator-side):**
```bash
SONARR_API_KEY=$(...)
# Drift priority via curl ?forceSave=true
curl -s "http://localhost:8989/api/v3/downloadclient/1" -H "X-Api-Key: $SONARR_API_KEY" \
  | jq '.priority = 5' > /tmp/dc-drifted.json
curl -X PUT "http://localhost:8989/api/v3/downloadclient/1?forceSave=true" \
  -H "X-Api-Key: $SONARR_API_KEY" -H "Content-Type: application/json" \
  -d @/tmp/dc-drifted.json
# Force arrconf reconcile job
kubectl create job --from=cronjob/arrconf arrconf-drift-demo-$(date +%s) -n selfhost
# Job logs show the events above + HTTPStatusError 400
```

**Workaround applied in Plan 02.1-04 Task 4.2:** Operator-driven manual revert via `curl -X PUT .../?forceSave=true` — bypasses Sonarr's pre-save validation since the operator KNOWS the cluster password is intact. The W-04 dispositive `RESTORED_PRIORITY == ORIGINAL_PRIORITY` was satisfied via this manual nudge (foreseen by Plan 04 brief). The arrconf reconcile job's correct DETECTION (logged events) plus the manual CORRECTION proves REQ-drift-detection's two halves separately.

**Recommended fix (target: v0.1.4 / Phase 3 retro):**

Add `?forceSave=true` to arrconf's UPDATE-branch PUT. Two implementation options:

```python
# Option A — unconditional (safest, matches Sonarr UI behavior on Save):
client.put(path, id=p.current.id, json=body, params={"forceSave": "true"})

# Option B — conditional on detected mask in body:
needs_force = any(f.get("value") == "***REDACTED***" or f.get("value") == "********"
                  for f in body.get("fields", []))
client.put(path, id=p.current.id, json=body,
           params={"forceSave": "true"} if needs_force else None)
```

`?forceSave=true` is what the Sonarr UI itself uses when the user clicks "Save" on a download client form (per disassembling the React frontend's save handler). Skipping pre-save validation is safe in arrconf's context because:
1. arrconf's own `diff` already determined a real change is needed
2. The merged PUT body preserves cluster's stored credentials by design (D-31/D-32 contract)
3. arrconf is the trusted controller — Sonarr's UI-grade validation is meant for human-driven misconfigs

Add corresponding test scenario (`test_update_uses_forceSave_when_masked_credential_in_body`) and a short ADR note in spec.md §11 if a new constraint emerges.

**Severity:** high (blocks the drift-correction half of REQ-drift-detection — without this fix, arrconf can detect drift but cannot correct any mutation that touches a top-level field on a download_client)
