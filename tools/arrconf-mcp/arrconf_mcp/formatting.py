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


def queue_item_brief(item: dict[str, Any], app: str) -> dict[str, Any]:
    """Reduce a Sonarr/Radarr queue record to the fields an LLM needs."""
    return {
        "title": item.get("title"),
        "status": item.get("status"),
        "sizeleft": item.get("sizeleft"),
        "errorMessage": item.get("errorMessage"),
        "app": app,
    }


def disk_brief(disk: dict[str, Any]) -> dict[str, Any]:
    """Reduce a *arr diskspace record to {path, freeGB}."""
    free = disk.get("freeSpace") or 0
    return {"path": disk.get("path"), "freeGB": round(free / 1024**3, 1)}


def transfer_brief(info: dict[str, Any]) -> dict[str, Any]:
    """Reduce a qBittorrent /transfer/info record to the headline metrics."""
    return {
        "dl_speed": info.get("dl_info_speed"),
        "up_speed": info.get("up_info_speed"),
        "dht_nodes": info.get("dht_nodes"),
        "connection_status": info.get("connection_status"),
    }


def lookup_result_brief(item: dict[str, Any], id_field: str) -> dict[str, Any]:
    """Reduce a Radarr/Sonarr lookup result to {title, year, <id_field>, overview[:200]}."""
    return {
        "title": item.get("title"),
        "year": item.get("year"),
        id_field: item.get(id_field),
        "overview": (item.get("overview") or "")[:200],
    }
