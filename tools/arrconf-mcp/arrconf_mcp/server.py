"""FastMCP server exposing read + safe-action tools over the arrconf clients."""

from pathlib import Path
from typing import Any

import structlog
from arrconf.exceptions import ConfigError
from arrconf.intent_config import IntentConfig, load_intent
from mcp.server.fastmcp import FastMCP

from arrconf_mcp import clients, formatting

log = structlog.get_logger()
mcp = FastMCP("arrconf-mcp")

# Candidate locations for the hand-edited intent.yml (chart source of truth).
_INTENT_PATHS = (
    Path("charts/arr-stack/files/intent.yml"),
    Path("/etc/arrconf/intent.yml"),
)


def _category_quality_profiles() -> dict[str, str]:
    """category->profile NAME mapping, reusing arrconf's IntentConfig.

    Reads ``category_quality_profiles`` from the chart intent.yml when present,
    else falls back to the IntentConfig pydantic default ({general:MULTi.VF, ...}).
    The source is logged so the resolution is never silent.
    """
    for path in _INTENT_PATHS:
        if path.exists():
            try:
                mapping = load_intent(path).category_quality_profiles
                log.info("profile_mapping_source", source=str(path))
                return mapping
            except ConfigError as e:
                log.warning("profile_mapping_intent_load_failed", path=str(path), error=str(e))
    mapping = IntentConfig().category_quality_profiles
    log.info("profile_mapping_source", source="IntentConfig default (no intent.yml found)")
    return mapping


def _resolve_profile_id(profiles: list[dict[str, Any]], name: str) -> int:
    """Return the quality-profile id whose name matches ``name`` (case-insensitive)."""
    for p in profiles:
        if str(p.get("name", "")).lower() == name.lower():
            return int(p["id"])
    raise ValueError(
        f"quality profile {name!r} not found among {[p.get('name') for p in profiles]}"
    )


def _resolve_root_folder(folders: list[dict[str, Any]], category: str) -> str:
    """Pick the root folder whose path contains ``category``, else the first one."""
    for f in folders:
        if category in str(f.get("path", "")):
            return str(f["path"])
    return str(folders[0]["path"])


@mcp.tool()
def stalled_torrents() -> list[dict[str, Any]]:
    """List qBittorrent torrents that are stuck (stalled/metadata/error), with seeders + tracker."""
    info = clients.qbit().get("/torrents/info")
    return [formatting.torrent_brief(t) for t in info if formatting.is_stalled(t)]


@mcp.tool()
def queue_status() -> list[dict[str, Any]]:
    """List active download-queue items across Sonarr and Radarr (title, status, size left, error)."""
    items: list[dict[str, Any]] = []
    for app, client in (("sonarr", clients.sonarr()), ("radarr", clients.radarr())):
        records = client.get("/queue").get("records", [])
        items.extend(formatting.queue_item_brief(r, app) for r in records)
    return items


@mcp.tool()
def library_overview() -> dict[str, Any]:
    """Library size summary: Sonarr series count, Radarr movie count, and free disk per root."""
    series_count = len(clients.sonarr().get("/series"))
    radarr = clients.radarr()
    movie_count = len(radarr.get("/movie"))
    disks = [formatting.disk_brief(d) for d in radarr.get("/diskspace")]
    return {"series_count": series_count, "movie_count": movie_count, "disks": disks}


@mcp.tool()
def transfer_info() -> dict[str, Any]:
    """Global qBittorrent transfer state: download/upload speed, DHT nodes, connection status."""
    return formatting.transfer_brief(clients.qbit().get("/transfer/info"))


@mcp.tool()
def cross_seed_status() -> dict[str, Any]:
    """Re-seed progress: count + brief of torrents in the cross-seed-link qBittorrent category."""
    info = clients.qbit().get("/torrents/info", params={"category": "cross-seed-link"})
    return {"count": len(info), "torrents": [formatting.torrent_brief(t) for t in info]}


@mcp.tool()
def search_media(query: str, kind: str) -> list[dict[str, Any]]:
    """Search Radarr (kind="movie") or Sonarr (kind="series") for a title; top 5 matches."""
    if kind == "movie":
        results = clients.radarr().get("/movie/lookup", params={"term": query})
        id_field = "tmdbId"
    elif kind == "series":
        results = clients.sonarr().get("/series/lookup", params={"term": query})
        id_field = "tvdbId"
    else:
        raise ValueError(f"kind must be 'movie' or 'series', got {kind!r}")
    return [formatting.lookup_result_brief(r, id_field) for r in results[:5]]


@mcp.tool()
def add_movie(tmdb_id: int, category: str) -> dict[str, Any]:
    """Add a movie to Radarr by TMDB id, profiling + filing it by category, and search for it."""
    radarr = clients.radarr()
    profile_name = _category_quality_profiles().get(category, category)
    profile_id = _resolve_profile_id(radarr.get("/qualityprofile"), profile_name)
    root_folder = _resolve_root_folder(radarr.get("/rootfolder"), category)
    lookup = radarr.get("/movie/lookup", params={"tmdbId": tmdb_id})
    movie = lookup[0] if isinstance(lookup, list) else lookup
    payload = {
        **movie,
        "qualityProfileId": profile_id,
        "rootFolderPath": root_folder,
        "tmdbId": tmdb_id,
        "monitored": True,
        "addOptions": {"searchForMovie": True},
    }
    created = radarr.post("/movie", json=payload)
    return {"title": created.get("title"), "id": created.get("id")}


@mcp.tool()
def add_series(tvdb_id: int, category: str) -> dict[str, Any]:
    """Add a series to Sonarr by TVDB id, profiling + filing it by category, and search missing."""
    sonarr = clients.sonarr()
    profile_name = _category_quality_profiles().get(category, category)
    profile_id = _resolve_profile_id(sonarr.get("/qualityprofile"), profile_name)
    root_folder = _resolve_root_folder(sonarr.get("/rootfolder"), category)
    lookup = sonarr.get("/series/lookup", params={"term": f"tvdb:{tvdb_id}"})
    series = lookup[0] if isinstance(lookup, list) else lookup
    payload = {
        **series,
        "qualityProfileId": profile_id,
        "rootFolderPath": root_folder,
        "tvdbId": tvdb_id,
        "monitored": True,
        "addOptions": {"searchForMissingEpisodes": True},
    }
    created = sonarr.post("/series", json=payload)
    return {"title": created.get("title"), "id": created.get("id")}


@mcp.tool()
def request_media(tmdb_id: int, kind: str) -> dict[str, Any]:
    """Request a movie/series via Jellyseerr (POST /request). Strips Seerr's read-only echoed id."""
    if kind not in ("movie", "series"):
        raise ValueError(f"kind must be 'movie' or 'series', got {kind!r}")
    body = {"mediaType": kind, "mediaId": tmdb_id}
    created = clients.seerr().post("/request", json=body)
    if isinstance(created, dict):
        created.pop("id", None)  # Seerr quirk: id is read-only, strip from echoed body
    return created


@mcp.tool()
def trigger_search_missing(app: str) -> dict[str, Any]:
    """Trigger a missing-content search on Sonarr or Radarr (POST /command)."""
    if app == "sonarr":
        command, client = "MissingEpisodeSearch", clients.sonarr()
    elif app == "radarr":
        command, client = "MissingMoviesSearch", clients.radarr()
    else:
        raise ValueError(f"app must be 'sonarr' or 'radarr', got {app!r}")
    client.post("/command", json={"name": command})
    return {"triggered": command}
