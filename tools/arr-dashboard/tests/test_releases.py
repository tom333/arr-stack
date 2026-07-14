import httpx
import respx

from arr_dashboard.releases import fetch_releases, parse_release_title
from arr_dashboard.settings import Settings


def test_parse_web_1080p_x265_french():
    p = parse_release_title("Bubble.2022.FRENCH.1080p.NF.WEB.AV1.DDP.5.1-Niroma")
    assert p["year"] == 2022
    assert p["resolution"] == "1080p"
    assert p["source"] == "WEB"
    assert p["language"] == "FRENCH"


def test_parse_bluray_x265_multi():
    p = parse_release_title("Mortal.Engines.2018.MULTI.VFF.1080p.BluRay.x265-mHDgz")
    assert p["resolution"] == "1080p"
    assert p["source"] == "BluRay"
    assert p["codec"] == "x265"
    assert p["language"] == "MULTI"


def test_parse_unknown_bits_are_none():
    p = parse_release_title("Some Movie Title")
    assert p["year"] is None and p["resolution"] is None and p["source"] is None


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
        releases_window_hours=100000,
        releases_cap_per_indexer=60,
    )


@respx.mock
def test_fetch_dedups_by_infohash_and_flags_library():
    respx.get("http://prowlarr/api/v1/indexer").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 7, "name": "Torr9", "enable": True},
                {"id": 3, "name": "Dead", "enable": False},
            ],
        )
    )
    rel = {
        "title": "Film.2022.VFF.1080p.BluRay.x265",
        "infoHash": "AAA",
        "guid": "g1",
        "indexerId": 7,
        "size": 100,
        "publishDate": "2026-07-14T00:00:00Z",
        "tmdbId": 0,
        "seeders": 12,
        "leechers": 3,
    }
    respx.get(url__regex=r"http://prowlarr/api/v1/search.*").mock(
        return_value=httpx.Response(200, json=[rel, rel])
    )  # same infohash twice
    respx.get("http://radarr/api/v3/movie").mock(return_value=httpx.Response(200, json=[]))
    respx.get(url__regex=r"http://radarr/api/v3/movie/lookup.*").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "title": "Film",
                    "year": 2022,
                    "tmdbId": 550,
                    "genres": ["Action", "Animation"],
                    "images": [{"coverType": "poster", "remoteUrl": "http://img/p.jpg"}],
                }
            ],
        )
    )

    releases = fetch_releases(_settings())
    assert len(releases) == 1
    assert releases[0].info_hash == "AAA"
    assert releases[0].indexer_name == "Torr9"
    assert releases[0].tmdb_id == 550
    assert releases[0].in_library is False
    assert releases[0].seeders == 12
    assert releases[0].genres == ["Action", "Animation"]
    assert releases[0].poster_url == "http://img/p.jpg"


@respx.mock
def test_fetch_skips_failing_indexer():
    respx.get("http://prowlarr/api/v1/indexer").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 7, "name": "Torr9", "enable": True},
                {"id": 5, "name": "Torrent9", "enable": True},
            ],
        )
    )

    def search_side(request):
        if "indexerIds=5" in str(request.url):
            return httpx.Response(500)
        return httpx.Response(
            200,
            json=[
                {
                    "title": "X.2022.1080p.WEB",
                    "infoHash": "H7",
                    "guid": "g",
                    "indexerId": 7,
                    "size": 1,
                    "publishDate": "2026-07-14T00:00:00Z",
                    "tmdbId": 0,
                }
            ],
        )

    respx.get(url__regex=r"http://prowlarr/api/v1/search.*").mock(side_effect=search_side)
    respx.get("http://radarr/api/v3/movie").mock(return_value=httpx.Response(200, json=[]))
    respx.get(url__regex=r"http://radarr/api/v3/movie/lookup.*").mock(
        return_value=httpx.Response(200, json=[])
    )
    releases = fetch_releases(_settings())
    assert len(releases) == 1  # indexer 5 failed, skipped; indexer 7 fine
