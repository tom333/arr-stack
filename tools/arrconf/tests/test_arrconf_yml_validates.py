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
from arrconf.generators.categories import (
    generate_jellyfin_libraries,
    generate_qbit_categories,
    generate_radarr_resources,
    generate_sonarr_resources,
)

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
    """Phase 12-B (D-01): generator outputs derive from categories[], NOT from
    deleted flat sections. Production arrconf.yml has 10 categories — 5 series-kind
    + 5 movies-kind — so generators produce 10 qbit categories, 5 sonarr tags,
    5 radarr tags, and so on per side.
    """
    cfg = load_config(ARRCONF_YML)
    assert isinstance(cfg, RootConfig)
    # qbittorrent.main must exist; categories come from generator (Phase 12-B)
    assert "main" in cfg.qbittorrent, "qbittorrent.main not declared"
    qbt_categories = generate_qbit_categories(cfg)
    cat_names = {c.name for c in qbt_categories}
    expected_cats = {
        "series",
        "series-emilie",
        "series-thomas",
        "series-garcons",
        "series-zoe",
        "films",
        "nouveaux-films",
        "films-enfants",
        "films-animation-enfants",
        "films-zoe",
    }
    assert cat_names == expected_cats, f"qBit categories mismatch: {cat_names}"
    # Sonarr.main: generator-derived from 5 series categories
    assert "main" in cfg.sonarr, "sonarr.main not declared"
    sonarr = cfg.sonarr["main"]
    sonarr_derived = generate_sonarr_resources(cfg)
    series_names = {c.name for c in cfg.categories if c.kind == "series"}
    assert {t.label for t in sonarr_derived.tags} == series_names
    assert len(sonarr_derived.root_folders) == 5
    assert len(sonarr_derived.download_clients) == 5
    assert len(sonarr_derived.remote_path_mappings) == 5
    assert sonarr.series_tags.default_tag == "tv", "series_tags.default_tag != tv"
    # Radarr.main: generator-derived from 5 movies categories
    assert "main" in cfg.radarr, "radarr.main not declared"
    radarr = cfg.radarr["main"]
    radarr_derived = generate_radarr_resources(cfg)
    movies_names = {c.name for c in cfg.categories if c.kind == "movies"}
    assert {t.label for t in radarr_derived.tags} == movies_names
    assert len(radarr_derived.root_folders) == 5
    assert len(radarr_derived.download_clients) == 5
    assert len(radarr_derived.remote_path_mappings) == 5
    assert radarr.movie_tags.default_tag == "movies", "movie_tags.default_tag != movies"


def test_arrconf_yml_validates_against_json_schema() -> None:
    from ruyaml import YAML

    y = YAML(typ="safe")
    with ARRCONF_YML.open("r", encoding="utf-8") as f:
        doc = y.load(f)
    schema = json.loads(ARRCONF_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(doc, schema)


def test_arrconf_yml_all_remote_path_mappings_end_with_slash() -> None:
    """Phase 12-B (D-01): 10 RPMs total (5 series + 5 movies), one per category."""
    cfg = load_config(ARRCONF_YML)
    sonarr_rpms = generate_sonarr_resources(cfg).remote_path_mappings
    radarr_rpms = generate_radarr_resources(cfg).remote_path_mappings
    all_rpms = list(sonarr_rpms) + list(radarr_rpms)
    n_rpms = len(all_rpms)
    assert n_rpms == 10, f"Expected 10 RPMs total (5+5), got {n_rpms}"
    for rpm in all_rpms:
        assert rpm.remotePath.endswith("/"), (
            f"Pitfall 6 violation: remotePath {rpm.remotePath!r} does not end with '/'"
        )
        assert rpm.localPath.endswith("/"), (
            f"Pitfall 6 violation: localPath {rpm.localPath!r} does not end with '/'"
        )


def test_arrconf_yml_films_category_uses_data_torrents_films() -> None:
    """D-05-PATHS-01 spirit: the canonical movies-bucket category ('films') maps
    to /data/torrents/films. Phase 12-B (D-01): generator now emits paths keyed
    on category names (not v0.2.0 'radarr-movies')."""
    cfg = load_config(ARRCONF_YML)
    cats = {c.name: c.savePath for c in generate_qbit_categories(cfg)}
    assert "films" in cats, "films category not declared"
    assert cats["films"] == "/data/torrents/films", (
        f"films savePath is {cats['films']!r}, expected '/data/torrents/films'"
    )


def test_arrconf_yml_all_qbit_categories_have_explicit_save_path() -> None:
    cfg = load_config(ARRCONF_YML)
    for cat in generate_qbit_categories(cfg):
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


# -- Phase 7 assertions (D-07-INSTANCE-01 + D-07-LIB-01 + D-07-USERS-01
#    + D-07-CONFIG-01 + D-07-PLUGINS-01) --


def test_arrconf_yml_validates_jellyfin() -> None:
    """Live chart YAML parses against the Phase 7 pydantic schema (D-07-INSTANCE-01).

    Regression contract — prevents shipping a chart-side jellyfin block that
    does not match the arrconf RootConfig schema. Mirrors the Seerr
    test_arrconf_yml_validates pattern.
    """
    cfg = load_config(ARRCONF_YML)
    assert "main" in cfg.jellyfin, (
        "charts/arr-stack/files/arrconf.yml missing jellyfin.main section"
    )

    j = cfg.jellyfin["main"]
    assert j.base_url == "http://jellyfin.selfhost.svc.cluster.local:8096"

    # Libraries (Phase 16 D-16-LIB-CREATE-01: 10 entries, 1 PathInfo each)
    jf_libraries = generate_jellyfin_libraries(cfg)
    assert len(jf_libraries) == 10
    # First entry mirrors first Category in arrconf.yml — Séries.
    assert jf_libraries[0].name == "Séries"
    assert jf_libraries[0].collection_type == "tvshows"
    assert jf_libraries[0].paths == ["/media/series"]
    # 5 tvshows + 5 movies (D-16-COLLECTIONTYPE-01 mapping)
    assert sum(1 for lib in jf_libraries if lib.collection_type == "tvshows") == 5
    assert sum(1 for lib in jf_libraries if lib.collection_type == "movies") == 5
    # D-16-PRUNE-01 default — operator opts in via YAML at cutover time.
    assert j.libraries.prune is False

    # Users (D-07-USERS-01: admin only, emilie protection)
    assert j.users.admin.IsAdministrator is True
    assert j.users.prune is False  # D-07-USERS-01 hardcoded — emilie protection

    # Server config (D-07-CONFIG-01: 7-field allowlist)
    assert j.server_config.ui_culture == "fr"
    assert j.server_config.metadata_country_code == "FR"
    assert j.server_config.activity_log_retention_days == 30
    assert len(j.server_config.plugin_repositories) == 1
    assert j.server_config.plugin_repositories[0].Url == (
        "https://repo.jellyfin.org/files/plugin/manifest.json"
    )

    # Plugins (D-07-PLUGINS-01: 6 plugins, activation-only)
    assert len(j.plugins.required) == 6
    plugin_names = [p.name for p in j.plugins.required]
    assert "TMDb" in plugin_names
    assert "Kodi Sync Queue" in plugin_names


# -- Phase 9 assertions (D-01, D-02, D-03, D-04 — categories block) ----------


def test_arrconf_yml_has_10_categories() -> None:
    """REQ-categories-10-target: production arrconf.yml declares exactly 10 categories.

    Asserts count, order, (name, kind, profile) tuples (D-01 + D-02), and the
    D-04 base_path invariant (/media/{name}). W-03: ruyaml parse-roundtrip check
    follows immediately after in test_arrconf_yml_categories_ruyaml_roundtrip.
    """
    cfg = load_config(ARRCONF_YML)
    assert len(cfg.categories) == 10, f"Expected 10 categories, got {len(cfg.categories)}"

    expected = [
        ("series", "series", "general"),
        ("series-emilie", "series", "general"),
        ("series-thomas", "series", "general"),
        ("series-garcons", "series", "family"),
        ("series-zoe", "series", "anime"),
        ("films", "movies", "general"),
        ("nouveaux-films", "movies", "general"),
        ("films-enfants", "movies", "family"),
        ("films-animation-enfants", "movies", "family"),
        ("films-zoe", "movies", "anime"),
    ]
    actual = [(c.name, c.kind, c.profile) for c in cfg.categories]
    assert actual == expected, f"Categories order/values mismatch: {actual}"

    for cat in cfg.categories:
        assert cat.base_path == f"/media/{cat.name}", (
            f"D-04 violation: base_path {cat.base_path!r} != /media/{cat.name!r}"
        )


def test_arrconf_yml_categories_ruyaml_roundtrip() -> None:
    """W-03 belt-and-suspenders: ruyaml can parse arrconf.yml + categories validates raw."""
    from ruyaml import YAML

    yaml = YAML(typ="safe")
    with ARRCONF_YML.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    cats = data.get("categories", [])
    assert len(cats) == 10, f"ruyaml saw {len(cats)} categories, expected 10"
    for cat in cats:
        assert cat["base_path"] == f"/media/{cat['name']}", (
            f"D-04 ruyaml-roundtrip violation: {cat}"
        )


def test_arrconf_yml_no_provider_ids_in_jellyfin_users() -> None:
    """Pitfall 6 / D-06-OPENAPI-01 carry-forward — defensive parse-level check.

    AuthenticationProviderId + PasswordResetProviderId MUST be re-injected
    from cluster GET, NEVER from YAML. If a future operator edits the chart
    to add them, the reconciler would land them in the POST body and stomp
    the cluster auth provider configuration.

    Note: comments in arrconf.yml cite these field names for documentation;
    the check verifies the PARSED YAML data (not raw text) does not contain them
    as actual keys in the jellyfin.main.users.admin block.
    """
    from ruyaml import YAML

    yaml = YAML(typ="safe")
    with ARRCONF_YML.open("r", encoding="utf-8") as f:
        data = yaml.load(f)

    admin_block = data.get("jellyfin", {}).get("main", {}).get("users", {}).get("admin", {})
    assert "AuthenticationProviderId" not in admin_block, (
        "Pitfall 6: AuthenticationProviderId leaked into YAML jellyfin.main.users.admin — "
        "reconciler re-injects this from cluster GET; YAML must not specify it."
    )
    assert "PasswordResetProviderId" not in admin_block, (
        "Pitfall 6: PasswordResetProviderId leaked into YAML jellyfin.main.users.admin — "
        "reconciler re-injects this from cluster GET; YAML must not specify it."
    )
