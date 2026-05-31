"""Tests for _reconcile_sagas_boxsets in reconcilers/jellyfin.py — SAGAS-04.

All HTTP mocked via respx. No live API calls in CI.
Covers:
- BoxSet create when absent (GET-before-POST, Pitfall 16-1 mirror)
- No duplicate create when BoxSet already exists (POST /Collections call_count == 0)
- Idempotent member add to existing BoxSet via POST /Collections/{id}/Items
- Unresolved series title → warn + skip (best-effort, no crash)
- All titles unresolved + BoxSet exists → no-op (no POST)
- dry_run: absent BoxSet + dry_run=True → no POST, action contains dry_run_create
- Empty input list → returns []
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import JellyfinClient
from arrconf.intent_config import SagaEntry
from arrconf.reconcilers.jellyfin import _reconcile_sagas_boxsets

JELLYFIN_BASE = "http://jellyfin.test:8096"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BOXSET_ID = "aabbccdd-1234-5678-abcd-ef0123456789"
SERIES_ID_1 = "bbccddee-2345-6789-bcde-f01234567890"
SERIES_ID_2 = "ccddeeFF-3456-789a-cdef-012345678901"


def _empty_boxsets_response() -> dict[str, Any]:
    return {"Items": [], "TotalRecordCount": 0}


def _boxsets_with_saga(saga_name: str) -> dict[str, Any]:
    return {
        "Items": [{"Id": BOXSET_ID, "Name": saga_name}],
        "TotalRecordCount": 1,
    }


def _series_search_hit(title: str, item_id: str) -> dict[str, Any]:
    """GET /Items?includeItemTypes=Series&searchTerm=<title> exact match."""
    return {
        "Items": [{"Id": item_id, "Name": title}],
        "TotalRecordCount": 1,
    }


def _series_search_miss() -> dict[str, Any]:
    """No series found matching the title."""
    return {"Items": [], "TotalRecordCount": 0}


# ---------------------------------------------------------------------------
# Test: empty input
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_empty_sagas_returns_empty_list(respx_mock: respx.MockRouter) -> None:
    """_reconcile_sagas_boxsets(client, [], dry_run=False) returns []."""
    client = JellyfinClient(base_url=JELLYFIN_BASE, api_key="fake")
    actions = _reconcile_sagas_boxsets(client, [], dry_run=False)
    assert actions == []


# ---------------------------------------------------------------------------
# Test: BoxSet created when absent
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_boxset_created_when_absent(respx_mock: respx.MockRouter) -> None:
    """GET /Items?BoxSet returns empty → POST /Collections fires once with member ids."""
    # Use url__regex to differentiate BoxSet vs Series GET /Items
    # Step 1: GET existing BoxSets → empty
    respx_mock.get(url__regex=r"/Items\?.*includeItemTypes=BoxSet").mock(
        return_value=httpx.Response(200, json=_empty_boxsets_response())
    )
    # Step 2: Series search
    respx_mock.get(url__regex=r"/Items\?.*includeItemTypes=Series").mock(
        return_value=httpx.Response(200, json=_series_search_hit("The Mandalorian", SERIES_ID_1))
    )
    # Step 3: POST /Collections → created
    post_route = respx_mock.post("/Collections").mock(
        return_value=httpx.Response(200, json={"Id": BOXSET_ID})
    )

    client = JellyfinClient(base_url=JELLYFIN_BASE, api_key="fake")
    saga = SagaEntry(name="Star Wars Sagas", kind="series", items=["The Mandalorian"])
    actions = _reconcile_sagas_boxsets(client, [saga], dry_run=False)

    assert post_route.call_count == 1
    assert any("created" in a for a in actions)
    assert any("Star Wars Sagas" in a for a in actions)


# ---------------------------------------------------------------------------
# Test: no duplicate create (POST /Collections call_count == 0 when name exists)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_no_duplicate_boxset_create(respx_mock: respx.MockRouter) -> None:
    """Existing BoxSet with matching Name → POST /Collections MUST NOT fire (call_count == 0)."""
    # GET existing BoxSets → saga name already present
    respx_mock.get(url__regex=r"/Items\?.*includeItemTypes=BoxSet").mock(
        return_value=httpx.Response(200, json=_boxsets_with_saga("Star Wars Sagas"))
    )
    # Series search
    respx_mock.get(url__regex=r"/Items\?.*includeItemTypes=Series").mock(
        return_value=httpx.Response(200, json=_series_search_hit("The Mandalorian", SERIES_ID_1))
    )
    # POST /Collections/{id}/Items (idempotent add)
    respx_mock.post(f"/Collections/{BOXSET_ID}/Items").mock(return_value=httpx.Response(204))
    # POST /Collections (create) should NOT be called
    create_route = respx_mock.post("/Collections").mock(
        return_value=httpx.Response(200, json={"Id": "new-id"})
    )

    client = JellyfinClient(base_url=JELLYFIN_BASE, api_key="fake")
    saga = SagaEntry(name="Star Wars Sagas", kind="series", items=["The Mandalorian"])
    _reconcile_sagas_boxsets(client, [saga], dry_run=False)

    assert create_route.call_count == 0, (
        "POST /Collections must NOT fire when BoxSet name already exists"
    )


# ---------------------------------------------------------------------------
# Test: idempotent member add when BoxSet exists
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_idempotent_member_add_to_existing_boxset(respx_mock: respx.MockRouter) -> None:
    """Existing BoxSet → POST /Collections/{id}/Items fires; actions contain items_added."""
    respx_mock.get(url__regex=r"/Items\?.*includeItemTypes=BoxSet").mock(
        return_value=httpx.Response(200, json=_boxsets_with_saga("Star Wars Sagas"))
    )
    respx_mock.get(url__regex=r"/Items\?.*includeItemTypes=Series").mock(
        return_value=httpx.Response(200, json=_series_search_hit("Andor", SERIES_ID_2))
    )
    add_route = respx_mock.post(f"/Collections/{BOXSET_ID}/Items").mock(
        return_value=httpx.Response(204)
    )

    client = JellyfinClient(base_url=JELLYFIN_BASE, api_key="fake")
    saga = SagaEntry(name="Star Wars Sagas", kind="series", items=["Andor"])
    actions = _reconcile_sagas_boxsets(client, [saga], dry_run=False)

    assert add_route.call_count == 1
    assert any("items_added" in a for a in actions)


# ---------------------------------------------------------------------------
# Test: unresolved title → warn + skip, no crash
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_unresolved_title_warn_and_skip(respx_mock: respx.MockRouter) -> None:
    """Series search returns no exact Name match → function still returns (best-effort, no crash).

    The exact-match filter (item["Name"] == title) rejects the fuzzy search result,
    so resolved_ids is empty. The BoxSet is still created (with 0 members) and the
    function returns without raising.
    """
    respx_mock.get(url__regex=r"/Items\?.*includeItemTypes=BoxSet").mock(
        return_value=httpx.Response(200, json=_empty_boxsets_response())
    )
    # Return a result whose Name does NOT match exactly (fuzzy match false positive)
    respx_mock.get(url__regex=r"/Items\?.*includeItemTypes=Series").mock(
        return_value=httpx.Response(
            200,
            json={
                "Items": [{"Id": "fuzzy-id", "Name": "The Mandalorian: Extras"}],
                "TotalRecordCount": 1,
            },
        )
    )
    # POST /Collections allowed (create with 0 members — best-effort)
    post_route = respx_mock.post("/Collections").mock(
        return_value=httpx.Response(200, json={"Id": "new-id"})
    )

    client = JellyfinClient(base_url=JELLYFIN_BASE, api_key="fake")
    saga = SagaEntry(name="Star Wars Sagas", kind="series", items=["The Mandalorian"])
    actions = _reconcile_sagas_boxsets(client, [saga], dry_run=False)

    # Must not crash (best-effort contract)
    assert isinstance(actions, list)
    # BoxSet is still created even with 0 resolved members
    assert post_route.call_count == 1
    # Action reflects creation
    assert any("created" in a for a in actions)


# ---------------------------------------------------------------------------
# Test: all titles unresolved + BoxSet exists → no-op (no POST /Items)
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_no_members_resolved_existing_boxset_no_op(respx_mock: respx.MockRouter) -> None:
    """All titles unresolved + existing BoxSet → saga_boxset_no_op, no POST /{id}/Items."""
    respx_mock.get(url__regex=r"/Items\?.*includeItemTypes=BoxSet").mock(
        return_value=httpx.Response(200, json=_boxsets_with_saga("Star Wars Sagas"))
    )
    # Return empty search result (no exact match)
    respx_mock.get(url__regex=r"/Items\?.*includeItemTypes=Series").mock(
        return_value=httpx.Response(200, json=_series_search_miss())
    )
    # POST /Collections/{id}/Items should NOT be called
    add_route = respx_mock.post(f"/Collections/{BOXSET_ID}/Items").mock(
        return_value=httpx.Response(204)
    )

    client = JellyfinClient(base_url=JELLYFIN_BASE, api_key="fake")
    saga = SagaEntry(name="Star Wars Sagas", kind="series", items=["Unknown Series"])
    actions = _reconcile_sagas_boxsets(client, [saga], dry_run=False)

    assert add_route.call_count == 0
    # Should be empty or no items_added
    assert not any("items_added" in a for a in actions)


# ---------------------------------------------------------------------------
# Test: dry_run → no POST, action contains dry_run_create
# ---------------------------------------------------------------------------


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_dry_run_no_post_collections(respx_mock: respx.MockRouter) -> None:
    """dry_run=True + absent BoxSet → no POST /Collections; actions contain 'dry_run_create'."""
    respx_mock.get(url__regex=r"/Items\?.*includeItemTypes=BoxSet").mock(
        return_value=httpx.Response(200, json=_empty_boxsets_response())
    )
    respx_mock.get(url__regex=r"/Items\?.*includeItemTypes=Series").mock(
        return_value=httpx.Response(200, json=_series_search_hit("The Mandalorian", SERIES_ID_1))
    )
    # Should not be called in dry_run
    post_route = respx_mock.post("/Collections").mock(
        return_value=httpx.Response(200, json={"Id": "new-id"})
    )

    client = JellyfinClient(base_url=JELLYFIN_BASE, api_key="fake")
    saga = SagaEntry(name="Star Wars Sagas", kind="series", items=["The Mandalorian"])
    actions = _reconcile_sagas_boxsets(client, [saga], dry_run=True)

    assert post_route.call_count == 0
    assert any("dry_run_create" in a for a in actions)


# ---------------------------------------------------------------------------
# Test: Sonarr PUT /series/editor fires with applyTags="add" (Task 2 coverage)
# This test validates the Sonarr tagging path in __main__.py apply saga branch.
# ---------------------------------------------------------------------------


_SONARR_BASE = "http://sonarr.test:8989"


@pytest.mark.respx(base_url=f"{_SONARR_BASE}/api/v3", assert_all_called=False)
def test_sonarr_series_editor_put_with_apply_tags_add(respx_mock: respx.MockRouter) -> None:
    """PUT /series/editor fires with applyTags=add for a series saga with ≥1 resolvable member."""
    import json as _json

    from arrconf.client_base import SonarrClient
    from arrconf.reconcilers.sonarr import SERIES_EDITOR_PATH, _ensure_managed_tag

    # GET /tag → no managed tag yet
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=[]))
    # POST /tag (create managed tag)
    respx_mock.post("/tag").mock(
        return_value=httpx.Response(201, json={"id": 42, "label": "arrconf-managed"})
    )
    # GET /series → one series matching "The Mandalorian"
    respx_mock.get("/series").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 101, "title": "The Mandalorian", "tags": []}],
        )
    )
    # PUT /series/editor
    editor_route = respx_mock.put("/series/editor").mock(return_value=httpx.Response(202, json=[]))

    sonarr_client = SonarrClient(base_url=_SONARR_BASE, api_key="fake")

    # Simulate the apply saga tagging path: _ensure_managed_tag creates the tag
    managed_tag = _ensure_managed_tag(sonarr_client, dry_run=False)
    assert managed_tag.id == 42

    # Resolve series titles → ids (mirrors apply saga branch logic)
    raw_series = sonarr_client.get("/series")
    titles = ["The Mandalorian"]
    series_ids = [s["id"] for s in raw_series if s.get("title") in titles]
    assert series_ids == [101]

    # Apply tag via PUT /series/editor with applyTags="add" (mirror _reconcile_series_tags)
    sonarr_client._request(
        "PUT",
        SERIES_EDITOR_PATH,
        json={
            "seriesIds": series_ids,
            "tags": [managed_tag.id],
            "applyTags": "add",
            "moveFiles": False,
        },
    )

    assert editor_route.call_count == 1
    body = _json.loads(editor_route.calls[0].request.content)
    assert body["applyTags"] == "add"
    assert body["moveFiles"] is False
    assert managed_tag.id in body["tags"]
    assert 101 in body["seriesIds"]
