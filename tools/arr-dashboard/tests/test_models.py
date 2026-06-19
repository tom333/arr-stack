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


def test_download_new_fields_default_none_and_diagnosis():
    from arr_dashboard.models import Download, StallDiagnosis

    d = Download(infohash="a", name="n", state="forcedDL", progress=0.0)
    # all new qBit/tracker fields default to None
    assert d.dl_speed is None and d.eta is None and d.num_seeds is None
    assert d.num_complete is None and d.num_leechs is None and d.num_incomplete is None
    assert d.ratio is None and d.added_on is None
    assert d.tracker_status is None and d.tracker_msg is None and d.tracker_host is None
    assert d.diagnosis is None

    diag = StallDiagnosis(
        cause="tracker-refused",
        label="tracker refuse: Forbidden",
        host="c411.org",
        recoverable=True,
    )
    d2 = Download(infohash="b", name="n", state="forcedDL", progress=0.0, diagnosis=diag)
    assert d2.diagnosis.cause == "tracker-refused"
    assert d2.diagnosis.host == "c411.org"
