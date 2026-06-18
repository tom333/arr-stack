import httpx
import respx
from arr_dashboard.import_runner import perform_import
from arr_dashboard.models import ChainHealth, Download, Row
from arrconf.client_base import RadarrClient


def _row():
    return Row(
        key="tmdb:42",
        title="M",
        type="movie",
        arr_app="radarr",
        arr_id=7,
        has_file=False,
        chain=ChainHealth(),
        downloads=[
            Download(
                infohash="abc",
                name="M.mkv",
                state="stalledUP",
                progress=1.0,
                save_path="/data/x",
                content_path="/data/x/M.mkv",
                size=4096,
            )
        ],
    )


def _mock_no_mappings():
    respx.get("http://r:7878/api/v3/remotepathmapping").mock(
        return_value=httpx.Response(200, json=[])
    )


@respx.mock
def test_perform_import_copies_matching_file():
    _mock_no_mappings()
    respx.get("http://r:7878/api/v3/manualimport").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "path": "/data/x/M.mkv",
                    "movie": {"id": 7},
                    "quality": {"q": 1},
                    "languages": [],
                    "rejections": [],
                },
                {
                    "path": "/data/x/other.mkv",
                    "movie": {"id": 999},
                    "quality": {},
                    "languages": [],
                    "rejections": [],
                },
            ],
        )
    )
    cmd = respx.post("http://r:7878/api/v3/command").mock(
        return_value=httpx.Response(201, json={"id": 5, "status": "started"})
    )
    respx.get("http://r:7878/api/v3/command/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "status": "completed"})
    )

    perform_import(_row(), RadarrClient("http://r:7878", "key"))

    import json

    body = json.loads(cmd.calls.last.request.content)
    assert body["importMode"] == "Copy"
    assert [f["movieId"] for f in body["files"]] == [7]  # only the matching file


@respx.mock
def test_perform_import_raises_when_no_match():
    _mock_no_mappings()
    respx.get("http://r:7878/api/v3/manualimport").mock(
        return_value=httpx.Response(
            200,
            json=[{"path": "/data/x/other.mkv", "movie": {"id": 999}, "rejections": []}],
        )
    )
    import pytest

    with pytest.raises(Exception):
        perform_import(_row(), RadarrClient("http://r:7878", "key"))


@respx.mock
def test_perform_import_skips_candidate_without_path():
    _mock_no_mappings()
    respx.get("http://r:7878/api/v3/manualimport").mock(
        return_value=httpx.Response(
            200,
            json=[{"movie": {"id": 7}, "rejections": []}],  # matches arr_id but no path
        )
    )
    import pytest

    with pytest.raises(Exception):
        perform_import(_row(), RadarrClient("http://r:7878", "key"))


@respx.mock
def test_perform_import_raises_when_no_content_path():
    _mock_no_mappings()
    import pytest

    row = _row()
    row.downloads[0].content_path = None
    with pytest.raises(Exception):
        perform_import(row, RadarrClient("http://r:7878", "key"))


@respx.mock
def test_perform_import_translates_content_path_to_arr_view():
    # qBit reports the stranded file under the unmapped /data/incomplete; the mapping
    # encodes the volume root (/data/ -> /data/torrents/). Import must scan the
    # TRANSLATED folder, not qBit's raw path. This is the Snow-White/Mermaid fix.
    respx.get("http://r:7878/api/v3/remotepathmapping").mock(
        return_value=httpx.Response(
            200,
            json=[{"remotePath": "/data/films/", "localPath": "/data/torrents/films/"}],
        )
    )
    mi = respx.get("http://r:7878/api/v3/manualimport").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "path": "/data/torrents/incomplete/radarr/M.mkv",
                    "movie": {"id": 7},
                    "quality": {},
                    "languages": [],
                    "rejections": [],
                }
            ],
        )
    )
    respx.post("http://r:7878/api/v3/command").mock(
        return_value=httpx.Response(201, json={"id": 5, "status": "started"})
    )
    respx.get("http://r:7878/api/v3/command/5").mock(
        return_value=httpx.Response(200, json={"id": 5, "status": "completed"})
    )

    row = _row()
    row.downloads[0].content_path = "/data/incomplete/radarr/M.mkv"
    perform_import(row, RadarrClient("http://r:7878", "key"))

    folder = dict(mi.calls.last.request.url.params)["folder"]
    assert folder == "/data/torrents/incomplete/radarr"  # translated + file -> dirname
