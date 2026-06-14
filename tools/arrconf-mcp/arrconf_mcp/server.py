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
