from arr_dashboard.diagnostics import diagnose_stall
from arr_dashboard.models import Download


def _dl(**kw) -> Download:
    base = dict(infohash="a", name="n", state="forcedDL", progress=0.0, dl_speed=0)
    base.update(kw)
    return Download(**base)


def test_not_stalled_when_downloading():
    assert diagnose_stall(_dl(dl_speed=500_000)) is None


def test_not_stalled_when_complete():
    assert diagnose_stall(_dl(dl_speed=0, progress=1.0)) is None


def test_not_stalled_when_dl_speed_unknown():
    assert diagnose_stall(_dl(dl_speed=None)) is None


def test_metadata():
    d = diagnose_stall(_dl(state="metaDL"))
    assert d.cause == "metadata" and d.recoverable is True


def test_queued():
    d = diagnose_stall(_dl(state="queuedDL"))
    assert d.cause == "queued" and d.recoverable is True


def test_tracker_refused_c411():
    d = diagnose_stall(_dl(tracker_status=4, tracker_msg="Forbidden", tracker_host="c411.org"))
    assert d.cause == "tracker-refused"
    assert d.label == "tracker refuse: Forbidden"
    assert d.host == "c411.org"
    assert d.recoverable is True


def test_no_source_when_tracker_ok_and_no_seeders():
    d = diagnose_stall(_dl(tracker_status=2, num_complete=0))
    assert d.cause == "no-source"
    assert d.recoverable is False


def test_fallback_stalled():
    d = diagnose_stall(_dl(tracker_status=2, num_complete=5))
    assert d.cause == "stalled"
    assert d.recoverable is True
