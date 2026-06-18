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


def test_import_action_requires_confirm_and_enqueues():
    from arr_dashboard.cache import SnapshotCache
    from arr_dashboard.models import ChainHealth, Download, Row, Snapshot

    cache = SnapshotCache()
    cache.set(
        Snapshot(
            rows=[
                Row(
                    key="tmdb:42",
                    title="M",
                    type="movie",
                    arr_app="radarr",
                    arr_id=7,
                    has_file=False,
                    chain=ChainHealth(),
                    downloads=[
                        Download(
                            infohash="a",
                            name="M.mkv",
                            state="stalledUP",
                            progress=1.0,
                            save_path="/data/x",
                            size=4096,
                        )
                    ],
                    flags=["non-importe"],
                )
            ],
            generated_at="t",
        )
    )
    app = create_app(cache=cache, start_refresher=False)
    client = TestClient(app)

    # missing confirm → 400
    assert client.post("/api/actions/import", json={"key": "tmdb:42"}).status_code == 400
    # unknown key → 404
    assert (
        client.post("/api/actions/import", json={"key": "tmdb:999", "confirm": True}).status_code
        == 404
    )
    # valid → queued
    r = client.post("/api/actions/import", json={"key": "tmdb:42", "confirm": True})
    assert r.status_code == 200
    assert r.json()["state"] == "queued"
    # listed
    actions = client.get("/api/actions").json()
    assert any(a["key"] == "tmdb:42" for a in actions)
