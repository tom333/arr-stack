from arr_dashboard.models import ActionJob, ChainHealth, Download, Row, Snapshot


def test_row_defaults_and_serialization():
    row = Row(
        key="tmdb:42",
        title="M",
        type="movie",
        chain=ChainHealth(
            requested=True,
            grabbed=True,
            downloaded=True,
            imported=False,
            in_jellyfin=False,
        ),
    )
    dumped = row.model_dump()
    assert dumped["downloads"] == []
    assert dumped["flags"] == []
    assert dumped["chain"]["imported"] is False


def test_snapshot_holds_rows():
    snap = Snapshot(rows=[], generated_at="2026-06-18T00:00:00Z", stale_sources=["jellyfin"])
    assert snap.stale_sources == ["jellyfin"]


def test_download_model():
    d = Download(infohash="ab", name="x", state="downloading", progress=0.5)
    assert d.category is None


def test_download_has_size():
    d = Download(infohash="a", name="x", state="downloading", progress=0.5, size=123)
    assert d.size == 123


def test_row_has_arr_id():
    r = Row(key="tmdb:1", title="M", type="movie", arr_id=42, chain=ChainHealth())
    assert r.arr_id == 42


def test_action_job_defaults():
    j = ActionJob(key="tmdb:1", title="M", app="radarr")
    assert j.state == "queued"
    assert j.message is None
