import os

from pydantic import BaseModel

_SVC = "selfhost.svc.cluster.local"


class Settings(BaseModel):
    sonarr_url: str
    radarr_url: str
    qbittorrent_url: str
    seerr_url: str
    jellyfin_url: str
    sonarr_api_key: str | None
    radarr_api_key: str | None
    seerr_api_key: str | None
    jellyfin_api_key: str | None
    qbt_user: str | None
    qbt_pass: str | None
    refresh_seconds: int = 30
    bind: str = "0.0.0.0:8080"


def load_settings() -> Settings:
    e = os.environ.get
    return Settings(
        sonarr_url=e("SONARR_URL", f"http://sonarr.{_SVC}:8989"),
        radarr_url=e("RADARR_URL", f"http://radarr.{_SVC}:7878"),
        qbittorrent_url=e("QBITTORRENT_URL", f"http://qbittorrent.{_SVC}:8080"),
        seerr_url=e("SEERR_URL", f"http://seerr.{_SVC}:5055"),
        jellyfin_url=e("JELLYFIN_URL", f"http://jellyfin.{_SVC}:8096"),
        sonarr_api_key=e("SONARR_API_KEY"),
        radarr_api_key=e("RADARR_API_KEY"),
        seerr_api_key=e("SEERR_API_KEY"),
        jellyfin_api_key=e("JELLYFIN_API_KEY"),
        qbt_user=e("QBT_USER"),
        qbt_pass=e("QBT_PASS"),
        refresh_seconds=int(e("DASHBOARD_REFRESH_SECONDS", "30")),
        bind=e("DASHBOARD_BIND", "0.0.0.0:8080"),
    )
