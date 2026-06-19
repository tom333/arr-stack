"""Unmonitor already-imported items (frontier-safe item-state writes only).

Radarr: movies with a file -> monitored=false (PUT /movie/editor).
Sonarr: episodes with a file -> monitored=false (PUT /episode/monitor); the SERIES
record is never touched, so newly-aired episodes still grab.

No quality-profile / custom-format DEFINITION is written -- ADR-5 boundary respected
by construction (only /movie/editor and /episode/monitor item endpoints are called).
"""

from __future__ import annotations

import structlog

from arrconf.client_base import ArrApiClient

log = structlog.get_logger()


def unmonitor_imported_movies(client: ArrApiClient, *, dry_run: bool) -> list[str]:
    """Unmonitor Radarr movies that already have a file."""
    movies = client.get("/movie")
    ids = [m["id"] for m in movies if m.get("hasFile") and m.get("monitored")]
    if not ids:
        log.info("unmonitor_movies_no_op")
        return ["unmonitor_movies:no-op"]
    if dry_run:
        log.info("dry_run_skip", resource="unmonitor_movies", count=len(ids))
        return [f"unmonitor_movies:dry_run:{len(ids)}"]
    client._request("PUT", "/movie/editor", json={"movieIds": ids, "monitored": False})
    log.info("unmonitor_movies_applied", count=len(ids))
    return [f"unmonitor_movies:applied:{len(ids)}"]


def unmonitor_downloaded_episodes(client: ArrApiClient, *, dry_run: bool) -> list[str]:
    """Unmonitor Sonarr episodes that already have a file; the series stays monitored."""
    series = client.get("/series")
    ep_ids: list[int] = []
    for s in series:
        # Sonarr returns ALL episodes for a series in one call (no pagination for the
        # seriesId-scoped GET) — one GET per series, then a single bulk PUT below.
        episodes = client.get(f"/episode?seriesId={s['id']}")
        ep_ids.extend(e["id"] for e in episodes if e.get("hasFile") and e.get("monitored"))
    if not ep_ids:
        log.info("unmonitor_episodes_no_op")
        return ["unmonitor_episodes:no-op"]
    if dry_run:
        log.info("dry_run_skip", resource="unmonitor_episodes", count=len(ep_ids))
        return [f"unmonitor_episodes:dry_run:{len(ep_ids)}"]
    client._request("PUT", "/episode/monitor", json={"episodeIds": ep_ids, "monitored": False})
    log.info("unmonitor_episodes_applied", count=len(ep_ids))
    return [f"unmonitor_episodes:applied:{len(ep_ids)}"]
