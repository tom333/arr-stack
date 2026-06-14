"""Lazy, cached factory building arrconf clients from McpSettings.

Single place that constructs clients. Mirrors arrconf.__main__ wiring:
SonarrClient(base_url=, api_key=) etc.; QbittorrentClient login-based
(base_url=, username=, password=).
"""

from functools import lru_cache

from arrconf.client_base import (
    JellyfinClient,
    ProwlarrClient,
    QbittorrentClient,
    RadarrClient,
    SeerrClient,
    SonarrClient,
)

from arrconf_mcp.settings import McpSettings


@lru_cache(maxsize=1)
def _settings() -> McpSettings:
    return McpSettings()


def reset() -> None:
    """Clear caches (tests)."""
    _settings.cache_clear()
    for fn in (sonarr, radarr, prowlarr, seerr, jellyfin, qbit):
        fn.cache_clear()


@lru_cache(maxsize=1)
def sonarr() -> SonarrClient:
    s = _settings()
    return SonarrClient(base_url=s.sonarr_url, api_key=s.sonarr_api_key.get_secret_value())


@lru_cache(maxsize=1)
def radarr() -> RadarrClient:
    s = _settings()
    return RadarrClient(base_url=s.radarr_url, api_key=s.radarr_api_key.get_secret_value())


@lru_cache(maxsize=1)
def prowlarr() -> ProwlarrClient:
    s = _settings()
    return ProwlarrClient(base_url=s.prowlarr_url, api_key=s.prowlarr_api_key.get_secret_value())


@lru_cache(maxsize=1)
def seerr() -> SeerrClient:
    s = _settings()
    return SeerrClient(base_url=s.seerr_url, api_key=s.seerr_api_key.get_secret_value())


@lru_cache(maxsize=1)
def jellyfin() -> JellyfinClient:
    s = _settings()
    return JellyfinClient(base_url=s.jellyfin_url, api_key=s.jellyfin_api_key.get_secret_value())


@lru_cache(maxsize=1)
def qbit() -> QbittorrentClient:
    s = _settings()
    return QbittorrentClient(
        base_url=s.qbt_url,
        username=s.qbt_user,
        password=s.qbt_pass.get_secret_value(),
    )
