import json

import httpx
import pytest
import respx

from arr_dashboard.series_grab import SeriesGrabError, add_series
from arr_dashboard.settings import Settings


def _settings() -> Settings:
    return Settings(
        sonarr_url="http://sonarr",
        radarr_url="http://radarr",
        qbittorrent_url="http://q",
        seerr_url="http://se",
        jellyfin_url="http://j",
        prowlarr_url="http://prowlarr",
        sonarr_api_key="sk",
        radarr_api_key=None,
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
def test_add_existing_untagged_series_gets_tagged():
    respx.get(url__regex=r"http://sonarr/api/v3/series\?tvdbId=550").mock(
        return_value=httpx.Response(
            200, json=[{"id": 42, "tvdbId": 550, "rootFolderPath": "/media/series", "tags": []}]
        )
    )
    respx.get("http://sonarr/api/v3/tag").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "label": "series"}])
    )
    editor = respx.put("http://sonarr/api/v3/series/editor").mock(
        return_value=httpx.Response(202, json={})
    )
    out = add_series(
        _settings(),
        tvdb_id=550,
        title="The Show",
        year=2022,
        root_path="/media/series",
        profile_name="MULTi.VF",
        series_type="standard",
        monitor="all",
    )
    assert out == {"status": "exists", "series_id": "42"}
    assert editor.called
    assert json.loads(editor.calls.last.request.content)["tags"] == [5]


@respx.mock
def test_add_existing_tagged_series_skips_editor():
    respx.get(url__regex=r"http://sonarr/api/v3/series\?tvdbId=550").mock(
        return_value=httpx.Response(
            200, json=[{"id": 42, "tvdbId": 550, "rootFolderPath": "/media/series", "tags": [5]}]
        )
    )
    respx.get("http://sonarr/api/v3/tag").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "label": "series"}])
    )
    editor = respx.put("http://sonarr/api/v3/series/editor").mock(
        return_value=httpx.Response(202, json={})
    )
    out = add_series(
        _settings(),
        tvdb_id=550,
        title="The Show",
        year=2022,
        root_path="/media/series",
        profile_name="MULTi.VF",
        series_type="standard",
        monitor="all",
    )
    assert out == {"status": "exists", "series_id": "42"}
    assert not editor.called


@respx.mock
def test_add_missing_series_posts_full_lookup_object_with_add_options():
    respx.get(url__regex=r"http://sonarr/api/v3/series\?tvdbId=550").mock(
        return_value=httpx.Response(200, json=[])
    )
    lookup = respx.get(url__regex=r"http://sonarr/api/v3/series/lookup\?term=tvdb:550").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "tvdbId": 550,
                    "title": "The Show",
                    "titleSlug": "the-show-550",
                    "year": 2022,
                    "seasons": [{"seasonNumber": 1}],
                    "images": [{"coverType": "poster", "remoteUrl": "http://x/p.jpg"}],
                }
            ],
        )
    )
    respx.get("http://sonarr/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 3, "name": "MULTi.VF"}])
    )
    respx.get("http://sonarr/api/v3/tag").mock(
        return_value=httpx.Response(200, json=[{"id": 5, "label": "series"}])
    )
    add = respx.post("http://sonarr/api/v3/series").mock(
        return_value=httpx.Response(201, json={"id": 99, "tvdbId": 550})
    )
    out = add_series(
        _settings(),
        tvdb_id=550,
        title="The Show",
        year=2022,
        root_path="/media/series",
        profile_name="MULTi.VF",
        series_type="standard",
        monitor="latestSeason",
    )
    assert out == {"status": "added", "series_id": "99"}
    assert lookup.called
    assert add.called
    body = json.loads(add.calls.last.request.content)
    assert body["titleSlug"] == "the-show-550"
    assert body["qualityProfileId"] == 3
    assert body["rootFolderPath"] == "/media/series"
    assert body["seriesType"] == "standard"
    assert body["tags"] == [5]
    assert body["addOptions"] == {"monitor": "latestSeason", "searchForMissingEpisodes": True}


@respx.mock
def test_add_missing_anime_series_sets_series_type_and_creates_tag():
    respx.get(url__regex=r"http://sonarr/api/v3/series\?tvdbId=551").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get(url__regex=r"http://sonarr/api/v3/series/lookup\?term=tvdb:551").mock(
        return_value=httpx.Response(
            200,
            json=[{"tvdbId": 551, "title": "Anime X", "titleSlug": "anime-x-551", "year": 2021}],
        )
    )
    respx.get("http://sonarr/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 4, "name": "Anime"}])
    )
    respx.get("http://sonarr/api/v3/tag").mock(return_value=httpx.Response(200, json=[]))
    create_tag = respx.post("http://sonarr/api/v3/tag").mock(
        return_value=httpx.Response(201, json={"id": 9, "label": "series-zoe"})
    )
    respx.post("http://sonarr/api/v3/series").mock(
        return_value=httpx.Response(201, json={"id": 77, "tvdbId": 551})
    )
    out = add_series(
        _settings(),
        tvdb_id=551,
        title="Anime X",
        year=2021,
        root_path="/media/series-zoe",
        profile_name="Anime",
        series_type="anime",
        monitor="all",
    )
    assert out == {"status": "added", "series_id": "77"}
    assert create_tag.called


@respx.mock
def test_add_raises_when_lookup_empty():
    respx.get(url__regex=r"http://sonarr/api/v3/series\?tvdbId=550").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get(url__regex=r"http://sonarr/api/v3/series/lookup\?term=tvdb:550").mock(
        return_value=httpx.Response(200, json=[])
    )
    with pytest.raises(SeriesGrabError, match="introuvable dans le lookup"):
        add_series(
            _settings(),
            tvdb_id=550,
            title="X",
            year=2020,
            root_path="/media/series",
            profile_name="MULTi.VF",
            series_type="standard",
            monitor="all",
        )


@respx.mock
def test_add_raises_when_quality_profile_missing():
    respx.get(url__regex=r"http://sonarr/api/v3/series\?tvdbId=550").mock(
        return_value=httpx.Response(200, json=[])
    )
    respx.get(url__regex=r"http://sonarr/api/v3/series/lookup\?term=tvdb:550").mock(
        return_value=httpx.Response(
            200, json=[{"tvdbId": 550, "title": "X", "titleSlug": "x-550", "year": 2020}]
        )
    )
    respx.get("http://sonarr/api/v3/qualityprofile").mock(return_value=httpx.Response(200, json=[]))
    with pytest.raises(SeriesGrabError, match="absent de Sonarr"):
        add_series(
            _settings(),
            tvdb_id=550,
            title="X",
            year=2020,
            root_path="/media/series",
            profile_name="MULTi.VF",
            series_type="standard",
            monitor="all",
        )
