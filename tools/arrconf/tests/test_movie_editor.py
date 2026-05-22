"""Tests for D-05-MIG-01 Radarr mirror — retroactive movie tagging via PUT /api/v3/movie/editor.

All HTTP mocked via respx. Tests cover the _reconcile_movie_tags sub-reconciler:
idempotence, preservation of operator tags, dry-run, disable gate, and the
critical T-05-CONTENT invariants (moveFiles=False, deleteFiles=False).

Critical schema divergence from Sonarr (RESEARCH lines 220–231):
- Body field ``movieIds`` (NOT ``seriesIds``) — verified by
  test_movie_editor_uses_movieIds_not_seriesIds
- Body field ``addImportExclusion`` (NOT ``addImportListExclusion``) — verified by
  test_movie_editor_uses_addImportExclusion_not_addImportListExclusion
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from arrconf.client_base import RadarrClient
from arrconf.config import (
    MovieTagsSection,
    RadarrInstance,
    TagItem,
)
from arrconf.exceptions import ReconcileError
from arrconf.generators.categories import RadarrDerived
from arrconf.reconcilers.radarr import reconcile_radarr

RADARR_BASE = "http://radarr.test"
MOVIES_TAG_ID = 2
MANAGED_TAG_ID = 1


def _mock_full_gets(
    respx_mock: respx.MockRouter,
    *,
    tags: list[dict[str, Any]],
    movies: list[dict[str, Any]],
) -> None:
    """Mock all GET endpoints the full reconciler touches for movie-editor tests."""
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=tags))
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=movies))


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_movie_editor_adds_default_tag_to_untagged_movies(
    respx_mock: respx.MockRouter,
    radarr_movie_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """D-05-MIG-01 Radarr mirror: untagged movies → single PUT /movie/editor with all 11 ids.

    Asserts:
    - Exactly ONE PUT to /movie/editor.
    - Body contains movieIds for all 11 untagged movies.
    - Body has applyTags="add", moveFiles=false, deleteFiles=false (JSON booleans).
    - Body tags=[<movies_id>].
    - Body addImportExclusion=false (Radarr-specific field, D-05-SPLIT-02).
    """
    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": MOVIES_TAG_ID, "label": "movies"},
    ]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        movies=radarr_movie_with_no_tags_fixture,
    )
    editor_route = respx_mock.put("/movie/editor").mock(return_value=httpx.Response(202, json={}))

    instance = RadarrInstance(
        base_url=RADARR_BASE,
        movie_tags=MovieTagsSection(enable=True, default_tag="movies"),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(
        client,
        instance,
        RadarrDerived(
            tags=[TagItem(label="movies")],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert editor_route.call_count == 1, "Expected exactly one PUT to /movie/editor"
    body = json.loads(editor_route.calls.last.request.content.decode())

    # All 11 untagged movies must appear in the request.
    all_movie_ids = [m["id"] for m in radarr_movie_with_no_tags_fixture]
    assert sorted(body["movieIds"]) == sorted(all_movie_ids)

    # Critical invariants (T-05-CONTENT mitigation):
    assert body["applyTags"] == "add", "Must use applyTags='add' — never 'replace'"
    assert body["tags"] == [MOVIES_TAG_ID]
    assert body["moveFiles"] is False, "moveFiles must be False (JSON boolean)"
    assert body["deleteFiles"] is False, "deleteFiles must be False (JSON boolean)"
    assert body["addImportExclusion"] is False, "addImportExclusion must be False (Radarr-specific)"


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_movie_editor_idempotent_when_all_tagged(
    respx_mock: respx.MockRouter,
    radarr_movie_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """SC#5 unit signal: all movies already tagged → ZERO PUT to /movie/editor.

    This is the dispositive idempotence proof for D-05-MIG-01 Radarr: a second
    reconcile run (cluster in-sync state) issues no write calls.
    """
    # Build "all tagged" variant by setting tags=[MOVIES_TAG_ID] on every movie.
    all_tagged = [{**m, "tags": [MOVIES_TAG_ID]} for m in radarr_movie_with_no_tags_fixture]

    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": MOVIES_TAG_ID, "label": "movies"},
    ]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        movies=all_tagged,
    )
    editor_route = respx_mock.put("/movie/editor")

    instance = RadarrInstance(
        base_url=RADARR_BASE,
        movie_tags=MovieTagsSection(enable=True, default_tag="movies"),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(
        client,
        instance,
        RadarrDerived(
            tags=[TagItem(label="movies")],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert editor_route.call_count == 0, (
        "SC#5: idempotence violated — PUT /movie/editor issued when all movies are tagged"
    )


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_movie_editor_preserves_existing_manual_tags(
    respx_mock: respx.MockRouter,
    radarr_movie_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """R-02: movies with ANY existing tag are skipped — only truly untagged movies are updated.

    The algorithm treats any non-empty tags list as "already tagged". A movie with
    tags=[99] (operator-custom) is excluded from the editor PUT movieIds. The remaining
    10 untagged movies receive the default tag via applyTags="add".
    """
    # Make one movie "already tagged" with an operator-custom tag (id=99).
    movies_mixed = [dict(m) for m in radarr_movie_with_no_tags_fixture]
    movies_mixed[0] = {**movies_mixed[0], "tags": [99]}  # 1 tagged, 10 untagged

    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": MOVIES_TAG_ID, "label": "movies"},
    ]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        movies=movies_mixed,
    )
    editor_route = respx_mock.put("/movie/editor").mock(return_value=httpx.Response(202, json={}))

    instance = RadarrInstance(
        base_url=RADARR_BASE,
        movie_tags=MovieTagsSection(enable=True, default_tag="movies"),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(
        client,
        instance,
        RadarrDerived(
            tags=[TagItem(label="movies")],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert editor_route.call_count == 1
    body = json.loads(editor_route.calls.last.request.content.decode())

    # The manually-tagged movie (index 0) must NOT be in the movieIds list.
    tagged_movie_id = movies_mixed[0]["id"]
    assert tagged_movie_id not in body["movieIds"], (
        f"R-02: movie {tagged_movie_id} already has tags=[99] and must be skipped"
    )
    # The 10 truly untagged movies must be present.
    assert len(body["movieIds"]) == 10


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_movie_editor_does_not_move_files(
    respx_mock: respx.MockRouter,
    radarr_movie_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """T-05-CONTENT: editor PUT MUST have moveFiles=False AND deleteFiles=False.

    These are CRITICAL invariants. A bug here would trigger file moves or deletions
    on a REAL production movie library (11 entries in prod). Never remove these asserts.
    """
    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": MOVIES_TAG_ID, "label": "movies"},
    ]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        movies=radarr_movie_with_no_tags_fixture,
    )
    editor_route = respx_mock.put("/movie/editor").mock(return_value=httpx.Response(202, json={}))

    instance = RadarrInstance(
        base_url=RADARR_BASE,
        movie_tags=MovieTagsSection(enable=True, default_tag="movies"),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(
        client,
        instance,
        RadarrDerived(
            tags=[TagItem(label="movies")],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert editor_route.call_count == 1
    body = json.loads(editor_route.calls.last.request.content.decode())

    assert body["moveFiles"] is False, (
        "T-05-CONTENT: moveFiles must be False — file moves on real movie library are destructive"
    )
    assert body["deleteFiles"] is False, (
        "T-05-CONTENT: deleteFiles must be False — "
        "file deletion on real movie library is irreversible"
    )


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_movie_editor_uses_movieIds_not_seriesIds(  # noqa: N802
    respx_mock: respx.MockRouter,
    radarr_movie_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """Schema divergence guard: PUT body must contain 'movieIds', NOT 'seriesIds'.

    Catches future copy-paste-from-Sonarr regressions (RESEARCH lines 220–231).
    A silent bug here would cause the Radarr editor to ignore the request
    (wrong field name → no-op on server), leaving movies untagged.
    """
    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": MOVIES_TAG_ID, "label": "movies"},
    ]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        movies=radarr_movie_with_no_tags_fixture,
    )
    editor_route = respx_mock.put("/movie/editor").mock(return_value=httpx.Response(202, json={}))

    instance = RadarrInstance(
        base_url=RADARR_BASE,
        movie_tags=MovieTagsSection(enable=True, default_tag="movies"),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(
        client,
        instance,
        RadarrDerived(
            tags=[TagItem(label="movies")],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert editor_route.call_count == 1
    body_bytes = editor_route.calls.last.request.content.decode()
    body = json.loads(body_bytes)

    assert "movieIds" in body, (
        "Schema divergence: PUT body must use 'movieIds' (Radarr field), not 'seriesIds'"
    )
    assert "seriesIds" not in body, (
        "Schema divergence: 'seriesIds' is a Sonarr-only field — must NOT appear in Radarr body"
    )


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_movie_editor_uses_addImportExclusion_not_addImportListExclusion(  # noqa: N802
    respx_mock: respx.MockRouter,
    radarr_movie_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """Schema divergence guard: PUT body must use 'addImportExclusion' (singular, no 'List').

    Radarr's MovieEditorResource.cs uses ``addImportExclusion`` (without 'List').
    Sonarr uses ``addImportListExclusion`` (with 'List'). This test is dispositive
    per RESEARCH lines 220–231. A silent bug here would be ignored by Radarr's
    API and is not detectable via response inspection.
    """
    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": MOVIES_TAG_ID, "label": "movies"},
    ]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        movies=radarr_movie_with_no_tags_fixture,
    )
    editor_route = respx_mock.put("/movie/editor").mock(return_value=httpx.Response(202, json={}))

    instance = RadarrInstance(
        base_url=RADARR_BASE,
        movie_tags=MovieTagsSection(enable=True, default_tag="movies"),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(
        client,
        instance,
        RadarrDerived(
            tags=[TagItem(label="movies")],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert editor_route.call_count == 1
    body_bytes = editor_route.calls.last.request.content.decode()
    body = json.loads(body_bytes)

    assert "addImportExclusion" in body, (
        "Schema divergence: PUT body must use 'addImportExclusion' (Radarr, no 'List')"
    )
    assert "addImportListExclusion" not in body, (
        "Schema divergence: 'addImportListExclusion' is Sonarr-only — "
        "must NOT appear in Radarr body"
    )


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_movie_editor_dry_run_emits_no_put(
    respx_mock: respx.MockRouter,
    radarr_movie_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """dry_run=True must suppress the PUT to /movie/editor."""
    tags_fixture = [
        {"id": MANAGED_TAG_ID, "label": "arrconf-managed"},
        {"id": MOVIES_TAG_ID, "label": "movies"},
    ]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        movies=radarr_movie_with_no_tags_fixture,
    )
    editor_route = respx_mock.put("/movie/editor")

    instance = RadarrInstance(
        base_url=RADARR_BASE,
        movie_tags=MovieTagsSection(enable=True, default_tag="movies"),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    reconcile_radarr(
        client,
        instance,
        RadarrDerived(
            tags=[TagItem(label="movies")],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=True,
    )

    assert editor_route.call_count == 0, "dry_run=True must not issue PUT to /movie/editor"


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_movie_editor_skipped_when_section_disabled(
    respx_mock: respx.MockRouter,
) -> None:
    """section.enable=False → no GET /movie, no PUT /movie/editor."""
    tags_fixture = [{"id": MANAGED_TAG_ID, "label": "arrconf-managed"}]
    # Note: /movie is NOT mocked here — if it were called, respx would raise.
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=tags_fixture))
    respx_mock.get("/indexer").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/rootfolder").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/notification").mock(return_value=httpx.Response(200, json=[]))
    respx_mock.get("/remotepathmapping").mock(return_value=httpx.Response(200, json=[]))
    # Register /movie but expect zero calls (enable=False gate).
    movie_route = respx_mock.get("/movie")
    editor_route = respx_mock.put("/movie/editor")

    instance = RadarrInstance(
        base_url=RADARR_BASE,
        movie_tags=MovieTagsSection(enable=False),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")
    # Empty Derived — test focuses on movie_editor gate, not tag/RF/DC reconciliation.
    reconcile_radarr(
        client,
        instance,
        RadarrDerived(
            tags=[],
            root_folders=[],
            download_clients=[],
            remote_path_mappings=[],
        ),
        dry_run=False,
    )

    assert movie_route.call_count == 0, "enable=False: GET /movie must not be issued"
    assert editor_route.call_count == 0, "enable=False: PUT /movie/editor must not be issued"


@pytest.mark.respx(base_url=f"{RADARR_BASE}/api/v3", assert_all_called=False)
def test_movie_tags_raises_when_default_tag_label_missing_from_yaml(
    respx_mock: respx.MockRouter,
    radarr_movie_with_no_tags_fixture: list[dict[str, Any]],
) -> None:
    """ReconcileError raised when movie_tags.default_tag label not in instance.tags.items.

    The operator must declare the tag in instance.tags.items so it is created
    in step 2 (D-05-ORDER-01) before movie_tags runs in step 9.
    """
    # Only the managed tag exists — "movies" is NOT declared in instance.tags.items.
    tags_fixture = [{"id": MANAGED_TAG_ID, "label": "arrconf-managed"}]
    _mock_full_gets(
        respx_mock,
        tags=tags_fixture,
        movies=radarr_movie_with_no_tags_fixture,
    )

    instance = RadarrInstance(
        base_url=RADARR_BASE,
        # tags.items is empty — "movies" will not be in all_tags after step 2.
        movie_tags=MovieTagsSection(enable=True, default_tag="movies"),
    )
    client = RadarrClient(base_url=RADARR_BASE, api_key="fake")

    with pytest.raises(ReconcileError, match="movies"):
        reconcile_radarr(
            client,
            instance,
            RadarrDerived(
                tags=[],
                root_folders=[],
                download_clients=[],
                remote_path_mappings=[],
            ),
            dry_run=False,
        )
