import json
from typing import Any

from arr_dashboard.models import Row

STUCK_STATES = {"stalledDL", "missingFiles", "error"}


class RecoveryActionError(Exception):
    """Raised when a recovery action cannot be applied to a row."""


def delete_download(infohash: str, qbit: Any) -> None:
    """Remove a single torrent + its files from qBit (the operator's chosen duplicate)."""
    qbit.post_form("/torrents/delete", {"hashes": infohash, "deleteFiles": "true"})


def remove_stuck(row: Row, qbit: Any, arr: Any) -> None:
    """Delete the row's stuck downloads (+ files) from qBit, then drop the matching
    *arr queue records. Raises RecoveryActionError if the row has no stuck download."""
    stuck = [d for d in row.downloads if d.state in STUCK_STATES]
    if not stuck:
        raise RecoveryActionError(f"{row.key}: no stuck download")
    stuck_hashes = {d.infohash.lower() for d in stuck}
    for d in stuck:
        qbit.post_form("/torrents/delete", {"hashes": d.infohash, "deleteFiles": "true"})
    # the torrents are already gone from the client, so removeFromClient=false
    for q in arr.list_queue():
        if (q.get("downloadId") or "").lower() in stuck_hashes:
            arr.delete(
                "/queue", q["id"], params={"removeFromClient": "false", "blocklist": "false"}
            )


def jellyfin_scan(row: Row, jellyfin: Any) -> None:
    """Targeted incremental scan: tell Jellyfin the row's file path(s) changed so it
    rescans just those paths (not a full /Library/Refresh)."""
    if not row.disk_paths:
        raise RecoveryActionError(f"{row.key}: no disk path to scan")
    updates = [{"Path": p, "UpdateType": "Created"} for p in row.disk_paths]
    try:
        jellyfin.post("/Library/Media/Updated", {"Updates": updates})
    except json.JSONDecodeError:
        pass  # Jellyfin write endpoints return 204 No Content → success, empty body
