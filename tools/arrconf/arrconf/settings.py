"""pydantic-settings BaseSettings for env var injection."""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Env-var-only secrets.

    SecretStr masks values in repr() and structlog output (T-01-01, D-22).
    """

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=True)

    sonarr_api_key: SecretStr | None = None  # SONARR_API_KEY
    radarr_api_key: SecretStr | None = None  # RADARR_API_KEY (Phase 3)
    prowlarr_api_key: SecretStr | None = None  # PROWLARR_API_KEY (Phase 3)
    arrconf_log_level: str = "INFO"
    arrconf_dry_run: bool = False
