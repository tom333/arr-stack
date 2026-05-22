"""Phase 10 wiring test: Categories->Jellyfin 2 super-libraries (REQ-categories-jellyfin-paths)."""

from __future__ import annotations

from arrconf.config import RootConfig
from arrconf.generators.categories import generate_jellyfin_libraries

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


def _build_cfg() -> RootConfig:
    return RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})


def test_jellyfin_libraries_wiring() -> None:
    """5+5 -> 2 libraries with 5 paths each."""
    cfg = _build_cfg()
    generated = generate_jellyfin_libraries(cfg)
    assert len(generated) == 2
    series_lib = next(lib for lib in generated if lib.name == "Séries")
    films_lib = next(lib for lib in generated if lib.name == "Films")
    assert len(series_lib.paths) == 5
    assert len(films_lib.paths) == 5
    assert series_lib.collection_type == "tvshows"
    assert films_lib.collection_type == "movies"


def test_jellyfin_libraries_path_content() -> None:
    cfg = _build_cfg()
    generated = generate_jellyfin_libraries(cfg)
    series_lib = next(lib for lib in generated if lib.name == "Séries")
    films_lib = next(lib for lib in generated if lib.name == "Films")
    assert "/media/series-zoe" in series_lib.paths
    assert "/media/films-zoe" in films_lib.paths
    # Cross-check: series base_paths must not appear in Films, and vice versa.
    for p in series_lib.paths:
        assert not p.startswith("/media/films")
    for p in films_lib.paths:
        assert p.startswith("/media/films") or p.startswith("/media/nouveaux-films")


def test_jellyfin_no_categories_returns_two_empty_libraries() -> None:
    """Generator always returns 2 libraries; when cfg is empty they have no paths.

    The reconciler's _reconcile_libraries will simply skip them
    (library_missing_skip warning if cluster doesn't have them, or no-op if it does).
    """
    cfg_empty = RootConfig()
    generated = generate_jellyfin_libraries(cfg_empty)
    assert len(generated) == 2
    assert generated[0].paths == []
    assert generated[1].paths == []


def test_jellyfin_only_series_no_movies() -> None:
    """Films library has empty paths when cfg has only series categories."""
    cfg = RootConfig.model_validate(
        {"categories": [c for c in PRODUCTION_CATEGORIES if c["kind"] == "series"]}
    )
    generated = generate_jellyfin_libraries(cfg)
    series_lib = next(lib for lib in generated if lib.name == "Séries")
    films_lib = next(lib for lib in generated if lib.name == "Films")
    assert len(series_lib.paths) == 5
    assert films_lib.paths == []


def test_jellyfin_libraries_order() -> None:
    """Library order is [Séries, Films] (matches generator output)."""
    cfg = _build_cfg()
    generated = generate_jellyfin_libraries(cfg)
    assert generated[0].name == "Séries"
    assert generated[1].name == "Films"
