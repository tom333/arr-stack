"""Unit tests for arrconf.config.load_config — YAML error paths + Phase 3 shape.

Covers PATTERNS.md File Classification row for ``tests/test_config.py``.
These tests target ``load_config()`` directly (no CLI runner) so failures
surface the loader behavior in isolation from typer wiring.

Phase 3 (D-03-05): RootConfig has flat ``sonarr`` / ``radarr`` / ``prowlarr``
dicts at the root level — no ``apps:`` indirection. AppEntry encodes the
Prowlarr app-sync YAML model (D-03-03).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from arrconf.config import RootConfig, load_config
from arrconf.exceptions import ConfigError


def test_load_config_happy_path_sonarr_only(tmp_path: Path) -> None:
    """Valid YAML with only sonarr.main returns a fully-validated RootConfig."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      items: []\n"
    )
    result = load_config(cfg)
    assert isinstance(result, RootConfig)
    assert "main" in result.sonarr
    assert result.sonarr["main"].base_url == "http://sonarr.test"
    assert result.sonarr["main"].download_clients.prune is False
    assert result.sonarr["main"].download_clients.items == []
    # Phase 3 sections default to empty / opt-in disabled:
    assert result.sonarr["main"].indexers.items == []
    assert result.sonarr["main"].notifications.items == []
    assert result.sonarr["main"].root_folders.items == []
    assert result.sonarr["main"].host_config.enable is False  # D-03-04 opt-in default
    # New top-level dicts default to empty:
    assert result.radarr == {}
    assert result.prowlarr == {}


def test_load_config_happy_path_all_three_apps(tmp_path: Path) -> None:
    """Phase 3 / D-03-05: RootConfig accepts sonarr + radarr + prowlarr blocks."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "radarr:\n  main:\n    base_url: http://radarr.test\n"
        "prowlarr:\n  main:\n    base_url: http://prowlarr.test\n"
        "    apps:\n      items:\n"
        "        - name: sonarr-main\n"
        "          type: sonarr\n"
        "          base_url: http://sonarr.test\n"
        "          api_key_env: SONARR_API_KEY\n"
        "          sync_level: fullSync\n"
    )
    result = load_config(cfg)
    assert "main" in result.sonarr
    assert "main" in result.radarr
    assert "main" in result.prowlarr
    assert result.radarr["main"].base_url == "http://radarr.test"
    assert len(result.prowlarr["main"].apps.items) == 1
    app = result.prowlarr["main"].apps.items[0]
    assert app.name == "sonarr-main"
    assert app.type == "sonarr"
    assert app.api_key_env == "SONARR_API_KEY"
    assert app.sync_level == "fullSync"


def test_load_config_validation_error_returns_exit_2(tmp_path: Path) -> None:
    """Schema-violating YAML raises ConfigError (mapped to CLI exit 2)."""
    cfg = tmp_path / "cfg.yml"
    # `bogus: 99` is not in DownloadClientsSection schema (extra="forbid")
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n      bogus: 99\n"
    )
    with pytest.raises(ConfigError, match=r"validation error"):
        load_config(cfg)


def test_load_config_yaml_syntax_error_returns_exit_2(tmp_path: Path) -> None:
    """Malformed YAML (not parseable by ruyaml) raises ConfigError."""
    cfg = tmp_path / "cfg.yml"
    # Unclosed flow sequence — ruyaml will fail to parse
    cfg.write_text("sonarr:\n  main:\n    base_url: [unclosed\n")
    with pytest.raises(ConfigError, match=r"parse error"):
        load_config(cfg)


def test_load_config_missing_file_returns_exit_2(tmp_path: Path) -> None:
    """Non-existent config path raises ConfigError (defensive coverage)."""
    with pytest.raises(ConfigError, match=r"not found"):
        load_config(tmp_path / "absent.yml")


def test_app_entry_rejects_invalid_type(tmp_path: Path) -> None:
    """D-03-03: AppEntry.type is Literal['sonarr','radarr'] — others rejected."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "prowlarr:\n  main:\n    base_url: http://prowlarr.test\n"
        "    apps:\n      items:\n"
        "        - name: jellyfin-main\n"
        "          type: jellyfin\n"
        "          base_url: http://jellyfin.test\n"
        "          api_key_env: JELLYFIN_API_KEY\n"
    )
    with pytest.raises(ConfigError, match=r"validation error"):
        load_config(cfg)


def test_app_entry_rejects_invalid_sync_level(tmp_path: Path) -> None:
    """D-03-03: AppEntry.sync_level is Literal — invalid values rejected."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "prowlarr:\n  main:\n    base_url: http://prowlarr.test\n"
        "    apps:\n      items:\n"
        "        - name: sonarr-main\n"
        "          type: sonarr\n"
        "          base_url: http://sonarr.test\n"
        "          api_key_env: SONARR_API_KEY\n"
        "          sync_level: maybeSync\n"
    )
    with pytest.raises(ConfigError, match=r"validation error"):
        load_config(cfg)


# ---------------------------------------------------------------------------
# Phase 5 (D-05): qBittorrent schema + Sonarr/Radarr extensions
# ---------------------------------------------------------------------------


def test_load_config_with_qbittorrent_main_section(tmp_path: Path) -> None:
    """Phase 5 D-05-QBT-02: qbittorrent.main block parses to QbittorrentInstance."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("qbittorrent:\n  main:\n    base_url: http://qbit:8080\n")
    result = load_config(cfg)
    assert "main" in result.qbittorrent
    assert result.qbittorrent["main"].base_url == "http://qbit:8080"


def test_load_config_qbittorrent_categories_default_empty(tmp_path: Path) -> None:
    """Phase 5: categories defaults to empty list and prune=False when not specified."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("qbittorrent:\n  main:\n    base_url: http://qbit:8080\n")
    result = load_config(cfg)
    instance = result.qbittorrent["main"]
    assert instance.categories.items == []
    assert instance.categories.prune is False


def test_load_config_qbittorrent_prune_defaults_to_false(tmp_path: Path) -> None:
    """Phase 5 R-04 mitigation: categories.prune is False by default (never auto-delete)."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "qbittorrent:\n  main:\n    base_url: http://qbit:8080\n    categories:\n      items: []\n"
    )
    result = load_config(cfg)
    assert result.qbittorrent["main"].categories.prune is False


def test_load_config_qbittorrent_preferences_extra_forbid_rejects_unknown_key(
    tmp_path: Path,
) -> None:
    """Phase 5 T-05-CONTENT: extra=forbid on QbitPreferences rejects unknown keys."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "qbittorrent:\n  main:\n    base_url: http://qbit:8080\n"
        "    preferences:\n      values:\n        max_active_downloads: 5\n"
    )
    with pytest.raises(ConfigError) as exc_info:
        load_config(cfg)
    assert "max_active_downloads" in str(exc_info.value)


def test_load_config_qbittorrent_preferences_enable_defaults_to_false(tmp_path: Path) -> None:
    """Phase 5 D-03-04 mirror: preferences.enable is False by default (opt-in)."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("qbittorrent:\n  main:\n    base_url: http://qbit:8080\n")
    result = load_config(cfg)
    assert result.qbittorrent["main"].preferences.enable is False


def test_load_config_sonarr_tags_section(tmp_path: Path) -> None:
    """Phase 5 D-05-SPLIT-01: sonarr.main.tags.items accepts list of TagItem entries."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    tags:\n"
        "      items:\n"
        "        - label: tv\n"
        "        - label: anime\n"
        "        - label: family\n"
    )
    result = load_config(cfg)
    instance = result.sonarr["main"]
    assert len(instance.tags.items) == 3
    labels = {item.label for item in instance.tags.items}
    assert labels == {"tv", "anime", "family"}


def test_load_config_sonarr_remote_path_mappings_section(tmp_path: Path) -> None:
    """Phase 5 D-05-PATHMAP-01: sonarr.main.remote_path_mappings parses correctly."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    remote_path_mappings:\n"
        "      items:\n"
        "        - host: qbittorrent.selfhost.svc.cluster.local\n"
        "          remotePath: /data/series/\n"
        "          localPath: /data/torrents/series/\n"
        "        - host: qbittorrent.selfhost.svc.cluster.local\n"
        "          remotePath: /data/anime/\n"
        "          localPath: /data/torrents/anime/\n"
        "        - host: qbittorrent.selfhost.svc.cluster.local\n"
        "          remotePath: /data/family/\n"
        "          localPath: /data/torrents/family/\n"
        "        - host: qbittorrent.selfhost.svc.cluster.local\n"
        "          remotePath: /data/complete/\n"
        "          localPath: /data/torrents/complete/\n"
    )
    result = load_config(cfg)
    instance = result.sonarr["main"]
    assert len(instance.remote_path_mappings.items) == 4
    first = instance.remote_path_mappings.items[0]
    assert first.host == "qbittorrent.selfhost.svc.cluster.local"
    assert first.remotePath == "/data/series/"
    assert first.localPath == "/data/torrents/series/"


def test_load_config_sonarr_series_tags_defaults(tmp_path: Path) -> None:
    """Phase 5 D-05-MIG-01: series_tags.enable=True and default_tag='tv' when not specified."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("sonarr:\n  main:\n    base_url: http://sonarr.test\n")
    result = load_config(cfg)
    instance = result.sonarr["main"]
    assert instance.series_tags.enable is True
    assert instance.series_tags.default_tag == "tv"


def test_load_config_radarr_movie_tags_defaults(tmp_path: Path) -> None:
    """Phase 5 D-05-SPLIT-02: movie_tags.enable=True and default_tag='movies' when not specified."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("radarr:\n  main:\n    base_url: http://radarr.test\n")
    result = load_config(cfg)
    instance = result.radarr["main"]
    assert instance.movie_tags.enable is True
    assert instance.movie_tags.default_tag == "movies"


def test_load_config_rejects_unknown_top_level_key(tmp_path: Path) -> None:
    """Phase 5: RootConfig still uses extra='forbid' — unknown top-level keys rejected."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("seerr:\n  main:\n    base_url: http://seerr.test\n")
    with pytest.raises(ConfigError, match=r"validation error"):
        load_config(cfg)
