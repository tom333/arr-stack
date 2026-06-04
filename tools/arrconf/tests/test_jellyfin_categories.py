"""Phase 16 wiring test: Categories → 10 Jellyfin libs (REQ-jellyfin-categories-as-libs).

Phase 16 (D-16-LIB-CREATE-01 + D-16-LIB-NAME-01 + D-16-COLLECTIONTYPE-01) replaces
the Phase 7 / Phase 10 ``2 super-libs (Séries, Films) with multi-path PathInfos``
design. Each Category in ``cfg.categories`` becomes its own JellyfinLibrary with
a single PathInfo /media/<name>.

Fixture mirrors the production ``charts/arr-stack/files/arrconf.yml`` 10-category list.
"""

from __future__ import annotations

from arrconf.resources.categories import Category as MediaCategory
from arrconf.generators.categories import generate_jellyfin_libraries

PRODUCTION_CATEGORIES = [
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
        "display": "Nouveaux Films",
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
]


def _build_cfg() -> list[MediaCategory]:
    return [MediaCategory.model_validate(c) for c in PRODUCTION_CATEGORIES]


def test_generate_jellyfin_libraries_ten_libs() -> None:
    """REQ-jellyfin-categories-as-libs: 10 categories → 10 JellyfinLibrary entries."""
    cfg = _build_cfg()
    libs = generate_jellyfin_libraries(cfg)
    assert len(libs) == 10


def test_generate_jellyfin_libraries_collection_type_mapping() -> None:
    """D-16-COLLECTIONTYPE-01: kind='series' → tvshows, kind='movies' → movies."""
    cfg = _build_cfg()
    libs = generate_jellyfin_libraries(cfg)

    series_libs = [lib for lib in libs if lib.collection_type == "tvshows"]
    movies_libs = [lib for lib in libs if lib.collection_type == "movies"]
    assert len(series_libs) == 5
    assert len(movies_libs) == 5

    # Cross-check pairing: kind matches collection_type position-by-position.
    for cat, lib in zip(PRODUCTION_CATEGORIES, libs, strict=True):
        expected = "tvshows" if cat["kind"] == "series" else "movies"
        assert lib.collection_type == expected, (
            f"Category {cat['name']!r} (kind={cat['kind']!r}) → "
            f"expected collection_type={expected!r}, got {lib.collection_type!r}"
        )


def test_generate_jellyfin_libraries_names_match_display() -> None:
    """D-16-LIB-NAME-01: lib.name = categories[].display (UTF-8 verbatim)."""
    cfg = _build_cfg()
    libs = generate_jellyfin_libraries(cfg)

    expected_names = [c["display"] for c in PRODUCTION_CATEGORIES]
    actual_names = [lib.name for lib in libs]
    assert actual_names == expected_names

    # Explicit UTF-8 spot-checks (guard against accidental normalization).
    assert "Séries - Émilie" in actual_names
    assert "Séries - Zoé" in actual_names
    assert "Films - Animation Enfants" in actual_names


def test_generate_jellyfin_libraries_paths_single_per_lib() -> None:
    """Each lib has exactly 1 PathInfo: /media/<categories[].name>."""
    cfg = _build_cfg()
    libs = generate_jellyfin_libraries(cfg)

    for cat, lib in zip(PRODUCTION_CATEGORIES, libs, strict=True):
        assert len(lib.paths) == 1
        assert lib.paths[0] == cat["base_path"]
        assert lib.paths[0] == f"/media/{cat['name']}"


def test_generate_jellyfin_libraries_order_follows_categories() -> None:
    """Generator preserves cfg.categories ordering (deterministic for tests + ops)."""
    cfg = _build_cfg()
    libs = generate_jellyfin_libraries(cfg)

    for cat, lib in zip(PRODUCTION_CATEGORIES, libs, strict=True):
        assert lib.name == cat["display"]


def test_generate_jellyfin_libraries_empty_cfg() -> None:
    """Empty categories → empty list (no implicit super-libs — Phase 16 reversal)."""
    libs = generate_jellyfin_libraries([])
    assert libs == []
