"""Smoke test: the FastMCP server registers all expected tools by name.

Uses FastMCP's synchronous introspection (``mcp._tool_manager.list_tools()``)
rather than the async ``await mcp.list_tools()`` — same data, no anyio/event-loop
plumbing needed for a pure registration assertion.

Read-only mode is import-time: ``server.settings.mcp_readonly`` is read once at
module load, and the destructive tools are registered (or not) right then. To
exercise both env values in one process we ``importlib.reload`` the server module
with the env var monkeypatched, then reload it bare in a finally to leave the
module cache in its default (all-15) state for any other test.
"""

import importlib

import pytest

import arrconf_mcp.server as server_module

READ_SAFE_TOOLS = {
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
}

DESTRUCTIVE_TOOLS = {
    "remove_torrent",
    "blocklist_and_research",
    "delete_movie",
    "delete_series",
    "set_quality_profile",
}

EXPECTED_TOOLS = READ_SAFE_TOOLS | DESTRUCTIVE_TOOLS


def _registered(mod: object) -> set[str]:
    return {t.name for t in mod.mcp._tool_manager.list_tools()}  # type: ignore[attr-defined]


def test_server_registers_all_tools() -> None:
    assert _registered(server_module) == EXPECTED_TOOLS


def test_readonly_mode_omits_destructive_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_READONLY", "true")
    try:
        reloaded = importlib.reload(server_module)
        registered = _registered(reloaded)
        assert registered == READ_SAFE_TOOLS
        assert not (registered & DESTRUCTIVE_TOOLS)
    finally:
        monkeypatch.delenv("MCP_READONLY", raising=False)
        importlib.reload(server_module)


def test_default_mode_registers_all_fifteen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_READONLY", raising=False)
    reloaded = importlib.reload(server_module)
    assert _registered(reloaded) == EXPECTED_TOOLS
    assert len(_registered(reloaded)) == 15
