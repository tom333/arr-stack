"""HTTP transport: bearer auth, healthz bypass, and authed requests reach MCP."""

import pytest
from starlette.testclient import TestClient

from arrconf_mcp.http import build_app
from arrconf_mcp.server import mcp

TOKEN = "s3cret-token"  # noqa: S105 - test-only token


@pytest.fixture(autouse=True)
def _fresh_session_manager():
    # FastMCP caches one StreamableHTTPSessionManager on the singleton and its
    # run() can only be entered once. Production builds the app once; tests build
    # it per case, so reset the cache to give each TestClient a fresh manager.
    mcp._session_manager = None
    yield
    mcp._session_manager = None


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_TOKEN", TOKEN)
    with TestClient(build_app()) as c:
        yield c


def test_build_app_requires_token(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_TOKEN", "")
    with pytest.raises(RuntimeError, match="MCP_AUTH_TOKEN is required"):
        build_app()


def test_healthz_no_token(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200


def test_mcp_no_token_is_401(client):
    resp = client.get("/mcp")
    assert resp.status_code == 401
    assert resp.json() == {"error": "unauthorized"}


def test_mcp_wrong_token_is_401(client):
    resp = client.get("/mcp", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


def test_mcp_authed_passes_middleware(client):
    # A correct bearer token clears the middleware and reaches the MCP app, which
    # then handles the (intentionally minimal) request itself — anything other
    # than 401 proves the bearer gate was passed.
    resp = client.get("/mcp", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status_code != 401
