import os.path
import time
from typing import Any

from arr_dashboard.models import Row

VIDEO_EXTS = (".mkv", ".mp4", ".avi", ".m4v", ".ts", ".mov", ".wmv")


class ImportActionError(Exception):
    """Raised when a manual import cannot be resolved or fails to complete."""


def _to_local(remote_path: str, mappings: list[dict[str, Any]]) -> str:
    """Translate a qBit-reported path to the *arr's local filesystem view.

    Uses the arr's remote path mappings. Longest exact prefix wins; if none match
    (e.g. qBit's incomplete dir has no explicit mapping), derive the volume-root
    transform from any mapping (the segment where remotePath/localPath diverge,
    e.g. ``/data/`` -> ``/data/torrents/``) and apply it. Returns the path
    unchanged when nothing applies (caller surfaces an explicit error)."""
    for m in sorted(mappings, key=lambda m: len(m.get("remotePath") or ""), reverse=True):
        rp, lp = m.get("remotePath") or "", m.get("localPath") or ""
        if rp and remote_path.startswith(rp):
            return lp + remote_path[len(rp) :]
    for m in mappings:
        rp, lp = m.get("remotePath") or "", m.get("localPath") or ""
        if not rp or not lp:
            continue
        i = 0
        while i < len(rp) and i < len(lp) and rp[-1 - i] == lp[-1 - i]:
            i += 1
        rbase, lbase = rp[: len(rp) - i], lp[: len(lp) - i]
        if rbase and remote_path.startswith(rbase):
            return lbase + remote_path[len(rbase) :]
    return remote_path


def perform_import(row: Row, client: Any) -> None:
    """Force-import the row's downloaded file into the arr library (Copy).

    Resolves the importable file via the arr's ManualImport candidates,
    fires a ManualImport Copy command for the file(s) matching ``row.arr_id``,
    and polls the command until it completes.

    Raises ``ImportActionError`` on no matching candidate, command failure,
    or timeout.
    """
    # Only a completed download has a file on disk to import. An in-progress
    # download (progress < 1.0) has nothing to scan — refuse up front with a clear
    # message instead of fruitlessly scanning the save-root ("no matching file").
    dl = next((d for d in row.downloads if (d.progress or 0.0) >= 1.0), None)
    if dl is None or not dl.content_path or row.arr_id is None:
        raise ImportActionError(f"{row.key}: no completed download to import")
    try:
        mappings = client.get("/remotepathmapping") or []
    except Exception:
        mappings = []
    folder = _to_local(dl.content_path, mappings)
    if folder.endswith(VIDEO_EXTS):
        folder = os.path.dirname(folder)
    candidates = client.manual_import_candidates(folder)

    files: list[dict[str, Any]] = []
    for c in candidates:
        if c.get("rejections"):
            continue
        if not c.get("path"):
            continue
        if row.type == "movie":
            if (c.get("movie") or {}).get("id") == row.arr_id:
                files.append(
                    {
                        "path": c["path"],
                        "movieId": row.arr_id,
                        "quality": c.get("quality"),
                        "languages": c.get("languages", []),
                        "releaseGroup": c.get("releaseGroup", ""),
                    }
                )
        else:
            if (c.get("series") or {}).get("id") == row.arr_id and c.get("episodes"):
                episode_ids = [e["id"] for e in c["episodes"] if e.get("id")]
                if not episode_ids:
                    continue
                files.append(
                    {
                        "path": c["path"],
                        "seriesId": row.arr_id,
                        "episodeIds": episode_ids,
                        "quality": c.get("quality"),
                        "languages": c.get("languages", []),
                        "releaseGroup": c.get("releaseGroup", ""),
                    }
                )
    if not files:
        raise ImportActionError(f"{row.key}: no matching importable file in {folder}")

    cmd = client.manual_import(files, mode="Copy")
    cmd_id = cmd.get("id")
    for _ in range(120):  # ~10 min budget (slow NAS); poll every 5s
        status = client.get(f"/command/{cmd_id}").get("status")
        if status == "completed":
            return
        if status == "failed":
            raise ImportActionError(f"{row.key}: arr ManualImport failed")
        time.sleep(5)
    raise ImportActionError(f"{row.key}: import timed out")
