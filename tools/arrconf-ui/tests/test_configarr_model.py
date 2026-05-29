"""Tests for ConfigarrRootConfig pydantic model (CFGUI-02).

6 behavior tests (plan 25-02, Task 1):
  1. Real-file validation — model_validate against the real configarr.yml succeeds.
  2. extra='forbid' rejects unmodeled top key (whisparr).
  3. extra='forbid' rejects unmodeled per-instance key (delete_unmanaged_custom_formats).
  4. upgrade conditional-required (allowed=true without until_quality/until_score → error).
  5. specifications polymorphism (fields.value = str OR int both validate).
  6. MediaNaming one-type (sonarr keys AND radarr keys both validate).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from ruyaml.comments import TaggedScalar

from arrconf_ui.configarr_config import (
    ConfigarrRootConfig,
    CustomFormatDefinition,
    MediaNaming,
)

# ---------------------------------------------------------------------------
# Local helper — mirrors Plan 01's _tagged_to_literal from configarr_io.py.
# Used here so this test module is self-contained for wave-1 parallel execution.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIGARR_YML = REPO_ROOT / "charts" / "arr-stack" / "files" / "configarr.yml"


def _tagged_to_literal(node: Any) -> Any:
    """Convert ruyaml CommentedMap to a JSON-safe dict preserving !env/!secret tags."""
    if isinstance(node, TaggedScalar):
        return f"{node.tag.value} {node.value}"
    if isinstance(node, dict):
        return {k: _tagged_to_literal(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_tagged_to_literal(v) for v in node]
    return node


def _read_configarr_yml() -> Any:
    """Read the real configarr.yml via ruyaml round-trip and convert to tag-literals."""
    from arrconf_ui.io import read_yaml

    raw = read_yaml(CONFIGARR_YML)
    return _tagged_to_literal(raw)


# ---------------------------------------------------------------------------
# Test 1: Real-file validation
# ---------------------------------------------------------------------------


def test_real_file_validates() -> None:
    """ConfigarrRootConfig.model_validate against the real configarr.yml must succeed."""
    data = _read_configarr_yml()
    config = ConfigarrRootConfig.model_validate(data)
    # Basic shape assertions
    assert "main" in config.sonarr
    assert "main" in config.radarr
    assert config.sonarr["main"].base_url == "http://sonarr.selfhost.svc.cluster.local:8989"
    # api_key holds the !env literal (tag-preserved)
    assert config.sonarr["main"].api_key == "!env SONARR_API_KEY"
    assert config.radarr["main"].api_key == "!env RADARR_API_KEY"
    # customFormatDefinitions present
    assert len(config.customFormatDefinitions) > 0


# ---------------------------------------------------------------------------
# Test 2: extra='forbid' rejects unmodeled top key
# ---------------------------------------------------------------------------


def test_extra_forbid_top_key_whisparr() -> None:
    """Payload with whisparr: {} must raise ValidationError (out-of-scope *arr)."""
    payload: dict[str, Any] = {
        "sonarr": {},
        "radarr": {},
        "whisparr": {},  # unmodeled — should be rejected
    }
    with pytest.raises(ValidationError):
        ConfigarrRootConfig.model_validate(payload)


# ---------------------------------------------------------------------------
# Test 3: extra='forbid' rejects unmodeled per-instance key
# ---------------------------------------------------------------------------


def test_extra_forbid_per_instance_key() -> None:
    """sonarr.main with delete_unmanaged_custom_formats must raise ValidationError."""
    payload: dict[str, Any] = {
        "sonarr": {
            "main": {
                "base_url": "http://sonarr:8989",
                "api_key": "!env SONARR_API_KEY",
                "delete_unmanaged_custom_formats": True,  # unmodeled — should be rejected
                "quality_profiles": [],
            }
        },
        "radarr": {},
    }
    with pytest.raises(ValidationError):
        ConfigarrRootConfig.model_validate(payload)


# ---------------------------------------------------------------------------
# Test 4: upgrade conditional-required (Pitfall 3)
# ---------------------------------------------------------------------------


def test_upgrade_allowed_true_requires_until_fields() -> None:
    """upgrade.allowed=true WITHOUT until_quality/until_score must raise ValidationError."""
    payload: dict[str, Any] = {
        "sonarr": {
            "main": {
                "base_url": "http://sonarr:8989",
                "api_key": "!env SONARR_API_KEY",
                "quality_profiles": [
                    {
                        "name": "TestProfile",
                        "upgrade": {
                            "allowed": True,
                            # until_quality and until_score intentionally MISSING
                        },
                    }
                ],
            }
        },
        "radarr": {},
    }
    with pytest.raises(ValidationError):
        ConfigarrRootConfig.model_validate(payload)


def test_upgrade_allowed_false_validates_without_until_fields() -> None:
    """upgrade.allowed=false without until_quality/until_score must validate OK."""
    payload: dict[str, Any] = {
        "sonarr": {
            "main": {
                "base_url": "http://sonarr:8989",
                "api_key": "!env SONARR_API_KEY",
                "quality_profiles": [
                    {
                        "name": "TestProfile",
                        "upgrade": {
                            "allowed": False,
                            # no until_quality / until_score — acceptable when allowed=False
                        },
                    }
                ],
            }
        },
        "radarr": {},
    }
    config = ConfigarrRootConfig.model_validate(payload)
    profile = config.sonarr["main"].quality_profiles[0]
    assert profile.upgrade is not None
    assert profile.upgrade.allowed is False


# ---------------------------------------------------------------------------
# Test 5: specifications polymorphism (Pitfall 4)
# ---------------------------------------------------------------------------


def test_specifications_fields_polymorphism() -> None:
    """specifications[].fields.value = str OR int both validate (Pitfall 4)."""
    cf_def: dict[str, Any] = {
        "trash_id": "fr-x265-hd",
        "name": "x265 / HEVC (HD)",
        "specifications": [
            {
                "name": "regex spec",
                "implementation": "ReleaseTitleSpecification",
                "fields": {
                    "value": "\\b(x265|hevc)\\b"  # str value
                },
            },
            {
                "name": "resolution spec",
                "implementation": "ResolutionSpecification",
                "negate": True,
                "required": True,
                "fields": {
                    "value": 2160  # int value — must NOT fail
                },
            },
        ],
    }
    validated = CustomFormatDefinition.model_validate(cf_def)
    assert validated.specifications[0].fields["value"] == "\\b(x265|hevc)\\b"
    assert validated.specifications[1].fields["value"] == 2160


# ---------------------------------------------------------------------------
# Test 6: MediaNaming one-type with sonarr AND radarr keys (Pitfall 5)
# ---------------------------------------------------------------------------


def test_media_naming_accepts_sonarr_keys() -> None:
    """MediaNaming with sonarr keys (series/season/episodes) must validate."""
    naming = MediaNaming.model_validate(
        {
            "series": "default",
            "season": "default",
            "episodes": {
                "rename": True,
                "standard": "default",
                "daily": "default",
                "anime": "default",
            },
        }
    )
    assert naming.series == "default"
    assert naming.episodes is not None
    assert naming.episodes.rename is True


def test_media_naming_accepts_radarr_keys() -> None:
    """MediaNaming with radarr keys (folder/movie) must validate."""
    naming = MediaNaming.model_validate(
        {
            "folder": "default",
            "movie": {
                "rename": True,
                "standard": "default",
            },
        }
    )
    assert naming.folder == "default"
    assert naming.movie is not None
    assert naming.movie.rename is True
