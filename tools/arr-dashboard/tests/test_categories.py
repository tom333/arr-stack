from arr_dashboard.categories import load_movie_categories, load_series_categories

_INTENT = """
categories:
  - {name: nouveaux-films, kind: movies, profile: general, display: Nouveaux Films, base_path: /media/nouveaux-films}
  - {name: series, kind: series, profile: general, display: Séries, base_path: /media/series}
  - {name: series-emilie, kind: series, profile: general, display: Séries - Émilie, base_path: /media/series-emilie}
  - {name: series-thomas, kind: series, profile: general, display: Séries - Thomas, base_path: /media/series-thomas}
  - {name: series-garcons, kind: series, profile: family, display: Séries - Garçons, base_path: /media/series-garcons}
  - {name: series-zoe, kind: series, profile: anime, display: Séries - Zoé, base_path: /media/series-zoe}
category_quality_profiles: {general: MULTi.VF, anime: Anime, family: Family}
profile_definitions: {}
configarr: {}
"""


def _write_intent(tmp_path):
    p = tmp_path / "intent.yml"
    p.write_text(_INTENT)
    return str(p)


def test_load_series_categories_returns_five_with_series_type(tmp_path):
    path = _write_intent(tmp_path)
    cats = load_series_categories(path)
    names = [c.name for c in cats]
    assert names == ["series", "series-emilie", "series-thomas", "series-garcons", "series-zoe"]
    by_name = {c.name: c for c in cats}
    assert by_name["series-zoe"].series_type == "anime"
    assert by_name["series-zoe"].profile == "Anime"
    assert by_name["series-garcons"].series_type == "standard"
    assert by_name["series-garcons"].profile == "Family"
    assert by_name["series"].series_type == "standard"
    assert by_name["series"].profile == "MULTi.VF"
    assert by_name["series"].root_path == "/media/series"


def test_load_movie_categories_unaffected_and_series_type_blank(tmp_path):
    path = _write_intent(tmp_path)
    cats = load_movie_categories(path)
    assert [c.name for c in cats] == ["nouveaux-films"]
    assert cats[0].series_type == ""


def test_load_series_categories_empty_when_intent_absent():
    assert load_series_categories("/does/not/exist.yml") == []
