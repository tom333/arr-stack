"""Phase 10 wiring test: Categories->Sonarr 4 resources.

Validates that generate_sonarr_resources delivers the right items to the 4 Sonarr
resource slots (tags, root_folders, download_clients, remote_path_mappings).

NOT an HTTP integration test -- pure data-flow verification.
"""

from __future__ import annotations

from arrconf.generators.categories import generate_sonarr_resources
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


def test_sonarr_tags_wiring() -> None:
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    assert len(derived.tags) == 5
    labels = [t.label for t in derived.tags]
    assert labels == [
        "series",
        "series-emilie",
        "series-thomas",
        "series-garcons",
        "series-zoe",
    ]


def test_sonarr_root_folders_wiring() -> None:
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    assert len(derived.root_folders) == 5
    paths = [rf.path for rf in derived.root_folders]
    assert paths == [
        "/media/series",
        "/media/series-emilie",
        "/media/series-thomas",
        "/media/series-garcons",
        "/media/series-zoe",
    ]


def test_sonarr_download_clients_wiring() -> None:
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    assert len(derived.download_clients) == 5
    for dc in derived.download_clients:
        assert dc.implementation == "QBittorrent"
        assert dc.configContract == "QBittorrentSettings"
        assert len(dc.tag_labels) == 1


def test_sonarr_rpm_wiring() -> None:
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    assert len(derived.remote_path_mappings) == 5
    for rpm in derived.remote_path_mappings:
        assert rpm.remotePath.endswith("/")
        assert rpm.localPath.endswith("/")
        assert rpm.host == "qbittorrent.selfhost.svc.cluster.local"
