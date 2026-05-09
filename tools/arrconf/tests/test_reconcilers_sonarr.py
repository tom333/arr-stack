"""Tests for arrconf.reconcilers.sonarr.reconcile_sonarr — REQ-app-coverage.

All HTTP mocked via respx (D-20). Coverage gate ≥ 70 % on the module.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import SonarrClient
from arrconf.config import DownloadClientsSection, SonarrInstance
from arrconf.differ import Action
from arrconf.reconcilers.sonarr import reconcile_sonarr
from arrconf.resources.sonarr.download_client import DownloadClient


def _build_dc(name: str = "qbit", **overrides: Any) -> DownloadClient:
    defaults: dict[str, Any] = {
        "protocol": "torrent",
        "implementation": "QBittorrent",
        "configContract": "QBittorrentSettings",
    }
    defaults.update(overrides)
    return DownloadClient(name=name, **defaults)


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
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=cluster_payload))
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
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
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
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(
        return_value=httpx.Response(200, json=sonarr_downloadclient_fixture)
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
def test_update_preserves_redacted_credentials_in_put_body(
    respx_mock: respx.MockRouter,
    sonarr_downloadclient_fixture: list[dict[str, Any]],
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """Regression — replays Phase 2 PR2 PUT 400 (D-31).

    Cluster fixture has username='admin' and password='***REDACTED***'.
    Desired YAML has empty values for both (mirrors my-kluster pre-D-36 shape).
    Reconciler runs dry_run=False — PUT body MUST carry cluster's credentials,
    NOT the empty values from YAML.
    """
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(
        return_value=httpx.Response(200, json=sonarr_downloadclient_fixture)
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
    # Cluster's username "admin" + password "***REDACTED***" MUST survive into PUT body:
    assert '"value":"admin"' in body or '"value": "admin"' in body, (
        "username value 'admin' must be preserved from cluster (D-31)"
    )
    assert '"value":"***REDACTED***"' in body or '"value": "***REDACTED***"' in body, (
        "password value '***REDACTED***' must be preserved from cluster (D-31)"
    )
    # Empty values from YAML for username/password MUST NOT have leaked through:
    assert '"name":"username","value":""' not in body
    assert '"name": "username", "value": ""' not in body
    assert '"name":"password","value":""' not in body
    assert '"name": "password", "value": ""' not in body


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_prune_skip_default(
    respx_mock: respx.MockRouter,
    sonarr_downloadclient_fixture: list[dict[str, Any]],
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """Orphan in cluster + desired empty + prune=False → 0 DELETE, PRUNE_SKIP logged."""
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(
        return_value=httpx.Response(200, json=sonarr_downloadclient_fixture)
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
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=orphan_unmanaged))
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
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=orphan_managed))
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
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
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
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(
        return_value=httpx.Response(200, json=sonarr_downloadclient_fixture)
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
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
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
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=cluster_payload))
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
