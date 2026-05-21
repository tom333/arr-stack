"""Tests for D-05-MIG-01 — retroactive series tagging via PUT /api/v3/series/editor.

All HTTP mocked via respx. Tests cover the _reconcile_series_tags sub-reconciler:
idempotence, preservation of operator tags, dry-run, disable gate, and the
critical T-05-CONTENT invariants (moveFiles=False, deleteFiles=False).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import SonarrClient
from arrconf.config import (
    SeriesTagsSection,
    SonarrInstance,
    TagItem,
    TagsSection,
)
from arrconf.exceptions import ReconcileError
from arrconf.generators.categories import SonarrDerived
from arrconf.reconcilers.sonarr import reconcile_sonarr

BASE_URL = "http://sonarr.test"
TV_TAG_ID = 2
MANAGED_TAG_ID = 1


def _mock_full_gets(
    respx_mock: respx.MockRouter,
    *,
    tags: list[dict[str, Any]],
    series: list[dict[str, Any]],
) -> None:
    """Mock all GET endpoints the full reconciler touches for series-editor tests."""
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=tags))
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/series").mock(return_value=httpx.Response(200, json=series))


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_series_editor_adds_default_tag_to_untagged_series(
    respx_mock: respx.MockRouter,
    sonarr_series_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """D-05-MIG-01: untagged series → single PUT /series/editor with all 8 ids.

    Asserts:
    - Exactly ONE PUT to /series/editor.
    - Body contains seriesIds for all 8 untagged series.
    - Body has applyTags="add", moveFiles=false, deleteFiles=false (JSON booleans).
    - Body tags=[<tv_id>].
    """
    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": TV_TAG_ID, "label": "tv"},
    ]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        series=sonarr_series_with_no_tags_fixture,
    )
    editor_route = respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    instance = SonarrInstance(
        base_url=BASE_URL,
        tags=TagsSection(items=[TagItem(label="tv")]),
        series_tags=SeriesTagsSection(enable=True, default_tag="tv"),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=instance.tags.items,
            root_folders=instance.root_folders.items,
            download_clients=instance.download_clients.items,
            remote_path_mappings=instance.remote_path_mappings.items,
        ),
        dry_run=False,
    )

    assert editor_route.call_count == 1, "Expected exactly one PUT to /series/editor"
    body = json.loads(editor_route.calls.last.request.content.decode())

    # All 8 untagged series must appear in the request.
    all_series_ids = [s["id"] for s in sonarr_series_with_no_tags_fixture]
    assert sorted(body["seriesIds"]) == sorted(all_series_ids)

    # Critical invariants (T-05-CONTENT mitigation):
    assert body["applyTags"] == "add", "Must use applyTags='add' — never 'replace'"
    assert body["tags"] == [TV_TAG_ID]
    assert body["moveFiles"] is False, "moveFiles must be False (JSON boolean)"
    assert body["deleteFiles"] is False, "deleteFiles must be False (JSON boolean)"


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_series_editor_idempotent_when_all_tagged(
    respx_mock: respx.MockRouter,
    sonarr_series_with_tv_tag_fixture: list[dict[str, Any]],
) -> None:
    """SC#5 unit signal: all series already tagged → ZERO PUT to /series/editor.

    This is the dispositive idempotence proof for D-05-MIG-01: a second reconcile
    run (cluster in-sync state) issues no write calls.
    """
    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": TV_TAG_ID, "label": "tv"},
    ]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        series=sonarr_series_with_tv_tag_fixture,
    )
    editor_route = respx_mock.put("/series/editor")

    instance = SonarrInstance(
        base_url=BASE_URL,
        tags=TagsSection(items=[TagItem(label="tv")]),
        series_tags=SeriesTagsSection(enable=True, default_tag="tv"),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=instance.tags.items,
            root_folders=instance.root_folders.items,
            download_clients=instance.download_clients.items,
            remote_path_mappings=instance.remote_path_mappings.items,
        ),
        dry_run=False,
    )

    assert editor_route.call_count == 0, (
        "SC#5: idempotence violated — PUT /series/editor issued when all series are tagged"
    )


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_series_editor_preserves_existing_manual_tags(
    respx_mock: respx.MockRouter,
    sonarr_series_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """R-02: series with ANY existing tag is skipped — only truly untagged series are updated.

    The algorithm treats any non-empty tags list as "already tagged". A series with
    tags=[99] (operator-custom) is excluded from the editor PUT seriesIds. The remaining
    7 untagged series receive the default tag via applyTags="add".
    """
    # Make one series "already tagged" with an operator-custom tag (id=99).
    series_mixed = list(sonarr_series_with_no_tags_fixture)  # shallow copy
    series_mixed = [dict(s) for s in series_mixed]  # deep copy each dict
    series_mixed[0] = {**series_mixed[0], "tags": [99]}  # 1 tagged, 7 untagged

    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": TV_TAG_ID, "label": "tv"},
    ]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        series=series_mixed,
    )
    editor_route = respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    instance = SonarrInstance(
        base_url=BASE_URL,
        tags=TagsSection(items=[TagItem(label="tv")]),
        series_tags=SeriesTagsSection(enable=True, default_tag="tv"),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=instance.tags.items,
            root_folders=instance.root_folders.items,
            download_clients=instance.download_clients.items,
            remote_path_mappings=instance.remote_path_mappings.items,
        ),
        dry_run=False,
    )

    assert editor_route.call_count == 1
    body = json.loads(editor_route.calls.last.request.content.decode())

    # The manually-tagged series (index 0) must NOT be in the seriesIds list.
    tagged_series_id = series_mixed[0]["id"]
    assert tagged_series_id not in body["seriesIds"], (
        f"R-02: series {tagged_series_id} already has tags=[99] and must be skipped"
    )
    # The 7 truly untagged series must be present.
    assert len(body["seriesIds"]) == 7


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_series_editor_does_not_move_files(
    respx_mock: respx.MockRouter,
    sonarr_series_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """T-05-CONTENT: editor PUT MUST have moveFiles=False AND deleteFiles=False.

    These are CRITICAL invariants. A bug here would trigger file moves or deletions
    on a REAL production series library (8 entries in prod). Never remove these asserts.
    """
    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": TV_TAG_ID, "label": "tv"},
    ]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        series=sonarr_series_with_no_tags_fixture,
    )
    respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    editor_route = respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json={}))

    instance = SonarrInstance(
        base_url=BASE_URL,
        tags=TagsSection(items=[TagItem(label="tv")]),
        series_tags=SeriesTagsSection(enable=True, default_tag="tv"),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=instance.tags.items,
            root_folders=instance.root_folders.items,
            download_clients=instance.download_clients.items,
            remote_path_mappings=instance.remote_path_mappings.items,
        ),
        dry_run=False,
    )

    assert editor_route.call_count == 1
    body = json.loads(editor_route.calls.last.request.content.decode())

    assert body["moveFiles"] is False, (
        "T-05-CONTENT: moveFiles must be False — file moves on real series library are destructive"
    )
    assert body["deleteFiles"] is False, (
        "T-05-CONTENT: deleteFiles must be False — "
        "file deletion on real series library is irreversible"
    )


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_series_editor_dry_run_emits_no_put(
    respx_mock: respx.MockRouter,
    sonarr_series_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """dry_run=True must suppress the PUT to /series/editor."""
    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": TV_TAG_ID, "label": "tv"},
    ]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        series=sonarr_series_with_no_tags_fixture,
    )
    editor_route = respx_mock.put("/series/editor")

    instance = SonarrInstance(
        base_url=BASE_URL,
        tags=TagsSection(items=[TagItem(label="tv")]),
        series_tags=SeriesTagsSection(enable=True, default_tag="tv"),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=instance.tags.items,
            root_folders=instance.root_folders.items,
            download_clients=instance.download_clients.items,
            remote_path_mappings=instance.remote_path_mappings.items,
        ),
        dry_run=True,
    )

    assert editor_route.call_count == 0, "dry_run=True must not issue PUT to /series/editor"


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_series_editor_skipped_when_section_disabled(
    respx_mock: respx.MockRouter,
) -> None:
    """section.enable=False → no GET /series, no PUT /series/editor."""
    tags_fixture = [{"id": MANAGED_TAG_ID, "label": "arrconf-managed"}]
    # Note: /series is NOT mocked here — if it were called, respx would raise.
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=tags_fixture))
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))
    # Register /series but expect zero calls (enable=False gate).
    series_route = respx_mock.get("/series")
    editor_route = respx_mock.put("/series/editor")

    instance = SonarrInstance(
        base_url=BASE_URL,
        series_tags=SeriesTagsSection(enable=False),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")
    reconcile_sonarr(
        client,
        instance,
        SonarrDerived(
            tags=instance.tags.items,
            root_folders=instance.root_folders.items,
            download_clients=instance.download_clients.items,
            remote_path_mappings=instance.remote_path_mappings.items,
        ),
        dry_run=False,
    )

    assert series_route.call_count == 0, "enable=False: GET /series must not be issued"
    assert editor_route.call_count == 0, "enable=False: PUT /series/editor must not be issued"


@pytest.mark.respx(base_url=f"{BASE_URL}/api/v3", assert_all_called=False)
def test_series_tags_raises_when_default_tag_label_missing_from_yaml(
    respx_mock: respx.MockRouter,
    sonarr_series_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """ReconcileError raised when series_tags.default_tag label not in instance.tags.items.

    The operator must declare the tag in instance.tags.items so it is created
    in step 2 (D-05-ORDER-01) before series_tags runs in step 9.
    """
    # Only the managed tag exists — "tv" is NOT declared in instance.tags.items.
    tags_fixture = [{"id": MANAGED_TAG_ID, "label": "arrconf-managed"}]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        series=sonarr_series_with_no_tags_fixture,
    )

    instance = SonarrInstance(
        base_url=BASE_URL,
        # tags.items is empty — "tv" will not be in all_tags after step 2.
        series_tags=SeriesTagsSection(enable=True, default_tag="tv"),
    )
    client = SonarrClient(base_url=BASE_URL, api_key="fake")

    with pytest.raises(ReconcileError, match="tv"):
        reconcile_sonarr(
            client,
            instance,
            SonarrDerived(
                tags=instance.tags.items,
                root_folders=instance.root_folders.items,
                download_clients=instance.download_clients.items,
                remote_path_mappings=instance.remote_path_mappings.items,
            ),
            dry_run=False,
        )
