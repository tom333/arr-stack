"""Phase 10 wiring test: Categories->Sonarr 4 resources via merge_with_manual.

Validates that generate_sonarr_resources + merge_with_manual deliver the right
items to the 4 Sonarr resource slots (tags, root_folders, download_clients,
remote_path_mappings) under both "manual empty" and "manual non-empty" toggles.

NOT an HTTP integration test -- pure data-flow verification.
"""

from __future__ import annotations

from arrconf.config import RootConfig, TagItem
from arrconf.generators.categories import generate_sonarr_resources
from arrconf.reconcilers._shared import merge_with_manual
from arrconf.resources.sonarr.remote_path_mapping import RemotePathMapping

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


def test_sonarr_tags_wiring_empty_manual() -> None:
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    merged = merge_with_manual([], derived.tags, app="sonarr", resource="tags")
    assert len(merged) == 5
    labels = [t.label for t in merged]
    assert labels == [
        "series",
        "series-emilie",
        "series-thomas",
        "series-garcons",
        "series-zoe",
    ]


def test_sonarr_root_folders_wiring_empty_manual() -> None:
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    merged = merge_with_manual([], derived.root_folders, app="sonarr", resource="root_folders")
    assert len(merged) == 5
    paths = [rf.path for rf in merged]
    assert paths == [
        "/media/series",
        "/media/series-emilie",
        "/media/series-thomas",
        "/media/series-garcons",
        "/media/series-zoe",
    ]


def test_sonarr_download_clients_wiring_empty_manual() -> None:
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    merged = merge_with_manual(
        [],
        derived.download_clients,
        app="sonarr",
        resource="download_clients",
    )
    assert len(merged) == 5
    for dc in merged:
        assert dc.implementation == "QBittorrent"
        assert dc.configContract == "QBittorrentSettings"
        assert len(dc.tag_labels) == 1


def test_sonarr_rpm_wiring_empty_manual() -> None:
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    merged = merge_with_manual(
        [],
        derived.remote_path_mappings,
        app="sonarr",
        resource="remote_path_mappings",
    )
    assert len(merged) == 5
    for rpm in merged:
        assert rpm.remotePath.endswith("/")
        assert rpm.localPath.endswith("/")
        assert rpm.host == "qbittorrent.selfhost.svc.cluster.local"


def test_sonarr_per_resource_override_tags_only() -> None:
    """Manual tags + empty root_folders -> tags survives manual, root_folders gets Categories."""
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    manual_tags = [TagItem(label="tv"), TagItem(label="anime"), TagItem(label="family")]
    merged_tags = merge_with_manual(manual_tags, derived.tags, app="sonarr", resource="tags")
    merged_rf = merge_with_manual(
        [],
        derived.root_folders,
        app="sonarr",
        resource="root_folders",
    )
    assert len(merged_tags) == 3  # manual wins
    assert [t.label for t in merged_tags] == ["tv", "anime", "family"]
    assert len(merged_rf) == 5  # generated wins (root_folders manual was empty)


def test_sonarr_per_resource_override_rpm_only() -> None:
    """Manual RPM + empty download_clients -> RPM keeps manual, DCs get Categories."""
    cfg = _build_cfg()
    derived = generate_sonarr_resources(cfg)
    manual_rpm = [RemotePathMapping(host="x", remotePath="/legacy/", localPath="/data/legacy/")]
    merged_rpm = merge_with_manual(
        manual_rpm,
        derived.remote_path_mappings,
        app="sonarr",
        resource="remote_path_mappings",
    )
    merged_dc = merge_with_manual(
        [],
        derived.download_clients,
        app="sonarr",
        resource="download_clients",
    )
    assert len(merged_rpm) == 1
    assert merged_rpm[0].remotePath == "/legacy/"
    assert len(merged_dc) == 5
