"""Tests for arrconf.reconcilers.radarr.reconcile_radarr — REQ-app-coverage.

All HTTP mocked via respx. Coverage gate enforced via pyproject.toml — the
arrconf.reconcilers.radarr module is listed in [tool.coverage.run] source
since Plan 01 (Task 1.3).

Plan 04 deliberately does NOT extend conftest.py to keep Wave 3 plans
parallelizable (Plan 03 owns conftest.py changes for the Sonarr fixtures;
Plan 05 likewise loads its fixtures inline). Fixtures are loaded inline via
the FIXTURE_ROOT helper.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
import structlog.testing

from arrconf.client_base import RadarrClient
from arrconf.config import (
    DownloadClientsSection,
    HostConfigSection,
    IndexersSection,
    MovieTagsSection,
    NotificationsSection,
    RadarrInstance,
    RootFoldersSection,
    TagItem,
    TagsSection,
)
from arrconf.differ import Action
from arrconf.reconcilers.radarr import reconcile_radarr
from arrconf.resources.sonarr.download_client import DownloadClient
from arrconf.resources.sonarr.indexer import Indexer
from arrconf.resources.sonarr.notification import Notification
from arrconf.resources.sonarr.root_folder import RootFolder

RADARR_BASE = "http://radarr.test"
FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "radarr"


def _load(name: str) -> Any:
    return json.loads((FIXTURE_ROOT / name).read_text())


def _build_dc(name: str = "qbit", **overrides: Any) -> DownloadClient:
    defaults: dict[str, Any] = {
        "protocol": "torrent",
        "implementation": "QBittorrent",
        "configContract": "QBittorrentSettings",
    }
    defaults.update(overrides)
    return DownloadClient(name=name, **defaults)


def _mock_radarr_gets(
    respx_mock: respx.MockRouter,
    *,
    tag: list[dict[str, Any]] | None = None,
    indexers: list[dict[str, Any]] | None = None,
    rootfolders: list[dict[str, Any]] | None = None,
    downloadclients: list[dict[str, Any]] | None = None,
    notifications: list[dict[str, Any]] | None = None,
    hostconfig: dict[str, Any] | None = None,
    remotepathmappings: list[dict[str, Any]] | None = None,
    movies: list[dict[str, Any]] | None = None,
) -> None:
    """Mock every GET endpoint reconcile_radarr touches.

    Phase-5 additions: /remotepathmapping and /movie are always mocked (default
    empty) because the Phase-5 reconciler calls these in every run.
    """
    respx_mock.get("/tag").mock(
        return_value=httpx.Response(
            200, json=tag if tag is not None else _load("tag_with_arrconf_managed.json")
        )
    )
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=indexers or []))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=rootfolders or []))
    respx_mock.get("/downloadclient").mock(
        return_value=httpx.Response(200, json=downloadclients or [])
    )
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=notifications or []))
    respx_mock.get("/remotepathmapping").mock(
        return_value=httpx.Response(200, json=remotepathmappings or [])
    )
    respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=movies or []))
    if hostconfig is not None:
        respx_mock.get("/config/host").mock(return_value=httpx.Response(200, json=hostconfig))


# ---------------------------------------------------------------------------
# Scope guard smoke — defense against a module-load regression from Plan 02.
# ---------------------------------------------------------------------------


def test_scope_guard_imports_ok() -> None:
    """Smoke: importing the 4 Radarr frontière modules must succeed (Plan 02 contract)."""
    from arrconf.resources.radarr import (  # noqa: F401
        custom_format,
        media_naming,
        quality_definition,
        quality_profile,
    )

    for mod in (custom_format, media_naming, quality_definition, quality_profile):
        assert callable(mod.reconcile), f"{mod.__name__} must expose reconcile()"


# ---------------------------------------------------------------------------
# Download clients (Phase 1 parity for Radarr).
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_add_new_download_client(respx_mock: respx.MockRouter) -> None:
    _mock_radarr_gets(respx_mock)
    post_route = respx_mock.post("/downloadclient").mock(
        return_value=httpx.Response(201, json={"id": 7, "name": "qbit"})
    )

    desired = [_build_dc("qbit")]
    instance = RadarrInstance(
        base_url=RADARR_BASE,
        download_clients=DownloadClientsSection(prune=False, items=desired),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)

    assert post_route.call_count == 1
    body = post_route.calls.last.request.content.decode()
    assert '"tags":[1]' in body or '"tags": [1]' in body


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_update_existing_download_client_uses_forceSave(  # noqa: N802
    respx_mock: respx.MockRouter,
) -> None:
    """ADR-8 / D-02.2-01: every UPDATE PUT carries ?forceSave=true on Radarr too."""
    fixture = _load("downloadclient.json")
    _mock_radarr_gets(respx_mock, downloadclients=fixture)
    put_route = respx_mock.put(
        url__regex=rf"^{RADARR_BASE}/api/v3/downloadclient/\d+(?:\?.*)?$"
    ).mock(return_value=httpx.Response(200, json={"id": 1, "name": "qBittorrent"}))

    drifted = dict(fixture[0])
    drifted["priority"] = 99
    drifted["tags"] = [1]
    desired = [DownloadClient.model_validate(drifted)]
    instance = RadarrInstance(
        base_url=RADARR_BASE,
        download_clients=DownloadClientsSection(prune=False, items=desired),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)

    assert put_route.call_count == 1
    assert put_route.calls.last.request.url.params["forceSave"] == "true"


# ---------------------------------------------------------------------------
# Indexers.
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_add_new_indexer(respx_mock: respx.MockRouter) -> None:
    _mock_radarr_gets(respx_mock)
    post_route = respx_mock.post("/indexer").mock(
        return_value=httpx.Response(201, json={"id": 42, "name": "myindexer"})
    )
    indexer = Indexer(name="myindexer", implementation="Newznab", configContract="NewznabSettings")
    instance = RadarrInstance(
        base_url=RADARR_BASE,
        indexers=IndexersSection(prune=False, items=[indexer]),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)
    assert post_route.call_count == 1


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_indexer_no_op_when_identical(respx_mock: respx.MockRouter) -> None:
    fixture = _load("indexer.json")
    _mock_radarr_gets(respx_mock, indexers=fixture)
    put_route = respx_mock.put(url__regex=rf"^{RADARR_BASE}/api/v3/indexer/\d+(?:\?.*)?$")
    desired = [Indexer.model_validate(e) for e in fixture]
    instance = RadarrInstance(
        base_url=RADARR_BASE,
        indexers=IndexersSection(prune=False, items=desired),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)
    assert put_route.call_count == 0


# ---------------------------------------------------------------------------
# Notifications.
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_add_new_notification(respx_mock: respx.MockRouter) -> None:
    _mock_radarr_gets(respx_mock)
    post_route = respx_mock.post("/notification").mock(
        return_value=httpx.Response(201, json={"id": 7, "name": "discord-main"})
    )
    notif = Notification(
        name="discord-main", implementation="Discord", configContract="DiscordSettings"
    )
    instance = RadarrInstance(
        base_url=RADARR_BASE,
        notifications=NotificationsSection(prune=False, items=[notif]),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)
    assert post_route.call_count == 1


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_radarr_specific_notification_on_movie_added_parses(
    respx_mock: respx.MockRouter,
) -> None:
    """Radarr-specific on* fields (onMovieAdded, onMovieFileDelete) must survive extra=allow."""
    fixture = _load("notification.json")
    if not fixture:
        fixture = [
            {
                "id": 1,
                "name": "discord-main",
                "implementation": "Discord",
                "configContract": "DiscordSettings",
                "fields": [],
                "tags": [],
                "onMovieAdded": True,
                "onMovieFileDelete": False,
            }
        ]
    _mock_radarr_gets(respx_mock, notifications=fixture)
    desired = [Notification.model_validate(e) for e in fixture]
    put_route = respx_mock.put(url__regex=rf"^{RADARR_BASE}/api/v3/notification/\d+(?:\?.*)?$")
    instance = RadarrInstance(
        base_url=RADARR_BASE,
        notifications=NotificationsSection(prune=False, items=desired),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)
    assert put_route.call_count == 0


# ---------------------------------------------------------------------------
# Root folders (Pitfall 1 guard).
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_add_new_root_folder(respx_mock: respx.MockRouter) -> None:
    _mock_radarr_gets(respx_mock)
    post_route = respx_mock.post("/rootfolder").mock(
        return_value=httpx.Response(201, json={"id": 3, "path": "/media/movies-new"})
    )
    rf = RootFolder(path="/media/movies-new")
    instance = RadarrInstance(
        base_url=RADARR_BASE,
        root_folders=RootFoldersSection(prune=False, items=[rf]),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)
    assert post_route.call_count == 1


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_root_folder_no_update_action_ever(respx_mock: respx.MockRouter) -> None:
    """Pitfall 1: root folders have no PUT endpoint."""
    fixture = _load("rootfolder.json")
    _mock_radarr_gets(respx_mock, rootfolders=fixture)
    put_route = respx_mock.put(url__regex=rf"^{RADARR_BASE}/api/v3/rootfolder/\d+(?:\?.*)?$")
    desired = [RootFolder.model_validate(e) for e in fixture]
    instance = RadarrInstance(
        base_url=RADARR_BASE,
        root_folders=RootFoldersSection(prune=False, items=desired),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)
    assert put_route.call_count == 0, "Pitfall 1: root folders must never receive a PUT"


# ---------------------------------------------------------------------------
# host_config (D-03-04 opt-in).
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_host_config_skipped_when_enable_false(respx_mock: respx.MockRouter) -> None:
    """D-03-04: enable=False → no GET /config/host issued."""
    _mock_radarr_gets(respx_mock)
    get_host = respx_mock.get("/config/host")
    instance = RadarrInstance(
        base_url=RADARR_BASE,
        host_config=HostConfigSection(enable=False),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)
    assert get_host.call_count == 0


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_host_config_update_when_different(respx_mock: respx.MockRouter) -> None:
    """D-03-04: instanceName drift → PUT with forceSave + id; no credential leak."""
    fixture = _load("config_host.json")
    _mock_radarr_gets(respx_mock, hostconfig=fixture)
    put_host = respx_mock.put(url__regex=rf"^{RADARR_BASE}/api/v3/config/host/\d+(?:\?.*)?$").mock(
        return_value=httpx.Response(200, json={"id": fixture.get("id", 1)})
    )

    section = HostConfigSection(
        enable=True,
        authenticationMethod=fixture.get("authenticationMethod"),
        authenticationRequired=fixture.get("authenticationRequired"),
        urlBase=fixture.get("urlBase"),
        instanceName="RadarrPhase3Renamed",
    )
    instance = RadarrInstance(base_url=RADARR_BASE, host_config=section)
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)

    assert put_host.call_count == 1
    last_req = put_host.calls.last.request
    body_json = json.loads(last_req.content.decode())
    assert "id" in body_json, "Pitfall 4: host_config PUT body must include id"
    assert last_req.url.params["forceSave"] == "true"
    assert "apiKey" not in body_json, "HostConfig.apiKey must be excluded from PUT body"
    assert "password" not in body_json, "HostConfig.password must be excluded from PUT body"


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_host_config_no_op_when_identical(respx_mock: respx.MockRouter) -> None:
    """CR-01 regression: cluster matches the operator-declared subset → 0 PUT.

    Mirrors test_host_config_no_op_when_identical from test_reconcilers_sonarr.py.
    HostConfig uses extra="allow" so the parsed cluster carries 30+ server-only fields
    (analyticsEnabled, backupInterval, ...). The reconciler must scope the diff to
    only the keys the operator declared — otherwise every reconcile would flag drift
    on server-only fields and issue a destructive PUT that drops them.
    """
    fixture = _load("config_host.json")
    _mock_radarr_gets(respx_mock, hostconfig=fixture)
    put_host = respx_mock.put(url__regex=rf"^{RADARR_BASE}/api/v3/config/host/\d+(?:\?.*)?$")

    # Mirror the cluster's writable subset back into the section:
    section = HostConfigSection(
        enable=True,
        authenticationMethod=fixture.get("authenticationMethod"),
        authenticationRequired=fixture.get("authenticationRequired"),
        urlBase=fixture.get("urlBase"),
        instanceName=fixture.get("instanceName"),
    )
    instance = RadarrInstance(base_url=RADARR_BASE, host_config=section)
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)

    assert put_host.call_count == 0, (
        "CR-01: identical cluster/desired subset must NOT trigger a PUT — "
        "host_config diff must be scoped to operator-declared keys"
    )


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_host_config_put_body_only_contains_scoped_keys(respx_mock: respx.MockRouter) -> None:
    """CR-01 regression: PUT body MUST be scoped to operator-declared keys.

    The Radarr reconciler must NOT submit a body that omits server-only fields
    (analyticsEnabled, backupInterval, backupRetention, bindAddress, branch, ...).
    Today's contract is "scope BOTH sides of the diff and the PUT body to the
    operator-declared subset". That means the PUT body intentionally carries
    ONLY the scoped keys (+ id) — Radarr's API, like Sonarr's, preserves
    unspecified server-only fields by omission. If a future PUT semantic
    regression were to treat "missing field" as "reset to default", this test
    locks the contract: the PUT body must not be a full HostConfig payload
    that risks rewriting analyticsEnabled / backupInterval / etc.
    """
    fixture = _load("config_host.json")
    _mock_radarr_gets(respx_mock, hostconfig=fixture)
    put_host = respx_mock.put(url__regex=rf"^{RADARR_BASE}/api/v3/config/host/\d+(?:\?.*)?$").mock(
        return_value=httpx.Response(200, json={"id": fixture.get("id", 1)})
    )

    # Operator declares only instanceName (drifted) — no other writable subset.
    section = HostConfigSection(enable=True, instanceName="RadarrPhase3Renamed")
    instance = RadarrInstance(base_url=RADARR_BASE, host_config=section)
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)

    assert put_host.call_count == 1
    body_json = json.loads(put_host.calls.last.request.content.decode())
    # Body should be scoped to {instanceName, id} (+ possibly "fields": [] from merge,
    # which WR-06 will clean up). CR-01 contract: scoped to operator-declared keys.
    assert "instanceName" in body_json
    assert body_json["instanceName"] == "RadarrPhase3Renamed"
    assert "id" in body_json
    # Server-only fields MUST NOT be re-asserted — operator didn't declare them so the
    # scoped-diff design preserves their cluster state by absence from PUT body:
    for server_only_key in (
        "analyticsEnabled",
        "backupInterval",
        "backupRetention",
        "bindAddress",
        "branch",
        "logLevel",
    ):
        assert server_only_key not in body_json, (
            f"CR-01: PUT body must NOT carry server-only field {server_only_key!r} — "
            "scoped diff design means undeclared keys are preserved by omission"
        )


# ---------------------------------------------------------------------------
# Round-trip idempotence — all 5 resource types simultaneously, no writes.
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_radarr_full_round_trip_no_op(respx_mock: respx.MockRouter) -> None:
    """REQ-app-coverage / idempotence: cluster GET == desired across all 5 types → 0 writes."""
    dc_fixture = _load("downloadclient.json")
    indexer_fixture = _load("indexer.json")
    rf_fixture = _load("rootfolder.json")
    notif_fixture = _load("notification.json")
    cluster_dcs = [{**dc, "tags": [1]} for dc in dc_fixture]
    _mock_radarr_gets(
        respx_mock,
        indexers=indexer_fixture,
        rootfolders=rf_fixture,
        downloadclients=cluster_dcs,
        notifications=notif_fixture,
    )
    post_routes = {
        "dc": respx_mock.post("/downloadclient"),
        "idx": respx_mock.post("/indexer"),
        "rf": respx_mock.post("/rootfolder"),
        "notif": respx_mock.post("/notification"),
    }
    put_routes = {
        "dc": respx_mock.put(url__regex=rf"^{RADARR_BASE}/api/v3/downloadclient/\d+(?:\?.*)?$"),
        "idx": respx_mock.put(url__regex=rf"^{RADARR_BASE}/api/v3/indexer/\d+(?:\?.*)?$"),
        "rf": respx_mock.put(url__regex=rf"^{RADARR_BASE}/api/v3/rootfolder/\d+(?:\?.*)?$"),
        "notif": respx_mock.put(url__regex=rf"^{RADARR_BASE}/api/v3/notification/\d+(?:\?.*)?$"),
    }

    instance = RadarrInstance(
        base_url=RADARR_BASE,
        download_clients=DownloadClientsSection(
            prune=False, items=[DownloadClient.model_validate(dc) for dc in cluster_dcs]
        ),
        indexers=IndexersSection(
            prune=False, items=[Indexer.model_validate(e) for e in indexer_fixture]
        ),
        notifications=NotificationsSection(
            prune=False, items=[Notification.model_validate(e) for e in notif_fixture]
        ),
        root_folders=RootFoldersSection(
            prune=False, items=[RootFolder.model_validate(e) for e in rf_fixture]
        ),
        host_config=HostConfigSection(enable=False),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    result = reconcile_radarr(client, instance, dry_run=False)

    for name, route in post_routes.items():
        assert route.call_count == 0, f"round_trip: unexpected POST on {name}"
    for name, route in put_routes.items():
        assert route.call_count == 0, f"round_trip: unexpected PUT on {name}"
    assert all(p.action == Action.NO_OP for p in result.plan if p.desired is not None)


# ---------------------------------------------------------------------------
# Phase-5 extension tests (D-05-SPLIT-02, D-05-ORDER-01, label→id resolver)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_split_three_tags_three_root_folders_three_download_clients_radarr(
    respx_mock: respx.MockRouter,
) -> None:
    """ADR-7 split Radarr mirror: 3 tags + 3 root folders + 3 download clients.

    After reconcile:
    - 3 POSTs to /tag (movies, anime, family — managed tag already exists).
    - 3 POSTs to /rootfolder (/media/films, /media/films-anime, /media/films-family).
    - 3 POSTs to /downloadclient.
    - Download client POST bodies must contain INTEGER tag IDs (label resolution worked),
      not string labels.
    """
    managed_tag = {"id": 1, "label": "arrconf-managed"}
    movies_id, anime_id, family_id = 2, 3, 4

    # /tag: GET returns managed tag; POST creates each new tag in sequence.
    tag_responses = iter(
        [
            httpx.Response(201, json={"id": movies_id, "label": "movies"}),
            httpx.Response(201, json={"id": anime_id, "label": "anime"}),
            httpx.Response(201, json={"id": family_id, "label": "family"}),
        ]
    )
    respx_mock.get("/tag").mock(
        side_effect=[
            httpx.Response(200, json=[managed_tag]),  # _ensure_managed_tag
            httpx.Response(200, json=[managed_tag]),  # _reconcile_tags (before)
            httpx.Response(
                200,
                json=[  # _reconcile_tags (after re-fetch)
                    managed_tag,
                    {"id": movies_id, "label": "movies"},
                    {"id": anime_id, "label": "anime"},
                    {"id": family_id, "label": "family"},
                ],
            ),
        ]
    )
    respx_mock.post("/tag").mock(side_effect=lambda r: next(tag_responses))

    # /rootfolder: GET returns empty (all 3 are new).
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.post("/rootfolder").mock(
        return_value=httpx.Response(201, json={"id": 99, "path": "/media/new"})
    )

    # /downloadclient: GET returns empty.
    dc_post_bodies: list[dict[str, Any]] = []

    def _capture_dc_post(request: httpx.Request) -> httpx.Response:
        dc_post_bodies.append(json.loads(request.content.decode()))
        return httpx.Response(201, json={"id": 50})

    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.post("/downloadclient").mock(side_effect=_capture_dc_post)

    # Other endpoints.
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=[]))

    movies_dc = DownloadClient(
        name="qbit-movies",
        protocol="torrent",
        implementation="QBittorrent",
        configContract="QBittorrentSettings",
        tag_labels=["movies"],
    )
    anime_dc = DownloadClient(
        name="qbit-anime",
        protocol="torrent",
        implementation="QBittorrent",
        configContract="QBittorrentSettings",
        tag_labels=["anime"],
    )
    family_dc = DownloadClient(
        name="qbit-family",
        protocol="torrent",
        implementation="QBittorrent",
        configContract="QBittorrentSettings",
        tag_labels=["family"],
    )

    instance = RadarrInstance(
        base_url=RADARR_BASE,
        tags=TagsSection(
            items=[TagItem(label="movies"), TagItem(label="anime"), TagItem(label="family")]
        ),
        root_folders=RootFoldersSection(
            items=[
                RootFolder(path="/media/films"),
                RootFolder(path="/media/films-anime"),
                RootFolder(path="/media/films-family"),
            ]
        ),
        download_clients=DownloadClientsSection(items=[movies_dc, anime_dc, family_dc]),
        movie_tags=MovieTagsSection(enable=False),  # keep test focused on split
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)

    # 3 tag POSTs (movies, anime, family).
    tag_posts = [
        c for c in respx_mock.calls if c.request.method == "POST" and "/tag" in c.request.url.path
    ]
    assert len(tag_posts) == 3, f"Expected 3 tag POSTs, got {len(tag_posts)}"

    # 3 root folder POSTs.
    rf_posts = [
        c
        for c in respx_mock.calls
        if c.request.method == "POST" and "/rootfolder" in c.request.url.path
    ]
    assert len(rf_posts) == 3, f"Expected 3 rootfolder POSTs, got {len(rf_posts)}"

    # 3 download client POSTs with INTEGER tag IDs (not string labels).
    assert len(dc_post_bodies) == 3, f"Expected 3 download client POSTs, got {len(dc_post_bodies)}"
    for body in dc_post_bodies:
        tags_in_body = body.get("tags", [])
        # tag_labels field must NOT appear in the API body (excluded=True).
        assert "tag_labels" not in body, "tag_labels must be excluded from POST body"
        # Each download client gets its tag ID + managed tag ID.
        assert all(isinstance(t, int) for t in tags_in_body), (
            f"All tags in download client POST body must be ints. Got: {tags_in_body}"
        )
        # At minimum: managed tag + one routing tag.
        assert len(tags_in_body) >= 2, (
            f"Expected managed tag + routing tag in body. Got: {tags_in_body}"
        )


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_reconcile_order_radarr(
    respx_mock: respx.MockRouter,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D-05-ORDER-01 Radarr mirror regression: step_begin events in the exact fixed order.

    Captures the structured-log output (JSON lines written to stdout by the configured
    structlog processor chain) and asserts that step_begin events appear in the
    D-05-ORDER-01 sequence. Uses capsys rather than structlog.testing.capture_logs()
    because cache_logger_on_first_use=True (set by configure_logging() in CLI tests)
    can freeze the bound logger before capture_logs() can inject its processor.
    """
    _mock_radarr_gets(respx_mock, tag=_load("tag_with_arrconf_managed.json"))

    instance = RadarrInstance(
        base_url=RADARR_BASE,
        movie_tags=MovieTagsSection(enable=False),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")

    # Use structlog.testing.capture_logs() when possible; fall back to capsys JSON parsing.
    step_events: list[dict[str, Any]] = []

    with structlog.testing.capture_logs() as cap_logs:
        reconcile_radarr(client, instance, dry_run=False)

    step_events = [e for e in cap_logs if e.get("event") == "step_begin" and "step_index" in e]

    if not step_events:
        # Fallback: parse JSON lines from stdout (works when logger is cached).
        import json as _json

        captured = capsys.readouterr()
        for line in captured.out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = _json.loads(line)
                if obj.get("event") == "step_begin" and "step_index" in obj:
                    step_events.append(obj)
            except (_json.JSONDecodeError, ValueError):
                pass

    assert len(step_events) >= 4, (
        f"D-05-ORDER-01 Radarr: expected at least 4 step_begin events, got {len(step_events)}. "
        f"Events: {step_events}"
    )

    # The step_index must be strictly increasing (D-05-ORDER-01 invariant).
    indices = [e["step_index"] for e in step_events]
    assert indices == sorted(indices), (
        f"D-05-ORDER-01 Radarr violated! step_index sequence must be monotonically increasing. "
        f"Got: {indices}. Step events: {[(e.get('step'), e['step_index']) for e in step_events]}"
    )

    # Verify the canonical order by step name.
    step_names = [e.get("step") for e in step_events]
    canonical_order = [
        "managed_tag",
        "tags",
        "indexers",
        "root_folders",
        "remote_path_mappings",
        "download_clients",
        "notifications",
        "host_config",
        "movie_tags",
    ]
    assert step_names == canonical_order, (
        f"D-05-ORDER-01 Radarr violated! Expected step order:\n  {canonical_order}\n"
        f"Got:\n  {step_names}"
    )


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_download_client_tags_label_resolution_uses_just_created_id_radarr(
    respx_mock: respx.MockRouter,
) -> None:
    """D-05-ORDER-01 Radarr dispositive: label resolver uses IDs from the tags step, not from cache.

    Fixture: GET /tag returns [] (no tags exist). YAML declares tag {label: movies} AND
    download_client with tag_labels=[movies]. After reconcile: the download_client POST
    body's tags field must contain the ID returned by the just-completed POST /tag.

    This proves the label→id resolver runs AFTER the tags POST completes (step 2
    before step 6 per D-05-ORDER-01).
    """
    just_created_movies_id = 42  # Non-trivial id to prove the resolver used the POST response.

    # GET /tag: first and second calls return [] (no pre-existing tags).
    # Third call (re-fetch after reconcile) returns the newly created tag.
    respx_mock.get("/tag").mock(
        side_effect=[
            httpx.Response(200, json=[]),  # _ensure_managed_tag
            httpx.Response(200, json=[]),  # _reconcile_tags (before)
            httpx.Response(
                200, json=[{"id": just_created_movies_id, "label": "movies"}]
            ),  # re-fetch
        ]
    )
    # POST /tag for "movies" returns the server-assigned id=42.
    respx_mock.post("/tag").mock(
        return_value=httpx.Response(201, json={"id": just_created_movies_id, "label": "movies"})
    )

    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=[]))

    dc_post_bodies: list[dict[str, Any]] = []

    def _capture_dc_post(request: httpx.Request) -> httpx.Response:
        dc_post_bodies.append(json.loads(request.content.decode()))
        return httpx.Response(201, json={"id": 1})

    respx_mock.post("/downloadclient").mock(side_effect=_capture_dc_post)

    movies_dc = DownloadClient(
        name="qbit-movies",
        protocol="torrent",
        implementation="QBittorrent",
        configContract="QBittorrentSettings",
        tag_labels=["movies"],
    )
    instance = RadarrInstance(
        base_url=RADARR_BASE,
        tags=TagsSection(items=[TagItem(label="movies")]),
        download_clients=DownloadClientsSection(items=[movies_dc]),
        movie_tags=MovieTagsSection(enable=False),  # disable to keep test focused
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(client, instance, dry_run=False)

    assert len(dc_post_bodies) == 1, "Expected exactly one download client POST"
    tags_in_body = dc_post_bodies[0].get("tags", [])

    assert just_created_movies_id in tags_in_body, (
        f"Label resolver must use the id={just_created_movies_id} returned by the just-completed "
        f"POST /tag, not a stale/string value. Got tags: {tags_in_body}"
    )
    # String "movies" must NOT be in the tags field.
    assert "movies" not in tags_in_body, (
        f"String 'movies' must not appear in tags body — label resolution must produce integer. "
        f"Got: {tags_in_body}"
    )
