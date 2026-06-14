"""Entrypoint: `python -m arrconf_mcp` → runs the MCP server over stdio."""

from arrconf_mcp.server import mcp


def main() -> None:
    mcp.run()  # stdio transport (default)


if __name__ == "__main__":
    main()
