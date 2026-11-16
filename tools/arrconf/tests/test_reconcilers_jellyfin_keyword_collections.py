"""Tests for rule-based Jellyfin movie BoxSets (keyword_collections).

All HTTP mocked via respx. Covers the pure member selector and the add-only
reconcile (create when absent, add only missing members, no-op, dry_run).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from pydantic import ValidationError

from arrconf.client_base import JellyfinClient
from arrconf.intent_config import KeywordCollection
from arrconf.reconcilers.jellyfin import (
    _reconcile_keyword_collections,
    select_keyword_collection_members,
)

JELLYFIN_BASE = "http://jellyfin.test:8096"
BOXSET_ID = "box1"
ADMIN_ID = "admin1"

RULE = KeywordCollection(
    name="Noël",
    keywords=["christmas", "santa claus"],
    title_pattern=r"no[eë]l",
    path_prefixes=["/media/films-enfants", "/media/films-animation-enfants/"],
    exclude=["Edward aux mains d'argent"],
)

MOVIES: list[dict[str, Any]] = [
    {
        "Id": "klaus",
        "Name": "Klaus",
        "Path": "/media/films-animation-enfants/Klaus/k.mkv",
        "Tags": ["Christmas", "santa claus"],
    },
    {
        "Id": "neige",
        "Name": "De la neige pour Noël",
        "Path": "/media/films-animation-enfants/N/n.mkv",
        "Tags": [],
    },
    {
        "Id": "diehard",
        "Name": "Piège de cristal",
        "Path": "/media/films/Die Hard/d.mkv",
        "Tags": ["christmas"],
    },
    {
        "Id": "edward",
        "Name": "Edward aux mains d'argent",
        "Path": "/media/films-enfants/E/e.mkv",
        "Tags": ["christmas"],
    },
    {
        "Id": "dory",
        "Name": "Le Monde de Dory",
        "Path": "/media/films-animation-enfants/D/d.mkv",
        "Tags": ["fish"],
    },
    {
        "Id": "lookalike",
        "Name": "Lookalike",
        "Path": "/media/films-enfants-old/L/l.mkv",
        "Tags": ["christmas"],
    },
]


def _client() -> JellyfinClient:
    return JellyfinClient(base_url=JELLYFIN_BASE, api_key="fake")


def _mock_reads(
    respx_mock: respx.MockRouter, boxsets: list[dict[str, Any]], members: list[str]
) -> None:
    def items(request: httpx.Request) -> httpx.Response:
        kind = request.url.params.get("includeItemTypes")
        if kind == "Movie":
            return httpx.Response(200, json={"Items": MOVIES})
        return httpx.Response(200, json={"Items": boxsets})

    respx_mock.get("/Items").mock(side_effect=items)
    respx_mock.get("/Users").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"Id": "kid", "Policy": {"IsAdministrator": False}},
                {"Id": ADMIN_ID, "Policy": {"IsAdministrator": True}},
            ],
        )
    )
    respx_mock.get(f"/Users/{ADMIN_ID}/Items").mock(
        return_value=httpx.Response(200, json={"Items": [{"Id": i} for i in members]})
    )


def test_select_members_applies_paths_keywords_title_and_exclude() -> None:
    assert select_keyword_collection_members(MOVIES, RULE) == ["klaus", "neige"]


def test_rule_requires_keywords_or_title_pattern() -> None:
    with pytest.raises(ValidationError):
        KeywordCollection(name="Vide")


def test_rule_rejects_invalid_regex() -> None:
    with pytest.raises(ValidationError):
        KeywordCollection(name="Bad", title_pattern="(")


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_empty_rules_returns_empty(respx_mock: respx.MockRouter) -> None:
    assert _reconcile_keyword_collections(_client(), [], dry_run=False) == []


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_creates_boxset_when_absent(respx_mock: respx.MockRouter) -> None:
    _mock_reads(respx_mock, boxsets=[], members=[])
    create = respx_mock.post("/Collections").mock(
        return_value=httpx.Response(200, json={"Id": BOXSET_ID})
    )

    actions = _reconcile_keyword_collections(_client(), [RULE], dry_run=False)

    assert create.call_count == 1
    params = create.calls.last.request.url.params
    assert params["name"] == "Noël"
    assert params["ids"] == "klaus,neige"
    assert actions == ["keyword_collection:created:Noël"]


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_adds_only_missing_members(respx_mock: respx.MockRouter) -> None:
    _mock_reads(respx_mock, boxsets=[{"Id": BOXSET_ID, "Name": "Noël"}], members=["klaus"])
    add = respx_mock.post(f"/Collections/{BOXSET_ID}/Items").mock(return_value=httpx.Response(204))
    create = respx_mock.post("/Collections").mock(return_value=httpx.Response(200, json={}))

    actions = _reconcile_keyword_collections(_client(), [RULE], dry_run=False)

    assert create.call_count == 0
    assert add.call_count == 1
    assert add.calls.last.request.url.params["ids"] == "neige"
    assert actions == ["keyword_collection:items_added:Noël:1"]


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_no_op_when_all_members_present(respx_mock: respx.MockRouter) -> None:
    _mock_reads(
        respx_mock,
        boxsets=[{"Id": BOXSET_ID, "Name": "Noël"}],
        members=["klaus", "neige", "hand-added"],
    )
    add = respx_mock.post(f"/Collections/{BOXSET_ID}/Items").mock(return_value=httpx.Response(204))

    assert _reconcile_keyword_collections(_client(), [RULE], dry_run=False) == []
    assert add.call_count == 0


@pytest.mark.respx(base_url=JELLYFIN_BASE, assert_all_called=False)
def test_dry_run_never_posts(respx_mock: respx.MockRouter) -> None:
    _mock_reads(respx_mock, boxsets=[], members=[])
    create = respx_mock.post("/Collections").mock(return_value=httpx.Response(200, json={}))

    actions = _reconcile_keyword_collections(_client(), [RULE], dry_run=True)

    assert create.call_count == 0
    assert actions == ["keyword_collection:dry_run_create:Noël"]
