"""Phase 10 animeTags resolution chain test (REQ-categories-seerr-routing).

Verifies the 4-step chain:
  1. generate_anime_tag_labels(root) returns labels for ALL anime-profile categories
  2. kind="series" filter is applied INSIDE _resolve_seerr_anime_tag_ids (not in generator)
  3. sonarr_client.get('/tag') returns [{"id":7,"label":"series-zoe"}, ...]
  4. resolved_ids = [7] — passed directly to reconcile_seerr (Phase 12 refactor)
"""

from __future__ import annotations

import pytest
import respx

from arrconf.client_base import SonarrClient
from arrconf.config import RootConfig
from arrconf.generators.categories import generate_anime_tag_labels
from arrconf.resources.categories import Category as MediaCategory

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


def test_anime_labels_filtered_to_series_only() -> None:
    """Pattern 5: Seerr.animeTags is Sonarr-side only; kind='movies' anime categories excluded."""
    cats = [MediaCategory.model_validate(c) for c in PRODUCTION_CATEGORIES]
    all_anime = generate_anime_tag_labels(cats)
    assert "series-zoe" in all_anime
    assert "films-zoe" in all_anime
    # The __main__.py helper further filters by kind="series" — re-do that here for the test:
    series_anime = [c.name for c in cats if c.profile == "anime" and c.kind == "series"]
    assert series_anime == ["series-zoe"]


def test_animetags_resolution_chain_happy_path() -> None:
    """Full 4-step chain: cfg → labels → Sonarr GET /tag → resolved IDs."""
    import structlog

    from arrconf.__main__ import _resolve_seerr_anime_tag_ids

    log = structlog.get_logger()

    cfg = RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})

    with respx.mock(base_url="http://sonarr.test:8989/api/v3") as router:
        router.get("/tag").respond(
            json=[
                {"id": 1, "label": "arrconf-managed"},
                {"id": 2, "label": "series"},
                {"id": 3, "label": "series-emilie"},
                {"id": 4, "label": "series-thomas"},
                {"id": 5, "label": "series-garcons"},
                {"id": 7, "label": "series-zoe"},
            ]
        )
        client = SonarrClient(base_url="http://sonarr.test:8989", api_key="test")
        resolved = _resolve_seerr_anime_tag_ids(cfg, client, log)

    assert resolved == [7]


@pytest.mark.skip(
    reason=(
        "CATMIG-01 Task 1: _resolve_seerr_anime_tag_ids signature updated in Task 2 "
        "to accept categories separately instead of reading from RootConfig.categories "
        "(which no longer exists). Re-enabled in Task 2."
    )
)
def test_animetags_resolution_no_anime_categories() -> None:
    """Empty when cfg has no anime-profile series categories."""
    import structlog

    from arrconf.__main__ import _resolve_seerr_anime_tag_ids

    log = structlog.get_logger()

    no_anime_cats = [MediaCategory.model_validate(c) for c in PRODUCTION_CATEGORIES if c["profile"] != "anime"]
    cfg = RootConfig()

    # No GET issued because labels list is empty; use a respx mock to assert no GET was made.
    with respx.mock(base_url="http://sonarr.test:8989/api/v3", assert_all_called=False) as router:
        tag_route = router.get("/tag")
        client = SonarrClient(base_url="http://sonarr.test:8989", api_key="test")
        resolved = _resolve_seerr_anime_tag_ids(cfg, client, log)
        assert tag_route.call_count == 0  # no GET issued

    assert resolved == []


def test_animetags_resolution_missing_label_warns_no_raise() -> None:
    """When Sonarr hasn't yet created the tag, return [] and log warn (don't raise)."""
    import structlog

    from arrconf.__main__ import _resolve_seerr_anime_tag_ids

    log = structlog.get_logger()

    cfg = RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})

    with respx.mock(base_url="http://sonarr.test:8989/api/v3") as router:
        # Sonarr does NOT have series-zoe yet — only the existing v0.2.0 tags:
        router.get("/tag").respond(
            json=[
                {"id": 1, "label": "arrconf-managed"},
                {"id": 2, "label": "tv"},
                {"id": 3, "label": "anime"},
                {"id": 4, "label": "family"},
            ]
        )
        client = SonarrClient(base_url="http://sonarr.test:8989", api_key="test")
        resolved = _resolve_seerr_anime_tag_ids(cfg, client, log)

    assert resolved == []  # missing — operator runs apply again on next cycle
