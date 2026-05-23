"""Semantic diff: 7 cases covering categories add/remove/modify + per-section changes."""

from __future__ import annotations

from typing import Any

from arrconf_ui.diff import diff_configs, has_changes


def _base() -> dict[str, Any]:
    return {
        "categories": [
            {
                "name": "series",
                "kind": "series",
                "profile": "general",
                "display": "Séries",
                "base_path": "/media/series",
            },
            {
                "name": "films",
                "kind": "movies",
                "profile": "general",
                "display": "Films",
                "base_path": "/media/films",
            },
        ],
        "sonarr": {"main": {"base_url": "http://sonarr:8989", "tags": {"prune": False}}},
        "radarr": {"main": {"base_url": "http://radarr:7878"}},
        "prowlarr": {},
        "qbittorrent": {},
        "seerr": {},
        "jellyfin": {},
    }


def test_empty_diff_when_identical() -> None:
    a = _base()
    b = _base()
    diff = diff_configs(a, b)
    assert diff["categories"] == {"added": [], "modified": [], "removed": []}
    for section in ("sonarr.main", "radarr.main"):
        assert diff[section]["changed_fields"] == []
    assert has_changes(diff) is False


def test_category_added() -> None:
    a = _base()
    b = _base()
    b["categories"].append(
        {
            "name": "series-zoe",
            "kind": "series",
            "profile": "anime",
            "display": "Séries - Zoé",
            "base_path": "/media/series-zoe",
        }
    )
    diff = diff_configs(a, b)
    assert diff["categories"]["added"] == ["series-zoe"]
    assert diff["categories"]["modified"] == []
    assert diff["categories"]["removed"] == []
    assert has_changes(diff) is True


def test_category_removed() -> None:
    a = _base()
    b = _base()
    b["categories"] = [c for c in b["categories"] if c["name"] != "films"]
    diff = diff_configs(a, b)
    assert diff["categories"]["removed"] == ["films"]


def test_category_modified() -> None:
    a = _base()
    b = _base()
    b["categories"][0]["display"] = "Séries v2"
    diff = diff_configs(a, b)
    assert diff["categories"]["modified"] == ["series"]


def test_sonarr_field_changed() -> None:
    a = _base()
    b = _base()
    b["sonarr"]["main"]["tags"]["prune"] = True
    diff = diff_configs(a, b)
    assert "sonarr.main.tags.prune" in diff["sonarr.main"]["changed_fields"]


def test_categories_reordered_no_change() -> None:
    """Reordering same categories (matched by name) MUST NOT register as modified."""
    a = _base()
    b = _base()
    b["categories"] = list(reversed(b["categories"]))
    diff = diff_configs(a, b)
    assert diff["categories"]["added"] == []
    assert diff["categories"]["modified"] == []
    assert diff["categories"]["removed"] == []


def test_new_section_added() -> None:
    """Adding a qbittorrent.main where there was none shows up as changed_fields."""
    a = _base()
    b = _base()
    b["qbittorrent"]["main"] = {"base_url": "http://qbit:8080"}
    diff = diff_configs(a, b)
    assert "qbittorrent.main.base_url" in diff["qbittorrent.main"]["changed_fields"]
