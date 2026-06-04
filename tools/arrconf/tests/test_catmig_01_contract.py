"""TDD RED → GREEN tests for CATMIG-01 contract migration (Phase 32 Plan 01).

Covers:
- IntentConfig gains categories: list[Category] + apps: dict[str, Any]
- RootConfig no longer accepts categories: (extra_forbidden)
- 5 generators accept list[Category] instead of RootConfig
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from arrconf.resources.categories import Category


# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

_SINGLE_SERIES_CAT: dict[str, str] = {
    "name": "series",
    "kind": "series",
    "profile": "general",
    "display": "Séries",
    "base_path": "/media/series",
}

_SINGLE_MOVIES_CAT: dict[str, str] = {
    "name": "films",
    "kind": "movies",
    "profile": "general",
    "display": "Films",
    "base_path": "/media/films",
}


# ---------------------------------------------------------------------------
# IntentConfig tests
# ---------------------------------------------------------------------------


def test_intent_config_accepts_categories_and_apps() -> None:
    """IntentConfig.model_validate with categories + apps succeeds and exposes both fields."""
    from arrconf.intent_config import IntentConfig

    data: dict[str, Any] = {
        "categories": [_SINGLE_SERIES_CAT],
        "apps": {"sonarr": {"main": {"base_url": "http://sonarr.test"}}},
    }
    cfg = IntentConfig.model_validate(data)
    assert len(cfg.categories) == 1
    assert cfg.categories[0].name == "series"
    assert cfg.apps == {"sonarr": {"main": {"base_url": "http://sonarr.test"}}}


def test_intent_config_categories_default_empty() -> None:
    """IntentConfig() without categories defaults to []."""
    from arrconf.intent_config import IntentConfig

    cfg = IntentConfig()
    assert cfg.categories == []
    assert cfg.apps == {}


def test_intent_config_extra_forbid_preserved() -> None:
    """extra=forbid is preserved — unknown top-level keys still raise ValidationError."""
    from arrconf.intent_config import IntentConfig

    with pytest.raises(ValidationError):
        IntentConfig.model_validate({"unknown_top_level_key": "value"})


# ---------------------------------------------------------------------------
# RootConfig tests — categories must now be rejected
# ---------------------------------------------------------------------------


def test_root_config_rejects_categories() -> None:
    """After CATMIG-01: categories in arrconf.yml raises ValidationError (extra_forbidden)."""
    from arrconf.config import RootConfig

    with pytest.raises(ValidationError) as exc_info:
        RootConfig.model_validate({"categories": [_SINGLE_SERIES_CAT], "sonarr": {}})
    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" for e in errors)


def test_root_config_empty_still_valid() -> None:
    """RootConfig({}) must still parse cleanly (no required fields)."""
    from arrconf.config import RootConfig

    cfg = RootConfig.model_validate({})
    assert cfg.sonarr == {}
    assert cfg.radarr == {}


# ---------------------------------------------------------------------------
# Generator signature tests — list[Category] input
# ---------------------------------------------------------------------------


def _make_cats(raw: list[dict[str, str]]) -> list[Category]:
    return [Category.model_validate(c) for c in raw]


_PRODUCTION_CATS_RAW: list[dict[str, str]] = [
    {"name": "series", "kind": "series", "profile": "general", "display": "Séries", "base_path": "/media/series"},
    {"name": "series-emilie", "kind": "series", "profile": "general", "display": "Séries - Émilie", "base_path": "/media/series-emilie"},
    {"name": "series-thomas", "kind": "series", "profile": "general", "display": "Séries - Thomas", "base_path": "/media/series-thomas"},
    {"name": "series-garcons", "kind": "series", "profile": "family", "display": "Séries - Garçons", "base_path": "/media/series-garcons"},
    {"name": "series-zoe", "kind": "series", "profile": "anime", "display": "Séries - Zoé", "base_path": "/media/series-zoe"},
    {"name": "films", "kind": "movies", "profile": "general", "display": "Films", "base_path": "/media/films"},
    {"name": "nouveaux-films", "kind": "movies", "profile": "general", "display": "Nouveaux Films", "base_path": "/media/nouveaux-films"},
    {"name": "films-enfants", "kind": "movies", "profile": "family", "display": "Films - Enfants", "base_path": "/media/films-enfants"},
    {"name": "films-animation-enfants", "kind": "movies", "profile": "family", "display": "Films - Animation Enfants", "base_path": "/media/films-animation-enfants"},
    {"name": "films-zoe", "kind": "movies", "profile": "anime", "display": "Films - Zoé", "base_path": "/media/films-zoe"},
]


def test_generate_qbit_categories_takes_list() -> None:
    """generate_qbit_categories accepts list[Category], returns 10 items."""
    from arrconf.generators.categories import generate_qbit_categories

    cats = _make_cats(_PRODUCTION_CATS_RAW)
    result = generate_qbit_categories(cats)
    assert len(result) == 10
    assert result[0].name == "series"


def test_generate_qbit_categories_empty_list() -> None:
    from arrconf.generators.categories import generate_qbit_categories

    assert generate_qbit_categories([]) == []


def test_generate_sonarr_resources_takes_list() -> None:
    """generate_sonarr_resources accepts list[Category], returns SonarrDerived with 5 each."""
    from arrconf.generators.categories import SonarrDerived, generate_sonarr_resources

    cats = _make_cats(_PRODUCTION_CATS_RAW)
    result = generate_sonarr_resources(cats)
    assert isinstance(result, SonarrDerived)
    assert len(result.tags) == 5
    assert len(result.root_folders) == 5
    assert len(result.download_clients) == 5
    assert len(result.remote_path_mappings) == 5


def test_generate_radarr_resources_takes_list() -> None:
    """generate_radarr_resources accepts list[Category], returns RadarrDerived with 5 each."""
    from arrconf.generators.categories import RadarrDerived, generate_radarr_resources

    cats = _make_cats(_PRODUCTION_CATS_RAW)
    result = generate_radarr_resources(cats)
    assert isinstance(result, RadarrDerived)
    assert len(result.tags) == 5


def test_generate_jellyfin_libraries_takes_list() -> None:
    """generate_jellyfin_libraries accepts list[Category], returns 10 libs."""
    from arrconf.generators.categories import generate_jellyfin_libraries

    cats = _make_cats(_PRODUCTION_CATS_RAW)
    result = generate_jellyfin_libraries(cats)
    assert len(result) == 10


def test_generate_anime_tag_labels_takes_list() -> None:
    """generate_anime_tag_labels accepts list[Category], returns anime labels."""
    from arrconf.generators.categories import generate_anime_tag_labels

    cats = _make_cats(_PRODUCTION_CATS_RAW)
    result = generate_anime_tag_labels(cats)
    assert set(result) == {"series-zoe", "films-zoe"}


def test_generate_anime_tag_labels_empty_list() -> None:
    from arrconf.generators.categories import generate_anime_tag_labels

    assert generate_anime_tag_labels([]) == []
