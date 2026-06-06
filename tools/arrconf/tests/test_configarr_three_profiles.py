"""Chart-side validation tests for charts/arr-stack/files/configarr.yml.

Phase 33 (hard cut): configarr.yml is now a GENERATED artifact produced by
'arrconf generate' from charts/arr-stack/files/intent.yml. Do NOT edit
configarr.yml by hand — edit intent.yml and re-run the generator.

These tests validate the GENERATED artifact has the expected 3-profile-per-instance
structure required by Phase 5, confirming the generator correctly emits the
declared profile_definitions + categories from intent.yml.

Plan 05-07 threat mitigations (still enforced on generated output):
- T-05-CONTENT: D-05-FAM-01 — Family is a byte-equivalent clone of MULTi.VF.
- D-05-CONFIGARR-01: 3 profiles per instance (MULTi.VF + Anime + Family).
- Q5 explicit-score syntax: VOSTFR has per-profile scores
  (MULTi.VF=-10000, Anime=+50, Family=-10000).
- R-06: no pre-existing Anime/Family profiles in cluster snapshots (guard test).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIGARR_YML = REPO_ROOT / "charts" / "arr-stack" / "files" / "configarr.yml"
SNAPSHOT_DIR = REPO_ROOT / "snapshots" / "before-phase-5-2026-05-14" / "sonarr"


def _load_configarr() -> dict[str, Any]:
    from ruyaml import YAML

    y = YAML()

    def env_constructor(loader: Any, node: Any) -> str:
        return loader.construct_scalar(node)

    y.constructor.add_constructor("!env", env_constructor)
    with CONFIGARR_YML.open("r", encoding="utf-8") as f:
        return y.load(f)  # type: ignore[return-value]


def test_three_profiles_per_instance() -> None:
    doc = _load_configarr()
    sonarr_profiles = [p["name"] for p in doc["sonarr"]["main"]["quality_profiles"]]
    radarr_profiles = [p["name"] for p in doc["radarr"]["main"]["quality_profiles"]]
    assert sorted(sonarr_profiles) == ["Anime", "Family", "MULTi.VF"], (
        f"sonarr quality_profiles mismatch: {sonarr_profiles}"
    )
    assert sorted(radarr_profiles) == ["Anime", "Family", "MULTi.VF"], (
        f"radarr quality_profiles mismatch: {radarr_profiles}"
    )


def test_family_clone_of_multivf() -> None:
    doc = _load_configarr()
    for app in ("sonarr", "radarr"):
        profiles = doc[app]["main"]["quality_profiles"]
        by_name = {p["name"]: p for p in profiles}
        assert "MULTi.VF" in by_name, f"{app}: MULTi.VF profile not found"
        assert "Family" in by_name, f"{app}: Family profile not found"
        # D-05-FAM-01: Family is a byte-equivalent clone of MULTi.VF (name excluded).
        multivf_dict = copy.deepcopy(by_name["MULTi.VF"])
        family_dict = copy.deepcopy(by_name["Family"])
        multivf_dict.pop("name")
        family_dict.pop("name")
        assert family_dict == multivf_dict, (
            f"{app}: Family profile is NOT a byte-equivalent clone of MULTi.VF.\n"
            f"MULTi.VF (minus name): {multivf_dict}\n"
            f"Family (minus name): {family_dict}"
        )


def test_vostfr_score_differs_per_profile() -> None:
    doc = _load_configarr()
    for app in ("sonarr", "radarr"):
        custom_formats = doc[app]["main"]["custom_formats"]
        vostfr_entry = next(
            (cf for cf in custom_formats if "fr-vostfr" in cf.get("trash_ids", [])),
            None,
        )
        assert vostfr_entry is not None, f"{app}: no custom_format entry with fr-vostfr"
        scores_by_profile = {
            entry["name"]: entry.get("score") for entry in vostfr_entry["assign_scores_to"]
        }
        assert "MULTi.VF" in scores_by_profile, f"{app}: MULTi.VF not in fr-vostfr assign_scores_to"
        assert "Anime" in scores_by_profile, f"{app}: Anime not in fr-vostfr assign_scores_to"
        assert "Family" in scores_by_profile, f"{app}: Family not in fr-vostfr assign_scores_to"
        assert scores_by_profile["MULTi.VF"] == -10000, (
            f"{app}: MULTi.VF VOSTFR score {scores_by_profile['MULTi.VF']!r} != -10000"
        )
        assert scores_by_profile["Anime"] == 50, (
            f"{app}: Anime VOSTFR score {scores_by_profile['Anime']!r} != 50"
        )
        assert scores_by_profile["Family"] == -10000, (
            f"{app}: Family VOSTFR score {scores_by_profile['Family']!r} != -10000"
        )


def test_no_quality_profile_named_anime_or_family_before_phase_5_baseline() -> None:
    qualityprofile_path = SNAPSHOT_DIR / "qualityprofile.json"
    if not qualityprofile_path.exists():
        pytest.skip(
            "TODO: snapshot before-phase-5-2026-05-14/sonarr/qualityprofile.json not found "
            "(Plan 01 snapshot did not capture qualityprofile.json). "
            "R-06 mitigation cannot be verified without baseline snapshot."
        )
    profiles = json.loads(qualityprofile_path.read_text(encoding="utf-8"))
    existing_names = {p["name"] for p in profiles}
    assert "Anime" not in existing_names, (
        "R-06: cluster ALREADY has a quality profile named 'Anime' — "
        "configarr will conflict on first sync. Resolve manually before applying."
    )
    assert "Family" not in existing_names, (
        "R-06: cluster ALREADY has a quality profile named 'Family' — "
        "configarr will conflict on first sync. Resolve manually before applying."
    )
