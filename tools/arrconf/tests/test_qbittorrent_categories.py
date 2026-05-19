"""Phase 10 wiring test: Categories->qBit categories via merge_with_manual.

Validates the integration between:
- arrconf.generators.categories.generate_qbit_categories
- arrconf.reconcilers._shared.merge_with_manual
- arrconf.reconcilers.qbittorrent._reconcile_categories

NOT a __main__.py end-to-end test -- just verifies the merge contract delivers
the right list to the reconciler input slot.
"""

from __future__ import annotations

from arrconf.config import RootConfig
from arrconf.generators.categories import generate_qbit_categories
from arrconf.reconcilers._shared import merge_with_manual
from arrconf.resources.qbittorrent.category import Category

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
    """When manual is empty + 10 categories declared -> reconciler sees 10 entries."""
    cfg = RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})
    generated = generate_qbit_categories(cfg)
    merged = merge_with_manual([], generated, app="qbittorrent", resource="categories")
    assert len(merged) == 10
    names = {c.name for c in merged}
    assert "series-zoe" in names
    assert "films" in names


def test_manual_override_wins() -> None:
    """When manual is non-empty -> generated is skipped entirely (D-02)."""
    cfg = RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})
    generated = generate_qbit_categories(cfg)
    manual = [Category(name="sonarr-tv", savePath="/data/series")]
    merged = merge_with_manual(manual, generated, app="qbittorrent", resource="categories")
    assert len(merged) == 1
    assert merged[0].name == "sonarr-tv"


def test_savepath_format() -> None:
    """Generated qBit savePath uses /data/torrents/<name> not <c.base_path>."""
    cfg = RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})
    generated = generate_qbit_categories(cfg)
    zoe = next(c for c in generated if c.name == "series-zoe")
    assert zoe.savePath == "/data/torrents/series-zoe"
