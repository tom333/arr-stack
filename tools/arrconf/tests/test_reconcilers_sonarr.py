"""Tests for arrconf.reconcilers.sonarr.reconcile_sonarr — REQ-app-coverage.

All HTTP mocked via respx (D-20). Coverage gate ≥ 70 % on the module.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx
import structlog.testing

from arrconf.client_base import SonarrClient
from arrconf.config import (
    DownloadClientsSection,
    HostConfigSection,
    IndexersSection,
    NotificationsSection,
    RootFoldersSection,
    SeriesTagsSection,
    SonarrInstance,
    TagItem,
    TagsSection,
)
from arrconf.differ import Action
from arrconf.generators.categories import SonarrDerived
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
    remotepathmappings: list[dict[str, Any]] | None = None,
    series: list[dict[str, Any]] | None = None,
) -> None:
    """Mock the GET endpoints that the extended reconciler always touches.

    The Phase-5 reconciler calls GET /tag (multiple times), /indexer, /rootfolder,
    /downloadclient, /notification, /remotepathmapping, /series in every run.
    Tests that focus on a specific resource must still mock all endpoints to avoid
    AllMockedAssertionError from respx. Defaults to empty lists for endpoints the
    test does not care about.
    """
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=tag_fixture))
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=indexers or []))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=rootfolders or []))
    respx_mock.get("/downloadclient").mock(
        return_value=httpx.Response(200, json=downloadclients or [])
    )
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=notifications or []))
    respx_mock.get("/remotepathmapping").mock(
        return_value=httpx.Response(200, json=remotepathmappings or [])
    )
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=series or []))


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
        download_clients=DownloadClientsSection(prune=False),
    )

    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=desired,
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
        download_clients=DownloadClientsSection(prune=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=desired,
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
        download_clients=DownloadClientsSection(prune=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=desired,
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert put_route.call_count == 1
    body = put_route.calls.last.request.content.decode()
    assert '"priority":99' in body or '"priority": 99' in body
    assert any(p.action == Action.UPDATE for p in result.plan)


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_update_omits_privacy_credential_fields_from_put_body(
    respx_mock: respx.MockRouter,
    sonarr_downloadclient_fixture: list[dict[str, Any]],
    sonarr_tag_managed_fixture: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
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

    Phase 18 (REQ-qbit-post-credentials) extends the test scope: the helper
    now injects QBT_USER / QBT_PASS into desired's empty credential fields
    BEFORE merge_fields_for_put runs. The omission contract is unchanged —
    merge_fields_for_put OMITS credential fields regardless of whether desired
    carries env-injected values or empty strings (the privacy-by-metadata
    strip path in differ.py is value-blind).
    """
    monkeypatch.setenv("QBT_USER", "phase18-fake-user")
    monkeypatch.setenv("QBT_PASS", "phase18-fake-pass")
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
        download_clients=DownloadClientsSection(prune=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=desired,
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert put_route.call_count == 1
    body = put_route.calls.last.request.content.decode()
    body_json = json.loads(body)
    field_names = {f["name"] for f in body_json.get("fields", [])}
    fields_by_name = {f["name"]: f for f in body_json.get("fields", [])}

    # Non-credential fields ARE present (host, port, tvCategory carry through normally):
    assert "host" in field_names, "non-credential field 'host' must remain in PUT body"
    assert "port" in field_names, "non-credential field 'port' must remain in PUT body"
    assert "tvCategory" in field_names, "non-credential field 'tvCategory' must remain in PUT body"

    # The cluster's API mask token must NEVER appear in the PUT body (defensive
    # against the v0.1.4 substitution regression that wrote the literal mask back
    # as a credential — D-02.2-AUTH-REGRESSION / ADR-8.1).
    assert "********" not in body, (
        "API mask must not appear in PUT body — defensive guard against the v0.1.4 "
        "substitution regression (D-02.2-AUTH-REGRESSION / ADR-8.1)"
    )
    assert "***REDACTED***" not in body, (
        "in-tree redaction token must not appear in PUT body — defensive guard "
        "against fixture sentinel leaking via the substitution path"
    )

    # Phase 18 / REQ-qbit-post-credentials: post-helper, desired carries env-injected
    # values for empty YAML creds. merge_fields_for_put's "Desired has a real value:
    # user intends credential rotation; pass through as-is" branch (differ.py CR-01)
    # then forwards them into the PUT body. The composite contract is:
    #   (a) credentials ARE present in the PUT body when desired has a real value
    #   (b) the value sent is EXACTLY the env-injected value (no cluster mask leak)
    # This proves Phase 18 closes the gap: Sonarr now receives real creds on UPDATE
    # too (not just CREATE) when the operator rotates QBT_USER / QBT_PASS.
    assert "username" in field_names, (
        "Phase 18: post-injection, username field must be PRESENT in PUT body with "
        "the env-injected value (rotation intent — differ.py CR-01 gap-closure)"
    )
    assert "password" in field_names, (
        "Phase 18: post-injection, password field must be PRESENT in PUT body with "
        "the env-injected value (rotation intent — differ.py CR-01 gap-closure)"
    )
    assert fields_by_name["username"]["value"] == "phase18-fake-user", (
        "Phase 18: env-injected QBT_USER must be the value carried in the PUT body "
        "(not the cluster mask, not the empty string)"
    )
    assert fields_by_name["password"]["value"] == "phase18-fake-pass", (
        "Phase 18: env-injected QBT_PASS must be the value carried in the PUT body "
        "(not the cluster mask, not the empty string)"
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
        download_clients=DownloadClientsSection(prune=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert delete_route.call_count == 0
    assert any(p.action == Action.PRUNE_SKIP for p in result.plan)


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_prune_executes_unmanaged_dc_when_prune_true(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """Phase 22 / D-04 / force_prune: prune=True on a DC without arrconf-managed tag → DELETE.

    This is a behaviour change from T-01-04: with force_prune wired to
    instance.download_clients.prune, even a DC with a non-managed tag (tags=[5])
    is deleted when the operator explicitly opts in via prune=True. The D-02
    PRUNE_PROTECTED protection is bypassed by the force_prune path (D-04).
    To preserve a DC without arrconf-managed, the operator must set prune=False
    (the default). See test_catch_all_dc_prune_false_protects_untagged for that path.
    """
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
            "tags": [5],  # NOT the managed tag id (=1) — force_prune still fires
            "removeCompletedDownloads": True,
            "removeFailedDownloads": True,
        }
    ]
    _mock_base_gets(respx_mock, sonarr_tag_managed_fixture, downloadclients=orphan_unmanaged)
    delete_route = respx_mock.delete(
        url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$"
    ).mock(return_value=httpx.Response(204))

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=True),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert delete_route.call_count == 1
    assert any(p.action == Action.DELETE and p.name == "manual-qbit" for p in result.plan)


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
        download_clients=DownloadClientsSection(prune=True),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
        download_clients=DownloadClientsSection(prune=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=desired,
            remote_path_mappings=[],
        ),
        dry_run=True,
    )

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
        download_clients=DownloadClientsSection(prune=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=desired,
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
        download_clients=DownloadClientsSection(prune=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[new_dc],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
        download_clients=DownloadClientsSection(prune=True),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
    remotepathmappings: list[dict[str, Any]] | None = None,
    series: list[dict[str, Any]] | None = None,
) -> None:
    """Mock every GET endpoint the extended reconciler touches.

    Defaults to empty lists for list resources. host_config GET is only
    mocked if `hostconfig` is provided — tests for the skipped branch should
    NOT pass a hostconfig fixture so respx records 0 calls.

    Phase-5 additions: /remotepathmapping and /series are always mocked (default
    empty) because the Phase-5 reconciler calls these in every run.
    """
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=tag_fixture))
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=indexers or []))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=rootfolders or []))
    respx_mock.get("/downloadclient").mock(
        return_value=httpx.Response(200, json=downloadclients or [])
    )
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=notifications or []))
    respx_mock.get("/remotepathmapping").mock(
        return_value=httpx.Response(200, json=remotepathmappings or [])
    )
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=series or []))
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
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
        root_folders=RootFoldersSection(prune=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[rf],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
        root_folders=RootFoldersSection(prune=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=desired,
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

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


# ---------------------------------------------------------------------------
# Phase-5 extension tests (D-05-SPLIT-01, D-05-ORDER-01, label→id resolver)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_split_three_tags_three_root_folders_three_download_clients(
    respx_mock: respx.MockRouter,
) -> None:
    """ADR-7 split: 3 tags + 3 root folders + 3 download clients in a single reconcile.

    After reconcile:
    - 3 POSTs to /tag (tv, anime, family — managed tag already exists).
    - 3 POSTs to /rootfolder (new media paths).
    - 3 POSTs to /downloadclient.
    - Download client POST bodies must contain INTEGER tag IDs (label resolution worked),
      not string labels.
    """
    managed_tag = {"id": 1, "label": "arrconf-managed"}
    tv_id, anime_id, family_id = 2, 3, 4

    # /tag: GET returns managed tag; POST creates each new tag in sequence.
    tag_responses = iter(
        [
            httpx.Response(201, json={"id": tv_id, "label": "tv"}),
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
                    {"id": tv_id, "label": "tv"},
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
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=[]))

    tv_dc = DownloadClient(
        name="qbit-tv",
        protocol="torrent",
        implementation="QBittorrent",
        configContract="QBittorrentSettings",
        tag_labels=["tv"],
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

    instance = SonarrInstance(
        base_url="http://sonarr.test",
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[TagItem(label="tv"), TagItem(label="anime"), TagItem(label="family")],
            root_folders=[
                RootFolder(path="/media/series"),
                RootFolder(path="/media/anime"),
                RootFolder(path="/media/family"),
            ],
            download_clients=[tv_dc, anime_dc, family_dc],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    # 3 tag POSTs (tv, anime, family).
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


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_reconcile_order(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D-05-ORDER-01 regression: step_begin events must appear in the exact fixed order.

    Captures the structured-log output (JSON lines written to stdout by the configured
    structlog processor chain) and asserts that step_begin events appear in the
    D-05-ORDER-01 sequence. Uses capsys rather than structlog.testing.capture_logs()
    because cache_logger_on_first_use=True (set by configure_logging() in CLI tests)
    can freeze the bound logger before capture_logs() can inject its processor.
    """
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture)

    instance = SonarrInstance(base_url="http://sonarr.test")
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")

    # Use structlog.testing.capture_logs() when possible; fall back to capsys JSON parsing.
    # Both approaches are tried: capture_logs() is clean when the logger is not cached;
    # capsys parsing is robust regardless of the processor chain state.
    step_events: list[dict[str, Any]] = []

    with structlog.testing.capture_logs() as cap_logs:
        reconcile_sonarr(
            client,
            instance,
            SonarrDerived(
                tags=[],
                root_folders=[],
                download_clients=[],
                remote_path_mappings=[],
            ),
            dry_run=False,
        )

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
        f"D-05-ORDER-01: expected at least 4 step_begin events, got {len(step_events)}. "
        f"Events: {step_events}"
    )

    # The step_index must be strictly increasing (D-05-ORDER-01 invariant).
    indices = [e["step_index"] for e in step_events]
    assert indices == sorted(indices), (
        f"D-05-ORDER-01 violated! step_index sequence must be monotonically increasing. "
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
        "series_tags",
        "content_tags",  # Phase 6 D-06-RETAG-01 — LAST step (step_index=10)
    ]
    assert step_names == canonical_order, (
        f"D-05-ORDER-01 violated! Expected step order:\n  {canonical_order}\nGot:\n  {step_names}"
    )


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_download_client_tags_label_resolution_uses_just_created_id(
    respx_mock: respx.MockRouter,
) -> None:
    """D-05-ORDER-01 dispositive: label resolver uses IDs from the tags step, not from cache.

    Fixture: GET /tag returns [] (no tags exist). YAML declares tag {label: tv} AND
    download_client with tag_labels=[tv]. After reconcile: the download_client POST
    body's tags field must contain the ID returned by the just-completed POST /tag.

    This proves the label→id resolver runs AFTER the tags POST completes (step 2
    before step 6 per D-05-ORDER-01).
    """
    just_created_tv_id = 42  # Non-trivial id to prove the resolver used the POST response.

    # GET /tag: first and second calls return [] (no pre-existing tags).
    # Third call (re-fetch after reconcile) returns the newly created tag.
    respx_mock.get("/tag").mock(
        side_effect=[
            httpx.Response(200, json=[]),  # _ensure_managed_tag
            httpx.Response(200, json=[]),  # _reconcile_tags (before)
            httpx.Response(200, json=[{"id": just_created_tv_id, "label": "tv"}]),  # re-fetch
        ]
    )
    # POST /tag for "tv" returns the server-assigned id=42.
    respx_mock.post("/tag").mock(
        return_value=httpx.Response(201, json={"id": just_created_tv_id, "label": "tv"})
    )

    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=[]))

    dc_post_bodies: list[dict[str, Any]] = []

    def _capture_dc_post(request: httpx.Request) -> httpx.Response:
        dc_post_bodies.append(json.loads(request.content.decode()))
        return httpx.Response(201, json={"id": 1})

    respx_mock.post("/downloadclient").mock(side_effect=_capture_dc_post)

    tv_dc = DownloadClient(
        name="qbit-tv",
        protocol="torrent",
        implementation="QBittorrent",
        configContract="QBittorrentSettings",
        tag_labels=["tv"],
    )
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        series_tags=SeriesTagsSection(enable=False),  # disable to keep test focused
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[TagItem(label="tv")],
            root_folders=[],
            download_clients=[tv_dc],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert len(dc_post_bodies) == 1, "Expected exactly one download client POST"
    tags_in_body = dc_post_bodies[0].get("tags", [])

    assert just_created_tv_id in tags_in_body, (
        f"Label resolver must use the id={just_created_tv_id} returned by the just-completed "
        f"POST /tag, not a stale/string value. Got tags: {tags_in_body}"
    )
    # String "tv" must NOT be in the tags field.
    assert "tv" not in tags_in_body, (
        f"String 'tv' must not appear in tags body — label resolution must produce integer. "
        f"Got: {tags_in_body}"
    )


# ---------------------------------------------------------------------------
# Phase 22 prune tests — root_folders, tags, catch-all DC
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_root_folder_prune_deletes_legacy_path(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """D-04/D-05: cluster has /media/anime (legacy), desired has only Category paths.
    With root_folders.prune=True → DELETE issued for the legacy path.
    """
    legacy_rf = [
        {
            "id": 10,
            "path": "/media/anime",
            "accessible": True,
            "freeSpace": 0,
            "unmappedFolders": [],
        }
    ]
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture, rootfolders=legacy_rf)
    # Mock DELETE (prune) and POST (ADD /media/series which is new in desired).
    delete_rf = respx_mock.delete(url__regex=r"^http://sonarr\.test/api/v3/rootfolder/\d+$").mock(
        return_value=httpx.Response(200)
    )
    respx_mock.post("/rootfolder").mock(
        return_value=httpx.Response(201, json={"id": 11, "path": "/media/series"})
    )

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        root_folders=RootFoldersSection(prune=True),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[RootFolder(path="/media/series")],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    # result.plan only contains the DC plan; root_folder actions are in actions_taken.
    assert delete_rf.call_count == 1
    assert "delete:/media/anime" in result.actions_taken


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_root_folder_prune_false_skips_legacy(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """prune=False → legacy /media/anime root folder is PRUNE_SKIP, 0 DELETE."""
    legacy_rf = [
        {
            "id": 10,
            "path": "/media/anime",
            "accessible": True,
            "freeSpace": 0,
            "unmappedFolders": [],
        }
    ]
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture, rootfolders=legacy_rf)
    delete_rf = respx_mock.delete(url__regex=r"^http://sonarr\.test/api/v3/rootfolder/\d+$")
    # Mock POST for the ADD action on /media/series (desired but not in cluster).
    respx_mock.post("/rootfolder").mock(
        return_value=httpx.Response(201, json={"id": 11, "path": "/media/series"})
    )

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        root_folders=RootFoldersSection(prune=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[RootFolder(path="/media/series")],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    # result.plan only contains DC plan. For root_folders, check actions_taken.
    assert delete_rf.call_count == 0
    assert "delete:/media/anime" not in result.actions_taken


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_tag_prune_deletes_legacy_tag(
    respx_mock: respx.MockRouter,
) -> None:
    """D-04/D-05: cluster tags [tv, anime, arrconf-managed]; desired Category tags [tv].
    With tags.prune=True → DELETE for "anime"; "arrconf-managed" NEVER deleted.
    """
    cluster_tags = [
        {"id": 1, "label": "arrconf-managed"},
        {"id": 2, "label": "tv"},
        {"id": 3, "label": "anime"},
    ]
    _mock_phase3_gets(respx_mock, cluster_tags)
    delete_tag = respx_mock.delete(url__regex=r"^http://sonarr\.test/api/v3/tag/\d+$").mock(
        return_value=httpx.Response(200)
    )

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        tags=TagsSection(prune=True),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[TagItem(label="tv")],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    # _reconcile_tags actions do not propagate to result.actions_taken.
    # Verify via respx call counts: exactly 1 DELETE (for "anime"), not for "arrconf-managed".
    assert delete_tag.call_count == 1
    # arrconf-managed is id=1, anime is id=3. Assert the deleted id was 3 (anime).
    deleted_url = str(delete_tag.calls.last.request.url)
    assert deleted_url.endswith("/3"), (
        f"DELETE must target tag id=3 (anime), not arrconf-managed (id=1). Got: {deleted_url}"
    )


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_catch_all_dc_prune_deletes_untagged(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """SC#4 / D-01: catch-all qBittorrent (id=1, tags=[]) deleted when prune=True.
    This is the force_prune path (D-02 PRUNE_PROTECTED bypass for untagged DCs).
    """
    catch_all_dc = [
        {
            "id": 1,
            "name": "qBittorrent",
            "enable": True,
            "protocol": "torrent",
            "priority": 1,
            "implementation": "QBittorrent",
            "configContract": "QBittorrentSettings",
            "fields": [],
            "tags": [],  # untagged catch-all — no arrconf-managed
            "removeCompletedDownloads": True,
            "removeFailedDownloads": True,
        }
    ]
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture, downloadclients=catch_all_dc)
    delete_dc = respx_mock.delete(
        url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$"
    ).mock(return_value=httpx.Response(204))

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=True),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert delete_dc.call_count == 1
    assert any(p.action == Action.DELETE and p.name == "qBittorrent" for p in result.plan)


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_catch_all_dc_prune_false_protects_untagged(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """Regression guard: prune=False → catch-all qBittorrent (untagged) → PRUNE_SKIP."""
    catch_all_dc = [
        {
            "id": 1,
            "name": "qBittorrent",
            "enable": True,
            "protocol": "torrent",
            "priority": 1,
            "implementation": "QBittorrent",
            "configContract": "QBittorrentSettings",
            "fields": [],
            "tags": [],
            "removeCompletedDownloads": True,
            "removeFailedDownloads": True,
        }
    ]
    _mock_phase3_gets(respx_mock, sonarr_tag_managed_fixture, downloadclients=catch_all_dc)
    delete_dc = respx_mock.delete(url__regex=r"^http://sonarr\.test/api/v3/downloadclient/\d+$")

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=False),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert delete_dc.call_count == 0
    assert any(p.action == Action.PRUNE_SKIP and p.name == "qBittorrent" for p in result.plan)
