"""Prowlarr latest-releases feed: fetch, parse, dedup, library cross-reference."""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

from arr_dashboard.models import Release
from arr_dashboard.settings import Settings

log = logging.getLogger("arr_dashboard.releases")

_ENRICH_WORKERS = 12  # concurrent Radarr lookups; cold fetch was ~180 sequential calls

_YEAR = re.compile(r"\b(19[3-9]\d|20[0-4]\d)\b")
_RES = re.compile(r"\b(2160p|1080p|720p|480p)\b", re.IGNORECASE)
_SOURCE = re.compile(r"\b(BluRay|WEB-?DL|WEB-?Rip|WEB|HDTV|Remux|DVDRip|HDRip)\b", re.IGNORECASE)
_CODEC = re.compile(r"\b(x265|h\.?265|hevc|x264|h\.?264|av1)\b", re.IGNORECASE)
_LANG = re.compile(r"\b(MULTI|TRUEFRENCH|FRENCH|VFF|VFI|VFQ|VOSTFR|SUBFRENCH)\b", re.IGNORECASE)


def parse_release_title(title: str) -> dict[str, Any]:
    """Extract year/resolution/source/codec/language from a scene-style title.
    Every field is best-effort; missing -> None."""
    ym = _YEAR.search(title)
    rm = _RES.search(title)
    sm = _SOURCE.search(title)
    cm = _CODEC.search(title)
    lm = _LANG.search(title)

    def norm_source(s: str) -> str:
        u = s.upper().replace("-", "")
        if u.startswith("WEB"):
            return "WEB"
        return {"BLURAY": "BluRay", "HDTV": "HDTV", "REMUX": "Remux"}.get(u, s)

    return {
        "year": int(ym.group(1)) if ym else None,
        "resolution": rm.group(1).lower() if rm else None,
        "source": norm_source(sm.group(1)) if sm else None,
        "codec": cm.group(1).lower() if cm else None,
        "language": lm.group(1).upper() if lm else None,
    }


def _within_window(publish_date: str, cutoff: datetime) -> bool:
    try:
        dt = datetime.fromisoformat(publish_date.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return True  # keep undated rather than drop
    return dt >= cutoff


def _lookup_term(title: str, year: int) -> str:
    """Strip scene noise to a 'Title Year' term for Radarr movie/lookup."""
    head = re.split(r"\b(?:19[3-9]\d|20[0-4]\d)\b", title, maxsplit=1)[0]
    clean = re.sub(r"[._]", " ", head).strip()
    return quote(f"{clean} {year}")


@dataclass(frozen=True)
class _Enrichment:
    tmdb_id: int
    genres: list[str]
    poster_url: str | None


def _poster_from(hit: dict[str, Any]) -> str | None:
    for img in hit.get("images", []):
        if img.get("coverType") == "poster":
            url = img.get("remoteUrl") or img.get("url")
            return str(url) if url else None
    return None


def _term(rel: dict[str, Any], parsed: dict[str, Any]) -> str | None:
    """The Radarr movie/lookup term for a release: tmdb:<id> when Prowlarr already
    gives a tmdbId, else a 'Title Year' term stripped of scene noise. None when
    neither a tmdbId nor a parsed year is available (can't look it up)."""
    pro_tmdb = int(rel.get("tmdbId") or 0)
    if pro_tmdb:
        return f"tmdb:{pro_tmdb}"
    if parsed["year"]:
        return _lookup_term(rel.get("title", ""), parsed["year"])
    return None


def _lookup(term: str, radarr: Any) -> _Enrichment:
    """Resolve one lookup term via Radarr movie/lookup. Never raises -- a failed or
    empty lookup degrades to the tmdbId encoded in the term (0 for title/year terms)."""
    pro_tmdb = int(term.split(":", 1)[1]) if term.startswith("tmdb:") else 0
    try:
        hits = radarr.get(f"/movie/lookup?term={term}")
    except Exception as exc:
        log.debug("lookup failed for term %s: %s", term, exc)
        hits = []
    if not hits:
        return _Enrichment(tmdb_id=pro_tmdb, genres=[], poster_url=None)
    hit = hits[0]
    tmdb = int(hit.get("tmdbId") or pro_tmdb or 0)
    return _Enrichment(
        tmdb_id=tmdb, genres=list(hit.get("genres") or []), poster_url=_poster_from(hit)
    )


def _enrich(
    rel: dict[str, Any],
    parsed: dict[str, Any],
    radarr: Any,
    cache: dict[str, _Enrichment] | None = None,
) -> _Enrichment:
    """Resolve tmdb + genres + poster via Radarr movie/lookup. FR trackers report
    tmdbId=0 -> lookup by title/year term. When Prowlarr already gives a tmdbId,
    look up by tmdb:<id> to still get genres/poster.

    ``cache`` memoizes the lookup per term so multiple releases of the same film
    (VOF/FRENCH/.mkv variants common on FR trackers) do one lookup, not one each."""
    pro_tmdb = int(rel.get("tmdbId") or 0)
    if radarr is None:
        return _Enrichment(tmdb_id=pro_tmdb, genres=[], poster_url=None)
    term = _term(rel, parsed)
    if term is None:
        return _Enrichment(tmdb_id=0, genres=[], poster_url=None)
    if cache is not None and term in cache:
        return cache[term]
    result = _lookup(term, radarr)
    if cache is not None:
        cache[term] = result
    return result


def _enrich_all(
    items: list[tuple[dict[str, Any], dict[str, Any]]], radarr: Any
) -> dict[str, _Enrichment]:
    """Look up every distinct term across ``items`` concurrently. Returns a
    term -> _Enrichment map; callers pass this as ``_enrich``'s ``cache`` so
    assembly stays a plain sequential dict lookup."""
    if radarr is None:
        return {}
    terms = {t for rel, parsed in items if (t := _term(rel, parsed)) is not None}
    if not terms:
        return {}
    with ThreadPoolExecutor(max_workers=_ENRICH_WORKERS) as ex:
        futures = {term: ex.submit(_lookup, term, radarr) for term in terms}
        return {term: fut.result() for term, fut in futures.items()}


def fetch_releases(settings: Settings) -> list[Release]:
    """Aggregate latest movie releases across healthy Prowlarr indexers.
    Per-indexer failures are skipped + logged. Dedup by infoHash. Flags in-library
    via Radarr tmdb set."""
    from arr_dashboard.sources import build_prowlarr, build_radarr

    prowlarr = build_prowlarr(settings)
    if prowlarr is None:
        return []

    try:
        indexers = prowlarr.get("/indexer")
    except Exception as exc:
        log.warning("prowlarr indexer list failed: %s", exc)
        return []

    radarr_tmdb: set[int] = set()
    radarr = build_radarr(settings)
    if radarr is not None:
        try:
            for m in radarr.get("/movie"):
                if m.get("hasFile") and m.get("tmdbId"):
                    radarr_tmdb.add(int(m["tmdbId"]))
        except Exception as exc:
            log.warning("radarr movie list failed: %s", exc)

    cutoff = datetime.now(UTC) - timedelta(hours=settings.releases_window_hours)
    # Collect phase: sequential per-indexer search, window filter, dedup-by-hash,
    # cap-per-indexer, parse. No arr lookups here -- those are batched below.
    seen_hashes: set[str] = set()
    collected: list[tuple[dict[str, Any], dict[str, Any], str, int, str]] = []
    for ix in indexers:
        if not ix.get("enable"):
            continue
        iid, iname = ix["id"], ix["name"]
        try:
            results = prowlarr.get(f"/search?query=&indexerIds={iid}&categories=2000")
        except Exception as exc:
            log.warning("prowlarr search failed on indexer %s (%s): %s", iid, iname, exc)
            continue
        kept = 0
        for rel in results:
            if kept >= settings.releases_cap_per_indexer:
                break
            ih = rel.get("infoHash")
            if not ih or ih in seen_hashes:
                continue
            if not _within_window(rel.get("publishDate", ""), cutoff):
                continue
            parsed = parse_release_title(rel.get("title", ""))
            seen_hashes.add(ih)
            collected.append((rel, parsed, ih, iid, iname))
            kept += 1

    # Parallel enrich phase: one Radarr lookup per DISTINCT term, not per release.
    lookup_cache = _enrich_all([(rel, parsed) for rel, parsed, *_ in collected], radarr)

    releases: list[Release] = []
    for rel, parsed, ih, iid, iname in collected:
        enr = _enrich(rel, parsed, radarr, lookup_cache)
        releases.append(
            Release(
                title=rel.get("title", ""),
                info_hash=ih,
                guid=rel.get("guid", ""),
                indexer_id=iid,
                indexer_name=iname,
                size=int(rel.get("size") or 0),
                publish_date=rel.get("publishDate", ""),
                year=parsed["year"],
                tmdb_id=(enr.tmdb_id or None),
                seeders=rel.get("seeders"),
                leechers=rel.get("leechers"),
                genres=enr.genres,
                poster_url=enr.poster_url,
                resolution=parsed["resolution"],
                source=parsed["source"],
                codec=parsed["codec"],
                language=parsed["language"],
                in_library=(enr.tmdb_id in radarr_tmdb) if enr.tmdb_id else False,
            )
        )
    return releases
