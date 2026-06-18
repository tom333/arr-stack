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
                size=4096,
            )
        ],
    )


@respx.mock
def test_perform_import_copies_matching_file():
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
    respx.get("http://r:7878/api/v3/manualimport").mock(
        return_value=httpx.Response(
            200,
            json=[{"movie": {"id": 7}, "rejections": []}],  # matches arr_id but no path
        )
    )
    import pytest

    with pytest.raises(Exception):
        perform_import(_row(), RadarrClient("http://r:7878", "key"))
