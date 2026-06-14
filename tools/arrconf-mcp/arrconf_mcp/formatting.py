"""API JSON → compact dicts for LLM consumption (drop noisy fields)."""

from typing import Any

_STALLED = {"stalledDL", "metaDL", "queuedDL", "missingFiles", "error"}


def torrent_brief(t: dict[str, Any]) -> dict[str, Any]:
    """Reduce a qBittorrent torrent record to the fields an LLM needs."""
    return {
        "name": t.get("name"),
        "state": t.get("state"),
        "progress_pct": round((t.get("progress") or 0) * 100),
        "seeders": t.get("num_complete"),
        "category": t.get("category"),
        "tracker": (t.get("tracker") or "").split("/announce")[0],
    }


def is_stalled(t: dict[str, Any]) -> bool:
    """True when a torrent is stuck (stalled/metadata/queued/missing/error)."""
    return t.get("state") in _STALLED
