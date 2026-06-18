import json

import pytest

from arr_dashboard.models import Download, Row
from arr_dashboard.recovery_actions import (
    RecoveryActionError,
    delete_download,
    jellyfin_scan,
    remove_stuck,
)


class FakeQbit:
    def __init__(self) -> None:
        self.deleted: list[dict[str, str]] = []

    def post_form(self, path: str, data: dict[str, str]) -> None:
        self.deleted.append({"path": path, **data})


class FakeArr:
    def __init__(self, queue: list[dict]) -> None:
        self._queue = queue
        self.deleted: list[tuple[str, int]] = []

    def list_queue(self) -> list[dict]:
        return self._queue

    def delete(self, path: str, id: int, **kwargs: object) -> None:
        self.deleted.append((path, id))


class FakeJellyfin:
    def __init__(self, raise_204: bool = False) -> None:
        self.calls: list[tuple[str, object]] = []
        self._raise_204 = raise_204

    def post(self, path: str, json_body: object) -> object:
        self.calls.append((path, json_body))
        if self._raise_204:
            raise json.JSONDecodeError("Expecting value", "", 0)
        return {}


def _row(**kw) -> Row:
    base = dict(key="tmdb:1", title="M", type="movie")
    base.update(kw)
    return Row(**base)


def test_delete_download_calls_qbit_delete_with_files():
    qb = FakeQbit()
    delete_download("HASH1", qb)
    assert qb.deleted == [{"path": "/torrents/delete", "hashes": "HASH1", "deleteFiles": "true"}]


def test_remove_stuck_deletes_only_stuck_and_cleans_queue():
    row = _row(
        arr_app="sonarr",
        arr_id=5,
        downloads=[
            Download(infohash="aaa", name="a", state="stalledDL", progress=0.3),
            Download(infohash="bbb", name="b", state="downloading", progress=0.5),
            Download(infohash="ccc", name="c", state="error", progress=0.0),
        ],
    )
    qb = FakeQbit()
    arr = FakeArr(queue=[{"id": 10, "downloadId": "AAA"}, {"id": 11, "downloadId": "ZZZ"}])
    remove_stuck(row, qb, arr)
    # only stuck hashes deleted from qBit
    assert {d["hashes"] for d in qb.deleted} == {"aaa", "ccc"}
    assert all(d["deleteFiles"] == "true" for d in qb.deleted)
    # arr queue record matching a stuck hash (case-insensitive) dropped; non-matching kept
    assert arr.deleted == [("/queue", 10)]


def test_remove_stuck_raises_when_no_stuck_download():
    row = _row(downloads=[Download(infohash="aaa", name="a", state="downloading", progress=0.5)])
    with pytest.raises(RecoveryActionError):
        remove_stuck(row, FakeQbit(), FakeArr(queue=[]))


def test_jellyfin_scan_posts_updates_for_each_disk_path():
    row = _row(disk_paths=["/media/films/A", "/media/films/B"])
    jf = FakeJellyfin()
    jellyfin_scan(row, jf)
    assert jf.calls == [
        (
            "/Library/Media/Updated",
            {
                "Updates": [
                    {"Path": "/media/films/A", "UpdateType": "Created"},
                    {"Path": "/media/films/B", "UpdateType": "Created"},
                ]
            },
        )
    ]


def test_jellyfin_scan_tolerates_204_no_content():
    row = _row(disk_paths=["/media/films/A"])
    jellyfin_scan(row, FakeJellyfin(raise_204=True))  # must not raise


def test_jellyfin_scan_raises_when_no_disk_path():
    with pytest.raises(RecoveryActionError):
        jellyfin_scan(_row(disk_paths=[]), FakeJellyfin())
