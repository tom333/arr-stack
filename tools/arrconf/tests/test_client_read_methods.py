import httpx
import respx

from arrconf.client_base import QbittorrentClient


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
