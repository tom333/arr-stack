"""Tests for the locked SagaEntry schema (Phase 29, SAGAS-01 / D-02).

Covers:
- Valid kind=movies saga (all required fields present)
- Invalid kind=movies without tmdb_collection
- Invalid kind=movies without profile
- Invalid kind=movies without root
- Valid kind=series saga (items list of titles)
- Invalid SagaEntry with extra forbidden key
- Invalid kind value (neither movies nor series)
"""

import pytest
from pydantic import ValidationError

from arrconf.intent_config import SagaEntry


def test_movies_saga_valid() -> None:
    """kind=movies with all required fields validates OK."""
    saga = SagaEntry(
        name="James Bond",
        kind="movies",
        tmdb_collection=645,
        profile="MULTi.VF",
        root="/media/films",
    )
    assert saga.name == "James Bond"
    assert saga.kind == "movies"
    assert saga.tmdb_collection == 645
    assert saga.profile == "MULTi.VF"
    assert saga.root == "/media/films"


def test_movies_saga_missing_tmdb_collection_raises() -> None:
    """kind=movies without tmdb_collection raises ValidationError."""
    with pytest.raises(ValidationError, match="tmdb_collection"):
        SagaEntry(
            name="x",
            kind="movies",
            profile="MULTi.VF",
            root="/media/films",
        )


def test_movies_saga_missing_profile_raises() -> None:
    """kind=movies without profile raises ValidationError."""
    with pytest.raises(ValidationError, match="profile"):
        SagaEntry(
            name="x",
            kind="movies",
            tmdb_collection=645,
            root="/media/films",
        )


def test_movies_saga_missing_root_raises() -> None:
    """kind=movies without root raises ValidationError."""
    with pytest.raises(ValidationError, match="root"):
        SagaEntry(
            name="x",
            kind="movies",
            tmdb_collection=645,
            profile="MULTi.VF",
        )


def test_series_saga_valid() -> None:
    """kind=series with items list of titles validates OK."""
    saga = SagaEntry(
        name="Star Wars",
        kind="series",
        items=["Andor", "The Mandalorian"],
    )
    assert saga.name == "Star Wars"
    assert saga.kind == "series"
    assert saga.items == ["Andor", "The Mandalorian"]


def test_extra_field_forbidden() -> None:
    """Extra fields on SagaEntry raise ValidationError (extra=forbid)."""
    with pytest.raises(ValidationError):
        SagaEntry(name="x", kind="series", bogus="z")  # type: ignore[call-arg]


def test_invalid_kind_raises() -> None:
    """Kind values other than movies|series raise ValidationError."""
    with pytest.raises(ValidationError):
        SagaEntry(name="x", kind="other")  # type: ignore[arg-type]
