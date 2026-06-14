import json as _json

import httpx

from arrconf_mcp import clients
from arrconf_mcp.server import (
    blocklist_and_research,
    delete_movie,
    delete_series,
    remove_torrent,
    set_quality_profile,
)


def _radarr_env(monkeypatch):
    monkeypatch.setenv("RADARR_API_KEY", "rk")
    monkeypatch.setenv("RADARR_URL", "http://radarr.test:7878")


def _sonarr_env(monkeypatch):
    monkeypatch.setenv("SONARR_API_KEY", "sk")
    monkeypatch.setenv("SONARR_URL", "http://sonarr.test:8989")


def _qbit_env(monkeypatch):
    monkeypatch.setenv("QBT_USER", "u")
    monkeypatch.setenv("QBT_PASS", "p")
    monkeypatch.setenv("QBT_URL", "http://qb.test:8080")


def _mock_qbit_login(mock_api):
    return mock_api.post("http://qb.test:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=x"})
    )


# --- guardrail: no confirm => structured payload, NO HTTP -----------------


def test_remove_torrent_needs_confirmation_no_http(monkeypatch, mock_api):
    _qbit_env(monkeypatch)
    clients.reset()
    login = _mock_qbit_login(mock_api)
    delete_route = mock_api.post("http://qb.test:8080/api/v2/torrents/delete").mock(
        return_value=httpx.Response(200)
    )
    out = remove_torrent("abc123")
    assert out == {
        "status": "needs_confirmation",
        "action": "remove_torrent",
        "details": {"torrent_hash": "abc123", "delete_files": False},
        "hint": "re-call with confirm=true",
    }
    # No client is even built (so no login) and no delete call happens.
    assert not login.called
    assert not delete_route.called


def test_delete_movie_needs_confirmation_no_http(monkeypatch, mock_api):
    _radarr_env(monkeypatch)
    clients.reset()
    route = mock_api.delete("http://radarr.test:7878/api/v3/movie/42").mock(
        return_value=httpx.Response(200)
    )
    out = delete_movie(42, delete_files=True)
    assert out["status"] == "needs_confirmation"
    assert out["details"] == {"movie_id": 42, "delete_files": True}
    assert not route.called


def test_delete_series_needs_confirmation_no_http(monkeypatch, mock_api):
    _sonarr_env(monkeypatch)
    clients.reset()
    route = mock_api.delete("http://sonarr.test:8989/api/v3/series/7").mock(
        return_value=httpx.Response(200)
    )
    out = delete_series(7)
    assert out["status"] == "needs_confirmation"
    assert out["details"] == {"series_id": 7, "delete_files": False}
    assert not route.called


def test_blocklist_needs_confirmation_no_http(monkeypatch, mock_api):
    _radarr_env(monkeypatch)
    clients.reset()
    route = mock_api.delete("http://radarr.test:7878/api/v3/queue/9").mock(
        return_value=httpx.Response(200)
    )
    out = blocklist_and_research("radarr", 9)
    assert out["status"] == "needs_confirmation"
    assert out["details"] == {"app": "radarr", "queue_id": 9}
    assert not route.called


def test_set_quality_profile_needs_confirmation_no_http(monkeypatch, mock_api):
    _radarr_env(monkeypatch)
    clients.reset()
    qp = mock_api.get("http://radarr.test:7878/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 2, "name": "Family"}])
    )
    out = set_quality_profile("radarr", 42, "Family")
    assert out["status"] == "needs_confirmation"
    assert out["details"] == {"app": "radarr", "item_id": 42, "profile_name": "Family"}
    assert not qp.called


# --- confirmed path: HTTP happens -----------------------------------------


def test_remove_torrent_confirmed(monkeypatch, mock_api):
    _qbit_env(monkeypatch)
    clients.reset()
    _mock_qbit_login(mock_api)
    posted = {}

    def _capture(request):
        posted.update(dict(httpx.QueryParams(request.content.decode())))
        return httpx.Response(200)

    mock_api.post("http://qb.test:8080/api/v2/torrents/delete").mock(side_effect=_capture)

    out = remove_torrent("abc123", delete_files=True, confirm=True)
    assert posted == {"hashes": "abc123", "deleteFiles": "true"}
    assert out == {"status": "removed", "torrent_hash": "abc123", "deleted_files": True}


def test_remove_torrent_confirmed_no_delete_files(monkeypatch, mock_api):
    _qbit_env(monkeypatch)
    clients.reset()
    _mock_qbit_login(mock_api)
    posted = {}

    def _capture(request):
        posted.update(dict(httpx.QueryParams(request.content.decode())))
        return httpx.Response(200)

    mock_api.post("http://qb.test:8080/api/v2/torrents/delete").mock(side_effect=_capture)

    remove_torrent("zzz", confirm=True)
    assert posted["deleteFiles"] == "false"


def test_delete_movie_confirmed(monkeypatch, mock_api):
    _radarr_env(monkeypatch)
    clients.reset()
    route = mock_api.delete("http://radarr.test:7878/api/v3/movie/42").mock(
        return_value=httpx.Response(200)
    )
    out = delete_movie(42, delete_files=True, confirm=True)
    assert route.called
    assert route.calls.last.request.url.params["deleteFiles"] == "true"
    assert out == {"status": "deleted", "movie_id": 42, "deleted_files": True}


def test_delete_series_confirmed(monkeypatch, mock_api):
    _sonarr_env(monkeypatch)
    clients.reset()
    route = mock_api.delete("http://sonarr.test:8989/api/v3/series/7").mock(
        return_value=httpx.Response(200)
    )
    out = delete_series(7, confirm=True)
    assert route.called
    assert route.calls.last.request.url.params["deleteFiles"] == "false"
    assert out == {"status": "deleted", "series_id": 7, "deleted_files": False}


def test_blocklist_and_research_confirmed(monkeypatch, mock_api):
    _sonarr_env(monkeypatch)
    clients.reset()
    delete_route = mock_api.delete("http://sonarr.test:8989/api/v3/queue/9").mock(
        return_value=httpx.Response(200)
    )
    posted = {}

    def _capture(request):
        posted.update(_json.loads(request.content))
        return httpx.Response(201, json={"name": "MissingEpisodeSearch"})

    mock_api.post("http://sonarr.test:8989/api/v3/command").mock(side_effect=_capture)

    out = blocklist_and_research("sonarr", 9, confirm=True)
    assert delete_route.called
    params = delete_route.calls.last.request.url.params
    assert params["removeFromClient"] == "true"
    assert params["blocklist"] == "true"
    assert posted == {"name": "MissingEpisodeSearch"}
    assert out["status"] == "blocklisted_and_researching"
    assert out["command"] == "MissingEpisodeSearch"


def test_set_quality_profile_confirmed(monkeypatch, mock_api):
    _radarr_env(monkeypatch)
    clients.reset()
    mock_api.get("http://radarr.test:7878/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 2, "name": "Family"}, {"id": 1, "name": "x"}])
    )
    mock_api.get("http://radarr.test:7878/api/v3/movie/42").mock(
        return_value=httpx.Response(200, json={"id": 42, "title": "Encanto", "qualityProfileId": 1})
    )
    put_body = {}

    def _capture(request):
        put_body.update(_json.loads(request.content))
        return httpx.Response(200, json=put_body)

    mock_api.put("http://radarr.test:7878/api/v3/movie/42").mock(side_effect=_capture)

    out = set_quality_profile("radarr", 42, "Family", confirm=True)
    assert put_body["qualityProfileId"] == 2
    assert put_body["title"] == "Encanto"
    assert out == {
        "status": "reprofiled",
        "app": "radarr",
        "item_id": 42,
        "qualityProfileId": 2,
    }


def test_blocklist_rejects_bad_app(monkeypatch):
    clients.reset()
    try:
        blocklist_and_research("prowlarr", 1, confirm=True)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
