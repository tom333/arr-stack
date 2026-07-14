"""Prowlarr latest-releases feed: fetch, parse, dedup, library cross-reference."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

from arr_dashboard.models import Release
from arr_dashboard.settings import Settings

log = logging.getLogger("arr_dashboard.releases")

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


def _resolve_tmdb(rel: dict[str, Any], parsed: dict[str, Any], radarr: Any) -> int:
    """FR trackers report tmdbId=0 -> resolve via Radarr movie/lookup (primary path)."""
    tmdb = int(rel.get("tmdbId") or 0)
    if tmdb:
        return tmdb
    if radarr is None or not parsed["year"]:
        return 0
    try:
        hits = radarr.get(
            f"/movie/lookup?term={_lookup_term(rel.get('title', ''), parsed['year'])}"
        )
        if hits and hits[0].get("tmdbId"):
            return int(hits[0]["tmdbId"])
    except Exception as exc:
        log.debug("tmdb lookup failed for %s: %s", rel.get("title"), exc)
    return 0


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
    by_hash: dict[str, Release] = {}
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
            if not ih or ih in by_hash:
                continue
            if not _within_window(rel.get("publishDate", ""), cutoff):
                continue
            parsed = parse_release_title(rel.get("title", ""))
            tmdb = _resolve_tmdb(rel, parsed, radarr)
            by_hash[ih] = Release(
                title=rel.get("title", ""),
                info_hash=ih,
                guid=rel.get("guid", ""),
                indexer_id=iid,
                indexer_name=iname,
                size=int(rel.get("size") or 0),
                publish_date=rel.get("publishDate", ""),
                year=parsed["year"],
                tmdb_id=(tmdb or None),
                resolution=parsed["resolution"],
                source=parsed["source"],
                codec=parsed["codec"],
                language=parsed["language"],
                in_library=(tmdb in radarr_tmdb) if tmdb else False,
            )
            kept += 1
    return list(by_hash.values())
