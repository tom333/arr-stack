from arr_dashboard.models import Release, ScoredRelease


def test_release_roundtrip():
    r = Release(
        title="Bubble.2022.FRENCH.1080p.WEB.x265",
        info_hash="ABC123",
        guid="http://x/download",
        indexer_id=7,
        indexer_name="Torr9",
        size=2_000_000_000,
        publish_date="2026-07-14T00:00:00Z",
        year=2022,
        tmdb_id=550,
        resolution="1080p",
        source="WEB",
        codec="x265",
        language="FRENCH",
        in_library=False,
    )
    assert r.model_dump()["info_hash"] == "ABC123"
    assert r.model_dump()["tmdb_id"] == 550


def test_scored_release_wraps_release():
    r = Release(
        title="x",
        info_hash="H",
        guid="g",
        indexer_id=1,
        indexer_name="i",
        size=1,
        publish_date="2026-07-14T00:00:00Z",
        year=None,
        tmdb_id=None,
        resolution=None,
        source=None,
        codec=None,
        language=None,
        in_library=False,
    )
    sr = ScoredRelease(
        release=r, score=800, accepted=True, quality="WEB 1080p", reasons=["+800 x265"]
    )
    assert sr.accepted and sr.score == 800
