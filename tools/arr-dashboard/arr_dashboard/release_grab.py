"""Grab a specific Prowlarr release into Radarr with a clean import.

Bridge: Prowlarr and Radarr assign different release GUIDs, so we add the movie
(if missing), let Radarr search its own indexers, match the target by infoHash
(stable), and POST Radarr's own guid to grab. No silent qBit orphan on failure.
"""

from __future__ import annotations

import logging
from typing import Any

from arr_dashboard.settings import Settings
from arr_dashboard.sources import build_radarr

log = logging.getLogger("arr_dashboard.release_grab")

# category-profile keyword -> default root folder path (matches intent.categories movies roots)
_PROFILE_ROOT = {
    "MULTi.VF": "/media/films",
    "Anime": "/media/films-zoe",
    "Family": "/media/films-enfants",
}


class ReleaseGrabError(Exception):
    """Raised when the release cannot be grabbed cleanly (surfaced as HTTP 409)."""


def _ensure_movie(radarr: Any, tmdb_id: int, profile_name: str) -> int:
    existing = radarr.get(f"/movie?tmdbId={tmdb_id}")
    if existing:
        return int(existing[0]["id"])
    # Radarr's POST /movie needs the FULL looked-up movie object (title/titleSlug/
    # images/…). A bare {tmdbId,...} payload makes its folder Organizer throw a
    # NullReferenceException (HTTP 500). So fetch the lookup object and merge the
    # add fields into it.
    hits = radarr.get(f"/movie/lookup?term=tmdb:{tmdb_id}")
    if not hits:
        raise ReleaseGrabError(f"film tmdb:{tmdb_id} introuvable dans le lookup Radarr")
    movie = dict(hits[0])
    profiles = radarr.get("/qualityprofile")
    prof = next((p for p in profiles if p["name"] == profile_name), None)
    if prof is None:
        raise ReleaseGrabError(f"quality profile {profile_name} absent de Radarr")
    roots = radarr.get("/rootfolder")
    want = _PROFILE_ROOT.get(profile_name, "/media/films")
    root = next((r for r in roots if r["path"] == want), roots[0] if roots else None)
    if root is None:
        raise ReleaseGrabError("aucun root folder Radarr")
    movie.update(
        {
            "qualityProfileId": prof["id"],
            "rootFolderPath": root["path"],
            "monitored": True,
            "addOptions": {"searchForMovie": False},
        }
    )
    added = radarr.post("/movie", json=movie)
    return int(added["id"])


def grab_release(
    settings: Settings,
    *,
    info_hash: str,
    tmdb_id: int,
    title: str,
    year: int | None,
    profile_name: str = "MULTi.VF",
) -> dict[str, str]:
    radarr = build_radarr(settings)
    if radarr is None:
        raise ReleaseGrabError("no radarr client")

    movie_id = _ensure_movie(radarr, tmdb_id, profile_name)

    candidates = radarr.get(f"/release?movieId={movie_id}")
    target_hash = info_hash.upper()
    match = next((c for c in candidates if str(c.get("infoHash", "")).upper() == target_hash), None)
    if match is None:
        raise ReleaseGrabError(
            "release introuvable côté Radarr (timing/re-catégorisation) — réessaie ou grab manuel"
        )
    radarr.post("/release", json={"guid": match["guid"], "indexerId": match["indexerId"]})
    log.info("grabbed release %s for movie %s", target_hash, movie_id)
    return {"status": "grabbed", "movie_id": str(movie_id)}
