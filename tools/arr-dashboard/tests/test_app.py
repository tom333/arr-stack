from fastapi.testclient import TestClient

from arr_dashboard.app import create_app
from arr_dashboard.cache import SnapshotCache
from arr_dashboard.models import ChainHealth, Row, Snapshot


def test_dashboard_endpoint_serves_cache():
    cache = SnapshotCache()
    cache.set(
        Snapshot(
            rows=[
                Row(
                    key="tmdb:1",
                    title="M",
                    type="movie",
                    chain=ChainHealth(),
                    flags=["ok"],
                )
            ],
            generated_at="t",
            stale_sources=["jellyfin"],
        )
    )
    app = create_app(cache=cache, start_refresher=False)
    client = TestClient(app)
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert body["rows"][0]["key"] == "tmdb:1"
    assert body["stale_sources"] == ["jellyfin"]


def test_healthz():
    app = create_app(cache=SnapshotCache(), start_refresher=False)
    assert TestClient(app).get("/healthz").status_code == 200
