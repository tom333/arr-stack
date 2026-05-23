"""arrconf-ui CLI entrypoint — `arrconf-ui [--port 8765] [--host 0.0.0.0] [--no-browser]`.

Behavior:
1. Locate the repo root via locator.repo_root().
2. Locate charts/arr-stack/files/arrconf.yml — fail fast if missing.
3. Start uvicorn on {host}:{port}.
4. Unless --no-browser: webbrowser.open() the URL after a short startup delay.
5. Log `INFO: Local config UI ready at http://...:{port}` so the operator
   sees both the local URL and the LAN-accessible URL.
6. SIGINT exits cleanly (uvicorn handles this).

Default port: 8765 (D-12 — fixed for muscle memory; overridable via flag
or ARRCONF_UI_PORT env var).

Default host: 0.0.0.0 (CONTEXT D-04 amended 2026-05-23 per operator request —
the UI is reachable on the local network). To restrict to loopback only,
set ARRCONF_UI_HOST=127.0.0.1 or pass --host 127.0.0.1. NO AUTH SCHEME —
the homelab trust model assumes everyone on the LAN is trusted (same as
the existing Sonarr/Radarr/Jellyfin/qBittorrent UIs which also expose
without app-level auth).
"""

from __future__ import annotations

import os
import socket
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
DEFAULT_HOST = "0.0.0.0"  # nosec — CONTEXT D-04 (revision-2): LAN-exposed by default.
# Operator may set ARRCONF_UI_HOST=127.0.0.1 or pass --host 127.0.0.1 to restrict.
LOOPBACK = "127.0.0.1"

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


def _resolve_host(host: str | None) -> str:
    """Host resolution: CLI flag -> env var -> default 0.0.0.0 (LAN-exposed)."""
    if host is not None:
        return host
    env = os.environ.get("ARRCONF_UI_HOST")
    if env:
        return env
    return DEFAULT_HOST


def _lan_url(port: int) -> str | None:
    """Return the LAN-accessible URL if the host has a non-loopback IP, else None.

    Best-effort: opens a UDP socket to a public IP (no packet sent) to learn
    the outbound interface address. Works on most homelab setups; fails
    gracefully if the host is offline.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.2)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        if ip and ip != LOOPBACK:
            return f"http://{ip}:{port}"
    except OSError:
        pass
    return None


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
    host: Annotated[
        str | None,
        typer.Option(
            "--host",
            "-h",
            help=(
                f"Bind interface (default: {DEFAULT_HOST} — LAN-accessible; "
                "use 127.0.0.1 for loopback only, env: ARRCONF_UI_HOST)."
            ),
        ),
    ] = None,
    no_browser: Annotated[
        bool,
        typer.Option("--no-browser", help="Do not auto-open the system browser."),
    ] = False,
) -> None:
    """Start the local config UI.

    Default bind: 0.0.0.0:8765 — the UI is reachable on the local network.
    To restrict to loopback only, pass --host 127.0.0.1 or set
    ARRCONF_UI_HOST=127.0.0.1.
    """
    yml = arrconf_yml_path()
    if not yml.exists():
        typer.echo(f"ERROR: arrconf.yml not found at {yml}", err=True)
        raise typer.Exit(code=2)

    resolved_port = _resolve_port(port)
    resolved_host = _resolve_host(host)
    local_url = f"http://localhost:{resolved_port}"
    typer.echo(f"INFO: Local config UI ready at {local_url}")
    if resolved_host == "0.0.0.0":  # nosec — intentional LAN exposure per CONTEXT D-04 amendment.
        lan_url = _lan_url(resolved_port)
        if lan_url:
            typer.echo(f"INFO: LAN-accessible at {lan_url}")
    typer.echo(f"INFO: Editing {yml}")

    if not no_browser:
        _open_browser_delayed(local_url)

    # uvicorn.run is blocking and handles SIGINT cleanly.
    uvicorn.run(
        "arrconf_ui.app:app",
        host=resolved_host,
        port=resolved_port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    app()
