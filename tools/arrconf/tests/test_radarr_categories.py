"""Phase 10 wiring test: Categories->Radarr 4 resources (mirror of Sonarr test).

Validates that generate_radarr_resources delivers the right items to the 4 Radarr
resource slots (tags, root_folders, download_clients, remote_path_mappings).

Key difference from Sonarr: kind=="movies" filter, movieCategory FieldKV (not tvCategory).

NOT an HTTP integration test -- pure data-flow verification.
"""

from __future__ import annotations

from arrconf.generators.categories import generate_radarr_resources
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


def _build_cfg() -> list[MediaCategory]:
    return [MediaCategory.model_validate(c) for c in PRODUCTION_CATEGORIES]


def test_radarr_tags_wiring() -> None:
    cfg = _build_cfg()
    derived = generate_radarr_resources(cfg)
    assert len(derived.tags) == 5
    assert [t.label for t in derived.tags] == [
        "films",
        "nouveaux-films",
        "films-enfants",
        "films-animation-enfants",
        "films-zoe",
    ]


def test_radarr_root_folders_wiring() -> None:
    cfg = _build_cfg()
    derived = generate_radarr_resources(cfg)
    assert len(derived.root_folders) == 5
    assert [rf.path for rf in derived.root_folders] == [
        "/media/films",
        "/media/nouveaux-films",
        "/media/films-enfants",
        "/media/films-animation-enfants",
        "/media/films-zoe",
    ]


def test_radarr_download_clients_have_movieCategory() -> None:
    """D-03b Radarr-side: movieCategory FieldKV, NOT tvCategory."""
    cfg = _build_cfg()
    derived = generate_radarr_resources(cfg)
    assert len(derived.download_clients) == 5
    for dc in derived.download_clients:
        movie_cat = next((f for f in dc.fields if f.name == "movieCategory"), None)
        tv_cat = next((f for f in dc.fields if f.name == "tvCategory"), None)
        assert movie_cat is not None, f"DC {dc.name} missing movieCategory FieldKV"
        assert tv_cat is None, (
            f"DC {dc.name} unexpectedly has tvCategory FieldKV (should be Radarr-side)"
        )


def test_radarr_rpm_wiring() -> None:
    cfg = _build_cfg()
    derived = generate_radarr_resources(cfg)
    assert len(derived.remote_path_mappings) == 5
    for rpm in derived.remote_path_mappings:
        assert rpm.remotePath.endswith("/")
        assert rpm.localPath.endswith("/")
        assert rpm.host == "qbittorrent.selfhost.svc.cluster.local"


def test_radarr_no_movies_in_cfg() -> None:
    """If cfg has only series categories, Radarr derived containers are all empty."""
    cfg = [MediaCategory.model_validate(c) for c in PRODUCTION_CATEGORIES if c["kind"] == "series"]
    derived = generate_radarr_resources(cfg)
    assert derived.tags == []
    assert derived.root_folders == []
    assert derived.download_clients == []
    assert derived.remote_path_mappings == []
