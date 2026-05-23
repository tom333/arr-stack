"""CLI contract: port + host resolution, default port 8765, default host 0.0.0.0
(D-04 amended 2026-05-23 — LAN-exposed by default, override via --host or env).
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from arrconf_ui.__main__ import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    LOOPBACK,
    _resolve_host,
    _resolve_port,
    app,
)


def test_default_port_is_8765() -> None:
    """D-12: default port 8765 (fixed for muscle memory)."""
    assert DEFAULT_PORT == 8765


def test_default_host_is_wildcard_lan_exposed() -> None:
    """D-04 (amended): bind 0.0.0.0 by default — UI accessible on the LAN.

    The homelab trust model assumes everyone on the LAN is trusted (same
    posture as the existing Sonarr/Radarr/Jellyfin UIs). Operator may
    override to 127.0.0.1 via --host flag or ARRCONF_UI_HOST env var.
    """
    assert DEFAULT_HOST == "0.0.0.0"
    assert LOOPBACK == "127.0.0.1"


def test_resolve_host_cli_flag_wins() -> None:
    """CLI --host wins over env var + default."""
    with patch.dict(os.environ, {"ARRCONF_UI_HOST": "192.168.1.42"}):
        assert _resolve_host("127.0.0.1") == "127.0.0.1"


def test_resolve_host_env_var_used_when_no_flag() -> None:
    with patch.dict(os.environ, {"ARRCONF_UI_HOST": "127.0.0.1"}):
        assert _resolve_host(None) == "127.0.0.1"


def test_resolve_host_default_when_nothing_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARRCONF_UI_HOST", raising=False)
    assert _resolve_host(None) == DEFAULT_HOST


def test_resolve_port_cli_flag_wins() -> None:
    """CLI --port wins over env var + default."""
    with patch.dict(os.environ, {"ARRCONF_UI_PORT": "9999"}):
        assert _resolve_port(1234) == 1234


def test_resolve_port_env_var_used_when_no_flag() -> None:
    with patch.dict(os.environ, {"ARRCONF_UI_PORT": "9999"}):
        assert _resolve_port(None) == 9999


def test_resolve_port_invalid_env_falls_back_to_default() -> None:
    with patch.dict(os.environ, {"ARRCONF_UI_PORT": "not_a_port"}):
        assert _resolve_port(None) == DEFAULT_PORT


def test_resolve_port_default_when_nothing_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARRCONF_UI_PORT", raising=False)
    assert _resolve_port(None) == DEFAULT_PORT


def test_cli_help_works() -> None:
    """The typer app has a help text and a `main` command registered."""
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # Typer shows the @app.command() docstring as help text.
    # The help text mentions "config UI" in the docstring body.
    output_lower = result.output.lower()
    assert "config ui" in output_lower or "local web ui" in output_lower


def test_cli_missing_arrconf_yml_exits_2(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If arrconf.yml is missing, CLI exits with code 2 BEFORE binding."""
    from typer.testing import CliRunner

    missing = tmp_path / "does-not-exist.yml"  # type: ignore[operator]
    monkeypatch.setattr("arrconf_ui.__main__.arrconf_yml_path", lambda: missing)
    runner = CliRunner()
    result = runner.invoke(app, ["--no-browser", "--port", "0"])
    assert result.exit_code == 2
    assert "ERROR" in result.output
