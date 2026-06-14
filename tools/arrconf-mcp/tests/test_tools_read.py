import httpx

from arrconf_mcp import clients
from arrconf_mcp.server import (
    cross_seed_status,
    library_overview,
    queue_status,
    stalled_torrents,
    transfer_info,
)


def test_stalled_torrents(monkeypatch, mock_api):
    monkeypatch.setenv("QBT_USER", "u")
    monkeypatch.setenv("QBT_PASS", "p")
    monkeypatch.setenv("QBT_URL", "http://qb.test:8080")
    clients.reset()
    mock_api.post("http://qb.test:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=x"})
    )
    mock_api.get("http://qb.test:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "name": "A",
                    "state": "stalledDL",
                    "progress": 0.0,
                    "num_complete": 0,
                    "category": "films-enfants",
                    "tracker": "https://c411.org/announce/x",
                },
                {
                    "name": "B",
                    "state": "downloading",
                    "progress": 0.5,
                    "num_complete": 3,
                    "category": "films",
                    "tracker": "udp://x",
                },
            ],
        )
    )
    out = stalled_torrents()
    names = [t["name"] for t in out]
    assert names == ["A"]  # only the stalled one


def test_queue_status(monkeypatch, mock_api):
    monkeypatch.setenv("SONARR_API_KEY", "ks")
    monkeypatch.setenv("SONARR_URL", "http://sonarr.test:8989")
    monkeypatch.setenv("RADARR_API_KEY", "kr")
    monkeypatch.setenv("RADARR_URL", "http://radarr.test:7878")
    clients.reset()
    mock_api.get("http://sonarr.test:8989/api/v3/queue").mock(
        return_value=httpx.Response(
            200,
            json={
                "records": [
                    {
                        "title": "S.E01",
                        "status": "downloading",
                        "sizeleft": 1024,
                        "errorMessage": None,
                    }
                ]
            },
        )
    )
    mock_api.get("http://radarr.test:7878/api/v3/queue").mock(
        return_value=httpx.Response(
            200,
            json={
                "records": [
                    {
                        "title": "Movie",
                        "status": "warning",
                        "sizeleft": 0,
                        "errorMessage": "stalled",
                    }
                ]
            },
        )
    )
    out = queue_status()
    apps = sorted(i["app"] for i in out)
    assert apps == ["radarr", "sonarr"]
    sonarr_item = next(i for i in out if i["app"] == "sonarr")
    assert sonarr_item["title"] == "S.E01"
    radarr_item = next(i for i in out if i["app"] == "radarr")
    assert radarr_item["errorMessage"] == "stalled"


def test_library_overview(monkeypatch, mock_api):
    monkeypatch.setenv("SONARR_API_KEY", "ks")
    monkeypatch.setenv("SONARR_URL", "http://sonarr.test:8989")
    monkeypatch.setenv("RADARR_API_KEY", "kr")
    monkeypatch.setenv("RADARR_URL", "http://radarr.test:7878")
    clients.reset()
    mock_api.get("http://sonarr.test:8989/api/v3/series").mock(
        return_value=httpx.Response(200, json=[{"id": 1}, {"id": 2}, {"id": 3}])
    )
    mock_api.get("http://radarr.test:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=[{"id": 1}, {"id": 2}])
    )
    mock_api.get("http://radarr.test:7878/api/v3/diskspace").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"path": "/media", "freeSpace": 10 * 1024**3},
                {"path": "/data", "freeSpace": 5 * 1024**3},
            ],
        )
    )
    out = library_overview()
    assert out["series_count"] == 3
    assert out["movie_count"] == 2
    disks = {d["path"]: d["freeGB"] for d in out["disks"]}
    assert disks == {"/media": 10.0, "/data": 5.0}


def test_transfer_info(monkeypatch, mock_api):
    monkeypatch.setenv("QBT_USER", "u")
    monkeypatch.setenv("QBT_PASS", "p")
    monkeypatch.setenv("QBT_URL", "http://qb.test:8080")
    clients.reset()
    mock_api.post("http://qb.test:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=x"})
    )
    mock_api.get("http://qb.test:8080/api/v2/transfer/info").mock(
        return_value=httpx.Response(
            200,
            json={
                "dl_info_speed": 4_000_000,
                "up_info_speed": 500_000,
                "dht_nodes": 321,
                "connection_status": "connected",
            },
        )
    )
    out = transfer_info()
    assert out == {
        "dl_speed": 4_000_000,
        "up_speed": 500_000,
        "dht_nodes": 321,
        "connection_status": "connected",
    }


def test_cross_seed_status(monkeypatch, mock_api):
    monkeypatch.setenv("QBT_USER", "u")
    monkeypatch.setenv("QBT_PASS", "p")
    monkeypatch.setenv("QBT_URL", "http://qb.test:8080")
    clients.reset()
    mock_api.post("http://qb.test:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=x"})
    )
    route = mock_api.get("http://qb.test:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "name": "X",
                    "state": "uploading",
                    "progress": 1.0,
                    "num_complete": 2,
                    "category": "cross-seed-link",
                    "tracker": "https://torr9.org/announce/x",
                }
            ],
        )
    )
    out = cross_seed_status()
    assert out["count"] == 1
    assert out["torrents"][0]["name"] == "X"
    # category filter forwarded as a query param
    assert route.calls.last.request.url.params["category"] == "cross-seed-link"
