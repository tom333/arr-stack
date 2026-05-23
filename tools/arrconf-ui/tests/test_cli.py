"""CLI contract: port resolution, default port 8765, host 127.0.0.1 (D-04 + D-12)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from arrconf_ui.__main__ import DEFAULT_PORT, HOST, _resolve_port, app


def test_default_port_is_8765() -> None:
    """D-12: default port 8765 (fixed for muscle memory)."""
    assert DEFAULT_PORT == 8765


def test_host_is_loopback_only() -> None:
    """D-04: bind 127.0.0.1 only — loopback interface, not wildcard."""
    assert HOST == "127.0.0.1"


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
