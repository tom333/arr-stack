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


def _row_snapshot(**row_kw):
    from arr_dashboard.models import Row, Snapshot

    cache = SnapshotCache()
    cache.set(Snapshot(rows=[Row(**row_kw)], generated_at="t"))
    return cache


def _settings_full():
    from arr_dashboard.settings import Settings

    return Settings(
        sonarr_url="http://sonarr:8989",
        radarr_url="http://radarr:7878",
        qbittorrent_url="http://qb:8080",
        seerr_url="http://seerr:5055",
        jellyfin_url="http://jf:8096",
        sonarr_api_key="k",
        radarr_api_key="k",
        seerr_api_key="k",
        jellyfin_api_key="k",
        qbt_user="u",
        qbt_pass="p",
    )


def test_delete_download_requires_confirm_and_404():
    from arr_dashboard.models import Download

    cache = _row_snapshot(
        key="tmdb:42",
        title="M",
        type="movie",
        downloads=[Download(infohash="aaa", name="a", state="stalledDL", progress=0.2)],
    )
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    # missing confirm → 400
    assert (
        client.post(
            "/api/actions/delete-download", json={"key": "tmdb:42", "infohash": "aaa"}
        ).status_code
        == 400
    )
    # unknown key → 404
    assert (
        client.post(
            "/api/actions/delete-download",
            json={"key": "nope", "infohash": "aaa", "confirm": True},
        ).status_code
        == 404
    )


def test_jellyfin_scan_dispatches(monkeypatch):
    cache = _row_snapshot(key="tmdb:42", title="M", type="movie", disk_paths=["/media/films/M"])
    called = {}

    def fake_scan(row, jellyfin):
        called["paths"] = row.disk_paths

    monkeypatch.setattr("arr_dashboard.app.jellyfin_scan", fake_scan)
    monkeypatch.setattr("arr_dashboard.app.build_jellyfin", lambda s: object())
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    r = client.post("/api/actions/jellyfin-scan", json={"key": "tmdb:42"})
    assert r.status_code == 200
    assert called["paths"] == ["/media/films/M"]


def test_delete_download_dispatches(monkeypatch):
    from arr_dashboard.models import Download

    cache = _row_snapshot(
        key="tmdb:42",
        title="M",
        type="movie",
        downloads=[Download(infohash="aaa", name="a", state="stalledDL", progress=0.2)],
    )
    got = {}
    monkeypatch.setattr(
        "arr_dashboard.app.delete_download", lambda infohash, qbit: got.update(h=infohash)
    )
    monkeypatch.setattr("arr_dashboard.app.build_qbit", lambda s: object())
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    r = client.post(
        "/api/actions/delete-download",
        json={"key": "tmdb:42", "infohash": "aaa", "confirm": True},
    )
    assert r.status_code == 200
    assert got["h"] == "aaa"


def test_remove_stuck_no_qbit_client_400(monkeypatch):
    from arr_dashboard.models import Download

    cache = _row_snapshot(
        key="tmdb:42",
        title="M",
        type="movie",
        arr_app="radarr",
        arr_id=1,
        downloads=[Download(infohash="aaa", name="a", state="stalledDL", progress=0.2)],
    )
    monkeypatch.setattr("arr_dashboard.app.build_qbit", lambda s: None)  # qBit down/absent
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    r = client.post("/api/actions/remove", json={"key": "tmdb:42", "confirm": True})
    assert r.status_code == 400


def test_delete_download_recovery_error_409(monkeypatch):
    from arr_dashboard.models import Download
    from arr_dashboard.recovery_actions import RecoveryActionError

    cache = _row_snapshot(
        key="tmdb:42",
        title="M",
        type="movie",
        downloads=[Download(infohash="aaa", name="a", state="stalledDL", progress=0.2)],
    )

    def boom(infohash, qbit):
        raise RecoveryActionError("boom")

    monkeypatch.setattr("arr_dashboard.app.delete_download", boom)
    monkeypatch.setattr("arr_dashboard.app.build_qbit", lambda s: object())
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    r = client.post(
        "/api/actions/delete-download",
        json={"key": "tmdb:42", "infohash": "aaa", "confirm": True},
    )
    assert r.status_code == 409


def test_remove_recovery_error_409(monkeypatch):
    from arr_dashboard.models import Download
    from arr_dashboard.recovery_actions import RecoveryActionError

    cache = _row_snapshot(
        key="tmdb:42",
        title="M",
        type="movie",
        arr_app="radarr",
        arr_id=1,
        downloads=[Download(infohash="aaa", name="a", state="stalledDL", progress=0.2)],
    )

    def boom(row, qbit, arr):
        raise RecoveryActionError("boom")

    monkeypatch.setattr("arr_dashboard.app.remove_stuck", boom)
    monkeypatch.setattr("arr_dashboard.app.build_qbit", lambda s: object())
    monkeypatch.setattr("arr_dashboard.app.build_clients", lambda s: {"radarr": object()})
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    r = client.post("/api/actions/remove", json={"key": "tmdb:42", "confirm": True})
    assert r.status_code == 409


def test_jellyfin_scan_recovery_error_409(monkeypatch):
    from arr_dashboard.recovery_actions import RecoveryActionError

    cache = _row_snapshot(key="tmdb:42", title="M", type="movie", disk_paths=[])

    def boom(row, jellyfin):
        raise RecoveryActionError("boom")

    monkeypatch.setattr("arr_dashboard.app.jellyfin_scan", boom)
    monkeypatch.setattr("arr_dashboard.app.build_jellyfin", lambda s: object())
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    r = client.post("/api/actions/jellyfin-scan", json={"key": "tmdb:42"})
    assert r.status_code == 409


def test_reannounce_dispatches_no_confirm(monkeypatch):
    from arr_dashboard.models import Download

    cache = _row_snapshot(
        key="tmdb:42",
        title="M",
        type="movie",
        downloads=[Download(infohash="aaa", name="a", state="forcedDL", progress=0.0)],
    )
    got = {}
    monkeypatch.setattr(
        "arr_dashboard.app.reannounce", lambda infohash, qbit: got.update(h=infohash)
    )
    monkeypatch.setattr("arr_dashboard.app.build_qbit", lambda s: object())
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    r = client.post("/api/actions/reannounce", json={"key": "tmdb:42", "infohash": "aaa"})
    assert r.status_code == 200
    assert got["h"] == "aaa"
    assert (
        client.post("/api/actions/reannounce", json={"key": "nope", "infohash": "aaa"}).status_code
        == 404
    )


def test_reannounce_no_qbit_client_400(monkeypatch):
    from arr_dashboard.models import Download

    cache = _row_snapshot(
        key="tmdb:42",
        title="M",
        type="movie",
        downloads=[Download(infohash="aaa", name="a", state="forcedDL", progress=0.0)],
    )
    monkeypatch.setattr("arr_dashboard.app.build_qbit", lambda s: None)
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    r = client.post("/api/actions/reannounce", json={"key": "tmdb:42", "infohash": "aaa"})
    assert r.status_code == 400


def test_recheck_requires_confirm_and_dispatches(monkeypatch):
    from arr_dashboard.models import Download

    cache = _row_snapshot(
        key="tmdb:42",
        title="M",
        type="movie",
        downloads=[Download(infohash="aaa", name="a", state="forcedDL", progress=0.0)],
    )
    got = {}
    monkeypatch.setattr("arr_dashboard.app.recheck", lambda infohash, qbit: got.update(h=infohash))
    monkeypatch.setattr("arr_dashboard.app.build_qbit", lambda s: object())
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    assert (
        client.post("/api/actions/recheck", json={"key": "tmdb:42", "infohash": "aaa"}).status_code
        == 400
    )
    r = client.post(
        "/api/actions/recheck", json={"key": "tmdb:42", "infohash": "aaa", "confirm": True}
    )
    assert r.status_code == 200
    assert got["h"] == "aaa"
