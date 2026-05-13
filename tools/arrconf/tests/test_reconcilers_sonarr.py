"""Tests for arrconf.reconcilers.sonarr.reconcile_sonarr — REQ-app-coverage.

All HTTP mocked via respx (D-20). Coverage gate ≥ 70 % on the module.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import SonarrClient
from arrconf.config import (
    DownloadClientsSection,
    HostConfigSection,
    IndexersSection,
    NotificationsSection,
    RootFoldersSection,
    SonarrInstance,
)
from arrconf.differ import Action
from arrconf.reconcilers.sonarr import reconcile_sonarr
from arrconf.resources.sonarr.download_client import DownloadClient
from arrconf.resources.sonarr.indexer import Indexer
from arrconf.resources.sonarr.notification import Notification
from arrconf.resources.sonarr.root_folder import RootFolder


def _build_dc(name: str = "qbit", **overrides: Any) -> DownloadClient:
    defaults: dict[str, Any] = {
        "protocol": "torrent",
        "implementation": "QBittorrent",
        "configContract": "QBittorrentSettings",
    }
    defaults.update(overrides)
    return DownloadClient(name=name, **defaults)


def _mock_base_gets(
    respx_mock: respx.MockRouter,
    tag_fixture: list[dict[str, Any]],
    *,
    indexers: list[dict[str, Any]] | None = None,
    rootfolders: list[dict[str, Any]] | None = None,
    downloadclients: list[dict[str, Any]] | None = None,
    notifications: list[dict[str, Any]] | None = None,
) -> None:
    """Mock the GET endpoints that the extended reconciler always touches.

    The Phase-3 reconciler calls GET /indexer, /rootfolder, /downloadclient,
    /notification in every run. Tests that focus on download_clients only must
    still mock all four endpoints to avoid AllMockedAssertionError from respx.
    Defaults to empty lists for endpoints the test does not care about.
    """
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=tag_fixture))
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=indexers or []))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=rootfolders or []))
    respx_mock.get("/downloadclient").mock(
        return_value=httpx.Response(200, json=downloadclients or [])
    )
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=notifications or []))


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_dump_apply_no_op(
    respx_mock: respx.MockRouter,
    sonarr_downloadclient_fixture: list[dict[str, Any]],
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """Round-trip property — desired = current → all NO_OP, zero writes."""
    # Cluster state must include the managed tag stamp for the round-trip to hold,
    # because the reconciler stamps the managed tag onto every desired item before
    # diffing (D-02). If the cluster fixture had tags=[] but desired has tags=[1],
    # diff_models would correctly flag UPDATE on `tags`.
    cluster_payload: list[dict[str, Any]] = [
        {**dc, "tags": [1]} for dc in sonarr_downloadclient_fixture
    ]
    _mock_base_gets(respx_mock, sonarr_tag_managed_fixture, downloadclients=cluster_payload)
    post_route = respx_mock.post("/downloadclient")
    put_route = respx_mock.put(url__regex=r"^http://sonarr\.test/api/v3/downloadclient(/\d+)?$")
    delete_route = respx_mock.delete(url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$")

    desired = [DownloadClient.model_validate(dc) for dc in cluster_payload]
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=False, items=desired),
    )

    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(client, instance, dry_run=False)

    assert all(p.action == Action.NO_OP for p in result.plan if p.desired is not None)
    assert post_route.call_count == 0
    assert put_route.call_count == 0
    assert delete_route.call_count == 0


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_add_new_download_client(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    _mock_base_gets(respx_mock, sonarr_tag_managed_fixture)
    post_route = respx_mock.post("/downloadclient").mock(
        return_value=httpx.Response(201, json={"id": 7, "name": "qbit"})
    )

    desired = [_build_dc("qbit")]
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=False, items=desired),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(client, instance, dry_run=False)

    assert post_route.call_count == 1
    body = post_route.calls.last.request.content.decode()
    # Managed tag id (=1 from fixture) must be present in the POSTed body.
    assert '"tags":[1]' in body or '"tags": [1]' in body
    assert any(p.action == Action.ADD and p.name == "qbit" for p in result.plan)


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_update_existing_download_client(
    respx_mock: respx.MockRouter,
    sonarr_downloadclient_fixture: list[dict[str, Any]],
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    _mock_base_gets(
        respx_mock, sonarr_tag_managed_fixture, downloadclients=sonarr_downloadclient_fixture
    )
    put_route = respx_mock.put(
        url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+(?:\?.*)?$"
    ).mock(return_value=httpx.Response(200, json={"id": 1, "name": "qBittorrent"}))

    # Build desired identical to current but with priority=99
    desired_payload = dict(sonarr_downloadclient_fixture[0])
    desired_payload["priority"] = 99
    desired_payload["tags"] = [1]  # managed tag (would be added by reconciler if missing)
    desired = [DownloadClient.model_validate(desired_payload)]
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=False, items=desired),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(client, instance, dry_run=False)

    assert put_route.call_count == 1
    body = put_route.calls.last.request.content.decode()
    assert '"priority":99' in body or '"priority": 99' in body
    assert any(p.action == Action.UPDATE for p in result.plan)


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_update_omits_privacy_credential_fields_from_put_body(
    respx_mock: respx.MockRouter,
    sonarr_downloadclient_fixture: list[dict[str, Any]],
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """Integration regression — v0.1.5 / D-02.2-AUTH-REGRESSION / ADR-8.1.

    Inverts the v0.1.3 contract (which asserted username/password VALUES
    survive into the PUT body via Phase 2.1's merge_fields_for_put substitution).
    v0.1.5 (Plan 08 GREEN) instead OMITS entries whose cluster-side privacy
    metadata is `password` or `userName`. Sonarr preserves stored values
    when fields are absent from the PUT body — safer than substituting the
    API mask `"********"` which v0.1.4's `?forceSave=true` would accept
    verbatim and overwrite the real credential.

    This test asserts the unit-level contract (Plan 07 / Plan 08
    test_differ.py) holds at the reconciler-integration level: the PUT body
    actually sent over respx has no credential entries.

    Plan 02 forceSave URL-param tests verify `?forceSave=true` is still set
    on this same UPDATE — the merge-layer omission and the HTTP-layer bypass
    are independent layered defenses.
    """
    _mock_base_gets(
        respx_mock, sonarr_tag_managed_fixture, downloadclients=sonarr_downloadclient_fixture
    )
    put_route = respx_mock.put(
        url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+(?:\?.*)?$"
    ).mock(return_value=httpx.Response(200, json={"id": 1, "name": "qBittorrent"}))

    # Build desired YAML where username and password are EMPTY (mirrors my-kluster pre-D-36)
    desired_payload = dict(sonarr_downloadclient_fixture[0])
    desired_payload["fields"] = [
        {"name": "host", "value": "qbittorrent.selfhost.svc.cluster.local"},
        {"name": "port", "value": 8080},
        {"name": "useSsl", "value": False},
        {"name": "urlBase", "value": ""},
        {"name": "username", "value": ""},
        {"name": "password", "value": ""},
        {"name": "tvCategory", "value": "sonarr"},
        {"name": "tvImportedCategory", "value": ""},
        {"name": "recentTvPriority", "value": 0},
        {"name": "olderTvPriority", "value": 0},
        {"name": "initialState", "value": 0},
        {"name": "sequentialOrder", "value": False},
        {"name": "firstAndLast", "value": False},
        {"name": "contentLayout", "value": 0},
    ]
    desired_payload["tags"] = [1]
    desired = [DownloadClient.model_validate(desired_payload)]
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=False, items=desired),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert put_route.call_count == 1
    body = put_route.calls.last.request.content.decode()
    body_json = json.loads(body)
    field_names = {f["name"] for f in body_json.get("fields", [])}

    # v0.1.5 / D-02.2-AUTH-REGRESSION contract: privacy=password|userName fields
    # are OMITTED from the PUT body. Sonarr preserves stored values via absence.
    assert "password" not in field_names, (
        "v0.1.5: privacy=password field must be OMITTED from PUT body, "
        "NOT substituted with cluster mask (D-02.2-AUTH-REGRESSION / ADR-8.1)"
    )
    assert "username" not in field_names, (
        "v0.1.5: privacy=userName field must be OMITTED from PUT body, "
        "NOT substituted with cluster value (uniform omit-by-metadata strategy)"
    )

    # Non-credential fields ARE present (host, port, tvCategory carry through normally):
    assert "host" in field_names, "non-credential field 'host' must remain in PUT body"
    assert "port" in field_names, "non-credential field 'port' must remain in PUT body"
    assert "tvCategory" in field_names, "non-credential field 'tvCategory' must remain in PUT body"

    # The API mask token must NOT appear ANYWHERE in the body (defensive against
    # any future leak path):
    assert "********" not in body, (
        "API mask must not appear in PUT body — credentials must be omitted, not masked"
    )
    assert "***REDACTED***" not in body, (
        "in-tree redaction token must not appear in PUT body — credentials omitted"
    )


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_prune_skip_default(
    respx_mock: respx.MockRouter,
    sonarr_downloadclient_fixture: list[dict[str, Any]],
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """Orphan in cluster + desired empty + prune=False → 0 DELETE, PRUNE_SKIP logged."""
    _mock_base_gets(
        respx_mock, sonarr_tag_managed_fixture, downloadclients=sonarr_downloadclient_fixture
    )
    delete_route = respx_mock.delete(url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$")

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=False, items=[]),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(client, instance, dry_run=False)

    assert delete_route.call_count == 0
    assert any(p.action == Action.PRUNE_SKIP for p in result.plan)


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_prune_protected_without_managed_tag(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """T-01-04: prune=True on a DC without arrconf-managed tag → 0 DELETE."""
    orphan_unmanaged = [
        {
            "id": 99,
            "name": "manual-qbit",
            "enable": True,
            "protocol": "torrent",
            "priority": 1,
            "implementation": "QBittorrent",
            "configContract": "QBittorrentSettings",
            "fields": [],
            "tags": [5],  # NOT the managed tag id (=1)
            "removeCompletedDownloads": True,
            "removeFailedDownloads": True,
        }
    ]
    _mock_base_gets(respx_mock, sonarr_tag_managed_fixture, downloadclients=orphan_unmanaged)
    delete_route = respx_mock.delete(url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$")

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=True, items=[]),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(client, instance, dry_run=False)

    assert delete_route.call_count == 0
    assert any(p.action == Action.PRUNE_PROTECTED for p in result.plan)


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_prune_executes_with_managed_tag(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """prune=True on a DC tagged with arrconf-managed → DELETE issued."""
    orphan_managed = [
        {
            "id": 99,
            "name": "old-qbit",
            "enable": True,
            "protocol": "torrent",
            "priority": 1,
            "implementation": "QBittorrent",
            "configContract": "QBittorrentSettings",
            "fields": [],
            "tags": [1],  # managed tag id from fixture
            "removeCompletedDownloads": True,
            "removeFailedDownloads": True,
        }
    ]
    _mock_base_gets(respx_mock, sonarr_tag_managed_fixture, downloadclients=orphan_managed)
    delete_route = respx_mock.delete(
        url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$"
    ).mock(return_value=httpx.Response(204))

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=True, items=[]),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(client, instance, dry_run=False)

    assert delete_route.call_count == 1
    assert any(p.action == Action.DELETE and p.name == "old-qbit" for p in result.plan)


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_dry_run_logs_no_writes(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """Dry-run plans actions but issues zero POST/PUT/DELETE."""
    _mock_base_gets(respx_mock, sonarr_tag_managed_fixture)
    post_route = respx_mock.post("/downloadclient")
    put_route = respx_mock.put(url__regex=r"^http://sonarr\.test/api/v3/downloadclient(/\d+)?$")
    delete_route = respx_mock.delete(url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$")

    desired = [_build_dc("qbit")]
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=False, items=desired),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(client, instance, dry_run=True)

    assert post_route.call_count == 0
    assert put_route.call_count == 0
    assert delete_route.call_count == 0
    # Plan still computed
    assert any(p.action == Action.ADD for p in result.plan)


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_update_passes_forceSave_query_param(  # noqa: N802 — `forceSave` matches Sonarr API param literal (locked by D-02.2 plan)
    respx_mock: respx.MockRouter,
    sonarr_downloadclient_fixture: list[dict[str, Any]],
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """Regression — D-02.1-06 / ADR-8: every UPDATE PUT for *arr v3 clients carries
    ``?forceSave=true`` so Sonarr skips the pre-save qBit auth re-validation against
    the literal ``********`` mask preserved by ``merge_fields_for_put``.

    Trigger is the action (UPDATE), not body content. Asserts URL params at the
    HTTP layer, not body shape.
    """
    _mock_base_gets(
        respx_mock, sonarr_tag_managed_fixture, downloadclients=sonarr_downloadclient_fixture
    )
    put_route = respx_mock.put(
        url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+(?:\?.*)?$"
    ).mock(return_value=httpx.Response(200, json={"id": 1, "name": "qBittorrent"}))

    # Trigger UPDATE by changing one field (priority is the canonical safe drift field per A6).
    desired_payload = dict(sonarr_downloadclient_fixture[0])
    desired_payload["priority"] = 99
    desired_payload["tags"] = [1]
    desired = [DownloadClient.model_validate(desired_payload)]
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=False, items=desired),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert put_route.call_count == 1
    last_request = put_route.calls.last.request
    assert last_request.url.params["forceSave"] == "true"


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_add_does_not_pass_forceSave_query_param(  # noqa: N802 — `forceSave` matches Sonarr API param literal (locked by D-02.2 plan)
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """Defensive — ADR-8: forceSave is UPDATE-only. POST (ADD) must NOT carry it."""
    _mock_base_gets(respx_mock, sonarr_tag_managed_fixture)
    post_route = respx_mock.post("/downloadclient").mock(
        return_value=httpx.Response(201, json={"id": 1, "name": "qbit-new"})
    )

    new_dc = _build_dc(name="qbit-new", priority=1)
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=False, items=[new_dc]),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert post_route.call_count == 1
    assert "forceSave" not in post_route.calls.last.request.url.params


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_delete_does_not_pass_forceSave_query_param(  # noqa: N802 — `forceSave` matches Sonarr API param literal (locked by D-02.2 plan)
    respx_mock: respx.MockRouter,
    sonarr_downloadclient_fixture: list[dict[str, Any]],
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """Defensive — ADR-8: forceSave is UPDATE-only. DELETE must NOT carry it."""
    cluster_payload: list[dict[str, Any]] = [
        {**dc, "tags": [1]} for dc in sonarr_downloadclient_fixture
    ]
    _mock_base_gets(respx_mock, sonarr_tag_managed_fixture, downloadclients=cluster_payload)
    delete_route = respx_mock.delete(
        url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$"
    ).mock(return_value=httpx.Response(204))

    # Empty desired + prune=True triggers DELETE on the existing qBit downloadclient.
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=True, items=[]),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert delete_route.call_count == 1
    assert "forceSave" not in delete_route.calls.last.request.url.params


# ---------------------------------------------------------------------------
# Phase 3 — Sonarr extension tests (REQ-app-coverage)
# ---------------------------------------------------------------------------


def _mock_phase3_gets(
    respx_mock: respx.MockRouter,
    tag_fixture: list[dict[str, Any]],
    *,
    indexers: list[dict[str, Any]] | None = None,
    notifications: list[dict[str, Any]] | None = None,
    rootfolders: list[dict[str, Any]] | None = None,
    downloadclients: list[dict[str, Any]] | None = None,
    hostconfig: dict[str, Any] | None = None,
) -> None:
    """Mock every GET endpoint the extended reconciler touches.

    Defaults to empty lists for list resources. host_config GET is only
    mocked if `hostconfig` is provided — tests for the skipped branch should
    NOT pass a hostconfig fixture so respx records 0 calls.
    """
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=tag_fixture))
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=indexers or []))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=rootfolders or []))
    respx_mock.get("/downloadclient").mock(
        return_value=httpx.Response(200, json=downloadclients or [])
    )
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=notifications or []))
    if hostconfig is not None:
        respx_mock.get("/config/host").mock(return_value=httpx.Response(200, json=hostconfig))


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_add_new_indexer(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """REQ-app-coverage: new indexer in YAML → POST /indexer."""
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture)
    post_indexer = respx_mock.post("/indexer").mock(
        return_value=httpx.Response(201, json={"id": 42, "name": "myindexer"})
    )

    indexer = Indexer(
        name="myindexer",
        implementation="Newznab",
        configContract="NewznabSettings",
    )
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        indexers=IndexersSection(prune=False, items=[indexer]),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert post_indexer.call_count == 1


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_indexer_no_op_when_identical(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
    sonarr_indexer_fixture: list[dict[str, Any]],
) -> None:
    """REQ-app-coverage: cluster indexer == desired → 0 PUT."""
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture, indexers=sonarr_indexer_fixture)
    put_indexer = respx_mock.put(url__regex=r"^http://sonarr\.test/api/v3/indexer/\d+(?:\?.*)?$")

    desired = [Indexer.model_validate(e) for e in sonarr_indexer_fixture]
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        indexers=IndexersSection(prune=False, items=desired),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert put_indexer.call_count == 0


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_add_new_notification(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """REQ-app-coverage: new notification in YAML → POST /notification."""
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture)
    post_notif = respx_mock.post("/notification").mock(
        return_value=httpx.Response(201, json={"id": 7, "name": "discord-main"})
    )

    notif = Notification(
        name="discord-main",
        implementation="Discord",
        configContract="DiscordSettings",
    )
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        notifications=NotificationsSection(prune=False, items=[notif]),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert post_notif.call_count == 1


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_notification_no_op_when_identical(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
    sonarr_notification_fixture: list[dict[str, Any]],
) -> None:
    """REQ-app-coverage: cluster notification == desired → 0 PUT."""
    _mock_phase3_gets(
        respx_mock, sonarr_tag_managed_fixture, notifications=sonarr_notification_fixture
    )
    put_notif = respx_mock.put(url__regex=r"^http://sonarr\.test/api/v3/notification/\d+(?:\?.*)?$")

    desired = [Notification.model_validate(e) for e in sonarr_notification_fixture]
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        notifications=NotificationsSection(prune=False, items=desired),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert put_notif.call_count == 0


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_add_new_root_folder(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """REQ-app-coverage: new root folder in YAML → POST /rootfolder."""
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture)
    post_rf = respx_mock.post("/rootfolder").mock(
        return_value=httpx.Response(201, json={"id": 3, "path": "/media/new"})
    )

    rf = RootFolder(path="/media/new")
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        root_folders=RootFoldersSection(prune=False, items=[rf]),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert post_rf.call_count == 1


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_root_folder_no_update_action_ever(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
    sonarr_rootfolder_fixture: list[dict[str, Any]],
) -> None:
    """Pitfall 1: root folders have no PUT endpoint. UPDATE plan_action is a bug.

    With the RootFolder model excluding accessible / freeSpace / unmappedFolders
    (Plan 01 Task 1.2), a path-matched root folder NEVER differs server-side —
    only ADD / NO_OP / PRUNE_SKIP / DELETE are valid outcomes.
    """
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture, rootfolders=sonarr_rootfolder_fixture)
    put_rf = respx_mock.put(url__regex=r"^http://sonarr\.test/api/v3/rootfolder/\d+(?:\?.*)?$")

    # Desired matches cluster path exactly:
    desired = [RootFolder.model_validate(e) for e in sonarr_rootfolder_fixture]
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        root_folders=RootFoldersSection(prune=False, items=desired),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert put_rf.call_count == 0, "Pitfall 1: root folders must never receive a PUT"


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_host_config_skipped_when_enable_false(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """D-03-04: host_config GET MUST NOT be issued when section.enable is False."""
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture)
    # Register the host route but expect 0 calls:
    get_host = respx_mock.get("/config/host")

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        host_config=HostConfigSection(enable=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert get_host.call_count == 0, (
        "D-03-04: host_config reconcile must not GET /config/host when enable=False"
    )


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_host_config_no_op_when_identical(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
    sonarr_hostconfig_fixture: dict[str, Any],
) -> None:
    """D-03-04 + idempotence: enable=True + desired matches cluster → 0 PUT."""
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture, hostconfig=sonarr_hostconfig_fixture)
    put_host = respx_mock.put(url__regex=r"^http://sonarr\.test/api/v3/config/host/\d+(?:\?.*)?$")

    # Mirror the cluster's writable subset back into the section:
    section = HostConfigSection(
        enable=True,
        authenticationMethod=sonarr_hostconfig_fixture.get("authenticationMethod"),
        authenticationRequired=sonarr_hostconfig_fixture.get("authenticationRequired"),
        urlBase=sonarr_hostconfig_fixture.get("urlBase"),
        instanceName=sonarr_hostconfig_fixture.get("instanceName"),
    )
    instance = SonarrInstance(base_url="http://sonarr.test", host_config=section)
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert put_host.call_count == 0


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_host_config_update_when_different(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
    sonarr_hostconfig_fixture: dict[str, Any],
) -> None:
    """D-03-04 + REQ-app-coverage: instanceName change → PUT /config/host/{id}?forceSave=true."""
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture, hostconfig=sonarr_hostconfig_fixture)
    put_host = respx_mock.put(
        url__regex=r"^http://sonarr\.test/api/v3/config/host/\d+(?:\?.*)?$"
    ).mock(return_value=httpx.Response(200, json={"id": sonarr_hostconfig_fixture.get("id", 1)}))

    section = HostConfigSection(
        enable=True,
        authenticationMethod=sonarr_hostconfig_fixture.get("authenticationMethod"),
        authenticationRequired=sonarr_hostconfig_fixture.get("authenticationRequired"),
        urlBase=sonarr_hostconfig_fixture.get("urlBase"),
        instanceName="PhaseThreeRenamed",  # intentionally drifts from cluster
    )
    instance = SonarrInstance(base_url="http://sonarr.test", host_config=section)
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert put_host.call_count == 1
    last_req = put_host.calls.last.request
    # Pitfall 4: id MUST be present in body (re-injected after merge):
    body_json = json.loads(last_req.content.decode())
    assert "id" in body_json, "Pitfall 4: host_config PUT body must include id"
    # Inherited from _ArrV3Client: forceSave=true on every UPDATE PUT:
    assert last_req.url.params["forceSave"] == "true"
    # Credentials MUST NOT leak via the PUT body
    # (Plan 01 Task 1.2 — HostConfig excludes apiKey/password):
    assert "apiKey" not in body_json, "HostConfig.apiKey must be excluded from PUT body"
    assert "password" not in body_json, "HostConfig.password must be excluded from PUT body"
