"""FastMCP server exposing read + safe-action tools over the arrconf clients."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from arrconf_mcp import clients, formatting

mcp = FastMCP("arrconf-mcp")


@mcp.tool()
def stalled_torrents() -> list[dict[str, Any]]:
    """List qBittorrent torrents that are stuck (stalled/metadata/error), with seeders + tracker."""
    info = clients.qbit().get("/torrents/info")
    return [formatting.torrent_brief(t) for t in info if formatting.is_stalled(t)]


@mcp.tool()
def queue_status() -> list[dict[str, Any]]:
    """List active download-queue items across Sonarr and Radarr (title, status, size left, error)."""
    items: list[dict[str, Any]] = []
    for app, client in (("sonarr", clients.sonarr()), ("radarr", clients.radarr())):
        records = client.get("/queue").get("records", [])
        items.extend(formatting.queue_item_brief(r, app) for r in records)
    return items


@mcp.tool()
def library_overview() -> dict[str, Any]:
    """Library size summary: Sonarr series count, Radarr movie count, and free disk per root."""
    series_count = len(clients.sonarr().get("/series"))
    radarr = clients.radarr()
    movie_count = len(radarr.get("/movie"))
    disks = [formatting.disk_brief(d) for d in radarr.get("/diskspace")]
    return {"series_count": series_count, "movie_count": movie_count, "disks": disks}


@mcp.tool()
def transfer_info() -> dict[str, Any]:
    """Global qBittorrent transfer state: download/upload speed, DHT nodes, connection status."""
    return formatting.transfer_brief(clients.qbit().get("/transfer/info"))


@mcp.tool()
def cross_seed_status() -> dict[str, Any]:
    """Re-seed progress: count + brief of torrents in the cross-seed-link qBittorrent category."""
    info = clients.qbit().get("/torrents/info", params={"category": "cross-seed-link"})
    return {"count": len(info), "torrents": [formatting.torrent_brief(t) for t in info]}
