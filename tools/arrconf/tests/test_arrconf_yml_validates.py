"""Chart-side validation tests for charts/arr-stack/files/arrconf.yml.

These tests ensure the declarative YAML source-of-truth round-trips cleanly
through pydantic (RootConfig) and validates against the generated JSON Schema
(schemas/arrconf-schema.json). They act as belt-and-suspenders to catch drift
between the chart YAML and the pydantic models.

Plan 05-07 threat mitigations:
- T-05-CATPATH: pydantic extra='forbid' rejects typos; JSON Schema validates structure.
- Pitfall 3 invariant: every qBit category MUST declare an explicit savePath.
- Pitfall 6 invariant: remotePath and localPath MUST end with '/'.
- D-05-PATHS-01: radarr-movies uses /data/films (NOT /data/movies).
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from arrconf.config import RootConfig, load_config

# ---------------------------------------------------------------------------
# Path helpers — relative to this file (tools/arrconf/tests/ — 3 dirs from repo root)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
ARRCONF_YML = REPO_ROOT / "charts" / "arr-stack" / "files" / "arrconf.yml"
ARRCONF_SCHEMA = REPO_ROOT / "schemas" / "arrconf-schema.json"


def test_files_exist() -> None:
    assert ARRCONF_YML.exists(), f"arrconf.yml not found at {ARRCONF_YML}"
    assert ARRCONF_SCHEMA.exists(), f"arrconf-schema.json not found at {ARRCONF_SCHEMA}"


def test_arrconf_yml_validates_against_pydantic() -> None:
    cfg = load_config(ARRCONF_YML)
    assert isinstance(cfg, RootConfig)
    # qbittorrent.main must exist with 6 categories
    assert "main" in cfg.qbittorrent, "qbittorrent.main not declared"
    qbit = cfg.qbittorrent["main"]
    cat_names = {c.name for c in qbit.categories.items}
    expected_cats = {
        "sonarr-tv",
        "sonarr-anime",
        "sonarr-family",
        "radarr-movies",
        "radarr-anime",
        "radarr-family",
    }
    assert cat_names == expected_cats, f"qBit categories mismatch: {cat_names}"
    # Sonarr.main: 3 tags, 3 root folders, 3 download clients, 4 RPMs, series_tags
    assert "main" in cfg.sonarr, "sonarr.main not declared"
    sonarr = cfg.sonarr["main"]
    n_sonarr_tags = len(sonarr.tags.items)
    assert n_sonarr_tags == 3, f"sonarr tags count: {n_sonarr_tags}"
    n_sonarr_rf = len(sonarr.root_folders.items)
    assert n_sonarr_rf == 3, f"sonarr root_folders: {n_sonarr_rf}"
    n_sonarr_dc = len(sonarr.download_clients.items)
    assert n_sonarr_dc == 3, f"sonarr DCs: {n_sonarr_dc}"
    n_sonarr_rpm = len(sonarr.remote_path_mappings.items)
    assert n_sonarr_rpm == 4, f"sonarr RPMs: {n_sonarr_rpm}"
    assert sonarr.series_tags.default_tag == "tv", "series_tags.default_tag != tv"
    # Radarr.main: 3 tags, 3 root folders, 3 download clients, 4 RPMs, movie_tags
    assert "main" in cfg.radarr, "radarr.main not declared"
    radarr = cfg.radarr["main"]
    n_radarr_tags = len(radarr.tags.items)
    assert n_radarr_tags == 3, f"radarr tags count: {n_radarr_tags}"
    n_radarr_rf = len(radarr.root_folders.items)
    assert n_radarr_rf == 3, f"radarr root_folders: {n_radarr_rf}"
    n_radarr_dc = len(radarr.download_clients.items)
    assert n_radarr_dc == 3, f"radarr DCs: {n_radarr_dc}"
    n_radarr_rpm = len(radarr.remote_path_mappings.items)
    assert n_radarr_rpm == 4, f"radarr RPMs: {n_radarr_rpm}"
    assert radarr.movie_tags.default_tag == "movies", "movie_tags.default_tag != movies"
    # Sonarr tag labels: tv, anime, family
    sonarr_tag_labels = {t.label for t in sonarr.tags.items}
    assert sonarr_tag_labels == {"tv", "anime", "family"}, f"sonarr tag labels: {sonarr_tag_labels}"
    # Radarr tag labels: movies, anime, family (D-05-SPLIT-02)
    radarr_tag_labels = {t.label for t in radarr.tags.items}
    assert radarr_tag_labels == {"movies", "anime", "family"}, (
        f"radarr tag labels: {radarr_tag_labels}"
    )


def test_arrconf_yml_validates_against_json_schema() -> None:
    from ruyaml import YAML

    y = YAML(typ="safe")
    with ARRCONF_YML.open("r", encoding="utf-8") as f:
        doc = y.load(f)
    schema = json.loads(ARRCONF_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)


def test_arrconf_yml_all_remote_path_mappings_end_with_slash() -> None:
    cfg = load_config(ARRCONF_YML)
    sonarr_rpms = cfg.sonarr["main"].remote_path_mappings.items
    radarr_rpms = cfg.radarr["main"].remote_path_mappings.items
    all_rpms = list(sonarr_rpms) + list(radarr_rpms)
    n_rpms = len(all_rpms)
    assert n_rpms == 8, f"Expected 8 RPMs total (4+4), got {n_rpms}"
    for rpm in all_rpms:
        assert rpm.remotePath.endswith("/"), (
            f"Pitfall 6 violation: remotePath {rpm.remotePath!r} does not end with '/'"
        )
        assert rpm.localPath.endswith("/"), (
            f"Pitfall 6 violation: localPath {rpm.localPath!r} does not end with '/'"
        )


def test_arrconf_yml_radarr_movies_category_uses_films_path() -> None:
    cfg = load_config(ARRCONF_YML)
    cats = {c.name: c.savePath for c in cfg.qbittorrent["main"].categories.items}
    assert "radarr-movies" in cats, "radarr-movies category not declared"
    assert cats["radarr-movies"] == "/data/films", (
        f"D-05-PATHS-01 violation: radarr-movies savePath is {cats['radarr-movies']!r}, "
        "expected '/data/films' (not '/data/movies')"
    )


def test_arrconf_yml_all_qbit_categories_have_explicit_save_path() -> None:
    cfg = load_config(ARRCONF_YML)
    for cat in cfg.qbittorrent["main"].categories.items:
        assert cat.savePath, (
            f"Pitfall 3 violation: category {cat.name!r} has empty savePath — "
            "must be explicit (qBit treats empty as default save path)"
        )


def test_arrconf_yml_prowlarr_apps_declared() -> None:
    cfg = load_config(ARRCONF_YML)
    assert "main" in cfg.prowlarr, "prowlarr.main not declared"
    apps = cfg.prowlarr["main"].apps.items
    app_names = {a.name for a in apps}
    assert "Sonarr" in app_names, f"Sonarr app not declared in prowlarr.main: {app_names}"
    assert "Radarr" in app_names, f"Radarr app not declared in prowlarr.main: {app_names}"


# -- Phase 6 assertions (D-06-SCOPE-01 + D-06-RETAG-01) ------------------------


def test_arrconf_yml_has_seerr_main_block() -> None:
    """charts/arr-stack/files/arrconf.yml validates against RootConfig with a seerr.main block."""
    cfg = load_config(ARRCONF_YML)
    assert "main" in cfg.seerr, "Phase 6 must wire seerr.main into the chart YAML"
    seerr_main = cfg.seerr["main"]
    # T-06-CREDS-LEAK: no apiKey at the YAML layer (D-06-CREDS-01 — runtime preservation).
    # SeerrSonarrServiceSection has NO apiKey field (Plan 06-02) — enforced by pydantic.
    # User defaults verified:
    assert seerr_main.users.admin.permissions == 2, (
        "Phase 6: admin permissions=2 (ADMIN per research bitmask)"
    )
    assert seerr_main.main_settings.defaultPermissions == 32, (
        "Phase 6: defaultPermissions=32 (REQUEST per research)"
    )
    # Anime routing fields configured (D-06-Q10-01 mechanism):
    assert seerr_main.sonarr_service.activeAnimeProfileId is not None, (
        "Phase 6: activeAnimeProfileId required for anime routing"
    )
    assert seerr_main.sonarr_service.activeAnimeDirectory == "/media/anime"
    assert seerr_main.sonarr_service.animeTags, "Phase 6: animeTags must be non-empty"
    assert seerr_main.sonarr_service.tagRequests is True
    # Radarr-side: NO animeTags field (research-verified absence on Radarr-side Seerr schema)
    assert not hasattr(seerr_main.radarr_service, "animeTags"), (
        "SeerrRadarrServiceSection MUST NOT have animeTags (research-verified)"
    )


def test_arrconf_yml_sonarr_content_routing_has_family_and_anime() -> None:
    """Sonarr content_routing wires both family + anime rules (D-06-RETAG-01)."""
    cfg = load_config(ARRCONF_YML)
    rules = cfg.sonarr["main"].content_routing.rules
    rule_tags = {r.tag for r in rules}
    assert "family" in rule_tags, "Sonarr Phase 6 must have a family rule"
    assert "anime" in rule_tags, (
        "Sonarr Phase 6 must have an anime rule (gap-fill for items Seerr missed)"
    )
    # Pitfall 5: family keywords must NOT include "Animation"
    family_rule = next(r for r in rules if r.tag == "family")
    assert "Animation" not in family_rule.keywords, (
        "Pitfall 5: 'Animation' must NEVER appear in Sonarr family keywords"
    )
    assert family_rule.keywords == ["Family", "Kids", "Children"], (
        "Sonarr family keywords must be the conservative trio per Pitfall 5"
    )


def test_arrconf_yml_radarr_content_routing_has_NO_anime_rule() -> None:
    """Pitfall 5 enforced at the chart layer: Radarr MUST NOT have an anime rule.

    TMDB has no 'Anime' first-class genre; 'Animation' would catch Pixar/Disney
    (false-positive). Anime films stay manual-tag until a future phase ships an
    originalLanguage-based filter (deferred — D-06+1).
    """
    cfg = load_config(ARRCONF_YML)
    rules = cfg.radarr["main"].content_routing.rules
    rule_tags = {r.tag for r in rules}
    assert "anime" not in rule_tags, (
        "Pitfall 5: Radarr MUST NOT have an anime rule (TMDB Animation catches Pixar/Disney)"
    )
    # Family rule MUST exist:
    assert "family" in rule_tags, (
        "Radarr Phase 6 must have the family rule (operator's stated need)"
    )
    family_rule = next(r for r in rules if r.tag == "family")
    # Pitfall 5: family keywords on Radarr are JUST ["Family"] — TMDB doesn't use Kids/Children
    assert family_rule.keywords == ["Family"], (
        "Radarr family keywords MUST be ['Family'] only (TMDB taxonomy)"
    )
