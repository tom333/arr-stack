"""CFGUI-07 CI gate: pydantic validation of the real committed configarr.yml.

D-08 RESOLVED — Option C (pydantic-only gate, user-acknowledged 2026-05-29):
  configarr v1.28.0 has NO offline validate mode (see 25-RESEARCH.md BLOCKER block);
  the project does NOT spin up *arr containers and does NOT invoke configarr in CI.
  ConfigarrRootConfig.model_validate IS the authoritative structural gate.

This test runs inside the existing ``arrconf-ui-backend`` ``uv run pytest -q``
step — no new CI runner is needed for the validation itself.
Task 2 of plan 25-04 separately adds a schema-reproducibility step
(``python -m arrconf_ui.configarr_schema_gen`` + ``git diff --exit-code``) to
the same CI job.

IMPORTANT: Do NOT add configarr-tool or *arr-container invocation to this file
(D-08 Option C). This test MUST remain pure pydantic.
"""

from __future__ import annotations

from arrconf_ui.configarr_config import ConfigarrRootConfig
from arrconf_ui.configarr_io import _tagged_to_literal
from arrconf_ui.io import read_yaml
from arrconf_ui.locator import configarr_yml_path

# ---------------------------------------------------------------------------
# Test 1 (CFGUI-07 authoritative gate): real file validates against the model
# ---------------------------------------------------------------------------


def test_real_configarr_yml_validates() -> None:
    """ConfigarrRootConfig.model_validate against the REAL committed configarr.yml
    must succeed (CFGUI-07 authority).

    This validates the file that ships in-cluster via the configarr CronJob.
    If a hand-edit introduces an unmodeled key or shape error, ``extra='forbid'``
    makes this test fail in CI before the bad config reaches the cluster.

    Uses ``configarr_yml_path()`` directly — no monkeypatch — so it always
    validates the REAL committed file.
    """
    raw = read_yaml(configarr_yml_path())
    data = _tagged_to_literal(raw)
    config = ConfigarrRootConfig.model_validate(data)

    # Shape: both sonarr and radarr instances present
    assert "main" in config.sonarr, "sonarr.main block must be present"
    assert "main" in config.radarr, "radarr.main block must be present"

    # Structural correctness: at least one quality profile per instance
    assert len(config.sonarr["main"].quality_profiles) > 0, (
        "sonarr.main must have at least one quality profile"
    )
    assert len(config.radarr["main"].quality_profiles) > 0, (
        "radarr.main must have at least one quality profile"
    )


# ---------------------------------------------------------------------------
# Test 2: tag-literal data retains !env references in the validated input
# ---------------------------------------------------------------------------


def test_env_tags_survive_into_gate() -> None:
    """The validated input dict carries !env SONARR_API_KEY and !env RADARR_API_KEY
    as literal strings (sanity that the gate runs on tag-literal data, not
    stripped data where tag markers were silently lost — SC#4 / D-04).

    If this fails, _tagged_to_literal is broken and the gate is validating
    a corrupt input where secret variable names were dropped.
    """
    raw = read_yaml(configarr_yml_path())
    data = _tagged_to_literal(raw)

    sonarr_api_key = data["sonarr"]["main"]["api_key"]
    radarr_api_key = data["radarr"]["main"]["api_key"]

    assert sonarr_api_key == "!env SONARR_API_KEY", (
        f"Expected '!env SONARR_API_KEY', got {sonarr_api_key!r} — "
        "tag dropped by _tagged_to_literal (SC#4 regression)"
    )
    assert radarr_api_key == "!env RADARR_API_KEY", (
        f"Expected '!env RADARR_API_KEY', got {radarr_api_key!r} — "
        "tag dropped by _tagged_to_literal (SC#4 regression)"
    )
