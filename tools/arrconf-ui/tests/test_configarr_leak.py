"""Task-zero anti-leak round-trip tests for configarr.yml (SC#1 / T-25-01 / T-25-02).

These tests ship in wave-1, BEFORE any write-path or endpoint code (Plans 03/04).
They form the regression net that ensures ``!env``/``!secret`` tags are never
silently stripped when configarr.yml is read → written back.

Threat coverage:
  T-25-01 — ``_tagged_to_literal`` must reconstruct ``"!env SONARR_API_KEY"``
             from TaggedScalar, never return the bare ``"SONARR_API_KEY"``
  T-25-02 — round-trip read→write→re-read must preserve both ``!env`` tags
             byte-for-byte in the output file
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from arrconf_ui.configarr_io import _tagged_to_literal
from arrconf_ui.io import read_yaml, write_yaml_atomic
from arrconf_ui.locator import configarr_yml_path

# ---------------------------------------------------------------------------
# Test 1 — Sonarr !env tag literal reconstruction
# ---------------------------------------------------------------------------


def test_tagged_to_literal_sonarr_api_key() -> None:
    """_tagged_to_literal on configarr.yml yields "!env SONARR_API_KEY", not bare key."""
    raw = read_yaml(configarr_yml_path())
    result = _tagged_to_literal(raw)
    sonarr_api_key = result["sonarr"]["main"]["api_key"]
    assert sonarr_api_key == "!env SONARR_API_KEY", (
        f"Expected '!env SONARR_API_KEY', got {sonarr_api_key!r}. "
        "The TaggedScalar was not reconstructed correctly."
    )


# ---------------------------------------------------------------------------
# Test 2 — Radarr !env tag literal reconstruction
# ---------------------------------------------------------------------------


def test_tagged_to_literal_radarr_api_key() -> None:
    """_tagged_to_literal on configarr.yml yields "!env RADARR_API_KEY", not bare key."""
    raw = read_yaml(configarr_yml_path())
    result = _tagged_to_literal(raw)
    radarr_api_key = result["radarr"]["main"]["api_key"]
    assert radarr_api_key == "!env RADARR_API_KEY", (
        f"Expected '!env RADARR_API_KEY', got {radarr_api_key!r}. "
        "The TaggedScalar was not reconstructed correctly."
    )


# ---------------------------------------------------------------------------
# Test 3 — Round-trip byte assertion (SC#1)
# ---------------------------------------------------------------------------


def test_roundtrip_preserves_env_tags_byte_for_byte(tmp_path: Path) -> None:
    """SC#1: read→write→re-read of configarr.yml contains both !env tags verbatim.

    This is the primary regression guard for T-25-02.  If io.py is ever changed
    to use a non-round-trip YAML type, this test will catch the regression.
    """
    src = configarr_yml_path()
    copy = tmp_path / "configarr.yml"
    shutil.copy(src, copy)

    data = read_yaml(copy)
    write_yaml_atomic(copy, data)

    output = copy.read_text(encoding="utf-8")
    assert "!env SONARR_API_KEY" in output, (
        "Round-trip lost '!env SONARR_API_KEY' — write_yaml_atomic stripped the tag."
    )
    assert "!env RADARR_API_KEY" in output, (
        "Round-trip lost '!env RADARR_API_KEY' — write_yaml_atomic stripped the tag."
    )


# ---------------------------------------------------------------------------
# Test 4 — Regression guard: JSON-coercion shortcut WOULD drop the tag (Pitfall 1)
# ---------------------------------------------------------------------------


def test_json_coercion_would_drop_env_tag() -> None:
    """Documents WHY json.dumps(default=str) must NOT be used (Pitfall 1 / SC#4).

    json.dumps with default=str calls str(TaggedScalar) which returns only
    .value — dropping the tag prefix.  This test proves the shortcut is broken
    and therefore the _tagged_to_literal helper is necessary.
    """
    raw = read_yaml(configarr_yml_path())
    # Simulate the naive coercion path that MUST NOT be used in configarr_io.py
    coerced = json.loads(json.dumps(raw["sonarr"]["main"]["api_key"], default=str))
    assert coerced == "SONARR_API_KEY", (
        f"Expected bare 'SONARR_API_KEY' from json coercion, got {coerced!r}. "
        "If this assertion fails, either the YAML type changed or ruyaml's "
        "TaggedScalar.__str__ behaviour changed — revisit Pitfall 1."
    )
    # Prove it is different from the safe literal
    assert coerced != "!env SONARR_API_KEY", (
        "json coercion unexpectedly preserved the tag — this contradicts Pitfall 1."
    )


# ---------------------------------------------------------------------------
# Test 5 — _tagged_to_literal passes through non-tagged scalars unchanged
# ---------------------------------------------------------------------------


def test_tagged_to_literal_leaves_plain_scalars_unchanged() -> None:
    """_tagged_to_literal recurses through nested dict+list; non-tagged values pass through."""
    raw = read_yaml(configarr_yml_path())
    result = _tagged_to_literal(raw)

    # base_url is a plain string — must not be altered
    sonarr_base_url = result["sonarr"]["main"]["base_url"]
    assert sonarr_base_url == "http://sonarr.selfhost.svc.cluster.local:8989"

    # The top-level structure is still a dict
    assert isinstance(result, dict)

    # Nested lists are preserved (e.g. quality_definition type is a plain string)
    quality_type = result["sonarr"]["main"]["quality_definition"]["type"]
    assert isinstance(quality_type, str)
    assert quality_type == "series"
