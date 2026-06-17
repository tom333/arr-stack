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
