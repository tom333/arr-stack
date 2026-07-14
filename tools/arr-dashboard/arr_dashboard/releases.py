"""Prowlarr latest-releases feed: fetch, parse, dedup, library cross-reference."""

from __future__ import annotations

import logging
import re
from typing import Any

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
