"""Unit tests for arrconf.generators.categories (Phase 10 D-01).

Coverage targets >=70% on the generators module per CLAUDE.md §"Couverture cible".
No HTTP — generators are pure Python.
"""

from __future__ import annotations

import pytest

from arrconf.resources.categories import Category as MediaCategory
from arrconf.generators.categories import (
    RadarrDerived,
    SonarrDerived,
    generate_anime_tag_labels,
    generate_jellyfin_libraries,
    generate_qbit_categories,
    generate_radarr_resources,
    generate_sonarr_resources,
)

# Production 10-category fixture (verbatim from charts/arr-stack/files/arrconf.yml).
# Order matches arrconf.yml: series categories first, then movies categories.
PRODUCTION_CATEGORIES: list[dict[str, str]] = [
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


def _make_cats(categories: list[dict[str, str]] | None = None) -> list[MediaCategory]:
    """Build a list[MediaCategory] from category dicts (default: production 10)."""
    cats_data = categories if categories is not None else PRODUCTION_CATEGORIES
    return [MediaCategory.model_validate(c) for c in cats_data]


@pytest.fixture
def cfg_production() -> list[MediaCategory]:
    return _make_cats()


@pytest.fixture
def cfg_empty() -> list[MediaCategory]:
    return []


# ===== qBit =====


def test_generate_qbit_categories_returns_10(cfg_production: list[MediaCategory]) -> None:
    result = generate_qbit_categories(cfg_production)
    assert len(result) == 10


def test_generate_qbit_categories_bare_names(cfg_production: list[MediaCategory]) -> None:
    """D-03a: names are bare slugs, NOT '<kind>-<name>'."""
    result = generate_qbit_categories(cfg_production)
    names = [c.name for c in result]
    assert "films" in names
    assert "series-zoe" in names
    # MUST NOT contain any '<kind>-' prefix variant:
    for name in names:
        assert not name.startswith("movies-")
        # series-* names exist but they must be legitimate category slugs
        if name.startswith("series-"):
            assert name in {
                "series-emilie",
                "series-thomas",
                "series-garcons",
                "series-zoe",
            }


def test_generate_qbit_categories_savepath_format(cfg_production: list[MediaCategory]) -> None:
    """Pitfall 3: savePath uses /data/torrents/<name>, NOT base_path (/media/<name>)."""
    result = generate_qbit_categories(cfg_production)
    for c in result:
        assert c.savePath == f"/data/torrents/{c.name}"


def test_generate_qbit_categories_empty(cfg_empty: list[MediaCategory]) -> None:
    assert generate_qbit_categories(cfg_empty) == []


# ===== Sonarr =====


def test_generate_sonarr_resources_5_each(cfg_production: list[MediaCategory]) -> None:
    """D-03b/c/d/e: 5 series → 5 of each resource."""
    result = generate_sonarr_resources(cfg_production)
    assert isinstance(result, SonarrDerived)
    assert len(result.tags) == 5
    assert len(result.root_folders) == 5
    assert len(result.download_clients) == 5
    assert len(result.remote_path_mappings) == 5


def test_generate_sonarr_tag_labels(cfg_production: list[MediaCategory]) -> None:
    """D-03c: TagItem(label=c.name) for each series category."""
    result = generate_sonarr_resources(cfg_production)
    labels = [t.label for t in result.tags]
    assert labels == [
        "series",
        "series-emilie",
        "series-thomas",
        "series-garcons",
        "series-zoe",
    ]


def test_generate_sonarr_root_folders(cfg_production: list[MediaCategory]) -> None:
    """D-03d: RootFolder(path=c.base_path) for each series category."""
    result = generate_sonarr_resources(cfg_production)
    paths = [rf.path for rf in result.root_folders]
    assert paths == [
        "/media/series",
        "/media/series-emilie",
        "/media/series-thomas",
        "/media/series-garcons",
        "/media/series-zoe",
    ]


def test_generate_sonarr_dc_tag_labels(cfg_production: list[MediaCategory]) -> None:
    """D-03b: each DC has tag_labels=[c.name]."""
    result = generate_sonarr_resources(cfg_production)
    expected_labels = [
        "series",
        "series-emilie",
        "series-thomas",
        "series-garcons",
        "series-zoe",
    ]
    for dc, expected_label in zip(result.download_clients, expected_labels, strict=True):
        assert dc.tag_labels == [expected_label]
        assert dc.implementation == "QBittorrent"
        assert dc.configContract == "QBittorrentSettings"


def test_generate_sonarr_dc_tvCategory_field(cfg_production: list[MediaCategory]) -> None:
    """D-03b Sonarr-side: fields[] contains tvCategory=<c.name>."""
    result = generate_sonarr_resources(cfg_production)
    expected_names = [
        "series",
        "series-emilie",
        "series-thomas",
        "series-garcons",
        "series-zoe",
    ]
    for dc, expected_name in zip(result.download_clients, expected_names, strict=True):
        tv_cat_field = next(f for f in dc.fields if f.name == "tvCategory")
        assert tv_cat_field.value == expected_name
        # Must NOT have Radarr-only fields:
        assert not any(f.name == "movieCategory" for f in dc.fields)


def test_generate_sonarr_rpm_trailing_slashes(cfg_production: list[MediaCategory]) -> None:
    """D-03e + Pitfall 6: both paths end with '/'."""
    result = generate_sonarr_resources(cfg_production)
    for rpm in result.remote_path_mappings:
        assert rpm.remotePath.endswith("/")
        assert rpm.localPath.endswith("/")
        assert rpm.host == "qbittorrent.selfhost.svc.cluster.local"
    # Spot check a specific entry:
    rpm_zoe = next(r for r in result.remote_path_mappings if "series-zoe" in r.remotePath)
    assert rpm_zoe.remotePath == "/data/series-zoe/"
    assert rpm_zoe.localPath == "/data/torrents/series-zoe/"


def test_generate_sonarr_resources_empty(cfg_empty: list[MediaCategory]) -> None:
    result = generate_sonarr_resources(cfg_empty)
    assert result.tags == []
    assert result.root_folders == []
    assert result.download_clients == []
    assert result.remote_path_mappings == []


# ===== Radarr =====


def test_generate_radarr_resources_5_each(cfg_production: list[MediaCategory]) -> None:
    """D-03b/c/d/e Radarr-side: 5 movies → 5 of each resource."""
    result = generate_radarr_resources(cfg_production)
    assert isinstance(result, RadarrDerived)
    assert len(result.tags) == 5
    assert len(result.root_folders) == 5
    assert len(result.download_clients) == 5
    assert len(result.remote_path_mappings) == 5


def test_generate_radarr_dc_movieCategory_field(cfg_production: list[MediaCategory]) -> None:
    """D-03b Radarr-side: fields[] contains movieCategory (NOT tvCategory)."""
    result = generate_radarr_resources(cfg_production)
    expected_names = [
        "films",
        "nouveaux-films",
        "films-enfants",
        "films-animation-enfants",
        "films-zoe",
    ]
    for dc, expected_name in zip(result.download_clients, expected_names, strict=True):
        movie_cat_field = next(f for f in dc.fields if f.name == "movieCategory")
        assert movie_cat_field.value == expected_name
        # Must NOT have Sonarr-only fields:
        assert not any(f.name == "tvCategory" for f in dc.fields)


def test_generate_radarr_resources_empty(cfg_empty: list[MediaCategory]) -> None:
    result = generate_radarr_resources(cfg_empty)
    assert result.tags == []
    assert result.root_folders == []
    assert result.download_clients == []
    assert result.remote_path_mappings == []


def test_generate_radarr_rpm_trailing_slashes(cfg_production: list[MediaCategory]) -> None:
    """Pitfall 6: Radarr RPMs also need trailing slashes."""
    result = generate_radarr_resources(cfg_production)
    for rpm in result.remote_path_mappings:
        assert rpm.remotePath.endswith("/")
        assert rpm.localPath.endswith("/")
        assert rpm.host == "qbittorrent.selfhost.svc.cluster.local"


# ===== Jellyfin =====


def test_generate_jellyfin_libraries_ten_libs(cfg_production: list[MediaCategory]) -> None:
    """REQ-jellyfin-categories-as-libs: 10 categories → 10 libs (D-16-LIB-CREATE-01)."""
    result = generate_jellyfin_libraries(cfg_production)
    assert len(result) == 10
    # First entry mirrors first Category in production fixture — Séries.
    assert result[0].name == "Séries"
    assert result[0].collection_type == "tvshows"
    assert result[0].paths == ["/media/series"]


def test_generate_jellyfin_paths_match_base_paths(cfg_production: list[MediaCategory]) -> None:
    """D-16-LIB-CREATE-01: each lib has exactly 1 PathInfo = categories[i].base_path."""
    result = generate_jellyfin_libraries(cfg_production)
    expected_paths = [
        "/media/series",
        "/media/series-emilie",
        "/media/series-thomas",
        "/media/series-garcons",
        "/media/series-zoe",
        "/media/films",
        "/media/nouveaux-films",
        "/media/films-enfants",
        "/media/films-animation-enfants",
        "/media/films-zoe",
    ]
    assert [lib.paths for lib in result] == [[p] for p in expected_paths]


def test_generate_jellyfin_all_series_no_movies() -> None:
    """D-16-LIB-CREATE-01: series-only cfg → only tvshows libs (no implicit empty Films)."""
    cats = _make_cats([c for c in PRODUCTION_CATEGORIES if c["kind"] == "series"])
    result = generate_jellyfin_libraries(cats)
    assert len(result) == 5
    assert all(lib.collection_type == "tvshows" for lib in result)


def test_generate_jellyfin_libraries_empty(cfg_empty: list[MediaCategory]) -> None:
    """D-16-LIB-CREATE-01: empty cfg → empty list (no implicit super-libs — Phase 16 reversal)."""
    result = generate_jellyfin_libraries(cfg_empty)
    assert result == []


# ===== animeTags =====


def test_generate_anime_tag_labels_production(cfg_production: list[MediaCategory]) -> None:
    """REQ-categories-seerr-routing: 2 anime categories in production (films-zoe + series-zoe)."""
    result = generate_anime_tag_labels(cfg_production)
    # Both anime-profile categories show up here; downstream filtering by kind
    # happens at the resolver step in 10-F.
    assert set(result) == {"films-zoe", "series-zoe"}


def test_generate_anime_tag_labels_empty(cfg_empty: list[MediaCategory]) -> None:
    assert generate_anime_tag_labels(cfg_empty) == []


# ===== Cross-case: order preservation =====


def test_order_preservation_qbit(cfg_production: list[MediaCategory]) -> None:
    """Categories ordering in cfg is preserved in qBit output (no sorting)."""
    result = generate_qbit_categories(cfg_production)
    names = [c.name for c in result]
    expected = [c["name"] for c in PRODUCTION_CATEGORIES]
    assert names == expected


def test_order_preservation_sonarr(cfg_production: list[MediaCategory]) -> None:
    """Series categories ordering preserved in Sonarr output (no sorting)."""
    result = generate_sonarr_resources(cfg_production)
    series_names = [c["name"] for c in PRODUCTION_CATEGORIES if c["kind"] == "series"]
    tag_labels = [t.label for t in result.tags]
    assert tag_labels == series_names


def test_generate_sonarr_dc_connection_constants(cfg_production: list[MediaCategory]) -> None:
    """Sonarr DCs use correct qBit connection constants."""
    result = generate_sonarr_resources(cfg_production)
    for dc in result.download_clients:
        assert dc.enable is True
        assert dc.protocol == "torrent"
        assert dc.priority == 1
        assert dc.removeCompletedDownloads is True
        assert dc.removeFailedDownloads is True
        host_field = next(f for f in dc.fields if f.name == "host")
        assert host_field.value == "qbittorrent.selfhost.svc.cluster.local"
        port_field = next(f for f in dc.fields if f.name == "port")
        assert port_field.value == 8080
