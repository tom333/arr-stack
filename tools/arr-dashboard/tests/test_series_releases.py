import httpx
import respx

from arr_dashboard.series_releases import fetch_series_releases, parse_series_title
from arr_dashboard.settings import Settings


def test_parse_season_episode():
    p = parse_series_title("The.Show.S02E11.FRENCH.1080p.WEB.x265-Niroma")
    assert p["series_name"] == "The Show"
    assert p["episode_label"] == "S02E11"
    assert p["resolution"] == "1080p"
    assert p["source"] == "WEB"
    assert p["codec"] == "x265"
    assert p["language"] == "FRENCH"


def test_parse_season_only():
    p = parse_series_title("Some.Series.S01.MULTI.1080p.BluRay.x264")
    assert p["series_name"] == "Some Series"
    assert p["episode_label"] == "S01"


def test_parse_complete_integrale():
    p = parse_series_title("Une.Serie.INTEGRALE.MULTI.720p.HDTV.x264")
    assert p["series_name"] == "Une Serie"
    assert p["episode_label"] == "COMPLETE"


def test_parse_unknown_bits_are_none():
    p = parse_series_title("Some Series Title")
    assert p["episode_label"] is None
    assert p["resolution"] is None


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
        "title": "The.Show.S02E11.FRENCH.1080p.WEB.x265",
        "infoHash": "AAA",
        "guid": "g1",
        "indexerId": 7,
        "size": 100,
        "publishDate": "2026-07-14T00:00:00Z",
        "tvdbId": 0,
        "seeders": 12,
        "leechers": 3,
    }
    respx.get(url__regex=r"http://prowlarr/api/v1/search.*").mock(
        return_value=httpx.Response(200, json=[rel, rel])
    )  # same infohash twice
    respx.get("http://sonarr/api/v3/series").mock(return_value=httpx.Response(200, json=[]))
    respx.get(url__regex=r"http://sonarr/api/v3/series/lookup.*").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "title": "The Show",
                    "year": 2022,
                    "tvdbId": 550,
                    "genres": ["Drama"],
                    "images": [{"coverType": "poster", "remoteUrl": "http://img/p.jpg"}],
                }
            ],
        )
    )

    releases = fetch_series_releases(_settings())
    assert len(releases) == 1
    assert releases[0].info_hash == "AAA"
    assert releases[0].indexer_name == "Torr9"
    assert releases[0].tmdb_id == 550  # tvdbId carried in tmdb_id field
    assert releases[0].in_library is False
    assert releases[0].seeders == 12
    assert releases[0].genres == ["Drama"]
    assert releases[0].poster_url == "http://img/p.jpg"
    assert releases[0].episode_label == "S02E11"
    assert releases[0].year == 2022


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
                    "title": "X.S01E01.1080p.WEB",
                    "infoHash": "H7",
                    "guid": "g",
                    "indexerId": 7,
                    "size": 1,
                    "publishDate": "2026-07-14T00:00:00Z",
                    "tvdbId": 0,
                }
            ],
        )

    respx.get(url__regex=r"http://prowlarr/api/v1/search.*").mock(side_effect=search_side)
    respx.get("http://sonarr/api/v3/series").mock(return_value=httpx.Response(200, json=[]))
    respx.get(url__regex=r"http://sonarr/api/v3/series/lookup.*").mock(
        return_value=httpx.Response(200, json=[])
    )
    releases = fetch_series_releases(_settings())
    assert len(releases) == 1  # indexer 5 failed, skipped; indexer 7 fine


@respx.mock
def test_fetch_flags_in_library_via_sonarr_series():
    respx.get("http://prowlarr/api/v1/indexer").mock(
        return_value=httpx.Response(200, json=[{"id": 7, "name": "Torr9", "enable": True}])
    )
    respx.get(url__regex=r"http://prowlarr/api/v1/search.*").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "title": "The.Show.S02E11.1080p.WEB",
                    "infoHash": "AAA",
                    "guid": "g1",
                    "indexerId": 7,
                    "size": 100,
                    "publishDate": "2026-07-14T00:00:00Z",
                    "tvdbId": 550,
                }
            ],
        )
    )
    respx.get("http://sonarr/api/v3/series").mock(
        return_value=httpx.Response(200, json=[{"tvdbId": 550}])
    )
    respx.get(url__regex=r"http://sonarr/api/v3/series/lookup.*").mock(
        return_value=httpx.Response(200, json=[{"title": "The Show", "tvdbId": 550, "year": 2022}])
    )
    releases = fetch_series_releases(_settings())
    assert releases[0].in_library is True


@respx.mock
def test_fetch_enriches_three_distinct_series_via_parallel_lookup():
    """3 releases, 3 distinct lookup terms -> each Release gets its own tvdb/genres/year,
    proving the parallel term->Enrichment map assembles back onto the right release."""
    respx.get("http://prowlarr/api/v1/indexer").mock(
        return_value=httpx.Response(200, json=[{"id": 7, "name": "Torr9", "enable": True}])
    )
    eps = [
        {
            "title": "Alpha.Show.S01E01.1080p.WEB",
            "infoHash": "H1",
            "guid": "g1",
            "indexerId": 7,
            "size": 1,
            "publishDate": "2026-07-14T00:00:00Z",
            "tvdbId": 0,
        },
        {
            "title": "Beta.Show.S01E01.1080p.WEB",
            "infoHash": "H2",
            "guid": "g2",
            "indexerId": 7,
            "size": 1,
            "publishDate": "2026-07-14T00:00:00Z",
            "tvdbId": 0,
        },
        {
            "title": "Gamma.Show.S01E01.1080p.WEB",
            "infoHash": "H3",
            "guid": "g3",
            "indexerId": 7,
            "size": 1,
            "publishDate": "2026-07-14T00:00:00Z",
            "tvdbId": 0,
        },
    ]
    respx.get(url__regex=r"http://prowlarr/api/v1/search.*").mock(
        return_value=httpx.Response(200, json=eps)
    )
    respx.get("http://sonarr/api/v3/series").mock(return_value=httpx.Response(200, json=[]))

    def lookup_side(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "Alpha" in url:
            return httpx.Response(
                200, json=[{"tvdbId": 111, "year": 2020, "genres": ["Action"], "images": []}]
            )
        if "Beta" in url:
            return httpx.Response(
                200, json=[{"tvdbId": 222, "year": 2021, "genres": ["Drama"], "images": []}]
            )
        return httpx.Response(
            200, json=[{"tvdbId": 333, "year": 2022, "genres": ["Comedy"], "images": []}]
        )

    respx.get(url__regex=r"http://sonarr/api/v3/series/lookup.*").mock(side_effect=lookup_side)

    releases = fetch_series_releases(_settings())
    assert len(releases) == 3
    by_hash = {r.info_hash: r for r in releases}
    assert by_hash["H1"].tmdb_id == 111 and by_hash["H1"].genres == ["Action"]
    assert by_hash["H1"].year == 2020
    assert by_hash["H2"].tmdb_id == 222 and by_hash["H2"].year == 2021
    assert by_hash["H3"].tmdb_id == 333 and by_hash["H3"].year == 2022


@respx.mock
def test_fetch_dedups_lookup_call_for_shared_series_term():
    """2 episodes of the same show (different infoHash) share the same series-name
    lookup term -> exactly ONE Sonarr lookup call, not two."""
    respx.get("http://prowlarr/api/v1/indexer").mock(
        return_value=httpx.Response(200, json=[{"id": 7, "name": "Torr9", "enable": True}])
    )
    eps = [
        {
            "title": "Same.Show.S01E01.1080p.WEB",
            "infoHash": "H1",
            "guid": "g1",
            "indexerId": 7,
            "size": 1,
            "publishDate": "2026-07-14T00:00:00Z",
            "tvdbId": 0,
        },
        {
            "title": "Same.Show.S01E02.1080p.WEB",
            "infoHash": "H2",
            "guid": "g2",
            "indexerId": 7,
            "size": 1,
            "publishDate": "2026-07-14T00:00:00Z",
            "tvdbId": 0,
        },
    ]
    respx.get(url__regex=r"http://prowlarr/api/v1/search.*").mock(
        return_value=httpx.Response(200, json=eps)
    )
    respx.get("http://sonarr/api/v3/series").mock(return_value=httpx.Response(200, json=[]))
    lookup_route = respx.get(url__regex=r"http://sonarr/api/v3/series/lookup.*").mock(
        return_value=httpx.Response(
            200, json=[{"tvdbId": 999, "year": 2020, "genres": [], "images": []}]
        )
    )

    releases = fetch_series_releases(_settings())
    assert len(releases) == 2
    assert lookup_route.call_count == 1
