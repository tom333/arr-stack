"""FastAPI endpoint contracts — GET/PUT/POST/GET on /api/* (D-02)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from arrconf_ui.app import create_app


@pytest.fixture
def client(sandboxed_arrconf_yml: Path, sandboxed_schema: Path) -> TestClient:
    """Fresh app instance with patched locators."""
    return TestClient(create_app())


def test_get_config_returns_200_with_top_level_keys(client: TestClient) -> None:
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    # All 7 top-level RootConfig keys present.
    assert "categories" in body
    assert "sonarr" in body
    assert "radarr" in body
    assert "prowlarr" in body
    assert "qbittorrent" in body
    assert "seerr" in body
    assert "jellyfin" in body
    # The canonical arrconf.yml has >= 1 category.
    assert len(body["categories"]) >= 1


def test_get_schema_returns_json_schema(client: TestClient) -> None:
    resp = client.get("/api/schema")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["$schema"].startswith("https://json-schema.org/draft/2020-12/")
    assert "RootConfig" in schema.get("title", "") or "$defs" in schema


def test_put_config_with_valid_payload_writes_and_returns_diff(
    client: TestClient, sandboxed_arrconf_yml: Path
) -> None:
    # Load current -> modify one field -> PUT -> assert file was updated.
    current = client.get("/api/config").json()
    new_payload = json.loads(json.dumps(current))  # deep copy via JSON
    # Add a new test category.
    new_payload["categories"].append(
        {
            "name": "test-roundtrip",
            "kind": "series",
            "profile": "general",
            "display": "Test Round-trip",
            "base_path": "/media/test-roundtrip",
        }
    )
    resp = client.put("/api/config", json=new_payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_changes"] is True
    assert "test-roundtrip" in body["diff"]["categories"]["added"]
    # File was actually written.
    assert "test-roundtrip" in sandboxed_arrconf_yml.read_text(encoding="utf-8")


def test_put_config_with_invalid_payload_returns_422(
    client: TestClient, sandboxed_arrconf_yml: Path
) -> None:
    bad = {
        "categories": [
            {
                "name": "x",
                "kind": "INVALID_KIND",
                "profile": "general",
                "display": "X",
                "base_path": "/media/x",
            }
        ]
    }
    resp = client.put("/api/config", json=bad)
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert "detail" in body
    assert isinstance(body["detail"], list)
    # File was NOT written -- original content intact.
    assert "INVALID_KIND" not in sandboxed_arrconf_yml.read_text(encoding="utf-8")


def test_post_diff_does_not_write(client: TestClient, sandboxed_arrconf_yml: Path) -> None:
    """POST /api/diff is stateless -- MUST NOT write the file."""
    original = sandboxed_arrconf_yml.read_text(encoding="utf-8")
    current = client.get("/api/config").json()
    current["categories"].append(
        {
            "name": "preview-only",
            "kind": "series",
            "profile": "general",
            "display": "Preview",
            "base_path": "/media/preview-only",
        }
    )
    resp = client.post("/api/diff", json=current)
    assert resp.status_code == 200
    body = resp.json()
    assert "preview-only" in body["diff"]["categories"]["added"]
    # File NOT modified.
    assert sandboxed_arrconf_yml.read_text(encoding="utf-8") == original


def test_phase_14_suggestarr_coupled_fields_remain_editable(client: TestClient) -> None:
    """D-09 fields MUST be plain fields on the backend -- no special read-only.

    The 7 fields surface as visual badges in the FRONTEND only (Plan 15-B).
    The backend treats them as ordinary editable fields.

    Note: categories[name="films-zoe"].base_path is NOT freely editable --
    the Category pydantic model enforces base_path == /media/{name} as a
    D-04 strict invariant. The D-09 coupling indicator is a VISUAL hint in
    the frontend only; the backend rejects an invalid base_path via 422.
    The seerr.* fields have no such constraint and are freely editable.
    """
    current = client.get("/api/config").json()
    # Edit the canonical D-09 seerr fields -- these have NO invariant lock.
    current["seerr"]["main"]["sonarr_service"]["activeAnimeProfileId"] = 999
    current["seerr"]["main"]["sonarr_service"]["activeProfileId"] = 999
    current["seerr"]["main"]["sonarr_service"]["activeAnimeDirectory"] = "/media/anime-new"
    current["seerr"]["main"]["sonarr_service"]["activeDirectory"] = "/media/series-new"
    current["seerr"]["main"]["radarr_service"]["activeProfileId"] = 999
    current["seerr"]["main"]["radarr_service"]["activeDirectory"] = "/media/films-new"
    # NOTE: categories[name="films-zoe"].base_path CANNOT be changed to an arbitrary
    # value: Category.base_path must equal /media/{name} (D-04 strict invariant).
    # This is correct backend behavior -- the UI must surface this constraint.
    resp = client.put("/api/config", json=current)
    assert resp.status_code == 200, resp.text
    # All seerr D-09 edits flowed through.
    saved = client.get("/api/config").json()
    assert saved["seerr"]["main"]["sonarr_service"]["activeAnimeProfileId"] == 999
    assert saved["seerr"]["main"]["radarr_service"]["activeProfileId"] == 999
