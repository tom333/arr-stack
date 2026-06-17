from arr_dashboard.correlate import correlate
from tests.conftest import sources


def test_radarr_movie_becomes_row():
    src = sources(
        radarr_movies=[
            {
                "id": 1,
                "title": "Ratatouille",
                "year": 2007,
                "tmdbId": 2062,
                "hasFile": True,
                "monitored": True,
                "movieFile": {"path": "/media/films/Ratatouille.mkv"},
            }
        ]
    )
    snap = correlate(src, "2026-06-18T00:00:00Z", [])
    row = snap.rows[0]
    assert row.key == "tmdb:2062"
    assert row.type == "movie"
    assert row.arr_app == "radarr"
    assert row.has_file is True
    assert row.disk_paths == ["/media/films/Ratatouille.mkv"]
    assert row.chain.imported is True


def test_sonarr_series_becomes_row():
    src = sources(
        sonarr_series=[
            {
                "id": 9,
                "title": "Supernatural",
                "year": 2005,
                "tvdbId": 78901,
                "monitored": True,
                "statistics": {"episodeCount": 22, "episodeFileCount": 22},
            }
        ]
    )
    snap = correlate(src, "t", [])
    row = snap.rows[0]
    assert row.key == "tvdb:78901"
    assert row.type == "series"
    assert row.has_file is True  # all episodes present
    assert row.chain.imported is True


def test_download_linked_via_queue_sets_chain():
    src = sources(
        radarr_movies=[
            {
                "id": 1,
                "title": "M",
                "tmdbId": 42,
                "hasFile": False,
                "monitored": True,
            }
        ],
        radarr_queue=[
            {"movieId": 1, "downloadId": "ABCDEF", "trackedDownloadStatus": "ok"}
        ],
        qbit_torrents=[
            {
                "hash": "abcdef",
                "name": "M.2025.mkv",
                "state": "downloading",
                "progress": 0.5,
                "category": "radarr-movies",
                "save_path": "/data/x",
                "tracker": "http://t/announce",
            }
        ],
    )
    snap = correlate(src, "t", [])
    row = snap.rows[0]
    assert len(row.downloads) == 1
    assert row.downloads[0].infohash == "abcdef"
    assert row.chain.grabbed is True
    assert row.chain.downloaded is False  # progress 0.5


def test_seerr_request_sets_requested_and_requester():
    src = sources(
        radarr_movies=[
            {"id": 1, "title": "M", "tmdbId": 42, "hasFile": False, "monitored": True}
        ],
        seerr_requests=[
            {
                "id": 7,
                "type": "movie",
                "status": 2,
                "media": {"tmdbId": 42},
                "requestedBy": {"displayName": "Thomas"},
            }
        ],
    )
    snap = correlate(src, "t", [])
    row = snap.rows[0]
    assert row.chain.requested is True
    assert row.requested_by == "Thomas"
    assert row.request_status == "approved"


def test_seerr_request_with_no_arr_item_creates_pending_row():
    src = sources(
        seerr_requests=[
            {
                "id": 8,
                "type": "movie",
                "status": 1,
                "media": {"tmdbId": 99},
                "requestedBy": {"displayName": "Emilie"},
            }
        ]
    )
    snap = correlate(src, "t", [])
    row = [r for r in snap.rows if r.key == "tmdb:99"][0]
    assert row.chain.requested is True
    assert row.chain.grabbed is False
    assert row.request_status == "pending"


def test_jellyfin_presence_sets_in_jellyfin():
    src = sources(
        radarr_movies=[
            {
                "id": 1,
                "title": "Ratatouille",
                "tmdbId": 2062,
                "hasFile": True,
                "monitored": True,
                "movieFile": {"path": "/media/films/Ratatouille.mkv"},
            }
        ],
        jellyfin_items=[
            {"Name": "Ratatouille", "Type": "Movie", "ProviderIds": {"Tmdb": "2062"}}
        ],
    )
    snap = correlate(src, "t", [])
    row = snap.rows[0]
    assert row.in_jellyfin is True
    assert row.chain.in_jellyfin is True
