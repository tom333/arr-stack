import httpx
import respx

from arrconf.client_base import (
    JellyfinClient,
    QbittorrentClient,
    RadarrClient,
    SeerrClient,
)


@respx.mock
def test_qbit_list_torrents_returns_list():
    # qBit login happens in __init__; mock it + the info endpoint
    respx.post("http://qb:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=abc"})
    )
    respx.get("http://qb:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "hash": "AB",
                    "name": "X",
                    "state": "stalledUP",
                    "progress": 1.0,
                    "category": "radarr-movies",
                    "save_path": "/data/x",
                    "tracker": "http://t/announce",
                }
            ],
        )
    )
    client = QbittorrentClient("http://qb:8080", "u", "p")
    out = client.list_torrents()
    assert isinstance(out, list)
    assert out[0]["hash"] == "AB"


@respx.mock
def test_radarr_list_queue():
    respx.get("http://r:7878/api/v3/queue").mock(
        return_value=httpx.Response(
            200,
            json={
                "records": [
                    {
                        "id": 1,
                        "movieId": 42,
                        "title": "M",
                        "status": "downloading",
                        "downloadId": "ABCDEF",
                        "trackedDownloadStatus": "ok",
                    }
                ]
            },
        )
    )
    client = RadarrClient("http://r:7878", "key")
    out = client.list_queue()
    assert out[0]["downloadId"] == "ABCDEF"


@respx.mock
def test_seerr_list_requests():
    respx.get("http://s:5055/api/v1/request").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": 7,
                        "type": "movie",
                        "status": 2,
                        "media": {"tmdbId": 42, "tvdbId": None},
                        "requestedBy": {"displayName": "Thomas"},
                    }
                ]
            },
        )
    )
    client = SeerrClient("http://s:5055", "key")
    out = client.list_requests()
    assert out[0]["media"]["tmdbId"] == 42


@respx.mock
def test_jellyfin_list_items():
    respx.get("http://j:8096/Items").mock(
        return_value=httpx.Response(
            200,
            json={
                "Items": [{"Name": "Ratatouille", "Type": "Movie", "ProviderIds": {"Tmdb": "2062"}}]
            },
        )
    )
    client = JellyfinClient("http://j:8096", "key")
    out = client.list_items()
    assert out[0]["ProviderIds"]["Tmdb"] == "2062"


@respx.mock
def test_radarr_manual_import_candidates():
    respx.get("http://r:7878/api/v3/manualimport").mock(
        return_value=httpx.Response(
            200,
            json=[{"path": "/data/x/M.mkv", "movie": {"id": 42}, "quality": {}, "rejections": []}],
        )
    )
    client = RadarrClient("http://r:7878", "key")
    out = client.manual_import_candidates("/data/x")
    assert out[0]["movie"]["id"] == 42
