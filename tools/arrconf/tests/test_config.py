"""Unit tests for arrconf.config.load_config — YAML error paths.

Covers PATTERNS.md File Classification row for ``tests/test_config.py``.
These tests target ``load_config()`` directly (no CLI runner) so failures
surface the loader behavior in isolation from typer wiring.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from arrconf.config import RootConfig, load_config
from arrconf.exceptions import ConfigError


def test_load_config_happy_path(tmp_path: Path) -> None:
    """Valid YAML returns a fully-validated RootConfig."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "apps:\n  sonarr:\n    main:\n      base_url: http://sonarr.test\n"
        "      download_clients:\n        prune: false\n        items: []\n"
    )
    result = load_config(cfg)
    assert isinstance(result, RootConfig)
    assert result.apps.sonarr is not None
    assert result.apps.sonarr.main is not None
    assert result.apps.sonarr.main.base_url == "http://sonarr.test"
    assert result.apps.sonarr.main.download_clients.prune is False
    assert result.apps.sonarr.main.download_clients.items == []


def test_load_config_validation_error_returns_exit_2(tmp_path: Path) -> None:
    """Schema-violating YAML raises ConfigError (mapped to CLI exit 2)."""
    cfg = tmp_path / "cfg.yml"
    # `bogus: 99` is not in DownloadClientsSection schema (extra="forbid")
    cfg.write_text(
        "apps:\n  sonarr:\n    main:\n      base_url: http://sonarr.test\n"
        "      download_clients:\n        prune: false\n        bogus: 99\n"
    )
    with pytest.raises(ConfigError, match=r"validation error"):
        load_config(cfg)


def test_load_config_yaml_syntax_error_returns_exit_2(tmp_path: Path) -> None:
    """Malformed YAML (not parseable by ruyaml) raises ConfigError."""
    cfg = tmp_path / "cfg.yml"
    # Unclosed flow sequence — ruyaml will fail to parse
    cfg.write_text("apps:\n  sonarr:\n    main:\n      base_url: [unclosed\n")
    with pytest.raises(ConfigError, match=r"parse error"):
        load_config(cfg)


def test_load_config_missing_file_returns_exit_2(tmp_path: Path) -> None:
    """Non-existent config path raises ConfigError (defensive coverage)."""
    with pytest.raises(ConfigError, match=r"not found"):
        load_config(tmp_path / "absent.yml")
