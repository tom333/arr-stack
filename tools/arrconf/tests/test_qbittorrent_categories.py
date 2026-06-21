"""Phase 10 wiring test: Categories->qBit categories.

Validates that generate_qbit_categories delivers the right list to the reconciler.

NOT a __main__.py end-to-end test -- pure data-flow verification.
"""

from __future__ import annotations

from arrconf.generators.categories import generate_qbit_categories
from arrconf.resources.categories import Category as MediaCategory

# Production fixture (same 10-category set as test_generators_categories.py).
PRODUCTION_CATEGORIES = [
    {
        "name": "films",
        "kind": "movies",
        "profile": "general",
        "display": "Films",
        "base_path": "/media/films",
    },
    {
        "name": "nouveaux-films",
        "kind": "movies",
        "profile": "general",
        "display": "Films - Nouveaux",
        "base_path": "/media/nouveaux-films",
    },
    {
        "name": "films-enfants",
        "kind": "movies",
        "profile": "family",
        "display": "Films - Enfants",
        "base_path": "/media/films-enfants",
    },
    {
        "name": "films-animation-enfants",
        "kind": "movies",
        "profile": "family",
        "display": "Films - Animation Enfants",
        "base_path": "/media/films-animation-enfants",
    },
    {
        "name": "films-zoe",
        "kind": "movies",
        "profile": "anime",
        "display": "Films - Zoé",
        "base_path": "/media/films-zoe",
    },
    {
        "name": "series",
        "kind": "series",
        "profile": "general",
        "display": "Séries",
        "base_path": "/media/series",
    },
    {
        "name": "series-emilie",
        "kind": "series",
        "profile": "general",
        "display": "Séries - Émilie",
        "base_path": "/media/series-emilie",
    },
    {
        "name": "series-thomas",
        "kind": "series",
        "profile": "general",
        "display": "Séries - Thomas",
        "base_path": "/media/series-thomas",
    },
    {
        "name": "series-garcons",
        "kind": "series",
        "profile": "family",
        "display": "Séries - Garçons",
        "base_path": "/media/series-garcons",
    },
    {
        "name": "series-zoe",
        "kind": "series",
        "profile": "anime",
        "display": "Séries - Zoé",
        "base_path": "/media/series-zoe",
    },
]


def test_categories_wiring_10_entries() -> None:
    """10 categories declared -> reconciler sees 10 entries."""
    cats = [MediaCategory.model_validate(c) for c in PRODUCTION_CATEGORIES]
    generated = generate_qbit_categories(cats)
    assert len(generated) == 10
    names = {c.name for c in generated}
    assert "series-zoe" in names
    assert "films" in names


def test_savepath_format() -> None:
    """Generated qBit savePath uses /data/<name> (qBit-side), not <c.base_path>.

    qBit mounts the shared torrents volume at /data, so /data/<name> is the same
    bytes as Sonarr/Radarr's /data/torrents/<name> (they mount it at /data/torrents).
    The Sonarr/Radarr RPM /data/<name>/ -> /data/torrents/<name>/ bridges the offset.
    Anchored by audit.py valid_qbit_save_paths = /data/<name>.
    """
    cats = [MediaCategory.model_validate(c) for c in PRODUCTION_CATEGORIES]
    generated = generate_qbit_categories(cats)
    zoe = next(c for c in generated if c.name == "series-zoe")
    assert zoe.savePath == "/data/series-zoe"
