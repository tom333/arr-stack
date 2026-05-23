"""arrconf-ui CLI entrypoint — `arrconf-ui [--port 8765] [--no-browser]` (D-12).

Behavior:
1. Locate the repo root via locator.repo_root().
2. Locate charts/arr-stack/files/arrconf.yml — fail fast if missing.
3. Start uvicorn on 127.0.0.1:{port} — loopback only, D-04.
4. Unless --no-browser: webbrowser.open() the URL after a short startup delay.
5. Log `INFO: Local config UI ready at http://localhost:{port}` so the
   operator sees the URL even with --no-browser.
6. SIGINT exits cleanly (uvicorn handles this).

Default port: 8765 (D-12 — fixed for muscle memory; overridable via flag
or ARRCONF_UI_PORT env var).
"""

from __future__ import annotations

import os
import threading
import time
import webbrowser
from typing import Annotated

import structlog
import typer
import uvicorn

from arrconf_ui.locator import arrconf_yml_path

log = structlog.get_logger()

DEFAULT_PORT = 8765
HOST = "127.0.0.1"  # D-04 — loopback only, never wildcard

app = typer.Typer(
    name="arrconf-ui",
    help="Local web UI for editing charts/arr-stack/files/arrconf.yml (Phase 15).",
    no_args_is_help=False,
    add_completion=False,
)


def _resolve_port(port: int | None) -> int:
    """Port resolution: CLI flag -> env var -> default 8765."""
    if port is not None:
        return port
    env = os.environ.get("ARRCONF_UI_PORT")
    if env:
        try:
            return int(env)
        except ValueError:
            log.warning("invalid_port_env", value=env, fallback=DEFAULT_PORT)
    return DEFAULT_PORT


def _open_browser_delayed(url: str, delay_s: float = 0.6) -> None:
    """Open the system browser after uvicorn is ready."""

    def _open() -> None:
        time.sleep(delay_s)
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()


@app.command()
def main(
    port: Annotated[
        int | None,
        typer.Option(
            "--port", "-p", help=f"TCP port (default: {DEFAULT_PORT}, env: ARRCONF_UI_PORT)."
        ),
    ] = None,
    no_browser: Annotated[
        bool,
        typer.Option("--no-browser", help="Do not auto-open the system browser."),
    ] = False,
) -> None:
    """Start the local config UI on 127.0.0.1.

    Logs the URL to stdout so the operator sees it even with --no-browser.
    """
    yml = arrconf_yml_path()
    if not yml.exists():
        typer.echo(f"ERROR: arrconf.yml not found at {yml}", err=True)
        raise typer.Exit(code=2)

    resolved_port = _resolve_port(port)
    url = f"http://localhost:{resolved_port}"
    typer.echo(f"INFO: Local config UI ready at {url}")
    typer.echo(f"INFO: Editing {yml}")

    if not no_browser:
        _open_browser_delayed(url)

    # uvicorn.run is blocking and handles SIGINT cleanly.
    uvicorn.run(
        "arrconf_ui.app:app",
        host=HOST,
        port=resolved_port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    app()
