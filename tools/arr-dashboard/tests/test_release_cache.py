from arr_dashboard.release_cache import ReleaseCache


def test_cache_serves_until_invalidated():
    calls = {"n": 0}

    def build():
        calls["n"] += 1
        return [calls["n"]]

    c = ReleaseCache(ttl_seconds=10_000)
    assert c.get(build) == [1]
    assert c.get(build) == [1]  # cached, builder not called again
    assert calls["n"] == 1
    c.invalidate()
    assert c.get(build) == [2]  # rebuilt after invalidate
    assert calls["n"] == 2


def test_cache_rebuilds_after_ttl():
    calls = {"n": 0}

    def build():
        calls["n"] += 1
        return calls["n"]

    ticks = {"t": 0.0}
    c = ReleaseCache(ttl_seconds=100, clock=lambda: ticks["t"])
    assert c.get(build) == 1
    ticks["t"] = 50.0
    assert c.get(build) == 1  # within TTL
    ticks["t"] = 150.0
    assert c.get(build) == 2  # past TTL -> rebuilt
