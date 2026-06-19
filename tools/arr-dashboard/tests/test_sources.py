import httpx
import respx
from arr_dashboard.settings import Settings
from arr_dashboard.sources import fetch_all


def _settings():
    return Settings(
        sonarr_url="http://sonarr:8989",
        radarr_url="http://radarr:7878",
        qbittorrent_url="http://qb:8080",
        seerr_url="http://seerr:5055",
        jellyfin_url="http://jf:8096",
        sonarr_api_key="k",
        radarr_api_key="k",
        seerr_api_key="k",
        jellyfin_api_key="k",
        qbt_user="u",
        qbt_pass="p",
    )


@respx.mock
def test_fetch_all_marks_failed_source_stale():
    respx.get("http://radarr:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "tmdbId": 42, "title": "M"}])
    )
    respx.get("http://radarr:7878/api/v3/queue").mock(
        return_value=httpx.Response(200, json={"records": []})
    )
    respx.get("http://sonarr:8989/api/v3/series").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://sonarr:8989/api/v3/queue").mock(
        return_value=httpx.Response(200, json={"records": []})
    )
    respx.post("http://qb:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=x"})
    )
    respx.get("http://qb:8080/api/v2/torrents/info").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://seerr:5055/api/v1/request").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    # Jellyfin DOWN
    respx.get("http://jf:8096/Items").mock(return_value=httpx.Response(500))

    src, stale = fetch_all(_settings())
    assert src["radarr_movies"][0]["tmdbId"] == 42
    assert "jellyfin" in stale
    assert src["jellyfin_items"] == []


@respx.mock
def test_qbit_probes_trackers_only_for_stalled():
    respx.get("http://radarr:7878/api/v3/movie").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://radarr:7878/api/v3/queue").mock(
        return_value=httpx.Response(200, json={"records": []})
    )
    respx.get("http://sonarr:8989/api/v3/series").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://sonarr:8989/api/v3/queue").mock(
        return_value=httpx.Response(200, json={"records": []})
    )
    respx.post("http://qb:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=x"})
    )
    respx.get("http://qb:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "hash": "STALLED",
                    "name": "s",
                    "state": "forcedDL",
                    "progress": 0.0,
                    "dlspeed": 0,
                },
                {
                    "hash": "HEALTHY",
                    "name": "h",
                    "state": "downloading",
                    "progress": 0.5,
                    "dlspeed": 9000,
                },
            ],
        )
    )
    respx.get("http://seerr:5055/api/v1/request").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    respx.get("http://jf:8096/Items").mock(return_value=httpx.Response(200, json={"Items": []}))
    trackers = respx.get("http://qb:8080/api/v2/torrents/trackers").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"url": "** [DHT] **", "status": 2, "msg": ""},
                {"url": "https://c411.org/announce/x", "status": 4, "msg": "Forbidden"},
            ],
        )
    )

    src, stale = fetch_all(_settings())
    torrents = {t["hash"]: t for t in src["qbit_torrents"]}
    assert trackers.call_count == 1  # only the stalled torrent probed
    assert torrents["STALLED"]["_tracker"] == {"status": 4, "msg": "Forbidden", "host": "c411.org"}
    assert "_tracker" not in torrents["HEALTHY"]


@respx.mock
def test_qbit_tracker_probe_failure_is_graceful():
    respx.get("http://radarr:7878/api/v3/movie").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://radarr:7878/api/v3/queue").mock(
        return_value=httpx.Response(200, json={"records": []})
    )
    respx.get("http://sonarr:8989/api/v3/series").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://sonarr:8989/api/v3/queue").mock(
        return_value=httpx.Response(200, json={"records": []})
    )
    respx.post("http://qb:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=x"})
    )
    respx.get("http://qb:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"hash": "STALLED", "name": "s", "state": "forcedDL", "progress": 0.0, "dlspeed": 0}
            ],
        )
    )
    respx.get("http://seerr:5055/api/v1/request").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    respx.get("http://jf:8096/Items").mock(return_value=httpx.Response(200, json={"Items": []}))
    respx.get("http://qb:8080/api/v2/torrents/trackers").mock(return_value=httpx.Response(500))

    src, stale = fetch_all(_settings())
    assert src["qbit_torrents"][0]["hash"] == "STALLED"
    assert "_tracker" not in src["qbit_torrents"][0]
    assert "qbittorrent" not in stale
