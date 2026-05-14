"""Tests for D-05-PATHMAP-01 — Remote Path Mapping reconciler (DELETE+ADD pattern).

Remote Path Mappings have NO PUT endpoint on the Sonarr/Radarr API. Updates are
performed as DELETE (by id) then POST (Pattern 6 in RESEARCH.md). Match key is the
composite tuple (host, remotePath).

Pitfall 6: both remotePath AND localPath MUST end with '/'. The reconciler does NOT
auto-append slashes — YAML is the operator's responsibility. This test file documents
the trailing-slash requirement and provides a smoke test for the gap.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import SonarrClient
from arrconf.config import (
    RemotePathMappingsSection,
    SonarrInstance,
)
from arrconf.reconcilers.sonarr import reconcile_sonarr
from arrconf.resources.sonarr.remote_path_mapping import RemotePathMapping

BASE_URL = "http://sonarr.test"
QBIT_HOST = "qbittorrent.selfhost.svc.cluster.local"
MANAGED_TAG_ID = 1


def _mock_full_gets(
    respx_mock: respx.MockRouter,
    *,
    remotepathmappings: list[dict[str, Any]],
) -> None:
    """Mock all GET endpoints the reconciler touches; focus on /remotepathmapping."""
    tags = [{"id": MANAGED_TAG_ID, "label": "arrconf-managed"}]
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=tags))
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/remotepathmapping").mock(
        return_value=httpx.Response(200, json=remotepathmappings)
    )
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=[]))


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_rpm_add_new_mapping(
    respx_mock: respx.MockRouter,
    sonarr_remotepathmapping_fixture: list[dict[str, Any]],
) -> None:
    """Cluster has 1 entry; YAML declares 4 entries → 3 POSTs, zero DELETEs."""
    # Cluster baseline: 1 existing entry (/data/complete/ → /data/torrents/complete/).
    _mock_full_gets(respx_mock, remotepathmappings=sonarr_remotepathmapping_fixture)
    post_route = respx_mock.post("/remotepathmapping").mock(
        return_value=httpx.Response(201, json={"id": 99})
    )
    delete_route = respx_mock.delete(
        url__regex=r"^http://sonarr\.test/api/v3/remotepathmapping/\d+$"
    )

    # YAML: the existing + 3 new entries for the split.
    desired = [
        RemotePathMapping(
            host=QBIT_HOST,
            remotePath="/data/complete/",
            localPath="/data/torrents/complete/",
        ),
        RemotePathMapping(
            host=QBIT_HOST,
            remotePath="/data/anime/",
            localPath="/data/torrents/anime/",
        ),
        RemotePathMapping(
            host=QBIT_HOST,
            remotePath="/data/family/",
            localPath="/data/torrents/family/",
        ),
        RemotePathMapping(
            host=QBIT_HOST,
            remotePath="/data/movies/",
            localPath="/data/torrents/movies/",
        ),
    ]
    instance = SonarrInstance(
        base_url=BASE_URL,
        remote_path_mappings=RemotePathMappingsSection(items=desired),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert post_route.call_count == 3, f"Expected 3 POSTs, got {post_route.call_count}"
    assert delete_route.call_count == 0, "Existing entry is in-sync — no DELETEs"


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_rpm_delete_plus_add_on_localpath_change(
    respx_mock: respx.MockRouter,
) -> None:
    """UPDATE = DELETE (old id) then POST (new body) — no PUT endpoint (RESEARCH Pattern 6).

    The composite key (host, remotePath) matches; localPath differs → DELETE + ADD.
    Order matters: DELETE must precede the POST.
    """
    cluster = [
        {
            "id": 5,
            "host": QBIT_HOST,
            "remotePath": "/data/complete/",
            "localPath": "/data/torrents/old/",
        }
    ]
    _mock_full_gets(respx_mock, remotepathmappings=cluster)

    calls_order: list[str] = []

    def _on_delete(request: httpx.Request) -> httpx.Response:
        calls_order.append("DELETE")
        return httpx.Response(200)

    def _on_post(request: httpx.Request) -> httpx.Response:
        calls_order.append("POST")
        return httpx.Response(201, json={"id": 6})

    respx_mock.delete(
        url__regex=r"^http://sonarr\.test/api/v3/remotepathmapping/\d+$"
    ).mock(side_effect=_on_delete)
    respx_mock.post("/remotepathmapping").mock(side_effect=_on_post)

    desired = [
        RemotePathMapping(
            host=QBIT_HOST,
            remotePath="/data/complete/",
            localPath="/data/torrents/new/",  # localPath changed
        )
    ]
    instance = SonarrInstance(
        base_url=BASE_URL,
        remote_path_mappings=RemotePathMappingsSection(items=desired),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert calls_order == ["DELETE", "POST"], (
        f"Pattern 6: DELETE must precede POST. Got order: {calls_order}"
    )

    # Verify the POST body contains the new localPath.
    post_calls = [c for c in respx_mock.calls if c.request.method == "POST"]
    assert len(post_calls) == 1
    body = json.loads(post_calls[0].request.content.decode())
    assert body["localPath"] == "/data/torrents/new/"


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_rpm_no_op_when_in_sync(
    respx_mock: respx.MockRouter,
    sonarr_remotepathmapping_fixture: list[dict[str, Any]],
) -> None:
    """Cluster state matches YAML exactly → zero writes (idempotence)."""
    _mock_full_gets(respx_mock, remotepathmappings=sonarr_remotepathmapping_fixture)
    post_route = respx_mock.post("/remotepathmapping")
    delete_route = respx_mock.delete(
        url__regex=r"^http://sonarr\.test/api/v3/remotepathmapping/\d+$"
    )

    # Mirror the cluster fixture back into desired (same host + paths):
    desired = [RemotePathMapping.model_validate(e) for e in sonarr_remotepathmapping_fixture]
    instance = SonarrInstance(
        base_url=BASE_URL,
        remote_path_mappings=RemotePathMappingsSection(items=desired),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")
    reconcile_sonarr(client, instance, dry_run=False)

    assert post_route.call_count == 0, "In-sync: no POST expected"
    assert delete_route.call_count == 0, "In-sync: no DELETE expected"


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_rpm_match_by_host_and_remote_path_tuple(
    respx_mock: respx.MockRouter,
) -> None:
    """Composite-key match: (host=A, remotePath=/x/) and (host=B, remotePath=/x/) are distinct.

    With prune=False: B entry survives (not in desired → logged as prune_skip, not deleted).
    With prune=True: B entry is DELETEd.
    """
    cluster = [
        {"id": 1, "host": "host-a", "remotePath": "/x/", "localPath": "/local-a/"},
        {"id": 2, "host": "host-b", "remotePath": "/x/", "localPath": "/local-b/"},
    ]
    _mock_full_gets(respx_mock, remotepathmappings=cluster)
    delete_route = respx_mock.delete(
        url__regex=r"^http://sonarr\.test/api/v3/remotepathmapping/\d+$"
    )

    # YAML keeps only the A entry; B entry is orphaned in cluster.
    desired = [
        RemotePathMapping(host="host-a", remotePath="/x/", localPath="/local-a/")
    ]

    # --- prune=False: B entry NOT deleted ---
    instance_no_prune = SonarrInstance(
        base_url=BASE_URL,
        remote_path_mappings=RemotePathMappingsSection(prune=False, items=desired),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")
    reconcile_sonarr(client, instance_no_prune, dry_run=False)

    assert delete_route.call_count == 0, (
        "prune=False: orphaned cluster entry (host=B) must NOT be deleted"
    )


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_rpm_prune_true_deletes_orphan(
    respx_mock: respx.MockRouter,
) -> None:
    """prune=True deletes cluster entries not in desired (complement of test above)."""
    cluster = [
        {"id": 1, "host": "host-a", "remotePath": "/x/", "localPath": "/local-a/"},
        {"id": 2, "host": "host-b", "remotePath": "/x/", "localPath": "/local-b/"},
    ]
    _mock_full_gets(respx_mock, remotepathmappings=cluster)
    delete_route = respx_mock.delete(
        url__regex=r"^http://sonarr\.test/api/v3/remotepathmapping/\d+$"
    ).mock(return_value=httpx.Response(200))

    # YAML keeps only the A entry; B entry is orphaned in cluster.
    desired = [
        RemotePathMapping(host="host-a", remotePath="/x/", localPath="/local-a/")
    ]
    instance_prune = SonarrInstance(
        base_url=BASE_URL,
        remote_path_mappings=RemotePathMappingsSection(prune=True, items=desired),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")
    reconcile_sonarr(client, instance_prune, dry_run=False)

    assert delete_route.call_count == 1, (
        "prune=True: orphaned cluster entry (host=B, id=2) must be DELETEd"
    )


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_rpm_trailing_slash_invariant(
    respx_mock: respx.MockRouter,
) -> None:
    """Pitfall 6 documentation: trailing slashes are the operator's responsibility.

    The reconciler does NOT auto-append slashes to remotePath or localPath.
    YAML must supply correct values with trailing slashes. This test documents
    the gap: a mapping without trailing slash passes through without error,
    but Sonarr's literal prefix-replacement will silently fail at import time.

    Known gap: trailing-slash validation is NOT enforced by the reconciler.
    Plan 07 (chart-side YAML) must enforce this via inline review.
    If this test starts failing (because validation was added), update the
    SUMMARY.md to reflect the improvement.
    """
    # YAML has remotePath WITHOUT trailing slash — the reconciler accepts it.
    no_trailing_slash = RemotePathMapping(
        host=QBIT_HOST,
        remotePath="/data/anime",  # Missing trailing slash (Pitfall 6).
        localPath="/data/torrents/anime/",
    )
    cluster: list[dict[str, Any]] = []
    _mock_full_gets(respx_mock, remotepathmappings=cluster)
    post_route = respx_mock.post("/remotepathmapping").mock(
        return_value=httpx.Response(201, json={"id": 10})
    )

    instance = SonarrInstance(
        base_url=BASE_URL,
        remote_path_mappings=RemotePathMappingsSection(items=[no_trailing_slash]),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")

    # The reconciler currently ACCEPTS values without trailing slashes.
    # No exception should be raised — the test documents this known gap.
    reconcile_sonarr(client, instance, dry_run=False)

    assert post_route.call_count == 1, "POST is issued even without trailing slash"
    body = json.loads(post_route.calls.last.request.content.decode())
    # The slash is absent in the POST body — Sonarr will silently fail at import.
    assert not body["remotePath"].endswith("/"), (
        "Known gap (Pitfall 6): reconciler does not auto-append trailing slash. "
        "Plan 07 YAML review is the enforcement point."
    )
