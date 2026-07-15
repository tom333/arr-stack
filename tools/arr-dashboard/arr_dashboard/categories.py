"""Movie and series categories read from intent.yml — the grab target picker's
source of truth.

Each category maps to a root folder (/media/<name>), a category tag (=name,
routes the download client), and a configarr quality profile (via the intent
category-keyword → profile-name mapping)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from arrconf.intent_config import load_intent

log = logging.getLogger("arr_dashboard.categories")


@dataclass(frozen=True)
class MovieCategory:
    name: str  # e.g. "nouveaux-films" — also the Radarr/Sonarr tag label
    display: str  # e.g. "Nouveaux Films"
    root_path: str  # e.g. "/media/nouveaux-films"
    profile: str  # configarr quality-profile name, e.g. "MULTi.VF"
    # Series only: "anime" or "standard" (Sonarr seriesType). "" for movies.
    series_type: str = ""


def _load_categories(intent_path: str, kind: Literal["movies", "series"]) -> list[MovieCategory]:
    """Return the categories of ``kind`` from intent.yml, ordered as declared.

    Empty list if intent.yml is unreadable (mount absent) — the caller decides how
    to degrade."""
    try:
        intent = load_intent(Path(intent_path))
    except Exception as exc:
        log.warning("intent unavailable (%s): no categories", exc)
        return []
    mapping = intent.category_quality_profiles
    cats: list[MovieCategory] = []
    for c in intent.categories:
        if c.kind != kind:
            continue
        cats.append(
            MovieCategory(
                name=c.name,
                display=c.display,
                root_path=c.base_path,
                profile=mapping.get(c.profile, c.profile),
                series_type=("anime" if c.profile == "anime" else "standard")
                if kind == "series"
                else "",
            )
        )
    return cats


def load_movie_categories(intent_path: str) -> list[MovieCategory]:
    return _load_categories(intent_path, "movies")


def load_series_categories(intent_path: str) -> list[MovieCategory]:
    return _load_categories(intent_path, "series")
