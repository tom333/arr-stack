from arr_dashboard.cache import SnapshotCache
from arr_dashboard.models import Snapshot


def test_cache_starts_initializing_then_stores():
    cache = SnapshotCache()
    assert cache.get().initializing is True
    cache.set(Snapshot(rows=[], generated_at="t"))
    assert cache.get().initializing is False
    assert cache.get().generated_at == "t"
