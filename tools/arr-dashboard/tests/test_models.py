from arr_dashboard.models import ChainHealth, Download, Row, Snapshot


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
