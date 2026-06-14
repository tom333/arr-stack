"""MCP settings: API keys (SecretStr, env) + per-app base URLs (env, with cluster defaults).

Local stdio use sets SONARR_URL=... to a port-forward or LAN address; in-cluster
deploy (Phase 3) the svc DNS defaults resolve.
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class McpSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    sonarr_api_key: SecretStr = SecretStr("")
    radarr_api_key: SecretStr = SecretStr("")
    prowlarr_api_key: SecretStr = SecretStr("")
    seerr_api_key: SecretStr = SecretStr("")
    jellyfin_api_key: SecretStr = SecretStr("")
    qbt_user: str = ""
    qbt_pass: SecretStr = SecretStr("")

    sonarr_url: str = "http://sonarr.selfhost.svc.cluster.local:8989"
    radarr_url: str = "http://radarr.selfhost.svc.cluster.local:7878"
    prowlarr_url: str = "http://prowlarr.selfhost.svc.cluster.local:9696"
    seerr_url: str = "http://seerr.selfhost.svc.cluster.local:5055"
    jellyfin_url: str = "http://jellyfin.selfhost.svc.cluster.local:8096"
    qbt_url: str = "http://qbittorrent.selfhost.svc.cluster.local:8080"
