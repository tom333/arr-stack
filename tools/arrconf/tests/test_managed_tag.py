"""Tests for the arrconf-managed tag lifecycle — REQ-managed-tag, T-01-04.

Covers _ensure_managed_tag() behaviour:
- Creates the tag when absent.
- Reuses an existing tag without POSTing.
- Dry-run never POSTs (returns sentinel id=-1).
- The tag is added to every desired DownloadClient on apply.
- The tag itself is never DELETEd, even with prune=True on download_clients.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import SonarrClient
from arrconf.config import DownloadClientsSection, SonarrInstance
from arrconf.differ import Action
from arrconf.reconcilers.sonarr import _ensure_managed_tag, reconcile_sonarr
from arrconf.resources.sonarr.download_client import DownloadClient


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_creates_managed_tag_when_missing(
    respx_mock: respx.MockRouter,
    sonarr_tag_empty_fixture: list[dict[str, Any]],
) -> None:
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_empty_fixture))
    post_route = respx_mock.post("/tag").mock(
        return_value=httpx.Response(201, json={"id": 1, "label": "arrconf-managed"})
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    tag = _ensure_managed_tag(client, dry_run=False)
    assert tag.label == "arrconf-managed"
    assert tag.id == 1
    assert post_route.call_count == 1
    body = post_route.calls.last.request.content.decode()
    assert "arrconf-managed" in body


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_returns_existing_managed_tag(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    post_route = respx_mock.post("/tag")
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    tag = _ensure_managed_tag(client, dry_run=False)
    assert tag.id == 1
    assert tag.label == "arrconf-managed"
    assert post_route.call_count == 0


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_dry_run_does_not_post_tag(
    respx_mock: respx.MockRouter,
    sonarr_tag_empty_fixture: list[dict[str, Any]],
) -> None:
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_empty_fixture))
    post_route = respx_mock.post("/tag")
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    tag = _ensure_managed_tag(client, dry_run=True)
    assert tag.label == "arrconf-managed"
    assert tag.id == -1  # placeholder sentinel for dry-run
    assert post_route.call_count == 0


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_managed_tag_added_to_download_client_on_apply(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """When applying, the managed tag id must end up in the POSTed DC body (D-02)."""
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    post_dc = respx_mock.post("/downloadclient").mock(
        return_value=httpx.Response(201, json={"id": 7, "name": "qbit"})
    )

    desired_dc = DownloadClient(
        name="qbit",
        protocol="torrent",
        implementation="QBittorrent",
        configContract="QBittorrentSettings",
        tags=[],
    )
    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=False, items=[desired_dc]),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(client, instance, dry_run=False)

    assert post_dc.call_count == 1
    body = post_dc.calls.last.request.content.decode()
    # The managed tag id (1, from the fixture) must appear in the tags list of the body.
    assert '"tags":[1]' in body or '"tags": [1]' in body
    assert any(p.action == Action.ADD for p in result.plan)


@pytest.mark.respx(base_url="http://sonarr.test/api/v3", assert_all_called=False)
def test_managed_tag_never_deleted_in_prune_mode(
    respx_mock: respx.MockRouter,
    sonarr_tag_managed_fixture: list[dict[str, Any]],
) -> None:
    """Even with prune=True on download_clients, the arrconf-managed tag itself is preserved.

    The reconciler does NOT touch /tag DELETE — Phase 1 only reconciles download_clients
    (D-08). This test asserts no DELETE call to /tag/{id} regardless of prune setting.
    """
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=sonarr_tag_managed_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    delete_tag_route = respx_mock.delete(url__regex=r"^http://sonarr\.test/api/v3/tag/\d+$")

    instance = SonarrInstance(
        base_url="http://sonarr.test",
        download_clients=DownloadClientsSection(prune=True, items=[]),
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert delete_tag_route.call_count == 0
