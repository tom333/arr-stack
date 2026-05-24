"""REQ-OBS-01: ArrApiClient._request emits client_4xx warning with body excerpt."""

from __future__ import annotations

import httpx
import pytest
import respx
import structlog.testing

from arrconf.client_base import SonarrClient
from arrconf.exceptions import AuthError, NotFoundError, ServerError


@respx.mock
def test_4xx_emits_client_4xx_warning_with_body_excerpt() -> None:
    body = '{"errors":[{"propertyName":"path","errorMessage":"Path does not exist"}]}'
    respx.post("http://sonarr.test/api/v3/rootfolder").mock(
        return_value=httpx.Response(400, text=body)
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    with structlog.testing.capture_logs() as cap_logs:
        with pytest.raises(httpx.HTTPStatusError):
            client.post("/rootfolder", json={"path": "/missing"})
    events = [e for e in cap_logs if e.get("event") == "client_4xx"]
    assert len(events) == 1
    e = events[0]
    assert e["client"] == "sonarr"
    assert e["method"] == "POST"
    assert e["path"] == "/rootfolder"
    assert e["status_code"] == 400
    assert e["body_excerpt"] == body


@respx.mock
def test_4xx_body_excerpt_truncated_at_500_chars() -> None:
    body = "x" * 600
    respx.get("http://sonarr.test/api/v3/series").mock(return_value=httpx.Response(422, text=body))
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    with structlog.testing.capture_logs() as cap_logs:
        with pytest.raises(httpx.HTTPStatusError):
            client.get("/series")
    events = [e for e in cap_logs if e.get("event") == "client_4xx"]
    assert len(events) == 1
    assert len(events[0]["body_excerpt"]) == 500
    assert events[0]["body_excerpt"] == "x" * 500


@respx.mock
def test_401_short_circuits_to_autherror_no_4xx_log() -> None:
    respx.get("http://sonarr.test/api/v3/series").mock(
        return_value=httpx.Response(401, text="unauthorized")
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    with structlog.testing.capture_logs() as cap_logs:
        with pytest.raises(AuthError):
            client.get("/series")
    assert [e for e in cap_logs if e.get("event") == "client_4xx"] == []


@respx.mock
def test_404_short_circuits_to_notfounderror_no_4xx_log() -> None:
    respx.get("http://sonarr.test/api/v3/series").mock(
        return_value=httpx.Response(404, text="not found")
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    with structlog.testing.capture_logs() as cap_logs:
        with pytest.raises(NotFoundError):
            client.get("/series")
    assert [e for e in cap_logs if e.get("event") == "client_4xx"] == []


@respx.mock
def test_5xx_path_unchanged_no_4xx_log() -> None:
    respx.get("http://sonarr.test/api/v3/series").mock(
        return_value=httpx.Response(500, text="boom")
    )
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    with structlog.testing.capture_logs() as cap_logs:
        with pytest.raises(ServerError):
            client.get("/series")
    assert [e for e in cap_logs if e.get("event") == "client_4xx"] == []
