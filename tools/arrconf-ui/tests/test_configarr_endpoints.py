"""Tests for /api/configarr/* endpoints (CFGUI-01 / CFGUI-03 / SC#2 / SC#3 / D-09).

Note: PUT /api/configarr/config was removed in D-34-04. configarr.yml is now 100%
generated from intent.yml. Tests 3-5 (PUT round-trip, PUT invalid, D-09 rollback)
are removed because the endpoint no longer exists.

Remaining tests:
- Test 1: SC#2 GET literal — api_key shows "!env SONARR_API_KEY" not bare var name
- Test 2: SC#2 GET literal — api_key shows "!env RADARR_API_KEY"
- Test 6: POST /diff — stateless, file byte-unchanged
- Test 7: GET /schema — returns configarr-schema.json; 404 when missing
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from arrconf_ui.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_SCHEMA = REPO_ROOT / "schemas" / "configarr-schema.json"


@pytest.fixture
def sandboxed_configarr_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copy the committed configarr-schema.json to tmp_path; patch locator."""
    target = tmp_path / "configarr-schema.json"
    shutil.copy(CANONICAL_SCHEMA, target)

    def fake_schema_path() -> Path:
        return target

    monkeypatch.setattr("arrconf_ui.locator.configarr_schema_json_path", fake_schema_path)
    monkeypatch.setattr(
        "arrconf_ui.app.configarr_schema_json_path", fake_schema_path, raising=False
    )
    return target


@pytest.fixture
def client(
    sandboxed_configarr_yml: Path,
    sandboxed_configarr_schema: Path,
) -> TestClient:
    """Fresh app instance with sandboxed configarr paths."""
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# Test 1: SC#2 GET literal — sonarr api_key
# ---------------------------------------------------------------------------


def test_get_configarr_config_sonarr_api_key_is_literal(client: TestClient) -> None:
    """GET /api/configarr/config must return api_key as '!env SONARR_API_KEY' literal."""
    resp = client.get("/api/configarr/config")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "sonarr" in body, f"sonarr not in response: {list(body.keys())}"
    assert "main" in body["sonarr"], f"main not in sonarr: {list(body['sonarr'].keys())}"
    api_key = body["sonarr"]["main"]["api_key"]
    assert api_key == "!env SONARR_API_KEY", (
        f"api_key must be '!env SONARR_API_KEY' literal, got: {api_key!r} (Pitfall 1 regression)"
    )


# ---------------------------------------------------------------------------
# Test 2: SC#2 GET literal — radarr api_key
# ---------------------------------------------------------------------------


def test_get_configarr_config_radarr_api_key_is_literal(client: TestClient) -> None:
    """GET /api/configarr/config must return radarr api_key as '!env RADARR_API_KEY' literal."""
    resp = client.get("/api/configarr/config")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "radarr" in body
    assert "main" in body["radarr"]
    api_key = body["radarr"]["main"]["api_key"]
    assert api_key == "!env RADARR_API_KEY", (
        f"api_key must be '!env RADARR_API_KEY' literal, got: {api_key!r} (Pitfall 1 regression)"
    )


# ---------------------------------------------------------------------------
# Test 6: POST /diff — stateless, file byte-unchanged
# ---------------------------------------------------------------------------


def test_post_configarr_diff_is_stateless(
    client: TestClient,
    sandboxed_configarr_yml: Path,
) -> None:
    """POST /api/configarr/diff returns a diff and does NOT write the file."""
    original = sandboxed_configarr_yml.read_bytes()

    current = client.get("/api/configarr/config").json()
    payload = json.loads(json.dumps(current))
    payload["trashGuideUrl"] = "https://preview-only.example.com"

    resp = client.post("/api/configarr/diff", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "diff" in body
    assert "has_changes" in body
    assert body["has_changes"] is True

    # File must NOT be modified
    assert sandboxed_configarr_yml.read_bytes() == original, (
        "POST /api/configarr/diff must NOT write the file (stateless)"
    )


# ---------------------------------------------------------------------------
# Test 7a: GET /schema returns the committed configarr-schema.json
# ---------------------------------------------------------------------------


def test_get_configarr_schema_returns_json_schema(
    client: TestClient,
    sandboxed_configarr_schema: Path,
) -> None:
    """GET /api/configarr/schema returns the committed configarr-schema.json."""
    resp = client.get("/api/configarr/schema")
    assert resp.status_code == 200, resp.text
    schema = resp.json()
    assert "$schema" in schema
    assert schema["$schema"].startswith("https://json-schema.org/draft/2020-12/")
    # Should have ConfigarrRootConfig as title or in $defs
    assert "ConfigarrRootConfig" in schema.get("title", "") or "$defs" in schema


# ---------------------------------------------------------------------------
# Test 7b: GET /schema → 404 when schema file is missing
# ---------------------------------------------------------------------------


def test_get_configarr_schema_404_when_missing(
    sandboxed_configarr_yml: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """GET /api/configarr/schema returns 404 when the schema file does not exist."""
    missing_path = tmp_path / "nonexistent-configarr-schema.json"

    def fake_schema_path() -> Path:
        return missing_path

    monkeypatch.setattr("arrconf_ui.locator.configarr_schema_json_path", fake_schema_path)
    monkeypatch.setattr(
        "arrconf_ui.app.configarr_schema_json_path", fake_schema_path, raising=False
    )

    client = TestClient(create_app())
    resp = client.get("/api/configarr/schema")
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
