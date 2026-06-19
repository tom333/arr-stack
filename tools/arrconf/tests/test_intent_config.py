"""Unit tests for arrconf.intent_config (Phase 28 INTENT-01). No HTTP — pure validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from arrconf.exceptions import ConfigError
from arrconf.intent_config import (
    CrossSeedConfig,
    IntentConfig,
    SagaEntry,
    ToolsConfig,
    load_intent,
)


def test_load_intent_valid_yaml_returns_cross_seed(tmp_path: Path) -> None:
    """load_intent on a valid intent.yml returns IntentConfig with cross_seed populated."""
    intent_yml = tmp_path / "intent.yml"
    intent_yml.write_text(
        "tools:\n"
        "  cross_seed:\n"
        "    torznab:\n"
        "      - http://prowlarr/1/api?apikey=ABC\n"
        "    torrent_clients:\n"
        "      - qbittorrent:http://user:pass@localhost:8080\n"
        "    link_dirs:\n"
        "      - /data/cross-seed\n"
        "    link_type: hardlink\n"
        "    action: inject\n",
        encoding="utf-8",
    )
    cfg = load_intent(intent_yml)
    assert cfg.tools.cross_seed is not None
    assert cfg.tools.cross_seed.torznab == ["http://prowlarr/1/api?apikey=ABC"]
    assert cfg.tools.cross_seed.torrent_clients == ["qbittorrent:http://user:pass@localhost:8080"]
    assert cfg.tools.cross_seed.link_dirs == ["/data/cross-seed"]
    assert cfg.tools.cross_seed.link_type == "hardlink"
    assert cfg.tools.cross_seed.action == "inject"


def test_load_intent_missing_path_raises_config_error(tmp_path: Path) -> None:
    """load_intent on a missing path raises ConfigError."""
    missing = tmp_path / "nonexistent.yml"
    with pytest.raises(ConfigError, match="Intent file not found"):
        load_intent(missing)


def test_load_intent_unknown_top_level_key_raises_config_error(tmp_path: Path) -> None:
    """load_intent on YAML with an unknown top-level key raises ConfigError (extra=forbid)."""
    intent_yml = tmp_path / "intent.yml"
    intent_yml.write_text("unknown_key: value\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Intent validation error"):
        load_intent(intent_yml)


def test_cross_seed_config_defaults() -> None:
    """CrossSeedConfig() defaults are hardlink / inject / empty lists."""
    cfg = CrossSeedConfig()
    assert cfg.link_type == "hardlink"
    assert cfg.action == "inject"
    assert cfg.torznab == []
    assert cfg.torrent_clients == []
    assert cfg.link_dirs == []


def test_saga_entry_rejects_extra_keys() -> None:
    """SagaEntry locked in Phase 29 to extra='forbid' — unknown keys are rejected."""
    # A valid movies saga validates.
    entry = SagaEntry.model_validate(
        {
            "name": "James Bond",
            "kind": "movies",
            "tmdb_collection": 645,
            "profile": "MULTi.VF",
            "root": "/media/films",
        }
    )
    assert entry.name == "James Bond"

    with pytest.raises(ValidationError):
        # extra=forbid — unknown keys must fail (was tolerated in the P28 stub).
        SagaEntry.model_validate({"name": "x", "kind": "series", "extra_field": "any-value"})

    with pytest.raises(ValidationError):
        # name is required — missing it must fail.
        SagaEntry.model_validate({"kind": "series"})


def test_empty_intent_returns_default_tools_and_empty_sagas(tmp_path: Path) -> None:
    """Empty intent ({}) returns tools=ToolsConfig(cross_seed=None), sagas==[]."""
    intent_yml = tmp_path / "intent.yml"
    intent_yml.write_text("{}\n", encoding="utf-8")
    cfg = load_intent(intent_yml)
    assert cfg.tools == ToolsConfig()
    assert cfg.tools.cross_seed is None
    assert cfg.sagas == []


def test_intent_config_empty_default_values() -> None:
    """IntentConfig() with no args has tools=ToolsConfig() and sagas=[]."""
    cfg = IntentConfig()
    assert cfg.tools.cross_seed is None
    assert cfg.sagas == []


def test_category_quality_profiles_defaults():
    from arrconf.intent_config import IntentConfig

    cfg = IntentConfig()
    assert cfg.category_quality_profiles == {
        "general": "MULTi.VF",
        "anime": "Anime",
        "family": "Family",
    }


def test_category_quality_profiles_override():
    from arrconf.intent_config import IntentConfig

    cfg = IntentConfig.model_validate(
        {"category_quality_profiles": {"general": "Custom", "anime": "Anime", "family": "Family"}}
    )
    assert cfg.category_quality_profiles["general"] == "Custom"


def test_unmonitor_imported_defaults_false_and_parses():
    from arrconf.intent_config import IntentConfig

    assert IntentConfig().unmonitor_imported is False
    assert IntentConfig(unmonitor_imported=True).unmonitor_imported is True
