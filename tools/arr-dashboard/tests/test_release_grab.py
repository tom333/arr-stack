import json

import httpx
import pytest
import respx

from arr_dashboard.release_grab import ReleaseGrabError, grab_release
from arr_dashboard.settings import Settings


def _settings() -> Settings:
    return Settings(
        sonarr_url="http://s",
        radarr_url="http://radarr",
        qbittorrent_url="http://q",
        seerr_url="http://se",
        jellyfin_url="http://j",
        prowlarr_url="http://prowlarr",
        sonarr_api_key=None,
        radarr_api_key="rk",
        seerr_api_key=None,
        jellyfin_api_key=None,
        qbt_user=None,
        qbt_pass=None,
        prowlarr_api_key="pk",
        intent_path="/x",
        releases_window_hours=72,
        releases_cap_per_indexer=60,
    )


@respx.mock
def test_grab_existing_untagged_movie_gets_tagged_then_grabs():
    # existing movie in /media/films but no category tag yet (arrconf not run) →
    # must be tagged before the grab so the download client resolves.
    respx.get(url__regex=r"http://radarr/api/v3/movie\?tmdbId=550").mock(
        return_value=httpx.Response(
            200, json=[{"id": 42, "tmdbId": 550, "rootFolderPath": "/media/films", "tags": []}]
        )
    )
    respx.get("http://radarr/api/v3/tag").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "label": "films"}])
    )
    editor = respx.put("http://radarr/api/v3/movie/editor").mock(
        return_value=httpx.Response(202, json={})
    )
    respx.get(url__regex=r"http://radarr/api/v3/release\?movieId=42").mock(
        return_value=httpx.Response(
            200, json=[{"guid": "radarr-guid", "infoHash": "AAA", "indexerId": 7, "title": "T"}]
        )
    )
    grab = respx.post("http://radarr/api/v3/release").mock(
        return_value=httpx.Response(201, json={})
    )
    out = grab_release(
        _settings(),
        info_hash="aaa",
        tmdb_id=550,
        title="Fight Club",
        year=1999,
        root_path="/media/films",
        profile_name="MULTi.VF",
    )
    assert out["status"] == "grabbed"
    assert editor.called  # tag applied to the existing untagged movie
    assert json.loads(editor.calls.last.request.content)["tags"] == [5]
    assert grab.called
    assert b"radarr-guid" in grab.calls.last.request.content


@respx.mock
def test_grab_existing_tagged_movie_skips_editor():
    respx.get(url__regex=r"http://radarr/api/v3/movie\?tmdbId=550").mock(
        return_value=httpx.Response(
            200, json=[{"id": 42, "tmdbId": 550, "rootFolderPath": "/media/films", "tags": [5]}]
        )
    )
    respx.get("http://radarr/api/v3/tag").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "label": "films"}])
    )
    editor = respx.put("http://radarr/api/v3/movie/editor").mock(
        return_value=httpx.Response(202, json={})
    )
    respx.get(url__regex=r"http://radarr/api/v3/release\?movieId=42").mock(
        return_value=httpx.Response(200, json=[{"guid": "gg", "infoHash": "AAA", "indexerId": 7}])
    )
    respx.post("http://radarr/api/v3/release").mock(return_value=httpx.Response(201, json={}))
    out = grab_release(
        _settings(),
        info_hash="aaa",
        tmdb_id=550,
        title="X",
        year=1999,
        root_path="/media/films",
        profile_name="MULTi.VF",
    )
    assert out["status"] == "grabbed"
    assert not editor.called  # already tagged → no edit


@respx.mock
def test_grab_fallback_when_infohash_absent_in_radarr():
    respx.get(url__regex=r"http://radarr/api/v3/movie\?tmdbId=550").mock(
        return_value=httpx.Response(
            200, json=[{"id": 42, "tmdbId": 550, "rootFolderPath": "/media/films", "tags": [5]}]
        )
    )
    respx.get("http://radarr/api/v3/tag").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "label": "films"}])
    )
    respx.get(url__regex=r"http://radarr/api/v3/release\?movieId=42").mock(
        return_value=httpx.Response(
            200, json=[{"guid": "other", "infoHash": "ZZZ", "indexerId": 7}]
        )
    )
    with pytest.raises(ReleaseGrabError, match="introuvable"):
        grab_release(
            _settings(),
            info_hash="aaa",
            tmdb_id=550,
            title="Fight Club",
            year=1999,
            root_path="/media/films",
            profile_name="MULTi.VF",
        )


@respx.mock
def test_grab_adds_missing_movie_first():
    respx.get(url__regex=r"http://radarr/api/v3/movie\?tmdbId=550").mock(
        return_value=httpx.Response(200, json=[])
    )
    # Radarr POST /movie needs the full looked-up object (title/titleSlug/...) —
    # a bare {tmdbId} payload 500s. The add flow must fetch this first.
    lookup = respx.get(url__regex=r"http://radarr/api/v3/movie/lookup\?term=tmdb:550").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "tmdbId": 550,
                    "title": "Fight Club",
                    "titleSlug": "fight-club-550",
                    "year": 1999,
                    "images": [{"coverType": "poster", "remoteUrl": "http://x/p.jpg"}],
                }
            ],
        )
    )
    respx.get("http://radarr/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "MULTi.VF"}])
    )
    respx.get("http://radarr/api/v3/rootfolder").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "path": "/media/films"}])
    )
    respx.get("http://radarr/api/v3/tag").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "label": "films"}])
    )
    add = respx.post("http://radarr/api/v3/movie").mock(
        return_value=httpx.Response(201, json={"id": 99, "tmdbId": 550})
    )
    respx.get(url__regex=r"http://radarr/api/v3/release\?movieId=99").mock(
        return_value=httpx.Response(200, json=[{"guid": "gg", "infoHash": "AAA", "indexerId": 7}])
    )
    respx.post("http://radarr/api/v3/release").mock(return_value=httpx.Response(201, json={}))
    out = grab_release(
        _settings(),
        info_hash="aaa",
        tmdb_id=550,
        title="Fight Club",
        year=1999,
        root_path="/media/films",
        profile_name="MULTi.VF",
    )
    assert out["status"] == "grabbed"
    assert lookup.called
    assert add.called
    # the POST body must be the full looked-up object, not a bare {tmdbId}
    body = json.loads(add.calls.last.request.content)
    assert body["titleSlug"] == "fight-club-550"
    assert body["qualityProfileId"] == 1
    assert body["rootFolderPath"] == "/media/films"
    assert body["addOptions"] == {"searchForMovie": False}
    # category tag ("films" → id 5) must be on the movie so the grab routes to the
    # matching download client (all clients tagged, no catch-all)
    assert body["tags"] == [5]


@respx.mock
def test_grab_creates_category_tag_when_absent():
    respx.get(url__regex=r"http://radarr/api/v3/movie\?tmdbId=550").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get(url__regex=r"http://radarr/api/v3/movie/lookup\?term=tmdb:550").mock(
        return_value=httpx.Response(
            200, json=[{"tmdbId": 550, "title": "X", "titleSlug": "x-550", "year": 2020}]
        )
    )
    respx.get("http://radarr/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "MULTi.VF"}])
    )
    respx.get("http://radarr/api/v3/rootfolder").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "path": "/media/films"}])
    )
    respx.get("http://radarr/api/v3/tag").mock(return_value=httpx.Response(200, json=[]))
    create_tag = respx.post("http://radarr/api/v3/tag").mock(
        return_value=httpx.Response(201, json={"id": 12, "label": "films"})
    )
    respx.post("http://radarr/api/v3/movie").mock(
        return_value=httpx.Response(201, json={"id": 77, "tmdbId": 550})
    )
    respx.get(url__regex=r"http://radarr/api/v3/release\?movieId=77").mock(
        return_value=httpx.Response(200, json=[{"guid": "g", "infoHash": "AAA", "indexerId": 7}])
    )
    respx.post("http://radarr/api/v3/release").mock(return_value=httpx.Response(201, json={}))
    out = grab_release(
        _settings(),
        info_hash="aaa",
        tmdb_id=550,
        title="X",
        year=2020,
        root_path="/media/films",
        profile_name="MULTi.VF",
    )
    assert out["status"] == "grabbed"
    assert create_tag.called  # tag "films" created on the fly


@respx.mock
def test_grab_raises_when_lookup_empty():
    respx.get(url__regex=r"http://radarr/api/v3/movie\?tmdbId=550").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get(url__regex=r"http://radarr/api/v3/movie/lookup\?term=tmdb:550").mock(
        return_value=httpx.Response(200, json=[])
    )
    with pytest.raises(ReleaseGrabError, match="introuvable dans le lookup"):
        grab_release(
            _settings(),
            info_hash="aaa",
            tmdb_id=550,
            title="X",
            year=2020,
            root_path="/media/films",
            profile_name="MULTi.VF",
        )
