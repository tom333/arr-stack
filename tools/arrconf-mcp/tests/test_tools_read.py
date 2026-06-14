import httpx

from arrconf_mcp import clients
from arrconf_mcp.server import stalled_torrents


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
