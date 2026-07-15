"""Add a TV release's series into Sonarr.

Bridge: mirrors release_grab.py's movie flow (ensure the resource carries the
category tag so Sonarr's download-client selection routes correctly), but ADDS
the series rather than grabbing one specific torrent — Sonarr's own indexer sync
searches for missing episodes via addOptions.searchForMissingEpisodes.
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath
from typing import Any

from arr_dashboard.release_grab import _category_tag_id
from arr_dashboard.settings import Settings
from arr_dashboard.sources import build_sonarr

log = logging.getLogger("arr_dashboard.series_grab")


class SeriesGrabError(Exception):
    """Raised when the series cannot be added/tagged cleanly (surfaced as HTTP 409)."""


def add_series(
    settings: Settings,
    *,
    tvdb_id: int,
    title: str,
    year: int | None,
    root_path: str,
    profile_name: str,
    series_type: str,
    monitor: str,
) -> dict[str, str]:
    sonarr = build_sonarr(settings)
    if sonarr is None:
        raise SeriesGrabError("no sonarr client")

    tag_label = PurePosixPath(root_path).name

    existing = sonarr.get(f"/series?tvdbId={tvdb_id}")
    if existing:
        series: dict[str, Any] = existing[0]
        sid = int(series["id"])
        # A series added elsewhere but not yet tagged by arrconf's periodic apply
        # carries no category tag → the grab would find no eligible download
        # client. Ensure the chosen category tag is present.
        tag_id = _category_tag_id(sonarr, tag_label)
        if tag_id not in (series.get("tags") or []):
            sonarr._request(
                "PUT",
                "/series/editor",
                json={"seriesIds": [sid], "tags": [tag_id], "applyTags": "add"},
            )
        return {"status": "exists", "series_id": str(sid)}

    # Sonarr's POST /series needs the FULL looked-up series object (title/
    # titleSlug/images/seasons/…) — a bare {tvdbId,...} payload 500s, same as
    # Radarr's movie add.
    hits = sonarr.get(f"/series/lookup?term=tvdb:{tvdb_id}")
    if not hits:
        raise SeriesGrabError(f"série tvdb:{tvdb_id} introuvable dans le lookup Sonarr")
    series = dict(hits[0])
    profiles = sonarr.get("/qualityprofile")
    prof = next((p for p in profiles if p["name"] == profile_name), None)
    if prof is None:
        raise SeriesGrabError(f"quality profile {profile_name} absent de Sonarr")
    # Category tag = the root folder's basename → routes the add to the matching
    # (tagged) download client → correct qBit category → correct /media bucket.
    tag_id = _category_tag_id(sonarr, tag_label)
    series.update(
        {
            "qualityProfileId": prof["id"],
            "rootFolderPath": root_path,
            "monitored": True,
            "seasonFolder": True,
            "seriesType": series_type,
            "tags": [tag_id],
            "addOptions": {"monitor": monitor, "searchForMissingEpisodes": True},
        }
    )
    added = sonarr.post("/series", json=series)
    log.info("added series (tvdb:%s) %s monitor=%s", tvdb_id, title, monitor)
    return {"status": "added", "series_id": str(added["id"])}
