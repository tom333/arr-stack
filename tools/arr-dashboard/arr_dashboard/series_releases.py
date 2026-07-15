"""Prowlarr latest TV-releases feed: fetch, parse, dedup, library cross-reference.

Mirrors releases.py (movies) but targets Sonarr/tvdb instead of Radarr/tmdb. The
quality regexes (_RES/_SOURCE/_CODEC/_LANG) are reused verbatim from releases.py —
scene naming conventions for resolution/source/codec/language don't differ between
movie and TV releases, only the title-prefix parsing (season/episode vs year) does.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

from arr_dashboard.models import Release
from arr_dashboard.releases import _CODEC, _LANG, _RES, _SOURCE, _poster_from, _within_window
from arr_dashboard.settings import Settings

log = logging.getLogger("arr_dashboard.series_releases")

_SEASON_EP = re.compile(r"\bS(\d{1,2})(?:E(\d{1,3}))?\b", re.IGNORECASE)
_COMPLETE = re.compile(r"\b(COMPLETE|INTEGRALE|COMPLET)\b", re.IGNORECASE)


def parse_series_title(title: str) -> dict[str, Any]:
    """Extract series_name/episode_label/resolution/source/codec/language from a
    scene-style TV release title. Every field is best-effort; missing -> None."""
    sm = _SEASON_EP.search(title)
    cm = _COMPLETE.search(title)
    if sm:
        season = int(sm.group(1))
        ep = sm.group(2)
        episode_label = f"S{season:02d}" + (f"E{int(ep):02d}" if ep else "")
        marker_start = sm.start()
    elif cm:
        episode_label = "COMPLETE"
        marker_start = cm.start()
    else:
        episode_label = None
        marker_start = len(title)

    head = title[:marker_start]
    series_name = re.sub(r"[._]", " ", head).strip(" -")

    rm = _RES.search(title)
    som = _SOURCE.search(title)
    cdm = _CODEC.search(title)
    lm = _LANG.search(title)

    def norm_source(s: str) -> str:
        u = s.upper().replace("-", "")
        if u.startswith("WEB"):
            return "WEB"
        return {"BLURAY": "BluRay", "HDTV": "HDTV", "REMUX": "Remux"}.get(u, s)

    return {
        "series_name": series_name,
        "episode_label": episode_label,
        "resolution": rm.group(1).lower() if rm else None,
        "source": norm_source(som.group(1)) if som else None,
        "codec": cdm.group(1).lower() if cdm else None,
        "language": lm.group(1).upper() if lm else None,
    }


@dataclass(frozen=True)
class _SeriesEnrichment:
    tvdb_id: int
    year: int | None
    genres: list[str]
    poster_url: str | None


def _enrich(
    rel: dict[str, Any],
    parsed: dict[str, Any],
    sonarr: Any,
    cache: dict[str, _SeriesEnrichment] | None = None,
) -> _SeriesEnrichment:
    """Resolve tvdb + year + genres + poster via Sonarr series/lookup. FR trackers
    report tvdbId=0 -> lookup by series name term. When Prowlarr already gives a
    tvdbId, look up by tvdb:<id> to still get year/genres/poster.

    Many episodes of the same show share the same lookup term; ``cache`` memoizes
    the result per term so the cold fetch does one Sonarr lookup per series, not per
    release (drops cold-fetch latency from minutes to seconds)."""
    pro_tvdb = int(rel.get("tvdbId") or 0)
    if sonarr is None:
        return _SeriesEnrichment(tvdb_id=pro_tvdb, year=None, genres=[], poster_url=None)
    name = parsed.get("series_name") or rel.get("title", "")
    term = f"tvdb:{pro_tvdb}" if pro_tvdb else (quote(name) if name else None)
    if term is None:
        return _SeriesEnrichment(tvdb_id=0, year=None, genres=[], poster_url=None)
    if cache is not None and term in cache:
        return cache[term]
    try:
        hits = sonarr.get(f"/series/lookup?term={term}")
    except Exception as exc:
        log.debug("lookup failed for %s: %s", rel.get("title"), exc)
        hits = []
    if not hits:
        result = _SeriesEnrichment(tvdb_id=pro_tvdb, year=None, genres=[], poster_url=None)
    else:
        hit = hits[0]
        tvdb = int(hit.get("tvdbId") or pro_tvdb or 0)
        result = _SeriesEnrichment(
            tvdb_id=tvdb,
            year=hit.get("year"),
            genres=list(hit.get("genres") or []),
            poster_url=_poster_from(hit),
        )
    if cache is not None:
        cache[term] = result
    return result


def fetch_series_releases(settings: Settings) -> list[Release]:
    """Aggregate latest TV releases across healthy Prowlarr indexers.
    Per-indexer failures are skipped + logged. Dedup by infoHash. Flags in-library
    via Sonarr tvdb set. NOTE: Release.tmdb_id holds the tvdbId for series rows —
    Release has no dedicated tvdb field (D-XX reuse, see series_releases.py)."""
    from arr_dashboard.sources import build_prowlarr, build_sonarr

    prowlarr = build_prowlarr(settings)
    if prowlarr is None:
        return []

    try:
        indexers = prowlarr.get("/indexer")
    except Exception as exc:
        log.warning("prowlarr indexer list failed: %s", exc)
        return []

    sonarr_tvdb: set[int] = set()
    sonarr = build_sonarr(settings)
    if sonarr is not None:
        try:
            for s in sonarr.get("/series"):
                if s.get("tvdbId"):
                    sonarr_tvdb.add(int(s["tvdbId"]))
        except Exception as exc:
            log.warning("sonarr series list failed: %s", exc)

    cutoff = datetime.now(UTC) - timedelta(hours=settings.releases_window_hours)
    lookup_cache: dict[str, _SeriesEnrichment] = {}  # memoize per series → 1 lookup/show
    by_hash: dict[str, Release] = {}
    for ix in indexers:
        if not ix.get("enable"):
            continue
        iid, iname = ix["id"], ix["name"]
        try:
            results = prowlarr.get(f"/search?query=&indexerIds={iid}&categories=5000")
        except Exception as exc:
            log.warning("prowlarr search failed on indexer %s (%s): %s", iid, iname, exc)
            continue
        kept = 0
        for rel in results:
            if kept >= settings.releases_cap_per_indexer:
                break
            ih = rel.get("infoHash")
            if not ih or ih in by_hash:
                continue
            if not _within_window(rel.get("publishDate", ""), cutoff):
                continue
            parsed = parse_series_title(rel.get("title", ""))
            enr = _enrich(rel, parsed, sonarr, lookup_cache)
            by_hash[ih] = Release(
                title=rel.get("title", ""),
                info_hash=ih,
                guid=rel.get("guid", ""),
                indexer_id=iid,
                indexer_name=iname,
                size=int(rel.get("size") or 0),
                publish_date=rel.get("publishDate", ""),
                year=enr.year,
                tmdb_id=(enr.tvdb_id or None),
                seeders=rel.get("seeders"),
                leechers=rel.get("leechers"),
                genres=enr.genres,
                poster_url=enr.poster_url,
                resolution=parsed["resolution"],
                source=parsed["source"],
                codec=parsed["codec"],
                language=parsed["language"],
                in_library=(enr.tvdb_id in sonarr_tvdb) if enr.tvdb_id else False,
                episode_label=parsed["episode_label"],
            )
            kept += 1
    return list(by_hash.values())
