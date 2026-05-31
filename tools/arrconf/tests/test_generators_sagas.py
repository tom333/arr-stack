"""Tests for generators/sagas.py — pure generate_sagas_desired function (Phase 29, SAGAS-01).

Covers:
- Empty sagas list returns empty SagasDesiredState
- Single kind=movies saga produces radarr_collections entry, empty series lists
- Single kind=series saga with items produces series_boxsets + series_tag_titles
- Mixed movies+series split correctly across three lists
- Pure: calling twice with same input returns equal results (no mutation/I/O)
"""

from arrconf.generators.sagas import SagasDesiredState, generate_sagas_desired
from arrconf.intent_config import SagaEntry


def _movies_saga(
    name: str = "James Bond",
    tmdb_collection: int = 645,
    profile: str = "MULTi.VF",
    root: str = "/media/films",
) -> SagaEntry:
    return SagaEntry(
        name=name,
        kind="movies",
        tmdb_collection=tmdb_collection,
        profile=profile,
        root=root,
    )


def _series_saga(
    name: str = "Star Wars",
    items: list[str] | None = None,
) -> SagaEntry:
    return SagaEntry(
        name=name,
        kind="series",
        items=items or ["Andor", "The Mandalorian"],
    )


def test_empty_sagas_returns_empty_state() -> None:
    """Empty sagas list → all three lists empty."""
    result = generate_sagas_desired([])
    assert isinstance(result, SagasDesiredState)
    assert result.radarr_collections == []
    assert result.series_boxsets == []
    assert result.series_tag_titles == []


def test_single_movies_saga_produces_radarr_collections() -> None:
    """Single kind=movies saga → one radarr_collections entry, empty series lists."""
    saga = _movies_saga()
    result = generate_sagas_desired([saga])

    assert len(result.radarr_collections) == 1
    assert result.series_boxsets == []
    assert result.series_tag_titles == []

    entry = result.radarr_collections[0]
    assert entry["tmdb_collection"] == 645
    assert entry["profile"] == "MULTi.VF"
    assert entry["root"] == "/media/films"
    assert entry["name"] == "James Bond"


def test_single_series_saga_produces_boxsets_and_titles() -> None:
    """Single kind=series saga → empty radarr_collections, one boxset, correct titles."""
    saga = _series_saga(name="Star Wars", items=["Andor", "The Mandalorian"])
    result = generate_sagas_desired([saga])

    assert result.radarr_collections == []
    assert len(result.series_boxsets) == 1
    assert result.series_tag_titles == ["Andor", "The Mandalorian"]
    assert result.series_boxsets[0].name == "Star Wars"


def test_mixed_sagas_split_correctly() -> None:
    """Mixed movies+series sagas split correctly across three output lists."""
    bond = _movies_saga(name="James Bond", tmdb_collection=645)
    trek = _movies_saga(name="Star Trek", tmdb_collection=115)
    star_wars = _series_saga(name="Star Wars", items=["Andor", "The Mandalorian"])
    marvel = _series_saga(name="Marvel Netflix", items=["Daredevil"])

    result = generate_sagas_desired([bond, trek, star_wars, marvel])

    assert len(result.radarr_collections) == 2
    assert {c["name"] for c in result.radarr_collections} == {"James Bond", "Star Trek"}
    assert len(result.series_boxsets) == 2
    assert {s.name for s in result.series_boxsets} == {"Star Wars", "Marvel Netflix"}
    assert "Andor" in result.series_tag_titles
    assert "The Mandalorian" in result.series_tag_titles
    assert "Daredevil" in result.series_tag_titles


def test_generate_sagas_desired_is_pure() -> None:
    """Calling twice with same input returns equal results (no mutation/I/O)."""
    sagas = [_movies_saga(), _series_saga()]
    result1 = generate_sagas_desired(sagas)
    result2 = generate_sagas_desired(sagas)

    assert result1.radarr_collections == result2.radarr_collections
    assert result1.series_tag_titles == result2.series_tag_titles
    assert len(result1.series_boxsets) == len(result2.series_boxsets)
    assert result1.series_boxsets[0].name == result2.series_boxsets[0].name
