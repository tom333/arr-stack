"""Grab a specific Prowlarr release into Radarr with a clean import.

Bridge: Prowlarr and Radarr assign different release GUIDs, so we add the movie
(if missing), let Radarr search its own indexers, match the target by infoHash
(stable), and POST Radarr's own guid to grab. No silent qBit orphan on failure.
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath
from typing import Any

from arr_dashboard.settings import Settings
from arr_dashboard.sources import build_radarr

log = logging.getLogger("arr_dashboard.release_grab")


class ReleaseGrabError(Exception):
    """Raised when the release cannot be grabbed cleanly (surfaced as HTTP 409)."""


def _category_tag_id(radarr: Any, label: str) -> int:
    """Resolve (or create) the Radarr tag id for a category label.

    Each category (films / films-zoe / films-enfants / …) is a Radarr tag whose
    matching download client routes the grab to the right qBit category → /media
    bucket. A freshly-added movie MUST carry this tag or Radarr's client selection
    finds no eligible (all-tagged, no catch-all) download client and the grab 500s
    with DownloadClientUnavailableException. arrconf normally sets it at apply time;
    we set it at add time so the immediate grab routes correctly."""
    for t in radarr.get("/tag"):
        if t.get("label") == label:
            return int(t["id"])
    created = radarr.post("/tag", json={"label": label})
    return int(created["id"])


def _ensure_movie(radarr: Any, tmdb_id: int, root_path: str, profile_name: str) -> int:
    """Ensure the movie exists in Radarr, in the chosen category (root_path), with
    the category tag so the grab routes to the matching download client.

    root_path = the category's root folder (e.g. /media/nouveaux-films); the tag
    label is its basename. profile_name = the configarr quality-profile name."""
    tag_label = PurePosixPath(root_path).name
    existing = radarr.get(f"/movie?tmdbId={tmdb_id}")
    if existing:
        movie = existing[0]
        mid = int(movie["id"])
        # A movie added elsewhere (e.g. Seerr) but not yet tagged by arrconf's
        # 4-hourly apply carries no category tag → the grab would find no eligible
        # download client. Ensure the chosen category tag is present.
        tag_id = _category_tag_id(radarr, tag_label)
        if tag_id not in (movie.get("tags") or []):
            radarr._request(
                "PUT",
                "/movie/editor",
                json={"movieIds": [mid], "tags": [tag_id], "applyTags": "add"},
            )
        return mid
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
    root = next((r for r in roots if r["path"] == root_path), roots[0] if roots else None)
    if root is None:
        raise ReleaseGrabError("aucun root folder Radarr")
    # Category tag = the root folder's basename → routes the grab to the matching
    # (tagged) download client → correct qBit category → correct /media bucket.
    tag_id = _category_tag_id(radarr, PurePosixPath(root["path"]).name)
    movie.update(
        {
            "qualityProfileId": prof["id"],
            "rootFolderPath": root["path"],
            "monitored": True,
            "tags": [tag_id],
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
    root_path: str,
    profile_name: str,
) -> dict[str, str]:
    radarr = build_radarr(settings)
    if radarr is None:
        raise ReleaseGrabError("no radarr client")

    movie_id = _ensure_movie(radarr, tmdb_id, root_path, profile_name)

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
