import time
from typing import Any

from arr_dashboard.models import Row


class ImportActionError(Exception):
    """Raised when a manual import cannot be resolved or fails to complete."""


def perform_import(row: Row, client: Any) -> None:
    """Force-import the row's downloaded file into the arr library (Copy).

    Resolves the importable file via the arr's ManualImport candidates,
    fires a ManualImport Copy command for the file(s) matching ``row.arr_id``,
    and polls the command until it completes.

    Raises ``ImportActionError`` on no matching candidate, command failure,
    or timeout.
    """
    if not row.downloads or not row.downloads[0].save_path or row.arr_id is None:
        raise ImportActionError(f"{row.key}: no importable download")
    folder = row.downloads[0].save_path
    candidates = client.manual_import_candidates(folder)

    files: list[dict[str, Any]] = []
    for c in candidates:
        if c.get("rejections"):
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
                files.append(
                    {
                        "path": c["path"],
                        "seriesId": row.arr_id,
                        "episodeIds": [e["id"] for e in c["episodes"]],
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
