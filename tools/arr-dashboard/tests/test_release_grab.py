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
def test_grab_existing_movie_matches_infohash_and_grabs():
    respx.get(url__regex=r"http://radarr/api/v3/movie\?tmdbId=550").mock(
        return_value=httpx.Response(200, json=[{"id": 42, "tmdbId": 550}])
    )
    respx.get(url__regex=r"http://radarr/api/v3/release\?movieId=42").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"guid": "radarr-guid", "infoHash": "AAA", "indexerId": 7, "title": "T"},
            ],
        )
    )
    grab = respx.post("http://radarr/api/v3/release").mock(
        return_value=httpx.Response(201, json={})
    )
    out = grab_release(_settings(), info_hash="aaa", tmdb_id=550, title="Fight Club", year=1999)
    assert out["status"] == "grabbed"
    assert grab.called
    body = grab.calls.last.request.content
    assert b"radarr-guid" in body


@respx.mock
def test_grab_fallback_when_infohash_absent_in_radarr():
    respx.get(url__regex=r"http://radarr/api/v3/movie\?tmdbId=550").mock(
        return_value=httpx.Response(200, json=[{"id": 42, "tmdbId": 550}])
    )
    respx.get(url__regex=r"http://radarr/api/v3/release\?movieId=42").mock(
        return_value=httpx.Response(
            200, json=[{"guid": "other", "infoHash": "ZZZ", "indexerId": 7}]
        )
    )
    with pytest.raises(ReleaseGrabError, match="introuvable"):
        grab_release(_settings(), info_hash="aaa", tmdb_id=550, title="Fight Club", year=1999)


@respx.mock
def test_grab_adds_missing_movie_first():
    respx.get(url__regex=r"http://radarr/api/v3/movie\?tmdbId=550").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get("http://radarr/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "MULTi.VF"}])
    )
    respx.get("http://radarr/api/v3/rootfolder").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "path": "/media/films"}])
    )
    add = respx.post("http://radarr/api/v3/movie").mock(
        return_value=httpx.Response(201, json={"id": 99, "tmdbId": 550})
    )
    respx.get(url__regex=r"http://radarr/api/v3/release\?movieId=99").mock(
        return_value=httpx.Response(200, json=[{"guid": "gg", "infoHash": "AAA", "indexerId": 7}])
    )
    respx.post("http://radarr/api/v3/release").mock(return_value=httpx.Response(201, json={}))
    out = grab_release(_settings(), info_hash="aaa", tmdb_id=550, title="Fight Club", year=1999)
    assert out["status"] == "grabbed"
    assert add.called
