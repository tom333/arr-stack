"""FastAPI endpoint contracts — GET/POST on /api/* (D-02, D-34-04).

Note: PUT /api/config was removed in D-34-04. arrconf.yml is now 100% generated
from intent.yml. The intent endpoints (PUT /api/intent) replace the old PUT /api/config.
Tests for PUT /api/config removal live in test_intent_endpoints.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from arrconf_ui.app import create_app


@pytest.fixture
def client(sandboxed_arrconf_yml: Path, sandboxed_schema: Path) -> TestClient:
    """Fresh app instance with patched locators."""
    return TestClient(create_app())


def test_get_config_returns_200_with_top_level_keys(client: TestClient) -> None:
    """GET /api/config returns arrconf.yml content (now 100% generated, no categories)."""
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    # RootConfig keys present in generated arrconf.yml (Phase 32: categories moved to intent.yml)
    assert "sonarr" in body
    assert "radarr" in body
    assert "prowlarr" in body
    assert "qbittorrent" in body
    assert "seerr" in body
    assert "jellyfin" in body


def test_get_schema_returns_json_schema(client: TestClient) -> None:
    resp = client.get("/api/schema")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["$schema"].startswith("https://json-schema.org/draft/2020-12/")
    assert "RootConfig" in schema.get("title", "") or "$defs" in schema


def test_post_diff_does_not_write(client: TestClient, sandboxed_arrconf_yml: Path) -> None:
    """POST /api/diff is stateless -- MUST NOT write the file."""
    original = sandboxed_arrconf_yml.read_text(encoding="utf-8")
    current = client.get("/api/config").json()
    # Modify a field that exists in generated arrconf.yml (sonarr base_url)
    current["sonarr"]["main"]["base_url"] = "http://sonarr-modified.example.com:8989"
    resp = client.post("/api/diff", json=current)
    assert resp.status_code == 200
    body = resp.json()
    assert "diff" in body
    assert "has_changes" in body
    # File NOT modified.
    assert sandboxed_arrconf_yml.read_text(encoding="utf-8") == original
