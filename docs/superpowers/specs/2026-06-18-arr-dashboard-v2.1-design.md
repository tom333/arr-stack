# arr-dashboard V2.1 — Recovery actions design spec

**Date:** 2026-06-18
**Status:** Design approved (brainstorming) — pending spec review → writing-plans
**Builds on:** V2.0 import action (`docs/superpowers/specs/2026-06-18-arr-dashboard-v2-design.md`).

## Goal

Add per-problem recovery actions to the dashboard so the operator fixes flagged rows in place instead of opening qBit/Sonarr/Jellyfin. Three actions, each tied to an existing flag:

| Flag | Action | Determinism |
|---|---|---|
| `doublon` (≥2 downloads) | **Delete a chosen download** (manual, per-download) | Operator picks which — NOT auto |
| `bloque` (stalledDL / missingFiles / error) | **Remove the stuck download** (+ files) | Auto/deterministic |
| `pas-dans-jellyfin` (imported, not in Jellyfin) | **Targeted Jellyfin scan** of the file's path | Auto/deterministic |

## Non-goals (V2.1)

- **grab-cancel** — deferred (operator chose to drop it).
- **doublon auto-delete** — explicitly rejected: the operator chooses which duplicate to delete (auto-deleting the wrong one is risky).
- **blocklist / re-search** on remove — `bloque` is delete-only (no blocklist, no auto re-search).
- No auth (LAN-trusted, consistent with the rest of the dashboard).

---

## Architecture

These actions are **fast API calls (no large NAS IO)** → they run **immediately**, NOT through the serialized `ImportQueue` (which stays reserved for the NAS-heavy import). No queue, no job tracking — the action returns a result; the next 30s snapshot reflects the change.

### Backend

```
tools/arr-dashboard/arr_dashboard/
  recovery_actions.py    # NEW: delete_download() / remove_stuck() / jellyfin_scan() — thin, client-driven
  sources.py             # build_clients(): add qBit + Jellyfin (currently radarr/sonarr only)
  app.py                 # 3 new endpoints
```

`build_clients(settings)` currently returns `{radarr, sonarr}`. Extend to also build:
- `qbit` → `QbittorrentClient(settings.qbittorrent_url, settings.qbt_user, settings.qbt_pass)` (when creds set)
- `jellyfin` → `JellyfinClient(settings.jellyfin_url, settings.jellyfin_api_key)` (when key set)

### Endpoints (in `app.py`)

| Method/Path | Body | Confirm gate | Effect |
|---|---|---|---|
| `POST /api/actions/delete-download` | `{key, infohash, confirm:true}` | **yes** | delete that one qBit torrent + its files |
| `POST /api/actions/remove` | `{key, confirm:true}` | **yes** | delete the row's stuck download(s) + files + clean arr queue |
| `POST /api/actions/jellyfin-scan` | `{key}` | no (safe) | targeted Jellyfin scan of the row's disk path(s) |

`confirm:true` gate mirrors the import endpoint (`HTTPException(400, "confirm:true required")` otherwise). Each resolves the row from the cache snapshot by `key` (404 if gone), then calls the matching `recovery_actions` function with the needed client(s).

### `recovery_actions.py` functions

```python
def delete_download(infohash: str, qbit: Any) -> None:
    """Remove a single torrent + its files from qBit (the operator's chosen duplicate)."""
    qbit.post_form("/torrents/delete", {"hashes": infohash, "deleteFiles": "true"})

def remove_stuck(row: Row, qbit: Any, arr: Any) -> None:
    """Delete the row's stuck downloads (state in STUCK_STATES) + files, then drop the
    matching arr queue records. Raises RecoveryActionError if no stuck download."""
    STUCK = {"stalledDL", "missingFiles", "error"}
    stuck = [d for d in row.downloads if d.state in STUCK]
    if not stuck:
        raise RecoveryActionError(f"{row.key}: no stuck download")
    for d in stuck:
        qbit.post_form("/torrents/delete", {"hashes": d.infohash, "deleteFiles": "true"})
    # drop arr queue entries pointing at those infohashes (already removed from client)
    for q in arr.list_queue():
        if (q.get("downloadId") or "").lower() in {d.infohash for d in stuck}:
            arr.delete("/queue", q["id"])  # removeFromClient handled above

def jellyfin_scan(row: Row, jellyfin: Any) -> None:
    """Targeted incremental scan: tell Jellyfin the row's file path(s) changed so it
    scans just that path's library (not a full /Library/Refresh)."""
    if not row.disk_paths:
        raise RecoveryActionError(f"{row.key}: no disk path to scan")
    updates = [{"Path": p, "UpdateType": "Created"} for p in row.disk_paths]
    jellyfin.post("/Library/Media/Updated", {"Updates": updates})
```

Notes:
- `QbittorrentClient.post_form` exists (arrconf). qBit delete = form POST `/torrents/delete` with `hashes` + `deleteFiles`.
- `ArrApiClient.delete(path, id)` exists (arrconf) for the queue cleanup.
- `JellyfinClient.post(path, json)` — verify it exists / supports a JSON body; if the arrconf JellyfinClient only has `get`, add a minimal `post` (or use the base client's post). `/Library/Media/Updated` is a documented Jellyfin endpoint accepting `{Updates:[{Path,UpdateType}]}`.
- `RecoveryActionError` raised → endpoint returns `HTTPException(400/409, str(exc))`.

---

## Frontend (`web/src/`)

Mirror the existing V2 action UX (`ImportButton`, `ConfirmDialog`, `ActionsPanel`, `api.ts`). These actions are immediate (no job panel); show a transient toast on success and rely on the 30s refresh to reflect the change.

- **`api.ts`**: add `deleteDownload(key, infohash)`, `removeStuck(key)`, `jellyfinScan(key)` (POST helpers; the two destructive ones send `confirm:true`).
- **`RowDetail.svelte`** (the expandable per-row detail, already lists downloads): add a **"Supprimer"** button next to each download → `ConfirmDialog` ("Supprimer ce torrent + ses fichiers ?") → `deleteDownload(key, d.infohash)`. This is the `doublon` workflow — operator expands the row, sees each download (name/state/%/tracker/size), picks which to delete.
- **Row-level buttons** (in `App.svelte` table, a small actions cell or inline with flags):
  - `bloque` flag → **"Suppr bloqué"** button → `ConfirmDialog` → `removeStuck(key)`.
  - `pas-dans-jellyfin` flag → **"Scan JF"** button → `jellyfinScan(key)` (no confirm; safe).
- Reuse `ConfirmDialog.svelte` for the two destructive actions. A small `Toast`/inline status for feedback.

---

## Safety

- `confirm:true` required on `delete-download` + `remove` (they delete files). `jellyfin-scan` needs none (non-destructive trigger).
- No new auth (LAN-trusted; the service already sits behind the oauth2-proxy ingress for external access).
- The cache-snapshot row lookup means actions operate on the last-known state (≤30s old). Acceptable — qBit delete by infohash is idempotent-ish (deleting an absent hash is a no-op on qBit's side).
- Graceful errors: a missing client (e.g. qBit creds absent) → `HTTPException(400, "no qbit client")`, never a 500.

---

## Testing

- **`recovery_actions`** (primary): mock the clients (respx for the arrconf clients), assert:
  - `delete_download` → qBit `/torrents/delete` called with the infohash + `deleteFiles=true`.
  - `remove_stuck` → only stuck-state downloads deleted; arr queue entries with matching downloadId dropped; raises when no stuck download.
  - `jellyfin_scan` → Jellyfin `/Library/Media/Updated` called with the row's paths; raises when no disk_path.
- **endpoint tests** (`test_app.py`): confirm gate (400 without `confirm:true`), row-not-found 404, happy path dispatches the right `recovery_actions` function (monkeypatch / mocked clients).
- Coverage ≥70% gate; recovery_actions ≥90%.
- Python triad (ruff + mypy) + frontend `npm run build` + `npm run check` clean.

---

## Deploy

- **arr-dashboard-only** change (no `tools/arrconf` touched) → bump **only** `arr-dashboard.image.tag`. `feat:` → minor → next tag (e.g. v0.36.0). Same release flow: co-bump values, push main, chart-lint auto-tags + dispatches the arr-dashboard image build, verify GHCR, bump my-kluster `targetRevision`.
- No chart/schema changes.

## Out of scope / future (V2.2+)

grab-cancel; doublon auto-rules; blocklist+re-search recovery; bulk actions (select many rows).
