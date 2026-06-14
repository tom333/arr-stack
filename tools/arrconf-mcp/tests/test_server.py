"""Smoke test: the FastMCP server registers all expected tools by name.

Uses FastMCP's synchronous introspection (``mcp._tool_manager.list_tools()``)
rather than the async ``await mcp.list_tools()`` — same data, no anyio/event-loop
plumbing needed for a pure registration assertion.
"""

from arrconf_mcp.server import mcp

EXPECTED_TOOLS = {
    "stalled_torrents",
    "queue_status",
    "library_overview",
    "transfer_info",
    "cross_seed_status",
    "search_media",
    "add_movie",
    "add_series",
    "request_media",
    "trigger_search_missing",
    "remove_torrent",
    "blocklist_and_research",
    "delete_movie",
    "delete_series",
    "set_quality_profile",
}


def test_server_registers_all_tools() -> None:
    registered = {t.name for t in mcp._tool_manager.list_tools()}
    assert registered == EXPECTED_TOOLS
