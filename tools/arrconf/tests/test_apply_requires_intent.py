"""CATMIG-01 guard-path test (Phase 32 Plan 01, Task 2 / T-32-03).

Verifies that apply() and diff() fail fast with exit 2 + structlog event
``intent_required_for_categories`` when intent.yml is absent and a
categories-driven app (sonarr/radarr/qbittorrent/jellyfin) is targeted.

This prevents a silent partial reconcile (T-32-03 mitigation).
Mirrors the missing_api_key gate test style (test_qbit_credentials_env_fallback.py).

Note: structlog.testing.capture_logs() does NOT intercept events when the app
uses configure_logging() (which installs a JSON renderer that writes to stdout
before the capture processor). We verify via result.output instead — mirrors
the pattern used throughout test_cli.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from arrconf.__main__ import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_arrconf_yml(tmp_path: Path) -> Path:
    """Minimal valid arrconf.yml with all 4 cat-driven apps declared."""
    cfg = tmp_path / "arrconf.yml"
    cfg.write_text(
        "sonarr:\n"
        "  main:\n"
        "    base_url: http://sonarr.test:8989\n"
        "radarr:\n"
        "  main:\n"
        "    base_url: http://radarr.test:7878\n"
        "qbittorrent:\n"
        "  main:\n"
        "    base_url: http://qbittorrent.test:8080\n"
        "jellyfin:\n"
        "  main:\n"
        "    base_url: http://jellyfin.test:8096\n",
        encoding="utf-8",
    )
    return cfg


# ---------------------------------------------------------------------------
# apply() guard tests
# ---------------------------------------------------------------------------


def test_apply_requires_intent_for_sonarr(minimal_arrconf_yml: Path, tmp_path: Path) -> None:
    """apply() with intent absent + --apps sonarr → exit 2 + intent_required_for_categories."""
    intent_path = tmp_path / "intent.yml"
    # intent.yml does NOT exist

    result = runner.invoke(
        app,
        [
            "--config",
            str(minimal_arrconf_yml),
            "--intent",
            str(intent_path),
            "apply",
            "--apps",
            "sonarr",
        ],
        env={"SONARR_API_KEY": "fake", "QBT_USER": "u", "QBT_PASS": "p"},
        catch_exceptions=False,
    )

    assert result.exit_code == 2, (
        f"Expected exit 2, got {result.exit_code}. Output:\n{result.output}"
    )
    assert "intent_required_for_categories" in result.output, (
        f"Expected intent_required_for_categories in output: {result.output}"
    )


def test_apply_requires_intent_for_radarr(minimal_arrconf_yml: Path, tmp_path: Path) -> None:
    """apply() with intent absent + --apps radarr → exit 2."""
    intent_path = tmp_path / "intent.yml"

    result = runner.invoke(
        app,
        [
            "--config",
            str(minimal_arrconf_yml),
            "--intent",
            str(intent_path),
            "apply",
            "--apps",
            "radarr",
        ],
        env={"RADARR_API_KEY": "fake", "QBT_USER": "u", "QBT_PASS": "p"},
        catch_exceptions=False,
    )

    assert result.exit_code == 2
    assert "intent_required_for_categories" in result.output


def test_apply_requires_intent_for_qbittorrent(minimal_arrconf_yml: Path, tmp_path: Path) -> None:
    """apply() with intent absent + --apps qbittorrent → exit 2."""
    intent_path = tmp_path / "intent.yml"

    result = runner.invoke(
        app,
        [
            "--config",
            str(minimal_arrconf_yml),
            "--intent",
            str(intent_path),
            "apply",
            "--apps",
            "qbittorrent",
        ],
        env={"QBT_USER": "u", "QBT_PASS": "p"},
        catch_exceptions=False,
    )

    assert result.exit_code == 2
    assert "intent_required_for_categories" in result.output


def test_apply_requires_intent_for_jellyfin(minimal_arrconf_yml: Path, tmp_path: Path) -> None:
    """apply() with intent absent + --apps jellyfin → exit 2."""
    intent_path = tmp_path / "intent.yml"

    result = runner.invoke(
        app,
        [
            "--config",
            str(minimal_arrconf_yml),
            "--intent",
            str(intent_path),
            "apply",
            "--apps",
            "jellyfin",
        ],
        env={"JELLYFIN_API_KEY": "fake"},
        catch_exceptions=False,
    )

    assert result.exit_code == 2
    assert "intent_required_for_categories" in result.output


def test_apply_prowlarr_does_not_require_intent(minimal_arrconf_yml: Path, tmp_path: Path) -> None:
    """apply() with intent absent + --apps prowlarr does NOT trigger the guard.

    Prowlarr does not use categories — no guard required.
    """
    intent_path = tmp_path / "intent.yml"
    # intent.yml does NOT exist

    result = runner.invoke(
        app,
        [
            "--config",
            str(minimal_arrconf_yml),
            "--intent",
            str(intent_path),
            "apply",
            "--apps",
            "prowlarr",
        ],
        env={"PROWLARR_API_KEY": "fake"},
        catch_exceptions=False,
    )
    # Key: NOT exit 2 from intent guard.
    assert "intent_required_for_categories" not in result.output


# ---------------------------------------------------------------------------
# diff() guard tests
# ---------------------------------------------------------------------------


def test_diff_requires_intent_for_sonarr(minimal_arrconf_yml: Path, tmp_path: Path) -> None:
    """diff() with intent absent + --apps sonarr → exit 2 + intent_required_for_categories."""
    intent_path = tmp_path / "intent.yml"

    result = runner.invoke(
        app,
        [
            "--config",
            str(minimal_arrconf_yml),
            "--intent",
            str(intent_path),
            "diff",
            "--apps",
            "sonarr",
        ],
        env={"SONARR_API_KEY": "fake", "QBT_USER": "u", "QBT_PASS": "p"},
        catch_exceptions=False,
    )

    assert result.exit_code == 2, (
        f"Expected exit 2, got {result.exit_code}. Output:\n{result.output}"
    )
    assert "intent_required_for_categories" in result.output, (
        f"Expected intent_required_for_categories in diff output: {result.output}"
    )
