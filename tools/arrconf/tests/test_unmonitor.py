import json

import httpx
import respx

from arrconf.client_base import RadarrClient, SonarrClient
from arrconf.reconcilers._unmonitor import (
    unmonitor_downloaded_episodes,
    unmonitor_imported_movies,
)


@respx.mock
def test_unmonitor_movies_flips_only_hasfile_monitored():
    respx.get("http://r:7878/api/v3/movie").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 1, "hasFile": True, "monitored": True},
                {"id": 2, "hasFile": False, "monitored": True},
                {"id": 3, "hasFile": True, "monitored": False},
            ],
        )
    )
    editor = respx.put("http://r:7878/api/v3/movie/editor").mock(
        return_value=httpx.Response(200, json={})
    )
    acts = unmonitor_imported_movies(RadarrClient("http://r:7878", "k"), dry_run=False)
    assert acts == ["unmonitor_movies:applied:1"]
    body = json.loads(editor.calls.last.request.content)
    assert body == {"movieIds": [1], "monitored": False}


@respx.mock
def test_unmonitor_movies_noop_when_none():
    respx.get("http://r:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=[{"id": 3, "hasFile": True, "monitored": False}])
    )
    editor = respx.put("http://r:7878/api/v3/movie/editor").mock(
        return_value=httpx.Response(200, json={})
    )
    acts = unmonitor_imported_movies(RadarrClient("http://r:7878", "k"), dry_run=False)
    assert acts == ["unmonitor_movies:no-op"]
    assert not editor.calls


@respx.mock
def test_unmonitor_movies_dry_run_no_put():
    respx.get("http://r:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "hasFile": True, "monitored": True}])
    )
    editor = respx.put("http://r:7878/api/v3/movie/editor").mock(
        return_value=httpx.Response(200, json={})
    )
    acts = unmonitor_imported_movies(RadarrClient("http://r:7878", "k"), dry_run=True)
    assert acts == ["unmonitor_movies:dry_run:1"]
    assert not editor.calls


@respx.mock
def test_unmonitor_episodes_flips_only_downloaded_keeps_series():
    respx.get("http://s:8989/api/v3/series").mock(
        return_value=httpx.Response(200, json=[{"id": 10}, {"id": 20}])
    )
    respx.get("http://s:8989/api/v3/episode?seriesId=10").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 101, "hasFile": True, "monitored": True},
                {"id": 102, "hasFile": False, "monitored": True},
            ],
        )
    )
    respx.get("http://s:8989/api/v3/episode?seriesId=20").mock(
        return_value=httpx.Response(200, json=[{"id": 201, "hasFile": True, "monitored": True}])
    )
    mon = respx.put("http://s:8989/api/v3/episode/monitor").mock(
        return_value=httpx.Response(200, json={})
    )
    series_editor = respx.put("http://s:8989/api/v3/series/editor").mock(
        return_value=httpx.Response(200, json={})
    )
    acts = unmonitor_downloaded_episodes(SonarrClient("http://s:8989", "k"), dry_run=False)
    assert acts == ["unmonitor_episodes:applied:2"]
    body = json.loads(mon.calls.last.request.content)
    assert body == {"episodeIds": [101, 201], "monitored": False}
    assert not series_editor.calls


@respx.mock
def test_unmonitor_episodes_noop_when_none():
    respx.get("http://s:8989/api/v3/series").mock(
        return_value=httpx.Response(200, json=[{"id": 10}])
    )
    respx.get("http://s:8989/api/v3/episode?seriesId=10").mock(
        return_value=httpx.Response(200, json=[{"id": 101, "hasFile": False, "monitored": True}])
    )
    mon = respx.put("http://s:8989/api/v3/episode/monitor").mock(
        return_value=httpx.Response(200, json={})
    )
    acts = unmonitor_downloaded_episodes(SonarrClient("http://s:8989", "k"), dry_run=False)
    assert acts == ["unmonitor_episodes:no-op"]
    assert not mon.calls
