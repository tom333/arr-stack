"""Tests for Category pydantic model — Phase 9 D-01/D-02/D-04/D-05 invariants.

Requirements covered: REQ-categories-schema.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from arrconf.resources.categories import Category

# The 10 production categories (verbatim from 09-CONTEXT.md §Specifics)
PRODUCTION_CATEGORIES = [
    {
        "name": "series",
        "kind": "series",
        "profile": "general",
        "display": "Séries",
        "base_path": "/media/series",
    },
    {
        "name": "series-emilie",
        "kind": "series",
        "profile": "general",
        "display": "Séries - Émilie",
        "base_path": "/media/series-emilie",
    },
    {
        "name": "series-thomas",
        "kind": "series",
        "profile": "general",
        "display": "Séries - Thomas",
        "base_path": "/media/series-thomas",
    },
    {
        "name": "series-garcons",
        "kind": "series",
        "profile": "family",
        "display": "Séries - Garçons",
        "base_path": "/media/series-garcons",
    },
    {
        "name": "series-zoe",
        "kind": "series",
        "profile": "anime",
        "display": "Séries - Zoé",
        "base_path": "/media/series-zoe",
    },
    {
        "name": "films",
        "kind": "movies",
        "profile": "general",
        "display": "Films",
        "base_path": "/media/films",
    },
    {
        "name": "nouveaux-films",
        "kind": "movies",
        "profile": "general",
        "display": "Nouveaux Films",
        "base_path": "/media/nouveaux-films",
    },
    {
        "name": "films-enfants",
        "kind": "movies",
        "profile": "family",
        "display": "Films - Enfants",
        "base_path": "/media/films-enfants",
    },
    {
        "name": "films-animation-enfants",
        "kind": "movies",
        "profile": "family",
        "display": "Films - Animation Enfants",
        "base_path": "/media/films-animation-enfants",
    },
    {
        "name": "films-zoe",
        "kind": "movies",
        "profile": "anime",
        "display": "Films - Zoé",
        "base_path": "/media/films-zoe",
    },
]


@pytest.mark.parametrize("data", PRODUCTION_CATEGORIES, ids=lambda d: d["name"])
def test_production_categories_validate(data: dict) -> None:  # type: ignore[type-arg]
    """All 10 production categories must parse cleanly (D-01/D-02/D-03/D-04 conjunction)."""
    cat = Category(**data)
    assert cat.name == data["name"]
    assert cat.kind == data["kind"]
    assert cat.profile == data["profile"]
    assert cat.display == data["display"]
    assert cat.base_path == data["base_path"]


@pytest.mark.parametrize(
    "bad_name",
    [
        "Series_Emilie",
        "SERIES",
        "series--emilie",
        "-series",
        "series-",
        "séries",
        "series emilie",
        "",
    ],
)
def test_kebab_case_name_violations(bad_name: str) -> None:
    """Non-kebab-case names must be rejected by the pattern= validator."""
    with pytest.raises(ValidationError, match="String should match pattern"):
        Category(
            name=bad_name,
            kind="series",
            profile="general",
            display="X",
            base_path=f"/media/{bad_name}",
        )


@pytest.mark.parametrize("bad_kind", ["music", "shorts", "books", "", "Movies"])
def test_kind_enum_violations(bad_kind: str) -> None:
    """Only 'movies' or 'series' (Literal) — D-01/D-02."""
    with pytest.raises(ValidationError):
        Category(
            name="x",
            kind=bad_kind,  # type: ignore[arg-type]
            profile="general",
            display="X",
            base_path="/media/x",
        )


@pytest.mark.parametrize("bad_profile", ["documentary", "kids", "", "General"])
def test_profile_enum_violations(bad_profile: str) -> None:
    """Only 'general'/'anime'/'family' (Literal) — D-01/D-02."""
    with pytest.raises(ValidationError):
        Category(
            name="x",
            kind="movies",
            profile=bad_profile,  # type: ignore[arg-type]
            display="X",
            base_path="/media/x",
        )


@pytest.mark.parametrize(
    "name,bad_base_path",
    [
        ("x", "/media/y"),
        ("x", "/data/x"),
        ("x", "/media/x/sub"),
        ("series-emilie", "/media/series_emilie"),
    ],
)
def test_base_path_invariant_violations(name: str, bad_base_path: str) -> None:
    """D-04: base_path MUST equal /media/{name}."""
    with pytest.raises(ValidationError, match="D-04 strict invariant"):
        Category(name=name, kind="movies", profile="general", display="X", base_path=bad_base_path)


def test_extra_forbid() -> None:
    """extra='forbid' rejects unknown fields."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Category(
            name="x",
            kind="movies",
            profile="general",
            display="X",
            base_path="/media/x",
            rogue="field",  # type: ignore[call-arg]
        )


@pytest.mark.parametrize("missing_field", ["name", "kind", "profile", "display", "base_path"])
def test_missing_required_field(missing_field: str) -> None:
    """Every field is required (no defaults)."""
    data: dict[str, str] = {
        "name": "x",
        "kind": "movies",
        "profile": "general",
        "display": "X",
        "base_path": "/media/x",
    }
    del data[missing_field]
    with pytest.raises(ValidationError, match=r"Field required|missing"):
        Category(**data)  # type: ignore[arg-type]
