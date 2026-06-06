"""Unit tests for generators/configarr.py (Phase 33 / CFGARR-01..04).

Tests:
- test_header_present: output starts with the GENERATED header line.
- test_quality_profiles_routed_by_kind: sonarr gets only kind=series profiles,
  radarr gets only kind=movies profiles (D-33-05 no dead profiles).
- test_profile_name_mapping: category profile=general → QP named "MULTi.VF" (D-33-04).
- test_vostfr_scores_per_profile: VOSTFR scores MULTi.VF=-10000, Anime=50, Family=-10000.
- test_api_key_is_env_tag_not_secret: api_key emitted as bare !env tag (CFGARR-03 / T-33-01).
- test_deterministic: identical calls produce identical strings.
- test_no_api_calls_adr5: source has no httpx/ArrApiClient/reconcile + runtime
  monkeypatch confirms no HTTP path exercised (CFGARR-04 / ADR-5).
"""

from __future__ import annotations

from typing import Any

import pytest

from arrconf.generators.configarr import generate_configarr_yml
from arrconf.intent_config import IntentConfig

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_QP_BODY: dict[str, Any] = {
    "language": "Any",
    "reset_unmatched_scores": {"enabled": True},
    "upgrade": {
        "allowed": True,
        "until_quality": "Bluray-1080p",
        "until_score": 2000,
        "min_format_score": 50,
    },
    "min_format_score": 0,
    "quality_sort": "top",
    "qualities": [
        {"name": "Bluray-1080p"},
        {"name": "WEB 1080p", "qualities": ["WEBDL-1080p", "WEBRip-1080p"]},
        {"name": "HDTV-1080p"},
    ],
}

_VOSTFR_CF_REFS: list[dict[str, Any]] = [
    {"trash_ids": ["fr-vostfr"], "score": -10000},  # MULTi.VF
]
_VOSTFR_CF_REFS_ANIME: list[dict[str, Any]] = [
    {"trash_ids": ["fr-vostfr"], "score": 50},  # Anime
]
_VOSTFR_CF_REFS_FAMILY: list[dict[str, Any]] = [
    {"trash_ids": ["fr-vostfr"], "score": -10000},  # Family
]


def _make_full_cfg() -> IntentConfig:
    """Build a representative IntentConfig with 3 series + 3 movie categories."""
    return IntentConfig.model_validate(
        {
            "categories": [
                {
                    "name": "series",
                    "kind": "series",
                    "profile": "general",
                    "display": "S",
                    "base_path": "/media/series",
                },
                {
                    "name": "series-zoe",
                    "kind": "series",
                    "profile": "anime",
                    "display": "Z",
                    "base_path": "/media/series-zoe",
                },
                {
                    "name": "series-garcons",
                    "kind": "series",
                    "profile": "family",
                    "display": "G",
                    "base_path": "/media/series-garcons",
                },
                {
                    "name": "films",
                    "kind": "movies",
                    "profile": "general",
                    "display": "F",
                    "base_path": "/media/films",
                },
                {
                    "name": "films-zoe",
                    "kind": "movies",
                    "profile": "anime",
                    "display": "Z",
                    "base_path": "/media/films-zoe",
                },
                {
                    "name": "films-enfants",
                    "kind": "movies",
                    "profile": "family",
                    "display": "E",
                    "base_path": "/media/films-enfants",
                },
            ],
            "profile_definitions": {
                "MULTi.VF": {
                    "body": _QP_BODY,
                    "custom_formats": _VOSTFR_CF_REFS,
                },
                "Anime": {
                    "body": _QP_BODY,
                    "custom_formats": _VOSTFR_CF_REFS_ANIME,
                },
                "Family": {
                    "body": _QP_BODY,
                    "custom_formats": _VOSTFR_CF_REFS_FAMILY,
                },
            },
            "configarr": {
                "trashGuideUrl": "https://github.com/TRaSH-Guides/Guides",
                "sonarr": {
                    "main": {
                        "base_url": "http://sonarr.selfhost.svc.cluster.local:8989",
                        "api_key": "!env SONARR_API_KEY",
                    }
                },
                "radarr": {
                    "main": {
                        "base_url": "http://radarr.selfhost.svc.cluster.local:7878",
                        "api_key": "!env RADARR_API_KEY",
                    }
                },
            },
        }
    )


def _parse_generated(content: str) -> dict[str, Any]:
    """Parse a generated configarr.yml string (handles bare !env tags)."""
    from ruyaml import YAML

    y = YAML()

    def env_constructor(loader: Any, node: Any) -> str:
        return f"!env {loader.construct_scalar(node)}"

    y.constructor.add_constructor("!env", env_constructor)

    import io

    return y.load(io.StringIO(content))  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_header_present() -> None:
    """Output must start with the GENERATED header (CI drift-guard anchor)."""
    cfg = _make_full_cfg()
    out = generate_configarr_yml(cfg)
    assert out.startswith(
        "# GENERATED by 'arrconf generate' from intent.yml — DO NOT EDIT BY HAND\n"
    ), f"GENERATED header missing; output starts with: {out[:120]!r}"


def test_quality_profiles_routed_by_kind() -> None:
    """D-33-05: sonarr only sees series profiles; radarr only movie profiles.

    Build a config where kind=series uses {general, anime} and kind=movies
    uses only {general}. Assert Anime never appears in radarr (no dead profile).
    """
    cfg = IntentConfig.model_validate(
        {
            "categories": [
                {
                    "name": "series",
                    "kind": "series",
                    "profile": "general",
                    "display": "S",
                    "base_path": "/media/series",
                },
                {
                    "name": "series-zoe",
                    "kind": "series",
                    "profile": "anime",
                    "display": "Z",
                    "base_path": "/media/series-zoe",
                },
                {
                    "name": "films",
                    "kind": "movies",
                    "profile": "general",
                    "display": "F",
                    "base_path": "/media/films",
                },
            ],
            "profile_definitions": {
                "MULTi.VF": {"body": {"language": "Any"}, "custom_formats": []},
                "Anime": {"body": {"language": "Any"}, "custom_formats": []},
            },
            "configarr": {
                "sonarr": {"main": {"api_key": "!env SONARR_API_KEY"}},
                "radarr": {"main": {"api_key": "!env RADARR_API_KEY"}},
            },
        }
    )
    out = generate_configarr_yml(cfg)
    doc = _parse_generated(out)

    sonarr_names = sorted(p["name"] for p in doc["sonarr"]["main"]["quality_profiles"])
    radarr_names = sorted(p["name"] for p in doc["radarr"]["main"]["quality_profiles"])

    assert sonarr_names == ["Anime", "MULTi.VF"], (
        f"sonarr quality_profiles mismatch: {sonarr_names}"
    )
    assert radarr_names == ["MULTi.VF"], (
        f"radarr quality_profiles should be [MULTi.VF] only, got: {radarr_names}"
    )
    assert "Anime" not in radarr_names, "D-33-05: dead Anime profile emitted in radarr"


def test_profile_name_mapping() -> None:
    """D-33-04 Option B: category profile=general → QP name "MULTi.VF"."""
    cfg = IntentConfig.model_validate(
        {
            "categories": [
                {
                    "name": "series",
                    "kind": "series",
                    "profile": "general",
                    "display": "S",
                    "base_path": "/media/series",
                }
            ],
            "profile_definitions": {
                "MULTi.VF": {"body": {"language": "Any"}, "custom_formats": []},
            },
            "configarr": {
                "sonarr": {"main": {"api_key": "!env SONARR_API_KEY"}},
            },
        }
    )
    out = generate_configarr_yml(cfg)
    doc = _parse_generated(out)

    sonarr_names = [p["name"] for p in doc["sonarr"]["main"]["quality_profiles"]]
    assert "MULTi.VF" in sonarr_names, (
        f"D-33-04: category profile=general did not map to MULTi.VF; got {sonarr_names}"
    )


def test_vostfr_scores_per_profile() -> None:
    """CFGARR-02: VOSTFR CF emits MULTi.VF=-10000, Anime=+50, Family=-10000."""
    cfg = _make_full_cfg()
    out = generate_configarr_yml(cfg)
    doc = _parse_generated(out)

    for instance in ("sonarr", "radarr"):
        custom_formats = doc[instance]["main"]["custom_formats"]
        vostfr = next(
            (cf for cf in custom_formats if "fr-vostfr" in cf.get("trash_ids", [])),
            None,
        )
        assert vostfr is not None, f"{instance}: no custom_format entry with fr-vostfr"

        scores_by_profile = {
            entry["name"]: entry.get("score") for entry in vostfr["assign_scores_to"]
        }
        assert scores_by_profile.get("MULTi.VF") == -10000, (
            f"{instance}: MULTi.VF VOSTFR score {scores_by_profile.get('MULTi.VF')!r} != -10000"
        )
        assert scores_by_profile.get("Anime") == 50, (
            f"{instance}: Anime VOSTFR score {scores_by_profile.get('Anime')!r} != 50"
        )
        assert scores_by_profile.get("Family") == -10000, (
            f"{instance}: Family VOSTFR score {scores_by_profile.get('Family')!r} != -10000"
        )


def test_api_key_is_env_tag_not_secret() -> None:
    """CFGARR-03 / T-33-01: api_key must be a bare !env tag, never a secret.

    Assert:
    - 'api_key: !env SONARR_API_KEY' (bare tag) is present.
    - Neither quoted form ('!env VAR' or "!env VAR") is present.
    - No literal secret value string leaks.
    """
    cfg = _make_full_cfg()
    out = generate_configarr_yml(cfg)

    assert "api_key: !env SONARR_API_KEY" in out, "SONARR_API_KEY not emitted as bare !env tag"
    assert "api_key: !env RADARR_API_KEY" in out, "RADARR_API_KEY not emitted as bare !env tag"

    # Neither single-quoted nor double-quoted form must appear.
    assert "'!env SONARR_API_KEY'" not in out, "SONARR_API_KEY still single-quoted in output"
    assert '"!env SONARR_API_KEY"' not in out, "SONARR_API_KEY still double-quoted in output"
    assert "'!env RADARR_API_KEY'" not in out, "RADARR_API_KEY still single-quoted in output"
    assert '"!env RADARR_API_KEY"' not in out, "RADARR_API_KEY still double-quoted in output"


def test_deterministic() -> None:
    """Same IntentConfig input must produce byte-identical output on every call."""
    cfg = _make_full_cfg()
    assert generate_configarr_yml(cfg) == generate_configarr_yml(cfg), (
        "generate_configarr_yml is not deterministic (same input produced different strings)"
    )


def test_no_api_calls_adr5(monkeypatch: pytest.MonkeyPatch) -> None:
    """CFGARR-04 / ADR-5: generator must never reach a live API.

    Source-level guard: inspect module source for forbidden imports.
    Runtime guard: monkeypatch httpx.Client to raise; call the generator;
    assert it still returns a string (proving no HTTP path is exercised).
    """
    import inspect

    import arrconf.generators.configarr as mod

    src = inspect.getsource(mod)

    # Check actual module imports/usage, not docstring text.
    # We verify the import list directly rather than scanning the full source string
    # (docstrings legitimately mention "No httpx, no ArrApiClient" as documentation).
    import re as _re

    assert not _re.search(r"^\s*import httpx\b", src, _re.MULTILINE), (
        "ADR-5 violation: 'import httpx' found in configarr.py imports"
    )
    assert not _re.search(r"^\s*from httpx\b", src, _re.MULTILINE), (
        "ADR-5 violation: 'from httpx' import found in configarr.py"
    )
    assert not _re.search(r"^\s*from arrconf\.client_base\b", src, _re.MULTILINE), (
        "ADR-5 violation: client_base import found in configarr.py"
    )
    assert not _re.search(r"^\s*from arrconf\.reconcilers\b", src, _re.MULTILINE), (
        "ADR-5 violation: reconcilers import found in configarr.py"
    )
    # ArrApiClient must not be instantiated or subclassed (not just mentioned in docs)
    assert not _re.search(r"\bArrApiClient\s*\(", src), (
        "ADR-5 violation: ArrApiClient instantiation found in configarr.py"
    )
    assert not _re.search(r"\(ArrApiClient\)", src), (
        "ADR-5 violation: ArrApiClient subclass found in configarr.py"
    )

    # Runtime guard: if any HTTP call were attempted, this would raise.
    try:
        import httpx

        def _raise(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("ADR-5 violation: HTTP call attempted during generate_configarr_yml")

        monkeypatch.setattr(httpx, "Client", _raise)
    except ImportError:
        pass  # httpx not available — still satisfied (source check above is the primary guard)

    cfg = _make_full_cfg()
    result = generate_configarr_yml(cfg)
    assert isinstance(result, str), "generate_configarr_yml did not return a string"
    assert result.startswith("# GENERATED"), "Expected GENERATED header in result"
