"""Entrypoint: `python -m arrconf_mcp`.

Default transport is stdio (runs locally beside Claude Code). When
``MCP_TRANSPORT=http`` the server runs over streamable-HTTP via uvicorn on
``MCP_BIND`` (host:port), bearer-authed in-server — used by the in-cluster
deploy (Phase 3).
"""

from arrconf_mcp.settings import McpSettings


def main() -> None:
    s = McpSettings()
    if s.mcp_transport == "http":
        import uvicorn

        from arrconf_mcp.http import build_app

        host, _, port = s.mcp_bind.rpartition(":")
        uvicorn.run(build_app(), host=host or "0.0.0.0", port=int(port))
    else:
        from arrconf_mcp.server import mcp

        mcp.run()  # stdio transport (default)


if __name__ == "__main__":
    main()
