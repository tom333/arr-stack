from arrconf_mcp import clients
from arrconf_mcp.settings import McpSettings


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("SONARR_API_KEY", "k1")
    monkeypatch.setenv("SONARR_URL", "http://localhost:8989")
    s = McpSettings()
    assert s.sonarr_api_key.get_secret_value() == "k1"
    assert s.sonarr_url == "http://localhost:8989"


def test_factory_builds_sonarr(monkeypatch):
    monkeypatch.setenv("SONARR_API_KEY", "k1")
    monkeypatch.setenv("SONARR_URL", "http://sonarr.test:8989")
    clients.reset()  # clear cache
    c = clients.sonarr()
    assert c.base_url == "http://sonarr.test:8989"
    assert c.api_key == "k1"
