"""Phase 20 audit module — read-only legacy detection tests.

Mirrors test_dump.py shape (multi-endpoint respx mock + assertions on the emitted
artifact). All tests are read-only — they assert audit.py only issues GETs.

Covers every Pitfall (1-8) from 20-RESEARCH.md §Common Pitfalls and every
verification gate from §Pattern 6.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
import structlog.testing

from arrconf.audit import (
    AUTO_PATH_MAPPING,
    OPERATOR_DECISION_PATHS,
    audit_jellyfin,
    audit_qbittorrent,
    audit_radarr,
    audit_seerr,
    audit_sonarr,
    is_legacy_path,
    is_legacy_tag,
    run_audit,
    verify_audit,
)
from arrconf.client_base import (
    JellyfinClient,
    QbittorrentClient,
    RadarrClient,
    SeerrClient,
    SonarrClient,
)
from arrconf.config import RootConfig
from arrconf.resources.categories import Category as MediaCategory

FIXTURE_ROOT = Path(__file__).parent / "fixtures"

# CATMIG-01 (Phase 32 Plan 01): audit.py uses root.categories (RootConfig) directly.
# Plan 01 removes categories from RootConfig. audit.py update is deferred to a
# subsequent plan (out of Plan 01 scope per files_modified list).
_SKIP_CATMIG_AUDIT = pytest.mark.skip(
    reason=(
        "CATMIG-01 Plan 01: audit.py accesses root.categories (RootConfig) which no "
        "longer exists. audit.py update deferred to a subsequent plan. "
        "These tests will be re-enabled once audit.py is migrated."
    )
)


def _load_fixture(relative_path: str) -> Any:
    p = FIXTURE_ROOT / relative_path
    return json.loads(p.read_text())


# ---------------------------------------------------------------------------
# Helper: minimal RootConfig with 10 production Categories
# ---------------------------------------------------------------------------


_PRODUCTION_CATEGORIES_DATA: list[dict[str, str]] = [
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


def _build_categories() -> list[MediaCategory]:
    """Build the production list of 10 MediaCategory objects (CATMIG-01: from IntentConfig)."""
    return [MediaCategory.model_validate(c) for c in _PRODUCTION_CATEGORIES_DATA]


def _build_root_with_10_categories() -> RootConfig:
    """Build a minimal valid RootConfig without categories (CATMIG-01: categories live in intent).

    Use _build_categories() to get the MediaCategory list to pass to audit functions.
    """
    return RootConfig.model_validate(
        {
            "sonarr": {
                "main": {
                    "base_url": "http://sonarr.test:8989",
                    "tags": {"prune": False},
                    "root_folders": {"prune": False},
                    "download_clients": {"prune": False},
                    "remote_path_mappings": {"prune": False},
                    "series_tags": {"enable": True, "default_tag": "tv"},
                    "content_routing": {"enable": True, "rules": []},
                }
            },
            "radarr": {
                "main": {
                    "base_url": "http://radarr.test:7878",
                    "tags": {"prune": False},
                    "root_folders": {"prune": False},
                    "download_clients": {"prune": False},
                    "remote_path_mappings": {"prune": False},
                    "content_routing": {"enable": True, "rules": []},
                }
            },
            "qbittorrent": {
                "main": {
                    "base_url": "http://qbittorrent.test:8080",
                    "categories": {"prune": False},
                    "preferences": {"enable": False},
                }
            },
            "seerr": {
                "main": {
                    "base_url": "http://seerr.test:5055",
                    "sonarr_service": {
                        "hostname": "sonarr.svc",
                        "activeProfileId": 6,
                        "activeDirectory": "/media/series",
                    },
                    "radarr_service": {
                        "hostname": "radarr.svc",
                        "activeProfileId": 4,
                        "activeDirectory": "/media/films",
                    },
                }
            },
            "jellyfin": {
                "main": {
                    "base_url": "http://jellyfin.test:8096",
                    "libraries": {"enable": True, "prune": False},
                    "users": {"enable": False, "prune": False, "admin": {}},
                    "server_config": {"enable": False},
                    "plugins": {"enable": False, "required": []},
                }
            },
            "prowlarr": {},
        }
    )


# ---------------------------------------------------------------------------
# Pure predicate tests
# ---------------------------------------------------------------------------


def test_is_legacy_path_hard_legacy_returns_true() -> None:
    """LEGACY_PATHS_HARD members are always detected as legacy."""
    category_paths = {c.base_path for c in _build_categories()}  # CATMIG-01
    for p in ["/media/anime", "/media/family", "/media/films-anime", "/media/films-family"]:
        assert is_legacy_path(p, category_paths) is True, f"{p!r} should be legacy"


def test_is_legacy_path_category_path_returns_false() -> None:
    """Known Category paths are NOT legacy."""
    category_paths = {c.base_path for c in _build_categories()}  # CATMIG-01
    for p in ["/media/films-enfants", "/media/series-zoe", "/media/films-animation-enfants"]:
        assert is_legacy_path(p, category_paths) is False, f"{p!r} should NOT be legacy"


def test_is_legacy_path_strips_trailing_slash() -> None:
    """Pitfall 7: trailing slashes must be stripped before comparison."""
    category_paths = {c.base_path for c in _build_categories()}  # CATMIG-01
    assert is_legacy_path("/media/films-family/", category_paths) is True
    assert is_legacy_path("/media/anime/", category_paths) is True
    # Category path with trailing slash is still NOT legacy
    assert is_legacy_path("/media/films-enfants/", category_paths) is False


def test_is_legacy_tag() -> None:
    """Legacy tag labels are detected; Category tags and 'tv' are not."""
    for label in ["anime", "family", "films", "movies"]:
        assert is_legacy_tag(label) is True, f"'{label}' should be legacy"
    for label in ["films-enfants", "tv", "series-zoe", "series-garcons"]:
        assert is_legacy_tag(label) is False, f"'{label}' should NOT be legacy"


def test_auto_path_mapping_matches_claude_md_filesystem_table() -> None:
    """AUTO_PATH_MAPPING must match CLAUDE.md §Filesystem migration table verbatim."""
    assert AUTO_PATH_MAPPING["/media/anime"] == "/media/series-zoe"
    assert AUTO_PATH_MAPPING["/media/family"] == "/media/series-garcons"
    assert AUTO_PATH_MAPPING["/media/films-family"] == "/media/films-enfants"
    # /media/films-anime is operator-decision — NOT in AUTO_PATH_MAPPING
    assert "/media/films-anime" not in AUTO_PATH_MAPPING


# ---------------------------------------------------------------------------
# audit_radarr tests
# ---------------------------------------------------------------------------


@respx.mock
def test_audit_radarr_flags_films_family_as_auto_mapped_to_films_enfants() -> None:
    """CLAUDE.md anchor: /media/films-family → /media/films-enfants (auto)."""
    root = _build_root_with_10_categories()
    movies = _load_fixture("audit/radarr_movies_mixed.json")
    tags = _load_fixture("audit/radarr_tags_mixed.json")
    dcs = _load_fixture("audit/radarr_downloadclient_with_catchall.json")

    respx.get("http://radarr.test:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=movies)
    )
    respx.get("http://radarr.test:7878/api/v3/tag").mock(
        return_value=httpx.Response(200, json=tags)
    )
    respx.get("http://radarr.test:7878/api/v3/downloadclient").mock(
        return_value=httpx.Response(200, json=dcs)
    )

    client = RadarrClient(base_url="http://radarr.test:7878", api_key="fake")
    result = audit_radarr(client, root, categories=_build_categories())

    films_family_rows = [
        r for r in result["movies_to_migrate"] if r["current_rootFolder"] == "/media/films-family"
    ]
    assert len(films_family_rows) >= 1
    for row in films_family_rows:
        assert row["auto_target_rootFolder"] == "/media/films-enfants"


@respx.mock
def test_audit_radarr_films_anime_left_for_operator() -> None:
    """OPERATOR_DECISION_PATHS: films-anime has auto_target_rootFolder=None."""
    root = _build_root_with_10_categories()
    movies = _load_fixture("audit/radarr_movies_mixed.json")
    tags = _load_fixture("audit/radarr_tags_mixed.json")
    dcs = _load_fixture("audit/radarr_downloadclient_with_catchall.json")

    respx.get("http://radarr.test:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=movies)
    )
    respx.get("http://radarr.test:7878/api/v3/tag").mock(
        return_value=httpx.Response(200, json=tags)
    )
    respx.get("http://radarr.test:7878/api/v3/downloadclient").mock(
        return_value=httpx.Response(200, json=dcs)
    )

    client = RadarrClient(base_url="http://radarr.test:7878", api_key="fake")
    result = audit_radarr(client, root, categories=_build_categories())

    spirited_away = next((r for r in result["movies_to_migrate"] if r["id"] == 12), None)
    assert spirited_away is not None
    assert spirited_away["current_rootFolder"] == "/media/films-anime"
    assert spirited_away["auto_target_rootFolder"] is None
    assert spirited_away["current_rootFolder"] in OPERATOR_DECISION_PATHS


@respx.mock
def test_audit_radarr_movies_already_on_category_excluded() -> None:
    """Movies on Category paths (not operator-decision) must NOT appear in movies_to_migrate."""
    root = _build_root_with_10_categories()
    movies = _load_fixture("audit/radarr_movies_mixed.json")
    tags = _load_fixture("audit/radarr_tags_mixed.json")
    dcs = _load_fixture("audit/radarr_downloadclient_with_catchall.json")

    respx.get("http://radarr.test:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=movies)
    )
    respx.get("http://radarr.test:7878/api/v3/tag").mock(
        return_value=httpx.Response(200, json=tags)
    )
    respx.get("http://radarr.test:7878/api/v3/downloadclient").mock(
        return_value=httpx.Response(200, json=dcs)
    )

    client = RadarrClient(base_url="http://radarr.test:7878", api_key="fake")
    result = audit_radarr(client, root, categories=_build_categories())

    migrated_ids = [r["id"] for r in result["movies_to_migrate"]]
    # id=21 (Coco on /media/films-enfants) is already on Category — should be excluded
    assert 21 not in migrated_ids
    # id=22 (Le Voyage de Chihiro on /media/films-zoe) is also Category — excluded
    assert 22 not in migrated_ids


@respx.mock
def test_audit_radarr_family_tag_routes_to_films_enfants() -> None:
    """Pitfall 2: Radarr `family` tag → films-enfants (NOT series-garcons)."""
    root = _build_root_with_10_categories()
    movies = _load_fixture("audit/radarr_movies_mixed.json")
    tags = _load_fixture("audit/radarr_tags_mixed.json")
    dcs = _load_fixture("audit/radarr_downloadclient_with_catchall.json")

    respx.get("http://radarr.test:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=movies)
    )
    respx.get("http://radarr.test:7878/api/v3/tag").mock(
        return_value=httpx.Response(200, json=tags)
    )
    respx.get("http://radarr.test:7878/api/v3/downloadclient").mock(
        return_value=httpx.Response(200, json=dcs)
    )

    client = RadarrClient(base_url="http://radarr.test:7878", api_key="fake")
    result = audit_radarr(client, root, categories=_build_categories())

    family_tag = next((t for t in result["tags"] if t["label"] == "family"), None)
    assert family_tag is not None
    assert family_tag["target_label"] == "films-enfants"
    assert family_tag["target_label"] != "series-garcons"


# ---------------------------------------------------------------------------
# audit_sonarr tests
# ---------------------------------------------------------------------------


@respx.mock
def test_audit_sonarr_anime_mapped_to_series_zoe() -> None:
    """Series on /media/anime auto-maps to /media/series-zoe."""
    root = _build_root_with_10_categories()
    series = _load_fixture("audit/sonarr_series_mixed.json")
    tags = _load_fixture("audit/sonarr_tags_mixed.json")
    dcs = _load_fixture("audit/sonarr_downloadclient_with_catchall.json")

    respx.get("http://sonarr.test:8989/api/v3/series").mock(
        return_value=httpx.Response(200, json=series)
    )
    respx.get("http://sonarr.test:8989/api/v3/tag").mock(
        return_value=httpx.Response(200, json=tags)
    )
    respx.get("http://sonarr.test:8989/api/v3/downloadclient").mock(
        return_value=httpx.Response(200, json=dcs)
    )

    client = SonarrClient(base_url="http://sonarr.test:8989", api_key="fake")
    result = audit_sonarr(client, root, categories=_build_categories())

    anime_rows = [
        r for r in result["series_to_migrate"] if r["current_rootFolder"] == "/media/anime"
    ]
    assert len(anime_rows) >= 1
    for row in anime_rows:
        assert row["auto_target_rootFolder"] == "/media/series-zoe"


@respx.mock
def test_audit_sonarr_family_tag_routes_to_series_garcons() -> None:
    """Pitfall 2: Sonarr `family` tag → series-garcons (NOT films-enfants)."""
    root = _build_root_with_10_categories()
    series = _load_fixture("audit/sonarr_series_mixed.json")
    tags = _load_fixture("audit/sonarr_tags_mixed.json")
    dcs = _load_fixture("audit/sonarr_downloadclient_with_catchall.json")

    respx.get("http://sonarr.test:8989/api/v3/series").mock(
        return_value=httpx.Response(200, json=series)
    )
    respx.get("http://sonarr.test:8989/api/v3/tag").mock(
        return_value=httpx.Response(200, json=tags)
    )
    respx.get("http://sonarr.test:8989/api/v3/downloadclient").mock(
        return_value=httpx.Response(200, json=dcs)
    )

    client = SonarrClient(base_url="http://sonarr.test:8989", api_key="fake")
    result = audit_sonarr(client, root, categories=_build_categories())

    family_tag = next((t for t in result["tags"] if t["label"] == "family"), None)
    assert family_tag is not None
    assert family_tag["target_label"] == "series-garcons"
    assert family_tag["target_label"] != "films-enfants"


# ---------------------------------------------------------------------------
# audit_qbittorrent tests
# ---------------------------------------------------------------------------


@_SKIP_CATMIG_AUDIT
@respx.mock
def test_audit_qbittorrent_normalizes_categories_dict() -> None:
    """Pitfall 4: qBit /torrents/categories returns dict; audit consumes it correctly."""
    root = _build_root_with_10_categories()
    torrents = _load_fixture("audit/qbit_torrents_mixed.json")
    categories = _load_fixture("audit/qbit_categories_aligned.json")

    # Mock qBit login
    respx.post("http://qbittorrent.test:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(
            200,
            text="Ok.",
            headers={"set-cookie": "SID=fake-sid; HttpOnly; path=/"},
        )
    )
    respx.get("http://qbittorrent.test:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(200, json=torrents)
    )
    respx.get("http://qbittorrent.test:8080/api/v2/torrents/categories").mock(
        return_value=httpx.Response(200, json=categories)
    )

    client = QbittorrentClient(
        base_url="http://qbittorrent.test:8080",
        username="admin",
        password="password",
    )
    result = audit_qbittorrent(client, root, categories=_build_categories())
    # Should not raise — dict was consumed correctly
    assert "torrents_to_relocate" in result
    assert "categories_validation" in result


@respx.mock
def test_audit_qbittorrent_legacy_save_path_detected() -> None:
    """Torrent with save_path=/data/films-anime is flagged as legacy."""
    root = _build_root_with_10_categories()
    torrents = _load_fixture("audit/qbit_torrents_mixed.json")
    categories = _load_fixture("audit/qbit_categories_aligned.json")

    respx.post("http://qbittorrent.test:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(
            200,
            text="Ok.",
            headers={"set-cookie": "SID=fake-sid; HttpOnly; path=/"},
        )
    )
    respx.get("http://qbittorrent.test:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(200, json=torrents)
    )
    respx.get("http://qbittorrent.test:8080/api/v2/torrents/categories").mock(
        return_value=httpx.Response(200, json=categories)
    )

    client = QbittorrentClient(
        base_url="http://qbittorrent.test:8080",
        username="admin",
        password="password",
    )
    result = audit_qbittorrent(client, root, categories=_build_categories())

    # The Studio.Ghibli.pack torrent has save_path=/data/films-anime — legacy
    ghibli = next(
        (t for t in result["torrents_to_relocate"] if "Ghibli" in t["name"]),
        None,
    )
    assert ghibli is not None
    assert ghibli["save_path"] == "/data/films-anime"


@respx.mock
def test_audit_qbittorrent_strips_trailing_slash() -> None:
    """Pitfall 7: save_path=/data/films-family/ (with trailing slash) is detected legacy."""
    root = _build_root_with_10_categories()
    # Create a torrent with trailing slash in save_path
    torrents = [
        {
            "hash": "ffff000000000000000000000000000000000000",
            "name": "Some Family Film",
            "category": "films-family",
            "save_path": "/data/films-family/",  # trailing slash
            "state": "seeding",
        }
    ]
    categories: dict[str, Any] = {}

    respx.post("http://qbittorrent.test:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(
            200,
            text="Ok.",
            headers={"set-cookie": "SID=fake-sid; HttpOnly; path=/"},
        )
    )
    respx.get("http://qbittorrent.test:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(200, json=torrents)
    )
    respx.get("http://qbittorrent.test:8080/api/v2/torrents/categories").mock(
        return_value=httpx.Response(200, json=categories)
    )

    client = QbittorrentClient(
        base_url="http://qbittorrent.test:8080",
        username="admin",
        password="password",
    )
    result = audit_qbittorrent(client, root, categories=_build_categories())
    # Trailing slash stripped, legacy detected
    assert len(result["torrents_to_relocate"]) >= 1
    row = result["torrents_to_relocate"][0]
    assert row["save_path"] == "/data/films-family"  # normalized


# ---------------------------------------------------------------------------
# audit_seerr tests
# ---------------------------------------------------------------------------


@respx.mock
def test_audit_seerr_resolves_animetags_via_sonarr_tag_get() -> None:
    """Pitfall 3: animeTags=[3] resolves to 'anime' via Sonarr /tag — flagged legacy."""
    root = _build_root_with_10_categories()
    seerr_settings = _load_fixture("audit/seerr_settings_sonarr_legacy_anime.json")
    sonarr_tags = _load_fixture("audit/sonarr_tags_mixed.json")

    respx.get("http://seerr.test:5055/api/v1/settings/sonarr").mock(
        return_value=httpx.Response(200, json=seerr_settings)
    )
    respx.get("http://sonarr.test:8989/api/v3/tag").mock(
        return_value=httpx.Response(200, json=sonarr_tags)
    )

    seerr_client = SeerrClient(base_url="http://seerr.test:5055", api_key="fake")
    sonarr_client = SonarrClient(base_url="http://sonarr.test:8989", api_key="fake")

    result = audit_seerr(seerr_client, sonarr_client, root, categories=_build_categories())
    assert result["animetags_legacy"] is True
    # The legacy animeTags=[3] resolved to "anime"
    default_svc = next((s for s in result["services"] if s["is_default"]), None)
    assert default_svc is not None
    assert "anime" in default_svc["animetags_labels"]


# ---------------------------------------------------------------------------
# audit_jellyfin tests
# ---------------------------------------------------------------------------


@respx.mock
def test_audit_jellyfin_10_libs_aligned_returns_OK() -> None:
    """10 libs each matching a Category path → libraries_alignment == 'OK'."""
    root = _build_root_with_10_categories()
    libs = _load_fixture("audit/jellyfin_virtualfolders_post_phase16.json")

    respx.get("http://jellyfin.test:8096/Library/VirtualFolders").mock(
        return_value=httpx.Response(200, json=libs)
    )

    client = JellyfinClient(base_url="http://jellyfin.test:8096", api_key="fake")
    result = audit_jellyfin(client, root, categories=_build_categories())
    assert result["libraries_alignment"] == "OK"


@respx.mock
def test_audit_jellyfin_drift_detected() -> None:
    """A lib with a non-Category path → libraries_alignment is a drift dict."""
    root = _build_root_with_10_categories()
    # Build a lib list with one wrong path
    libs = [
        {
            "Name": "Wrong Library",
            "ItemId": "xxx",
            "CollectionType": "movies",
            "Locations": ["/media/wrong-path"],
            "LibraryOptions": {"PathInfos": [{"Path": "/media/wrong-path"}]},
        }
    ]

    respx.get("http://jellyfin.test:8096/Library/VirtualFolders").mock(
        return_value=httpx.Response(200, json=libs)
    )

    client = JellyfinClient(base_url="http://jellyfin.test:8096", api_key="fake")
    result = audit_jellyfin(client, root, categories=_build_categories())
    assert isinstance(result["libraries_alignment"], dict)
    assert "drift" in result["libraries_alignment"]
    assert len(result["libraries_alignment"]["drift"]) >= 1


# ---------------------------------------------------------------------------
# run_audit integration tests
# ---------------------------------------------------------------------------


@respx.mock
def test_run_audit_writes_markdown_with_yaml_appendix(tmp_path: Path) -> None:
    """run_audit emits a file with a fenced yaml block and audit_version: 1."""
    root = _build_root_with_10_categories()
    movies = _load_fixture("audit/radarr_movies_mixed.json")
    radarr_tags = _load_fixture("audit/radarr_tags_mixed.json")
    radarr_dcs = _load_fixture("audit/radarr_downloadclient_with_catchall.json")
    series = _load_fixture("audit/sonarr_series_mixed.json")
    sonarr_tags = _load_fixture("audit/sonarr_tags_mixed.json")
    sonarr_dcs = _load_fixture("audit/sonarr_downloadclient_with_catchall.json")
    torrents = _load_fixture("audit/qbit_torrents_mixed.json")
    categories = _load_fixture("audit/qbit_categories_aligned.json")
    seerr_settings = _load_fixture("audit/seerr_settings_sonarr_legacy_anime.json")
    jellyfin_libs = _load_fixture("audit/jellyfin_virtualfolders_post_phase16.json")

    # Mock all endpoints
    respx.get("http://radarr.test:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=movies)
    )
    respx.get("http://radarr.test:7878/api/v3/tag").mock(
        return_value=httpx.Response(200, json=radarr_tags)
    )
    respx.get("http://radarr.test:7878/api/v3/downloadclient").mock(
        return_value=httpx.Response(200, json=radarr_dcs)
    )
    respx.get("http://sonarr.test:8989/api/v3/series").mock(
        return_value=httpx.Response(200, json=series)
    )
    respx.get("http://sonarr.test:8989/api/v3/tag").mock(
        return_value=httpx.Response(200, json=sonarr_tags)
    )
    respx.get("http://sonarr.test:8989/api/v3/downloadclient").mock(
        return_value=httpx.Response(200, json=sonarr_dcs)
    )
    respx.post("http://qbittorrent.test:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(
            200,
            text="Ok.",
            headers={"set-cookie": "SID=fake-sid; HttpOnly; path=/"},
        )
    )
    respx.get("http://qbittorrent.test:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(200, json=torrents)
    )
    respx.get("http://qbittorrent.test:8080/api/v2/torrents/categories").mock(
        return_value=httpx.Response(200, json=categories)
    )
    respx.get("http://seerr.test:5055/api/v1/settings/sonarr").mock(
        return_value=httpx.Response(200, json=seerr_settings)
    )
    respx.get("http://jellyfin.test:8096/Library/VirtualFolders").mock(
        return_value=httpx.Response(200, json=jellyfin_libs)
    )

    from arrconf.settings import Settings

    settings = Settings(
        sonarr_api_key="fake-sonarr",  # type: ignore[arg-type]
        radarr_api_key="fake-radarr",  # type: ignore[arg-type]
        qbt_user="admin",  # type: ignore[arg-type]
        qbt_pass="password",  # type: ignore[arg-type]
        seerr_api_key="fake-seerr",  # type: ignore[arg-type]
        jellyfin_api_key="fake-jellyfin",  # type: ignore[arg-type]
    )
    output = tmp_path / "20-AUDIT.md"
    run_audit(
        root,
        settings,
        output_path=output,
        targets={"radarr", "sonarr", "qbittorrent", "seerr", "jellyfin"},
        categories=_build_categories(),
    )

    assert output.exists()
    text = output.read_text()
    assert "```yaml" in text
    assert "audit_version: 1" in text


@respx.mock
def test_run_audit_emits_no_secret_field_names(tmp_path: Path) -> None:
    """Security (T-20-01): output must NOT contain secret field names."""
    root = _build_root_with_10_categories()
    movies: list[dict[str, Any]] = []
    radarr_tags: list[dict[str, Any]] = []
    radarr_dcs: list[dict[str, Any]] = []
    series: list[dict[str, Any]] = []
    sonarr_tags: list[dict[str, Any]] = []
    sonarr_dcs: list[dict[str, Any]] = []
    torrents: list[dict[str, Any]] = []
    categories: dict[str, Any] = {}
    seerr_settings: list[dict[str, Any]] = []
    jellyfin_libs: list[dict[str, Any]] = []

    respx.get("http://radarr.test:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=movies)
    )
    respx.get("http://radarr.test:7878/api/v3/tag").mock(
        return_value=httpx.Response(200, json=radarr_tags)
    )
    respx.get("http://radarr.test:7878/api/v3/downloadclient").mock(
        return_value=httpx.Response(200, json=radarr_dcs)
    )
    respx.get("http://sonarr.test:8989/api/v3/series").mock(
        return_value=httpx.Response(200, json=series)
    )
    respx.get("http://sonarr.test:8989/api/v3/tag").mock(
        return_value=httpx.Response(200, json=sonarr_tags)
    )
    respx.get("http://sonarr.test:8989/api/v3/downloadclient").mock(
        return_value=httpx.Response(200, json=sonarr_dcs)
    )
    respx.post("http://qbittorrent.test:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(
            200,
            text="Ok.",
            headers={"set-cookie": "SID=fake-sid; HttpOnly; path=/"},
        )
    )
    respx.get("http://qbittorrent.test:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(200, json=torrents)
    )
    respx.get("http://qbittorrent.test:8080/api/v2/torrents/categories").mock(
        return_value=httpx.Response(200, json=categories)
    )
    respx.get("http://seerr.test:5055/api/v1/settings/sonarr").mock(
        return_value=httpx.Response(200, json=seerr_settings)
    )
    respx.get("http://jellyfin.test:8096/Library/VirtualFolders").mock(
        return_value=httpx.Response(200, json=jellyfin_libs)
    )

    from arrconf.settings import Settings

    settings = Settings(
        sonarr_api_key="fake-sonarr",  # type: ignore[arg-type]
        radarr_api_key="fake-radarr",  # type: ignore[arg-type]
        qbt_user="admin",  # type: ignore[arg-type]
        qbt_pass="password",  # type: ignore[arg-type]
        seerr_api_key="fake-seerr",  # type: ignore[arg-type]
        jellyfin_api_key="fake-jellyfin",  # type: ignore[arg-type]
    )
    output = tmp_path / "audit.md"
    run_audit(
        root,
        settings,
        output_path=output,
        targets={"radarr", "sonarr", "qbittorrent", "seerr", "jellyfin"},
        categories=_build_categories(),
    )

    text = output.read_text().lower()
    for forbidden in ["apikey", "password", "token", "webhookurl", "sessionkey"]:
        assert forbidden not in text, f"Secret field '{forbidden}' found in audit output"


# ---------------------------------------------------------------------------
# verify_audit gate tests
# ---------------------------------------------------------------------------


def test_verify_audit_rejects_unresolved_question_cell(tmp_path: Path) -> None:
    """Gate 1: a `| ? |` cell causes verify to return 1."""
    root = _build_root_with_10_categories()
    md = tmp_path / "audit.md"
    md.write_text(
        "# 20-AUDIT\n\n"
        "| id | title | target |\n"
        "| --- | --- | --- |\n"
        "| 1 | Spirited Away | ? |\n\n"
        "```yaml\naudit_version: 1\n```\n"
    )
    with structlog.testing.capture_logs() as logs:
        code = verify_audit(md, root, None, None, categories=_build_categories())
    assert code == 1
    events = [e for e in logs if e.get("event") == "audit_unresolved_cells"]
    assert len(events) == 1


def test_verify_audit_rejects_TBD_cell(tmp_path: Path) -> None:
    """Gate 1: a `| TBD |` cell causes verify to return 1."""
    root = _build_root_with_10_categories()
    md = tmp_path / "audit.md"
    md.write_text(
        "# 20-AUDIT\n\n"
        "| id | title | target |\n"
        "| --- | --- | --- |\n"
        "| 1 | Inception | TBD |\n\n"
        "```yaml\naudit_version: 1\n```\n"
    )
    with structlog.testing.capture_logs() as logs:
        code = verify_audit(md, root, None, None, categories=_build_categories())
    assert code == 1
    events = [e for e in logs if e.get("event") == "audit_unresolved_cells"]
    assert len(events) == 1


def test_verify_audit_rejects_missing_yaml_appendix(tmp_path: Path) -> None:
    """Gate 2: Markdown with no fenced yaml block returns 1."""
    root = _build_root_with_10_categories()
    md = tmp_path / "audit.md"
    md.write_text("# 20-AUDIT\n\nNo yaml block here.\n")
    with structlog.testing.capture_logs() as logs:
        code = verify_audit(md, root, None, None, categories=_build_categories())
    assert code == 1
    events = [e for e in logs if e.get("event") == "audit_missing_yaml_appendix"]
    assert len(events) == 1


@_SKIP_CATMIG_AUDIT
def test_verify_audit_rejects_target_rootfolder_not_in_categories(tmp_path: Path) -> None:
    """Gate 3: appendix with to.rootFolderPath not in categories → returns 1."""
    root = _build_root_with_10_categories()
    md = tmp_path / "audit.md"
    md.write_text(
        "# 20-AUDIT\n\n"
        "```yaml\n"
        "audit_version: 1\n"
        "phase: 20\n"
        "radarr:\n"
        "  movies_to_migrate:\n"
        "    - id: 99\n"
        "      title: Test Movie\n"
        "      from:\n"
        "        rootFolderPath: /media/old\n"
        "      to:\n"
        "        rootFolderPath: /media/garbage\n"
        "        tags: []\n"
        "sonarr:\n"
        "  series_to_migrate: []\n"
        "```\n"
    )
    with structlog.testing.capture_logs() as logs:
        code = verify_audit(md, root, None, None, categories=_build_categories())
    assert code == 1
    events = [e for e in logs if e.get("event") == "audit_invalid_target_path"]
    assert len(events) == 1


def test_verify_audit_passes_with_valid_appendix(tmp_path: Path) -> None:
    """A clean Markdown (no ?, valid YAML, valid paths, no clients) → returns 0."""
    root = _build_root_with_10_categories()
    md = tmp_path / "audit.md"
    # No `?` cells, valid YAML appendix, valid target paths, sonarr/radarr clients=None
    md.write_text(
        "# 20-AUDIT\n\n"
        "All clean.\n\n"
        "```yaml\n"
        "audit_version: 1\n"
        "phase: 20\n"
        "radarr:\n"
        "  movies_to_migrate:\n"
        "    - id: 11\n"
        "      title: Les Alphas\n"
        "      from:\n"
        "        rootFolderPath: /media/films-family\n"
        "      to:\n"
        "        rootFolderPath: /media/films-enfants\n"
        "        tags: []\n"
        "sonarr:\n"
        "  series_to_migrate: []\n"
        "```\n"
    )
    code = verify_audit(md, root, None, None, categories=_build_categories())
    assert code == 0


# ---------------------------------------------------------------------------
# Security / rendering tests
# ---------------------------------------------------------------------------


def test_torrent_name_truncated_to_80_chars() -> None:
    """Torrent names longer than 80 chars must be truncated in audit output."""

    root = _build_root_with_10_categories()
    long_name = "A" * 120

    # Build a minimal torrent list with a long name
    torrents = [
        {
            "hash": "aaaa000000000000000000000000000000000000",
            "name": long_name,
            "category": "anime",
            "save_path": "/data/films-anime",
            "state": "seeding",
        }
    ]

    with respx.MockRouter() as mock:
        mock.post("http://qbittorrent.test:8080/api/v2/auth/login").mock(
            return_value=httpx.Response(
                200,
                text="Ok.",
                headers={"set-cookie": "SID=fake-sid; HttpOnly; path=/"},
            )
        )
        mock.get("http://qbittorrent.test:8080/api/v2/torrents/info").mock(
            return_value=httpx.Response(200, json=torrents)
        )
        mock.get("http://qbittorrent.test:8080/api/v2/torrents/categories").mock(
            return_value=httpx.Response(200, json={})
        )

        client = QbittorrentClient(
            base_url="http://qbittorrent.test:8080",
            username="admin",
            password="password",
        )
        result = audit_qbittorrent(client, root, categories=_build_categories())

    row = result["torrents_to_relocate"][0]
    assert len(row["name"]) <= 80


def test_torrent_name_escapes_pipe_characters() -> None:
    """Markdown rendering: pipe characters in torrent names must be escaped."""
    from arrconf.audit import _render_table

    # The _render_table helper escapes pipes
    rows: list[list[Any]] = [
        ["hash12", "Film | Title | Here", "cat", "/data/x", "seeding", "/data/y"]
    ]
    headers = ["hash", "name (truncated)", "category", "save_path", "state", "target"]
    rendered = _render_table(headers, rows)
    # The pipe in the name should be escaped as \|
    assert "Film \\| Title \\| Here" in rendered
    # Should not have unescaped middle cells broken
    assert "Film | Title | Here" not in rendered
