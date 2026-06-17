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


_SEERR_STATUS = {
    1: "pending",
    2: "approved",
    3: "declined",
    4: "partially-available",
    5: "available",
}


def _seerr_key(req: dict) -> str | None:
    media = req.get("media") or {}
    if req.get("type") == "movie" and media.get("tmdbId"):
        return f"tmdb:{media['tmdbId']}"
    if req.get("type") in ("tv", "series") and media.get("tvdbId"):
        return f"tvdb:{media['tvdbId']}"
    if media.get("tmdbId"):
        return f"tmdb:{media['tmdbId']}"
    return None


def _torrent_index(qbit: list[dict]) -> dict[str, dict]:
    return {t["hash"].lower(): t for t in qbit if t.get("hash")}


def _to_download(t: dict) -> Download:
    return Download(
        infohash=t["hash"].lower(),
        name=t.get("name", "?"),
        state=t.get("state", "?"),
        progress=float(t.get("progress", 0.0)),
        category=t.get("category"),
        tracker=(t.get("tracker") or None),
        save_path=t.get("save_path"),
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
    by_arr_id: dict[tuple[str, int], Row] = {
        ("radarr", m["id"]): rows[f"tmdb:{m['tmdbId']}"]
        for m in sources.get("radarr_movies", [])
        if m.get("tmdbId")
    }
    by_arr_id.update(
        {
            ("sonarr", s["id"]): rows[f"tvdb:{s['tvdbId']}"]
            for s in sources.get("sonarr_series", [])
            if s.get("tvdbId")
        }
    )
    tindex = _torrent_index(sources.get("qbit_torrents", []))

    for app, qkey, idkey in [
        ("radarr", "radarr_queue", "movieId"),
        ("sonarr", "sonarr_queue", "seriesId"),
    ]:
        for q in sources.get(qkey, []):
            row = by_arr_id.get((app, q.get(idkey)))
            if not row:
                continue
            row.chain.grabbed = True
            dl_id = (q.get("downloadId") or "").lower()
            t = tindex.get(dl_id)
            if t:
                d = _to_download(t)
                row.downloads.append(d)
                if d.progress >= 1.0:
                    row.chain.downloaded = True

    for req in sources.get("seerr_requests", []):
        key = _seerr_key(req)
        if not key:
            continue
        row = rows.get(key)
        if row is None:
            row = Row(
                key=key,
                title=(req.get("media") or {}).get("title", key),
                type="movie" if key.startswith("tmdb:") else "series",
            )
            rows[key] = row
        row.chain.requested = True
        row.requested_by = (req.get("requestedBy") or {}).get("displayName")
        row.request_status = _SEERR_STATUS.get(req.get("status"), str(req.get("status")))

    return Snapshot(
        rows=list(rows.values()),
        generated_at=generated_at,
        stale_sources=stale_sources,
    )
