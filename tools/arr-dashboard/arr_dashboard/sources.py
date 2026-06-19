import logging
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

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


def build_clients(settings: Settings) -> dict[str, object]:
    clients: dict[str, object] = {}
    if settings.radarr_api_key:
        clients["radarr"] = RadarrClient(settings.radarr_url, settings.radarr_api_key)
    if settings.sonarr_api_key:
        clients["sonarr"] = SonarrClient(settings.sonarr_url, settings.sonarr_api_key)
    return clients


def build_qbit(settings: Settings) -> QbittorrentClient | None:
    """Build a logged-in qBit client, or None when creds are absent."""
    if settings.qbt_user and settings.qbt_pass:
        return QbittorrentClient(settings.qbittorrent_url, settings.qbt_user, settings.qbt_pass)
    return None


def build_jellyfin(settings: Settings) -> JellyfinClient | None:
    """Build a Jellyfin client, or None when the API key is absent."""
    if settings.jellyfin_api_key:
        return JellyfinClient(settings.jellyfin_url, settings.jellyfin_api_key)
    return None


def _worst_tracker(trackers: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the most informative real tracker entry. A not-working entry (status 4)
    with a message wins (e.g. C411 'Forbidden'); else the first real entry. Pseudo-rows
    (** [DHT] **, ** [PeX] **, ** [LSD] **) are ignored. Returns {status, msg, host}."""
    real = [t for t in trackers if not str(t.get("url", "")).startswith("**")]
    if not real:
        return None
    refused = [t for t in real if t.get("status") == 4 and (t.get("msg") or "")]
    chosen = refused[0] if refused else real[0]
    return {
        "status": chosen.get("status"),
        "msg": (chosen.get("msg") or None),
        "host": urlsplit(str(chosen.get("url", ""))).hostname,
    }


def _fetch_qbit_torrents(settings: Settings) -> list[dict[str, Any]]:
    """List torrents, then probe trackers for STALLED ones (dlspeed==0 & progress<1)
    and attach the worst tracker entry as t['_tracker']. One qBit login reused."""
    qb = QbittorrentClient(
        settings.qbittorrent_url, settings.qbt_user or "", settings.qbt_pass or ""
    )
    torrents: list[dict[str, Any]] = qb.list_torrents()
    for t in torrents:
        if t.get("dlspeed", 0) == 0 and float(t.get("progress", 0.0)) < 1.0:
            try:
                trackers = qb.get(f"/torrents/trackers?hash={t['hash']}")
            except Exception:  # tracker probe must never break the refresh
                continue
            worst = _worst_tracker(trackers or [])
            if worst:
                t["_tracker"] = worst
    return torrents


def fetch_all(settings: Settings) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    src: dict[str, list[dict[str, Any]]] = {k: [] for k in EMPTY}
    stale: list[str] = []
    clients = build_clients(settings)

    radarr = clients.get("radarr")
    if isinstance(radarr, RadarrClient):
        src["radarr_movies"] = _safe("radarr", lambda: radarr.get("/movie"), stale) or []
        src["radarr_queue"] = _safe("radarr_queue", radarr.list_queue, stale) or []
    sonarr = clients.get("sonarr")
    if isinstance(sonarr, SonarrClient):
        src["sonarr_series"] = _safe("sonarr", lambda: sonarr.get("/series"), stale) or []
        src["sonarr_queue"] = _safe("sonarr_queue", sonarr.list_queue, stale) or []
    if settings.qbt_user and settings.qbt_pass:
        src["qbit_torrents"] = (
            _safe("qbittorrent", lambda: _fetch_qbit_torrents(settings), stale) or []
        )
    if settings.seerr_api_key:
        seerr = SeerrClient(settings.seerr_url, settings.seerr_api_key)
        src["seerr_requests"] = _safe("seerr", seerr.list_requests, stale) or []
    if settings.jellyfin_api_key:
        jf = JellyfinClient(settings.jellyfin_url, settings.jellyfin_api_key)
        src["jellyfin_items"] = _safe("jellyfin", jf.list_items, stale) or []

    return src, stale
