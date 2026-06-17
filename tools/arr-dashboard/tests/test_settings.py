import os

from arr_dashboard.settings import load_settings


def test_load_settings_defaults(monkeypatch):
    for k in list(os.environ):
        if k.endswith("_URL") or k.endswith("_API_KEY") or k.startswith("QBT_"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("RADARR_API_KEY", "rk")
    s = load_settings()
    assert s.radarr_url.endswith(":7878")
    assert s.radarr_api_key == "rk"
    assert s.refresh_seconds == 30


def test_load_settings_overrides(monkeypatch):
    monkeypatch.setenv("DASHBOARD_REFRESH_SECONDS", "10")
    monkeypatch.setenv("SONARR_URL", "http://custom:1234")
    s = load_settings()
    assert s.refresh_seconds == 10
    assert s.sonarr_url == "http://custom:1234"
