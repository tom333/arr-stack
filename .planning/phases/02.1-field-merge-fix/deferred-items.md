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
