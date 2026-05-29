"""Tests for /api/configarr/* endpoints (CFGUI-01 / CFGUI-03 / SC#2 / SC#3 / D-09).

Covers:
- Test 1: SC#2 GET literal — api_key shows "!env SONARR_API_KEY" not bare var name
- Test 2: SC#2 GET literal — api_key shows "!env RADARR_API_KEY"
- Test 3: SC#2 PUT round-trip — file still has !env tags after write; diff returned
- Test 4: PUT invalid payload → 422, file byte-unchanged
- Test 5: D-09 rollback — tag-dropping write → 500 + file rolled back
- Test 6: POST /diff — stateless, file byte-unchanged
- Test 7: GET /schema — returns configarr-schema.json; 404 when missing
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

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
# Test 3: SC#2 PUT round-trip — tags survive, diff returned
# ---------------------------------------------------------------------------


def test_put_configarr_config_roundtrip_preserves_env_tags(
    client: TestClient,
    sandboxed_configarr_yml: Path,
) -> None:
    """PUT /api/configarr/config writes an editable field; !env tags remain; diff returned."""
    # GET current config
    current = client.get("/api/configarr/config").json()
    payload = json.loads(json.dumps(current))  # deep copy via JSON

    # Modify an editable field (trashGuideUrl)
    payload["trashGuideUrl"] = "https://github.com/TRaSH-Guides/Guides-modified"

    resp = client.put("/api/configarr/config", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Response contains diff and has_changes
    assert "diff" in body
    assert "has_changes" in body
    assert body["has_changes"] is True

    # File on disk still contains both !env tags (SC#2 / D-09)
    content = sandboxed_configarr_yml.read_text("utf-8")
    assert "!env SONARR_API_KEY" in content, (
        "!env SONARR_API_KEY tag missing from file after PUT — tag was dropped (D-09 violation)"
    )
    assert "!env RADARR_API_KEY" in content, (
        "!env RADARR_API_KEY tag missing from file after PUT — tag was dropped (D-09 violation)"
    )
    # The change was actually written
    assert "Guides-modified" in content


# ---------------------------------------------------------------------------
# Test 4: PUT invalid payload → 422, file byte-unchanged
# ---------------------------------------------------------------------------


def test_put_configarr_config_invalid_payload_returns_422_no_write(
    client: TestClient,
    sandboxed_configarr_yml: Path,
) -> None:
    """PUT with an unknown top key returns 422; on-disk file is byte-unchanged."""
    original_bytes = sandboxed_configarr_yml.read_bytes()

    # whisparr is out-of-scope (extra="forbid" on ConfigarrRootConfig rejects it)
    bad_payload: dict[str, Any] = {"whisparr": {}}

    resp = client.put("/api/configarr/config", json=bad_payload)
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert "detail" in body

    # File is byte-unchanged
    assert sandboxed_configarr_yml.read_bytes() == original_bytes, (
        "File was written despite 422 validation failure"
    )


# ---------------------------------------------------------------------------
# Test 5: D-09 rollback — tag-dropping write triggers 500 + rollback
# ---------------------------------------------------------------------------


def test_put_configarr_config_d09_rollback_on_tag_loss(
    client: TestClient,
    sandboxed_configarr_yml: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-09: if write_yaml_atomic drops an !env tag, endpoint returns 500 and rolls back."""
    original_bytes = sandboxed_configarr_yml.read_bytes()
    original_text = original_bytes.decode("utf-8")

    # Confirm original has both tags
    assert "!env SONARR_API_KEY" in original_text
    assert "!env RADARR_API_KEY" in original_text

    # Monkeypatch write_yaml_atomic in the app module to write content with !env stripped
    def write_drops_tags(path: Path, data: Any) -> None:
        # Write a version of the file with !env tags removed
        content = original_text.replace("!env SONARR_API_KEY", "SONARR_API_KEY_LEAKED")
        path.write_text(content, encoding="utf-8")

    monkeypatch.setattr("arrconf_ui.app.write_yaml_atomic", write_drops_tags, raising=False)
    monkeypatch.setattr("arrconf_ui.io.write_yaml_atomic", write_drops_tags)

    current = client.get("/api/configarr/config").json()
    payload = json.loads(json.dumps(current))
    payload["trashGuideUrl"] = "https://example.com"

    resp = client.put("/api/configarr/config", json=payload)
    assert resp.status_code == 500, (
        f"Expected 500 from D-09 anti-leak guard, got {resp.status_code}: {resp.text}"
    )
    assert "anti-leak" in resp.text.lower() or "tag" in resp.text.lower(), (
        f"Expected anti-leak error message, got: {resp.text}"
    )

    # File must be rolled back to original bytes
    after_bytes = sandboxed_configarr_yml.read_bytes()
    assert after_bytes == original_bytes, (
        "D-09 rollback failed: file was not restored to original bytes after tag loss"
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
