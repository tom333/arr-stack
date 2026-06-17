import logging
from collections.abc import Callable
from typing import Any

from arrconf.client_base import (
    JellyfinClient,
    QbittorrentClient,
    RadarrClient,
    SeerrClient,
    SonarrClient,
)

from arr_dashboard.settings import Settings

log = logging.getLogger("arr_dashboard.sources")

EMPTY: dict[str, list[dict[str, Any]]] = {
    "radarr_movies": [],
    "sonarr_series": [],
    "radarr_queue": [],
    "sonarr_queue": [],
    "qbit_torrents": [],
    "seerr_requests": [],
    "jellyfin_items": [],
}


def _safe(
    name: str, fn: Callable[[], list[dict[str, Any]]], stale: list[str]
) -> list[dict[str, Any]] | None:
    try:
        return fn()
    except Exception as exc:  # graceful degradation: one source down != dashboard down
        log.warning("source %s failed: %s", name, exc)
        stale.append(name)
        return None


def fetch_all(settings: Settings) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    src: dict[str, list[dict[str, Any]]] = {k: [] for k in EMPTY}
    stale: list[str] = []

    if settings.radarr_api_key:
        radarr = RadarrClient(settings.radarr_url, settings.radarr_api_key)
        src["radarr_movies"] = _safe("radarr", lambda: radarr.get("/movie"), stale) or []
        src["radarr_queue"] = _safe("radarr_queue", radarr.list_queue, stale) or []
    if settings.sonarr_api_key:
        sonarr = SonarrClient(settings.sonarr_url, settings.sonarr_api_key)
        src["sonarr_series"] = _safe("sonarr", lambda: sonarr.get("/series"), stale) or []
        src["sonarr_queue"] = _safe("sonarr_queue", sonarr.list_queue, stale) or []
    if settings.qbt_user and settings.qbt_pass:
        src["qbit_torrents"] = (
            _safe(
                "qbittorrent",
                lambda: QbittorrentClient(
                    settings.qbittorrent_url, settings.qbt_user or "", settings.qbt_pass or ""
                ).list_torrents(),
                stale,
            )
            or []
        )
    if settings.seerr_api_key:
        seerr = SeerrClient(settings.seerr_url, settings.seerr_api_key)
        src["seerr_requests"] = _safe("seerr", seerr.list_requests, stale) or []
    if settings.jellyfin_api_key:
        jf = JellyfinClient(settings.jellyfin_url, settings.jellyfin_api_key)
        src["jellyfin_items"] = _safe("jellyfin", jf.list_items, stale) or []

    return src, stale
