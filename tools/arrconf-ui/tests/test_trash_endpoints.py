"""Tests for /api/trash/* endpoints (Phase 27 — CFGUI-05, CFGUI-06, CFGUI-08).

Covers:
- Test 1: GET /api/trash/custom-formats?app=sonarr → 200, list with trash_id/name/default_score
- Test 2: GET /api/trash/custom-formats?app=radarr → 200, non-empty list
- Test 3: GET /api/trash/quality-profiles?app=sonarr → 200, entries have trash_id + items
- Test 4: GET /api/trash/recyclarr-templates?app=radarr → 200, entries have id, no description
- Test 5: invalid app → 400
- Test 6: path-traversal app param → 400 (enum gate blocks traversal, T-27-05)
- Test 7: missing app param → 422 (FastAPI required-query)
- Test 8: trash_metadata_dir() resolves under expected path and exists
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from arrconf_ui.app import create_app
from arrconf_ui.locator import trash_metadata_dir

# One shared TestClient — these endpoints are stateless disk reads, no sandbox needed.
client = TestClient(create_app())


# ---------------------------------------------------------------------------
# Test 1: GET /api/trash/custom-formats?app=sonarr
# ---------------------------------------------------------------------------


def test_get_sonarr_custom_formats_returns_catalog() -> None:
    resp = client.get("/api/trash/custom-formats", params={"app": "sonarr"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0
    first = body[0]
    assert "trash_id" in first
    assert "name" in first
    assert "default_score" in first


# ---------------------------------------------------------------------------
# Test 2: GET /api/trash/custom-formats?app=radarr
# ---------------------------------------------------------------------------


def test_get_radarr_custom_formats_non_empty() -> None:
    resp = client.get("/api/trash/custom-formats", params={"app": "radarr"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0


# ---------------------------------------------------------------------------
# Test 3: GET /api/trash/quality-profiles?app=sonarr
# ---------------------------------------------------------------------------


def test_get_quality_profiles_have_items() -> None:
    resp = client.get("/api/trash/quality-profiles", params={"app": "sonarr"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0
    for entry in body:
        assert "trash_id" in entry, f"missing trash_id in entry: {entry}"
        assert "items" in entry, f"missing items in entry: {entry}"


# ---------------------------------------------------------------------------
# Test 4: GET /api/trash/recyclarr-templates?app=radarr — id present, no description
# ---------------------------------------------------------------------------


def test_get_recyclarr_templates_have_id_no_description() -> None:
    resp = client.get("/api/trash/recyclarr-templates", params={"app": "radarr"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0
    for entry in body:
        assert "id" in entry, f"missing id in entry: {entry}"
        # includes.json entries are {id, template} only — assert the real
        # contract (template present) rather than the absence of a key that
        # is never produced (IN-01: that absence assertion can never fail).
        assert "template" in entry, f"missing template in entry: {entry}"
        assert "description" not in entry, f"unexpected description in entry: {entry}"


# ---------------------------------------------------------------------------
# Test 5: invalid app → 400
# ---------------------------------------------------------------------------


def test_invalid_app_returns_400() -> None:
    resp = client.get("/api/trash/custom-formats", params={"app": "bogus"})
    assert resp.status_code == 400
    assert "sonarr" in resp.json()["detail"] or "radarr" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Test 6: path-traversal app param → 400 (T-27-05: enum gate blocks traversal)
# ---------------------------------------------------------------------------


def test_path_traversal_app_returns_400() -> None:
    resp = client.get("/api/trash/custom-formats", params={"app": "../../etc/passwd"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Test 7: missing app param → 422 (FastAPI required-query)
# ---------------------------------------------------------------------------


def test_missing_app_param_returns_422() -> None:
    resp = client.get("/api/trash/custom-formats")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test 8: trash_metadata_dir() resolves to expected path and exists on disk
# ---------------------------------------------------------------------------


def test_trash_metadata_dir_path() -> None:
    p = trash_metadata_dir()
    assert p.is_absolute()
    assert p.exists(), f"trash_metadata_dir not found: {p}"
    # Must end with the canonical segment (platform-agnostic)
    expected_suffix = Path("tools") / "arrconf-ui" / "web" / "src" / "assets" / "trash-metadata"
    assert str(p).endswith(str(expected_suffix)), (
        f"Expected path to end with '{expected_suffix}', got: {p}"
    )
