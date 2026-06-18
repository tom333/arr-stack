import httpx
import respx
from arrconf.client_base import JellyfinClient, QbittorrentClient
from arr_dashboard.settings import Settings
from arr_dashboard.sources import build_jellyfin, build_qbit


def _settings(**kw):
    base = dict(
        sonarr_url="http://sonarr:8989",
        radarr_url="http://radarr:7878",
        qbittorrent_url="http://qb:8080",
        seerr_url="http://seerr:5055",
        jellyfin_url="http://jf:8096",
        sonarr_api_key=None,
        radarr_api_key=None,
        seerr_api_key=None,
        jellyfin_api_key=None,
        qbt_user=None,
        qbt_pass=None,
    )
    base.update(kw)
    return Settings(**base)


def test_build_qbit_none_without_creds():
    assert build_qbit(_settings()) is None


@respx.mock
def test_build_qbit_logs_in_when_creds_present():
    respx.post("http://qb:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=x"})
    )
    c = build_qbit(_settings(qbt_user="u", qbt_pass="p"))
    assert isinstance(c, QbittorrentClient)


def test_build_jellyfin_none_without_key():
    assert build_jellyfin(_settings()) is None


def test_build_jellyfin_when_key_present():
    c = build_jellyfin(_settings(jellyfin_api_key="k"))
    assert isinstance(c, JellyfinClient)
