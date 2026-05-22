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
from arrconf.resources.jellyfin import JellyfinUserPolicy


def test_load_config_happy_path_sonarr_only(tmp_path: Path) -> None:
    """Valid YAML with only sonarr.main returns a fully-validated RootConfig."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    download_clients:\n      prune: false\n"
    )
    result = load_config(cfg)
    assert isinstance(result, RootConfig)
    assert "main" in result.sonarr
    assert result.sonarr["main"].base_url == "http://sonarr.test"
    assert result.sonarr["main"].download_clients.prune is False
    # Phase 3 sections still present with opt-in disabled:
    assert result.sonarr["main"].indexers.items == []
    assert result.sonarr["main"].notifications.items == []
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


def test_load_config_qbittorrent_categories_default_prune_false(tmp_path: Path) -> None:
    """Phase 5: categories section prune defaults to False when not specified."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("qbittorrent:\n  main:\n    base_url: http://qbit:8080\n")
    result = load_config(cfg)
    instance = result.qbittorrent["main"]
    assert instance.categories.prune is False


def test_load_config_qbittorrent_prune_defaults_to_false(tmp_path: Path) -> None:
    """Phase 5 R-04 mitigation: categories.prune is False by default (never auto-delete)."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "qbittorrent:\n  main:\n    base_url: http://qbit:8080\n    categories:\n      prune: false\n"
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


def test_load_config_sonarr_tags_section_rejects_items(tmp_path: Path) -> None:
    """D-13: sonarr.main.tags.items: [] in YAML raises ConfigError (extra=forbid, Phase 12)."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    tags:\n"
        "      items:\n"
        "        - label: tv\n"
        "        - label: anime\n"
        "        - label: family\n"
    )
    with pytest.raises(ConfigError, match=r"validation error"):
        load_config(cfg)


def test_load_config_sonarr_tags_section_prune_only(tmp_path: Path) -> None:
    """Phase 12 D-01: sonarr.main.tags accepts only prune flag (items removed)."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    tags:\n"
        "      prune: false\n"
    )
    result = load_config(cfg)
    instance = result.sonarr["main"]
    assert instance.tags.prune is False


def test_load_config_sonarr_remote_path_mappings_section_rejects_items(tmp_path: Path) -> None:
    """D-13: sonarr.main.remote_path_mappings.items: [...] raises ConfigError (Phase 12)."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    remote_path_mappings:\n"
        "      items:\n"
        "        - host: qbittorrent.selfhost.svc.cluster.local\n"
        "          remotePath: /data/series/\n"
        "          localPath: /data/torrents/series/\n"
    )
    with pytest.raises(ConfigError, match=r"validation error"):
        load_config(cfg)


def test_load_config_sonarr_remote_path_mappings_section_prune_only(tmp_path: Path) -> None:
    """Phase 12 D-01: remote_path_mappings accepts only prune flag (items removed)."""
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        "sonarr:\n  main:\n    base_url: http://sonarr.test\n"
        "    remote_path_mappings:\n"
        "      prune: true\n"
    )
    result = load_config(cfg)
    instance = result.sonarr["main"]
    assert instance.remote_path_mappings.prune is True


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


# -- Phase 6 (D-06-SCOPE-01 + D-06-RETAG-01) -----------------------------------


def test_root_config_accepts_seerr_block(tmp_path: Path) -> None:
    """RootConfig validates the full Phase-6 seerr schema (D-06-SCOPE-01)."""
    yaml_src = """
seerr:
  main:
    base_url: http://seerr.selfhost.svc.cluster.local:5055
    sonarr_service:
      hostname: sonarr.selfhost.svc.cluster.local
      port: 8989
      activeProfileId: 6
      activeDirectory: /media/series
      activeAnimeProfileId: 7
      activeAnimeDirectory: /media/anime
      animeTags: [3]
      tags: [2]
      tagRequests: true
    radarr_service:
      hostname: radarr.selfhost.svc.cluster.local
      port: 7878
      activeProfileId: 6
      activeDirectory: /media/films
      tags: [2]
      tagRequests: true
    users:
      enable: true
      admin:
        displayName: admin
        permissions: 2
        movieQuotaDays: 0
        movieQuotaLimit: 0
        tvQuotaDays: 0
        tvQuotaLimit: 0
    main_settings:
      enable: true
      defaultPermissions: 32
      defaultQuotas:
        movie: {quotaDays: 7, quotaLimit: 5}
        tv: {quotaDays: 7, quotaLimit: 5}
"""
    cfg_file = tmp_path / "arrconf.yml"
    cfg_file.write_text(yaml_src)
    cfg = load_config(cfg_file)
    assert "main" in cfg.seerr
    assert cfg.seerr["main"].sonarr_service.animeTags == [3]
    assert cfg.seerr["main"].users.admin.permissions == 2  # ADMIN — research correction
    assert cfg.seerr["main"].main_settings.defaultPermissions == 32  # REQUEST


def test_seerr_models_exclude_id_from_dump() -> None:
    """All 4 Seerr resource models MUST exclude `id` from model_dump (Pitfall 1).

    Seerr returns HTTP 400 "request.body.id is read-only" if id is in PUT body.
    """
    from arrconf.resources.seerr import (
        SeerrMainSettings,
        SeerrRadarrService,
        SeerrSonarrService,
        SeerrUser,
    )

    s = SeerrSonarrService(
        id=0, hostname="h", port=1, apiKey="k", activeProfileId=1, activeDirectory="/a"
    )
    assert "id" not in s.model_dump(), "SeerrSonarrService leaked id"
    assert "apiKey" not in s.model_dump(), "SeerrSonarrService leaked apiKey"
    assert "activeProfileName" not in s.model_dump(), "SeerrSonarrService leaked activeProfileName"
    assert "activeAnimeProfileName" not in s.model_dump(), (
        "SeerrSonarrService leaked activeAnimeProfileName"
    )

    r = SeerrRadarrService(
        id=0, hostname="h", port=1, apiKey="k", activeProfileId=1, activeDirectory="/a"
    )
    assert "id" not in r.model_dump()
    assert "apiKey" not in r.model_dump()

    u = SeerrUser(id=1, email="x@y", displayName="d", permissions=2)
    assert "id" not in u.model_dump()
    assert "email" not in u.model_dump()
    assert "userType" not in u.model_dump()  # 16 read-only exclusions

    m = SeerrMainSettings(apiKey="secret", defaultPermissions=32)
    assert "apiKey" not in m.model_dump()


def test_content_routing_section_defaults_disabled() -> None:
    """content_routing is opt-in: enable=False default on Sonarr and Radarr instances."""
    from arrconf.config import RadarrInstance, SonarrInstance

    assert SonarrInstance(base_url="http://x").content_routing.enable is False
    assert RadarrInstance(base_url="http://x").content_routing.enable is False


def test_root_config_rejects_seerr_typo(tmp_path: Path) -> None:
    """`extra='forbid'` on SeerrInstance catches YAML typos (sonar_service vs sonarr_service)."""
    yaml_src = """
seerr:
  main:
    base_url: http://seerr:5055
    sonar_service:  # TYPO
      hostname: sonarr
      port: 8989
      activeProfileId: 6
      activeDirectory: /media/series
    radarr_service:
      hostname: radarr
      port: 7878
      activeProfileId: 6
      activeDirectory: /media/films
"""
    cfg_file = tmp_path / "arrconf.yml"
    cfg_file.write_text(yaml_src)
    with pytest.raises(ConfigError):
        load_config(cfg_file)


# -- Phase 7 (D-07-INSTANCE-01, D-07-LIB-01, D-07-USERS-01, D-07-CONFIG-01, D-07-PLUGINS-01) --


def test_root_config_accepts_jellyfin_block(tmp_path: Path) -> None:
    """RootConfig validates the full Phase-7 jellyfin schema (D-07-INSTANCE-01).

    Mirrors test_root_config_accepts_seerr_block — covers the 4 Section models
    (libraries / users / server_config / plugins) + JellyfinInstance + RootConfig.jellyfin field.
    """
    yaml_src = """
jellyfin:
  main:
    base_url: http://jellyfin.selfhost.svc.cluster.local:8096
    libraries:
      enable: true
      prune: false
    users:
      enable: true
      prune: false
      admin:
        IsAdministrator: true
        EnableContentDeletion: true
        EnableRemoteAccess: true
    server_config:
      enable: true
      ui_culture: "fr"
      metadata_country_code: "FR"
      preferred_metadata_language: "fr"
      activity_log_retention_days: 30
      log_file_retention_days: 3
      server_name: "jellyfin"
      plugin_repositories:
        - Name: "Jellyfin Stable"
          Url: "https://repo.jellyfin.org/files/plugin/manifest.json"
          Enabled: true
    plugins:
      enable: true
      required:
        - name: "TMDb"
        - name: "OMDb"
        - name: "MusicBrainz"
        - name: "AudioDb"
        - name: "Studio Images"
        - name: "Kodi Sync Queue"
"""
    cfg_file = tmp_path / "arrconf.yml"
    cfg_file.write_text(yaml_src)
    cfg = load_config(cfg_file)

    assert "main" in cfg.jellyfin
    instance = cfg.jellyfin["main"]
    assert instance.base_url == "http://jellyfin.selfhost.svc.cluster.local:8096"

    # Libraries (D-07-LIB-01: Phase 12 — items derived from categories generator)
    assert instance.libraries.enable is True
    assert instance.libraries.prune is False

    # Users (D-07-USERS-01: admin only)
    assert instance.users.admin.IsAdministrator is True
    assert instance.users.admin.EnableContentDeletion is True
    assert instance.users.prune is False  # D-07-USERS-01 hardcoded protection

    # Server config (D-07-CONFIG-01: 7-field allowlist)
    sc = instance.server_config
    assert sc.ui_culture == "fr"
    assert sc.metadata_country_code == "FR"
    assert sc.preferred_metadata_language == "fr"
    assert sc.activity_log_retention_days == 30
    assert sc.log_file_retention_days == 3
    assert sc.server_name == "jellyfin"
    assert len(sc.plugin_repositories) == 1
    assert sc.plugin_repositories[0].Url == "https://repo.jellyfin.org/files/plugin/manifest.json"

    # Plugins (D-07-PLUGINS-01: activation-only allowlist of 6)
    assert len(instance.plugins.required) == 6
    plugin_names = [p.name for p in instance.plugins.required]
    assert "TMDb" in plugin_names
    assert "Kodi Sync Queue" in plugin_names


def test_jellyfin_user_policy_excludes_required_providerids_from_dump() -> None:
    """Pitfall 6 (D-06-OPENAPI-01 carry-forward) type-layer enforcement.

    AuthenticationProviderId + PasswordResetProviderId are OpenAPI-required
    but NEVER configured by operator in YAML. Field(exclude=True) guarantees
    they cannot leak from operator YAML into the POST body. The reconciler
    (Plan 07-04) re-injects them from cluster GET — same pattern as Seerr apiKey
    (D-06-CREDS-01).
    """
    policy = JellyfinUserPolicy(
        AuthenticationProviderId="Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider",
        PasswordResetProviderId="Jellyfin.Server.Implementations.Users.DefaultPasswordResetProvider",
        IsAdministrator=True,
        EnableContentDeletion=True,
    )
    result = policy.model_dump()

    assert "AuthenticationProviderId" not in result, (
        "Pitfall 6: AuthenticationProviderId leaked from YAML — exclude=True failed"
    )
    assert "PasswordResetProviderId" not in result, (
        "Pitfall 6: PasswordResetProviderId leaked from YAML — exclude=True failed"
    )
    # Writable fields ARE in dump
    assert result["IsAdministrator"] is True
    assert result["EnableContentDeletion"] is True
