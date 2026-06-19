# arr-dashboard — Re-announce / Re-check recovery actions design spec

**Date:** 2026-06-19
**Status:** Design approved (brainstorming) — pending spec review → writing-plans
**Builds on:** V2.1 recovery actions (`recovery_actions.py` + `/api/actions/*`) and the stall-diagnostics feature (`Download.diagnosis`).

## Goal

Give the operator two qBit-level recovery levers on a stalled download, directly from the
dashboard's expanded row detail:
- **Re-announce** — force a fresh tracker announce. Unsticks a transient no-peers/announce
  hiccup, and (key for this homelab) re-accepts a private-tracker torrent *immediately
  after the operator improves their ratio* instead of waiting for qBit's announce interval.
- **Re-check** — force qBit to re-verify the downloaded pieces against disk. Unsticks a
  download whose data qBit believes is incomplete/corrupt.

Both are read-only with respect to deletion (no data removed); they complement the V2.1
`delete-download` (the destructive lever).

## Honesty about ratio-blocked downloads

Re-announce does **not** create ratio. On a `tracker-refused` download (e.g. C411 returning
`Forbidden` for low ratio), re-announcing while the ratio is still too low just gets another
`Forbidden`. We still offer it (it is the correct action *after* the operator feeds ratio),
but the UI shows a hint on `tracker-refused` downloads: *"ne débloque qu'après remontée du
ratio"*. We do not hide the button (hiding it would remove the legitimate post-ratio-fix use).

## Non-goals

- grab-cancel, arr re-search/blocklist, automatic ratio feeding, bulk actions — out of scope.
- No new stall classification (uses the existing `Download.diagnosis` for the hint only).

---

## Architecture

arr-dashboard-only, a thin extension of the V2.1 recovery-action pattern. Uses the existing
public `QbittorrentClient.post_form` — no `tools/arrconf` change → no arrconf image co-bump.

### Backend — `recovery_actions.py` (two new functions, mirroring `delete_download`)

```python
def reannounce(infohash: str, qbit: Any) -> None:
    """Force a fresh tracker announce for one torrent (qBit /torrents/reannounce)."""
    if not infohash:
        raise RecoveryActionError("reannounce: empty infohash")
    qbit.post_form("/torrents/reannounce", {"hashes": infohash})


def recheck(infohash: str, qbit: Any) -> None:
    """Force qBit to re-verify a torrent's downloaded pieces (/torrents/recheck)."""
    if not infohash:
        raise RecoveryActionError("recheck: empty infohash")
    qbit.post_form("/torrents/recheck", {"hashes": infohash})
```

Both are per-download (keyed by `infohash`), non-destructive, and idempotent-ish (qBit
accepts repeated reannounce/recheck). The empty-infohash guard mirrors `delete_download`
(an empty `hashes` form value would target *all* torrents in qBit).

### Backend — endpoints in `app.py`

| Method/Path | Body | Confirm gate | Effect |
|---|---|---|---|
| `POST /api/actions/reannounce` | `{key, infohash}` | **no** (instant, free) | `reannounce(infohash, qbit)` |
| `POST /api/actions/recheck` | `{key, infohash, confirm:true}` | **yes** | `recheck(infohash, qbit)` |

Re-check requires `confirm:true` because re-verifying a large partially-downloaded torrent
re-reads its data from the slow NAS (read IO; can degrade Jellyfin — same caution class as
import, though read-only). Re-announce needs no confirm (a tracker ping, no IO).

Each endpoint: gate (recheck only) → resolve the row from the cache snapshot by `key`
(404 if gone) → require non-empty `infohash` (400) → `build_qbit(...)` (400 `"no qbit
client"` if creds absent) → call the `recovery_actions` function → `RecoveryActionError`
→ 409. Return `{"status": "...", "infohash": infohash}`. This is exactly the shape of the
V2.1 `delete-download` endpoint.

### Frontend — `web/src/`

- **`api.ts`**: `reannounce(key, infohash)` (POST, no confirm) and `recheck(key, infohash)`
  (POST with `confirm:true`). Both `Promise<void>`, throw on `!res.ok` — same shape as the
  V2.1 `deleteDownload`.
- **`RowDetail.svelte`** (the expanded per-download list, already has the "Supprimer"
  button): add two buttons per download next to "Supprimer":
  - **"Re-announce"** → calls `reannounce(row.key, d.infohash)` directly (no dialog).
  - **"Re-check"** → opens `ConfirmDialog` (warn: *"re-vérifie les pièces — relit les
    données depuis le NAS"*) → `recheck(row.key, d.infohash)`.
  - When `d.diagnosis?.cause === "tracker-refused"`, render a small inline hint after the
    Re-announce button: *"ne débloque qu'après remontée du ratio"*.
  These are immediate actions (no job panel); the 30s refresh reflects the new state.
- Reuse the existing `ConfirmDialog` (it already takes a `warn` prop from V2.1).

---

## Error handling / edge cases

- qBit creds absent → `build_qbit` returns None → endpoint 400 `"no qbit client"`, never 500.
- Empty/missing `infohash` in the body → 400 (and the `recovery_actions` guard is a second
  layer that would raise `RecoveryActionError` → 409).
- Row evicted from snapshot between render and click → 404.
- qBit rejects the form (unexpected) → `post_form` raises → surfaces as 500 from the
  endpoint only if not a `RecoveryActionError`; acceptable (matches V2.1 delete-download,
  which also lets unexpected qBit errors propagate). The confirm gate + row-resolve cover
  the foreseeable bad inputs.
- A complete or non-stalled download: the buttons still work (re-announce/re-check are valid
  on any torrent) — we do not restrict them to stalled rows, but they only *appear* in the
  expanded detail, which the operator opens deliberately.

---

## Testing

- **`recovery_actions`** (mock the qBit client): `reannounce` → `post_form("/torrents/reannounce",
  {"hashes": infohash})`; `recheck` → `post_form("/torrents/recheck", {"hashes": infohash})`;
  both raise `RecoveryActionError` on empty infohash and send nothing.
- **endpoint tests** (`test_app.py`): `recheck` 400 without `confirm:true`; both 404 on
  unknown key; both 400 when `build_qbit` returns None (monkeypatch); both dispatch the right
  `recovery_actions` function on the happy path (monkeypatch). `reannounce` needs no confirm
  (200 without it).
- Coverage ≥70% gate; recovery_actions stays ≥90%. Python triad (ruff + mypy) + frontend
  `npm run build` + `npm run check` clean.

## Deploy

arr-dashboard-only (no `tools/arrconf`) → bump only `arr-dashboard.image.tag`. `feat:` →
minor → next tag from latest (`v0.38.0` → **`v0.39.0`**; recompute at release from the
highest conventional-commit type since the last tag — the `feat:` release-pin commit forces
minor). Same lockstep: push main → chart-lint auto-tags + dispatches the arr-dashboard image
→ verify GHCR manifest → bump my-kluster `targetRevision` → hard-refresh app-of-apps → verify
pod.

## Out of scope / future

grab-cancel; arr re-search + blocklist; automatic ratio feeding; bulk select+act; pausing a
ratio-blocked torrent to stop it churning announces.
