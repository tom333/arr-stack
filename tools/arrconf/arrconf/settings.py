"""pydantic-settings BaseSettings for env var injection."""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Env-var-only secrets.

    SecretStr masks values in repr() and structlog output (T-01-01, D-22).
    """

    # case_sensitive=False so the documented MAJUSCULE convention from CLAUDE.md
    # (SONARR_API_KEY, ARRCONF_LOG_LEVEL, ARRCONF_DRY_RUN) binds to lowercase
    # pydantic field names — `case_sensitive=True` would silently leave every
    # field as None even when the env var is exported.
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    sonarr_api_key: SecretStr | None = None  # SONARR_API_KEY
    radarr_api_key: SecretStr | None = None  # RADARR_API_KEY (Phase 3)
    prowlarr_api_key: SecretStr | None = None  # PROWLARR_API_KEY (Phase 3)
    qbt_user: SecretStr | None = None  # QBT_USER (Phase 5, D-05-QBT-01)
    qbt_pass: SecretStr | None = None  # QBT_PASS (Phase 5, D-05-QBT-01)
    seerr_api_key: SecretStr | None = None  # SEERR_API_KEY (Phase 6, D-06-AUTH-01)
    jellyfin_api_key: SecretStr | None = None  # JELLYFIN_API_KEY (Phase 7, D-07-AUTH-01)
    arrconf_log_level: str = "INFO"
    arrconf_dry_run: bool = False
