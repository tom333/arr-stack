import json as _json

import httpx
import pytest
import respx

from arrconf.client_base import SonarrClient
from arrconf.exceptions import ConfigError
from arrconf.reconcilers._category_tags import reconcile_category_tags
from arrconf.resources.categories import Category

BASE = "http://sonarr.test:8989"

CATS = [
    Category(
        name="series",
        kind="series",
        profile="general",
        display="Series",
        base_path="/media/series",
    ),
    Category(
        name="series-zoe",
        kind="series",
        profile="anime",
        display="Series - Zoe",
        base_path="/media/series-zoe",
    ),
]

# tag ids: tv=10, arrconf-managed=1, series=20, series-zoe=21
TAGS = [
    {"id": 1, "label": "arrconf-managed"},
    {"id": 10, "label": "tv"},
    {"id": 20, "label": "series"},
    {"id": 21, "label": "series-zoe"},
]


def _client() -> SonarrClient:
    return SonarrClient(base_url=BASE, api_key="k")


@respx.mock
def test_retags_series_with_stray_tags() -> None:
    respx.get(f"{BASE}/api/v3/tag").mock(return_value=httpx.Response(200, json=TAGS))
    respx.get(f"{BASE}/api/v3/series").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 1, "path": "/media/series/Lucky Luke", "tags": [10, 1, 20]},
            ],
        )
    )
    editor = respx.put(f"{BASE}/api/v3/series/editor").mock(
        return_value=httpx.Response(202, json={})
    )
    actions = reconcile_category_tags(
        _client(),
        CATS,
        item_path="/series",
        editor_path="/series/editor",
        ids_key="seriesIds",
        dry_run=False,
    )
    assert editor.called
    body = _json.loads(editor.calls.last.request.content)
    assert body["seriesIds"] == [1]
    assert body["tags"] == [20]
    assert body["applyTags"] == "set"
    assert actions


@respx.mock
def test_retags_series_under_zoe_bucket() -> None:
    respx.get(f"{BASE}/api/v3/tag").mock(return_value=httpx.Response(200, json=TAGS))
    respx.get(f"{BASE}/api/v3/series").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 2, "path": "/media/series-zoe/Naruto", "tags": []},
            ],
        )
    )
    editor = respx.put(f"{BASE}/api/v3/series/editor").mock(
        return_value=httpx.Response(202, json={})
    )
    reconcile_category_tags(
        _client(),
        CATS,
        item_path="/series",
        editor_path="/series/editor",
        ids_key="seriesIds",
        dry_run=False,
    )
    assert editor.called
    body = _json.loads(editor.calls.last.request.content)
    assert body["seriesIds"] == [2]
    assert body["tags"] == [21]
    assert body["applyTags"] == "set"


@respx.mock
def test_noop_when_already_correctly_tagged() -> None:
    respx.get(f"{BASE}/api/v3/tag").mock(return_value=httpx.Response(200, json=TAGS))
    respx.get(f"{BASE}/api/v3/series").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 3, "path": "/media/series/Already Right", "tags": [20]},
            ],
        )
    )
    editor = respx.put(f"{BASE}/api/v3/series/editor").mock(
        return_value=httpx.Response(202, json={})
    )
    actions = reconcile_category_tags(
        _client(),
        CATS,
        item_path="/series",
        editor_path="/series/editor",
        ids_key="seriesIds",
        dry_run=False,
    )
    assert not editor.called
    assert actions == []


@respx.mock
def test_dry_run_does_not_put() -> None:
    respx.get(f"{BASE}/api/v3/tag").mock(return_value=httpx.Response(200, json=TAGS))
    respx.get(f"{BASE}/api/v3/series").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 1, "path": "/media/series/Lucky Luke", "tags": [10, 1, 20]},
            ],
        )
    )
    editor = respx.put(f"{BASE}/api/v3/series/editor").mock(
        return_value=httpx.Response(202, json={})
    )
    actions = reconcile_category_tags(
        _client(),
        CATS,
        item_path="/series",
        editor_path="/series/editor",
        ids_key="seriesIds",
        dry_run=True,
    )
    assert not editor.called
    assert actions


@respx.mock
def test_missing_tag_label_raises_configerror() -> None:
    respx.get(f"{BASE}/api/v3/tag").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "label": "arrconf-managed"}])
    )
    respx.get(f"{BASE}/api/v3/series").mock(return_value=httpx.Response(200, json=[]))
    with pytest.raises(ConfigError):
        reconcile_category_tags(
            _client(),
            CATS,
            item_path="/series",
            editor_path="/series/editor",
            ids_key="seriesIds",
            dry_run=False,
        )
