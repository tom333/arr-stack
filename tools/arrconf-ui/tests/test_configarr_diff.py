"""Tests for configarr-shape structured diff (D-05 / D-06 / SC#4).

configarr_diff groups changes per-quality-profile and per-custom-format,
preserves ``!env`` literals in the diff output, and reuses no arrconf-
shape diff code.
"""

from __future__ import annotations

from typing import Any

import pytest

from arrconf_ui.configarr_diff import configarr_diff, has_changes


# ---------------------------------------------------------------------------
# Test fixtures — minimal configarr-shaped dicts (tag-literal data)
# ---------------------------------------------------------------------------

SONARR_MAIN_BASE: dict[str, Any] = {
    "base_url": "http://sonarr:8989",
    "api_key": "!env SONARR_API_KEY",  # tag-literal as produced by _tagged_to_literal
    "quality_profiles": [
        {
            "name": "MULTi.VF",
            "upgrade": {"allowed": True, "until_quality": "Bluray-1080p", "until_score": 10000},
            "min_format_score": 0,
            "score_set": "frenchHD",
        },
        {
            "name": "Anime",
            "upgrade": {"allowed": True, "until_quality": "Bluray-1080p", "until_score": 10000},
            "min_format_score": 0,
        },
    ],
    "custom_formats": [
        {
            "trash_ids": ["fr-vff"],
            "assign_scores_to": [{"name": "MULTi.VF", "score": 150}],
        },
    ],
}

RADARR_MAIN_BASE: dict[str, Any] = {
    "base_url": "http://radarr:7878",
    "api_key": "!env RADARR_API_KEY",
    "quality_profiles": [
        {
            "name": "MULTi.VF",
            "upgrade": {"allowed": True, "until_quality": "Bluray-1080p", "until_score": 10000},
        },
    ],
    "custom_formats": [],
}

BASE_CONFIG: dict[str, Any] = {
    "trashGuideUrl": "https://github.com/TRaSH-Guides/Guides",
    "recyclarrConfigUrl": "https://github.com/recyclarr/config-templates",
    "customFormatDefinitions": [],
    "sonarr": {"main": SONARR_MAIN_BASE},
    "radarr": {"main": RADARR_MAIN_BASE},
}


def deep_copy(d: Any) -> Any:
    """Simple deep copy via JSON round-trip (safe for plain dict/list/scalar)."""
    import json

    return json.loads(json.dumps(d))


# ---------------------------------------------------------------------------
# Test 1: per-quality-profile grouping — changed score shows under that profile
# ---------------------------------------------------------------------------


def test_changed_quality_profile_score_groups_under_profile_name() -> None:
    """A changed quality_profile score groups the change under that profile name."""
    before = deep_copy(BASE_CONFIG)
    after = deep_copy(BASE_CONFIG)

    # Modify min_format_score on MULTi.VF in sonarr.main
    after["sonarr"]["main"]["quality_profiles"][0]["min_format_score"] = 100

    diff = configarr_diff(before, after)

    # sonarr.main should be in the diff
    assert "sonarr.main" in diff, f"sonarr.main not in diff keys: {list(diff.keys())}"
    sonarr_diff = diff["sonarr.main"]

    # quality_profiles section should list the changed profile
    assert "quality_profiles" in sonarr_diff
    qp_diff = sonarr_diff["quality_profiles"]
    assert "MULTi.VF" in qp_diff, f"MULTi.VF not in quality_profiles diff: {qp_diff}"
    mutlivf_diff = qp_diff["MULTi.VF"]
    # Must have changed_fields
    assert "changed_fields" in mutlivf_diff
    assert len(mutlivf_diff["changed_fields"]) > 0

    # Unchanged profile (Anime) still present with empty change-set (predictable shape)
    assert "Anime" in qp_diff
    anime_diff = qp_diff["Anime"]
    assert "changed_fields" in anime_diff
    assert len(anime_diff["changed_fields"]) == 0


# ---------------------------------------------------------------------------
# Test 2: per-custom-format grouping
# ---------------------------------------------------------------------------


def test_changed_custom_format_groups_under_format_name() -> None:
    """A changed custom_format appears under its name; unchanged ones have empty change-sets."""
    before = deep_copy(BASE_CONFIG)
    after = deep_copy(BASE_CONFIG)

    # Change score on the custom format in sonarr.main
    after["sonarr"]["main"]["custom_formats"][0]["assign_scores_to"][0]["score"] = 200

    diff = configarr_diff(before, after)

    assert "sonarr.main" in diff
    sonarr_diff = diff["sonarr.main"]
    assert "custom_formats" in sonarr_diff
    cf_diff = sonarr_diff["custom_formats"]

    # The changed format should be present with changed_fields
    assert "fr-vff" in cf_diff, f"fr-vff not in custom_formats diff: {cf_diff}"
    frvff_diff = cf_diff["fr-vff"]
    assert "changed_fields" in frvff_diff
    assert len(frvff_diff["changed_fields"]) > 0


# ---------------------------------------------------------------------------
# Test 3: SC#4 — tag literals preserved in diff output
# ---------------------------------------------------------------------------


def test_sc4_tag_literals_preserved_not_resolved() -> None:
    """Diff runs on tag-literal data; !env SONARR_API_KEY is never resolved."""
    before = deep_copy(BASE_CONFIG)
    after = deep_copy(BASE_CONFIG)

    # Change a non-api_key field so we get a diff
    after["sonarr"]["main"]["quality_profiles"][0]["min_format_score"] = 999

    diff = configarr_diff(before, after)

    # Serialise the whole diff to a string and check for bad patterns
    import json

    diff_str = json.dumps(diff)

    # Must NOT contain the resolved env var name without the "!env" prefix
    # (i.e., bare "SONARR_API_KEY" would be the leaked version)
    # The diff is computed on tag-literal data, so api_key values
    # should never appear as "SONARR_API_KEY" (without "!env ") in the output.
    assert "SONARR_API_KEY" not in diff_str or "!env SONARR_API_KEY" in diff_str, (
        "api_key appears to have been resolved/stripped of !env prefix in diff"
    )
    assert "RADARR_API_KEY" not in diff_str or "!env RADARR_API_KEY" in diff_str


def test_sc4_api_key_literal_appears_in_diff_when_changed() -> None:
    """If api_key field changed, it shows as the literal '!env ...' string, never bare."""
    before = deep_copy(BASE_CONFIG)
    after = deep_copy(BASE_CONFIG)

    # Simulate an api_key value change (still a tag-literal string)
    after["sonarr"]["main"]["api_key"] = "!env NEW_SONARR_API_KEY"

    diff = configarr_diff(before, after)

    import json

    diff_str = json.dumps(diff)
    # If api_key appears in the diff, it must be as a tag-literal, not bare
    if "NEW_SONARR_API_KEY" in diff_str:
        assert "!env NEW_SONARR_API_KEY" in diff_str, (
            "api_key changed_field surfaced bare var name instead of !env literal"
        )


# ---------------------------------------------------------------------------
# Test 4: has_changes
# ---------------------------------------------------------------------------


def test_has_changes_returns_false_when_identical() -> None:
    """has_changes returns False when before == after."""
    config = deep_copy(BASE_CONFIG)
    diff = configarr_diff(config, config)
    assert has_changes(diff) is False


def test_has_changes_returns_true_when_any_leaf_differs() -> None:
    """has_changes returns True when any leaf value changed."""
    before = deep_copy(BASE_CONFIG)
    after = deep_copy(BASE_CONFIG)
    after["sonarr"]["main"]["quality_profiles"][0]["min_format_score"] = 999

    diff = configarr_diff(before, after)
    assert has_changes(diff) is True


def test_has_changes_returns_true_for_top_level_scalar_change() -> None:
    """has_changes returns True for trashGuideUrl change."""
    before = deep_copy(BASE_CONFIG)
    after = deep_copy(BASE_CONFIG)
    after["trashGuideUrl"] = "https://github.com/TRaSH-Guides/Other"

    diff = configarr_diff(before, after)
    assert has_changes(diff) is True


# ---------------------------------------------------------------------------
# Test 5: empty change-sets still present (predictable shape)
# ---------------------------------------------------------------------------


def test_unchanged_sections_present_with_empty_changesets() -> None:
    """Sections with zero changes are STILL present — frontend hides them."""
    config = deep_copy(BASE_CONFIG)
    diff = configarr_diff(config, config)

    # Top-level sections always present
    assert "sonarr.main" in diff
    assert "radarr.main" in diff

    sonarr_diff = diff["sonarr.main"]
    assert "quality_profiles" in sonarr_diff

    # All profiles present with empty changed_fields
    for profile_name, profile_diff in sonarr_diff["quality_profiles"].items():
        assert "changed_fields" in profile_diff, f"profile {profile_name} missing changed_fields"
        assert profile_diff["changed_fields"] == []


# ---------------------------------------------------------------------------
# Acceptance criteria checks (D-05 boundary — no arrconf diff code reused)
# ---------------------------------------------------------------------------


def test_d05_no_app_sections_import() -> None:
    """Acceptance: configarr_diff.py must not reference APP_SECTIONS or categories."""
    import inspect

    import arrconf_ui.configarr_diff as mod

    src = inspect.getsource(mod)
    assert "APP_SECTIONS" not in src, "configarr_diff.py must not reference APP_SECTIONS (D-05)"
    assert (
        "from arrconf_ui.diff" not in src and "import diff" not in src
    ), "configarr_diff.py must not import from arrconf_ui.diff (D-05)"


def test_sc4_no_env_resolution_in_module() -> None:
    """Acceptance: configarr_diff.py must not use os.environ, getenv, or model_dump."""
    import inspect

    import arrconf_ui.configarr_diff as mod

    src = inspect.getsource(mod)
    assert "os.environ" not in src, "configarr_diff must not access os.environ (SC#4)"
    assert "getenv" not in src, "configarr_diff must not call getenv (SC#4)"
    assert "model_dump" not in src, "configarr_diff must not call model_dump (SC#4 — would drop !env tag)"
