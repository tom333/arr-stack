import httpx
import pytest
import respx

from arrconf.client_base import RadarrClient
from arrconf.exceptions import ConfigError
from arrconf.reconcilers._category_profiles import reconcile_category_profiles
from arrconf.resources.categories import Category

BASE = "http://radarr.test:7878"

CATS = [
    Category(
        name="films-enfants",
        kind="movies",
        profile="family",
        display="Films - Enfants",
        base_path="/media/films-enfants",
    ),
    Category(
        name="films",
        kind="movies",
        profile="general",
        display="Films",
        base_path="/media/films",
    ),
    Category(
        name="films-zoe",
        kind="movies",
        profile="anime",
        display="Films - Zoe",
        base_path="/media/films-zoe",
    ),
]
PROFILE_MAP = {"general": "MULTi.VF", "anime": "Anime", "family": "Family"}
QPROFILES = [
    {"id": 6, "name": "HD - 720p/1080p"},
    {"id": 7, "name": "MULTi.VF"},
    {"id": 8, "name": "Anime"},
    {"id": 9, "name": "Family"},
]


def _client() -> RadarrClient:
    return RadarrClient(base_url=BASE, api_key="k")


@respx.mock
def test_reassigns_item_on_stock_profile() -> None:
    respx.get(f"{BASE}/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=QPROFILES)
    )
    respx.get(f"{BASE}/api/v3/movie").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 1, "path": "/media/films-enfants/Some Movie (2016)", "qualityProfileId": 6}
            ],
        )
    )
    editor = respx.put(f"{BASE}/api/v3/movie/editor").mock(
        return_value=httpx.Response(202, json={})
    )
    actions = reconcile_category_profiles(
        _client(),
        CATS,
        PROFILE_MAP,
        item_path="/movie",
        editor_path="/movie/editor",
        ids_key="movieIds",
        dry_run=False,
    )
    assert editor.called
    import json as _json

    body = _json.loads(editor.calls.last.request.content)
    assert body["movieIds"] == [1]
    assert body["qualityProfileId"] == 9
    assert actions


@respx.mock
def test_skips_item_already_on_managed_profile() -> None:
    respx.get(f"{BASE}/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=QPROFILES)
    )
    respx.get(f"{BASE}/api/v3/movie").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 2, "path": "/media/films-enfants/Pinned (2020)", "qualityProfileId": 7}],
        )
    )
    editor = respx.put(f"{BASE}/api/v3/movie/editor").mock(
        return_value=httpx.Response(202, json={})
    )
    actions = reconcile_category_profiles(
        _client(),
        CATS,
        PROFILE_MAP,
        item_path="/movie",
        editor_path="/movie/editor",
        ids_key="movieIds",
        dry_run=False,
    )
    assert not editor.called
    assert actions == []


@respx.mock
def test_skips_unmapped_path() -> None:
    respx.get(f"{BASE}/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=QPROFILES)
    )
    respx.get(f"{BASE}/api/v3/movie").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 3, "path": "/media/unknown-bucket/X (2019)", "qualityProfileId": 6}],
        )
    )
    editor = respx.put(f"{BASE}/api/v3/movie/editor").mock(
        return_value=httpx.Response(202, json={})
    )
    reconcile_category_profiles(
        _client(),
        CATS,
        PROFILE_MAP,
        item_path="/movie",
        editor_path="/movie/editor",
        ids_key="movieIds",
        dry_run=False,
    )
    assert not editor.called


@respx.mock
def test_dry_run_does_not_put() -> None:
    respx.get(f"{BASE}/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=QPROFILES)
    )
    respx.get(f"{BASE}/api/v3/movie").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 1, "path": "/media/films-enfants/M (2016)", "qualityProfileId": 6}],
        )
    )
    editor = respx.put(f"{BASE}/api/v3/movie/editor").mock(
        return_value=httpx.Response(202, json={})
    )
    actions = reconcile_category_profiles(
        _client(),
        CATS,
        PROFILE_MAP,
        item_path="/movie",
        editor_path="/movie/editor",
        ids_key="movieIds",
        dry_run=True,
    )
    assert not editor.called
    assert actions


@respx.mock
def test_missing_profile_name_raises_configerror() -> None:
    respx.get(f"{BASE}/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 6, "name": "HD - 720p/1080p"}])
    )
    with pytest.raises(ConfigError):
        reconcile_category_profiles(
            _client(),
            CATS,
            PROFILE_MAP,
            item_path="/movie",
            editor_path="/movie/editor",
            ids_key="movieIds",
            dry_run=False,
        )
