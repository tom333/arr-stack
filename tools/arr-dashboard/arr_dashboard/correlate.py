from arr_dashboard.models import ChainHealth, Download, Row, Snapshot


def _movie_row(m: dict) -> Row:
    path = (m.get("movieFile") or {}).get("path")
    has_file = bool(m.get("hasFile"))
    return Row(
        key=f"tmdb:{m['tmdbId']}",
        title=m.get("title", "?"),
        year=m.get("year"),
        type="movie",
        arr_app="radarr",
        monitored=m.get("monitored"),
        has_file=has_file,
        disk_paths=[path] if path else [],
        chain=ChainHealth(imported=has_file),
    )


def _series_row(s: dict) -> Row:
    st = s.get("statistics") or {}
    total = st.get("episodeCount", 0)
    have = st.get("episodeFileCount", 0)
    has_file = total > 0 and have >= total
    return Row(
        key=f"tvdb:{s['tvdbId']}",
        title=s.get("title", "?"),
        year=s.get("year"),
        type="series",
        arr_app="sonarr",
        monitored=s.get("monitored"),
        has_file=has_file,
        chain=ChainHealth(imported=has_file),
    )


def correlate(sources: dict, generated_at: str, stale_sources: list[str]) -> Snapshot:
    rows: dict[str, Row] = {}
    for m in sources.get("radarr_movies", []):
        if m.get("tmdbId"):
            r = _movie_row(m)
            rows[r.key] = r
    for s in sources.get("sonarr_series", []):
        if s.get("tvdbId"):
            r = _series_row(s)
            rows[r.key] = r
    return Snapshot(
        rows=list(rows.values()),
        generated_at=generated_at,
        stale_sources=stale_sources,
    )
