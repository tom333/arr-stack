"""FastAPI intent endpoint contracts — GET/POST/PUT on /api/intent/* (UI-01, UI-02, UI-04)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from arrconf_ui.app import create_app


@pytest.fixture
def client(
    sandboxed_intent_yml: Path,
    sandboxed_arrconf_yml: Path,
    sandboxed_configarr_yml: Path,
) -> TestClient:
    """Fresh app instance with all three sandboxed paths (intent + arrconf + configarr)."""
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# Test 1: GET /api/intent returns 200 with top-level keys
# ---------------------------------------------------------------------------


def test_get_intent_returns_200_with_top_level_keys(client: TestClient) -> None:
    """GET /api/intent returns IntentConfig as JSON with all 6 top-level keys."""
    resp = client.get("/api/intent")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "categories" in body
    assert "sagas" in body
    assert "apps" in body
    assert "tools" in body
    assert "profile_definitions" in body
    assert "configarr" in body


# ---------------------------------------------------------------------------
# Test 2: GET /api/intent/schema returns the JSON Schema (200)
# ---------------------------------------------------------------------------


def test_get_intent_schema_returns_json_schema(client: TestClient) -> None:
    """GET /api/intent/schema returns the committed intent-schema.json."""
    resp = client.get("/api/intent/schema")
    assert resp.status_code == 200, resp.text
    schema = resp.json()
    assert "properties" in schema


# ---------------------------------------------------------------------------
# Test 3: POST /api/intent/diff returns two labelled diffs + has_changes
# ---------------------------------------------------------------------------


def test_post_intent_diff_returns_two_labelled_diffs(
    client: TestClient, sandboxed_intent_yml: Path
) -> None:
    """POST /api/intent/diff returns arrconf_diff, configarr_diff, has_changes."""
    current = client.get("/api/intent").json()
    resp = client.post("/api/intent/diff", json=current)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "arrconf_diff" in body
    assert "configarr_diff" in body
    assert "has_changes" in body
    assert isinstance(body["arrconf_diff"], str)
    assert isinstance(body["configarr_diff"], str)
    assert isinstance(body["has_changes"], bool)


# ---------------------------------------------------------------------------
# Test 4: POST /api/intent/diff with unchanged intent → has_changes == false
# ---------------------------------------------------------------------------


def test_post_intent_diff_unchanged_has_no_changes(
    client: TestClient,
    sandboxed_intent_yml: Path,
    sandboxed_arrconf_yml: Path,
    sandboxed_configarr_yml: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Posting the current intent regenerates files byte-identical → has_changes false.

    To test this properly: first regenerate both sandboxed files so they match
    the current intent, then POST diff — the regenerated files should match,
    producing empty diffs.
    """
    from arrconf.generators.configarr import generate_configarr_yml
    from arrconf.generators.intent import generate_arrconf_yml
    from arrconf.intent_config import load_intent

    # Regenerate both sandboxed files so they match the current intent
    intent_cfg = load_intent(sandboxed_intent_yml)
    sandboxed_arrconf_yml.write_text(generate_arrconf_yml(intent_cfg), encoding="utf-8")
    sandboxed_configarr_yml.write_text(generate_configarr_yml(intent_cfg), encoding="utf-8")

    current = client.get("/api/intent").json()
    resp = client.post("/api/intent/diff", json=current)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_changes"] is False
    assert body["arrconf_diff"] == ""
    assert body["configarr_diff"] == ""


# ---------------------------------------------------------------------------
# Test 5: PUT /api/intent writes intent.yml AND regenerates both files
# ---------------------------------------------------------------------------


def test_put_intent_writes_intent_yml_and_regenerates_both_files(
    client: TestClient,
    sandboxed_intent_yml: Path,
    sandboxed_arrconf_yml: Path,
    sandboxed_configarr_yml: Path,
) -> None:
    """PUT /api/intent → 200 {"saved": true}; intent.yml updated; both files regenerated."""
    from arrconf.generators.configarr import generate_configarr_yml
    from arrconf.generators.intent import generate_arrconf_yml
    from arrconf.intent_config import load_intent

    current = client.get("/api/intent").json()
    resp = client.put("/api/intent", json=current)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["saved"] is True

    # intent.yml was written
    assert sandboxed_intent_yml.exists()
    assert sandboxed_intent_yml.stat().st_size > 0

    # arrconf.yml + configarr.yml regenerated byte-identical to generator output
    cfg = load_intent(sandboxed_intent_yml)
    assert sandboxed_arrconf_yml.read_text("utf-8") == generate_arrconf_yml(cfg)
    assert sandboxed_configarr_yml.read_text("utf-8") == generate_configarr_yml(cfg)


# ---------------------------------------------------------------------------
# Test 6: PUT /api/intent with invalid payload → 422, no files written
# ---------------------------------------------------------------------------


def test_put_intent_with_invalid_payload_returns_422(
    client: TestClient, sandboxed_intent_yml: Path
) -> None:
    """PUT /api/intent with extra forbidden field returns 422; intent.yml unchanged."""
    original = sandboxed_intent_yml.read_bytes()
    bad_payload = {"this_field_does_not_exist": True}
    resp = client.put("/api/intent", json=bad_payload)
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert "detail" in body
    # File unchanged
    assert sandboxed_intent_yml.read_bytes() == original


# ---------------------------------------------------------------------------
# Test 7: GET /api/config still returns 200 (read-only inspector kept)
# ---------------------------------------------------------------------------


def test_get_config_still_returns_200_readonly(client: TestClient) -> None:
    """GET /api/config must still return 200 (read-only inspector not removed)."""
    resp = client.get("/api/config")
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Test 8: PUT /api/config endpoint removed (405 or 404)
# ---------------------------------------------------------------------------


def test_put_config_endpoint_removed(client: TestClient) -> None:
    """PUT /api/config must not be routable (D-34-04) — returns 405 or 404."""
    resp = client.put("/api/config", json={})
    assert resp.status_code in (404, 405), (
        f"Expected 404 or 405 (endpoint removed), got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Test 9: PUT /api/intent writes all 3 files atomically (WR-01)
# ---------------------------------------------------------------------------


def test_put_intent_writes_all_files_atomically(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All three files written by PUT /api/intent go through _write_text_atomic (WR-01)."""
    import arrconf_ui.app as app_module

    written_paths: list[Path] = []
    real_atomic = app_module._write_text_atomic

    def recording_atomic(path: Path, text: str) -> None:
        written_paths.append(path)
        real_atomic(path, text)

    monkeypatch.setattr(app_module, "_write_text_atomic", recording_atomic)

    intent = client.get("/api/intent").json()
    resp = client.put("/api/intent", json=intent)
    assert resp.status_code == 200, resp.text

    names = sorted(p.name for p in written_paths)
    assert names == ["arrconf.yml", "configarr.yml", "intent.yml"], (
        f"expected all 3 files via _write_text_atomic, got {names}"
    )
